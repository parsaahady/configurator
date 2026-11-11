"""Application service for benchmarking H.264 encoder strategies on Raspberry Pi."""

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Final

from real_time_cam.domain.constants import DEFAULT_CAMERA_DEVICE_PATH
from real_time_cam.domain.entities import (
    SUPPORTED_CAMERA_RESOLUTIONS,
    EncoderBenchmarkResult,
    EncoderKind,
    StreamConfig,
)
from real_time_cam.domain.ports import (
    AsyncProcessHandle,
    CpuTickSnapshot,
    EncoderLookupPort,
    PipelineBuilderPort,
    ProcessSpawner,
    SystemMetricsPort,
)

FPS_AVERAGE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"average:\s*([0-9]+(?:\.[0-9]+)?)"
)
SAMPLE_INTERVAL_S: Final[float] = 1.0
DEFAULT_BENCHMARK_DURATION_S: Final[float] = 10.0
SHUTDOWN_WAIT_TIMEOUT_S: Final[float] = 3.0
MS_PER_SECOND: Final[float] = 1000.0
PERCENT_SCALE: Final[float] = 100.0
MIN_STABLE_FPS_RATIO: Final[float] = 0.80


@dataclass(frozen=True, slots=True)
class BenchmarkRunOptions:
    """Parameters controlling an encoder benchmark sweep."""

    device_path: str = DEFAULT_CAMERA_DEVICE_PATH
    duration_s: float = DEFAULT_BENCHMARK_DURATION_S
    sample_interval_s: float = SAMPLE_INTERVAL_S


@dataclass(slots=True)
class _RunTelemetryAccumulator:
    """Mutable collector private to a single async benchmark execution."""

    fps_samples_hz: list[float]
    cpu_samples_percent: list[float]
    temp_samples_celsius: list[float]
    first_frame_latency_ms: float | None = None
    last_error_line: str = ""


def extract_average_fps_hz(log_line: str) -> float | None:
    """Parse ``average: XX.XX`` FPS from a ``fpsdisplaysink`` output line."""
    match = FPS_AVERAGE_PATTERN.search(log_line)
    if match is None:
        return None
    return float(match.group(1))


def _compute_cpu_delta_percent(
    previous: CpuTickSnapshot,
    current: CpuTickSnapshot,
) -> float:
    """Compute aggregate CPU load percentage `[0.0, 100.0]` between snapshots."""
    total_delta = current.total_ticks - previous.total_ticks
    if total_delta <= 0:
        return 0.0
    idle_delta = max(0, current.idle_ticks - previous.idle_ticks)
    busy_ratio = max(0.0, min(1.0, (total_delta - idle_delta) / total_delta))
    return round(busy_ratio * PERCENT_SCALE, 1)


async def _consume_process_logs(
    process: AsyncProcessHandle,
    started_at_monotonic_s: float,
    accumulator: _RunTelemetryAccumulator,
) -> None:
    """Read GStreamer stdout/stderr lines until EOF without blocking the loop."""
    while True:
        line = await process.read_line()
        if line is None:
            return
        fps_hz = extract_average_fps_hz(line)
        if fps_hz is not None:
            accumulator.fps_samples_hz.append(fps_hz)
            if accumulator.first_frame_latency_ms is None:
                elapsed_s = time.monotonic() - started_at_monotonic_s
                accumulator.first_frame_latency_ms = round(
                    elapsed_s * MS_PER_SECOND,
                    1,
                )
        if "ERROR:" in line:
            accumulator.last_error_line = line.strip()


async def _sample_pi_metrics(
    process: AsyncProcessHandle,
    metrics_reader: SystemMetricsPort,
    options: BenchmarkRunOptions,
    accumulator: _RunTelemetryAccumulator,
) -> None:
    """Periodically sample CPU load % and temperature while GStreamer runs."""
    previous_cpu = metrics_reader.read_cpu_snapshot()
    elapsed_s = 0.0
    while elapsed_s < options.duration_s and process.returncode is None:
        await asyncio.sleep(options.sample_interval_s)
        elapsed_s += options.sample_interval_s
        current_cpu = metrics_reader.read_cpu_snapshot()
        if previous_cpu is not None and current_cpu is not None:
            accumulator.cpu_samples_percent.append(
                _compute_cpu_delta_percent(previous_cpu, current_cpu)
            )
        previous_cpu = current_cpu
        temp_c = metrics_reader.read_cpu_temp_celsius()
        if temp_c is not None:
            accumulator.temp_samples_celsius.append(temp_c)


async def _gracefully_stop_process(process: AsyncProcessHandle) -> None:
    """Send SIGINT for clean EOS, falling back to kill on timeout."""
    if process.returncode is not None:
        return
    process.send_sigint()
    try:
        await asyncio.wait_for(process.wait_exit(), timeout=SHUTDOWN_WAIT_TIMEOUT_S)
    except TimeoutError:
        process.kill_process()
        await process.wait_exit()


def _summarize_benchmark_run(
    config: StreamConfig,
    accumulator: _RunTelemetryAccumulator,
) -> EncoderBenchmarkResult:
    """Compute final ``EncoderBenchmarkResult`` from collected samples."""
    mean_fps_hz = (
        round(sum(accumulator.fps_samples_hz) / len(accumulator.fps_samples_hz), 1)
        if accumulator.fps_samples_hz
        else 0.0
    )
    mean_cpu = (
        round(
            sum(accumulator.cpu_samples_percent) / len(accumulator.cpu_samples_percent),
            1,
        )
        if accumulator.cpu_samples_percent
        else 0.0
    )
    peak_temp = (
        max(accumulator.temp_samples_celsius)
        if accumulator.temp_samples_celsius
        else 0.0
    )
    min_acceptable_fps = config.fps_hz * MIN_STABLE_FPS_RATIO
    is_stable = not accumulator.last_error_line and mean_fps_hz >= min_acceptable_fps
    note = accumulator.last_error_line or ("OK" if is_stable else "Low FPS / stalled")
    return EncoderBenchmarkResult(
        resolution_label=config.resolution.get_label(),
        encoder_kind=config.encoder_kind,
        is_stable=is_stable,
        mean_cpu_percent=mean_cpu,
        peak_temp_celsius=peak_temp,
        achieved_fps_hz=mean_fps_hz,
        startup_latency_ms=accumulator.first_frame_latency_ms or 0.0,
        note=note,
    )


@dataclass(frozen=True, slots=True)
class BenchmarkDependencies:
    """Injected ports required by ``EncoderBenchmarkService``."""

    encoder_lookup: EncoderLookupPort
    pipeline_builder: PipelineBuilderPort
    metrics_reader: SystemMetricsPort
    spawner: ProcessSpawner


class EncoderBenchmarkService:
    """Runs isolated H.264 encoder benchmarks across resolutions and strategies."""

    def __init__(self, deps: BenchmarkDependencies) -> None:
        """Inject inward domain ports via ``BenchmarkDependencies``."""
        self._deps = deps

    async def benchmark_single(
        self,
        config: StreamConfig,
        options: BenchmarkRunOptions,
    ) -> EncoderBenchmarkResult:
        """Benchmark one `(resolution, encoder_kind)` combination."""
        command = self._deps.pipeline_builder.build_benchmark_command(
            config=config,
            device_path=options.device_path,
        )
        accumulator = _RunTelemetryAccumulator([], [], [])
        started_at_s = time.monotonic()
        process = await self._deps.spawner(command)
        log_task = asyncio.create_task(
            _consume_process_logs(process, started_at_s, accumulator)
        )
        await _sample_pi_metrics(
            process,
            self._deps.metrics_reader,
            options,
            accumulator,
        )
        await _gracefully_stop_process(process)
        await log_task
        return _summarize_benchmark_run(config, accumulator)

    async def run_full_matrix(
        self,
        options: BenchmarkRunOptions,
    ) -> tuple[EncoderBenchmarkResult, ...]:
        """Benchmark all supported resolutions across all registered encoders."""
        results: list[EncoderBenchmarkResult] = []
        supported_kinds = self._deps.encoder_lookup.list_supported_kinds()
        for resolution in SUPPORTED_CAMERA_RESOLUTIONS:
            for encoder_kind in supported_kinds:
                config = StreamConfig(resolution=resolution, encoder_kind=encoder_kind)
                result = await self.benchmark_single(config=config, options=options)
                results.append(result)
        return tuple(results)


def select_recommended_encoder(
    results: tuple[EncoderBenchmarkResult, ...],
) -> EncoderKind:
    """Pick the best default encoder that passes every resolution stably."""
    stable_counts: dict[EncoderKind, int] = dict.fromkeys(EncoderKind, 0)
    cpu_totals: dict[EncoderKind, float] = dict.fromkeys(EncoderKind, 0.0)
    expected_resolutions = len(SUPPORTED_CAMERA_RESOLUTIONS)
    for item in results:
        if item.is_stable:
            stable_counts[item.encoder_kind] += 1
            cpu_totals[item.encoder_kind] += item.mean_cpu_percent
    fully_stable = [
        kind for kind, count in stable_counts.items() if count == expected_resolutions
    ]
    if not fully_stable:
        return EncoderKind.SOFTWARE_X264
    return min(fully_stable, key=lambda kind: cpu_totals[kind])


def format_benchmark_markdown_report(
    results: tuple[EncoderBenchmarkResult, ...],
) -> str:
    """Render benchmark results and recommendation as a clean Markdown table."""
    recommended = select_recommended_encoder(results)
    lines = [
        "# Raspberry Pi 4 Camera H.264 Encoder Benchmark Report",
        "",
        (
            "| Resolution | Encoder | Stable | FPS (Hz) | CPU (%) "
            "| Peak Temp (°C) | First Metrics (ms) | Note |"
        ),
        "| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |",
    ]
    for row in results:
        status = "PASS" if row.is_stable else "FAIL"
        lines.append(
            f"| `{row.resolution_label}` | `{row.encoder_kind}` | {status} | "
            f"{row.achieved_fps_hz:.1f} | {row.mean_cpu_percent:.1f} | "
            f"{row.peak_temp_celsius:.1f} | {row.startup_latency_ms:.0f} | {row.note} |"
        )
    lines.extend(["", f"**Recommended Default Encoder:** `{recommended}`", ""])
    return "\n".join(lines)

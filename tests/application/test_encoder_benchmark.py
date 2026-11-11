"""Unit tests for EncoderBenchmarkService with mocked subprocesses and sysfs."""

import asyncio
from pathlib import Path

import pytest

from real_time_cam.application.encoder_benchmark import (
    BenchmarkDependencies,
    BenchmarkRunOptions,
    EncoderBenchmarkService,
    extract_average_fps_hz,
    format_benchmark_markdown_report,
    select_recommended_encoder,
)
from real_time_cam.domain.entities import (
    RESOLUTION_960X600,
    EncoderBenchmarkResult,
    EncoderKind,
    StreamConfig,
)
from real_time_cam.domain.ports import AsyncProcessHandle
from real_time_cam.infrastructure.encoders.registry import (
    create_default_encoder_registry,
)
from real_time_cam.infrastructure.gstreamer.pipeline_builder import GstPipelineBuilder
from real_time_cam.infrastructure.gstreamer.subprocess_runner import (
    spawn_gst_subprocess,
)
from real_time_cam.infrastructure.system.pi_metrics import LinuxSystemMetricsReader

EXPECTED_PARSED_FPS_HZ: float = 29.95
EXPECTED_MATRIX_CELL_COUNT: int = 4


class FakeGstProcess:
    """In-memory mock of a gst-launch-1.0 subprocess for fast deterministic tests."""

    def __init__(
        self,
        lines: list[str],
        hang_on_sigint: bool = False,
    ) -> None:
        self._lines = list(lines)
        self._hang_on_sigint = hang_on_sigint
        self._returncode: int | None = None
        self.was_killed: bool = False
        self.received_sigint: bool = False

    @property
    def returncode(self) -> int | None:
        return self._returncode

    async def read_line(self) -> str | None:
        if self._lines:
            await asyncio.sleep(0)
            return self._lines.pop(0)
        while self._returncode is None:
            await asyncio.sleep(0.005)
        return None

    def send_sigint(self) -> None:
        self.received_sigint = True
        if not self._hang_on_sigint:
            self._returncode = 0

    def kill_process(self) -> None:
        self.was_killed = True
        self._returncode = -9

    async def wait_exit(self) -> int:
        while self._returncode is None:
            await asyncio.sleep(0.005)
        return self._returncode


def test_extract_average_fps_hz_parses_gst_output() -> None:
    """Verify fpsdisplaysink log line parsing."""
    sample = (
        "/GstPipeline:p0/GstFPSDisplaySink:fpssink: "
        "last-message = rendered: 31, dropped: 0, current: 30.02, average: 29.95"
    )
    assert extract_average_fps_hz(sample) == EXPECTED_PARSED_FPS_HZ
    assert extract_average_fps_hz("Setting pipeline to PLAYING ...") is None


def test_benchmark_service_runs_full_matrix_and_formats_report(tmp_path: Path) -> None:
    """Verify full 4-way matrix runs asynchronously with mocked GStreamer & sysfs."""
    stat_file = tmp_path / "stat"
    temp_file = tmp_path / "temp"
    stat_file.write_text("cpu 100 0 50 850 0\n", encoding="utf-8")
    temp_file.write_text("51200\n", encoding="utf-8")
    reader = LinuxSystemMetricsReader(stat_file, temp_file)

    call_index = 0

    async def fake_spawner(command: tuple[str, ...]) -> AsyncProcessHandle:
        nonlocal call_index
        call_index += 1
        stat_file.write_text(
            f"cpu {100 + call_index * 20} 0 50 {850 + call_index * 80} 0\n",
            encoding="utf-8",
        )
        is_high_v4l2 = (
            "v4l2h264enc" in command and "width=1920,height=1200" in " ".join(command)
        )
        if is_high_v4l2:
            return FakeGstProcess(
                lines=["ERROR: from element v4l2h264enc0: Failed to process frame.\n"]
            )
        return FakeGstProcess(
            lines=[
                "last-message = rendered: 30, dropped: 0, "
                "current: 30.0, average: 29.9\n"
            ]
        )

    registry = create_default_encoder_registry()
    deps = BenchmarkDependencies(
        encoder_lookup=registry,
        pipeline_builder=GstPipelineBuilder(registry=registry),
        metrics_reader=reader,
        spawner=fake_spawner,
    )
    service = EncoderBenchmarkService(deps=deps)
    options = BenchmarkRunOptions(
        device_path="/dev/video1",
        duration_s=0.02,
        sample_interval_s=0.01,
    )
    results = asyncio.run(service.run_full_matrix(options))
    report = format_benchmark_markdown_report(results)

    assert len(results) == EXPECTED_MATRIX_CELL_COUNT
    assert select_recommended_encoder(results) == EncoderKind.SOFTWARE_X264
    assert "| `960x600` | `software_x264` | PASS |" in report
    assert "| `1920x1200` | `hardware_v4l2` | FAIL |" in report
    assert "**Recommended Default Encoder:** `software_x264`" in report


def test_select_recommended_encoder_fallback_when_all_fail() -> None:
    """Verify fallback to software_x264 if camera is unplugged during benchmark."""
    failed = (
        EncoderBenchmarkResult(
            resolution_label="960x600",
            encoder_kind=EncoderKind.SOFTWARE_X264,
            is_stable=False,
            mean_cpu_percent=0.0,
            peak_temp_celsius=45.0,
            achieved_fps_hz=0.0,
            startup_latency_ms=0.0,
            note="Cannot identify device",
        ),
    )
    assert select_recommended_encoder(failed) == EncoderKind.SOFTWARE_X264


def test_graceful_stop_kills_unresponsive_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify unresponsive subprocess is force-killed on shutdown timeout."""
    monkeypatch.setattr(
        "real_time_cam.application.encoder_benchmark.SHUTDOWN_WAIT_TIMEOUT_S",
        0.01,
    )
    hung_proc = FakeGstProcess(lines=[], hang_on_sigint=True)

    async def hung_spawner(_cmd: tuple[str, ...]) -> AsyncProcessHandle:
        return hung_proc

    registry = create_default_encoder_registry()
    deps = BenchmarkDependencies(
        encoder_lookup=registry,
        pipeline_builder=GstPipelineBuilder(registry=registry),
        metrics_reader=LinuxSystemMetricsReader(tmp_path / "s", tmp_path / "t"),
        spawner=hung_spawner,
    )
    service = EncoderBenchmarkService(deps=deps)
    result = asyncio.run(
        service.benchmark_single(
            StreamConfig(resolution=RESOLUTION_960X600),
            BenchmarkRunOptions(duration_s=0.01, sample_interval_s=0.005),
        )
    )
    assert hung_proc.received_sigint is True
    assert hung_proc.was_killed is True
    assert result.is_stable is False


def test_asyncio_subprocess_handle_lifecycle() -> None:
    """Verify AsyncioSubprocessHandle reads lines, sends SIGINT, and waits exit."""

    async def _exercise_handle() -> tuple[str | None, str | None, int]:
        handle = await spawn_gst_subprocess(("python3", "-c", "print('hello_gst')"))
        first_line = await handle.read_line()
        eof_line = await handle.read_line()
        exit_code = await handle.wait_exit()
        return first_line, eof_line, exit_code

    first_line, eof_line, exit_code = asyncio.run(_exercise_handle())
    assert first_line == "hello_gst\n"
    assert eof_line is None
    assert exit_code == 0

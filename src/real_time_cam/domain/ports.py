"""Abstract domain port protocols (Hexagonal Architecture inward boundaries)."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from real_time_cam.domain.entities import (
    EncoderKind,
    RtspPublishEndpoint,
    StreamConfig,
)


@dataclass(frozen=True, slots=True)
class CpuTickSnapshot:
    """Cumulative kernel CPU ticks parsed from the aggregate ``cpu`` line."""

    total_ticks: int
    idle_ticks: int


class EncoderStrategy(Protocol):
    """Strategy interface for converting raw camera frames into H.264 NAL units."""

    @property
    def kind(self) -> EncoderKind:
        """Return the unique identifier of this encoder strategy."""
        ...

    def build_encoder_tokens(self, config: StreamConfig) -> tuple[str, ...]:
        """Build GStreamer argv tokens from raw video input through ``h264parse``."""
        ...


class EncoderLookupPort(Protocol):
    """Port for looking up registered H.264 encoder strategies without if/elif."""

    def get_encoder(self, kind: EncoderKind) -> EncoderStrategy:
        """Return registered strategy for ``kind``."""
        ...

    def list_supported_kinds(self) -> tuple[EncoderKind, ...]:
        """Return all registered encoder kinds."""
        ...


class SystemMetricsPort(Protocol):
    """Port for reading host CPU tick counters and SoC temperature."""

    def read_cpu_snapshot(self) -> CpuTickSnapshot | None:
        """Return current CPU tick snapshot, or ``None`` when unsupported."""
        ...

    def read_cpu_temp_celsius(self) -> float | None:
        """Return SoC temperature in Celsius, or ``None`` when unsupported."""
        ...


class PipelineBuilderPort(Protocol):
    """Port for translating validated ``StreamConfig`` into GStreamer commands."""

    def build_rtsp_command(
        self,
        config: StreamConfig,
        device_path: str,
        endpoint: RtspPublishEndpoint,
    ) -> tuple[str, ...]:
        """Build ``gst-launch-1.0`` argv tokens pushing RTSP to MediaMTX."""
        ...

    def build_benchmark_command(
        self,
        config: StreamConfig,
        device_path: str,
    ) -> tuple[str, ...]:
        """Build ``gst-launch-1.0`` argv tokens encoding locally into ``fakesink``."""
        ...


class AsyncProcessHandle(Protocol):
    """Minimal async OS subprocess handle for non-blocking GStreamer supervision."""

    @property
    def returncode(self) -> int | None:
        """Process exit code, or ``None`` while running."""
        ...

    async def read_line(self) -> str | None:
        """Read next line from merged stdout/stderr, or ``None`` on EOF."""
        ...

    def send_sigint(self) -> None:
        """Send ``SIGINT`` for clean GStreamer EOS shutdown."""
        ...

    def kill_process(self) -> None:
        """Forcefully kill an unresponsive process."""
        ...

    async def wait_exit(self) -> int:
        """Wait until process exits and return its exit code."""
        ...


ProcessSpawner = Callable[[tuple[str, ...]], Awaitable[AsyncProcessHandle]]

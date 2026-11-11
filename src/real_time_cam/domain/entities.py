"""Immutable domain entities for camera stream configuration and benchmarks."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from real_time_cam.domain.constants import (
    DEFAULT_BITRATE_KBPS,
    DEFAULT_FPS_HZ,
    DEFAULT_MEDIAMTX_RTSP_PORT,
    DEFAULT_STREAM_PATH,
    HEIGHT_HIGH_PX,
    HEIGHT_LOW_PX,
    KEYFRAME_INTERVAL_S,
    MAX_BITRATE_KBPS,
    MAX_FPS_HZ,
    MAX_VALID_PORT,
    MIN_BITRATE_KBPS,
    MIN_FPS_HZ,
    MIN_KEYFRAME_INTERVAL_FRAMES,
    MIN_VALID_PORT,
    WIDTH_HIGH_PX,
    WIDTH_LOW_PX,
)
from real_time_cam.domain.errors import InvalidEndpointError, InvalidStreamConfigError


class EncoderKind(StrEnum):
    """Supported H.264 encoder implementations on the Raspberry Pi 4."""

    SOFTWARE_X264 = "software_x264"
    HARDWARE_V4L2 = "hardware_v4l2"


DEFAULT_ENCODER_KIND: Final[EncoderKind] = EncoderKind.SOFTWARE_X264


@dataclass(frozen=True, slots=True)
class FrameResolution:
    """Video frame dimensions in pixels (`width_px` by `height_px`)."""

    width_px: int
    height_px: int

    def get_label(self) -> str:
        """Return compact ``WIDTHxHEIGHT`` text representation."""
        return f"{self.width_px}x{self.height_px}"


RESOLUTION_960X600: Final[FrameResolution] = FrameResolution(
    width_px=WIDTH_LOW_PX,
    height_px=HEIGHT_LOW_PX,
)
RESOLUTION_1920X1200: Final[FrameResolution] = FrameResolution(
    width_px=WIDTH_HIGH_PX,
    height_px=HEIGHT_HIGH_PX,
)
SUPPORTED_CAMERA_RESOLUTIONS: Final[tuple[FrameResolution, ...]] = (
    RESOLUTION_960X600,
    RESOLUTION_1920X1200,
)


def parse_frame_resolution(label: str) -> FrameResolution:
    """Resolve a ``WIDTHxHEIGHT`` label into a supported Arducam B0495 resolution.

    Args:
        label: Resolution text such as ``"960x600"`` or ``"1920x1200"``.

    Returns:
        Matching ``FrameResolution`` instance.

    Raises:
        InvalidStreamConfigError: If ``label`` is not supported by the B0495 camera.
    """
    normalized_label = label.strip().lower()
    for candidate in SUPPORTED_CAMERA_RESOLUTIONS:
        if candidate.get_label() == normalized_label:
            return candidate
    allowed_text = ", ".join(res.get_label() for res in SUPPORTED_CAMERA_RESOLUTIONS)
    msg = f"Unsupported resolution '{label}'. Allowed: {allowed_text}."
    raise InvalidStreamConfigError(msg)


@dataclass(frozen=True, slots=True)
class StreamConfig:
    """Validated live camera encoding configuration.

    Attributes:
        resolution: Frame size in pixels (must be supported by Arducam B0495).
        fps_hz: Target output frame rate in Hertz (frames per second).
        bitrate_kbps: Target H.264 encoder bitrate in kilobits per second.
        encoder_kind: Selected H.264 encoder strategy.
    """

    resolution: FrameResolution = RESOLUTION_960X600
    fps_hz: int = DEFAULT_FPS_HZ
    bitrate_kbps: int = DEFAULT_BITRATE_KBPS
    encoder_kind: EncoderKind = DEFAULT_ENCODER_KIND

    def __post_init__(self) -> None:
        """Enforce Arducam B0495 resolution and safe streaming bounds."""
        if self.resolution not in SUPPORTED_CAMERA_RESOLUTIONS:
            msg = f"Unsupported camera resolution: {self.resolution.get_label()}."
            raise InvalidStreamConfigError(msg)
        if not (MIN_FPS_HZ <= self.fps_hz <= MAX_FPS_HZ):
            msg = f"fps_hz ({self.fps_hz}) must be in [{MIN_FPS_HZ}, {MAX_FPS_HZ}]."
            raise InvalidStreamConfigError(msg)
        if not (MIN_BITRATE_KBPS <= self.bitrate_kbps <= MAX_BITRATE_KBPS):
            msg = (
                f"bitrate_kbps ({self.bitrate_kbps}) must be in "
                f"[{MIN_BITRATE_KBPS}, {MAX_BITRATE_KBPS}]."
            )
            raise InvalidStreamConfigError(msg)

    def compute_keyframe_interval_frames(self) -> int:
        """Compute IDR keyframe interval in frames for sub-second stream recovery."""
        return max(MIN_KEYFRAME_INTERVAL_FRAMES, self.fps_hz * KEYFRAME_INTERVAL_S)


@dataclass(frozen=True, slots=True)
class RtspPublishEndpoint:
    """Target MediaMTX RTSP ingestion endpoint (never hardcoded in source).

    Attributes:
        host: Hostname or IP address of the laptop running MediaMTX.
        port: TCP port of MediaMTX RTSP listener.
        stream_path: MediaMTX path name without leading slash.
    """

    host: str
    port: int = DEFAULT_MEDIAMTX_RTSP_PORT
    stream_path: str = DEFAULT_STREAM_PATH

    def __post_init__(self) -> None:
        """Validate host, port range, and non-empty stream path."""
        cleaned_host = self.host.strip()
        cleaned_path = self.stream_path.strip().strip("/")
        if not cleaned_host or "/" in cleaned_host or " " in cleaned_host:
            msg = f"Invalid MediaMTX host: '{self.host}'."
            raise InvalidEndpointError(msg)
        if not (MIN_VALID_PORT <= self.port <= MAX_VALID_PORT):
            msg = f"Invalid RTSP port: {self.port}."
            raise InvalidEndpointError(msg)
        if not cleaned_path:
            msg = "MediaMTX stream_path must not be empty."
            raise InvalidEndpointError(msg)

    def build_rtsp_url(self) -> str:
        """Format full ``rtsp://host:port/path`` URL."""
        cleaned_host = self.host.strip()
        cleaned_path = self.stream_path.strip().strip("/")
        return f"rtsp://{cleaned_host}:{self.port}/{cleaned_path}"


@dataclass(frozen=True, slots=True)
class EncoderBenchmarkResult:
    """Summary metrics from a single Raspberry Pi H.264 encoder benchmark run."""

    resolution_label: str
    encoder_kind: EncoderKind
    is_stable: bool
    mean_cpu_percent: float
    peak_temp_celsius: float
    achieved_fps_hz: float
    startup_latency_ms: float
    note: str

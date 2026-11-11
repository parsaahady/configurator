"""Pure GStreamer command-line token builders implementing ``PipelineBuilderPort``."""

import shlex
from dataclasses import dataclass
from typing import Final

from real_time_cam.domain.constants import (
    CAMERA_RAW_PIXEL_FORMAT,
    DEFAULT_CAMERA_DEVICE_PATH,
    MAX_CAPTURE_QUEUE_BUFFERS,
    RTSP_SINK_LATENCY_MS,
)
from real_time_cam.domain.entities import RtspPublishEndpoint, StreamConfig
from real_time_cam.domain.ports import EncoderLookupPort

GST_LAUNCH_BINARY: Final[str] = "gst-launch-1.0"
BENCHMARK_FPS_UPDATE_INTERVAL_MS: Final[int] = 1000


@dataclass(frozen=True, slots=True)
class CameraSourceSpec:
    """V4L2 camera capture source parameters."""

    config: StreamConfig
    device_path: str = DEFAULT_CAMERA_DEVICE_PATH


def build_camera_capture_tokens(source: CameraSourceSpec) -> tuple[str, ...]:
    """Build V4L2 raw ``YUY2`` capture, frame-rate limiter, and leaky queue tokens."""
    raw_caps = (
        f"video/x-raw,format={CAMERA_RAW_PIXEL_FORMAT},"
        f"width={source.config.resolution.width_px},"
        f"height={source.config.resolution.height_px}"
    )
    rate_caps = f"video/x-raw,framerate={source.config.fps_hz}/1"
    return (
        "v4l2src",
        f"device={source.device_path}",
        "do-timestamp=true",
        "!",
        raw_caps,
        "!",
        "videorate",
        "drop-only=true",
        f"max-rate={source.config.fps_hz}",
        "!",
        rate_caps,
        "!",
        "queue",
        f"max-size-buffers={MAX_CAPTURE_QUEUE_BUFFERS}",
        "leaky=downstream",
    )


def build_rtsp_push_command(
    source: CameraSourceSpec,
    endpoint: RtspPublishEndpoint,
    registry: EncoderLookupPort,
) -> tuple[str, ...]:
    """Build complete ``gst-launch-1.0`` argv tokens pushing H.264 to MediaMTX."""
    encoder = registry.get_encoder(source.config.encoder_kind)
    capture_tokens = build_camera_capture_tokens(source)
    encoder_tokens = encoder.build_encoder_tokens(source.config)
    sink_tokens = (
        "rtspclientsink",
        f"location={endpoint.build_rtsp_url()}",
        "protocols=tcp",
        f"latency={RTSP_SINK_LATENCY_MS}",
    )
    return (
        GST_LAUNCH_BINARY,
        "-e",
        *capture_tokens,
        "!",
        *encoder_tokens,
        "!",
        *sink_tokens,
    )


def build_local_benchmark_command(
    source: CameraSourceSpec,
    registry: EncoderLookupPort,
) -> tuple[str, ...]:
    """Build ``gst-launch-1.0`` argv tokens encoding camera video into ``fakesink``."""
    encoder = registry.get_encoder(source.config.encoder_kind)
    capture_tokens = build_camera_capture_tokens(source)
    encoder_tokens = encoder.build_encoder_tokens(source.config)
    sink_tokens = (
        "fpsdisplaysink",
        "name=fpssink",
        "text-overlay=false",
        "video-sink=fakesink",
        "sync=false",
        f"fps-update-interval={BENCHMARK_FPS_UPDATE_INTERVAL_MS}",
    )
    return (
        GST_LAUNCH_BINARY,
        "-e",
        "-v",
        *capture_tokens,
        "!",
        *encoder_tokens,
        "!",
        *sink_tokens,
    )


class GstPipelineBuilder:
    """Adapter implementing ``PipelineBuilderPort`` using an ``EncoderLookupPort``."""

    def __init__(self, registry: EncoderLookupPort) -> None:
        """Inject encoder strategy lookup registry."""
        self._registry = registry

    def build_rtsp_command(
        self,
        config: StreamConfig,
        device_path: str,
        endpoint: RtspPublishEndpoint,
    ) -> tuple[str, ...]:
        """Build ``gst-launch-1.0`` argv tokens pushing RTSP to MediaMTX."""
        source = CameraSourceSpec(config=config, device_path=device_path)
        return build_rtsp_push_command(source, endpoint, self._registry)

    def build_benchmark_command(
        self,
        config: StreamConfig,
        device_path: str,
    ) -> tuple[str, ...]:
        """Build ``gst-launch-1.0`` argv tokens encoding locally into ``fakesink``."""
        source = CameraSourceSpec(config=config, device_path=device_path)
        return build_local_benchmark_command(source, self._registry)


def format_command_for_shell(command_tokens: tuple[str, ...]) -> str:
    """Format argv tokens as a POSIX shell-escaped command string for display."""
    return shlex.join(command_tokens)

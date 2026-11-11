"""CLI entrypoint to push Arducam B0495 H.264 stream over RTSP to MediaMTX."""

import argparse
import subprocess
from typing import Final

from real_time_cam.domain.constants import (
    DEFAULT_BITRATE_KBPS,
    DEFAULT_CAMERA_DEVICE_PATH,
    DEFAULT_FPS_HZ,
    DEFAULT_MEDIAMTX_RTSP_PORT,
    DEFAULT_STREAM_PATH,
)
from real_time_cam.domain.entities import (
    DEFAULT_ENCODER_KIND,
    RESOLUTION_960X600,
    EncoderKind,
    RtspPublishEndpoint,
    StreamConfig,
    parse_frame_resolution,
)
from real_time_cam.infrastructure.encoders.registry import (
    create_default_encoder_registry,
)
from real_time_cam.infrastructure.gstreamer.pipeline_builder import (
    CameraSourceSpec,
    build_rtsp_push_command,
    format_command_for_shell,
)

SIGINT_EXIT_CODE: Final[int] = 0


def build_push_arg_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for streaming camera video to MediaMTX."""
    parser = argparse.ArgumentParser(
        description="Push Arducam YUY2 camera as H.264 RTSP stream to MediaMTX."
    )
    parser.add_argument(
        "--mediamtx-host",
        required=True,
        help="Laptop IP or hostname running MediaMTX (never hardcoded).",
    )
    parser.add_argument(
        "--rtsp-port",
        type=int,
        default=DEFAULT_MEDIAMTX_RTSP_PORT,
        help="MediaMTX RTSP port (default: 8554).",
    )
    parser.add_argument(
        "--stream-path",
        default=DEFAULT_STREAM_PATH,
        help="MediaMTX stream path name (default: cam).",
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_CAMERA_DEVICE_PATH,
        help="V4L2 camera device path (default: /dev/video1).",
    )
    parser.add_argument(
        "--resolution",
        default=RESOLUTION_960X600.get_label(),
        help="Camera resolution: 960x600 or 1920x1200 (default: 960x600).",
    )
    parser.add_argument(
        "--fps-hz",
        type=int,
        default=DEFAULT_FPS_HZ,
        help="Target frame rate in Hz (default: 30).",
    )
    parser.add_argument(
        "--bitrate-kbps",
        type=int,
        default=DEFAULT_BITRATE_KBPS,
        help="Target H.264 bitrate in kbps (default: 2000).",
    )
    parser.add_argument(
        "--encoder",
        type=EncoderKind,
        choices=list(EncoderKind),
        default=DEFAULT_ENCODER_KIND,
        help="Encoder strategy: software_x264 (default) or hardware_v4l2.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the exact gst-launch-1.0 command without executing it.",
    )
    return parser


def build_command_from_args(args: argparse.Namespace) -> tuple[str, ...]:
    """Validate CLI inputs through domain entities and build GStreamer argv."""
    config = StreamConfig(
        resolution=parse_frame_resolution(args.resolution),
        fps_hz=args.fps_hz,
        bitrate_kbps=args.bitrate_kbps,
        encoder_kind=args.encoder,
    )
    endpoint = RtspPublishEndpoint(
        host=args.mediamtx_host,
        port=args.rtsp_port,
        stream_path=args.stream_path,
    )
    source = CameraSourceSpec(config=config, device_path=args.device)
    return build_rtsp_push_command(
        source=source,
        endpoint=endpoint,
        registry=create_default_encoder_registry(),
    )


def main(argv: list[str] | None = None) -> int:
    """CLI main entry point for ``xerox-cam-push``."""
    parser = build_push_arg_parser()
    parsed_args = parser.parse_args(argv)
    command_tokens = build_command_from_args(parsed_args)
    print(
        f"GStreamer pipeline:\n  {format_command_for_shell(command_tokens)}", flush=True
    )
    if parsed_args.dry_run:
        return 0
    try:
        completed = subprocess.run(command_tokens, check=False)
    except KeyboardInterrupt:
        return SIGINT_EXIT_CODE
    return completed.returncode


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

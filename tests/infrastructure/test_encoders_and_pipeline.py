"""Unit tests for H.264 encoder strategies, registry, and GStreamer builders."""

import pytest

from real_time_cam.domain.entities import (
    RESOLUTION_960X600,
    RESOLUTION_1920X1200,
    EncoderKind,
    RtspPublishEndpoint,
    StreamConfig,
)
from real_time_cam.domain.errors import UnknownEncoderError
from real_time_cam.infrastructure.encoders.hardware_v4l2 import HardwareV4l2H264Encoder
from real_time_cam.infrastructure.encoders.registry import (
    EncoderRegistry,
    create_default_encoder_registry,
)
from real_time_cam.infrastructure.encoders.software_x264 import SoftwareH264Encoder
from real_time_cam.infrastructure.gstreamer.pipeline_builder import (
    CameraSourceSpec,
    build_local_benchmark_command,
    build_rtsp_push_command,
    format_command_for_shell,
)


def test_software_x264_encoder_uses_kbps_and_zerolatency() -> None:
    """Verify x264enc receives kbps bitrate, baseline profile, and sliced-threads."""
    encoder = SoftwareH264Encoder()
    config = StreamConfig(
        resolution=RESOLUTION_960X600,
        fps_hz=30,
        bitrate_kbps=2500,
        encoder_kind=EncoderKind.SOFTWARE_X264,
    )

    tokens = encoder.build_encoder_tokens(config)

    assert encoder.kind == EncoderKind.SOFTWARE_X264
    assert "x264enc" in tokens
    assert "tune=zerolatency" in tokens
    assert "speed-preset=ultrafast" in tokens
    assert "sliced-threads=true" in tokens
    assert "bitrate=2500" in tokens
    assert "key-int-max=30" in tokens
    assert "video/x-h264,profile=baseline" in tokens


def test_hardware_v4l2_encoder_converts_kbps_to_bps_and_sets_level() -> None:
    """Verify v4l2h264enc receives bps bitrate, bt601 colorimetry, and H.264 level."""
    encoder = HardwareV4l2H264Encoder()
    low_res_cfg = StreamConfig(
        resolution=RESOLUTION_960X600,
        fps_hz=25,
        bitrate_kbps=1800,
        encoder_kind=EncoderKind.HARDWARE_V4L2,
    )
    high_res_cfg = StreamConfig(
        resolution=RESOLUTION_1920X1200,
        fps_hz=30,
        bitrate_kbps=4000,
        encoder_kind=EncoderKind.HARDWARE_V4L2,
    )

    low_tokens = encoder.build_encoder_tokens(low_res_cfg)
    high_tokens = encoder.build_encoder_tokens(high_res_cfg)

    assert encoder.kind == EncoderKind.HARDWARE_V4L2
    assert "video/x-raw,format=I420,colorimetry=bt601" in low_tokens
    assert (
        "extra-controls=controls,repeat_sequence_header=1,"
        "video_bitrate=1800000,h264_i_frame_period=25"
    ) in low_tokens
    assert "video/x-h264,profile=baseline,level=(string)4" in low_tokens
    assert "video/x-h264,profile=baseline,level=(string)4.2" in high_tokens


def test_encoder_registry_resolves_both_strategies_and_rejects_missing() -> None:
    """Verify registry lookup without if/elif ladders and empty-registry error."""
    full_registry = create_default_encoder_registry()
    empty_registry = EncoderRegistry(strategies=())

    assert full_registry.list_supported_kinds() == (
        EncoderKind.SOFTWARE_X264,
        EncoderKind.HARDWARE_V4L2,
    )
    assert (
        full_registry.get_encoder(EncoderKind.SOFTWARE_X264).kind
        == EncoderKind.SOFTWARE_X264
    )
    assert (
        full_registry.get_encoder(EncoderKind.HARDWARE_V4L2).kind
        == EncoderKind.HARDWARE_V4L2
    )
    with pytest.raises(UnknownEncoderError):
        empty_registry.get_encoder(EncoderKind.SOFTWARE_X264)


def test_pipeline_builders_generate_rtsp_push_and_benchmark_commands() -> None:
    """Verify full GStreamer argv tokens for RTSP push and local benchmark."""
    registry = create_default_encoder_registry()
    config = StreamConfig(resolution=RESOLUTION_960X600, fps_hz=30, bitrate_kbps=2000)
    source = CameraSourceSpec(config=config, device_path="/dev/video1")
    endpoint = RtspPublishEndpoint(host="laptop.local", port=8554, stream_path="cam")

    rtsp_cmd = build_rtsp_push_command(source, endpoint, registry)
    bench_cmd = build_local_benchmark_command(source, registry)
    shell_str = format_command_for_shell(rtsp_cmd)

    assert rtsp_cmd[0] == "gst-launch-1.0"
    assert "device=/dev/video1" in rtsp_cmd
    assert "video/x-raw,format=YUY2,width=960,height=600" in rtsp_cmd
    assert "leaky=downstream" in rtsp_cmd
    assert "location=rtsp://laptop.local:8554/cam" in rtsp_cmd
    assert "latency=0" in rtsp_cmd
    assert "fpsdisplaysink" in bench_cmd
    assert "video-sink=fakesink" in bench_cmd
    assert "rtsp://laptop.local:8554/cam" in shell_str

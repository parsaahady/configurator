"""Unit tests for pure camera domain entities and guard-clause validations."""

import pytest

from real_time_cam.domain.constants import (
    DEFAULT_BITRATE_KBPS,
    DEFAULT_FPS_HZ,
    MAX_BITRATE_KBPS,
    MAX_FPS_HZ,
    MIN_BITRATE_KBPS,
    MIN_FPS_HZ,
)
from real_time_cam.domain.entities import (
    RESOLUTION_960X600,
    RESOLUTION_1920X1200,
    EncoderKind,
    FrameResolution,
    RtspPublishEndpoint,
    StreamConfig,
    parse_frame_resolution,
)
from real_time_cam.domain.errors import InvalidEndpointError, InvalidStreamConfigError


def test_parse_frame_resolution_accepts_supported_labels() -> None:
    """Verify both Arducam B0495 resolutions parse cleanly."""
    assert parse_frame_resolution("960x600") == RESOLUTION_960X600
    assert parse_frame_resolution(" 1920X1200 ") == RESOLUTION_1920X1200


def test_parse_frame_resolution_rejects_unsupported_label() -> None:
    """Verify unsupported camera resolutions raise InvalidStreamConfigError."""
    with pytest.raises(InvalidStreamConfigError, match="Unsupported resolution"):
        parse_frame_resolution("1280x720")


def test_stream_config_defaults_and_keyframe_interval() -> None:
    """Verify default StreamConfig uses 960x600@30fps x264 and 1-second IDR interval."""
    config = StreamConfig()

    assert config.resolution == RESOLUTION_960X600
    assert config.fps_hz == DEFAULT_FPS_HZ
    assert config.bitrate_kbps == DEFAULT_BITRATE_KBPS
    assert config.encoder_kind == EncoderKind.SOFTWARE_X264
    assert config.compute_keyframe_interval_frames() == DEFAULT_FPS_HZ


def test_stream_config_rejects_unsupported_resolution_object() -> None:
    """Verify arbitrary FrameResolution objects outside B0495 modes fail validation."""
    unsupported = FrameResolution(width_px=640, height_px=480)

    with pytest.raises(InvalidStreamConfigError, match="Unsupported camera resolution"):
        StreamConfig(resolution=unsupported)


@pytest.mark.parametrize("bad_fps_hz", [MIN_FPS_HZ - 1, MAX_FPS_HZ + 1, 0, -10])
def test_stream_config_rejects_out_of_range_fps(bad_fps_hz: int) -> None:
    """Verify fps_hz outside safe range raises InvalidStreamConfigError."""
    with pytest.raises(InvalidStreamConfigError, match="fps_hz"):
        StreamConfig(fps_hz=bad_fps_hz)


@pytest.mark.parametrize(
    "bad_bitrate_kbps",
    [MIN_BITRATE_KBPS - 1, MAX_BITRATE_KBPS + 1, 0],
)
def test_stream_config_rejects_out_of_range_bitrate(bad_bitrate_kbps: int) -> None:
    """Verify bitrate_kbps outside safe range raises InvalidStreamConfigError."""
    with pytest.raises(InvalidStreamConfigError, match="bitrate_kbps"):
        StreamConfig(bitrate_kbps=bad_bitrate_kbps)


def test_rtsp_publish_endpoint_builds_clean_url() -> None:
    """Verify RtspPublishEndpoint normalizes slashes and builds RTSP URL."""
    endpoint = RtspPublishEndpoint(
        host=" 192.168.10.2 ", port=8554, stream_path="/cam/"
    )

    assert endpoint.build_rtsp_url() == "rtsp://192.168.10.2:8554/cam"


@pytest.mark.parametrize(
    ("host", "port", "stream_path"),
    [
        ("", 8554, "cam"),
        ("   ", 8554, "cam"),
        ("http://bad/host", 8554, "cam"),
        ("bad host", 8554, "cam"),
        ("laptop.local", 0, "cam"),
        ("laptop.local", 70000, "cam"),
        ("laptop.local", 8554, " / "),
    ],
)
def test_rtsp_publish_endpoint_rejects_invalid_inputs(
    host: str,
    port: int,
    stream_path: str,
) -> None:
    """Verify invalid host, port, or empty stream path raises InvalidEndpointError."""
    with pytest.raises(InvalidEndpointError):
        RtspPublishEndpoint(host=host, port=port, stream_path=stream_path)

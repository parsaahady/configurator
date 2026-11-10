"""Unit tests for domain MediaMTX port constants and config alignment."""

from pathlib import Path

import pytest

from real_time_cam.domain.constants import (
    DEFAULT_MEDIAMTX_HLS_HTTP_PORT,
    DEFAULT_MEDIAMTX_RTCP_UDP_PORT,
    DEFAULT_MEDIAMTX_RTP_UDP_PORT,
    DEFAULT_MEDIAMTX_RTSP_PORT,
    DEFAULT_MEDIAMTX_WEBRTC_HTTP_PORT,
    DEFAULT_MEDIAMTX_WEBRTC_ICE_UDP_PORT,
    DEFAULT_STREAM_PATH,
    MAX_VALID_PORT,
    MIN_VALID_PORT,
    OCCUPIED_LAPTOP_UDP_PORT,
    is_usable_laptop_udp_port,
)

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
MEDIAMTX_CONFIG_PATH: Path = REPO_ROOT / "configs" / "mediamtx.yml"


@pytest.mark.parametrize(
    "candidate_port",
    [
        DEFAULT_MEDIAMTX_RTP_UDP_PORT,
        DEFAULT_MEDIAMTX_RTCP_UDP_PORT,
        DEFAULT_MEDIAMTX_WEBRTC_ICE_UDP_PORT,
        MIN_VALID_PORT,
        MAX_VALID_PORT,
    ],
)
def test_is_usable_laptop_udp_port_accepts_valid_unoccupied_ports(
    candidate_port: int,
) -> None:
    """Verify valid, non-conflicting UDP ports are accepted."""
    assert is_usable_laptop_udp_port(candidate_port) is True


@pytest.mark.parametrize(
    "invalid_port",
    [
        0,
        -1,
        MAX_VALID_PORT + 1,
        OCCUPIED_LAPTOP_UDP_PORT,
    ],
)
def test_is_usable_laptop_udp_port_rejects_invalid_or_occupied_ports(
    invalid_port: int,
) -> None:
    """Verify out-of-range ports and occupied laptop UDP port 5000 are rejected."""
    assert is_usable_laptop_udp_port(invalid_port) is False


def test_mediamtx_config_aligns_with_domain_ports_and_avoids_occupied_port() -> None:
    """Verify configs/mediamtx.yml declares expected listeners and avoids :5000."""
    config_text = MEDIAMTX_CONFIG_PATH.read_text(encoding="utf-8")

    expected_fragments = (
        f"rtspAddress: :{DEFAULT_MEDIAMTX_RTSP_PORT}",
        f"rtpAddress: :{DEFAULT_MEDIAMTX_RTP_UDP_PORT}",
        f"rtcpAddress: :{DEFAULT_MEDIAMTX_RTCP_UDP_PORT}",
        f"hlsAddress: :{DEFAULT_MEDIAMTX_HLS_HTTP_PORT}",
        f"webrtcAddress: :{DEFAULT_MEDIAMTX_WEBRTC_HTTP_PORT}",
        f"webrtcLocalUDPAddress: :{DEFAULT_MEDIAMTX_WEBRTC_ICE_UDP_PORT}",
        f"  {DEFAULT_STREAM_PATH}:",
    )
    for fragment in expected_fragments:
        assert fragment in config_text

    assert f":{OCCUPIED_LAPTOP_UDP_PORT}" not in config_text

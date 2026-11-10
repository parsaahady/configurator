"""Pure domain constants for MediaMTX network ports and stream paths."""

from typing import Final

DEFAULT_STREAM_PATH: Final[str] = "cam"

MIN_VALID_PORT: Final[int] = 1
MAX_VALID_PORT: Final[int] = 65535
OCCUPIED_LAPTOP_UDP_PORT: Final[int] = 5000

DEFAULT_MEDIAMTX_RTSP_PORT: Final[int] = 8554
DEFAULT_MEDIAMTX_RTP_UDP_PORT: Final[int] = 8000
DEFAULT_MEDIAMTX_RTCP_UDP_PORT: Final[int] = 8001
DEFAULT_MEDIAMTX_HLS_HTTP_PORT: Final[int] = 8888
DEFAULT_MEDIAMTX_WEBRTC_HTTP_PORT: Final[int] = 8889
DEFAULT_MEDIAMTX_WEBRTC_ICE_UDP_PORT: Final[int] = 8189


def is_usable_laptop_udp_port(port: int) -> bool:
    """Check whether a UDP port is in the valid range and free on the laptop.

    Args:
        port: Candidate UDP port number in ``[1, 65535]``.

    Returns:
        ``True`` if ``port`` is valid and does not collide with the occupied
        laptop UDP port (``5000``); ``False`` otherwise.
    """
    if port < MIN_VALID_PORT or port > MAX_VALID_PORT:
        return False
    return port != OCCUPIED_LAPTOP_UDP_PORT

"""Pure domain constants for MediaMTX ports, camera capabilities, and stream limits."""

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

DEFAULT_CAMERA_DEVICE_PATH: Final[str] = "/dev/video1"
CAMERA_RAW_PIXEL_FORMAT: Final[str] = "YUY2"
ENCODER_INPUT_PIXEL_FORMAT: Final[str] = "I420"
V4L2_COLORIMETRY_BT601: Final[str] = "bt601"
H264_BASELINE_PROFILE: Final[str] = "baseline"

WIDTH_LOW_PX: Final[int] = 960
HEIGHT_LOW_PX: Final[int] = 600
WIDTH_HIGH_PX: Final[int] = 1920
HEIGHT_HIGH_PX: Final[int] = 1200

MIN_FPS_HZ: Final[int] = 5
MAX_FPS_HZ: Final[int] = 60
DEFAULT_FPS_HZ: Final[int] = 30

MIN_BITRATE_KBPS: Final[int] = 300
MAX_BITRATE_KBPS: Final[int] = 12000
DEFAULT_BITRATE_KBPS: Final[int] = 2000
BITS_PER_KILOBIT: Final[int] = 1000

KEYFRAME_INTERVAL_S: Final[int] = 1
MIN_KEYFRAME_INTERVAL_FRAMES: Final[int] = 1
# Raspberry Pi 4 bcm2835-codec hangs when h264_i_frame_period == 1 (linux#4740)
MIN_V4L2_IFRAME_PERIOD_FRAMES: Final[int] = 2
PI4_H264_LEVEL_4_MAX_HEIGHT_PX: Final[int] = 1080
MAX_CAPTURE_QUEUE_BUFFERS: Final[int] = 2
RTSP_SINK_LATENCY_MS: Final[int] = 0


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

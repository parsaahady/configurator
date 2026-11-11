"""Hardware V4L2 M2M H.264 encoder strategy for Raspberry Pi 4 (`v4l2h264enc`)."""

from typing import Final

from real_time_cam.domain.constants import (
    BITS_PER_KILOBIT,
    ENCODER_INPUT_PIXEL_FORMAT,
    H264_BASELINE_PROFILE,
    MIN_V4L2_IFRAME_PERIOD_FRAMES,
    PI4_H264_LEVEL_4_MAX_HEIGHT_PX,
    V4L2_COLORIMETRY_BT601,
)
from real_time_cam.domain.entities import EncoderKind, StreamConfig

H264_LEVEL_4_0: Final[str] = "4"
H264_LEVEL_4_2: Final[str] = "4.2"


def select_v4l2_h264_level(frame_height_px: int) -> str:
    """Select H.264 level string requested from ``v4l2h264enc`` downstream caps."""
    if frame_height_px <= PI4_H264_LEVEL_4_MAX_HEIGHT_PX:
        return H264_LEVEL_4_0
    return H264_LEVEL_4_2


class HardwareV4l2H264Encoder:
    """Raspberry Pi 4 VideoCore hardware H.264 encoder using ``v4l2h264enc``."""

    @property
    def kind(self) -> EncoderKind:
        """Return ``EncoderKind.HARDWARE_V4L2``."""
        return EncoderKind.HARDWARE_V4L2

    def build_encoder_tokens(self, config: StreamConfig) -> tuple[str, ...]:
        """Build ``v4l2h264enc`` GStreamer tokens for ``bcm2835-codec``.

        Note:
            Unlike ``x264enc`` (`kbps`), V4L2's ``video_bitrate`` control expects
            **bits per second** (`bps`). Also ``bcm2835-codec`` requires explicit
            ``bt601`` colorimetry when fed from UVC ``YUY2`` cameras and hangs if
            ``h264_i_frame_period == 1``.
        """
        bitrate_bps = config.bitrate_kbps * BITS_PER_KILOBIT
        iframe_period_frames = max(
            MIN_V4L2_IFRAME_PERIOD_FRAMES,
            config.compute_keyframe_interval_frames(),
        )
        level_text = select_v4l2_h264_level(config.resolution.height_px)
        extra_controls = (
            "controls,"
            "repeat_sequence_header=1,"
            f"video_bitrate={bitrate_bps},"
            f"h264_i_frame_period={iframe_period_frames}"
        )
        raw_caps = (
            f"video/x-raw,format={ENCODER_INPUT_PIXEL_FORMAT},"
            f"colorimetry={V4L2_COLORIMETRY_BT601}"
        )
        h264_caps = (
            f"video/x-h264,profile={H264_BASELINE_PROFILE},level=(string){level_text}"
        )
        return (
            "videoconvert",
            "!",
            raw_caps,
            "!",
            "v4l2h264enc",
            f"extra-controls={extra_controls}",
            "!",
            h264_caps,
            "!",
            "h264parse",
            "config-interval=-1",
        )

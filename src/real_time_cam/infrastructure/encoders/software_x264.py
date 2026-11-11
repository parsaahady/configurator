"""Software H.264 encoder strategy backed by GStreamer's x264enc."""

from real_time_cam.domain.constants import (
    ENCODER_INPUT_PIXEL_FORMAT,
    H264_BASELINE_PROFILE,
)
from real_time_cam.domain.entities import EncoderKind, StreamConfig


class SoftwareH264Encoder:
    """Low-latency CPU H.264 encoder strategy using ``x264enc``."""

    @property
    def kind(self) -> EncoderKind:
        """Return ``EncoderKind.SOFTWARE_X264``."""
        return EncoderKind.SOFTWARE_X264

    def build_encoder_tokens(self, config: StreamConfig) -> tuple[str, ...]:
        """Build zero-latency ``x264enc`` GStreamer pipeline tokens.

        Note:
            ``x264enc`` expects ``bitrate`` in **kilobits per second** (`kbps`),
            matching ``config.bitrate_kbps`` directly. ``sliced-threads=true``
            parallelizes encoding across Raspberry Pi 4's four Cortex-A72 cores
            within each frame so multi-threading adds zero frame buffering latency.
        """
        keyframe_interval_frames = config.compute_keyframe_interval_frames()
        return (
            "videoconvert",
            "!",
            f"video/x-raw,format={ENCODER_INPUT_PIXEL_FORMAT}",
            "!",
            "x264enc",
            "tune=zerolatency",
            "speed-preset=ultrafast",
            "sliced-threads=true",
            "bframes=0",
            f"bitrate={config.bitrate_kbps}",
            f"key-int-max={keyframe_interval_frames}",
            "!",
            f"video/x-h264,profile={H264_BASELINE_PROFILE}",
            "!",
            "h264parse",
            "config-interval=-1",
        )

"""Registry mapping ``EncoderKind`` values to concrete ``EncoderStrategy`` objects."""

from collections.abc import Iterable
from types import MappingProxyType

from real_time_cam.domain.entities import EncoderKind
from real_time_cam.domain.errors import UnknownEncoderError
from real_time_cam.domain.ports import EncoderStrategy
from real_time_cam.infrastructure.encoders.hardware_v4l2 import HardwareV4l2H264Encoder
from real_time_cam.infrastructure.encoders.software_x264 import SoftwareH264Encoder


class EncoderRegistry:
    """Immutable lookup registry eliminating ``if/elif`` ladders for encoders."""

    def __init__(self, strategies: Iterable[EncoderStrategy]) -> None:
        """Register strategies keyed by their ``EncoderKind``."""
        strategy_map = {strategy.kind: strategy for strategy in strategies}
        self._strategies: MappingProxyType[EncoderKind, EncoderStrategy] = (
            MappingProxyType(strategy_map)
        )

    def get_encoder(self, kind: EncoderKind) -> EncoderStrategy:
        """Return registered strategy for ``kind`` or raise ``UnknownEncoderError``."""
        strategy = self._strategies.get(kind)
        if strategy is None:
            msg = f"No encoder strategy registered for '{kind}'."
            raise UnknownEncoderError(msg)
        return strategy

    def list_supported_kinds(self) -> tuple[EncoderKind, ...]:
        """Return all registered encoder kinds in registration order."""
        return tuple(self._strategies.keys())


def create_default_encoder_registry() -> EncoderRegistry:
    """Build the standard Raspberry Pi 4 encoder registry (x264 + V4L2 M2M)."""
    return EncoderRegistry(
        strategies=(
            SoftwareH264Encoder(),
            HardwareV4l2H264Encoder(),
        )
    )

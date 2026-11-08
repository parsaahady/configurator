"""XeroxUAV real-time camera configurator and streaming control package."""

from typing import Final

PACKAGE_VERSION: Final[str] = "0.1.0"
__version__: Final[str] = PACKAGE_VERSION


def get_package_version() -> str:
    """Return the semantic version string of the real_time_cam package.

    Returns:
        Semantic version string in ``MAJOR.MINOR.PATCH`` format.
    """
    return PACKAGE_VERSION

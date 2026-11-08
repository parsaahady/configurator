"""Smoke tests verifying package layout, hexagonal layer imports, and versioning."""

from importlib import import_module

import pytest

from real_time_cam import __version__, get_package_version

HEXAGONAL_LAYER_MODULES: tuple[str, ...] = (
    "real_time_cam.domain",
    "real_time_cam.application",
    "real_time_cam.infrastructure",
    "real_time_cam.presentation",
)


def test_get_package_version_matches_dunder_version() -> None:
    """Verify the pure version query returns the package semantic version."""
    version_text = get_package_version()

    assert version_text == __version__
    assert version_text == "0.1.0"


@pytest.mark.parametrize("module_path", HEXAGONAL_LAYER_MODULES)
def test_hexagonal_layers_are_importable(module_path: str) -> None:
    """Verify every hexagonal architecture layer package imports cleanly."""
    imported_module = import_module(module_path)

    assert imported_module.__name__ == module_path

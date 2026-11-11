"""Tests verifying Step 3 local web assets, offline-only policy, and zero IPs."""

import re
from pathlib import Path

import pytest

WEB_ROOT: Path = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "real_time_cam"
    / "presentation"
    / "web"
)

EXPECTED_WEB_FILES: tuple[str, ...] = (
    "index.html",
    "styles/main.css",
    "js/constants.js",
    "js/whep-client.js",
    "js/ui-view.js",
    "js/app.js",
)

EXTERNAL_URL_PATTERN: re.Pattern[str] = re.compile(r"https?://[a-zA-Z0-9]")
HARDCODED_LAN_IP_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"
)


@pytest.mark.parametrize("relative_path", EXPECTED_WEB_FILES)
def test_web_asset_exists_and_has_no_cdn_or_hardcoded_lan_ip(
    relative_path: str,
) -> None:
    """Verify every web asset exists locally with zero CDN URLs or hardcoded IPs."""
    asset_path = WEB_ROOT / relative_path
    assert asset_path.is_file()

    content = asset_path.read_text(encoding="utf-8")
    assert len(content.strip()) > 0
    assert EXTERNAL_URL_PATTERN.search(content) is None
    assert HARDCODED_LAN_IP_PATTERN.search(content) is None


def test_index_html_declares_persian_rtl_video_and_es_module_entry() -> None:
    """Verify index.html wires RTL Persian attributes, muted live video, and app.js."""
    html_text = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

    assert 'lang="fa"' in html_text
    assert 'dir="rtl"' in html_text
    assert 'id="live-video"' in html_text
    assert 'type="module" src="./js/app.js"' in html_text

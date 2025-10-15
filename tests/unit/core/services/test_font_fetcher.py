from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.services.font_fetcher import FontFetcher, FontSource


class DummyResponse:
    def __init__(self, data: bytes):
        self.data = data

    def read(self, amt: int = -1) -> bytes:
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_font_fetcher_downloads_and_caches(tmp_path):
    font_bytes = b"\x00\x01FONT"
    response = DummyResponse(font_bytes)

    with patch("urllib.request.urlopen", return_value=response) as mock_urlopen:
        fetcher = FontFetcher(cache_directory=tmp_path / "cache")
        source = FontSource(
            url="https://fonts.gstatic.com/s/test-font.ttf",
            font_family="Test",
        )

        path1 = fetcher.fetch(source)
        assert path1 is not None
        assert path1.read_bytes() == font_bytes

        mock_urlopen.reset_mock()
        path2 = fetcher.fetch(source)
        assert path2 == path1
        mock_urlopen.assert_not_called()


def test_font_fetcher_handles_google_css(tmp_path):
    css = DummyResponse(b"@font-face { src: url('https://fonts.gstatic.com/s/test-regular.ttf'); }")
    font_bytes = DummyResponse(b"\x00\x01FONT")

    def side_effect(url, timeout=15):
        if "googleapis" in url:
            return css
        return font_bytes

    with patch("urllib.request.urlopen", side_effect=side_effect):
        fetcher = FontFetcher(cache_directory=tmp_path / "cache")
        source = FontSource(
            url="https://fonts.googleapis.com/css2?family=Test",
            font_family="Test",
        )
        path = fetcher.fetch(source)
        assert path is not None
        assert path.read_bytes() == b"\x00\x01FONT"


def test_font_fetcher_respects_network_flag(tmp_path):
    fetcher = FontFetcher(cache_directory=tmp_path / "cache", allow_network=False)
    source = FontSource(
        url="https://example.com/font.ttf",
        font_family="Example",
    )
    with patch("urllib.request.urlopen") as mock_urlopen:
        result = fetcher.fetch(source)
        assert result is None
        mock_urlopen.assert_not_called()

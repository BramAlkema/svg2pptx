"""Font fetching utilities for remote @font-face sources."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
import urllib.request

MAX_FONT_SIZE = 10 * 1024 * 1024  # 10MB safety limit


@dataclass
class FontSource:
    url: str
    font_family: str
    font_weight: str = "regular"
    font_style: str = "normal"


class FontFetcher:
    """Download and cache remote font files for embedding."""

    def __init__(
        self,
        cache_directory: str | Path | None = None,
        allow_network: bool = True,
        max_download_size: int = MAX_FONT_SIZE,
    ):
        self.cache_directory = Path(cache_directory or Path.cwd() / ".cache" / "fonts")
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        self.allow_network = allow_network
        self.max_download_size = max_download_size

    def fetch_sources(self, sources: Iterable[FontSource]) -> list[tuple[FontSource, Path]]:
        """Attempt to download each font source, returning successful paths."""
        results: list[tuple[FontSource, Path]] = []
        for source in sources:
            path = self.fetch(source)
            if path:
                results.append((source, path))
        return results

    def fetch(self, source: FontSource) -> Path | None:
        """Download a single font source, returning the cached path if available."""
        cache_key = self._cache_key(source.url)
        target_path = self.cache_directory / cache_key
        if target_path.exists():
            return target_path

        if not self.allow_network:
            return None

        parsed = urlparse(source.url)
        host = parsed.netloc.lower()
        try:
            if "fonts.googleapis.com" in host:
                css = self._download_bytes(source.url)
                if css is None:
                    return None
                urls = self._extract_urls_from_css(css.decode("utf-8", errors="ignore"))
                for font_url in urls:
                    path = self._download_to_cache(font_url)
                    if path:
                        return path
                return None
            return self._download_to_cache(source.url)
        except Exception:
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            return None

    def _download_to_cache(self, url: str) -> Path | None:
        cache_key = self._cache_key(url)
        target_path = self.cache_directory / cache_key
        data = self._download_bytes(url)
        if data is None:
            return None
        if not self._sanitize_font_data(data):
            return None
        target_path.write_bytes(data)
        return target_path

    def _download_bytes(self, url: str) -> bytes | None:
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                data = response.read(self.max_download_size + 1)
            if len(data) > self.max_download_size:
                return None
            return data
        except Exception:
            return None

    @staticmethod
    def _sanitize_font_data(data: bytes) -> bool:
        sniff = data[:32].lower()
        if b"<script" in sniff or b"<html" in sniff:
            return False
        return True

    @staticmethod
    def _extract_urls_from_css(css: str) -> list[str]:
        import re

        return [match.strip() for match in re.findall(r"url\(['\"]?(.*?)['\"]?\)", css)]

    @staticmethod
    def _cache_key(url: str) -> str:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        _, ext = os.path.splitext(url)
        ext = ext.lower() if ext else ".ttf"
        return f"{digest}{ext}"

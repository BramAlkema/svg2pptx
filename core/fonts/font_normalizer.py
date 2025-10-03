#!/usr/bin/env python3
"""
Font Normalizer for SVG @font-face

- Accepts: TTF, OTF, WOFF, WOFF2 via: data: URLs, file paths, file://, http(s)://
- Produces: TTF bytes when sfnt flavor is TrueType; OTF bytes when CFF/CFF2
- Pure Python: uses fontTools (with [woff] extra) — no system binaries
- Safe for embedding pipelines (PowerPoint/ODTTF, etc.)

Typical use:
    normalizer = FontNormalizer()
    asset = normalizer.normalize_from_src(src_string, format_hint="woff2")
    embed(asset.ttf_bytes or asset.otf_bytes)

Notes:
- WOFF/WOFF2: decompressed to original sfnt (may be TrueType *or* CFF)
- If original sfnt uses CFF/CFF2, you'll get OTF bytes (can't losslessly force TTF)
- TTC is detected and rejected (you can extend to choose a face)
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Tuple

from fontTools.ttLib import TTFont
from fontTools.ttLib.sfnt import SFNTReader

try:
    import requests  # optional; only used if available for http(s)
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False

logger = logging.getLogger(__name__)


# ---------- Models ----------

@dataclass
class FontAsset:
    # payload
    ttf_bytes: Optional[bytes]          # present when sfnt flavor is TrueType
    otf_bytes: Optional[bytes]          # present when sfnt flavor is CFF/CFF2
    flavor: str                         # "TTF" | "OTF" | "UNKNOWN"
    original_format: str                # "TTF" | "OTF" | "WOFF" | "WOFF2" | "TTC" | "UNKNOWN"
    sha256: str

    # metadata (best effort)
    family: Optional[str] = None
    subfamily: Optional[str] = None
    postscript_name: Optional[str] = None
    full_name: Optional[str] = None
    weight: Optional[int] = None        # usWeightClass
    stretch: Optional[int] = None       # usWidthClass
    italic: Optional[bool] = None
    units_per_em: Optional[int] = None
    ascent: Optional[int] = None
    descent: Optional[int] = None
    license_info: Optional[str] = None
    suggested_filename: Optional[str] = None

    @property
    def embeddable_bytes(self) -> Optional[bytes]:
        """Prefer TTF when available, else OTF."""
        return self.ttf_bytes or self.otf_bytes


# ---------- Utility: format detection ----------

_MAGIC = {
    b"\x00\x01\x00\x00": "TTF",   # TrueType sfnt
    b"OTTO": "OTF",               # CFF-based OpenType
    b"wOFF": "WOFF",
    b"wOF2": "WOFF2",
    b"ttcf": "TTC",               # TrueType Collection
}

def _detect_container(data: bytes) -> str:
    head = data[:4]
    return _MAGIC.get(head, "UNKNOWN")


# ---------- Loader: data:/file:/http(s) ----------

_DATA_URL_RE = re.compile(r"^data:([^;]+)?(;charset=[^;]+)?(;base64)?,(.*)$", re.IGNORECASE)

def _load_bytes(src: str, base_dir: Optional[str]) -> Tuple[bytes, str]:
    """
    Returns (bytes, origin_label).
    Supports data: URLs, file paths (absolute/relative), file://, http(s):// (if requests installed).
    """
    # data: URL
    m = _DATA_URL_RE.match(src.strip())
    if m:
        is_b64 = bool(m.group(3))
        payload = m.group(4)
        try:
            raw = base64.b64decode(payload) if is_b64 else payload.encode("utf-8")
            return raw, "dataurl"
        except Exception as e:
            raise ValueError(f"Invalid data URL font payload: {e}")

    # file://
    if src.lower().startswith("file://"):
        path = src[7:]
        with open(path, "rb") as f:
            return f.read(), path

    # http(s)
    if src.lower().startswith("http://") or src.lower().startswith("https://"):
        if not _HAS_REQUESTS:
            raise RuntimeError("HTTP font source requires 'requests' installed; or inline as data: URL.")
        resp = requests.get(src, timeout=20)
        resp.raise_for_status()
        return resp.content, src

    # plain path
    path = src
    if not os.path.isabs(path) and base_dir:
        path = os.path.join(base_dir, path)
    with open(path, "rb") as f:
        return f.read(), path


# ---------- Core normalizer ----------

class FontNormalizer:
    """
    Normalizes any @font-face src item to TTF (if TrueType) or OTF (if CFF).

    API:
        normalize_from_src(src, format_hint=None, base_dir=None) -> FontAsset
        normalize_from_fontface(svg_fontface_el, base_dir=None) -> FontAsset
    """

    def __init__(self):
        pass

    def normalize_from_fontface(self, fontface_el, base_dir: Optional[str] = None) -> FontAsset:
        """
        fontface_el: an <font-face> or CSS-parsed rule node that has `src` attribute/content.
        You can adapt this to your parser — this method expects:
          - .get('src') or nested <src> parsing done by caller.
        """
        src_attr = fontface_el.get("src") or ""
        # very basic parser for src lists: url(...) format('woff2'), ...
        src_items = _parse_src_list(src_attr)
        if not src_items:
            raise ValueError("No usable src in @font-face.")

        last_err = None
        for url, fmt in src_items:
            try:
                return self.normalize_from_src(url, format_hint=fmt, base_dir=base_dir)
            except Exception as e:
                last_err = e
                logger.debug(f"FontNormalizer: tried {url} ({fmt}), failed: {e}")
        # If we get here, everything failed
        raise RuntimeError(f"No @font-face src could be normalized. Last error: {last_err}")

    def normalize_from_src(
        self,
        src: str,
        *,
        format_hint: Optional[str] = None,
        base_dir: Optional[str] = None,
    ) -> FontAsset:
        data, origin = _load_bytes(src, base_dir)
        return self._normalize_bytes(data, origin, format_hint=format_hint)

    def _normalize_bytes(self, data: bytes, origin: str, *, format_hint: Optional[str]) -> FontAsset:
        container = _detect_container(data)

        # WOFF/WOFF2 → decode via fontTools
        if container in ("WOFF", "WOFF2"):
            font = TTFont(io.BytesIO(data))
            return self._font_to_asset(font, container, origin)

        if container == "TTC":
            # Could be extended to choose a face by name/index
            raise ValueError("TrueType Collections (TTC) not supported by this normalizer.")

        if container in ("TTF", "OTF"):
            font = TTFont(io.BytesIO(data))
            return self._font_to_asset(font, container, origin)

        # Try to let TTFont sniff unknown containers (some WOFFs lack magic in first 4 bytes)
        try:
            font = TTFont(io.BytesIO(data))
            # If sfnt is valid, container was just "UNKNOWN"
            return self._font_to_asset(font, container, origin)
        except Exception:
            raise ValueError(f"Unrecognized font container from {origin}: {container}")

    def _font_to_asset(self, font: TTFont, original_format: str, origin: str) -> FontAsset:
        """
        Decide output flavor, serialize, and extract metadata.
        """
        # Inspect flavor from sfnt tables
        flavor = _infer_flavor(font)  # "TTF" or "OTF"
        out_buf = io.BytesIO()
        font.save(out_buf)  # fontTools writes sfnt (TTF or OTF) accordingly
        raw = out_buf.getvalue()

        sha256 = hashlib.sha256(raw).hexdigest()
        meta = _extract_metadata(font)

        # Filename suggestion
        filename_base = meta.postscript_name or meta.family or "embedded-font"
        ext = ".ttf" if flavor == "TTF" else ".otf"
        suggested = f"{_sanitize_filename(filename_base)}{ext}"

        asset = FontAsset(
            ttf_bytes=raw if flavor == "TTF" else None,
            otf_bytes=raw if flavor == "OTF" else None,
            flavor=flavor,
            original_format=original_format,
            sha256=sha256,
            family=meta.family,
            subfamily=meta.subfamily,
            postscript_name=meta.postscript_name,
            full_name=meta.full_name,
            weight=meta.weight,
            stretch=meta.stretch,
            italic=meta.italic,
            units_per_em=meta.units_per_em,
            ascent=meta.ascent,
            descent=meta.descent,
            license_info=meta.license_info,
            suggested_filename=suggested,
        )
        logger.debug(
            f"FontNormalizer: {origin} → {asset.flavor}, orig={asset.original_format}, "
            f"family={asset.family}, ps={asset.postscript_name}, sha256={asset.sha256[:8]}…"
        )
        return asset


# ---------- Helpers ----------

@dataclass
class _Meta:
    family: Optional[str]
    subfamily: Optional[str]
    postscript_name: Optional[str]
    full_name: Optional[str]
    weight: Optional[int]
    stretch: Optional[int]
    italic: Optional[bool]
    units_per_em: Optional[int]
    ascent: Optional[int]
    descent: Optional[int]
    license_info: Optional[str]

def _infer_flavor(font: TTFont) -> str:
    """
    Decide if final sfnt is TrueType ('TTF') or CFF/CFF2 ('OTF').
    """
    # glyf -> TrueType, CFF/CFF2 -> OTF
    if "glyf" in font:
        return "TTF"
    if "CFF " in font or "CFF2" in font:
        return "OTF"
    # fallback
    return "TTF"

def _extract_name(font: TTFont, nameID: int) -> Optional[str]:
    try:
        name = font["name"].getName(nameID, 3, 1) or font["name"].getName(nameID, 1, 0)
        return str(name) if name else None
    except Exception:
        return None

def _extract_metadata(font: TTFont) -> _Meta:
    family = _extract_name(font, 1)
    subfamily = _extract_name(font, 2)
    full_name = _extract_name(font, 4)
    postscript_name = _extract_name(font, 6)
    license_info = _extract_name(font, 13) or _extract_name(font, 0)

    units = None
    ascent = None
    descent = None
    try:
        units = font["head"].unitsPerEm
        ascent = getattr(font["hhea"], "ascent", None)
        descent = getattr(font["hhea"], "descent", None)
    except Exception:
        pass

    weight = None
    stretch = None
    italic = None
    try:
        os2 = font["OS/2"]
        weight = getattr(os2, "usWeightClass", None)
        stretch = getattr(os2, "usWidthClass", None)
        italic = bool(getattr(os2, "fsSelection", 0) & 0x01)
    except Exception:
        # Try post table for italic as fallback
        try:
            italic_angle = getattr(font["post"], "italicAngle", 0)
            italic = bool(italic_angle and italic_angle != 0)
        except Exception:
            pass

    return _Meta(
        family=family,
        subfamily=subfamily,
        postscript_name=postscript_name,
        full_name=full_name,
        weight=weight,
        stretch=stretch,
        italic=italic,
        units_per_em=units,
        ascent=ascent,
        descent=descent,
        license_info=license_info,
    )

def _sanitize_filename(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("._-") or "font"

_SRC_ITEM_RE = re.compile(
    r"url\(\s*([^)]+?)\s*\)\s*(?:format\(\s*['\"]?([^)'\"]+)['\"]?\s*\))?",
    re.IGNORECASE,
)

def _parse_src_list(src_value: str) -> list[tuple[str, Optional[str]]]:
    """
    Minimal parser for `src: url(a.woff2) format('woff2'), url(b.ttf) format('truetype')`.
    Returns list of (url, format_hint).
    URL may be quoted or unquoted; data: URLs supported as-is.
    """
    items = []
    for m in _SRC_ITEM_RE.finditer(src_value or ""):
        url = m.group(1).strip().strip("'\"")
        fmt = (m.group(2) or "").strip().lower() or None
        items.append((url, fmt))
    if not items and src_value and src_value.strip().startswith("data:"):
        # Fallback for data: without url() wrapper
        return [(src_value.strip(), None)]
    return items

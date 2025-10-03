#!/usr/bin/env python3
"""
FontFaceScanner

- Scans an SVG (string or lxml element) for @font-face rules
- Supports <style> blocks and external <link rel="stylesheet" href="...">
- Parses src: url(...) format('woff2'), ...
- Normalizes each candidate with FontNormalizer to TTF/OTF bytes
- Dedupes by SHA256 and builds an index: (family, weight, style) -> FontAsset

Dependencies:
  - fonttools[woff] (for WOFF/WOFF2)
  - requests (optional; only if you want to fetch http(s) styles/fonts)
  - tinycss2 (optional; better CSS parser; falls back to regex otherwise)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Iterable

try:
    import requests  # optional for http(s)
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False

try:
    import tinycss2  # optional parsing
    _HAS_TINYCSS2 = True
except Exception:
    _HAS_TINYCSS2 = False

from lxml import etree as ET

from .font_normalizer import FontNormalizer, FontAsset, _parse_src_list


logger = logging.getLogger(__name__)


# ---------------- Models ----------------

@dataclass
class FontFaceRule:
    family: Optional[str] = None
    weight: Optional[str] = None
    style: Optional[str] = None
    stretch: Optional[str] = None
    unicode_range: Optional[str] = None
    display: Optional[str] = None
    src_items: List[Tuple[str, Optional[str]]] = field(default_factory=list)  # (url, format_hint)

@dataclass
class ScannedFont:
    rule: FontFaceRule
    asset: Optional[FontAsset]          # normalized (TTF or OTF) or None if all sources failed
    error: Optional[str] = None

@dataclass
class ScanReport:
    fonts: List[ScannedFont]
    by_key: Dict[Tuple[str, str, str], FontAsset]   # (family, weight, style) -> asset
    by_family: Dict[str, List[FontAsset]]
    dedup_sha256: Dict[str, FontAsset]
    errors: List[str] = field(default_factory=list)


# ---------------- Public API ----------------

class FontFaceScanner:
    def __init__(self, allow_remote: bool = True):
        """
        allow_remote: if False, http(s) styles and fonts are ignored (safer/air-gapped)
        """
        self.normalizer = FontNormalizer()
        self.allow_remote = allow_remote and _HAS_REQUESTS

    # Entry points -------------------------------------------------------------

    def scan_svg_string(self, svg_text: str, base_dir: Optional[str] = None) -> ScanReport:
        root = ET.fromstring(svg_text.encode("utf-8")) if isinstance(svg_text, str) else ET.fromstring(svg_text)
        return self.scan_svg_root(root, base_dir=base_dir)

    def scan_svg_root(self, svg_root: ET.Element, base_dir: Optional[str] = None) -> ScanReport:
        style_texts: List[str] = []
        errors: List[str] = []

        # 1) Collect inline <style> contents
        for style_el in _iter_style_elements(svg_root):
            txt = "".join(style_el.itertext())
            if txt.strip():
                style_texts.append(txt)

        # 2) Collect external stylesheets via <link rel="stylesheet">
        for href in _iter_stylesheet_links(svg_root):
            if not self.allow_remote and _is_http_url(href):
                errors.append(f"Skipped remote stylesheet (allow_remote=False): {href}")
                continue
            try:
                css_text, src_label = _load_text(href, base_dir)
                style_texts.append(css_text)
            except Exception as e:
                errors.append(f"Failed to load stylesheet {href}: {e}")

        # 3) Parse all gathered CSS for @font-face
        rules: List[FontFaceRule] = []
        for css in style_texts:
            try:
                rules.extend(self._parse_font_face_blocks(css))
            except Exception as e:
                errors.append(f"CSS parse failed: {e}")

        # 4) Normalize each rule -> FontAsset
        scanned: List[ScannedFont] = []
        dedup_sha: Dict[str, FontAsset] = {}
        by_key: Dict[Tuple[str, str, str], FontAsset] = {}
        by_family: Dict[str, List[FontAsset]] = {}

        for rule in rules:
            asset: Optional[FontAsset] = None
            err: Optional[str] = None
            for url, fmt in rule.src_items:
                if not self.allow_remote and _is_http_url(url):
                    err = f"Skipped remote font source (allow_remote=False): {url}"
                    continue
                try:
                    result = self.normalizer.normalize_from_src(url, format_hint=fmt, base_dir=base_dir)
                    # dedupe by sha
                    if result.sha256 not in dedup_sha:
                        dedup_sha[result.sha256] = result
                    asset = dedup_sha[result.sha256]
                    break
                except Exception as e:
                    err = str(e)
                    continue

            scanned.append(ScannedFont(rule=rule, asset=asset, error=err))

            # index by (family, weight, style)
            fam = _norm(rule.family)
            w = _norm(rule.weight) or "normal"
            st = _norm(rule.style) or "normal"
            if fam and asset:
                by_key[(fam, w, st)] = asset
                by_family.setdefault(fam, []).append(asset)

        return ScanReport(
            fonts=scanned,
            by_key=by_key,
            by_family=by_family,
            dedup_sha256=dedup_sha,
            errors=errors,
        )

    # Parsing ------------------------------------------------------------------

    def _parse_font_face_blocks(self, css_text: str) -> List[FontFaceRule]:
        if _HAS_TINYCSS2:
            return self._parse_with_tinycss2(css_text)
        return self._parse_with_regex(css_text)

    def _parse_with_tinycss2(self, css_text: str) -> List[FontFaceRule]:
        rules: List[FontFaceRule] = []
        stylesheet = tinycss2.parse_stylesheet(css_text, skip_comments=True, skip_whitespace=True)

        for rule in stylesheet:
            if rule.type != "at-rule" or rule.at_keyword.lower() != "font-face":
                continue
            decls = tinycss2.parse_declaration_list(rule.content or "", skip_comments=True, skip_whitespace=True)
            ff = FontFaceRule()
            for d in decls:
                if d.type != "declaration":
                    continue
                name = d.name.lower()
                value = tinycss2.serialize(d.value).strip()
                if name == "font-family":
                    ff.family = _strip_quotes(value)
                elif name == "font-weight":
                    ff.weight = value
                elif name == "font-style":
                    ff.style = value
                elif name == "font-stretch":
                    ff.stretch = value
                elif name == "unicode-range":
                    ff.unicode_range = value
                elif name == "font-display":
                    ff.display = value
                elif name == "src":
                    # naive split — src may contain multiple url(...) format(...)
                    ff.src_items = _parse_src_list(value)
            if ff.src_items:
                rules.append(ff)
        return rules

    def _parse_with_regex(self, css_text: str) -> List[FontFaceRule]:
        """
        Lightweight parser that handles common @font-face blocks.
        """
        rules: List[FontFaceRule] = []
        block_re = re.compile(r"@font-face\s*\{([^}]*)\}", re.IGNORECASE | re.DOTALL)
        decl_re = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;]+);")
        for m in block_re.finditer(css_text):
            body = m.group(1)
            ff = FontFaceRule()
            for dm in decl_re.finditer(body):
                name = dm.group(1).strip().lower()
                val = dm.group(2).strip()
                if name == "font-family":
                    ff.family = _strip_quotes(val)
                elif name == "font-weight":
                    ff.weight = val
                elif name == "font-style":
                    ff.style = val
                elif name == "font-stretch":
                    ff.stretch = val
                elif name == "unicode-range":
                    ff.unicode_range = val
                elif name == "font-display":
                    ff.display = val
                elif name == "src":
                    ff.src_items = _parse_src_list(val)
            if ff.src_items:
                rules.append(ff)
        return rules


# ---------------- XML helpers ----------------

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
HTML_NS = "http://www.w3.org/1999/xhtml"

def _iter_style_elements(svg_root: ET.Element) -> Iterable[ET.Element]:
    # SVG <style> and possible embedded HTML <style> within <foreignObject>
    for el in svg_root.xpath(".//*[local-name()='style']"):
        yield el

def _iter_stylesheet_links(svg_root: ET.Element) -> Iterable[str]:
    href_attrs = ("href", f"{{{XLINK_NS}}}href")
    for el in svg_root.xpath(".//*[local-name()='link' and translate(@rel,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='stylesheet']"):
        for attr in href_attrs:
            if el.get(attr):
                yield el.get(attr)


# ---------------- IO helpers ----------------

def _load_text(src: str, base_dir: Optional[str]) -> Tuple[str, str]:
    if _is_http_url(src):
        if not _HAS_REQUESTS:
            raise RuntimeError("HTTP stylesheet requires 'requests'; install or inline CSS.")
        r = requests.get(src, timeout=20)
        r.raise_for_status()
        return r.text, src

    if src.lower().startswith("file://"):
        path = src[7:]
    else:
        path = src
        if not os.path.isabs(path) and base_dir:
            path = os.path.join(base_dir, path)

    with open(path, "r", encoding="utf-8") as fh:
        return fh.read(), path

def _is_http_url(u: str) -> bool:
    s = u.lower().strip()
    return s.startswith("http://") or s.startswith("https://")

def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    return s

def _norm(s: Optional[str]) -> Optional[str]:
    return s.lower().strip() if isinstance(s, str) else None

#!/usr/bin/env python3
"""
Enhanced CSS style service for SVG2PPTX.

Lightweight CSS engine that properly handles:
- CSS cascade and specificity
- Property inheritance
- <style> blocks, #id, .class, tag selectors
- Inline style attributes
- Presentation attributes
"""

from __future__ import annotations
import re
from typing import Dict, List, Tuple, Optional
from lxml import etree as ET

# Presentation attribute → CSS property mapping (SVG spec subset)
PRESENTATION_MAP = {
    "fill": "fill",
    "fill-opacity": "fill-opacity",
    "stroke": "stroke",
    "stroke-width": "stroke-width",
    "stroke-opacity": "stroke-opacity",
    "stroke-linecap": "stroke-linecap",
    "stroke-linejoin": "stroke-linejoin",
    "stroke-miterlimit": "stroke-miterlimit",
    "stroke-dasharray": "stroke-dasharray",
    "stroke-dashoffset": "stroke-dashoffset",
    "opacity": "opacity",
    "font-family": "font-family",
    "font-size": "font-size",
    "font-weight": "font-weight",
    "font-style": "font-style",
    "text-anchor": "text-anchor",
    "text-decoration": "text-decoration",
    "letter-spacing": "letter-spacing",
    "word-spacing": "word-spacing",
    "stop-color": "stop-color",
    "stop-opacity": "stop-opacity",
    "transform": "transform",
    "display": "display",
    "visibility": "visibility",
    "clip-path": "clip-path",
    "mask": "mask",
    "filter": "filter",
}

# Inheritable properties per SVG specification
INHERITED = {
    "fill", "fill-opacity", "fill-rule",
    "stroke", "stroke-opacity", "stroke-width", "stroke-linecap",
    "stroke-linejoin", "stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset",
    "font-family", "font-size", "font-weight", "font-style", "font-variant",
    "font-stretch", "font-size-adjust",
    "text-anchor", "text-decoration", "letter-spacing", "word-spacing",
    "color", "cursor", "direction", "writing-mode",
    "clip-rule", "color-interpolation", "color-interpolation-filters",
    "color-rendering", "image-rendering", "shape-rendering", "text-rendering",
    "kerning", "dominant-baseline", "alignment-baseline", "baseline-shift",
    # Note: opacity is NOT inherited per CSS spec
}

# --- CSS Parser (handles single selectors: #id, .class, tag) ---

DECL_RE = re.compile(r'\s*([-\w]+)\s*:\s*([^;]+)\s*;?')
RULE_SPLIT_RE = re.compile(r'}')
SELECTOR_SPLIT_RE = re.compile(r'\s*,\s*')


def parse_inline_style(style_value: str) -> Dict[str, str]:
    """Parse inline style attribute into property dict."""
    out = {}
    for m in DECL_RE.finditer(style_value or ""):
        prop, val = m.group(1).strip(), m.group(2).strip()
        # Remove !important for now (could track priority separately)
        val = re.sub(r'\s*!\s*important\s*$', '', val, flags=re.IGNORECASE)
        out[prop] = val
    return out


def _specificity(selector: str) -> Tuple[int, int, int]:
    """
    Calculate CSS specificity: (id_count, class_count, tag_count).

    For simple selectors:
    - #id -> (1, 0, 0)
    - .class -> (0, 1, 0)
    - tag -> (0, 0, 1)
    """
    selector = selector.strip()
    if selector.startswith('#'):
        return (1, 0, 0)
    if selector.startswith('.'):
        return (0, 1, 0)
    # Element/tag selector
    return (0, 0, 1)


def parse_css(css_text: str) -> List[Tuple[str, Dict[str, str], Tuple[int, int, int], int]]:
    """
    Parse CSS text into rules.

    Returns:
        List of (selector, declarations, specificity, order) tuples.
        Order preserves source order for stable tie-breaking.
    """
    rules = []
    order = 0

    # Remove CSS comments
    css_text = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)

    # Simple block parser: selector { declarations }
    i = 0
    while True:
        start = css_text.find('{', i)
        if start == -1:
            break

        # Find matching }
        end_match = RULE_SPLIT_RE.search(css_text, start + 1)
        if not end_match:
            break
        end = end_match.start()

        selectors_part = css_text[i:start].strip()
        body = css_text[start + 1:end].strip()
        i = end_match.end()

        if not body or not selectors_part:
            continue

        # Parse declarations
        decls = parse_inline_style(body if body.endswith(';') else body + ';')

        # Split comma-separated selectors
        for sel in SELECTOR_SPLIT_RE.split(selectors_part):
            sel = sel.strip()
            if not sel:
                continue
            rules.append((sel, decls, _specificity(sel), order))
            order += 1

    return rules


def _matches(element: ET.Element, selector: str) -> bool:
    """Check if element matches CSS selector."""
    tag = element.tag

    # Handle namespaced tags like "{http://www.w3.org/2000/svg}rect"
    if isinstance(tag, str) and tag.startswith('{'):
        tag = tag.split('}', 1)[1]

    selector = selector.strip()

    if selector.startswith('#'):
        # ID selector
        wanted = selector[1:]
        return element.get('id') == wanted

    if selector.startswith('.'):
        # Class selector
        wanted = selector[1:]
        classes = (element.get('class') or '').split()
        return wanted in classes

    # Tag selector
    return tag == selector


def _merge(dst: Dict[str, str], src: Dict[str, str]) -> None:
    """Merge source properties into destination."""
    for k, v in src.items():
        dst[k] = v


class StyleService:
    """
    Minimal but correct CSS engine for SVG.

    Features:
    - Collects and parses <style> blocks on initialization
    - Computes styles respecting cascade, specificity, and inheritance
    - Handles presentation attributes and inline styles correctly
    - Provides convenience methods for common property access
    """

    def __init__(self, svg_root: Optional[ET.Element] = None) -> None:
        """
        Initialize StyleService.

        Args:
            svg_root: Optional SVG root element to parse styles from
        """
        self.rules: List[Tuple[str, Dict[str, str], Tuple[int, int, int], int]] = []
        if svg_root is not None:
            self._collect_style_rules(svg_root)

    def _collect_style_rules(self, root: ET.Element) -> None:
        """Collect and parse all <style> elements in the document."""
        # Find all <style> elements (handle namespaces)
        for el in root.iter():
            tag = el.tag
            if isinstance(tag, str) and (tag == 'style' or tag.endswith('}style')):
                css_text = (el.text or '')
                if css_text.strip():
                    self.rules.extend(parse_css(css_text))

    def compute_style(self,
                     element: ET.Element,
                     parent_style: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Compute the final style for an element.

        Applies CSS cascade in correct order:
        1. Inherited properties from parent
        2. CSS rules by ascending specificity (then source order)
        3. Presentation attributes on the element
        4. Inline style="" attribute (highest priority)

        Args:
            element: The element to compute style for
            parent_style: Parent element's computed style for inheritance

        Returns:
            Dict of computed CSS properties
        """
        # 1) Start with inherited properties from parent
        style: Dict[str, str] = {}
        if parent_style:
            for k in INHERITED:
                if k in parent_style:
                    style[k] = parent_style[k]

        # 2) Apply matching CSS rules sorted by specificity then source order
        applicable = []
        for sel, decls, spec, order in self.rules:
            if _matches(element, sel):
                applicable.append((spec, order, decls))

        # Sort by specificity (ascending), then by source order (ascending)
        applicable.sort(key=lambda t: (t[0], t[1]))

        for _, _, decls in applicable:
            _merge(style, decls)

        # 3) Apply presentation attributes
        for attr, prop in PRESENTATION_MAP.items():
            if attr in element.attrib:
                style[prop] = element.attrib[attr]

        # 4) Apply inline style="" (highest priority)
        inline = element.get('style')
        if inline:
            _merge(style, parse_inline_style(inline))

        return style

    # --- Convenience methods for common property access ---

    def fill(self, style: Dict[str, str], default: Optional[str] = None) -> Optional[str]:
        """
        Get fill value from computed style.

        Args:
            style: Computed style dict
            default: Default value if not set (SVG default is black)

        Returns:
            Fill value or default
        """
        return style.get('fill', default)

    def stroke(self, style: Dict[str, str], default: Optional[str] = None) -> Optional[str]:
        """Get stroke value from computed style."""
        return style.get('stroke', default)

    def stroke_width(self, style: Dict[str, str], default: str = '1') -> str:
        """Get stroke-width value from computed style."""
        return style.get('stroke-width', default)

    def opacity(self, style: Dict[str, str], default: str = '1') -> str:
        """Get opacity value from computed style."""
        return style.get('opacity', default)

    def font_family(self, style: Dict[str, str], default: str = 'Arial') -> str:
        """Get font-family value from computed style."""
        return style.get('font-family', default)

    def font_size(self, style: Dict[str, str], default_pt: float = 12.0) -> float:
        """
        Get font-size value from computed style in points.

        Handles common units:
        - No unit or 'pt': Direct point value
        - 'px': Convert assuming 96 DPI (1px = 0.75pt)
        - 'em': Relative to parent (would need parent font-size)

        Args:
            style: Computed style dict
            default_pt: Default size in points

        Returns:
            Font size in points
        """
        v = style.get('font-size')
        if not v:
            return default_pt

        try:
            # Handle different units
            if v.endswith('pt'):
                return float(v[:-2])
            elif v.endswith('px'):
                # Standard web: 96 DPI -> 72pt/inch -> pt = px * 72/96 = px * 0.75
                return float(v[:-2]) * 0.75
            elif v.endswith('em'):
                # Would need parent font-size for proper em calculation
                # For now, treat 1em as default size
                return float(v[:-2]) * default_pt
            elif v.endswith('%'):
                # Percentage of parent font-size
                return float(v[:-1]) / 100 * default_pt
            else:
                # Assume points if no unit
                return float(v)
        except (ValueError, IndexError):
            return default_pt

    def font_weight(self, style: Dict[str, str], default: str = 'normal') -> str:
        """Get font-weight value from computed style."""
        return style.get('font-weight', default)

    def font_style(self, style: Dict[str, str], default: str = 'normal') -> str:
        """Get font-style value from computed style."""
        return style.get('font-style', default)

    def text_anchor(self, style: Dict[str, str], default: str = 'start') -> str:
        """Get text-anchor value from computed style."""
        return style.get('text-anchor', default)

    def display(self, style: Dict[str, str], default: str = 'inline') -> str:
        """Get display value from computed style."""
        return style.get('display', default)

    def visibility(self, style: Dict[str, str], default: str = 'visible') -> str:
        """Get visibility value from computed style."""
        return style.get('visibility', default)

    def is_visible(self, style: Dict[str, str]) -> bool:
        """Check if element should be rendered based on display/visibility."""
        return (self.display(style) != 'none' and
                self.visibility(style) == 'visible')
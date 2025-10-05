"""
SVG Dasharray to PowerPoint DrawingML Conversion with Policy

Converts SVG stroke-dasharray patterns to PowerPoint <a:prstDash> or <a:custDash>
with intelligent preset detection and policy-based rendering decisions.

Reference: ECMA-376 DrawingML dash patterns
"""

from __future__ import annotations
from typing import List, Tuple, Optional, TYPE_CHECKING
from math import isclose
from lxml import etree

if TYPE_CHECKING:
    from core.policy.config import Thresholds


# DrawingML values for cap:
CAP_MAP = {
    "butt": "flat",
    "square": "sq",
    "round": "rnd",
    None: None,
}


# --- Public entry point -------------------------------------------------------

def apply_svg_dash_to_ln(
    ln_el: etree._Element,
    *,
    stroke_width_px: float,
    dasharray_px: Optional[List[float]],
    dashoffset_px: float = 0.0,
    linecap: Optional[str] = None,  # "butt" | "square" | "round"
    respect_non_scaling_stroke: bool = False,
    effective_geom_scale: float = 1.0,
    thresholds: Optional['Thresholds'] = None,
) -> bool:
    """
    Given an <a:ln> element, apply SVG-like dash behavior.

    - If dasharray is None or empty or all zeros -> solid (no prstDash/custDash)
    - Else:
        * normalize offset
        * try to map to a preset (smaller XML, great compatibility)
        * otherwise emit <a:custDash> with <a:ds d="…" sp="…"/> pairs
    - Sets cap style if provided.

    Args:
        ln_el: <a:ln> element (DrawingML, namespace 'a')
        stroke_width_px: final stroke width in pixels
        dasharray_px: SVG dasharray in *final user units/pixels* (resolved)
        dashoffset_px: SVG dashoffset (pixels)
        linecap: "butt" | "square" | "round"
        respect_non_scaling_stroke: if True, don't scale by geom transforms
        effective_geom_scale: scale factor for geometry (ignored if above True)
        thresholds: Thresholds from PolicyConfig for rendering decisions

    Returns:
        True if dash pattern was applied, False if fallback needed
    """
    # Use default thresholds if not provided
    if thresholds is None:
        from core.policy.config import Thresholds
        thresholds = Thresholds()

    nsmap = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}

    # 1) Cap
    cap_val = CAP_MAP.get(linecap)
    if cap_val:
        cap_el = ln_el.find("a:cap", namespaces=nsmap)
        if cap_el is None:
            cap_el = etree.SubElement(ln_el, f"{{{nsmap['a']}}}cap")
        cap_el.attrib["val"] = cap_val

    # 2) If solid → ensure no dash children present
    if not dasharray_px or all(_almost_zero(v) for v in dasharray_px):
        _remove_dash_children(ln_el, nsmap)
        # leave solid
        return True

    # 3) Resolve stroke width and dash lengths
    eff_width = max(0.01, float(stroke_width_px))  # avoid div-by-zero
    scale = 1.0 if respect_non_scaling_stroke else float(effective_geom_scale)
    pattern_px = [max(0.0, float(x) * scale) for x in dasharray_px]
    offset_px = float(dashoffset_px) * scale if thresholds.respect_dashoffset else 0.0

    # 4) Normalize offset and pair into (dash, space)
    normalized = _normalize_dasharray_with_offset(pattern_px, offset_px)
    pairs = _to_dash_space_pairs(normalized)

    # 5) Apply policy constraints
    if len(pairs) > thresholds.max_dash_segments:
        # Too many segments - degrade to solid
        _remove_dash_children(ln_el, nsmap)
        return True

    # 6) Try preset mapping first (if thresholds allow)
    preset = None
    if thresholds.prefer_dash_presets:
        preset = _match_preset(pairs, eff_width)

    _remove_dash_children(ln_el, nsmap)

    if preset is not None:
        # <a:prstDash val="dot|dash|lgDash|lgDashDot|lgDashDotDot|sysDash|sysDot|solid">
        prst = etree.SubElement(ln_el, f"{{{nsmap['a']}}}prstDash")
        prst.attrib["val"] = preset
        return True

    # 7) Custom dash (if thresholds allow)
    if not thresholds.allow_custom_dash:
        # Custom patterns not allowed - degrade to solid
        return True

    # 8) Emit <a:custDash>: convert to 1/1000% of line width (100000 = 100%)
    cust = etree.SubElement(ln_el, f"{{{nsmap['a']}}}custDash")
    for d_px, sp_px in pairs:
        d_u = _pct_1k(d_px / eff_width, min_pct=thresholds.min_dash_segment_pct)
        sp_u = _pct_1k(sp_px / eff_width, min_pct=thresholds.min_dash_segment_pct)
        ds = etree.SubElement(cust, f"{{{nsmap['a']}}}ds")
        ds.attrib["d"] = str(d_u)
        ds.attrib["sp"] = str(sp_u)

    return True


# --- Internals ---------------------------------------------------------------

def _remove_dash_children(ln_el: etree._Element, nsmap: dict) -> None:
    """Remove existing prstDash/custDash children"""
    for tag in ("prstDash", "custDash"):
        node = ln_el.find(f"a:{tag}", namespaces=nsmap)
        if node is not None:
            ln_el.remove(node)


def _almost_zero(x: float, eps: float = 1e-9) -> bool:
    """Check if value is effectively zero"""
    return abs(x) <= eps


def _loop_len(seq: List[float]) -> float:
    """Calculate total length of dash pattern"""
    return sum(seq)


def _normalize_dasharray_with_offset(pattern: List[float], offset: float) -> List[float]:
    """
    Rotate/trim pattern so the first segment begins at the given offset
    (mod total pattern length).
    Keeps the dash/space phase correct.

    SVG semantics: pattern repeats; offset shifts start point along the path.
    """
    if not pattern:
        return []
    total = _loop_len(pattern)
    if _almost_zero(total):
        return pattern[:]  # degenerate, but nothing to do

    o = offset % total
    if _almost_zero(o):
        return pattern[:]

    # Walk the pattern subtracting offset until the segment in which it lands
    out: List[float] = []
    i = 0
    seg = pattern[i]
    while o > 0:
        if o >= seg:
            o -= seg
            i = (i + 1) % len(pattern)
            seg = pattern[i]
        else:
            # Trim the current segment by 'o'
            seg -= o
            o = 0
            # Start new sequence from the trimmed segment
            out.append(seg)
            i = (i + 1) % len(pattern)
            break

    # Append the rest, continuing from i
    for k in range(len(pattern) - (1 if out else 0)):
        idx = (i + k) % len(pattern)
        out.append(pattern[idx])

    # If we trimmed into the middle of a segment, ensure phase alignment is preserved:
    # If we started mid-segment, the preceding partial was consumed by offset; remainder is first.
    return out


def _to_dash_space_pairs(pattern: List[float]) -> List[Tuple[float, float]]:
    """
    Convert a sequence [d1, s1, d2, s2, ...] into list of (dash, space) pairs.
    If odd length, the sequence is cycled: [d1, s1, d2] -> (d1,s1), (d2, s1) …
    Enforce minimal floors to avoid rendering collapse in PPT.
    """
    if not pattern:
        return []

    # Floor tiny segments to ~1% of stroke width at serialization stage,
    # but avoid true zeros here to keep pairing sane.
    # Still clip negative to zero (already ensured upstream).
    seq = pattern[:]
    if len(seq) % 2 == 1:
        seq.append(seq[1] if len(seq) > 1 else seq[0])

    pairs: List[Tuple[float, float]] = []
    for i in range(0, len(seq), 2):
        d = max(0.0, seq[i])
        sp = max(0.0, seq[i + 1])
        pairs.append((d, sp))
    return pairs


def _pct_1k(ratio: float, min_pct: float = 0.01) -> int:
    """
    Convert ratio (e.g., 2.5 = 250%) to DrawingML unit:
    1/1000 of a percent → 100000 == 100%.
    Clamp to [min_pct%, 100000] to avoid collapse and overflows.

    Args:
        ratio: Ratio (1.0 = 100%)
        min_pct: Minimum percent (default 1% = 0.01)

    Returns:
        DrawingML units (1/1000%)
    """
    # Avoid collapse at slideshow zoom: enforce >= min_pct% (default 1000 units = 1%)
    val = int(round(ratio * 100000))
    min_val = int(round(min_pct * 100000))
    return max(min_val, min(100000, val))


# --- Preset matching (heuristics) --------------------------------------------

def _match_preset(pairs: List[Tuple[float, float]], stroke_w: float) -> Optional[str]:
    """
    Try to identify common presets from the normalized (dash, space) pairs.
    Returns a DrawingML preset name or None.
    Presets we care about: solid, dot, dash, lgDash, lgDashDot, lgDashDotDot, sysDash, sysDot.
    Heuristics based on relative lengths to stroke width.
    """
    if not pairs:
        return "solid"

    # Normalize to width ratios
    rs = [(d / stroke_w, sp / stroke_w if stroke_w > 0 else 0.0) for d, sp in pairs]

    # Helpers
    def pattern_is(reps: int, tol=0.25):
        return len(rs) == reps

    def near(a, b, tol=0.25):
        # relative tolerance
        if a == b == 0:
            return True
        return isclose(a, b, rel_tol=tol, abs_tol=tol * 0.1)

    # Very small dash vs space looks like dot
    # Typical "dot": tiny dash (~0–0.5w), medium/large space (>0.8w)
    if pattern_is(1) and rs[0][0] <= 0.5 and rs[0][1] >= 0.8:
        return "dot"

    # "dash": dash ≈ 2–3x width, space ≈ ~1x width
    if pattern_is(1) and 1.5 <= rs[0][0] <= 3.5 and 0.5 <= rs[0][1] <= 1.5:
        return "dash"

    # "lgDash": dash ≈ 4–6x width, space ≈ ~1–2x width
    if pattern_is(1) and 3.5 <= rs[0][0] <= 6.5 and 0.8 <= rs[0][1] <= 2.5:
        return "lgDash"

    # "lgDashDot": (long dash, space) + (dot, space)
    if pattern_is(2):
        (d1, s1), (d2, s2) = rs
        if d1 >= 3.0 and 0.5 <= s1 <= 2.5 and d2 <= 0.6 and 0.5 <= s2 <= 2.5:
            return "lgDashDot"

    # "lgDashDotDot": (long dash, space) + (dot, space) + (dot, space)
    if len(rs) == 3:
        (d1, s1), (d2, s2), (d3, s3) = rs
        if d1 >= 3.0 and 0.5 <= s1 <= 2.5 and d2 <= 0.6 and d3 <= 0.6 and 0.3 <= s2 <= 2.5 and 0.3 <= s3 <= 2.5:
            return "lgDashDotDot"

    # "sysDot" / "sysDash" are platform presets; we can offer them as broad fallbacks
    # based on density of pattern:
    avg_len = sum(d + s for d, s in rs) / max(1, len(rs))
    if avg_len >= 4.0:
        return "sysDash"
    if avg_len <= 1.2 and all(d <= 0.6 for d, _ in rs):
        return "sysDot"

    return None

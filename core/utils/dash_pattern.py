"""
SVG Dasharray to PowerPoint custDash Conversion

Converts SVG stroke-dasharray patterns to PowerPoint DrawingML <a:custDash>
with proper percent-of-stroke-width normalization.

Reference: ECMA-376 DrawingML dash patterns
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass


# PowerPoint preset dash patterns (common cases)
# Maps normalized pattern signatures to preset names
PRESET_PATTERNS = {
    # Dot: short dash, short space (typically 1:1 ratio around 100-200% each)
    'dot': [(1, 1)],  # Very short dash/space

    # Dash: medium dash, medium space (typically 300-400% dash, similar space)
    'dash': [(3, 3)],

    # Long dash: longer segments
    'lgDash': [(8, 3)],

    # Dash-dot: dash, space, dot, space
    'dashDot': [(8, 3, 1, 3)],

    # Long dash-dot
    'lgDashDot': [(12, 3, 1, 3)],

    # Long dash-dot-dot
    'lgDashDotDot': [(12, 3, 1, 3, 1, 3)],
}


@dataclass
class DashPattern:
    """Represents a converted dash pattern for PowerPoint."""

    # List of (dash_pct, space_pct) tuples in 1/1000% units
    stops: List[Tuple[int, int]]

    # Optional preset name if pattern matches a standard preset
    preset: Optional[str] = None

    # Original SVG pattern for reference
    svg_pattern: Optional[List[float]] = None


def normalize_dasharray(dasharray: List[float]) -> List[float]:
    """
    Normalize SVG dasharray.

    SVG spec: if odd number of values, the list is repeated to yield even count.
    Example: [5, 3, 2] becomes [5, 3, 2, 5, 3, 2]

    Args:
        dasharray: SVG stroke-dasharray values (in user units)

    Returns:
        Normalized list with even count
    """
    if not dasharray:
        return []

    # Remove zeros and negatives (invalid per SVG spec)
    dasharray = [max(0.01, d) for d in dasharray if d > 0]

    if not dasharray:
        return []

    # If odd count, repeat the pattern
    if len(dasharray) % 2 != 0:
        dasharray = dasharray * 2

    return dasharray


def phase_rotate_pattern(
    dasharray: List[float],
    dashoffset: float
) -> List[float]:
    """
    Apply SVG stroke-dashoffset by rotating and trimming the pattern.

    DrawingML has no explicit offset, so we phase-shift the pattern
    to start at the correct position.

    Args:
        dasharray: Normalized dasharray (even count)
        dashoffset: SVG stroke-dashoffset value

    Returns:
        Phase-rotated pattern
    """
    if not dasharray or dashoffset == 0:
        return dasharray

    # Calculate total pattern length
    pattern_length = sum(dasharray)
    if pattern_length == 0:
        return dasharray

    # Normalize offset to pattern length (handle negative and > pattern_length)
    offset = dashoffset % pattern_length
    if offset == 0:
        return dasharray

    # Find where offset lands in the pattern
    accumulated = 0.0
    new_pattern = []
    started = False

    for i, segment in enumerate(dasharray):
        if accumulated + segment <= offset:
            # Skip this entire segment
            accumulated += segment
            continue

        if not started:
            # First segment after offset - trim the start
            trim = offset - accumulated
            if segment - trim > 0.01:  # Avoid tiny segments
                new_pattern.append(segment - trim)
            started = True
            accumulated += segment
        else:
            # Copy remaining segments
            new_pattern.append(segment)

    # Append segments before offset to end (wrapping)
    accumulated = 0.0
    for segment in dasharray:
        if accumulated >= offset:
            break
        if accumulated + segment <= offset:
            new_pattern.append(segment)
            accumulated += segment
        else:
            # Partial segment at wrap point
            remaining = offset - accumulated
            if remaining > 0.01:
                new_pattern.append(remaining)
            break

    return new_pattern if new_pattern else dasharray


def to_dash_space_pairs(pattern: List[float]) -> List[Tuple[float, float]]:
    """
    Convert flat dasharray to (dash, space) pairs.

    Args:
        pattern: Normalized dasharray [d1, s1, d2, s2, ...]

    Returns:
        List of (dash, space) tuples
    """
    pairs = []
    for i in range(0, len(pattern), 2):
        if i + 1 < len(pattern):
            pairs.append((pattern[i], pattern[i + 1]))
        else:
            # Shouldn't happen with normalized pattern, but handle it
            pairs.append((pattern[i], pattern[i]))

    return pairs


def to_percent_units(
    value: float,
    stroke_width: float,
    min_value: int = 1,  # Changed from 1000 - let caller decide clamping
    max_value: int = 100000000  # 100000% - allows dashes up to 1000x stroke width
) -> int:
    """
    Convert user unit to percent-of-stroke-width in DrawingML units.

    DrawingML uses 1/1000% units:
    - 100000 = 100%
    - 1000 = 1%
    - 500 = 0.5%

    Args:
        value: Dash/space length in user units
        stroke_width: Stroke width in user units
        min_value: Minimum value to prevent rendering glitches (default 1)
        max_value: Maximum value (default 100000000 = 100000%, allows 1000x stroke width)

    Returns:
        Value in DrawingML percent units (1/1000%)
    """
    if stroke_width <= 0:
        stroke_width = 1.0  # Fallback

    # Convert to percent of stroke width
    percent = (value / stroke_width) * 100.0

    # Convert to 1/1000% units
    units = round(percent * 1000)

    # Clamp to valid range
    return max(min_value, min(max_value, units))


def detect_preset_pattern(pairs: List[Tuple[int, int]]) -> Optional[str]:
    """
    Detect if dash pattern matches a PowerPoint preset.

    This keeps PPTX files smaller and ensures consistent rendering.

    Args:
        pairs: Dash/space pairs in DrawingML percent units

    Returns:
        Preset name or None
    """
    if not pairs:
        return None

    # Convert to ratio signatures for fuzzy matching
    # (allows some tolerance for rounding)
    def to_signature(pattern: List[Tuple[int, int]]) -> Tuple[float, ...]:
        """Convert pattern to normalized ratios"""
        if not pattern:
            return tuple()

        # Flatten
        flat = []
        for d, s in pattern:
            flat.extend([d, s])

        # Normalize to first value
        if flat[0] == 0:
            return tuple(flat)

        return tuple(v / flat[0] for v in flat)

    current_sig = to_signature(pairs)

    # Check against known presets with tolerance
    tolerance = 0.3  # 30% tolerance for fuzzy matching

    for preset_name, preset_pattern in PRESET_PATTERNS.items():
        # Convert preset pattern (normalized ratios) to signature
        preset_sig = tuple(preset_pattern) if len(preset_pattern) == len(current_sig) else None

        if preset_sig and len(preset_sig) == len(current_sig):
            # Check if all ratios match within tolerance
            match = all(
                abs(c - p) <= tolerance
                for c, p in zip(current_sig, preset_sig)
            )

            if match:
                return preset_name

    return None


def svg_dasharray_to_custdash(
    dasharray: List[float],
    stroke_width: float,
    dashoffset: float = 0.0
) -> DashPattern:
    """
    Convert SVG stroke-dasharray to PowerPoint custDash pattern.

    This is the main conversion function that:
    1. Normalizes dasharray (handle odd counts)
    2. Applies dashoffset (phase rotation)
    3. Converts to percent-of-stroke-width
    4. Detects preset patterns

    Args:
        dasharray: SVG stroke-dasharray values (user units)
        stroke_width: Stroke width (user units)
        dashoffset: SVG stroke-dashoffset (user units)

    Returns:
        DashPattern with stops and optional preset

    Example:
        >>> pattern = svg_dasharray_to_custdash(
        ...     dasharray=[5, 3, 10, 4],
        ...     stroke_width=2.0,
        ...     dashoffset=2.0
        ... )
        >>> pattern.stops
        [(150000, 150000), (500000, 200000)]
    """
    # Normalize dasharray
    pattern = normalize_dasharray(dasharray)

    if not pattern:
        # Solid line (no dashes)
        return DashPattern(stops=[], preset='solid', svg_pattern=dasharray)

    # Apply phase rotation for dashoffset
    if dashoffset != 0:
        pattern = phase_rotate_pattern(pattern, dashoffset)

    # Convert to (dash, space) pairs
    raw_pairs = to_dash_space_pairs(pattern)

    # Convert to percent units
    # Apply minimum of 1000 (1%) to prevent PowerPoint rendering glitches
    percent_pairs = [
        (
            max(1000, to_percent_units(d, stroke_width)),
            max(1000, to_percent_units(s, stroke_width))
        )
        for d, s in raw_pairs
    ]

    # Try to detect preset
    preset = detect_preset_pattern(percent_pairs)

    return DashPattern(
        stops=percent_pairs,
        preset=preset,
        svg_pattern=dasharray
    )


def linecap_svg_to_drawingml(svg_linecap: str) -> str:
    """
    Convert SVG linecap to DrawingML a:cap value.

    Args:
        svg_linecap: SVG linecap value (butt, round, square)

    Returns:
        DrawingML cap value (flat, rnd, sq)
    """
    mapping = {
        'butt': 'flat',
        'round': 'rnd',
        'square': 'sq',
    }

    return mapping.get(svg_linecap.lower(), 'flat')


def linejoin_svg_to_drawingml(svg_linejoin: str) -> str:
    """
    Convert SVG linejoin to DrawingML a:join value.

    Args:
        svg_linejoin: SVG linejoin value (miter, round, bevel)

    Returns:
        DrawingML join value (miter, round, bevel)
    """
    # Same values, but ensure lowercase
    return svg_linejoin.lower()

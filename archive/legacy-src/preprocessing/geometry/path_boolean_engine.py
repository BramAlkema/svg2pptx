"""
Path Boolean Engine Interface

Provides a pluggable interface for performing boolean operations on SVG paths.
Supports multiple backends (Skia PathOps, PyClipper) with consistent API.

This interface allows for:
- Intersection (clipping): subject ∩ clips
- Union: path1 ∪ path2 ∪ ... ∪ pathN
- Difference: subject - clips

All operations respect SVG fill rules (nonzero/evenodd) and maintain vector precision.
"""

from __future__ import annotations
from typing import List, Tuple, Literal, Protocol, Optional

# Type definitions
FillRule = Literal["nonzero", "evenodd"]
PathSpec = Tuple[str, FillRule]  # (svg_d_string, fill_rule)


class PathBooleanEngine(Protocol):
    """
    Protocol for path boolean operation engines.

    Implementations must handle SVG path d-strings with proper fill rule semantics.
    All methods should preserve vector precision when possible.
    """

    def union(self, paths: List[PathSpec]) -> str:
        """
        Compute union of multiple paths.

        Args:
            paths: List of (d_string, fill_rule) tuples

        Returns:
            SVG path d-string representing the union

        Raises:
            ValueError: If paths are malformed or operation fails
        """
        ...

    def intersect(self, subject: PathSpec, clips: List[PathSpec]) -> str:
        """
        Compute intersection of subject with clip paths.

        This is the primary operation for clipPath resolution:
        result = subject ∩ clip1 ∩ clip2 ∩ ... ∩ clipN

        Args:
            subject: (d_string, fill_rule) for the element being clipped
            clips: List of (d_string, fill_rule) for clip paths

        Returns:
            SVG path d-string representing the intersection
            Empty string if no intersection exists

        Raises:
            ValueError: If paths are malformed or operation fails
        """
        ...

    def difference(self, subject: PathSpec, clips: List[PathSpec]) -> str:
        """
        Compute difference of subject minus clip paths.

        Args:
            subject: (d_string, fill_rule) for the base path
            clips: List of (d_string, fill_rule) to subtract

        Returns:
            SVG path d-string representing subject - clips

        Raises:
            ValueError: If paths are malformed or operation fails
        """
        ...


def normalize_fill_rule(rule: Optional[str]) -> FillRule:
    """
    Normalize fill rule string to canonical form.

    SVG supports 'nonzero' and 'evenodd' fill rules. This function
    normalizes various inputs to the canonical literals.

    Args:
        rule: Fill rule string from SVG attribute (fill-rule or clip-rule)

    Returns:
        Canonical FillRule ("nonzero" or "evenodd")

    Examples:
        >>> normalize_fill_rule("evenodd")
        "evenodd"
        >>> normalize_fill_rule("nonzero")
        "nonzero"
        >>> normalize_fill_rule(None)
        "nonzero"
        >>> normalize_fill_rule("")
        "nonzero"
    """
    if not rule:
        return "nonzero"

    rule = rule.strip().lower()
    return "evenodd" if rule == "evenodd" else "nonzero"


def validate_path_spec(path_spec: PathSpec) -> bool:
    """
    Validate that a PathSpec tuple is well-formed.

    Args:
        path_spec: (d_string, fill_rule) tuple to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(path_spec, tuple) or len(path_spec) != 2:
        return False

    d_string, fill_rule = path_spec

    # Basic d-string validation
    if not isinstance(d_string, str) or not d_string.strip():
        return False

    # Fill rule validation
    if fill_rule not in ("nonzero", "evenodd"):
        return False

    return True


def create_path_spec(d_string: str, fill_rule: Optional[str] = None) -> PathSpec:
    """
    Create a validated PathSpec tuple.

    Args:
        d_string: SVG path d attribute value
        fill_rule: Optional fill rule (defaults to "nonzero")

    Returns:
        Valid PathSpec tuple

    Raises:
        ValueError: If d_string is invalid
    """
    if not isinstance(d_string, str) or not d_string.strip():
        raise ValueError(f"Invalid d_string: {d_string!r}")

    normalized_rule = normalize_fill_rule(fill_rule)
    path_spec = (d_string.strip(), normalized_rule)

    if not validate_path_spec(path_spec):
        raise ValueError(f"Created invalid PathSpec: {path_spec}")

    return path_spec
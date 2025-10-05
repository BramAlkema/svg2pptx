#!/usr/bin/env python3
"""
TextPath IR Structures for Clean Slate

Immutable data structures for text following path curves.
Supports SVG textPath elements with character positioning along curves.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union
from enum import Enum

from .geometry import Point, Rect
from .text import EnhancedRun, Run, TextAnchor


class TextPathMethod(Enum):
    """Text path layout methods."""
    ALIGN = "align"      # Characters aligned to path
    STRETCH = "stretch"  # Text stretched along path length


class TextPathSpacing(Enum):
    """Text path spacing methods."""
    EXACT = "exact"      # Exact character positioning
    AUTO = "auto"        # Automatic spacing adjustments


class TextPathSide(Enum):
    """Side of path for text placement."""
    LEFT = "left"        # Text on left side of path
    RIGHT = "right"      # Text on right side of path


@dataclass(frozen=True)
class PathPoint:
    """Point along a path with tangent information for text positioning."""
    x: float                           # X coordinate
    y: float                           # Y coordinate
    tangent_angle: float               # Tangent angle in radians
    distance_along_path: float         # Distance from path start
    curvature: float = 0.0            # Path curvature at this point
    normal_angle: float = 0.0         # Normal angle for text orientation

    @property
    def position(self) -> Point:
        """Get position as Point."""
        return Point(x=self.x, y=self.y)

    @property
    def tangent_degrees(self) -> float:
        """Get tangent angle in degrees."""
        import math
        return math.degrees(self.tangent_angle)

    @property
    def normal_degrees(self) -> float:
        """Get normal angle in degrees."""
        import math
        return math.degrees(self.normal_angle)


@dataclass(frozen=True)
class CharacterPlacement:
    """Placement information for a single character along a path."""
    character: str                     # Character to place
    position: PathPoint               # Position along path
    run_index: int                    # Index of run this character belongs to
    char_index: int                   # Index within the run
    advance_width: float              # Character advance width
    baseline_offset: float = 0.0     # Baseline adjustment
    rotation: float = 0.0            # Additional rotation in degrees

    @property
    def effective_rotation(self) -> float:
        """Get effective rotation (tangent + additional)."""
        return self.position.tangent_degrees + self.rotation


@dataclass(frozen=True)
class TextPathFrame:
    """
    Text following a path curve.

    Represents SVG textPath elements with characters positioned
    along a path curve. Includes all information needed for
    character-by-character positioning.
    """
    runs: List[Union[Run, EnhancedRun]]       # Text runs to place on path
    path_reference: str                        # Reference to path element ID
    start_offset: float = 0.0                 # Start offset along path (0-1 or length)
    method: TextPathMethod = TextPathMethod.ALIGN
    spacing: TextPathSpacing = TextPathSpacing.AUTO
    side: TextPathSide = TextPathSide.LEFT

    # Optional pre-calculated positioning
    character_placements: Optional[List[CharacterPlacement]] = None
    path_points: Optional[List[PathPoint]] = None
    total_path_length: Optional[float] = None

    # Layout hints
    auto_rotate: bool = True                   # Rotate characters with path
    baseline_offset: float = 0.0              # Global baseline offset
    letter_spacing: float = 0.0               # Additional letter spacing

    # Rendering options
    render_method: str = "positioned_chars"   # positioned_chars|approximation|emf
    fallback_anchor: TextAnchor = TextAnchor.START

    def __post_init__(self):
        if not self.runs:
            raise ValueError("TextPathFrame must have at least one run")
        if not self.path_reference.strip():
            raise ValueError("Path reference cannot be empty")
        if not (0.0 <= self.start_offset <= 1.0) and self.start_offset < 0:
            raise ValueError("Start offset must be non-negative")

    @property
    def text_content(self) -> str:
        """Get combined text content from all runs."""
        return ''.join(run.text for run in self.runs)

    @property
    def character_count(self) -> int:
        """Get total number of characters."""
        return len(self.text_content)

    @property
    def run_count(self) -> int:
        """Get number of text runs."""
        return len(self.runs)

    @property
    def is_positioned(self) -> bool:
        """Check if character positioning has been calculated."""
        return (self.character_placements is not None and
                len(self.character_placements) == self.character_count)

    @property
    def path_coverage(self) -> float:
        """Get estimated path coverage (0-1) if positioning is available."""
        if not self.is_positioned or not self.total_path_length:
            return 0.0

        if self.character_placements:
            last_placement = self.character_placements[-1]
            return last_placement.position.distance_along_path / self.total_path_length

        return 0.0

    @property
    def complexity_score(self) -> int:
        """Complexity score for rendering decisions."""
        score = 0
        score += self.character_count           # More characters = more complex
        score += self.run_count                 # Multiple runs = more complex
        score += 1 if self.auto_rotate else 0  # Rotation adds complexity
        score += 1 if self.spacing == TextPathSpacing.EXACT else 0
        score += 1 if self.method == TextPathMethod.STRETCH else 0
        return score

    @property
    def estimated_bounds(self) -> Optional[Rect]:
        """Get estimated bounding box if positioning is available."""
        if not self.is_positioned:
            return None

        positions = [cp.position for cp in self.character_placements]
        if not positions:
            return None

        min_x = min(pos.x for pos in positions)
        max_x = max(pos.x for pos in positions)
        min_y = min(pos.y for pos in positions)
        max_y = max(pos.y for pos in positions)

        return Rect(
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y
        )

    def get_characters_with_runs(self) -> List[tuple]:
        """
        Get list of (character, run_index, char_index) tuples.

        Returns:
            List of tuples with character information
        """
        characters = []
        for run_idx, run in enumerate(self.runs):
            for char_idx, char in enumerate(run.text):
                characters.append((char, run_idx, char_idx))
        return characters

    def get_run_for_character(self, global_char_index: int) -> Optional[Union[Run, EnhancedRun]]:
        """
        Get the run that contains the character at global index.

        Args:
            global_char_index: Index across all runs

        Returns:
            Run containing the character, or None if index invalid
        """
        if global_char_index < 0:
            return None

        current_index = 0
        for run in self.runs:
            if current_index <= global_char_index < current_index + len(run.text):
                return run
            current_index += len(run.text)

        return None

    def with_positioning(
        self,
        character_placements: List[CharacterPlacement],
        path_points: Optional[List[PathPoint]] = None,
        total_path_length: Optional[float] = None
    ) -> 'TextPathFrame':
        """
        Create new TextPathFrame with positioning information.

        Args:
            character_placements: Character positioning data
            path_points: Optional path point data
            total_path_length: Optional total path length

        Returns:
            New TextPathFrame with positioning
        """
        return TextPathFrame(
            runs=self.runs,
            path_reference=self.path_reference,
            start_offset=self.start_offset,
            method=self.method,
            spacing=self.spacing,
            side=self.side,
            character_placements=character_placements,
            path_points=path_points,
            total_path_length=total_path_length,
            auto_rotate=self.auto_rotate,
            baseline_offset=self.baseline_offset,
            letter_spacing=self.letter_spacing,
            render_method=self.render_method,
            fallback_anchor=self.fallback_anchor
        )


@dataclass(frozen=True)
class TextPathLayout:
    """
    Complete layout result for TextPath processing.

    Contains all information needed to render text along a path,
    including character positioning, path information, and
    rendering metadata.
    """
    text_path_frame: TextPathFrame            # Original TextPath data
    character_placements: List[CharacterPlacement]  # Character positioning
    path_points: List[PathPoint]              # Path point data
    total_path_length: float                  # Total path length
    layout_time_ms: float                     # Time taken for layout

    # Layout metadata
    method_used: str = "exact"                # Method used for positioning
    spacing_adjustments: List[float] = field(default_factory=list)
    overflow_characters: int = 0              # Characters that didn't fit
    layout_quality: float = 1.0              # Quality score (0-1)

    @property
    def positioned_frame(self) -> TextPathFrame:
        """Get TextPathFrame with positioning applied."""
        return self.text_path_frame.with_positioning(
            self.character_placements,
            self.path_points,
            self.total_path_length
        )

    @property
    def rendering_bounds(self) -> Optional[Rect]:
        """Get rendering bounds for the positioned text."""
        return self.positioned_frame.estimated_bounds

    @property
    def has_overflow(self) -> bool:
        """Check if some characters didn't fit on the path."""
        return self.overflow_characters > 0

    @property
    def coverage_percentage(self) -> float:
        """Get path coverage as percentage (0-100)."""
        return self.positioned_frame.path_coverage * 100

    def get_character_at_distance(self, distance: float) -> Optional[CharacterPlacement]:
        """
        Get character placement at specific distance along path.

        Args:
            distance: Distance along path

        Returns:
            CharacterPlacement at that distance, or None
        """
        for placement in self.character_placements:
            if abs(placement.position.distance_along_path - distance) < 0.1:
                return placement
        return None


# Factory functions
def create_text_path_frame(
    runs: List[Union[Run, EnhancedRun]],
    path_reference: str,
    **kwargs
) -> TextPathFrame:
    """
    Create TextPathFrame with validation.

    Args:
        runs: Text runs for the path
        path_reference: Path element reference
        **kwargs: Additional TextPathFrame parameters

    Returns:
        Validated TextPathFrame instance
    """
    return TextPathFrame(runs=runs, path_reference=path_reference, **kwargs)


def create_simple_text_path(
    text: str,
    path_reference: str,
    font_family: str = "Arial",
    font_size_pt: float = 12.0,
    **kwargs
) -> TextPathFrame:
    """
    Create simple TextPathFrame from text string.

    Args:
        text: Text content
        path_reference: Path element reference
        font_family: Font family name
        font_size_pt: Font size in points
        **kwargs: Additional TextPathFrame parameters

    Returns:
        TextPathFrame with single run
    """
    from .text import Run

    run = Run(
        text=text,
        font_family=font_family,
        font_size_pt=font_size_pt
    )

    return TextPathFrame(runs=[run], path_reference=path_reference, **kwargs)
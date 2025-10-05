#!/usr/bin/env python3
"""
Text representation for IR

Canonical text handling with resolved per-run styling.
Implements the documented text fixes for proper alignment and positioning.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# Use shared numpy compatibility
from .geometry import Point, Rect


class TextAnchor(Enum):
    """SVG text-anchor values (raw, no double mapping)"""
    START = "start"
    MIDDLE = "middle"
    END = "end"


@dataclass(frozen=True)
class Run:
    """Single styled text run

    Represents one <tspan> after style inheritance resolution.
    Fixes the critical per-tspan styling issues.
    """
    text: str
    font_family: str
    font_size_pt: float
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    rgb: str = "000000"  # RRGGBB format, default black (not red)

    def __post_init__(self):
        if self.font_size_pt <= 0:
            raise ValueError(f"Font size must be positive, got {self.font_size_pt}")
        if len(self.rgb) != 6:
            raise ValueError(f"RGB must be 6 hex chars, got {self.rgb}")

    @property
    def has_decoration(self) -> bool:
        """Check if run has text decoration"""
        return self.underline or self.strike

    @property
    def weight_class(self) -> int:
        """Font weight as numeric class"""
        return 700 if self.bold else 400


@dataclass(frozen=True)
class EnhancedRun:
    """Enhanced text run with comprehensive font metadata and styling.

    Extends the basic Run concept with:
    - Full font metadata integration
    - Text decorations support
    - Style inheritance tracking
    - Advanced typography properties

    Maintains backward compatibility with Run interface.
    """
    text: str
    font_family: str
    font_size_pt: float
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    rgb: str = "000000"  # RRGGBB format, default black

    # Enhanced properties
    font_metadata: Optional['FontMetadata'] = None  # Forward reference
    text_decorations: list[str] = field(default_factory=list)
    style_inheritance: dict[str, Any] = field(default_factory=dict)

    # Advanced typography
    letter_spacing: float | None = None  # Letter spacing in points
    word_spacing: float | None = None    # Word spacing multiplier
    text_transform: str = "none"            # none|uppercase|lowercase|capitalize

    # Positioning hints (for advanced layout)
    baseline_shift: float = 0.0             # Baseline shift in points
    rotation_angle: float = 0.0             # Text rotation in degrees

    def __post_init__(self):
        if self.font_size_pt <= 0:
            raise ValueError(f"Font size must be positive, got {self.font_size_pt}")
        if len(self.rgb) != 6:
            raise ValueError(f"RGB must be 6 hex chars, got {self.rgb}")

    @property
    def has_decoration(self) -> bool:
        """Check if run has text decoration"""
        return self.underline or self.strike or bool(self.text_decorations)

    @property
    def weight_class(self) -> int:
        """Font weight as numeric class"""
        if self.font_metadata:
            return self.font_metadata.weight
        return 700 if self.bold else 400

    @property
    def effective_font_family(self) -> str:
        """Get effective font family (with metadata if available)"""
        if self.font_metadata:
            return self.font_metadata.family
        return self.font_family

    @property
    def effective_font_size(self) -> float:
        """Get effective font size (with metadata if available)"""
        if self.font_metadata:
            return self.font_metadata.size_pt
        return self.font_size_pt

    @property
    def is_transformed(self) -> bool:
        """Check if text has transformations applied"""
        return (self.baseline_shift != 0.0 or
                self.rotation_angle != 0.0 or
                self.text_transform != "none")

    def to_basic_run(self) -> 'Run':
        """Convert to basic Run for backward compatibility"""
        return Run(
            text=self.text,
            font_family=self.font_family,
            font_size_pt=self.font_size_pt,
            bold=self.bold,
            italic=self.italic,
            underline=self.underline,
            strike=self.strike,
            rgb=self.rgb,
        )

    @classmethod
    def from_basic_run(cls, run: 'Run', **kwargs) -> 'EnhancedRun':
        """Create EnhancedRun from basic Run"""
        return cls(
            text=run.text,
            font_family=run.font_family,
            font_size_pt=run.font_size_pt,
            bold=run.bold,
            italic=run.italic,
            underline=run.underline,
            strike=run.strike,
            rgb=run.rgb,
            **kwargs,
        )


@dataclass(frozen=True)
class TextFrame:
    """Text element with resolved positioning and styling

    Fixes critical text positioning bugs:
    - Uses raw SVG anchor (no double mapping)
    - Coordinates from ConversionContext (not manual viewport math)
    - Conservative baseline handling
    - Per-run styling preserved
    """
    origin: Point                    # Already transformed coordinates (EMU)
    runs: list[Run]                  # Per-tspan runs with inherited styling
    anchor: TextAnchor               # Raw SVG anchor (start|middle|end)
    bbox: Rect                       # Calculated text bounding box
    line_height: float | None = None  # Line height multiplier
    baseline_shift: float = 0.0      # Conservative baseline adjustment

    def __post_init__(self):
        if not self.runs:
            raise ValueError("TextFrame must have at least one run")
        if any(not run.text.strip() for run in self.runs):
            # Allow empty runs for spacing, but warn about all-empty
            pass

    @property
    def text_content(self) -> str:
        """Get combined text content"""
        return ''.join(run.text for run in self.runs)

    @property
    def is_multiline(self) -> bool:
        """Check if text contains line breaks"""
        return '\n' in self.text_content

    @property
    def primary_font_family(self) -> str:
        """Get primary font family (from first run)"""
        return self.runs[0].font_family if self.runs else "Arial"

    @property
    def primary_font_size(self) -> float:
        """Get primary font size (from first run)"""
        return self.runs[0].font_size_pt if self.runs else 12.0

    @property
    def complexity_score(self) -> int:
        """Complexity score for policy decisions"""
        score = 0
        score += len(self.runs)  # Multiple runs increase complexity
        if self.is_multiline:
            score += 2
        if any(run.has_decoration for run in self.runs):
            score += 1
        if len(set(run.font_family for run in self.runs)) > 1:
            score += 2  # Mixed fonts
        return score

    def lines(self) -> list[list[Run]]:
        """Split runs into lines based on newline characters

        Returns list of run lists, one per line.
        Handles positioned tspans that create line breaks.
        """
        if not self.is_multiline:
            return [self.runs]

        lines = []
        current_line = []

        for run in self.runs:
            if '\n' in run.text:
                # Split this run on newlines
                parts = run.text.split('\n')
                for i, part in enumerate(parts):
                    if part:  # Non-empty part
                        current_line.append(Run(
                            text=part,
                            font_family=run.font_family,
                            font_size_pt=run.font_size_pt,
                            bold=run.bold,
                            italic=run.italic,
                            underline=run.underline,
                            strike=run.strike,
                            rgb=run.rgb,
                        ))
                    if i < len(parts) - 1:  # Not the last part
                        if current_line:
                            lines.append(current_line)
                        current_line = []
            else:
                current_line.append(run)

        if current_line:
            lines.append(current_line)

        return lines if lines else [[]]  # Always return at least one line


@dataclass(frozen=True)
class TextLine:
    """Single line of text with multiple runs and line-specific properties

    Represents one logical line that may contain multiple styled runs.
    Used for enhanced multi-line text processing with per-line properties.
    """
    runs: list[Run]
    anchor: TextAnchor = TextAnchor.START
    line_height: float | None = None
    spacing_before: float = 0.0  # Space before this line (EMU)
    spacing_after: float = 0.0   # Space after this line (EMU)

    def __post_init__(self):
        if not self.runs:
            raise ValueError("TextLine must have at least one run")

    @property
    def text_content(self) -> str:
        """Get combined text content for this line"""
        return ''.join(run.text for run in self.runs)

    @property
    def is_empty(self) -> bool:
        """Check if line contains only whitespace"""
        return not self.text_content.strip()

    @property
    def primary_font_size(self) -> float:
        """Get primary font size (from first run)"""
        return self.runs[0].font_size_pt if self.runs else 12.0

    @property
    def has_mixed_styling(self) -> bool:
        """Check if line has multiple different styles"""
        if len(self.runs) <= 1:
            return False

        first_run = self.runs[0]
        return any(
            run.font_family != first_run.font_family or
            run.font_size_pt != first_run.font_size_pt or
            run.bold != first_run.bold or
            run.italic != first_run.italic or
            run.rgb != first_run.rgb
            for run in self.runs[1:]
        )


@dataclass(frozen=True)
class RichTextFrame:
    """Enhanced text frame supporting structured multi-line text

    Provides explicit line-by-line control for complex text layouts.
    Complements the existing TextFrame with enhanced structure for
    precise multi-line and multi-run text processing.
    """
    lines: list[TextLine]
    position: Point  # Already transformed coordinates (EMU)
    bounds: Rect | None = None
    transform: str | None = None  # SVG transform attribute
    baseline_adjust: bool = True     # Apply baseline corrections

    def __post_init__(self):
        if not self.lines:
            raise ValueError("RichTextFrame must have at least one line")

    @property
    def all_runs(self) -> list[Run]:
        """Get all runs from all lines"""
        return [run for line in self.lines for run in line.runs]

    @property
    def text_content(self) -> str:
        """Get combined text content with line breaks"""
        return '\n'.join(line.text_content for line in self.lines)

    @property
    def line_count(self) -> int:
        """Number of lines in this text frame"""
        return len(self.lines)

    @property
    def run_count(self) -> int:
        """Total number of runs across all lines"""
        return sum(len(line.runs) for line in self.lines)

    @property
    def primary_anchor(self) -> TextAnchor:
        """Primary text anchor (from first line)"""
        return self.lines[0].anchor if self.lines else TextAnchor.START

    @property
    def complexity_score(self) -> int:
        """Enhanced complexity score for policy decisions"""
        score = 0
        score += self.line_count      # Multiple lines increase complexity
        score += self.run_count       # Multiple runs increase complexity

        # Mixed anchors across lines
        anchors = set(line.anchor for line in self.lines)
        if len(anchors) > 1:
            score += 2

        # Mixed styling within lines
        score += sum(1 for line in self.lines if line.has_mixed_styling)

        # Font variations
        fonts = set(run.font_family for run in self.all_runs)
        if len(fonts) > 1:
            score += len(fonts) - 1

        return score

    def to_text_frame(self) -> TextFrame:
        """Convert to standard TextFrame for backward compatibility"""
        all_runs = self.all_runs

        # Combine line breaks back into run text where appropriate
        combined_runs = []
        for i, line in enumerate(self.lines):
            for j, run in enumerate(line.runs):
                # Add line break to last run of each line (except the last line)
                if i < len(self.lines) - 1 and j == len(line.runs) - 1:
                    combined_runs.append(Run(
                        text=run.text + '\n',
                        font_family=run.font_family,
                        font_size_pt=run.font_size_pt,
                        bold=run.bold,
                        italic=run.italic,
                        underline=run.underline,
                        strike=run.strike,
                        rgb=run.rgb,
                    ))
                else:
                    combined_runs.append(run)

        # Use bounds if available, otherwise create minimal bounds
        bbox = self.bounds or Rect(
            x=self.position.x,
            y=self.position.y,
            width=100.0,  # Minimal fallback
            height=20.0 * self.line_count,
        )

        return TextFrame(
            origin=self.position,
            runs=combined_runs,
            anchor=self.primary_anchor,
            bbox=bbox,
        )
#!/usr/bin/env python3
"""
TextPath Processor for Clean Slate Architecture

Modern implementation of text-on-path functionality, refactored from legacy
src/converters/text_path.py with Clean Slate architecture principles.

Key Features:
- Character-by-character positioning along path curves
- Integration with Clean Slate FontSystem and TextLayoutEngine
- Clean separation of concerns with algorithm extraction
- Comprehensive path sampling and text positioning
- PowerPoint-compatible output generation
"""

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..ir.font_metadata import FontMetadata, create_font_metadata
from ..ir.text import EnhancedRun

# Import Clean Slate components
from ..ir.text_path import CharacterPlacement, PathPoint, TextPathFrame, TextPathLayout

logger = logging.getLogger(__name__)


@dataclass
class TextPathProcessingResult:
    """Result of text path processing"""
    layout: TextPathLayout
    processing_method: str  # "positioned_chars", "approximation", "emf"
    character_count: int
    path_coverage: float
    processing_time_ms: float
    complexity_score: int
    metadata: dict[str, Any]


class TextPathProcessor:
    """
    Modern text-on-path processor using Clean Slate architecture.

    Integrates with FontSystem, TextLayoutEngine, and path processing
    to provide precise text positioning along curved paths.
    """

    def __init__(self, font_system=None, text_layout_engine=None, path_processor=None):
        """
        Initialize TextPath processor with Clean Slate services.

        Args:
            font_system: FontSystem for font analysis
            text_layout_engine: TextLayoutEngine for text measurement
            path_processor: Path processing service for curve sampling
        """
        self.logger = logging.getLogger(__name__)
        self.font_system = font_system
        self.text_layout_engine = text_layout_engine
        self.path_processor = path_processor

        # Initialize fallback services if needed
        if not self.font_system:
            try:
                from .font_system import create_font_system
                self.font_system = create_font_system()
            except ImportError:
                self.logger.warning("FontSystem not available")

        if not self.text_layout_engine:
            try:
                from .text_layout_engine import create_text_layout_engine
                self.text_layout_engine = create_text_layout_engine()
            except ImportError:
                self.logger.warning("TextLayoutEngine not available")

    def process_text_path(self, text_path_frame: TextPathFrame, path_data: str) -> TextPathProcessingResult:
        """
        Process TextPath frame and generate character positioning.

        Args:
            text_path_frame: TextPath IR structure
            path_data: SVG path data string

        Returns:
            TextPathProcessingResult with positioning and metadata
        """
        import time
        start_time = time.perf_counter()

        try:
            # Step 1: Analyze path complexity and length
            path_analysis = self._analyze_path(path_data)

            # Step 2: Sample path points for character positioning
            path_points = self._sample_path_points(path_data, path_analysis)

            # Step 3: Calculate character positioning with font metrics
            character_placements = self._calculate_character_positioning(
                text_path_frame, path_points, path_analysis,
            )

            # Step 4: Create layout result
            layout = TextPathLayout(
                text_path_frame=text_path_frame,
                character_placements=character_placements,
                path_points=path_points,
                total_path_length=path_analysis['total_length'],
                layout_time_ms=(time.perf_counter() - start_time) * 1000,
                method_used="precise_positioning",
                layout_quality=self._calculate_layout_quality(character_placements, path_analysis),
            )

            # Step 5: Determine processing method based on complexity
            processing_method = self._determine_processing_method(
                text_path_frame, path_analysis, character_placements,
            )

            return TextPathProcessingResult(
                layout=layout,
                processing_method=processing_method,
                character_count=len(character_placements),
                path_coverage=layout.coverage_percentage / 100.0,
                processing_time_ms=layout.layout_time_ms,
                complexity_score=text_path_frame.complexity_score,
                metadata={
                    'path_analysis': path_analysis,
                    'font_system_used': self.font_system is not None,
                    'text_layout_used': self.text_layout_engine is not None,
                    'path_processor_used': self.path_processor is not None,
                },
            )

        except Exception as e:
            self.logger.error(f"TextPath processing failed: {e}")
            raise

    def _analyze_path(self, path_data: str) -> dict[str, Any]:
        """Analyze path complexity and characteristics."""
        try:
            # Basic path analysis (can be enhanced with path_processor)
            analysis = {
                'total_length': self._estimate_path_length(path_data),
                'curve_count': path_data.count('C') + path_data.count('c') + path_data.count('Q') + path_data.count('q'),
                'has_curves': 'C' in path_data or 'c' in path_data or 'Q' in path_data or 'q' in path_data,
                'is_closed': 'Z' in path_data or 'z' in path_data,
                'complexity_score': self._calculate_path_complexity(path_data),
            }

            # Use path processor if available for detailed analysis
            if self.path_processor:
                try:
                    enhanced_analysis = self.path_processor.analyze_path(path_data)
                    analysis.update(enhanced_analysis)
                except Exception as e:
                    self.logger.debug(f"Path processor analysis failed: {e}")

            return analysis

        except Exception as e:
            self.logger.warning(f"Path analysis failed: {e}")
            return {
                'total_length': 100.0,  # Fallback estimate
                'curve_count': 0,
                'has_curves': False,
                'is_closed': False,
                'complexity_score': 1,
            }

    def _sample_path_points(self, path_data: str, path_analysis: dict[str, Any]) -> list[PathPoint]:
        """Sample points along path for character positioning."""
        try:
            # Use path processor if available
            if self.path_processor:
                try:
                    return self.path_processor.sample_path_points(
                        path_data,
                        num_samples=min(200, max(50, int(path_analysis['total_length'] / 2))),
                    )
                except Exception as e:
                    self.logger.debug(f"Path processor sampling failed: {e}")

            # Fallback to basic path sampling
            return self._basic_path_sampling(path_data, path_analysis)

        except Exception as e:
            self.logger.warning(f"Path sampling failed: {e}")
            # Return minimal fallback path
            return [
                PathPoint(x=0.0, y=0.0, tangent_angle=0.0, distance_along_path=0.0),
                PathPoint(x=100.0, y=0.0, tangent_angle=0.0, distance_along_path=100.0),
            ]

    def _calculate_character_positioning(self, text_path_frame: TextPathFrame,
                                       path_points: list[PathPoint],
                                       path_analysis: dict[str, Any]) -> list[CharacterPlacement]:
        """Calculate precise character positioning along path."""
        character_placements = []
        current_distance = text_path_frame.start_offset

        if path_analysis.get('total_length', 0) > 0:
            if current_distance > 1.0:  # Assume percentage if > 1
                current_distance = (current_distance / 100.0) * path_analysis['total_length']

        try:
            # Process each run
            for run_index, run in enumerate(text_path_frame.runs):
                # Get font metadata for precise measurements
                font_metadata = self._get_font_metadata_for_run(run)

                # Process each character in the run
                for char_index, char in enumerate(run.text):
                    # Get character advance width
                    advance_width = self._get_character_advance(char, font_metadata)

                    # Find position along path
                    path_point = self._find_path_point_at_distance(path_points, current_distance)

                    if path_point:
                        # Create character placement
                        placement = CharacterPlacement(
                            character=char,
                            position=path_point,
                            run_index=run_index,
                            char_index=char_index,
                            advance_width=advance_width,
                            baseline_offset=text_path_frame.baseline_offset,
                            rotation=path_point.tangent_degrees if text_path_frame.auto_rotate else 0.0,
                        )
                        character_placements.append(placement)

                    # Advance position
                    current_distance += advance_width + text_path_frame.letter_spacing

                    # Check if we've exceeded path length
                    if current_distance > path_analysis.get('total_length', float('inf')):
                        break

                if current_distance > path_analysis.get('total_length', float('inf')):
                    break

        except Exception as e:
            self.logger.error(f"Character positioning calculation failed: {e}")

        return character_placements

    def _get_font_metadata_for_run(self, run) -> FontMetadata:
        """Get font metadata for a text run."""
        if isinstance(run, EnhancedRun) and run.font_metadata:
            return run.font_metadata

        # Create font metadata from run properties
        return create_font_metadata(
            run.font_family,
            weight="700" if run.bold else "400",
            style="italic" if run.italic else "normal",
            size_pt=run.font_size_pt,
        )

    def _get_character_advance(self, char: str, font_metadata: FontMetadata) -> float:
        """Get character advance width using available services."""
        try:
            # Use TextLayoutEngine if available
            if self.text_layout_engine:
                measurements = self.text_layout_engine.measure_text_only(char, font_metadata)
                return measurements.width_pt

            # Fallback to estimation
            return self._estimate_character_width(char, font_metadata.size_pt)

        except Exception as e:
            self.logger.debug(f"Character advance calculation failed: {e}")
            return self._estimate_character_width(char, font_metadata.size_pt)

    def _estimate_character_width(self, char: str, font_size: float) -> float:
        """Estimate character width based on character type."""
        if char == ' ':
            return font_size * 0.25
        elif char in 'il1|!':
            return font_size * 0.3
        elif char in 'fijrt':
            return font_size * 0.4
        elif char in 'abcdeghknopqsuvxyz':
            return font_size * 0.6
        elif char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            return font_size * 0.8
        elif char in 'mw':
            return font_size * 1.0
        elif char in 'MW':
            return font_size * 1.2
        else:
            return font_size * 0.6

    def _basic_path_sampling(self, path_data: str, path_analysis: dict[str, Any]) -> list[PathPoint]:
        """Basic fallback path sampling when path processor unavailable."""
        # Simple line approximation for basic functionality
        num_samples = min(100, max(20, int(path_analysis.get('total_length', 100) / 5)))
        points = []

        # For this basic implementation, create a horizontal line
        # In a full implementation, this would parse and sample the actual path
        total_length = path_analysis.get('total_length', 100.0)

        for i in range(num_samples):
            t = i / (num_samples - 1) if num_samples > 1 else 0
            distance = t * total_length

            point = PathPoint(
                x=distance,
                y=0.0,  # Horizontal line approximation
                tangent_angle=0.0,  # Horizontal tangent
                distance_along_path=distance,
            )
            points.append(point)

        return points

    def _find_path_point_at_distance(self, path_points: list[PathPoint], target_distance: float) -> PathPoint | None:
        """Find path point at specific distance along path."""
        if not path_points:
            return None

        # Find closest point by distance
        closest_point = None
        min_distance_diff = float('inf')

        for point in path_points:
            distance_diff = abs(point.distance_along_path - target_distance)
            if distance_diff < min_distance_diff:
                min_distance_diff = distance_diff
                closest_point = point

        return closest_point

    def _estimate_path_length(self, path_data: str) -> float:
        """Estimate total path length."""
        # Very basic estimation - would be enhanced with proper path parsing
        import re

        # Count approximate path segments
        numbers = re.findall(r'-?\d+\.?\d*', path_data)
        if len(numbers) >= 4:
            # Rough approximation based on coordinate ranges
            coords = [float(n) for n in numbers[:20]]  # First 20 numbers
            if coords:
                x_range = max(coords[::2]) - min(coords[::2]) if len(coords) >= 2 else 100
                y_range = max(coords[1::2]) - min(coords[1::2]) if len(coords) >= 2 else 100
                return math.sqrt(x_range**2 + y_range**2)

        return 100.0  # Default fallback

    def _calculate_path_complexity(self, path_data: str) -> int:
        """Calculate path complexity score."""
        score = 0
        score += len(path_data) // 50  # Length complexity
        score += path_data.count('C') + path_data.count('c')  # Cubic curves
        score += path_data.count('Q') + path_data.count('q')  # Quadratic curves
        score += path_data.count('A') + path_data.count('a')  # Arcs
        return max(1, min(10, score))

    def _calculate_layout_quality(self, character_placements: list[CharacterPlacement],
                                path_analysis: dict[str, Any]) -> float:
        """Calculate layout quality score (0-1)."""
        if not character_placements:
            return 0.0

        # Base quality on character coverage and spacing consistency
        quality = 1.0

        # Reduce quality for very sparse placement
        if len(character_placements) < 3:
            quality *= 0.7

        # Reduce quality for high complexity paths
        complexity = path_analysis.get('complexity_score', 1)
        if complexity > 5:
            quality *= 0.8

        return max(0.0, min(1.0, quality))

    def _determine_processing_method(self, text_path_frame: TextPathFrame,
                                   path_analysis: dict[str, Any],
                                   character_placements: list[CharacterPlacement]) -> str:
        """Determine optimal processing method based on complexity."""

        # Use positioned characters for simple cases
        if (len(character_placements) <= 50 and
            path_analysis.get('complexity_score', 1) <= 5 and
            text_path_frame.complexity_score <= 10):
            return "positioned_chars"

        # Use approximation for medium complexity
        elif (len(character_placements) <= 100 and
              path_analysis.get('complexity_score', 1) <= 7):
            return "approximation"

        # Use EMF for complex cases
        else:
            return "emf"

    def get_processing_statistics(self) -> dict[str, Any]:
        """Get processing statistics and capabilities."""
        return {
            'services_available': {
                'font_system': self.font_system is not None,
                'text_layout_engine': self.text_layout_engine is not None,
                'path_processor': self.path_processor is not None,
            },
            'capabilities': {
                'precise_font_measurement': self.text_layout_engine is not None,
                'font_strategy_analysis': self.font_system is not None,
                'advanced_path_processing': self.path_processor is not None,
                'basic_text_path_support': True,
            },
        }


def create_text_path_processor(font_system=None, text_layout_engine=None, path_processor=None) -> TextPathProcessor:
    """
    Create TextPath processor with services.

    Args:
        font_system: FontSystem service (optional)
        text_layout_engine: TextLayoutEngine service (optional)
        path_processor: Path processing service (optional)

    Returns:
        Configured TextPathProcessor instance
    """
    return TextPathProcessor(font_system, text_layout_engine, path_processor)
#!/usr/bin/env python3
"""
CoordinateTransformer utility service for SVG2PPTX.

This module provides centralized coordinate parsing and transformation functionality,
eliminating duplicate coordinate processing implementations across the codebase.
"""

import re
import numpy as np
from typing import List, Tuple, Union, Optional, Any
from dataclasses import dataclass
# Removed circular import - CoordinateTransformer is now a standalone service


@dataclass
class CoordinateParsingResult:
    """Result of coordinate parsing operation."""
    coordinates: List[Tuple[float, float]]
    raw_text: str
    parsing_errors: List[str]


@dataclass
class ViewBoxData:
    """Parsed ViewBox data structure."""
    min_x: float
    min_y: float
    width: float
    height: float


class CoordinateTransformer:
    """
    Centralized coordinate parsing and transformation service.

    Provides unified coordinate processing functionality to replace duplicate
    implementations across converters, preprocessing, and path processing.
    """

    def __init__(self):
        """Initialize CoordinateTransformer with optimization settings."""
        # Cache frequently used regex patterns
        self._coordinate_pattern = re.compile(r'[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?')
        self._viewbox_pattern = re.compile(r'^\s*([+-]?(?:\d*\.)?\d+)\s+([+-]?(?:\d*\.)?\d+)\s+([+-]?(?:\d*\.)?\d+)\s+([+-]?(?:\d*\.)?\d+)\s*$')
        self._points_separator_pattern = re.compile(r'[,\s]+')

    def parse_coordinate_string(self, coord_string: str) -> CoordinateParsingResult:
        """
        Parse coordinate string into list of (x, y) tuples.

        Args:
            coord_string: Coordinate string (e.g., "10,20 30,40" or "10 20 30 40")

        Returns:
            CoordinateParsingResult with parsed coordinates and metadata
        """
        if not coord_string or not coord_string.strip():
            return CoordinateParsingResult(
                coordinates=[],
                raw_text=coord_string,
                parsing_errors=[]
            )

        coordinates = []
        errors = []

        try:
            # Extract all numbers from the string
            numbers = self._coordinate_pattern.findall(coord_string.strip())

            # Convert to floats
            float_numbers = []
            for num_str in numbers:
                try:
                    float_numbers.append(float(num_str))
                except ValueError as e:
                    errors.append(f"Invalid number '{num_str}': {str(e)}")

            # Group into coordinate pairs
            if len(float_numbers) % 2 != 0:
                errors.append(f"Odd number of coordinates: {len(float_numbers)}")
                # Drop the last coordinate to make pairs
                float_numbers = float_numbers[:-1]

            # Create coordinate pairs
            for i in range(0, len(float_numbers), 2):
                if i + 1 < len(float_numbers):
                    coordinates.append((float_numbers[i], float_numbers[i + 1]))

        except Exception as e:
            errors.append(f"Coordinate parsing failed: {str(e)}")

        return CoordinateParsingResult(
            coordinates=coordinates,
            raw_text=coord_string,
            parsing_errors=errors
        )

    def parse_points_string(self, points_string: str) -> List[Tuple[float, float]]:
        """
        Parse SVG points attribute string.

        Args:
            points_string: Points string (e.g., "10,20 30,40 50,60")

        Returns:
            List of (x, y) coordinate tuples
        """
        result = self.parse_coordinate_string(points_string)
        return result.coordinates

    def parse_viewbox_string(self, viewbox_string: str) -> Optional[ViewBoxData]:
        """
        Parse SVG viewBox attribute string.

        Args:
            viewbox_string: ViewBox string (e.g., "0 0 100 200")

        Returns:
            ViewBoxData or None if parsing fails
        """
        if not viewbox_string or not viewbox_string.strip():
            return None

        # Use specialized regex for viewBox (4 space-separated numbers)
        match = self._viewbox_pattern.match(viewbox_string.strip())
        if match:
            try:
                min_x = float(match.group(1))
                min_y = float(match.group(2))
                width = float(match.group(3))
                height = float(match.group(4))

                return ViewBoxData(
                    min_x=min_x,
                    min_y=min_y,
                    width=width,
                    height=height
                )
            except ValueError:
                return None

        # Fallback to general coordinate parsing
        result = self.parse_coordinate_string(viewbox_string)
        if len(result.coordinates) == 2:
            # Interpret as two points: (min_x, min_y) and (width, height)
            (min_x, min_y), (width, height) = result.coordinates
            return ViewBoxData(min_x=min_x, min_y=min_y, width=width, height=height)

        return None

    def transform_coordinates_with_precision(self,
                                           coordinates: List[Tuple[float, float]],
                                           precision: int = 3) -> List[Tuple[float, float]]:
        """
        Transform coordinates with specified precision.

        Args:
            coordinates: List of (x, y) coordinate tuples
            precision: Decimal places for precision

        Returns:
            List of precision-adjusted coordinate tuples
        """
        if not coordinates:
            return []

        transformed = []
        for x, y in coordinates:
            # Round to specified precision
            rounded_x = round(x, precision)
            rounded_y = round(y, precision)

            # Convert to integer if they're whole numbers
            if rounded_x == int(rounded_x):
                rounded_x = int(rounded_x)
            if rounded_y == int(rounded_y):
                rounded_y = int(rounded_y)

            transformed.append((rounded_x, rounded_y))

        return transformed

    def coordinates_to_string(self, coordinates: List[Tuple[float, float]],
                            separator: str = " ") -> str:
        """
        Convert coordinate list back to string format.

        Args:
            coordinates: List of (x, y) coordinate tuples
            separator: Separator between coordinate pairs

        Returns:
            Formatted coordinate string
        """
        if not coordinates:
            return ""

        coord_strings = []
        for x, y in coordinates:
            # Format numbers cleanly (avoid .0 for integers)
            x_str = str(int(x)) if x == int(x) else str(x)
            y_str = str(int(y)) if y == int(y) else str(y)
            coord_strings.append(f"{x_str},{y_str}")

        return separator.join(coord_strings)

    def extract_coordinate_pairs_from_path(self, path_data: str) -> List[Tuple[float, float]]:
        """
        Extract coordinate pairs from SVG path data.

        Args:
            path_data: SVG path data string

        Returns:
            List of all coordinate pairs found in path
        """
        coordinates = []

        # Remove path commands and extract only numbers
        # This is a simplified extraction - a full path parser would handle each command type
        numbers = self._coordinate_pattern.findall(path_data)

        # Convert to floats and group into pairs
        try:
            float_numbers = [float(num) for num in numbers]
            for i in range(0, len(float_numbers) - 1, 2):
                if i + 1 < len(float_numbers):
                    coordinates.append((float_numbers[i], float_numbers[i + 1]))
        except ValueError:
            # Return empty list if parsing fails
            pass

        return coordinates

    def calculate_bounding_box(self, coordinates: List[Tuple[float, float]]) -> Optional[ViewBoxData]:
        """
        Calculate bounding box for a set of coordinates.

        Args:
            coordinates: List of (x, y) coordinate tuples

        Returns:
            ViewBoxData representing the bounding box or None if no coordinates
        """
        if not coordinates:
            return None

        # Extract x and y coordinates
        x_coords = [coord[0] for coord in coordinates]
        y_coords = [coord[1] for coord in coordinates]

        # Find min/max
        min_x = min(x_coords)
        max_x = max(x_coords)
        min_y = min(y_coords)
        max_y = max(y_coords)

        # Calculate width and height
        width = max_x - min_x
        height = max_y - min_y

        return ViewBoxData(
            min_x=min_x,
            min_y=min_y,
            width=width,
            height=height
        )

    def normalize_coordinates_to_viewbox(self,
                                       coordinates: List[Tuple[float, float]],
                                       viewbox: ViewBoxData,
                                       target_width: float = 100.0,
                                       target_height: float = 100.0) -> List[Tuple[float, float]]:
        """
        Normalize coordinates to fit within a target viewbox.

        Args:
            coordinates: List of (x, y) coordinate tuples
            viewbox: Source ViewBox data
            target_width: Target width for normalization
            target_height: Target height for normalization

        Returns:
            List of normalized coordinate tuples
        """
        if not coordinates or viewbox.width == 0 or viewbox.height == 0:
            return coordinates

        normalized = []
        for x, y in coordinates:
            # Normalize to 0-1 range within source viewbox
            norm_x = (x - viewbox.min_x) / viewbox.width
            norm_y = (y - viewbox.min_y) / viewbox.height

            # Scale to target dimensions
            new_x = norm_x * target_width
            new_y = norm_y * target_height

            normalized.append((new_x, new_y))

        return normalized

    def validate_coordinates(self, coordinates: List[Tuple[float, float]]) -> List[str]:
        """
        Validate coordinate list and return list of issues.

        Args:
            coordinates: List of (x, y) coordinate tuples

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        if not coordinates:
            return issues

        for i, (x, y) in enumerate(coordinates):
            # Check for NaN or infinite values
            if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
                issues.append(f"Coordinate {i}: non-numeric values ({x}, {y})")
                continue

            if np.isnan(x) or np.isnan(y):
                issues.append(f"Coordinate {i}: NaN values ({x}, {y})")
            elif np.isinf(x) or np.isinf(y):
                issues.append(f"Coordinate {i}: infinite values ({x}, {y})")

        return issues

    def transform_coordinates(self, coordinates: List[Tuple[float, float]],
                            transform_matrix: Any) -> List[Tuple[float, float]]:
        """
        Transform coordinates using matrix - adapter compatibility alias.

        Args:
            coordinates: List of coordinate tuples
            transform_matrix: Transformation matrix

        Returns:
            List of transformed coordinate tuples
        """
        return self.transform_coordinates_with_precision(coordinates, transform_matrix)


# Global transformer instance for convenience
_transformer_instance = None

def get_coordinate_transformer():
    """Get or create global CoordinateTransformer instance with ConversionServices awareness."""
    global _transformer_instance
    if _transformer_instance is None:
        # Service-aware fallback: try ConversionServices first
        try:
            from ..services.conversion_services import ConversionServices
            services = ConversionServices.get_default_instance()
            _transformer_instance = services.coordinate_transformer
        except (ImportError, RuntimeError, AttributeError):
            # Final fallback to direct instantiation
            _transformer_instance = CoordinateTransformer()
    return _transformer_instance


def parse_coordinate_string(coord_string: str) -> List[Tuple[float, float]]:
    """Convenience function for simple coordinate parsing."""
    result = get_coordinate_transformer().parse_coordinate_string(coord_string)
    return result.coordinates


def parse_viewbox_string(viewbox_string: str) -> Optional[ViewBoxData]:
    """Convenience function for viewBox parsing."""
    return get_coordinate_transformer().parse_viewbox_string(viewbox_string)
#!/usr/bin/env python3
"""
Simple Transform Parser for SVG transform attribute parsing.

Provides basic SVG transform parsing functionality that returns Matrix objects.
This is a minimal implementation focused on the core functionality needed by converters.
"""

import re
from typing import Optional
from .core import Matrix


class TransformParser:
    """Simple parser for SVG transform attributes."""

    def __init__(self):
        """Initialize the transform parser."""
        pass

    def parse_to_matrix(self, transform_str: str, viewport_context=None) -> Optional[Matrix]:
        """
        Parse SVG transform string to Matrix object.

        Args:
            transform_str: SVG transform string (e.g., "translate(10,20) rotate(45)")
            viewport_context: Ignored for now (for compatibility)

        Returns:
            Matrix object or None if parsing fails
        """
        if not transform_str or not transform_str.strip():
            return None

        try:
            return self._parse_transform_string(transform_str.strip())
        except Exception:
            return None

    def _parse_transform_string(self, transform_str: str) -> Matrix:
        """Parse a complete transform string into a Matrix."""
        # Start with identity matrix
        result = Matrix.identity()

        # Find all transform functions: funcname(args)
        pattern = r'(\w+)\s*\(\s*([^)]*)\s*\)'
        matches = re.findall(pattern, transform_str)

        for func_name, args_str in matches:
            # Parse arguments (comma or space separated numbers)
            args = self._parse_args(args_str)

            # Apply transform based on function name
            transform_matrix = self._create_transform(func_name, args)
            if transform_matrix:
                result = result.multiply(transform_matrix)

        return result

    def _parse_args(self, args_str: str) -> list:
        """Parse comma/space separated numeric arguments."""
        if not args_str.strip():
            return []

        # Replace commas with spaces and split
        args_str = re.sub(r'[,\s]+', ' ', args_str.strip())
        args = []

        for arg in args_str.split():
            try:
                args.append(float(arg))
            except ValueError:
                continue

        return args

    def _create_transform(self, func_name: str, args: list) -> Optional[Matrix]:
        """Create a Matrix for a specific transform function."""
        func_name = func_name.lower()

        if func_name == 'translate':
            if len(args) >= 1:
                tx = args[0]
                ty = args[1] if len(args) > 1 else 0
                return Matrix.translate(tx, ty)

        elif func_name == 'scale':
            if len(args) >= 1:
                sx = args[0]
                sy = args[1] if len(args) > 1 else sx
                return Matrix.scale(sx, sy)

        elif func_name == 'rotate':
            if len(args) >= 1:
                angle = args[0]
                if len(args) >= 3:
                    # Rotate around point: rotate(angle, cx, cy)
                    cx, cy = args[1], args[2]
                    # Translate to origin, rotate, translate back
                    t1 = Matrix.translate(-cx, -cy)
                    r = Matrix.rotate(angle)
                    t2 = Matrix.translate(cx, cy)
                    return t2.multiply(r).multiply(t1)
                else:
                    return Matrix.rotate(angle)

        elif func_name == 'skewx':
            if len(args) >= 1:
                return Matrix.skew_x(args[0])

        elif func_name == 'skewy':
            if len(args) >= 1:
                return Matrix.skew_y(args[0])

        elif func_name == 'matrix':
            if len(args) >= 6:
                return Matrix(args[0], args[1], args[2], args[3], args[4], args[5])

        return None


# Alias for backward compatibility
TransformEngine = TransformParser
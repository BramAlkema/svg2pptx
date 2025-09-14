#!/usr/bin/env python3
"""
Simple Unit Tests for Transforms Module
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.transforms import TransformParser, Matrix, parse_transform

class TestTransformParser:
    """Simple test cases for TransformParser class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.parser = TransformParser()

    def test_initialization(self):
        """Test TransformParser initialization."""
        parser = TransformParser()
        assert parser is not None

    def test_parse_basic_transform(self):
        """Test parsing basic transform."""
        result = self.parser.parse("translate(10, 20)")
        assert result is not None

    def test_parse_empty_transform(self):
        """Test parsing empty transform."""
        result = self.parser.parse("")
        assert result is not None


class TestMatrix:
    """Simple test cases for Matrix class."""

    def test_matrix_creation(self):
        """Test Matrix creation."""
        matrix = Matrix()
        assert matrix is not None

    def test_matrix_with_params(self):
        """Test Matrix creation with parameters."""
        matrix = Matrix(1, 0, 0, 1, 10, 20)
        assert matrix is not None
        assert matrix.e == 10
        assert matrix.f == 20


class TestUtilityFunctions:
    """Test utility functions."""

    def test_parse_transform_function(self):
        """Test parse_transform utility function."""
        result = parse_transform("translate(10, 20)")
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
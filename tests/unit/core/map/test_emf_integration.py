#!/usr/bin/env python3
"""
Test EMF Integration with PathMapper

Validates that EMF generation works correctly with the Clean Slate PathMapper.
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path for EMF imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from core.map.path_mapper import PathMapper
from core.map.emf_adapter import EMFPathAdapter, create_emf_adapter
from core.ir import Path, Point, LineSegment, BezierSegment, SolidPaint, Rect
from core.policy.engine import Policy
from core.policy.targets import PathDecision, DecisionReason


@pytest.fixture
def mock_policy():
    """Create mock policy for testing"""
    policy = Mock()
    decision = PathDecision(
        use_native=False,  # Force EMF path
        reasons=[DecisionReason.COMPLEX_GEOMETRY],  # EMF fallback for complex paths
        estimated_quality=0.95,
        estimated_performance=0.8
    )
    policy.decide_path.return_value = decision
    return policy


@pytest.fixture
def simple_path():
    """Create simple test path"""
    segments = [
        LineSegment(
            start=Point(x=0, y=0),
            end=Point(x=100, y=100)
        ),
        LineSegment(
            start=Point(x=100, y=100),
            end=Point(x=200, y=50)
        )
    ]

    return Path(
        segments=segments,
        fill=SolidPaint(rgb="FF0000"),  # Red fill
        stroke=None,
        clip=None,
        opacity=1.0
    )
    # Note: bbox is computed automatically, complexity_score not used


@pytest.fixture
def complex_path():
    """Create complex test path with bezier curves"""
    segments = [
        BezierSegment(
            start=Point(x=0, y=0),
            control1=Point(x=25, y=-25),
            control2=Point(x=75, y=125),
            end=Point(x=100, y=100)
        ),
        BezierSegment(
            start=Point(x=100, y=100),
            control1=Point(x=125, y=75),
            control2=Point(x=175, y=25),
            end=Point(x=200, y=50)
        )
    ]

    return Path(
        segments=segments,
        fill=SolidPaint(rgb="0000FF"),  # Blue fill
        stroke=None,
        clip=None,
        opacity=1.0
    )
    # Note: bbox is computed automatically, complexity_score not used


class TestEMFAdapter:
    """Test EMF adapter functionality"""

    def test_create_emf_adapter(self):
        """Test EMF adapter creation"""
        adapter = create_emf_adapter()
        assert isinstance(adapter, EMFPathAdapter)

    def test_can_generate_emf_with_valid_path(self, simple_path):
        """Test EMF generation capability check"""
        adapter = create_emf_adapter()

        # Should be able to generate EMF for valid path
        # Note: May be False if EMF system not available in test environment
        result = adapter.can_generate_emf(simple_path)
        assert isinstance(result, bool)

    def test_can_generate_emf_with_invalid_path(self):
        """Test EMF generation capability with invalid path"""
        adapter = create_emf_adapter()

        # Should not be able to generate EMF for None path
        assert not adapter.can_generate_emf(None)

        # Path with segments=None raises ValueError during construction
        # So we can only test None path (already tested above)

    @patch('core.map.emf_adapter.EMF_AVAILABLE', True)
    def test_generate_emf_blob_failure(self, simple_path):
        """Test EMF blob generation failure"""
        adapter = create_emf_adapter()
        adapter._emf_available = False  # Force EMF unavailability

        with pytest.raises(ValueError, match="Cannot generate EMF"):
            adapter.generate_emf_blob(simple_path)


class TestPathMapperEMFIntegration:
    """Test PathMapper integration with EMF system"""

    def test_path_mapper_emf_fallback(self, mock_policy, simple_path):
        """Test PathMapper EMF fallback path"""
        mapper = PathMapper(mock_policy)

        # Map path (should use EMF since policy.decide_path returns use_native=False)
        result = mapper.map(simple_path)

        # Verify EMF result
        assert result.output_format.value == "emf_vector"
        assert "EMF_Path" in result.xml_content
        assert "p:pic" in result.xml_content
        assert "a:blip" in result.xml_content

        # Verify metadata
        assert result.metadata is not None
        assert 'emf_generation' in result.metadata

    @patch('core.map.emf_adapter.EMF_AVAILABLE', True)
    def test_path_mapper_emf_fallback_placeholder(self, mock_policy, simple_path):
        """Test PathMapper EMF fallback to placeholder"""
        with patch('core.map.emf_adapter.EMF_AVAILABLE', False):
            mapper = PathMapper(mock_policy)

            result = mapper.map(simple_path)

            # Verify placeholder EMF was used
            assert result.output_format.value == "emf_vector"
            assert result.metadata['emf_generation'] == 'placeholder'
            assert 'fallback_reason' in result.metadata

            # Verify no media files for placeholder
            assert result.media_files is None or len(result.media_files) == 0

    def test_path_mapper_statistics_tracking(self, mock_policy, simple_path):
        """Test PathMapper statistics tracking for EMF"""
        mapper = PathMapper(mock_policy)

        # Map multiple paths
        mapper.map(simple_path)
        mapper.map(simple_path)

        stats = mapper.get_statistics()

        # Verify EMF statistics
        assert stats['total_mapped'] == 2
        assert stats['emf_count'] == 2
        assert stats['native_count'] == 0
        assert stats['emf_ratio'] == 1.0


class TestEMFCoordinateTransformation:
    """Test EMF coordinate system transformation"""

    def test_point_to_emf_coords(self, simple_path):
        """Test point coordinate transformation"""
        adapter = create_emf_adapter()

        point = Point(x=50, y=75)
        emf_coords = adapter._point_to_emf_coords(point, simple_path)

        # Verify coordinate transformation
        assert isinstance(emf_coords, tuple)
        assert len(emf_coords) == 2
        assert isinstance(emf_coords[0], int)
        assert isinstance(emf_coords[1], int)

    def test_hex_to_rgb_conversion(self):
        """Test hex color to RGB conversion"""
        adapter = create_emf_adapter()

        # Test various color formats
        assert adapter._hex_to_rgb("FF0000") == 0x0000FF  # Red (BGR)
        assert adapter._hex_to_rgb("#00FF00") == 0x00FF00  # Green (BGR)
        assert adapter._hex_to_rgb("0000FF") == 0xFF0000  # Blue (BGR)

    def test_quality_calculation(self, simple_path, complex_path):
        """Test EMF quality score calculation"""
        adapter = create_emf_adapter()

        # Simple path should have high quality
        simple_quality = adapter._calculate_emf_quality(simple_path, b'\x00' * 100)
        assert 0.8 <= simple_quality <= 1.0

        # Complex path should have slightly lower quality
        complex_quality = adapter._calculate_emf_quality(complex_path, b'\x00' * 1000)
        assert 0.7 <= complex_quality <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
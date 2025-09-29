#!/usr/bin/env python3
"""
Unit Tests for ClipPath Resolution System

Tests the complete clipPath preprocessing pipeline:
- Boolean engine interfaces and backends
- Path system adapters
- ResolveClipPathsPlugin functionality
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from lxml import etree as ET

from src.preprocessing.geometry import (
    PathBooleanEngine, PathSpec, FillRule, normalize_fill_rule,
    validate_path_spec, create_path_spec, get_available_backends,
    PATHOPS_AVAILABLE, PYCLIPPER_AVAILABLE
)
from src.preprocessing.geometry.path_adapters import BooleanEngineFactory, create_boolean_engine
from src.preprocessing.resolve_clippath_plugin import ResolveClipPathsPlugin
from src.preprocessing.base import PreprocessingContext


class TestBooleanEngineInterface:
    """Test the core boolean engine interface and utilities."""

    def test_normalize_fill_rule(self):
        """Test fill rule normalization."""
        assert normalize_fill_rule(None) == "nonzero"
        assert normalize_fill_rule("") == "nonzero"
        assert normalize_fill_rule("nonzero") == "nonzero"
        assert normalize_fill_rule("evenodd") == "evenodd"
        assert normalize_fill_rule("EVENODD") == "evenodd"
        assert normalize_fill_rule(" evenodd ") == "evenodd"
        assert normalize_fill_rule("invalid") == "nonzero"

    def test_validate_path_spec(self):
        """Test PathSpec validation."""
        # Valid PathSpecs
        assert validate_path_spec(("M 0 0 L 10 10", "nonzero")) == True
        assert validate_path_spec(("M 0 0", "evenodd")) == True

        # Invalid PathSpecs
        assert validate_path_spec(("", "nonzero")) == False
        assert validate_path_spec(("M 0 0", "invalid")) == False
        assert validate_path_spec(("M 0 0",)) == False  # Missing fill rule
        assert validate_path_spec(None) == False
        assert validate_path_spec("not a tuple") == False

    def test_create_path_spec(self):
        """Test PathSpec creation."""
        # Valid creation
        spec = create_path_spec("M 0 0 L 10 10", "evenodd")
        assert spec == ("M 0 0 L 10 10", "evenodd")

        # Default fill rule
        spec = create_path_spec("M 0 0")
        assert spec == ("M 0 0", "nonzero")

        # Invalid d-string
        with pytest.raises(ValueError):
            create_path_spec("")

        with pytest.raises(ValueError):
            create_path_spec(None)

    def test_get_available_backends(self):
        """Test backend availability detection."""
        backends = get_available_backends()
        assert isinstance(backends, list)

        # Should include both backends if dependencies are installed
        if PATHOPS_AVAILABLE:
            assert "pathops" in backends
        if PYCLIPPER_AVAILABLE:
            assert "pyclipper" in backends

    def test_boolean_engine_factory_creation(self):
        """Test boolean engine factory creation."""
        # Create minimal factory
        factory = BooleanEngineFactory(
            path_parser=Mock(),
            path_serializer=Mock(),
            curve_approximator=Mock()
        )
        assert factory is not None

        # Test backend priority
        priority = factory.get_backend_priority_order()
        assert isinstance(priority, list)

        # PathOps should come first if available
        if PATHOPS_AVAILABLE:
            assert "pathops" in priority
            assert priority.index("pathops") == 0 if "pathops" in priority else True

    @pytest.mark.skipif(not (PATHOPS_AVAILABLE or PYCLIPPER_AVAILABLE),
                       reason="No boolean engines available")
    def test_create_boolean_engine(self):
        """Test boolean engine creation."""
        engine = create_boolean_engine()

        if engine:  # Only test if we have an engine
            assert hasattr(engine, 'union')
            assert hasattr(engine, 'intersect')
            assert hasattr(engine, 'difference')


class TestResolveClipPathsPlugin:
    """Test the ResolveClipPathsPlugin implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = ResolveClipPathsPlugin()
        self.context = Mock(spec=PreprocessingContext)

    def create_svg_element(self, tag_name, **attrs):
        """Helper to create SVG elements."""
        element = ET.Element(f"{{http://www.w3.org/2000/svg}}{tag_name}")
        for key, value in attrs.items():
            element.set(key, value)
        return element

    def test_plugin_initialization(self):
        """Test plugin initialization with different configs."""
        # Default configuration
        plugin = ResolveClipPathsPlugin()
        assert plugin.name == "resolve_clippath"
        assert plugin.description == "Resolves clipPath elements into boolean path intersections"
        assert plugin.enable_nested_clips == True
        assert plugin.enable_transforms == True
        assert plugin.fallback_behavior == "keep_original"

        # Custom configuration
        config = {
            'enable_nested_clips': False,
            'enable_transforms': False,
            'fallback_behavior': 'remove_clips'
        }
        plugin = ResolveClipPathsPlugin(config)
        assert plugin.enable_nested_clips == False
        assert plugin.enable_transforms == False
        assert plugin.fallback_behavior == 'remove_clips'

    def test_can_process_clip_path_attribute(self):
        """Test processing elements with clip-path attributes."""
        # Element with clip-path attribute
        element = self.create_svg_element('rect', **{'clip-path': 'url(#clip1)'})
        assert self.plugin.can_process(element, self.context) == True

        # Element without clip-path attribute
        element = self.create_svg_element('rect')
        assert self.plugin.can_process(element, self.context) == False

    def test_can_process_clippath_definition(self):
        """Test processing clipPath definition elements."""
        # clipPath definition element
        element = self.create_svg_element('clipPath', id='clip1')
        assert self.plugin.can_process(element, self.context) == True

        # Other definition element
        element = self.create_svg_element('defs')
        assert self.plugin.can_process(element, self.context) == False

    def test_parse_clippath_reference(self):
        """Test clipPath reference parsing."""
        # Standard URL reference
        clip_id = self.plugin._parse_clippath_reference('url(#clipPath1)')
        assert clip_id == 'clipPath1'

        # Direct hash reference
        clip_id = self.plugin._parse_clippath_reference('#clipPath2')
        assert clip_id == 'clipPath2'

        # Invalid references
        assert self.plugin._parse_clippath_reference('') is None
        assert self.plugin._parse_clippath_reference('invalid') is None
        assert self.plugin._parse_clippath_reference(None) is None

    def test_element_to_path_spec_rect(self):
        """Test converting rect element to path specification."""
        rect = self.create_svg_element('rect', x='10', y='20', width='100', height='50')
        path_spec = self.plugin._element_to_path_spec(rect)

        assert path_spec is not None
        d_string, fill_rule = path_spec
        assert 'M 10.0 20.0' in d_string
        assert 'L 110.0 20.0' in d_string
        assert 'L 110.0 70.0' in d_string
        assert 'L 10.0 70.0' in d_string
        assert 'Z' in d_string
        assert fill_rule == 'nonzero'

    def test_element_to_path_spec_circle(self):
        """Test converting circle element to path specification."""
        circle = self.create_svg_element('circle', cx='50', cy='60', r='25')
        path_spec = self.plugin._element_to_path_spec(circle)

        assert path_spec is not None
        d_string, fill_rule = path_spec
        assert 'M 25.0 60.0' in d_string  # Start point
        assert 'A 25.0 25.0' in d_string   # Arc command
        assert 'Z' in d_string
        assert fill_rule == 'nonzero'

    def test_element_to_path_spec_path(self):
        """Test converting path element to path specification."""
        path = self.create_svg_element('path', d='M 0 0 L 10 10 Z', **{'fill-rule': 'evenodd'})
        path_spec = self.plugin._element_to_path_spec(path)

        assert path_spec is not None
        d_string, fill_rule = path_spec
        assert d_string == 'M 0 0 L 10 10 Z'
        assert fill_rule == 'evenodd'

    def test_element_to_path_spec_invalid(self):
        """Test handling invalid elements."""
        # Empty rect
        rect = self.create_svg_element('rect', width='0', height='10')
        path_spec = self.plugin._element_to_path_spec(rect)
        assert path_spec is None

        # Unsupported element
        text = self.create_svg_element('text')
        path_spec = self.plugin._element_to_path_spec(text)
        assert path_spec is None

    def test_parse_points(self):
        """Test points string parsing for polygon/polyline."""
        # Comma-separated points
        points = self.plugin._parse_points('10,20 30,40 50,60')
        assert points == [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)]

        # Space-separated points
        points = self.plugin._parse_points('10 20 30 40 50 60')
        assert points == [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)]

        # Mixed separators
        points = self.plugin._parse_points('10,20 30 40 50,60')
        assert points == [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)]

        # Empty string
        points = self.plugin._parse_points('')
        assert points == []

    def test_polygon_to_path_spec(self):
        """Test converting polygon element to path specification."""
        polygon = self.create_svg_element('polygon', points='0,0 10,0 10,10 0,10')
        path_spec = self.plugin._element_to_path_spec(polygon)

        assert path_spec is not None
        d_string, fill_rule = path_spec
        assert d_string.startswith('M 0.0 0.0')
        assert 'L 10.0 0.0' in d_string
        assert 'L 10.0 10.0' in d_string
        assert 'L 0.0 10.0' in d_string
        assert d_string.endswith('Z')

    def test_polyline_to_path_spec(self):
        """Test converting polyline element to path specification."""
        polyline = self.create_svg_element('polyline', points='0,0 10,5 20,0')
        path_spec = self.plugin._element_to_path_spec(polyline)

        assert path_spec is not None
        d_string, fill_rule = path_spec
        assert d_string.startswith('M 0.0 0.0')
        assert 'L 10.0 5.0' in d_string
        assert 'L 20.0 0.0' in d_string
        assert not d_string.endswith('Z')  # Polyline is not closed

    def test_fallback_behavior_remove_clips(self):
        """Test fallback behavior when removing clip-path attributes."""
        plugin = ResolveClipPathsPlugin({'fallback_behavior': 'remove_clips'})
        element = self.create_svg_element('rect', **{'clip-path': 'url(#clip1)'})

        # Mock no boolean engine available
        plugin._boolean_engine = None

        modified = plugin._handle_no_boolean_engine_element(element, self.context)
        assert modified == True
        assert element.get('clip-path') is None

    def test_fallback_behavior_hide_clipped(self):
        """Test fallback behavior when hiding clipped elements."""
        plugin = ResolveClipPathsPlugin({'fallback_behavior': 'hide_clipped'})
        element = self.create_svg_element('rect', **{'clip-path': 'url(#clip1)'})

        # Mock no boolean engine available
        plugin._boolean_engine = None

        modified = plugin._handle_no_boolean_engine_element(element, self.context)
        assert modified == True
        assert element.get('visibility') == 'hidden'

    def test_catalog_clippath_definitions(self):
        """Test cataloging clipPath definitions."""
        # Create SVG with clipPath definitions
        svg = self.create_svg_element('svg')
        defs = ET.SubElement(svg, 'defs')

        clip1 = ET.SubElement(defs, 'clipPath')
        clip1.set('id', 'clip1')

        clip2 = ET.SubElement(defs, 'clipPath')
        clip2.set('id', 'clip2')

        # clipPath without ID should be ignored
        clip_no_id = ET.SubElement(defs, 'clipPath')

        definitions = self.plugin._catalog_clippath_definitions(svg)
        assert len(definitions) == 2
        assert 'clip1' in definitions
        assert 'clip2' in definitions
        assert definitions['clip1'] is clip1
        assert definitions['clip2'] is clip2

    @pytest.mark.skipif(not (PATHOPS_AVAILABLE or PYCLIPPER_AVAILABLE),
                       reason="Boolean engines not available")
    def test_process_with_boolean_engine(self):
        """Test processing when boolean engine is available."""
        # Create element with clip-path
        element = self.create_svg_element('rect', **{'clip-path': 'url(#clip1)'})

        # Mock SVG root with clipPath definition
        svg_root = self.create_svg_element('svg')
        defs = ET.SubElement(svg_root, 'defs')
        clippath = ET.SubElement(defs, 'clipPath')
        clippath.set('id', 'clip1')
        clip_rect = ET.SubElement(clippath, 'rect')
        clip_rect.set('width', '50')
        clip_rect.set('height', '50')

        self.plugin._svg_root = svg_root

        # Try to process (will fail without proper boolean engine setup, but should not crash)
        result = self.plugin.process(element, self.context)
        assert isinstance(result, bool)  # Should return boolean, not crash

    def test_create_factory_function(self):
        """Test the factory function for creating clipPath resolver."""
        from src.preprocessing.resolve_clippath_plugin import create_clippath_resolver

        plugin = create_clippath_resolver(
            enable_nested_clips=False,
            enable_transforms=False,
            fallback_behavior="remove_clips"
        )

        assert isinstance(plugin, ResolveClipPathsPlugin)
        assert plugin.enable_nested_clips == False
        assert plugin.enable_transforms == False
        assert plugin.fallback_behavior == "remove_clips"


class TestSVGToPathConversions:
    """Test SVG element to path conversions in detail."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = ResolveClipPathsPlugin()

    def create_svg_element(self, tag_name, **attrs):
        """Helper to create SVG elements."""
        element = ET.Element(f"{{http://www.w3.org/2000/svg}}{tag_name}")
        for key, value in attrs.items():
            element.set(key, value)
        return element

    def test_rect_with_rounded_corners(self):
        """Test rect conversion (rounded corners not implemented yet)."""
        rect = self.create_svg_element('rect', x='0', y='0', width='100', height='50', rx='5', ry='5')
        path_spec = self.plugin._element_to_path_spec(rect)

        # Current implementation doesn't handle rounded corners
        # Should still create a basic rectangle path
        assert path_spec is not None
        d_string, fill_rule = path_spec
        assert 'M 0.0 0.0' in d_string

    def test_ellipse_conversion(self):
        """Test ellipse element conversion."""
        ellipse = self.create_svg_element('ellipse', cx='50', cy='30', rx='40', ry='20')
        path_spec = self.plugin._element_to_path_spec(ellipse)

        assert path_spec is not None
        d_string, fill_rule = path_spec
        assert 'M 10.0 30.0' in d_string  # Start point (cx - rx, cy)
        assert 'A 40.0 20.0' in d_string   # Arc with rx, ry

    def test_line_conversion(self):
        """Test line element conversion."""
        line = self.create_svg_element('line', x1='0', y1='0', x2='100', y2='50')
        path_spec = self.plugin._element_to_path_spec(line)

        assert path_spec is not None
        d_string, fill_rule = path_spec
        assert d_string == 'M 0.0 0.0 L 100.0 50.0'

    def test_element_conversion_error_handling(self):
        """Test error handling in element conversion."""
        # Invalid numeric values
        rect = self.create_svg_element('rect', x='invalid', y='0', width='100', height='50')
        path_spec = self.plugin._element_to_path_spec(rect)
        assert path_spec is None

        # Missing required attributes
        circle = self.create_svg_element('circle', cx='50', cy='50')  # Missing radius
        path_spec = self.plugin._element_to_path_spec(circle)
        assert path_spec is None

        # Zero dimensions
        rect_zero = self.create_svg_element('rect', x='0', y='0', width='0', height='50')
        path_spec = self.plugin._element_to_path_spec(rect_zero)
        assert path_spec is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
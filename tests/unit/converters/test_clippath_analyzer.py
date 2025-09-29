#!/usr/bin/env python3
"""
Unit tests for ClipPathAnalyzer.

Tests the complete clipPath complexity analysis system including:
- Complexity classification (SIMPLE, NESTED, COMPLEX, UNSUPPORTED)
- Nested clipPath chain resolution
- Content analysis for conversion strategy
- Performance benchmarks
"""

import pytest
from unittest.mock import Mock, MagicMock
from lxml import etree as ET

from src.converters.clippath_analyzer import ClipPathAnalyzer, ClipPathComplexity
from src.converters.clippath_types import ClipPathDefinition, ClipPathAnalysis, ClippingType
from tests.fixtures.clippath_fixtures import (
    create_svg_element, create_simple_rect_clippath, create_simple_path_clippath,
    create_complex_path_clippath, create_text_clippath, create_filter_clippath,
    create_animation_clippath, create_transform_clippath, create_nested_clippath_definitions,
    create_multiple_shapes_clippath, create_circular_reference_clippath,
    SAMPLE_SVG_DATA, parse_svg_string, get_clippath_definitions_from_svg
)


class TestClipPathAnalyzer:
    """Test the ClipPathAnalyzer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = ClipPathAnalyzer()
        self.mock_services = Mock()

    def test_analyzer_initialization(self):
        """Test analyzer initialization with and without services."""
        # Without services
        analyzer = ClipPathAnalyzer()
        assert analyzer.services is None
        assert len(analyzer._analysis_cache) == 0
        assert len(analyzer._clippath_definitions) == 0

        # With services
        analyzer_with_services = ClipPathAnalyzer(self.mock_services)
        assert analyzer_with_services.services == self.mock_services

    def test_simple_clippath_analysis(self):
        """Test analysis of simple clipPath definitions."""
        # Simple rectangular clipPath
        rect_clip = create_simple_rect_clippath()
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        clippath_definitions = {'simple_rect': rect_clip}

        analysis = self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#simple_rect)')

        assert analysis.complexity == ClipPathComplexity.SIMPLE
        assert len(analysis.clip_chain) == 1
        assert analysis.can_flatten == True
        assert analysis.requires_emf == False
        assert analysis.estimated_nodes == 1
        assert analysis.has_text == False
        assert analysis.has_filters == False
        assert analysis.has_animations == False

    def test_simple_path_clippath_analysis(self):
        """Test analysis of simple path-based clipPath."""
        path_clip = create_simple_path_clippath()
        element = create_svg_element('circle', cx=50, cy=50, r=25)
        clippath_definitions = {'simple_path': path_clip}

        analysis = self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#simple_path)')

        assert analysis.complexity == ClipPathComplexity.SIMPLE
        assert analysis.can_flatten == True
        assert analysis.requires_emf == False
        assert "Single simple clipPath" in analysis.reason

    def test_nested_clippath_analysis(self):
        """Test analysis of nested clipPath definitions."""
        nested_clips = create_nested_clippath_definitions()
        element = create_svg_element('rect', x=0, y=0, width=300, height=300)

        analysis = self.analyzer.analyze_clippath(element, nested_clips, 'url(#nested_clip)')

        assert analysis.complexity == ClipPathComplexity.NESTED
        assert len(analysis.clip_chain) >= 1  # May resolve to multiple clips
        assert analysis.can_flatten == True
        assert "Nested clipPath chain" in analysis.reason

    def test_text_clippath_analysis(self):
        """Test analysis of clipPath containing text."""
        text_clip = create_text_clippath()
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        clippath_definitions = {'text_clip': text_clip}

        analysis = self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#text_clip)')

        assert analysis.complexity == ClipPathComplexity.COMPLEX
        assert analysis.has_text == True
        assert analysis.requires_emf == True
        assert "Contains text elements" in analysis.reason

    def test_filter_clippath_analysis(self):
        """Test analysis of clipPath with filter effects."""
        filter_clip = create_filter_clippath()
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        clippath_definitions = {'filter_clip': filter_clip}

        analysis = self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#filter_clip)')

        assert analysis.complexity == ClipPathComplexity.COMPLEX
        assert analysis.has_filters == True
        assert analysis.requires_emf == True
        assert "Contains filter effects" in analysis.reason

    def test_animation_clippath_analysis(self):
        """Test analysis of clipPath with animations."""
        animation_clip = create_animation_clippath()
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        clippath_definitions = {'animated_clip': animation_clip}

        analysis = self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#animated_clip)')

        assert analysis.complexity == ClipPathComplexity.UNSUPPORTED
        assert analysis.has_animations == True
        assert analysis.can_flatten == False
        assert analysis.requires_emf == False
        assert "Contains animations" in analysis.reason

    def test_transform_clippath_analysis(self):
        """Test analysis of clipPath with complex transforms."""
        transform_clip = create_transform_clippath()
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        clippath_definitions = {'transform_clip': transform_clip}

        analysis = self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#transform_clip)')

        assert analysis.complexity == ClipPathComplexity.COMPLEX
        assert analysis.transform_complexity >= 2
        assert analysis.requires_emf == True
        assert "Complex transforms require EMF" in analysis.reason

    def test_multiple_shapes_clippath_analysis(self):
        """Test analysis of clipPath with multiple shapes."""
        multi_clip = create_multiple_shapes_clippath()
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        clippath_definitions = {'multi_shapes': multi_clip}

        analysis = self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#multi_shapes)')

        assert analysis.estimated_nodes == 3
        # Should be complex due to multiple shapes
        assert analysis.complexity in [ClipPathComplexity.NESTED, ClipPathComplexity.COMPLEX]

    def test_circular_reference_detection(self):
        """Test detection of circular clipPath references."""
        circular_clips = create_circular_reference_clippath()
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)

        analysis = self.analyzer.analyze_clippath(element, circular_clips, 'url(#clip_a)')

        # Should handle circular references gracefully
        assert analysis.complexity != ClipPathComplexity.UNSUPPORTED or "circular" in analysis.reason.lower()

    def test_invalid_clippath_reference(self):
        """Test handling of invalid clipPath references."""
        clippath_definitions = {}
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)

        # Invalid reference
        analysis = self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#nonexistent)')

        assert analysis.complexity == ClipPathComplexity.UNSUPPORTED
        assert "not found" in analysis.reason

        # Malformed reference
        analysis = self.analyzer.analyze_clippath(element, clippath_definitions, 'invalid-ref')

        assert analysis.complexity == ClipPathComplexity.UNSUPPORTED
        assert "Invalid clipPath reference" in analysis.reason

    def test_clippath_reference_parsing(self):
        """Test clipPath reference parsing."""
        # url(#id) format
        assert self.analyzer._parse_clippath_reference('url(#clip1)') == 'clip1'

        # Direct #id format
        assert self.analyzer._parse_clippath_reference('#clip2') == 'clip2'

        # Invalid formats
        assert self.analyzer._parse_clippath_reference('') is None
        assert self.analyzer._parse_clippath_reference('invalid') is None
        assert self.analyzer._parse_clippath_reference(None) is None

    def test_transform_complexity_analysis(self):
        """Test transform complexity detection."""
        # No transform
        element = create_svg_element('rect', x=0, y=0, width=100, height=100)
        complexity = self.analyzer._analyze_transform_complexity(element)
        assert complexity == 0

        # Simple transform
        element.set('transform', 'translate(10, 20)')
        complexity = self.analyzer._analyze_transform_complexity(element)
        assert complexity == 1

        # Complex transform with matrix
        element.set('transform', 'matrix(1 0.5 -0.5 1 10 20)')
        complexity = self.analyzer._analyze_transform_complexity(element)
        assert complexity == 2

        # Multiple transforms
        element.set('transform', 'translate(10, 20) rotate(45) scale(1.5)')
        complexity = self.analyzer._analyze_transform_complexity(element)
        assert complexity == 2

    def test_text_content_detection(self):
        """Test text content detection in elements."""
        # Text element
        text = create_svg_element('text', x=10, y=20)
        assert self.analyzer._has_text_content(text) == True

        # tspan element
        tspan = create_svg_element('tspan', x=10, y=20)
        assert self.analyzer._has_text_content(tspan) == True

        # textPath element
        text_path = create_svg_element('textPath')
        assert self.analyzer._has_text_content(text_path) == True

        # Element with nested text
        group = create_svg_element('g')
        nested_text = create_svg_element('text', x=5, y=15)
        group.append(nested_text)
        assert self.analyzer._has_text_content(group) == True

        # Non-text element
        rect = create_svg_element('rect', x=0, y=0, width=100, height=100)
        assert self.analyzer._has_text_content(rect) == False

    def test_filter_effects_detection(self):
        """Test filter effects detection."""
        # Element with filter attribute
        rect = create_svg_element('rect', x=0, y=0, width=100, height=100)
        rect.set('filter', 'url(#blur)')
        assert self.analyzer._has_filter_effects(rect) == True

        # Element with nested filter
        group = create_svg_element('g')
        filtered_circle = create_svg_element('circle', cx=50, cy=50, r=25)
        filtered_circle.set('filter', 'url(#shadow)')
        group.append(filtered_circle)
        assert self.analyzer._has_filter_effects(group) == True

        # Element without filters
        plain_rect = create_svg_element('rect', x=0, y=0, width=100, height=100)
        assert self.analyzer._has_filter_effects(plain_rect) == False

    def test_animation_detection(self):
        """Test animation detection."""
        # Element with animate
        rect = create_svg_element('rect', x=0, y=0, width=100, height=100)
        animate = create_svg_element('animate', attributeName='width', dur='2s')
        rect.append(animate)
        assert self.analyzer._has_animations(rect) == True

        # Element with animateTransform
        rect2 = create_svg_element('rect', x=0, y=0, width=100, height=100)
        animate_transform = create_svg_element('animateTransform', attributeName='transform')
        rect2.append(animate_transform)
        assert self.analyzer._has_animations(rect2) == True

        # Element without animations
        static_rect = create_svg_element('rect', x=0, y=0, width=100, height=100)
        assert self.analyzer._has_animations(static_rect) == False

    def test_analysis_caching(self):
        """Test analysis result caching."""
        rect_clip = create_simple_rect_clippath()
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        clippath_definitions = {'simple_rect': rect_clip}

        # First analysis
        analysis1 = self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#simple_rect)')

        # Second analysis (should use cache)
        analysis2 = self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#simple_rect)')

        assert analysis1 == analysis2
        assert len(self.analyzer._analysis_cache) == 1

        # Clear cache
        self.analyzer.clear_cache()
        assert len(self.analyzer._analysis_cache) == 0

    def test_cache_statistics(self):
        """Test cache statistics reporting."""
        stats = self.analyzer.get_cache_stats()
        assert 'cache_size' in stats
        assert 'definitions_count' in stats
        assert stats['cache_size'] == 0

        # Add some analysis
        rect_clip = create_simple_rect_clippath()
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        clippath_definitions = {'simple_rect': rect_clip}

        self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#simple_rect)')

        stats = self.analyzer.get_cache_stats()
        assert stats['cache_size'] == 1


class TestClipPathAnalyzerWithRealSVG:
    """Test analyzer with real SVG data."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = ClipPathAnalyzer()

    @pytest.mark.parametrize("svg_name,expected_complexity", [
        ('simple_rect_clip', ClipPathComplexity.SIMPLE),
        ('nested_clips', ClipPathComplexity.NESTED),
        ('text_in_clippath', ClipPathComplexity.COMPLEX),
        ('complex_path_clip', ClipPathComplexity.SIMPLE),  # Complex path but still simple structure
    ])
    def test_real_svg_analysis(self, svg_name, expected_complexity):
        """Test analyzer with real SVG samples."""
        svg_string = SAMPLE_SVG_DATA[svg_name]
        svg_element = parse_svg_string(svg_string)

        # Extract clipPath definitions
        clippath_defs_elements = get_clippath_definitions_from_svg(svg_element)

        # Convert to ClipPathDefinition objects
        clippath_definitions = {}
        for clip_id, clip_element in clippath_defs_elements.items():
            shapes = list(clip_element)
            clippath_definitions[clip_id] = ClipPathDefinition(
                id=clip_id,
                units=clip_element.get('clipPathUnits', 'userSpaceOnUse'),
                clip_rule=clip_element.get('clip-rule', 'nonzero'),
                shapes=shapes if shapes else None,
                clipping_type=ClippingType.SHAPE_BASED if shapes else ClippingType.PATH_BASED
            )

        # Find element with clip-path
        clipped_elements = svg_element.findall('.//*[@clip-path]')
        assert len(clipped_elements) > 0, f"No clipped elements found in {svg_name}"

        element = clipped_elements[0]
        clip_ref = element.get('clip-path')

        # Analyze
        analysis = self.analyzer.analyze_clippath(element, clippath_definitions, clip_ref)

        assert analysis.complexity == expected_complexity
        assert len(analysis.clip_chain) > 0

    def test_performance_with_large_clippath(self):
        """Test analyzer performance with large clipPath structures."""
        import time

        # Create a large clipPath with many shapes
        shapes = []
        for i in range(100):  # 100 shapes
            rect = create_svg_element('rect', x=i*2, y=i*2, width=10, height=10)
            shapes.append(rect)

        large_clip = ClipPathDefinition(
            id='large_clip',
            units='userSpaceOnUse',
            clip_rule='nonzero',
            shapes=shapes,
            clipping_type=ClippingType.COMPLEX
        )

        element = create_svg_element('rect', x=0, y=0, width=1000, height=1000)
        clippath_definitions = {'large_clip': large_clip}

        # Measure analysis time
        start_time = time.time()
        analysis = self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#large_clip)')
        end_time = time.time()

        analysis_time = end_time - start_time

        # Should complete within reasonable time (1 second)
        assert analysis_time < 1.0, f"Analysis took too long: {analysis_time:.3f}s"
        assert analysis.estimated_nodes == 100
        assert analysis.complexity == ClipPathComplexity.COMPLEX

    def test_error_handling(self):
        """Test error handling in analysis."""
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)

        # Test with None clipPath definitions
        analysis = self.analyzer.analyze_clippath(element, {}, None)
        assert analysis.complexity == ClipPathComplexity.UNSUPPORTED

        # Test with malformed clipPath definition
        malformed_clip = ClipPathDefinition(
            id='malformed',
            units='userSpaceOnUse',
            clip_rule='nonzero',
            shapes=None,  # No shapes or path_data
            clipping_type=ClippingType.PATH_BASED
        )

        clippath_definitions = {'malformed': malformed_clip}
        analysis = self.analyzer.analyze_clippath(element, clippath_definitions, 'url(#malformed)')

        # Should handle gracefully
        assert isinstance(analysis, ClipPathAnalysis)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
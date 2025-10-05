#!/usr/bin/env python3
"""
Tests for safe analyzer iteration with cython Comment objects.

Tests that previously caused "argument of type '_cython_3_1_3.cython_function_or_method' is not iterable" errors.
"""

import pytest
from lxml import etree as ET
from core.xml.safe_iter import walk, children, is_element, count_elements, find_elements_by_tag
from core.parse.parser import SVGParser
from core.analyze.analyzer import SVGAnalyzer


class TestSafeIterationBasics:
    """Test core safe iteration utilities."""

    def test_walk_ignores_comments(self):
        """Test that walk() filters out XML comments."""
        svg_content = b'''<svg xmlns="http://www.w3.org/2000/svg">
          <!-- top comment -->
          <g>
            <!-- inner comment -->
            <rect x="0" y="0" width="10" height="10"/>
          </g>
          <!-- bottom comment -->
        </svg>'''

        root = ET.fromstring(svg_content)
        elements = list(walk(root))

        # Should only get svg, g, rect (3 elements), no comments
        assert len(elements) == 3
        tags = [elem.tag.split('}')[-1] for elem in elements]
        assert 'svg' in tags
        assert 'g' in tags
        assert 'rect' in tags

    def test_children_ignores_comments(self):
        """Test that children() filters out XML comments."""
        svg_content = b'''<svg xmlns="http://www.w3.org/2000/svg">
          <!-- comment 1 -->
          <rect width="10" height="10"/>
          <!-- comment 2 -->
          <circle cx="5" cy="5" r="3"/>
          <!-- comment 3 -->
        </svg>'''

        root = ET.fromstring(svg_content)
        child_elements = list(children(root))

        # Should only get rect and circle, no comments
        assert len(child_elements) == 2
        tags = [elem.tag.split('}')[-1] for elem in child_elements]
        assert 'rect' in tags
        assert 'circle' in tags

    def test_is_element_filters_comments(self):
        """Test that is_element() correctly identifies comments."""
        svg_content = b'''<svg xmlns="http://www.w3.org/2000/svg">
          <!-- This is a comment -->
          <rect x="0" y="0" width="10" height="10"/>
        </svg>'''

        root = ET.fromstring(svg_content)

        # Test all children including comments
        for child in root:
            if hasattr(child, 'tag') and 'Comment' in str(type(child)):
                assert not is_element(child)
            elif hasattr(child, 'tag') and child.tag.endswith('rect'):
                assert is_element(child)

    def test_count_elements_excludes_comments(self):
        """Test element counting excludes comments."""
        svg_content = b'''<svg xmlns="http://www.w3.org/2000/svg">
          <!-- comment -->
          <g>
            <!-- nested comment -->
            <rect width="10" height="10"/>
            <!-- another comment -->
            <circle cx="5" cy="5" r="3"/>
          </g>
          <!-- final comment -->
        </svg>'''

        root = ET.fromstring(svg_content)
        count = count_elements(root)

        # Should count: svg, g, rect, circle = 4 elements
        assert count == 4

    def test_find_elements_by_tag_with_comments(self):
        """Test finding elements by tag ignores comments."""
        svg_content = b'''<svg xmlns="http://www.w3.org/2000/svg">
          <!-- comment about rects -->
          <rect x="0" y="0" width="10" height="10"/>
          <g>
            <!-- another comment -->
            <rect x="20" y="20" width="5" height="5"/>
          </g>
          <!-- final comment -->
        </svg>'''

        root = ET.fromstring(svg_content)
        rects = list(find_elements_by_tag(root, 'rect'))

        # Should find exactly 2 rect elements
        assert len(rects) == 2
        for rect in rects:
            assert rect.tag.endswith('rect')


class TestAnalyzerWithComments:
    """Test analyzer functionality with comment-heavy SVG content."""

    def test_analyzer_ignores_comments(self):
        """Test that analyzer completes without errors on comment-heavy SVG."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
          <!-- Header comment -->
          <?xml-stylesheet type="text/css" href="x.css"?>
          <defs>
            <!-- Definitions comment -->
            <linearGradient id="grad1">
              <stop offset="0%" stop-color="red"/>
              <!-- Gradient stop comment -->
              <stop offset="100%" stop-color="blue"/>
            </linearGradient>
          </defs>
          <!-- Main content comment -->
          <g transform="translate(10,10)">
            <!-- Group comment -->
            <rect x="0" y="0" width="10" height="10" fill="url(#grad1)"/>
          </g>
          <!-- Footer comment -->
        </svg>'''

        # Parse SVG
        parser = SVGParser()
        parse_result = parser.parse(svg_content)
        assert parse_result.success, f"Parse failed: {parse_result.error}"

        # Analyze without crashing
        analyzer = SVGAnalyzer()
        analysis_result = analyzer.analyze(parse_result.svg_root)

        # Should complete successfully
        assert analysis_result.element_count >= 2  # At least svg and some children
        assert analysis_result.complexity_score > 0
        assert analysis_result.scene is not None

    def test_analyzer_with_interleaved_comments(self):
        """Test analyzer with comments interleaved throughout structure."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
          <!-- Start -->
          <g>
            <!-- Level 1 -->
            <g>
              <!-- Level 2 -->
              <rect width="50" height="50"/>
              <!-- Between elements -->
              <circle cx="100" cy="100" r="25"/>
              <!-- Level 2 end -->
            </g>
            <!-- Level 1 end -->
          </g>
          <!-- End -->
        </svg>'''

        parser = SVGParser()
        parse_result = parser.parse(svg_content)
        assert parse_result.success

        analyzer = SVGAnalyzer()
        analysis_result = analyzer.analyze(parse_result.svg_root)

        # Should detect nested groups and shapes
        assert analysis_result.element_count >= 3  # svg, groups, shapes
        assert analysis_result.group_count > 0  # Should detect groups

    def test_analyzer_with_deep_nesting_and_comments(self):
        """Test analyzer with deeply nested structure and comments at every level."""
        # Build deeply nested SVG with comments
        svg_parts = ['<svg xmlns="http://www.w3.org/2000/svg">']
        svg_parts.append('<!-- Root comment -->')

        for i in range(5):
            svg_parts.append(f'<g id="group{i}">')
            svg_parts.append(f'<!-- Group {i} comment -->')

        svg_parts.append('<rect width="10" height="10"/>')
        svg_parts.append('<!-- Leaf comment -->')

        for i in range(5):
            svg_parts.append('</g>')
            svg_parts.append(f'<!-- End group {4-i} -->')

        svg_parts.append('</svg>')

        svg_content = '\n'.join(svg_parts)

        parser = SVGParser()
        parse_result = parser.parse(svg_content)
        assert parse_result.success

        analyzer = SVGAnalyzer()
        analysis_result = analyzer.analyze(parse_result.svg_root)

        # Should handle deep nesting without issues
        assert analysis_result.element_count >= 6  # svg + 5 groups + rect
        assert analysis_result.group_count >= 5  # Should detect all groups

    def test_parser_element_counting_with_comments(self):
        """Test that parser correctly counts elements excluding comments."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
          <!-- This comment should not be counted -->
          <rect width="100" height="50"/>
          <!-- Neither should this one -->
          <circle cx="50" cy="25" r="20"/>
          <!-- Or this final one -->
        </svg>'''

        parser = SVGParser()
        result = parser.parse(svg_content)

        assert result.success
        # Should count: svg(1) + rect(1) + circle(1) = 3 elements
        assert result.element_count == 3

    def test_text_elements_with_comments(self):
        """Test text processing with comments."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
          <!-- Text element comment -->
          <text x="10" y="20" font-size="12">
            <!-- Text content comment -->
            Hello World
            <tspan x="10" y="35">
              <!-- Tspan comment -->
              Second line
            </tspan>
            <!-- After tspan comment -->
          </text>
          <!-- End text comment -->
        </svg>'''

        parser = SVGParser()
        parse_result = parser.parse(svg_content)
        assert parse_result.success

        analyzer = SVGAnalyzer()
        analysis_result = analyzer.analyze(parse_result.svg_root)

        # Should detect text without crashing
        assert analysis_result.element_count >= 2  # svg, text (tspan might be counted separately)
        assert analysis_result.text_count > 0  # Should detect text elements


class TestProcessingInstructionsAndEntities:
    """Test handling of processing instructions and other non-element nodes."""

    def test_processing_instructions_ignored(self):
        """Test that processing instructions are ignored safely."""
        svg_content = b'''<svg xmlns="http://www.w3.org/2000/svg">
          <?xml-stylesheet type="text/css" href="style.css"?>
          <rect width="10" height="10"/>
          <?custom-pi data="value"?>
          <circle cx="5" cy="5" r="3"/>
        </svg>'''

        root = ET.fromstring(svg_content)
        elements = list(walk(root))

        # Should only count actual elements: svg, rect, circle
        assert len(elements) == 3
        tags = [elem.tag.split('}')[-1] for elem in elements]
        assert set(tags) == {'svg', 'rect', 'circle'}

    def test_mixed_node_types_parsing(self):
        """Test parsing with mixed node types (comments, PIs, elements)."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
          <?xml-stylesheet type="text/css" href="style.css"?>
          <!-- Header comment -->
          <defs>
            <!-- Defs comment -->
            <linearGradient id="grad1">
              <stop offset="0%" stop-color="red"/>
            </linearGradient>
          </defs>
          <!-- Content comment -->
          <?custom-instruction?>
          <rect width="50" height="50" fill="url(#grad1)"/>
          <!-- Footer comment -->
        </svg>'''

        parser = SVGParser()
        result = parser.parse(svg_content)

        assert result.success
        # Should count elements only: svg, defs, linearGradient, stop, rect
        assert result.element_count == 5

        analyzer = SVGAnalyzer()
        analysis_result = analyzer.analyze(result.svg_root)

        # Should complete without errors
        assert analysis_result.element_count >= 4  # Excluding root SVG
        assert analysis_result.scene is not None


class TestRegressionPrevention:
    """Tests that specifically prevent regression of the original cython error."""

    def test_original_error_scenario(self):
        """Test the exact scenario that caused the original cython error."""
        # This is the SVG content from the original failing test
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 400 300" width="400" height="300">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
        <pattern id="pattern1" patternUnits="userSpaceOnUse" width="20" height="20">
            <rect width="10" height="10" fill="blue"/>
            <rect x="10" y="10" width="10" height="10" fill="blue"/>
        </pattern>
    </defs>

    <!-- Basic shapes -->
    <rect x="10" y="10" width="100" height="60" fill="url(#grad1)" stroke="black" stroke-width="2"/>
    <circle cx="200" cy="50" r="40" fill="url(#pattern1)"/>
    <ellipse cx="320" cy="50" rx="60" ry="30" fill="green" opacity="0.7"/>

    <!-- Paths -->
    <path d="M 50 150 Q 100 100 150 150 T 250 150" stroke="purple" stroke-width="3" fill="none"/>
    <path d="M 20 200 L 50 180 L 80 200 Z" fill="orange"/>

    <!-- Text with transformations -->
    <g transform="translate(50, 250) rotate(15)">
        <text font-size="16" fill="darkblue">Transformed Text</text>
    </g>

    <!-- Groups and nested transforms -->
    <g transform="scale(0.8) translate(200, 180)">
        <g transform="rotate(30)">
            <rect width="60" height="40" fill="pink" stroke="navy"/>
            <text x="30" y="25" text-anchor="middle" font-size="12">Nested</text>
        </g>
    </g>
</svg>'''

        # This should NOT raise the cython error anymore
        parser = SVGParser()
        parse_result = parser.parse(svg_content)
        assert parse_result.success, f"Parse failed: {parse_result.error}"

        analyzer = SVGAnalyzer()
        analysis_result = analyzer.analyze(parse_result.svg_root)

        # Should complete successfully with meaningful results
        assert analysis_result.element_count > 10  # Complex SVG with many elements
        assert analysis_result.complexity_score > 1.0  # Should be complex
        assert analysis_result.scene is not None
        assert len(analysis_result.scene) > 0

    def test_iterator_error_prevention(self):
        """Test that prevents the specific 'cython_function_or_method' is not iterable error."""
        svg_content = b'''<svg xmlns="http://www.w3.org/2000/svg">
          <!-- This type of comment previously caused the error -->
          <g>
            <rect width="10" height="10"/>
            <!-- Another problematic comment -->
          </g>
        </svg>'''

        root = ET.fromstring(svg_content)

        # These operations should NOT raise TypeError about cython functions
        try:
            # Test walk operation
            elements = list(walk(root))
            assert len(elements) == 3  # svg, g, rect

            # Test children operation
            svg_children = list(children(root))
            assert len(svg_children) == 1  # Just the g element

            # Test nested children
            g_element = svg_children[0]
            g_children = list(children(g_element))
            assert len(g_children) == 1  # Just the rect element

        except TypeError as e:
            if 'cython_function_or_method' in str(e):
                pytest.fail(f"Cython iteration error not prevented: {e}")
            else:
                raise  # Re-raise if it's a different TypeError
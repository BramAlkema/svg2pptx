#!/usr/bin/env python3
"""
Comprehensive tests for StyleService CSS cascade implementation.

Tests CSS specificity, inheritance, and proper cascade order
following W3C CSS specifications.
"""

import pytest
from lxml import etree as ET
from src.services.style_service import StyleService, parse_inline_style, parse_css, _specificity


class TestInlineStyleParsing:
    """Test inline style parsing functionality."""

    def test_parse_inline_style_basic(self):
        """Test basic inline style parsing."""
        style_text = "fill: red; stroke: blue; stroke-width: 2px;"
        result = parse_inline_style(style_text)

        assert result['fill'] == 'red'
        assert result['stroke'] == 'blue'
        assert result['stroke-width'] == '2px'

    def test_parse_inline_style_with_important(self):
        """Test that !important is removed from values."""
        style_text = "fill: red !important; stroke: blue;"
        result = parse_inline_style(style_text)

        assert result['fill'] == 'red'  # !important stripped
        assert result['stroke'] == 'blue'

    def test_parse_inline_style_malformed(self):
        """Test parsing malformed style strings."""
        style_text = "fill: red; invalid-property; stroke: blue"
        result = parse_inline_style(style_text)

        assert result['fill'] == 'red'
        assert result['stroke'] == 'blue'
        assert len(result) == 2  # Invalid property ignored

    def test_parse_inline_style_empty(self):
        """Test parsing empty or None style."""
        assert parse_inline_style("") == {}
        assert parse_inline_style(None) == {}
        assert parse_inline_style("   ") == {}


class TestCSSParsing:
    """Test CSS rule parsing functionality."""

    def test_parse_css_single_rule(self):
        """Test parsing single CSS rule."""
        css = """
        .my-class {
            fill: red;
            stroke: blue;
        }
        """
        rules = parse_css(css)

        assert len(rules) == 1
        selector, decls, spec, order = rules[0]
        assert selector == '.my-class'
        assert decls['fill'] == 'red'
        assert decls['stroke'] == 'blue'
        assert spec == (0, 1, 0)  # Class specificity
        assert order == 0

    def test_parse_css_multiple_rules(self):
        """Test parsing multiple CSS rules with different selectors."""
        css = """
        rect { fill: black; }
        .class { fill: green; }
        #id { fill: red; }
        """
        rules = parse_css(css)

        assert len(rules) == 3

        # Check selector parsing
        selectors = [rule[0] for rule in rules]
        assert 'rect' in selectors
        assert '.class' in selectors
        assert '#id' in selectors

        # Check specificity
        specificities = [rule[2] for rule in rules]
        assert (0, 0, 1) in specificities  # tag
        assert (0, 1, 0) in specificities  # class
        assert (1, 0, 0) in specificities  # id

    def test_parse_css_comma_separated_selectors(self):
        """Test parsing comma-separated selectors."""
        css = """
        rect, circle, ellipse {
            fill: blue;
            stroke: red;
        }
        """
        rules = parse_css(css)

        assert len(rules) == 3
        selectors = [rule[0] for rule in rules]
        assert 'rect' in selectors
        assert 'circle' in selectors
        assert 'ellipse' in selectors

        # All should have same declarations
        for _, decls, _, _ in rules:
            assert decls['fill'] == 'blue'
            assert decls['stroke'] == 'red'

    def test_parse_css_with_comments(self):
        """Test CSS parsing with comments."""
        css = """
        /* This is a comment */
        rect {
            fill: red; /* inline comment */
            stroke: blue;
        }
        /* Another comment */
        """
        rules = parse_css(css)

        assert len(rules) == 1
        _, decls, _, _ = rules[0]
        assert decls['fill'] == 'red'
        assert decls['stroke'] == 'blue'


class TestSpecificity:
    """Test CSS specificity calculation."""

    def test_specificity_tag_selector(self):
        """Test tag selector specificity."""
        assert _specificity('rect') == (0, 0, 1)
        assert _specificity('circle') == (0, 0, 1)
        assert _specificity('  ellipse  ') == (0, 0, 1)  # Whitespace trimmed

    def test_specificity_class_selector(self):
        """Test class selector specificity."""
        assert _specificity('.my-class') == (0, 1, 0)
        assert _specificity('.another-class') == (0, 1, 0)

    def test_specificity_id_selector(self):
        """Test ID selector specificity."""
        assert _specificity('#my-id') == (1, 0, 0)
        assert _specificity('#another-id') == (1, 0, 0)


class TestStyleService:
    """Test complete StyleService functionality."""

    def test_initialization_empty(self):
        """Test StyleService initialization without SVG."""
        service = StyleService()
        assert service.rules == []

    def test_initialization_with_svg(self):
        """Test StyleService initialization with SVG containing styles."""
        svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <style>
                rect { fill: blue; }
                .my-class { stroke: red; }
            </style>
        </svg>''')

        service = StyleService(svg)
        assert len(service.rules) == 2

        # Check rules were parsed correctly
        selectors = [rule[0] for rule in service.rules]
        assert 'rect' in selectors
        assert '.my-class' in selectors

    def test_style_collection_multiple_style_elements(self):
        """Test collecting styles from multiple <style> elements."""
        svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <style>rect { fill: blue; }</style>
            </defs>
            <style>.my-class { stroke: red; }</style>
        </svg>''')

        service = StyleService(svg)
        assert len(service.rules) == 2

    def test_css_cascade_specificity(self):
        """Test CSS cascade with specificity precedence."""
        svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <style>
                rect { fill: blue; }
                .my-class { fill: green; }
                #my-id { fill: red; }
            </style>
            <rect class="my-class" id="my-id" fill="yellow" style="fill: purple"/>
        </svg>''')

        service = StyleService(svg)
        rect = svg.find('.//{http://www.w3.org/2000/svg}rect')
        style = service.compute_style(rect)

        # Inline style (highest specificity) should win
        assert style['fill'] == 'purple'

    def test_css_cascade_without_inline(self):
        """Test CSS cascade without inline styles."""
        svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <style>
                rect { fill: blue; }
                .my-class { fill: green; }
                #my-id { fill: red; }
            </style>
            <rect class="my-class" id="my-id" fill="yellow"/>
        </svg>''')

        service = StyleService(svg)
        rect = svg.find('.//{http://www.w3.org/2000/svg}rect')
        style = service.compute_style(rect)

        # Presentation attribute should win over CSS rules
        assert style['fill'] == 'yellow'

    def test_css_cascade_css_only(self):
        """Test CSS cascade with only CSS rules."""
        svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <style>
                rect { fill: blue; }
                .my-class { fill: green; }
                #my-id { fill: red; }
            </style>
            <rect class="my-class" id="my-id"/>
        </svg>''')

        service = StyleService(svg)
        rect = svg.find('.//{http://www.w3.org/2000/svg}rect')
        style = service.compute_style(rect)

        # ID selector (highest CSS specificity) should win
        assert style['fill'] == 'red'

    def test_css_inheritance(self):
        """Test CSS property inheritance."""
        svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <g style="fill: red; opacity: 0.5">
                <rect/>
            </g>
        </svg>''')

        service = StyleService(svg)
        g = svg.find('.//{http://www.w3.org/2000/svg}g')
        rect = svg.find('.//{http://www.w3.org/2000/svg}rect')

        parent_style = service.compute_style(g)
        child_style = service.compute_style(rect, parent_style)

        # Fill should inherit
        assert child_style['fill'] == 'red'
        # Opacity should NOT inherit (per CSS spec)
        assert 'opacity' not in child_style

    def test_css_inheritance_override(self):
        """Test CSS inheritance with child override."""
        svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <g style="fill: red; stroke: blue">
                <rect fill="green"/>
            </g>
        </svg>''')

        service = StyleService(svg)
        g = svg.find('.//{http://www.w3.org/2000/svg}g')
        rect = svg.find('.//{http://www.w3.org/2000/svg}rect')

        parent_style = service.compute_style(g)
        child_style = service.compute_style(rect, parent_style)

        # Fill should be overridden
        assert child_style['fill'] == 'green'
        # Stroke should inherit
        assert child_style['stroke'] == 'blue'

    def test_source_order_tie_breaking(self):
        """Test source order tie-breaking for equal specificity."""
        svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <style>
                .class1 { fill: blue; }
                .class2 { fill: red; }
            </style>
            <rect class="class1 class2"/>
        </svg>''')

        service = StyleService(svg)
        rect = svg.find('.//{http://www.w3.org/2000/svg}rect')
        style = service.compute_style(rect)

        # Later rule (.class2) should win due to source order
        assert style['fill'] == 'red'


class TestStyleServiceConvenienceMethods:
    """Test StyleService convenience methods."""

    def test_fill_method(self):
        """Test fill convenience method."""
        service = StyleService()

        style = {'fill': 'red'}
        assert service.fill(style) == 'red'

        style = {}
        assert service.fill(style, 'blue') == 'blue'
        assert service.fill(style) is None

    def test_font_size_method(self):
        """Test font_size convenience method with units."""
        service = StyleService()

        # Points
        style = {'font-size': '14pt'}
        assert service.font_size(style) == 14.0

        # Pixels (96 DPI conversion)
        style = {'font-size': '16px'}
        assert service.font_size(style) == 12.0  # 16 * 0.75

        # No unit (assumes points)
        style = {'font-size': '18'}
        assert service.font_size(style) == 18.0

        # Invalid
        style = {'font-size': 'invalid'}
        assert service.font_size(style, 12.0) == 12.0

        # Not set
        style = {}
        assert service.font_size(style, 10.0) == 10.0

    def test_stroke_width_method(self):
        """Test stroke_width convenience method."""
        service = StyleService()

        style = {'stroke-width': '2px'}
        assert service.stroke_width(style) == '2px'

        style = {}
        assert service.stroke_width(style) == '1'  # Default

    def test_is_visible_method(self):
        """Test is_visible convenience method."""
        service = StyleService()

        # Default (visible)
        style = {}
        assert service.is_visible(style) is True

        # Explicitly visible
        style = {'display': 'inline', 'visibility': 'visible'}
        assert service.is_visible(style) is True

        # Hidden by display
        style = {'display': 'none'}
        assert service.is_visible(style) is False

        # Hidden by visibility
        style = {'visibility': 'hidden'}
        assert service.is_visible(style) is False


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    def test_illustrator_export_pattern(self):
        """Test typical Illustrator export with .cls- classes."""
        svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <style>
                .cls-1 { fill: #ff6b35; stroke: #1e3a8a; stroke-width: 2; }
                .cls-2 { fill: #10b981; }
                .cls-3 { opacity: 0.8; }
            </style>
            <rect class="cls-1 cls-3" width="100" height="50"/>
            <circle class="cls-2" r="25"/>
        </svg>''')

        service = StyleService(svg)

        rect = svg.find('.//{http://www.w3.org/2000/svg}rect')
        rect_style = service.compute_style(rect)

        circle = svg.find('.//{http://www.w3.org/2000/svg}circle')
        circle_style = service.compute_style(circle)

        # Rectangle should have combined styles
        assert rect_style['fill'] == '#ff6b35'
        assert rect_style['stroke'] == '#1e3a8a'
        assert rect_style['stroke-width'] == '2'
        assert rect_style['opacity'] == '0.8'

        # Circle should have only its class
        assert circle_style['fill'] == '#10b981'
        assert 'stroke' not in circle_style

    def test_nested_inheritance_chain(self):
        """Test inheritance through nested elements."""
        svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <g style="fill: blue; stroke: red">
                <g class="inner" style="fill: green">
                    <rect/>
                </g>
            </g>
            <style>
                .inner { stroke-width: 3; }
            </style>
        </svg>''')

        service = StyleService(svg)

        outer_g = svg.find('.//{http://www.w3.org/2000/svg}g')
        inner_g = svg.find('.//{http://www.w3.org/2000/svg}g[@class="inner"]')
        rect = svg.find('.//{http://www.w3.org/2000/svg}rect')

        # Compute styles through inheritance chain
        outer_style = service.compute_style(outer_g)
        inner_style = service.compute_style(inner_g, outer_style)
        rect_style = service.compute_style(rect, inner_style)

        # Rect should have final computed style
        assert rect_style['fill'] == 'green'  # Overridden by inner g
        assert rect_style['stroke'] == 'red'   # Inherited from outer g
        assert rect_style['stroke-width'] == '3'  # From CSS rule

    def test_real_world_corporate_logo(self):
        """Test realistic corporate logo pattern."""
        svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <style>
                .brand-primary { fill: #1f2937; }
                .brand-secondary { fill: #3b82f6; }
                .logo-text { font-family: 'Arial Black', sans-serif; font-size: 24pt; }
                #company-name { text-anchor: middle; }
            </style>
            <g class="logo">
                <rect class="brand-primary" width="100" height="20"/>
                <circle class="brand-secondary" r="10"/>
                <text id="company-name" class="logo-text brand-primary">ACME</text>
            </g>
        </svg>''')

        service = StyleService(svg)

        rect = svg.find('.//{http://www.w3.org/2000/svg}rect')
        circle = svg.find('.//{http://www.w3.org/2000/svg}circle')
        text = svg.find('.//{http://www.w3.org/2000/svg}text')

        rect_style = service.compute_style(rect)
        circle_style = service.compute_style(circle)
        text_style = service.compute_style(text)

        # Verify brand colors
        assert rect_style['fill'] == '#1f2937'
        assert circle_style['fill'] == '#3b82f6'
        assert text_style['fill'] == '#1f2937'

        # Verify text styling
        assert text_style['font-family'] == "'Arial Black', sans-serif"
        assert text_style['text-anchor'] == 'middle'

        # ID selector should have highest specificity
        assert 'text-anchor' in text_style

    def test_performance_with_many_rules(self):
        """Test performance with large number of CSS rules."""
        # Generate many CSS rules
        css_rules = []
        for i in range(100):
            css_rules.append(f'.class-{i} {{ fill: hsl({i * 3.6}, 70%, 50%); }}')

        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg">
            <style>{' '.join(css_rules)}</style>
            <rect class="class-50"/>
        </svg>'''

        svg = ET.fromstring(svg_content)
        service = StyleService(svg)

        # Should handle many rules efficiently
        assert len(service.rules) == 100

        rect = svg.find('.//{http://www.w3.org/2000/svg}rect')
        style = service.compute_style(rect)

        # Should find the correct matching rule
        assert 'fill' in style
        assert 'hsl(' in style['fill']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
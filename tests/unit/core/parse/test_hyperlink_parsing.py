#!/usr/bin/env python3
"""
Unit tests for SVG hyperlink parsing functionality.

Tests the hyperlink-related parsing methods added to SVGParser:
- _convert_hyperlink_to_ir()
- _extract_hyperlink_tooltip()
- SVG <a> element parsing and metadata attachment
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

from core.parse.parser import SVGParser
from core.pipeline.hyperlinks import HyperlinkSpec
from core.pipeline.navigation import NavigationSpec, NavKind, JumpAction


class TestSVGHyperlinkParsing:
    """Test SVG hyperlink parsing functionality in SVGParser."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for testing."""
        return SVGParser(enable_normalization=False)  # Disable normalization for cleaner tests

    @pytest.fixture
    def basic_hyperlink_svg(self):
        """Create basic SVG with hyperlink."""
        return '''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
            <a href="https://example.com">
                <rect x="0" y="0" width="100" height="50" fill="blue"/>
            </a>
        </svg>'''

    @pytest.fixture
    def hyperlink_with_tooltip_svg(self):
        """Create SVG with hyperlink and tooltip."""
        return '''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
            <a href="mailto:contact@example.com">
                <title>Send us an email</title>
                <circle cx="50" cy="50" r="25" fill="red"/>
            </a>
        </svg>'''

    @pytest.fixture
    def internal_link_svg(self):
        """Create SVG with internal slide link."""
        return '''<svg xmlns="http://www.w3.org/2000/svg">
            <a href="slide:3">
                <title>Go to slide 3</title>
                <text x="10" y="20">Next slide</text>
            </a>
        </svg>'''

    @pytest.fixture
    def xlink_href_svg(self):
        """Create SVG using xlink:href attribute."""
        return '''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
            <a xlink:href="https://example.com">
                <ellipse cx="75" cy="75" rx="30" ry="20" fill="green"/>
            </a>
        </svg>'''

    @pytest.fixture
    def multiple_children_svg(self):
        """Create SVG with hyperlink containing multiple child elements."""
        return '''<svg xmlns="http://www.w3.org/2000/svg">
            <a href="https://example.com">
                <title>Visit our website</title>
                <rect x="0" y="0" width="50" height="20" fill="blue"/>
                <text x="5" y="15">Click me</text>
                <circle cx="60" cy="10" r="8" fill="red"/>
            </a>
        </svg>'''

    @pytest.fixture
    def nested_groups_svg(self):
        """Create SVG with hyperlink containing nested groups."""
        return '''<svg xmlns="http://www.w3.org/2000/svg">
            <a href="tel:+1-555-0123">
                <title>Call us</title>
                <g transform="translate(10,10)">
                    <rect x="0" y="0" width="40" height="15" fill="yellow"/>
                    <text x="5" y="12">Call</text>
                </g>
            </a>
        </svg>'''

    def test_extract_hyperlink_tooltip_basic(self, parser):
        """Test _extract_hyperlink_tooltip with basic title element."""
        svg_xml = '''<a xmlns="http://www.w3.org/2000/svg">
            <title>Visit our website</title>
            <rect x="0" y="0" width="100" height="50"/>
        </a>'''

        element = ET.fromstring(svg_xml)
        tooltip = parser._extract_hyperlink_tooltip(element)

        assert tooltip == "Visit our website"

    def test_extract_hyperlink_tooltip_no_title(self, parser):
        """Test _extract_hyperlink_tooltip with no title element."""
        svg_xml = '''<a xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="100" height="50"/>
        </a>'''

        element = ET.fromstring(svg_xml)
        tooltip = parser._extract_hyperlink_tooltip(element)

        assert tooltip is None

    def test_extract_hyperlink_tooltip_empty_title(self, parser):
        """Test _extract_hyperlink_tooltip with empty title element."""
        svg_xml = '''<a xmlns="http://www.w3.org/2000/svg">
            <title>   </title>
            <rect x="0" y="0" width="100" height="50"/>
        </a>'''

        element = ET.fromstring(svg_xml)
        tooltip = parser._extract_hyperlink_tooltip(element)

        assert tooltip is None

    def test_extract_hyperlink_tooltip_whitespace_normalization(self, parser):
        """Test tooltip text normalization."""
        svg_xml = '''<a xmlns="http://www.w3.org/2000/svg">
            <title>  Visit our website  </title>
            <rect x="0" y="0" width="100" height="50"/>
        </a>'''

        element = ET.fromstring(svg_xml)
        tooltip = parser._extract_hyperlink_tooltip(element)

        assert tooltip == "Visit our website"

    def test_convert_hyperlink_to_ir_basic(self, parser):
        """Test _convert_hyperlink_to_ir with basic hyperlink."""
        svg_xml = '''<a xmlns="http://www.w3.org/2000/svg" href="https://example.com">
            <rect x="0" y="0" width="100" height="50" fill="blue"/>
        </a>'''

        element = ET.fromstring(svg_xml)
        ir_elements = []

        parser._convert_hyperlink_to_ir(element, ir_elements)

        # Should have created one IR element (rect)
        assert len(ir_elements) == 1
        assert ir_elements[0].hyperlink is not None

        hyperlink = ir_elements[0].hyperlink
        assert hyperlink.href == "https://example.com"
        assert hyperlink.tooltip is None

    def test_convert_hyperlink_to_ir_with_tooltip(self, parser):
        """Test _convert_hyperlink_to_ir with tooltip."""
        svg_xml = '''<a xmlns="http://www.w3.org/2000/svg" href="mailto:test@example.com">
            <title>Send email</title>
            <circle cx="50" cy="50" r="25" fill="red"/>
        </a>'''

        element = ET.fromstring(svg_xml)
        ir_elements = []

        parser._convert_hyperlink_to_ir(element, ir_elements)

        # Should have created one IR element (circle)
        assert len(ir_elements) == 1
        assert ir_elements[0].hyperlink is not None

        hyperlink = ir_elements[0].hyperlink
        assert hyperlink.href == "mailto:test@example.com"
        assert hyperlink.tooltip == "Send email"

    def test_convert_hyperlink_to_ir_xlink_href(self, parser):
        """Test _convert_hyperlink_to_ir with xlink:href attribute."""
        svg_xml = '''<a xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="https://example.com">
            <ellipse cx="75" cy="75" rx="30" ry="20" fill="green"/>
        </a>'''

        element = ET.fromstring(svg_xml)
        ir_elements = []

        parser._convert_hyperlink_to_ir(element, ir_elements)

        # Should have created one IR element (ellipse)
        assert len(ir_elements) == 1
        assert ir_elements[0].hyperlink is not None

        hyperlink = ir_elements[0].hyperlink
        assert hyperlink.href == "https://example.com"

    def test_convert_hyperlink_to_ir_no_href(self, parser):
        """Test _convert_hyperlink_to_ir with no href attribute."""
        svg_xml = '''<a xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="100" height="50" fill="blue"/>
        </a>'''

        element = ET.fromstring(svg_xml)
        ir_elements = []

        parser._convert_hyperlink_to_ir(element, ir_elements)

        # Should have created IR element but without hyperlink metadata
        assert len(ir_elements) == 1
        assert ir_elements[0].hyperlink is None

    def test_convert_hyperlink_to_ir_invalid_href(self, parser):
        """Test _convert_hyperlink_to_ir with invalid href."""
        svg_xml = '''<a xmlns="http://www.w3.org/2000/svg" href="slide:0">
            <rect x="0" y="0" width="100" height="50" fill="blue"/>
        </a>'''

        element = ET.fromstring(svg_xml)
        ir_elements = []

        parser._convert_hyperlink_to_ir(element, ir_elements)

        # Should have created IR element but without hyperlink metadata
        assert len(ir_elements) == 1
        assert ir_elements[0].hyperlink is None

    def test_convert_hyperlink_to_ir_multiple_children(self, parser):
        """Test _convert_hyperlink_to_ir with multiple child elements."""
        svg_xml = '''<a xmlns="http://www.w3.org/2000/svg" href="https://example.com">
            <title>Visit website</title>
            <rect x="0" y="0" width="50" height="20" fill="blue"/>
            <circle cx="60" cy="10" r="8" fill="red"/>
        </a>'''

        element = ET.fromstring(svg_xml)
        ir_elements = []

        parser._convert_hyperlink_to_ir(element, ir_elements)

        # Should have created two IR elements (rect and circle)
        assert len(ir_elements) == 2

        # Both should have hyperlink metadata
        for ir_element in ir_elements:
            assert ir_element.hyperlink is not None
            hyperlink = ir_element.hyperlink
            assert hyperlink.href == "https://example.com"
            assert hyperlink.tooltip == "Visit website"

    def test_parse_svg_with_hyperlinks_integration(self, parser, basic_hyperlink_svg):
        """Test full SVG parsing integration with hyperlinks."""
        parse_result = parser.parse(basic_hyperlink_svg)

        assert parse_result.success
        assert parse_result.svg_root is not None

    def test_parse_to_ir_with_hyperlinks_integration(self, parser, basic_hyperlink_svg):
        """Test parse_to_ir integration with hyperlinks."""
        scene, parse_result = parser.parse_to_ir(basic_hyperlink_svg)

        assert parse_result.success
        assert scene is not None
        assert len(scene) > 0

        # Check if any elements have hyperlink metadata
        hyperlinked_elements = [elem for elem in scene if elem.hyperlink is not None]
        assert len(hyperlinked_elements) > 0

        # Verify hyperlink data
        hyperlink = hyperlinked_elements[0].hyperlink
        assert hyperlink.href == "https://example.com"

    def test_parse_hyperlink_with_tooltip_integration(self, parser, hyperlink_with_tooltip_svg):
        """Test parsing hyperlink with tooltip through full pipeline."""
        scene, parse_result = parser.parse_to_ir(hyperlink_with_tooltip_svg)

        assert parse_result.success
        assert scene is not None

        # Find hyperlinked elements
        hyperlinked_elements = [elem for elem in scene if elem.hyperlink is not None]
        assert len(hyperlinked_elements) > 0

        # Verify hyperlink data with tooltip
        hyperlink = hyperlinked_elements[0].hyperlink
        assert hyperlink.href == "mailto:contact@example.com"
        assert hyperlink.tooltip == "Send us an email"

    def test_parse_internal_slide_link_integration(self, parser, internal_link_svg):
        """Test parsing internal slide links."""
        scene, parse_result = parser.parse_to_ir(internal_link_svg)

        assert parse_result.success
        assert scene is not None

        # Find hyperlinked elements
        hyperlinked_elements = [elem for elem in scene if elem.hyperlink is not None]
        assert len(hyperlinked_elements) > 0

        # Verify internal slide link
        hyperlink = hyperlinked_elements[0].hyperlink
        assert hyperlink.href == "slide:3"
        assert hyperlink.tooltip == "Go to slide 3"
        assert hyperlink.is_internal_slide_link()
        assert hyperlink.get_slide_number() == 3

    def test_parse_xlink_href_integration(self, parser, xlink_href_svg):
        """Test parsing xlink:href attributes."""
        scene, parse_result = parser.parse_to_ir(xlink_href_svg)

        assert parse_result.success
        assert scene is not None

        # Find hyperlinked elements
        hyperlinked_elements = [elem for elem in scene if elem.hyperlink is not None]
        assert len(hyperlinked_elements) > 0

        # Verify xlink:href parsing
        hyperlink = hyperlinked_elements[0].hyperlink
        assert hyperlink.href == "https://example.com"
        assert hyperlink.is_external_link()

    def test_parse_multiple_children_integration(self, parser, multiple_children_svg):
        """Test parsing hyperlinks with multiple child elements."""
        scene, parse_result = parser.parse_to_ir(multiple_children_svg)

        assert parse_result.success
        assert scene is not None

        # Find hyperlinked elements
        hyperlinked_elements = [elem for elem in scene if elem.hyperlink is not None]
        assert len(hyperlinked_elements) >= 2  # Should have rect, text, and circle

        # All should have the same hyperlink data
        for element in hyperlinked_elements:
            hyperlink = element.hyperlink
            assert hyperlink.href == "https://example.com"
            assert hyperlink.tooltip == "Visit our website"

    def test_parse_nested_groups_integration(self, parser, nested_groups_svg):
        """Test parsing hyperlinks with nested groups."""
        scene, parse_result = parser.parse_to_ir(nested_groups_svg)

        assert parse_result.success
        assert scene is not None

        # Find hyperlinked elements (groups should preserve hyperlink metadata)
        hyperlinked_elements = [elem for elem in scene if elem.hyperlink is not None]
        assert len(hyperlinked_elements) > 0

        # Verify hyperlink data
        hyperlink = hyperlinked_elements[0].hyperlink
        assert hyperlink.href == "tel:+1-555-0123"
        assert hyperlink.tooltip == "Call us"

    def test_hyperlink_metadata_preservation(self, parser):
        """Test that hyperlink metadata is properly preserved on IR elements."""
        svg_xml = '''<svg xmlns="http://www.w3.org/2000/svg">
            <a href="https://example.com">
                <title>Test link</title>
                <rect x="0" y="0" width="100" height="50" fill="blue"/>
            </a>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_xml)

        assert parse_result.success
        assert len(scene) > 0

        # Find the hyperlinked element
        hyperlinked_element = None
        for element in scene:
            if element.hyperlink is not None:
                hyperlinked_element = element
                break

        assert hyperlinked_element is not None

        # Verify metadata is a proper HyperlinkSpec
        metadata = hyperlinked_element.hyperlink
        assert isinstance(metadata, HyperlinkSpec)
        assert metadata.href == "https://example.com"
        assert metadata.tooltip == "Test link"
        assert metadata.visited is True  # Default

    def test_edge_cases_empty_hyperlink(self, parser):
        """Test edge cases with empty or malformed hyperlinks."""
        svg_xml = '''<svg xmlns="http://www.w3.org/2000/svg">
            <a href="">
                <rect x="0" y="0" width="100" height="50" fill="blue"/>
            </a>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_xml)

        assert parse_result.success
        assert len(scene) > 0

        # Should create element but without hyperlink metadata
        rect_element = scene[0]
        assert rect_element.hyperlink is None

    def test_edge_cases_no_children(self, parser):
        """Test hyperlink elements with no child elements."""
        svg_xml = '''<svg xmlns="http://www.w3.org/2000/svg">
            <a href="https://example.com">
                <title>Empty link</title>
            </a>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_xml)

        assert parse_result.success
        # Should not create any IR elements since no drawable content
        assert len(scene) == 0

    def test_hyperlink_type_detection_integration(self, parser):
        """Test that different hyperlink types are properly detected."""
        svg_xml = '''<svg xmlns="http://www.w3.org/2000/svg">
            <a href="mailto:test@example.com">
                <rect x="0" y="0" width="50" height="25" fill="blue"/>
            </a>
            <a href="tel:+1-555-0123">
                <rect x="60" y="0" width="50" height="25" fill="red"/>
            </a>
            <a href="file:///path/to/file.pdf">
                <rect x="120" y="0" width="50" height="25" fill="green"/>
            </a>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_xml)

        assert parse_result.success
        assert len(scene) >= 3

        # Find all hyperlinked elements
        hyperlinked_elements = [elem for elem in scene if elem.hyperlink is not None]
        assert len(hyperlinked_elements) == 3

        # Check that different link types are properly identified
        link_types = [elem.hyperlink.get_link_type().value for elem in hyperlinked_elements]
        assert "external_mailto" in link_types
        assert "external_tel" in link_types
        assert "external_file" in link_types


class TestSVGNavigationAttributeParsing:
    """Test enhanced navigation attribute parsing functionality."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for testing."""
        return SVGParser(enable_normalization=False)

    @pytest.fixture
    def slide_navigation_svg(self):
        """Create SVG with data-slide navigation."""
        return '''<svg xmlns="http://www.w3.org/2000/svg">
            <a data-slide="5">
                <title>Go to slide 5</title>
                <rect x="0" y="0" width="100" height="50" fill="blue"/>
            </a>
        </svg>'''

    @pytest.fixture
    def action_navigation_svg(self):
        """Create SVG with data-jump navigation."""
        return '''<svg xmlns="http://www.w3.org/2000/svg">
            <a data-jump="nextslide">
                <title>Next slide</title>
                <circle cx="50" cy="50" r="25" fill="green"/>
            </a>
        </svg>'''

    @pytest.fixture
    def bookmark_navigation_svg(self):
        """Create SVG with data-bookmark navigation."""
        return '''<svg xmlns="http://www.w3.org/2000/svg">
            <a data-bookmark="intro">
                <title>Jump to intro section</title>
                <text x="10" y="30">Intro</text>
            </a>
        </svg>'''

    @pytest.fixture
    def custom_show_navigation_svg(self):
        """Create SVG with data-custom-show navigation."""
        return '''<svg xmlns="http://www.w3.org/2000/svg">
            <a data-custom-show="SalesDeck">
                <title>Sales presentation</title>
                <rect x="0" y="0" width="80" height="40" fill="red"/>
            </a>
        </svg>'''

    @pytest.fixture
    def mixed_navigation_svg(self):
        """Create SVG with mixed navigation types."""
        return '''<svg xmlns="http://www.w3.org/2000/svg">
            <a href="https://example.com">
                <title>External link</title>
                <rect x="10" y="10" width="50" height="25" fill="blue"/>
            </a>
            <a data-slide="3">
                <title>Slide jump</title>
                <rect x="70" y="10" width="50" height="25" fill="green"/>
            </a>
            <a data-jump="previousslide">
                <title>Previous slide</title>
                <rect x="130" y="10" width="50" height="25" fill="red"/>
            </a>
        </svg>'''

    def test_extract_navigation_attributes(self, parser):
        """Test extraction of navigation data attributes."""
        svg_content = '''<a data-slide="5" data-bookmark="intro" href="https://example.com">
            <rect x="0" y="0" width="100" height="50"/>
        </a>'''

        element = ET.fromstring(svg_content)
        attrs = parser._extract_navigation_attributes(element)

        assert attrs['data-slide'] == '5'
        assert attrs['data-bookmark'] == 'intro'
        assert 'href' not in attrs  # href is not a data attribute

    def test_parse_data_slide_navigation(self, parser, slide_navigation_svg):
        """Test parsing of data-slide navigation."""
        scene, parse_result = parser.parse_to_ir(slide_navigation_svg)

        assert parse_result.success
        assert len(scene) > 0

        # Check for navigation context
        navigation_elements = [elem for elem in scene if hasattr(parser, '_current_navigation')]

        # Check backward compatibility - should also set hyperlink
        hyperlinked_elements = [elem for elem in scene if hasattr(elem, 'hyperlink') and elem.hyperlink is not None]
        assert len(hyperlinked_elements) > 0

        hyperlink = hyperlinked_elements[0].hyperlink
        assert hyperlink.href == "slide:5"
        assert hyperlink.tooltip == "Go to slide 5"

    def test_parse_data_jump_navigation(self, parser, action_navigation_svg):
        """Test parsing of data-jump navigation."""
        scene, parse_result = parser.parse_to_ir(action_navigation_svg)

        assert parse_result.success
        assert len(scene) > 0

        # Action navigation doesn't create backward-compatible hyperlinks
        # since it's PowerPoint-specific

    def test_parse_data_bookmark_navigation(self, parser, bookmark_navigation_svg):
        """Test parsing of data-bookmark navigation."""
        scene, parse_result = parser.parse_to_ir(bookmark_navigation_svg)

        assert parse_result.success
        assert len(scene) > 0

    def test_parse_data_custom_show_navigation(self, parser, custom_show_navigation_svg):
        """Test parsing of data-custom-show navigation."""
        scene, parse_result = parser.parse_to_ir(custom_show_navigation_svg)

        assert parse_result.success
        assert len(scene) > 0

    def test_mixed_navigation_types(self, parser, mixed_navigation_svg):
        """Test parsing of mixed navigation types in one SVG."""
        scene, parse_result = parser.parse_to_ir(mixed_navigation_svg)

        assert parse_result.success
        assert len(scene) >= 3

        # Check backward compatibility - external and slide links should create hyperlinks
        hyperlinked_elements = [elem for elem in scene if hasattr(elem, 'hyperlink') and elem.hyperlink is not None]
        assert len(hyperlinked_elements) >= 2  # External and slide links

    def test_attribute_precedence(self, parser):
        """Test that data attributes take precedence over href."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <a href="https://example.com" data-slide="7">
                <title>Should be slide navigation</title>
                <rect x="0" y="0" width="100" height="50"/>
            </a>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert parse_result.success
        assert len(scene) > 0

        # Should create slide navigation, not external link
        hyperlinked_elements = [elem for elem in scene if hasattr(elem, 'hyperlink') and elem.hyperlink is not None]
        assert len(hyperlinked_elements) > 0

        hyperlink = hyperlinked_elements[0].hyperlink
        assert hyperlink.href == "slide:7"  # data-slide takes precedence
        assert hyperlink.tooltip == "Should be slide navigation"

    def test_invalid_navigation_attributes(self, parser):
        """Test handling of invalid navigation attributes."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <a data-slide="invalid" data-jump="unknown">
                <rect x="0" y="0" width="100" height="50"/>
            </a>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert parse_result.success
        assert len(scene) > 0

        # Invalid navigation should not create hyperlinks
        hyperlinked_elements = [elem for elem in scene if hasattr(elem, 'hyperlink') and elem.hyperlink is not None]
        assert len(hyperlinked_elements) == 0

    def test_navigation_context_propagation(self, parser):
        """Test that navigation context propagates to child elements."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <a data-slide="3">
                <g>
                    <rect x="0" y="0" width="50" height="25"/>
                    <text x="5" y="15">Click</text>
                </g>
            </a>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert parse_result.success
        assert len(scene) > 0

        # Check that elements have navigation context
        hyperlinked_elements = [elem for elem in scene if hasattr(elem, 'hyperlink') and elem.hyperlink is not None]
        assert len(hyperlinked_elements) > 0

    def test_backward_compatibility_maintained(self, parser):
        """Test that existing href-based parsing still works."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <a href="https://example.com">
                <title>External link</title>
                <rect x="0" y="0" width="100" height="50"/>
            </a>
            <a href="slide:5">
                <title>Slide link</title>
                <circle cx="50" cy="50" r="25"/>
            </a>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert parse_result.success
        assert len(scene) >= 2

        hyperlinked_elements = [elem for elem in scene if hasattr(elem, 'hyperlink') and elem.hyperlink is not None]
        assert len(hyperlinked_elements) >= 2

        # Check that both types are parsed correctly
        hrefs = [elem.hyperlink.href for elem in hyperlinked_elements]
        assert "https://example.com" in hrefs
        assert "slide:5" in hrefs
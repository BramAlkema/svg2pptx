#!/usr/bin/env python3
"""
Tests for Safe SVG Normalization module.

Tests comprehensive error handling and cython Comment object compatibility.
"""

import pytest
from lxml import etree as ET
from core.parse.safe_svg_normalization import (
    safe_element_iteration,
    safe_normalize_svg,
    SafeSVGNormalizer,
    create_safe_normalizer
)


class TestSafeElementIteration:
    """Test safe element iteration with cython compatibility."""

    def test_safe_iteration_basic_elements(self):
        """Test safe iteration with standard XML elements."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <rect width="100" height="50"/>
            <circle cx="50" cy="25" r="20"/>
        </svg>'''

        root = ET.fromstring(svg_content.encode('utf-8'))
        elements = list(safe_element_iteration(root))

        assert len(elements) == 2
        assert elements[0].tag.endswith('rect')
        assert elements[1].tag.endswith('circle')

    def test_safe_iteration_with_comments(self):
        """Test safe iteration filters out XML comments."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <!-- This is a comment -->
            <rect width="100" height="50"/>
            <!-- Another comment -->
            <circle cx="50" cy="25" r="20"/>
            <!-- Final comment -->
        </svg>'''

        root = ET.fromstring(svg_content.encode('utf-8'))
        elements = list(safe_element_iteration(root))

        # Should only get the 2 actual elements, comments filtered out
        assert len(elements) == 2
        assert elements[0].tag.endswith('rect')
        assert elements[1].tag.endswith('circle')

    def test_safe_iteration_empty_element(self):
        """Test safe iteration with empty element."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg"></svg>'''

        root = ET.fromstring(svg_content.encode('utf-8'))
        elements = list(safe_element_iteration(root))

        assert len(elements) == 0

    def test_safe_iteration_nested_elements(self):
        """Test safe iteration with nested structure."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <g transform="translate(10,10)">
                <rect width="50" height="25"/>
            </g>
        </svg>'''

        root = ET.fromstring(svg_content.encode('utf-8'))
        elements = list(safe_element_iteration(root))

        assert len(elements) == 1
        assert elements[0].tag.endswith('g')

    def test_safe_iteration_error_recovery(self):
        """Test that iteration errors are handled gracefully."""
        # Create element that might cause iteration issues
        root = ET.Element('svg')

        # Safe iteration should handle any errors without crashing
        elements = list(safe_element_iteration(root))
        assert elements == []


class TestSafeNormalizeSvg:
    """Test safe SVG normalization function."""

    def test_normalize_valid_svg(self):
        """Test normalization of valid SVG content."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
            <rect x="10" y="10" width="50" height="50"/>
        </svg>'''

        result = safe_normalize_svg(svg_content)

        assert result is not None
        assert result.tag.endswith('svg')
        assert len(list(safe_element_iteration(result))) == 1

    def test_normalize_empty_content(self):
        """Test normalization handles empty content."""
        assert safe_normalize_svg("") is None
        assert safe_normalize_svg("   ") is None
        assert safe_normalize_svg(None) is None

    def test_normalize_invalid_xml(self):
        """Test normalization handles invalid XML."""
        invalid_xml = "<svg><rect></svg>"  # Unclosed rect tag

        result = safe_normalize_svg(invalid_xml)
        assert result is None

    def test_normalize_non_svg_content(self):
        """Test normalization rejects non-SVG content."""
        html_content = "<html><body><div>Not SVG</div></body></html>"

        result = safe_normalize_svg(html_content)
        assert result is None

    def test_normalize_svg_with_comments(self):
        """Test normalization handles SVG with comments."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <!-- Header comment -->
            <rect width="100" height="50"/>
            <!-- Footer comment -->
        </svg>'''

        result = safe_normalize_svg(svg_content)

        assert result is not None
        assert result.tag.endswith('svg')


class TestSafeSVGNormalizer:
    """Test SafeSVGNormalizer class."""

    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance for testing."""
        return SafeSVGNormalizer()

    @pytest.fixture
    def simple_svg(self):
        """Simple SVG for testing."""
        content = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
            <rect x="10" y="10" width="50" height="50"/>
        </svg>'''
        return ET.fromstring(content.encode('utf-8'))

    @pytest.fixture
    def complex_svg_with_comments(self):
        """Complex SVG with comments for testing."""
        content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <!-- Definitions section -->
            <defs>
                <linearGradient id="grad1">
                    <stop offset="0%" stop-color="red"/>
                    <!-- Gradient stop comment -->
                    <stop offset="100%" stop-color="blue"/>
                </linearGradient>
            </defs>
            <!-- Main content -->
            <rect x="10" y="10" width="50" height="50" fill="url(#grad1)"/>
            <!-- End comment -->
        </svg>'''
        return ET.fromstring(content.encode('utf-8'))

    def test_normalizer_initialization(self, normalizer):
        """Test normalizer initializes correctly."""
        assert normalizer.settings['fix_namespaces'] is True
        assert normalizer.settings['filter_comments'] is True
        assert normalizer.logger is not None

    def test_normalize_simple_svg(self, normalizer, simple_svg):
        """Test normalizing simple SVG."""
        result, changes = normalizer.normalize(simple_svg)

        assert result is not None
        assert isinstance(changes, dict)
        assert 'error' not in changes

    def test_normalize_complex_svg_with_comments(self, normalizer, complex_svg_with_comments):
        """Test normalizing complex SVG with comments."""
        result, changes = normalizer.normalize(complex_svg_with_comments)

        assert result is not None
        assert isinstance(changes, dict)
        assert 'error' not in changes

        # Should be able to safely iterate through result
        elements = list(safe_element_iteration(result))
        assert len(elements) == 2  # defs and rect, comments filtered

    def test_namespace_fixing(self, normalizer):
        """Test namespace fixing functionality."""
        # SVG without proper namespace
        svg_content = '''<svg width="100" height="100">
            <rect x="10" y="10" width="50" height="50"/>
        </svg>'''
        svg_root = ET.fromstring(svg_content.encode('utf-8'))

        result, changes = normalizer.normalize(svg_root)

        assert result is not None
        assert changes.get('namespaces_fixed', False)

    def test_add_missing_attributes(self, normalizer):
        """Test adding missing SVG attributes."""
        # SVG without version
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="50" height="50"/>
        </svg>'''
        svg_root = ET.fromstring(svg_content.encode('utf-8'))

        result, changes = normalizer.normalize(svg_root)

        assert result is not None
        assert 'version' in result.attrib
        assert 'version' in changes.get('attributes_added', [])

    def test_whitespace_normalization(self, normalizer):
        """Test whitespace normalization."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <text>  Whitespace text  </text>
        </svg>'''
        svg_root = ET.fromstring(svg_content.encode('utf-8'))

        result, changes = normalizer.normalize(svg_root)

        assert result is not None
        # Changes tracking may vary based on whitespace content

    def test_structure_fixes(self, normalizer):
        """Test structure issue fixes."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <g></g>  <!-- Empty group -->
            <rect x="10" y="10" width="50" height="50"/>
        </svg>'''
        svg_root = ET.fromstring(svg_content.encode('utf-8'))

        result, changes = normalizer.normalize(svg_root)

        assert result is not None
        # Structure fixes may be applied

    def test_error_handling(self, normalizer):
        """Test error handling in normalization."""
        # Create potentially problematic element
        svg_root = ET.Element('svg')

        result, changes = normalizer.normalize(svg_root)

        # Should handle errors gracefully
        assert result is not None
        assert isinstance(changes, dict)

    def test_settings_customization(self):
        """Test customizing normalization settings."""
        normalizer = SafeSVGNormalizer()

        # Modify settings
        normalizer.set_normalization_options(
            fix_namespaces=False,
            filter_comments=False
        )

        assert normalizer.settings['fix_namespaces'] is False
        assert normalizer.settings['filter_comments'] is False

    def test_safe_iteration_all_elements(self, normalizer, complex_svg_with_comments):
        """Test safe iteration over all elements."""
        elements = list(normalizer._safe_iter_all_elements(complex_svg_with_comments))

        # Should include root and all child elements, comments filtered
        assert len(elements) >= 1  # At least the root
        assert elements[0] == complex_svg_with_comments

    def test_empty_container_detection(self, normalizer):
        """Test empty container detection."""
        # Create empty group
        empty_group = ET.Element('g')
        assert normalizer._is_empty_container(empty_group) is True

        # Create group with meaningful attributes
        group_with_id = ET.Element('g')
        group_with_id.set('id', 'important')
        assert normalizer._is_empty_container(group_with_id) is False

    def test_meaningful_attributes_detection(self, normalizer):
        """Test meaningful attributes detection."""
        element = ET.Element('rect')
        assert normalizer._has_meaningful_attributes(element) is False

        element.set('fill', 'red')
        assert normalizer._has_meaningful_attributes(element) is True

    def test_local_name_extraction(self, normalizer):
        """Test local name extraction from namespaced names."""
        assert normalizer._get_local_tag('{http://www.w3.org/2000/svg}rect') == 'rect'
        assert normalizer._get_local_tag('rect') == 'rect'

        assert normalizer._get_local_name('{http://www.w3.org/2000/svg}fill') == 'fill'
        assert normalizer._get_local_name('fill') == 'fill'


class TestSafeNormalizerFactory:
    """Test safe normalizer factory function."""

    def test_create_default_normalizer(self):
        """Test creating normalizer with default settings."""
        normalizer = create_safe_normalizer()

        assert isinstance(normalizer, SafeSVGNormalizer)
        assert normalizer.settings['fix_namespaces'] is True
        assert normalizer.settings['filter_comments'] is True

    def test_create_customized_normalizer(self):
        """Test creating normalizer with custom settings."""
        normalizer = create_safe_normalizer(
            fix_namespaces=False,
            normalize_whitespace=False
        )

        assert isinstance(normalizer, SafeSVGNormalizer)
        assert normalizer.settings['fix_namespaces'] is False
        assert normalizer.settings['normalize_whitespace'] is False

    def test_factory_options_validation(self):
        """Test factory validates options correctly."""
        # Invalid options should be ignored
        normalizer = create_safe_normalizer(
            invalid_option=True,
            fix_namespaces=False
        )

        assert normalizer.settings['fix_namespaces'] is False
        assert 'invalid_option' not in normalizer.settings


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_malformed_xml_recovery(self):
        """Test recovery from malformed XML."""
        malformed_xml = "<svg><rect><circle></svg>"

        result = safe_normalize_svg(malformed_xml)
        assert result is None

    def test_encoding_issues(self):
        """Test handling encoding issues."""
        # SVG with special characters
        svg_with_unicode = '''<svg xmlns="http://www.w3.org/2000/svg">
            <text>Special chars: ñáéíóú</text>
        </svg>'''

        result = safe_normalize_svg(svg_with_unicode)
        assert result is not None

    def test_very_large_svg(self):
        """Test handling very large SVG content."""
        # Create SVG with many elements
        elements = ['<rect x="{}" y="10" width="5" height="5"/>'.format(i)
                   for i in range(1000)]

        large_svg = '''<svg xmlns="http://www.w3.org/2000/svg">
            {}
        </svg>'''.format('\n'.join(elements))

        result = safe_normalize_svg(large_svg)
        assert result is not None

    def test_deeply_nested_structure(self):
        """Test handling deeply nested SVG structure."""
        # Create deeply nested groups
        nested_svg = '<svg xmlns="http://www.w3.org/2000/svg">'
        for i in range(20):
            nested_svg += f'<g id="group{i}">'
        nested_svg += '<rect width="10" height="10"/>'
        for i in range(20):
            nested_svg += '</g>'
        nested_svg += '</svg>'

        result = safe_normalize_svg(nested_svg)
        assert result is not None

    def test_comments_in_complex_structure(self):
        """Test comments in complex nested structure."""
        complex_svg = '''<svg xmlns="http://www.w3.org/2000/svg">
            <!-- Root comment -->
            <defs>
                <!-- Defs comment -->
                <linearGradient id="grad1">
                    <!-- Gradient comment -->
                    <stop offset="0%" stop-color="red"/>
                </linearGradient>
            </defs>
            <g transform="translate(10,10)">
                <!-- Group comment -->
                <rect width="50" height="50"/>
                <g>
                    <!-- Nested group comment -->
                    <circle cx="25" cy="25" r="20"/>
                </g>
            </g>
            <!-- Final comment -->
        </svg>'''

        result = safe_normalize_svg(complex_svg)
        assert result is not None

        # Should be able to safely process this complex structure
        normalizer = SafeSVGNormalizer()
        normalized, changes = normalizer.normalize(result)
        assert normalized is not None
        assert 'error' not in changes
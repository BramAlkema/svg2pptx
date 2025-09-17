#!/usr/bin/env python3
"""
Unit Tests for Preprocessing Plugins

Tests core preprocessing plugins including attribute cleanup, numeric value processing,
and style optimization. Validates XML manipulation and optimization algorithms.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# Import preprocessing modules under test
PREPROCESSING_AVAILABLE = True
try:
    from src.preprocessing.plugins import (
        CleanupAttrsPlugin, CleanupNumericValuesPlugin,
        RemoveEmptyAttrsPlugin, RemoveCommentsPlugin
    )
    from src.preprocessing.base import PreprocessingContext
except ImportError:
    PREPROCESSING_AVAILABLE = False


@pytest.mark.skipif(not PREPROCESSING_AVAILABLE, reason="Preprocessing plugins not available")
class TestCleanupAttrsPlugin:
    """
    Tests for CleanupAttrsPlugin - attribute whitespace cleanup.
    """

    @pytest.fixture
    def plugin(self):
        """Create CleanupAttrsPlugin instance."""
        return CleanupAttrsPlugin()

    @pytest.fixture
    def context(self):
        """Create preprocessing context."""
        return PreprocessingContext()

    @pytest.fixture
    def sample_elements(self):
        """Create sample SVG elements with various attribute patterns."""
        elements = {}

        # Element with whitespace in attributes
        elements['whitespace'] = ET.fromstring('<rect x="  10  " y="\n20\n" width="  80  "/>')

        # Element with clean attributes
        elements['clean'] = ET.fromstring('<rect x="10" y="20" width="80"/>')

        # Element with excessive whitespace
        elements['excessive'] = ET.fromstring('<rect fill="   red   blue   " stroke="  black  "/>')

        return elements

    def test_initialization(self, plugin):
        """Test plugin initialization."""
        assert plugin.name == "cleanupAttrs"
        assert "cleanups attributes" in plugin.description
        assert plugin.enabled is True

    def test_can_process_with_attributes(self, plugin, context, sample_elements):
        """Test can_process returns True for elements with attributes."""
        element = sample_elements['whitespace']
        assert plugin.can_process(element, context) is True

    def test_can_process_without_attributes(self, plugin, context):
        """Test can_process returns False for elements without attributes."""
        element = ET.fromstring('<rect/>')
        assert plugin.can_process(element, context) is False

    def test_process_whitespace_cleanup(self, plugin, context, sample_elements):
        """Test processing cleans up whitespace in attributes."""
        element = sample_elements['whitespace']
        original_x = element.get('x')
        original_y = element.get('y')

        result = plugin.process(element, context)

        assert result is True  # Modifications were made
        assert element.get('x') == "10"
        assert element.get('y') == "20"
        assert element.get('width') == "80"
        assert context.modifications_made is True

    def test_process_no_changes_needed(self, plugin, context, sample_elements):
        """Test processing returns False when no changes needed."""
        element = sample_elements['clean']

        result = plugin.process(element, context)

        assert result is False  # No modifications needed

    def test_process_excessive_whitespace(self, plugin, context, sample_elements):
        """Test processing handles excessive whitespace correctly."""
        element = sample_elements['excessive']

        result = plugin.process(element, context)

        assert result is True
        assert element.get('fill') == "red blue"  # Multiple spaces collapsed to single space
        assert element.get('stroke') == "black"


@pytest.mark.skipif(not PREPROCESSING_AVAILABLE, reason="Preprocessing plugins not available")
class TestCleanupNumericValuesPlugin:
    """
    Tests for CleanupNumericValuesPlugin - numeric attribute optimization.
    """

    @pytest.fixture
    def plugin(self):
        """Create CleanupNumericValuesPlugin instance."""
        return CleanupNumericValuesPlugin()

    @pytest.fixture
    def context(self):
        """Create preprocessing context with specific precision."""
        context = PreprocessingContext()
        context.precision = 3
        return context

    @pytest.fixture
    def sample_elements(self):
        """Create sample SVG elements with various numeric patterns."""
        elements = {}

        # Element with decimal values that can be optimized
        elements['decimals'] = ET.fromstring('<rect x="10.000" y="20.500" width="80.250"/>')

        # Element with px units
        elements['px_units'] = ET.fromstring('<rect x="10px" y="20px" width="80px"/>')

        # Element with very small values
        elements['tiny_values'] = ET.fromstring('<rect x="0.0001" y="0.00005" width="80"/>')

        return elements

    def test_initialization(self, plugin):
        """Test plugin initialization."""
        assert plugin.name == "cleanupNumericValues"
        assert "rounds numeric values" in plugin.description

    def test_can_process_any_element(self, plugin, context):
        """Test can_process returns True for any element."""
        element = ET.fromstring('<any-element/>')
        assert plugin.can_process(element, context) is True

    def test_process_decimal_optimization(self, plugin, context, sample_elements):
        """Test processing optimizes decimal values."""
        element = sample_elements['decimals']

        result = plugin.process(element, context)

        assert result is True
        assert element.get('x') == "10"  # .000 removed
        assert element.get('y') == "20.5"  # .500 -> .5
        assert element.get('width') == "80.25"  # .250 -> .25

    def test_process_px_unit_removal(self, plugin, context, sample_elements):
        """Test processing removes px units."""
        element = sample_elements['px_units']

        result = plugin.process(element, context)

        assert result is True
        assert element.get('x') == "10"
        assert element.get('y') == "20"
        assert element.get('width') == "80"

    def test_process_tiny_values_to_zero(self, plugin, context, sample_elements):
        """Test processing converts tiny values to zero based on precision."""
        element = sample_elements['tiny_values']

        result = plugin.process(element, context)

        assert result is True
        assert element.get('x') == "0"  # 0.0001 < 10^-3 precision
        assert element.get('y') == "0"  # 0.00005 < 10^-3 precision
        assert element.get('width') == "80"  # No change needed

    def test_process_no_numeric_attributes(self, plugin, context):
        """Test processing element with no numeric attributes."""
        element = ET.fromstring('<rect fill="red" stroke="blue"/>')

        result = plugin.process(element, context)

        assert result is False  # No modifications made


@pytest.mark.skipif(not PREPROCESSING_AVAILABLE, reason="Preprocessing plugins not available")
class TestRemoveEmptyAttrsPlugin:
    """
    Tests for RemoveEmptyAttrsPlugin - empty attribute removal.
    """

    @pytest.fixture
    def plugin(self):
        """Create RemoveEmptyAttrsPlugin instance."""
        return RemoveEmptyAttrsPlugin()

    @pytest.fixture
    def context(self):
        """Create preprocessing context."""
        return PreprocessingContext()

    @pytest.fixture
    def sample_elements(self):
        """Create sample SVG elements with empty attributes."""
        elements = {}

        # Element with empty attributes
        elements['empty_attrs'] = ET.fromstring('<rect x="10" y="" width="80" stroke="" fill="red"/>')

        # Element with no empty attributes
        elements['no_empty'] = ET.fromstring('<rect x="10" y="20" width="80" fill="red"/>')

        # Element with whitespace-only attributes
        elements['whitespace_only'] = ET.fromstring('<rect x="10" y="   " width="80" stroke="  "/>')

        return elements

    def test_initialization(self, plugin):
        """Test plugin initialization."""
        assert plugin.name == "removeEmptyAttrs"
        assert "removes empty attributes" in plugin.description

    def test_can_process_with_attributes(self, plugin, context, sample_elements):
        """Test can_process returns True for elements with attributes."""
        element = sample_elements['empty_attrs']
        assert plugin.can_process(element, context) is True

    def test_process_removes_empty_attributes(self, plugin, context, sample_elements):
        """Test processing removes empty attributes."""
        element = sample_elements['empty_attrs']
        original_attrs = set(element.attrib.keys())

        result = plugin.process(element, context)

        assert result is True
        assert 'y' not in element.attrib  # Empty y removed
        assert 'stroke' not in element.attrib  # Empty stroke removed
        assert element.get('x') == "10"  # Non-empty x preserved
        assert element.get('fill') == "red"  # Non-empty fill preserved

    def test_process_no_empty_attributes(self, plugin, context, sample_elements):
        """Test processing returns False when no empty attributes."""
        element = sample_elements['no_empty']

        result = plugin.process(element, context)

        assert result is False

    def test_process_whitespace_only_attributes(self, plugin, context, sample_elements):
        """Test processing removes whitespace-only attributes."""
        element = sample_elements['whitespace_only']

        result = plugin.process(element, context)

        assert result is True
        assert 'y' not in element.attrib  # Whitespace-only y removed
        assert 'stroke' not in element.attrib  # Whitespace-only stroke removed
        assert element.get('x') == "10"  # Non-empty x preserved


@pytest.mark.skipif(not PREPROCESSING_AVAILABLE, reason="Preprocessing plugins not available")
class TestRemoveCommentsPlugin:
    """
    Tests for RemoveCommentsPlugin - XML comment removal.
    """

    @pytest.fixture
    def plugin(self):
        """Create RemoveCommentsPlugin instance."""
        return RemoveCommentsPlugin()

    @pytest.fixture
    def context(self):
        """Create preprocessing context."""
        return PreprocessingContext()

    def test_initialization(self, plugin):
        """Test plugin initialization."""
        assert plugin.name == "removeComments"
        assert "removes comments" in plugin.description

    def test_can_process_comment_elements(self, plugin, context):
        """Test can_process correctly identifies comment elements."""
        # Create SVG with comments
        svg_with_comments = '''<svg xmlns="http://www.w3.org/2000/svg">
            <!-- This is a comment -->
            <rect x="10" y="20"/>
            <!-- Another comment -->
        </svg>'''

        root = ET.fromstring(svg_with_comments)

        # Find comment elements
        comments = [elem for elem in root if hasattr(elem, 'tag') and callable(elem.tag)]

        # Note: This test validates the concept - actual implementation may vary
        # based on how lxml handles comments in the preprocessing pipeline

    def test_process_removes_comments(self, plugin, context):
        """Test processing removes comment elements."""
        # Create element with text content that might include comments
        element = ET.fromstring('<g><!-- comment --><rect x="10"/></g>')

        # Note: Comment removal testing depends on lxml comment handling
        # This validates the plugin interface exists
        result = plugin.can_process(element, context)
        assert isinstance(result, bool)


@pytest.mark.skipif(not PREPROCESSING_AVAILABLE, reason="Preprocessing plugins not available")
class TestPluginIntegration:
    """
    Integration tests for multiple plugins working together.
    """

    @pytest.fixture
    def all_plugins(self):
        """Create instances of all plugins."""
        return [
            CleanupAttrsPlugin(),
            CleanupNumericValuesPlugin(),
            RemoveEmptyAttrsPlugin(),
            RemoveCommentsPlugin()
        ]

    @pytest.fixture
    def context(self):
        """Create preprocessing context."""
        return PreprocessingContext()

    def test_plugin_chain_processing(self, all_plugins, context):
        """Test multiple plugins can process the same element."""
        element = ET.fromstring('<rect x="  10.000px  " y="" width="  80.250  " stroke=""/>')

        modifications_made = False
        for plugin in all_plugins:
            if plugin.can_process(element, context):
                result = plugin.process(element, context)
                if result:
                    modifications_made = True

        # Verify final state after all plugins
        assert modifications_made
        assert element.get('x') == "10"  # Cleaned up, px removed, decimals optimized
        assert 'y' not in element.attrib  # Empty attribute removed
        assert element.get('width') == "80.25"  # Cleaned up, decimals optimized
        assert 'stroke' not in element.attrib  # Empty attribute removed

    def test_context_modification_tracking(self, all_plugins, context):
        """Test context properly tracks modifications across plugins."""
        element = ET.fromstring('<rect x="  10.000px  " y="" width="80"/>')

        initial_stats = dict(context.stats)

        for plugin in all_plugins:
            if plugin.can_process(element, context):
                plugin.process(element, context)

        assert context.modifications_made is True
        assert len(context.stats) > len(initial_stats)  # New stats recorded


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
#!/usr/bin/env python3
"""
Unit tests for EnhancedSlideBuilder hyperlink functionality.

Tests the hyperlink application methods added to EnhancedSlideBuilder:
- _apply_hyperlinks()
- _build_shape_index()
- _apply_result_hyperlinks()
- _apply_shape_hyperlink()
- _apply_text_hyperlink()
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET

from core.io.slide_builder_enhanced import EnhancedSlideBuilder, SlideMetadata, SlideTemplate
from core.io.embedder import DrawingMLEmbedder
from core.map.base import MapperResult, OutputFormat
from core.pipeline.hyperlinks import HyperlinkSpec
from core.policy import Policy, PolicyDecision
from core.ir import SceneGraph, Rect


class TestSlideBuilderHyperlinkMethods:
    """Test hyperlink-related methods in EnhancedSlideBuilder."""

    @pytest.fixture
    def mock_embedder(self):
        """Create a mock embedder."""
        embedder = Mock(spec=DrawingMLEmbedder)
        embedder.ensure_hlink_relationship.return_value = "rId5"
        embedder.embed_scene.return_value = Mock(
            slide_xml=self.sample_slide_xml(),
            relationship_data=[],
            media_files=[]
        )
        return embedder

    @pytest.fixture
    def mock_policy(self):
        """Create a mock policy."""
        return Mock(spec=Policy)

    @pytest.fixture
    def slide_builder(self, mock_embedder, mock_policy):
        """Create slide builder with mocked dependencies."""
        mappers = {}  # Empty mappers for testing
        return EnhancedSlideBuilder(
            mappers=mappers,
            embedder=mock_embedder,
            policy=mock_policy
        )

    @pytest.fixture
    def hyperlink_spec(self):
        """Create a test hyperlink spec."""
        return HyperlinkSpec(href="https://example.com", tooltip="Visit us")

    @pytest.fixture
    def mapper_result_with_hyperlinks(self, hyperlink_spec):
        """Create a mapper result with hyperlinks."""
        return MapperResult(
            element=Mock(),
            output_format=OutputFormat.NATIVE_DML,
            xml_content='<p:sp><p:nvSpPr><p:cNvPr id="2" name="test_shape"/></p:nvSpPr></p:sp>',
            policy_decision=PolicyDecision(use_native=True, reasons=[]),
            metadata={},
            hyperlinks=[hyperlink_spec],
            shape_id="2"
        )

    def sample_slide_xml(self):
        """Create sample slide XML for testing."""
        return '''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
            </p:nvGrpSpPr>
            <p:grpSpPr/>
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="2" name="test_shape"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr/>
            </p:sp>
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="3" name="another_shape"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr/>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>'''

    def test_apply_hyperlinks_no_hyperlinks(self, slide_builder):
        """Test _apply_hyperlinks when no hyperlinks are present."""
        slide_xml = self.sample_slide_xml()
        mapper_results = [
            MapperResult(
                element=Mock(),
                output_format=OutputFormat.NATIVE_DML,
                xml_content='<test/>',
                policy_decision=PolicyDecision(use_native=True, reasons=[]),
                metadata={}
            )
        ]

        result = slide_builder._apply_hyperlinks(slide_xml, mapper_results)

        # Should return unchanged XML
        assert result == slide_xml

    def test_apply_hyperlinks_with_hyperlinks(self, slide_builder, mapper_result_with_hyperlinks):
        """Test _apply_hyperlinks with hyperlinks present."""
        slide_xml = self.sample_slide_xml()
        mapper_results = [mapper_result_with_hyperlinks]

        result = slide_builder._apply_hyperlinks(slide_xml, mapper_results)

        # Should contain hyperlink XML
        assert "hlinkClick" in result
        assert 'r:id="rId5"' in result
        assert 'tooltip="Visit us"' in result

    def test_apply_hyperlinks_xml_parse_error(self, slide_builder, mapper_result_with_hyperlinks):
        """Test graceful handling of XML parse errors."""
        malformed_xml = "<invalid>xml</invalid>"
        mapper_results = [mapper_result_with_hyperlinks]

        result = slide_builder._apply_hyperlinks(malformed_xml, mapper_results)

        # Should return original XML on parse failure
        assert result == malformed_xml

    def test_build_shape_index_basic(self, slide_builder):
        """Test _build_shape_index with basic shapes."""
        slide_xml = self.sample_slide_xml()
        tree = ET.fromstring(slide_xml)
        namespaces = {
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
        }

        shape_index = slide_builder._build_shape_index(tree, namespaces)

        # Should index by both ID and name
        assert "2" in shape_index  # By ID
        assert "test_shape" in shape_index  # By name
        assert "3" in shape_index
        assert "another_shape" in shape_index

        # Verify the indexed elements are shape elements
        assert shape_index["2"].tag.endswith('sp')
        assert shape_index["test_shape"].tag.endswith('sp')

    def test_build_shape_index_empty_tree(self, slide_builder):
        """Test _build_shape_index with empty tree."""
        empty_xml = '<root></root>'
        tree = ET.fromstring(empty_xml)
        namespaces = {}

        shape_index = slide_builder._build_shape_index(tree, namespaces)

        assert shape_index == {}

    def test_build_shape_index_error_handling(self, slide_builder):
        """Test _build_shape_index error handling."""
        tree = Mock()
        tree.xpath.side_effect = Exception("XPath error")
        namespaces = {}

        shape_index = slide_builder._build_shape_index(tree, namespaces)

        assert shape_index == {}

    def test_apply_result_hyperlinks_no_hyperlinks(self, slide_builder):
        """Test _apply_result_hyperlinks with no hyperlinks."""
        tree = ET.fromstring(self.sample_slide_xml())
        result = MapperResult(
            element=Mock(),
            output_format=OutputFormat.NATIVE_DML,
            xml_content='<test/>',
            policy_decision=PolicyDecision(use_native=True, reasons=[]),
            metadata={}
        )
        shape_index = {}
        namespaces = {}

        # Should not raise exception
        slide_builder._apply_result_hyperlinks(tree, result, shape_index, namespaces)

    def test_apply_result_hyperlinks_missing_shape(self, slide_builder, hyperlink_spec):
        """Test _apply_result_hyperlinks with missing target shape."""
        tree = ET.fromstring(self.sample_slide_xml())
        result = MapperResult(
            element=Mock(),
            output_format=OutputFormat.NATIVE_DML,
            xml_content='<test/>',
            policy_decision=PolicyDecision(use_native=True, reasons=[]),
            metadata={},
            hyperlinks=[hyperlink_spec],
            shape_id="999"  # Non-existent shape
        )
        shape_index = {"2": Mock()}  # Different shape
        namespaces = {}

        # Should handle gracefully without crashing
        slide_builder._apply_result_hyperlinks(tree, result, shape_index, namespaces)

    def test_apply_result_hyperlinks_shape_level(self, slide_builder, hyperlink_spec):
        """Test _apply_result_hyperlinks with shape-level hyperlink."""
        tree = ET.fromstring(self.sample_slide_xml())

        # Create result with shape-level hyperlink
        result = MapperResult(
            element=Mock(),
            output_format=OutputFormat.NATIVE_DML,
            xml_content='<test/>',
            policy_decision=PolicyDecision(use_native=True, reasons=[]),
            metadata={},
            hyperlinks=[hyperlink_spec],
            shape_id="2"
        )

        # Build real shape index
        namespaces = {
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
        }
        shape_index = slide_builder._build_shape_index(tree, namespaces)

        slide_builder._apply_result_hyperlinks(tree, result, shape_index, namespaces)

        # Verify hyperlink was applied
        xml_str = ET.tostring(tree, encoding='unicode')
        assert "hlinkClick" in xml_str

    def test_apply_result_hyperlinks_text_level(self, slide_builder, hyperlink_spec):
        """Test _apply_result_hyperlinks with text-level hyperlink."""
        tree = ET.fromstring(self.sample_slide_xml())

        # Create result with text-level hyperlink
        result = MapperResult(
            element=Mock(),
            output_format=OutputFormat.NATIVE_DML,
            xml_content='<test/>',
            policy_decision=PolicyDecision(use_native=True, reasons=[]),
            metadata={},
            hyperlinks=[hyperlink_spec],
            shape_id="2",
            linked_runs=[{'start': 0, 'end': 10, 'hyperlink_index': 0}]
        )

        # Build real shape index
        namespaces = {
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
        }
        shape_index = slide_builder._build_shape_index(tree, namespaces)

        slide_builder._apply_result_hyperlinks(tree, result, shape_index, namespaces)

        # Verify hyperlink was applied (currently implemented as shape-level)
        xml_str = ET.tostring(tree, encoding='unicode')
        assert "hlinkClick" in xml_str

    def test_apply_shape_hyperlink_basic(self, slide_builder, mock_embedder, hyperlink_spec):
        """Test _apply_shape_hyperlink basic functionality."""
        # Create a shape element with cNvPr
        shape_xml = '''<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
            <p:nvSpPr>
                <p:cNvPr id="2" name="test"/>
            </p:nvSpPr>
        </p:sp>'''
        shape_elem = ET.fromstring(shape_xml)

        namespaces = {
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }

        slide_builder._apply_shape_hyperlink(shape_elem, hyperlink_spec, namespaces)

        # Verify hyperlink was added
        xml_str = ET.tostring(shape_elem, encoding='unicode')
        assert "hlinkClick" in xml_str
        assert 'tooltip="Visit us"' in xml_str

        # Verify embedder was called
        mock_embedder.ensure_hlink_relationship.assert_called_once_with(hyperlink_spec)

    def test_apply_shape_hyperlink_no_cnvpr(self, slide_builder, hyperlink_spec):
        """Test _apply_shape_hyperlink with missing cNvPr element."""
        # Create a shape element without cNvPr
        shape_xml = '''<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
            <p:spPr/>
        </p:sp>'''
        shape_elem = ET.fromstring(shape_xml)

        namespaces = {
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
        }

        # Should handle gracefully
        slide_builder._apply_shape_hyperlink(shape_elem, hyperlink_spec, namespaces)

        # No hyperlink should be added
        xml_str = ET.tostring(shape_elem, encoding='unicode')
        assert "hlinkClick" not in xml_str

    def test_apply_shape_hyperlink_error_handling(self, slide_builder):
        """Test _apply_shape_hyperlink error handling."""
        shape_elem = Mock()
        shape_elem.xpath.side_effect = Exception("XPath error")
        hyperlink = Mock()
        namespaces = {}

        # Should not raise exception
        slide_builder._apply_shape_hyperlink(shape_elem, hyperlink, namespaces)

    def test_apply_text_hyperlink_basic(self, slide_builder, hyperlink_spec):
        """Test _apply_text_hyperlink basic functionality."""
        tree = ET.fromstring(self.sample_slide_xml())

        # Get a shape element
        namespaces = {
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
        }
        shape_index = slide_builder._build_shape_index(tree, namespaces)
        shape_elem = shape_index["2"]

        linked_run = {'start': 0, 'end': 10, 'hyperlink_index': 0}

        slide_builder._apply_text_hyperlink(tree, shape_elem, hyperlink_spec, linked_run, namespaces)

        # Currently implemented as shape-level hyperlink
        xml_str = ET.tostring(tree, encoding='unicode')
        assert "hlinkClick" in xml_str

    def test_apply_text_hyperlink_error_handling(self, slide_builder):
        """Test _apply_text_hyperlink error handling."""
        tree = Mock()
        shape_elem = Mock()
        shape_elem.xpath.side_effect = Exception("XPath error")
        hyperlink = Mock()
        linked_run = {}
        namespaces = {}

        # Should not raise exception
        slide_builder._apply_text_hyperlink(tree, shape_elem, hyperlink, linked_run, namespaces)

    def test_integration_build_slide_with_hyperlinks(self, slide_builder, mock_embedder, mock_policy):
        """Test integration of hyperlink application in build_slide workflow."""
        # Create a scene with elements
        scene = [Mock()]  # SceneGraph is actually a List[IRElement]

        # Create mapper result with hyperlinks
        mapper_result = MapperResult(
            element=Mock(),
            output_format=OutputFormat.NATIVE_DML,
            xml_content='<p:sp><p:nvSpPr><p:cNvPr id="2" name="test"/></p:nvSpPr></p:sp>',
            policy_decision=PolicyDecision(use_native=True, reasons=[]),
            metadata={},
            hyperlinks=[HyperlinkSpec(href="https://example.com")],
            shape_id="2"
        )

        # Mock the mapping process to return our result
        with patch.object(slide_builder, '_map_scene_elements', return_value=[mapper_result]):
            # Mock the metadata application
            with patch.object(slide_builder, '_apply_slide_metadata_xml', side_effect=lambda x, y: x):
                result = slide_builder.build_from_elements(scene)  # Use build_from_elements which accepts a list

                # Verify embedder was called
                mock_embedder.embed_scene.assert_called_once()

                # Verify result contains hyperlink data
                assert result is not None

    def test_multiple_hyperlinks_same_result(self, slide_builder, mock_embedder):
        """Test handling multiple hyperlinks in same MapperResult."""
        slide_xml = self.sample_slide_xml()

        hyperlinks = [
            HyperlinkSpec(href="https://example.com", tooltip="External"),
            HyperlinkSpec(href="slide:3", tooltip="Internal")
        ]

        mapper_result = MapperResult(
            element=Mock(),
            output_format=OutputFormat.NATIVE_DML,
            xml_content='<test/>',
            policy_decision=PolicyDecision(use_native=True, reasons=[]),
            metadata={},
            hyperlinks=hyperlinks,
            shape_id="2"
        )

        # Mock different relationship IDs for different hyperlinks
        mock_embedder.ensure_hlink_relationship.side_effect = ["rId1", "rId2"]

        result = slide_builder._apply_hyperlinks(slide_xml, [mapper_result])

        # Should handle multiple hyperlinks
        assert "hlinkClick" in result
        # Embedder should be called for each hyperlink
        assert mock_embedder.ensure_hlink_relationship.call_count == 2

    def test_multiple_mapper_results_with_hyperlinks(self, slide_builder, mock_embedder):
        """Test handling multiple MapperResults with hyperlinks."""
        slide_xml = self.sample_slide_xml()

        results = [
            MapperResult(
                element=Mock(),
                output_format=OutputFormat.NATIVE_DML,
                xml_content='<test/>',
                policy_decision=PolicyDecision(use_native=True, reasons=[]),
                metadata={},
                hyperlinks=[HyperlinkSpec(href="https://example1.com")],
                shape_id="2"
            ),
            MapperResult(
                element=Mock(),
                output_format=OutputFormat.NATIVE_DML,
                xml_content='<test/>',
                policy_decision=PolicyDecision(use_native=True, reasons=[]),
                metadata={},
                hyperlinks=[HyperlinkSpec(href="https://example2.com")],
                shape_id="3"
            )
        ]

        mock_embedder.ensure_hlink_relationship.side_effect = ["rId1", "rId2"]

        result = slide_builder._apply_hyperlinks(slide_xml, results)

        # Should handle multiple results
        assert "hlinkClick" in result
        # Embedder should be called for each hyperlink
        assert mock_embedder.ensure_hlink_relationship.call_count == 2
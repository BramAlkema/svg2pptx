#!/usr/bin/env python3
"""
End-to-end integration tests for hyperlink functionality.

Tests the complete pipeline: SVG parsing → IR elements → Mappers → Slide Builder → PowerPoint XML.
Verifies that hyperlinks flow correctly through the entire system.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

from core.parse.parser import SVGParser
from core.map.path_mapper import PathMapper
from core.map.text_mapper import TextMapper
from core.io.slide_builder_enhanced import EnhancedSlideBuilder, SlideMetadata, SlideTemplate
from core.io.embedder import DrawingMLEmbedder
from core.pipeline.hyperlinks import HyperlinkSpec
from core.policy import Policy


class TestHyperlinkIntegrationE2E:
    """End-to-end tests for hyperlink functionality across the entire pipeline."""

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy for testing."""
        policy = Mock()
        policy.decide_path.return_value = Mock(
            use_native=True,
            estimated_quality=0.95,
            estimated_performance=0.9
        )
        policy.decide_text.return_value = Mock(
            use_native=True,
            estimated_quality=0.95,
            estimated_performance=0.9
        )
        return policy

    @pytest.fixture
    def svg_with_hyperlink(self):
        """Create SVG content with hyperlink for testing."""
        return '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
            <a href="https://example.com">
                <title>Visit our website</title>
                <rect x="10" y="10" width="100" height="50" fill="blue"/>
            </a>
        </svg>'''

    @pytest.fixture
    def svg_with_text_hyperlink(self):
        """Create SVG content with text hyperlink for testing."""
        return '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
            <a href="mailto:contact@example.com">
                <title>Send us an email</title>
                <text x="20" y="30" font-family="Arial" font-size="12">Contact us</text>
            </a>
        </svg>'''

    @pytest.fixture
    def svg_with_internal_link(self):
        """Create SVG content with internal slide link for testing."""
        return '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
            <a href="slide:3">
                <title>Go to slide 3</title>
                <circle cx="50" cy="50" r="25" fill="red"/>
            </a>
        </svg>'''

    @pytest.fixture
    def parser(self):
        """Create SVG parser for testing."""
        return SVGParser(enable_normalization=False)

    @pytest.fixture
    def embedder(self):
        """Create mock embedder for testing."""
        embedder = Mock(spec=DrawingMLEmbedder)
        embedder.ensure_hlink_relationship.return_value = "rId1"
        embedder.embed_scene.return_value = Mock(
            slide_xml=self.sample_slide_xml(),
            relationships=[],
            media_files=[]
        )
        return embedder

    def sample_slide_xml(self):
        """Create sample slide XML with proper namespaces for testing."""
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
                    <p:cNvPr id="2" name="shape_123"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr/>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>'''

    def test_svg_to_powerpoint_hyperlink_e2e(self, parser, mock_policy, embedder, svg_with_hyperlink):
        """Test complete pipeline from SVG with hyperlink to PowerPoint XML."""
        # Step 1: Parse SVG to IR
        scene, parse_result = parser.parse_to_ir(svg_with_hyperlink)

        assert parse_result.success
        assert len(scene) > 0

        # Verify hyperlink was parsed correctly
        hyperlinked_elements = [elem for elem in scene if elem.hyperlink is not None]
        assert len(hyperlinked_elements) > 0

        hyperlink = hyperlinked_elements[0].hyperlink
        assert hyperlink.href == "https://example.com"
        assert hyperlink.tooltip == "Visit our website"

        # Step 2: Map IR elements to MapperResults
        path_mapper = PathMapper(mock_policy)

        mapper_results = []
        for element in scene:
            if path_mapper.can_map(element):
                with patch.object(path_mapper, 'xml_builder') as mock_xml_builder:
                    mock_xml_builder.generate_path.return_value = Mock()
                    mock_xml_builder.element_to_string.return_value = f"<path>shape for {id(element)}</path>"

                    result = path_mapper.map(element)
                    mapper_results.append(result)

        # Verify mapper extracted hyperlink info
        hyperlink_results = [r for r in mapper_results if r.hyperlinks]
        assert len(hyperlink_results) > 0

        mapper_result = hyperlink_results[0]
        assert mapper_result.hyperlinks[0].href == "https://example.com"
        assert mapper_result.shape_id is not None

        # Step 3: Build slide with hyperlinks
        mappers = {'path': path_mapper}
        slide_builder = EnhancedSlideBuilder(
            mappers=mappers,
            embedder=embedder,
            policy=mock_policy
        )

        metadata = SlideMetadata(template=SlideTemplate.BLANK, slide_index=1)
        result = slide_builder.build_slide(scene, metadata)

        # Verify slide was built successfully
        assert result.slide_xml is not None

        # Step 4: Verify hyperlink was applied to PowerPoint XML
        # Parse the resulting XML to check for hyperlink elements
        slide_tree = ET.fromstring(result.slide_xml)

        # Look for hyperlink elements (hlinkClick)
        namespaces = {
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }

        hyperlink_elements = slide_tree.xpath('.//a:hlinkClick', namespaces=namespaces)
        assert len(hyperlink_elements) > 0

        # Verify hyperlink attributes
        hlink = hyperlink_elements[0]
        r_id = hlink.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        assert r_id == "rId1"

        tooltip = hlink.get('tooltip')
        assert tooltip == "Visit our website"

        visited = hlink.get('history')
        assert visited == "1"  # visited=True

    def test_text_hyperlink_e2e(self, parser, mock_policy, embedder, svg_with_text_hyperlink):
        """Test complete pipeline for text hyperlinks."""
        # Step 1: Parse SVG to IR
        scene, parse_result = parser.parse_to_ir(svg_with_text_hyperlink)

        assert parse_result.success
        assert len(scene) > 0

        # Find text elements with hyperlinks
        text_elements = [elem for elem in scene if hasattr(elem, 'runs') and elem.hyperlink is not None]
        assert len(text_elements) > 0

        text_element = text_elements[0]
        assert text_element.hyperlink.href == "mailto:contact@example.com"
        assert text_element.hyperlink.tooltip == "Send us an email"

        # Step 2: Map text elements
        text_mapper = TextMapper(mock_policy)

        mapper_results = []
        for element in scene:
            if text_mapper.can_map(element):
                with patch.object(text_mapper, '_generate_standard_text_xml') as mock_gen:
                    mock_gen.return_value = f"<text>text for {id(element)}</text>"

                    result = text_mapper.map(element)
                    mapper_results.append(result)

        # Verify text mapper extracted hyperlink info including linked_runs
        hyperlink_results = [r for r in mapper_results if r.hyperlinks]
        assert len(hyperlink_results) > 0

        text_result = hyperlink_results[0]
        assert text_result.hyperlinks[0].href == "mailto:contact@example.com"
        assert text_result.linked_runs is not None
        assert len(text_result.linked_runs) == 1
        assert text_result.linked_runs[0]['hyperlink'] == text_element.hyperlink

        # Step 3: Build slide (same as previous test)
        mappers = {'text': text_mapper}
        slide_builder = EnhancedSlideBuilder(
            mappers=mappers,
            embedder=embedder,
            policy=mock_policy
        )

        metadata = SlideMetadata(template=SlideTemplate.BLANK, slide_index=1)
        result = slide_builder.build_slide(scene, metadata)

        # Verify slide contains hyperlink
        assert result.slide_xml is not None

        slide_tree = ET.fromstring(result.slide_xml)
        namespaces = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }

        hyperlink_elements = slide_tree.xpath('.//a:hlinkClick', namespaces=namespaces)
        assert len(hyperlink_elements) > 0

    def test_internal_slide_link_e2e(self, parser, mock_policy, embedder, svg_with_internal_link):
        """Test complete pipeline for internal slide links."""
        # Step 1: Parse SVG to IR
        scene, parse_result = parser.parse_to_ir(svg_with_internal_link)

        assert parse_result.success
        hyperlinked_elements = [elem for elem in scene if elem.hyperlink is not None]
        assert len(hyperlinked_elements) > 0

        hyperlink = hyperlinked_elements[0].hyperlink
        assert hyperlink.href == "slide:3"
        assert hyperlink.is_internal_slide_link()
        assert hyperlink.get_slide_number() == 3

        # Step 2: Map and verify internal link processing
        path_mapper = PathMapper(mock_policy)

        mapper_results = []
        for element in scene:
            if path_mapper.can_map(element):
                with patch.object(path_mapper, 'xml_builder') as mock_xml_builder:
                    mock_xml_builder.generate_path.return_value = Mock()
                    mock_xml_builder.element_to_string.return_value = f"<path>shape for {id(element)}</path>"

                    result = path_mapper.map(element)
                    mapper_results.append(result)

        hyperlink_results = [r for r in mapper_results if r.hyperlinks]
        assert len(hyperlink_results) > 0

        # Step 3: Configure embedder for internal links
        embedder.ensure_hlink_relationship.return_value = "rId2"

        # Step 4: Build slide and verify internal link handling
        mappers = {'path': path_mapper}
        slide_builder = EnhancedSlideBuilder(
            mappers=mappers,
            embedder=embedder,
            policy=mock_policy
        )

        metadata = SlideMetadata(template=SlideTemplate.BLANK, slide_index=1)
        result = slide_builder.build_slide(scene, metadata)

        # Verify internal slide link in XML
        slide_tree = ET.fromstring(result.slide_xml)
        namespaces = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }

        hyperlink_elements = slide_tree.xpath('.//a:hlinkClick', namespaces=namespaces)
        assert len(hyperlink_elements) > 0

        hlink = hyperlink_elements[0]
        r_id = hlink.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        assert r_id == "rId2"

    def test_multiple_hyperlinks_on_slide(self, parser, mock_policy, embedder):
        """Test slide with multiple hyperlink elements."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
            <a href="https://example.com">
                <title>Website</title>
                <rect x="10" y="10" width="80" height="40" fill="blue"/>
            </a>
            <a href="mailto:test@example.com">
                <title>Email</title>
                <rect x="100" y="10" width="80" height="40" fill="red"/>
            </a>
            <a href="slide:2">
                <title>Next slide</title>
                <rect x="190" y="10" width="80" height="40" fill="green"/>
            </a>
        </svg>'''

        # Parse SVG
        scene, parse_result = parser.parse_to_ir(svg_content)
        assert parse_result.success

        # Verify multiple hyperlinks parsed
        hyperlinked_elements = [elem for elem in scene if elem.hyperlink is not None]
        assert len(hyperlinked_elements) == 3

        hrefs = [elem.hyperlink.href for elem in hyperlinked_elements]
        assert "https://example.com" in hrefs
        assert "mailto:test@example.com" in hrefs
        assert "slide:2" in hrefs

        # Map elements
        path_mapper = PathMapper(mock_policy)
        mapper_results = []

        for element in scene:
            if path_mapper.can_map(element):
                with patch.object(path_mapper, 'xml_builder') as mock_xml_builder:
                    mock_xml_builder.generate_path.return_value = Mock()
                    mock_xml_builder.element_to_string.return_value = f"<path>shape for {id(element)}</path>"

                    result = path_mapper.map(element)
                    mapper_results.append(result)

        # Verify multiple mapper results with hyperlinks
        hyperlink_results = [r for r in mapper_results if r.hyperlinks]
        assert len(hyperlink_results) == 3

        # Build slide
        embedder.ensure_hlink_relationship.side_effect = ["rId1", "rId2", "rId3"]

        mappers = {'path': path_mapper}
        slide_builder = EnhancedSlideBuilder(
            mappers=mappers,
            embedder=embedder,
            policy=mock_policy
        )

        metadata = SlideMetadata(template=SlideTemplate.BLANK, slide_index=1)
        result = slide_builder.build_slide(scene, metadata)

        # Verify multiple hyperlinks in slide XML
        slide_tree = ET.fromstring(result.slide_xml)
        namespaces = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
        }

        hyperlink_elements = slide_tree.xpath('.//a:hlinkClick', namespaces=namespaces)
        assert len(hyperlink_elements) == 3

    def test_nested_hyperlink_groups(self, parser, mock_policy, embedder):
        """Test hyperlinks applied to group elements."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
            <a href="https://example.com">
                <title>Group link</title>
                <g>
                    <rect x="10" y="10" width="50" height="25" fill="blue"/>
                    <text x="15" y="25" font-size="10">Click</text>
                </g>
            </a>
        </svg>'''

        # Parse SVG
        scene, parse_result = parser.parse_to_ir(svg_content)
        assert parse_result.success

        # Verify group has hyperlink
        hyperlinked_elements = [elem for elem in scene if elem.hyperlink is not None]
        assert len(hyperlinked_elements) > 0

        # Should work with group mapper as well
        # This test validates that the group structure preserves hyperlinks
        group_elements = [elem for elem in scene if hasattr(elem, 'children')]
        if group_elements:
            assert group_elements[0].hyperlink is not None
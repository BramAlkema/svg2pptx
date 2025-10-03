#!/usr/bin/env python3
"""
Unit tests for DrawingML Embedder hyperlink functionality.

Tests the hyperlink-related methods added to DrawingMLEmbedder:
- ensure_hlink_relationship()
- attach_hlink_to_shape()
- attach_hlink_to_run()
- get_hyperlink_relationships()
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

from core.io.embedder import DrawingMLEmbedder, EmbeddingError
from core.pipeline.hyperlinks import HyperlinkSpec


class TestEmbedderHyperlinkMethods:
    """Test hyperlink-related methods in DrawingMLEmbedder."""

    @pytest.fixture
    def embedder(self):
        """Create a fresh embedder instance for each test."""
        return DrawingMLEmbedder()

    @pytest.fixture
    def external_hyperlink(self):
        """Create an external hyperlink for testing."""
        return HyperlinkSpec(href="https://example.com", tooltip="Visit our website")

    @pytest.fixture
    def internal_hyperlink(self):
        """Create an internal slide hyperlink for testing."""
        return HyperlinkSpec(href="slide:3", tooltip="Go to slide 3")

    @pytest.fixture
    def mailto_hyperlink(self):
        """Create a mailto hyperlink for testing."""
        return HyperlinkSpec(href="mailto:contact@example.com", tooltip="Send email")

    def test_ensure_hlink_relationship_creates_new_relationship(self, embedder, external_hyperlink):
        """Test that ensure_hlink_relationship creates a new relationship."""
        rel_id = embedder.ensure_hlink_relationship(external_hyperlink)

        assert rel_id == "rId1"
        assert external_hyperlink.href in embedder._hyperlink_relationships
        assert embedder._hyperlink_relationships[external_hyperlink.href] == "rId1"

    def test_ensure_hlink_relationship_deduplicates_same_href(self, embedder, external_hyperlink):
        """Test that same href returns same relationship ID."""
        rel_id1 = embedder.ensure_hlink_relationship(external_hyperlink)
        rel_id2 = embedder.ensure_hlink_relationship(external_hyperlink)

        assert rel_id1 == rel_id2 == "rId1"
        assert len(embedder._hyperlink_relationships) == 1

    def test_ensure_hlink_relationship_different_hrefs_get_different_ids(self, embedder):
        """Test that different hrefs get different relationship IDs."""
        link1 = HyperlinkSpec(href="https://example.com")
        link2 = HyperlinkSpec(href="https://other.com")

        rel_id1 = embedder.ensure_hlink_relationship(link1)
        rel_id2 = embedder.ensure_hlink_relationship(link2)

        assert rel_id1 == "rId1"
        assert rel_id2 == "rId2"
        assert len(embedder._hyperlink_relationships) == 2

    def test_ensure_hlink_relationship_increments_counter(self, embedder):
        """Test that relationship counter increments properly."""
        initial_counter = embedder._relationship_id_counter

        link1 = HyperlinkSpec(href="https://example.com")
        link2 = HyperlinkSpec(href="mailto:test@example.com")

        embedder.ensure_hlink_relationship(link1)
        embedder.ensure_hlink_relationship(link2)

        assert embedder._relationship_id_counter == initial_counter + 2

    def test_attach_hlink_to_shape_basic_functionality(self, embedder, external_hyperlink):
        """Test basic shape hyperlink attachment."""
        shape_xml = '''<p:sp>
            <p:nvSpPr>
                <p:cNvPr id="2" name="rectangle"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr/>
        </p:sp>'''

        result = embedder.attach_hlink_to_shape(shape_xml, external_hyperlink)

        # Verify the hyperlink was added
        assert "hlinkClick" in result
        assert 'r:id="rId1"' in result
        assert 'tooltip="Visit our website"' in result
        assert 'history="1"' in result  # visited=True default

    def test_attach_hlink_to_shape_without_tooltip(self, embedder):
        """Test shape hyperlink attachment without tooltip."""
        hyperlink = HyperlinkSpec(href="https://example.com")  # No tooltip
        shape_xml = '''<p:sp>
            <p:nvSpPr>
                <p:cNvPr id="2" name="rectangle"/>
            </p:nvSpPr>
        </p:sp>'''

        result = embedder.attach_hlink_to_shape(shape_xml, hyperlink)

        assert "hlinkClick" in result
        assert 'r:id="rId1"' in result
        assert 'tooltip=' not in result  # No tooltip attribute

    def test_attach_hlink_to_shape_unvisited_link(self, embedder):
        """Test shape hyperlink attachment with visited=False."""
        hyperlink = HyperlinkSpec(href="https://example.com", visited=False)
        shape_xml = '''<p:sp>
            <p:nvSpPr>
                <p:cNvPr id="2" name="rectangle"/>
            </p:nvSpPr>
        </p:sp>'''

        result = embedder.attach_hlink_to_shape(shape_xml, hyperlink)

        assert "hlinkClick" in result
        assert 'history=' not in result  # No history attribute for unvisited

    def test_attach_hlink_to_shape_xml_parsing_error(self, embedder, external_hyperlink):
        """Test graceful handling of XML parsing errors."""
        malformed_xml = '''<p:sp><unclosed_tag>malformed</p:sp>'''

        result = embedder.attach_hlink_to_shape(malformed_xml, external_hyperlink)

        # Should return original XML on parse failure
        assert result == malformed_xml

    def test_attach_hlink_to_shape_no_cnvpr_element(self, embedder, external_hyperlink):
        """Test behavior when no cNvPr element is found."""
        shape_xml = '''<p:sp>
            <p:spPr/>
        </p:sp>'''

        result = embedder.attach_hlink_to_shape(shape_xml, external_hyperlink)

        # Should not contain hyperlink since no cNvPr found
        assert "hlinkClick" not in result
        assert result != shape_xml  # But XML should be processed

    def test_attach_hlink_to_run_basic_functionality(self, embedder, external_hyperlink):
        """Test basic text run hyperlink attachment."""
        text_xml = '''<a:p><a:r><a:t>Click here</a:t></a:r></a:p>'''

        result = embedder.attach_hlink_to_run(
            text_xml, external_hyperlink, 0, 10, "Click here"
        )

        # Should contain hyperlink run properties
        assert "hlinkClick" in result
        assert 'r:id="rId1"' in result
        assert "Click here" in result

    def test_attach_hlink_to_run_with_tooltip(self, embedder, external_hyperlink):
        """Test text run hyperlink with tooltip."""
        text_xml = '''<a:p><a:r><a:t>Visit us</a:t></a:r></a:p>'''

        result = embedder.attach_hlink_to_run(
            text_xml, external_hyperlink, 0, 8, "Visit us"
        )

        assert "hlinkClick" in result
        assert 'tooltip="Visit our website"' in result

    def test_attach_hlink_to_run_error_handling(self, embedder):
        """Test text run hyperlink error handling."""
        malformed_xml = '''<invalid>xml</invalid>'''

        # This should use an invalid hyperlink to trigger an error
        with patch.object(embedder, 'ensure_hlink_relationship', side_effect=Exception("Test error")):
            hyperlink = HyperlinkSpec(href="https://example.com")
            result = embedder.attach_hlink_to_run(
                malformed_xml, hyperlink, 0, 5, "test"
            )

            # Should return original XML on error
            assert result == malformed_xml

    def test_get_hyperlink_relationships_external_links(self, embedder):
        """Test relationship generation for external links."""
        external_link = HyperlinkSpec(href="https://example.com")
        mailto_link = HyperlinkSpec(href="mailto:test@example.com")

        # Create relationships
        embedder.ensure_hlink_relationship(external_link)
        embedder.ensure_hlink_relationship(mailto_link)

        relationships = embedder.get_hyperlink_relationships()

        assert len(relationships) == 2

        # Check external HTTP link
        http_rel = next(r for r in relationships if r['target'] == 'https://example.com')
        assert http_rel['id'] == 'rId1'
        assert http_rel['type'] == 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink'
        assert http_rel['target_mode'] == 'External'

        # Check mailto link
        mailto_rel = next(r for r in relationships if r['target'] == 'mailto:test@example.com')
        assert mailto_rel['id'] == 'rId2'
        assert mailto_rel['type'] == 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink'
        assert mailto_rel['target_mode'] == 'External'

    def test_get_hyperlink_relationships_internal_links(self, embedder, internal_hyperlink):
        """Test relationship generation for internal slide links."""
        embedder.ensure_hlink_relationship(internal_hyperlink)

        relationships = embedder.get_hyperlink_relationships()

        assert len(relationships) == 1
        rel = relationships[0]

        assert rel['id'] == 'rId1'
        assert rel['type'] == 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide'
        assert rel['target'] == '../slides/slide3.xml'
        assert 'target_mode' not in rel  # Internal links don't have TargetMode

    def test_get_hyperlink_relationships_mixed_types(self, embedder):
        """Test relationship generation with mixed link types."""
        external_link = HyperlinkSpec(href="https://example.com")
        internal_link = HyperlinkSpec(href="slide:5")
        tel_link = HyperlinkSpec(href="tel:+1-555-0123")

        embedder.ensure_hlink_relationship(external_link)
        embedder.ensure_hlink_relationship(internal_link)
        embedder.ensure_hlink_relationship(tel_link)

        relationships = embedder.get_hyperlink_relationships()

        assert len(relationships) == 3

        # Verify different relationship types are handled correctly
        external_rels = [r for r in relationships if 'target_mode' in r]
        internal_rels = [r for r in relationships if 'target_mode' not in r]

        assert len(external_rels) == 2  # https and tel
        assert len(internal_rels) == 1   # slide

    def test_get_hyperlink_relationships_error_handling(self, embedder):
        """Test error handling in relationship generation."""
        # Manually add an invalid href to trigger error
        embedder._hyperlink_relationships["invalid://href"] = "rId1"

        # Mock HyperlinkSpec constructor to raise an error
        with patch('core.io.embedder.HyperlinkSpec', side_effect=ValueError("Invalid href")):
            relationships = embedder.get_hyperlink_relationships()

            # Should return empty list when all relationships fail
            assert relationships == []

    def test_reset_statistics_clears_hyperlink_relationships(self, embedder, external_hyperlink):
        """Test that reset_statistics also clears hyperlink relationships."""
        # Create some relationships
        embedder.ensure_hlink_relationship(external_hyperlink)
        assert len(embedder._hyperlink_relationships) == 1

        # Reset statistics
        embedder.reset_statistics()

        # Relationships should be cleared
        assert len(embedder._hyperlink_relationships) == 0

    def test_relationship_id_counter_persistence(self, embedder):
        """Test that relationship ID counter persists correctly."""
        link1 = HyperlinkSpec(href="https://example.com")
        link2 = HyperlinkSpec(href="mailto:test@example.com")

        rel_id1 = embedder.ensure_hlink_relationship(link1)
        rel_id2 = embedder.ensure_hlink_relationship(link2)

        # IDs should be sequential
        assert rel_id1 == "rId1"
        assert rel_id2 == "rId2"

        # Counter should be at 3 for next relationship
        assert embedder._relationship_id_counter == 3

    def test_complex_shape_xml_hyperlink_attachment(self, embedder, external_hyperlink):
        """Test hyperlink attachment to complex shape XML."""
        complex_shape_xml = '''<p:sp>
            <p:nvSpPr>
                <p:cNvPr id="5" name="complex_shape">
                    <a:extLst>
                        <a:ext uri="{existing-extension}"/>
                    </a:extLst>
                </p:cNvPr>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="100" y="200"/>
                    <a:ext cx="300" cy="400"/>
                </a:xfrm>
            </p:spPr>
        </p:sp>'''

        result = embedder.attach_hlink_to_shape(complex_shape_xml, external_hyperlink)

        # Should still work with complex structure
        assert "hlinkClick" in result
        assert 'r:id="rId1"' in result
        assert 'tooltip="Visit our website"' in result

        # Original structure should be preserved
        assert "existing-extension" in result
        assert '<a:off x="100" y="200"/>' in result

    def test_hyperlink_namespace_handling(self, embedder, external_hyperlink):
        """Test proper namespace handling in hyperlink XML generation."""
        shape_xml = '''<p:sp>
            <p:nvSpPr>
                <p:cNvPr id="2" name="test"/>
            </p:nvSpPr>
        </p:sp>'''

        result = embedder.attach_hlink_to_shape(shape_xml, external_hyperlink)

        # Parse result to verify namespace correctness
        root = ET.fromstring(f"<root>{result}</root>")

        # Find the hyperlink element
        hyperlink_elem = None
        for elem in root.iter():
            if elem.tag.endswith('hlinkClick'):
                hyperlink_elem = elem
                break

        assert hyperlink_elem is not None

        # Verify namespace attributes
        r_id_attr = hyperlink_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        assert r_id_attr == 'rId1'
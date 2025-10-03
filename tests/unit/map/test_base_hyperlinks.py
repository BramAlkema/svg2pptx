#!/usr/bin/env python3
"""
Unit tests for MapperResult hyperlink extensions.

Tests the new hyperlink-related fields added to MapperResult
while ensuring backward compatibility is maintained.
"""

import pytest
from unittest.mock import Mock

from core.map.base import MapperResult, OutputFormat
from core.policy import PolicyDecision
from core.pipeline.hyperlinks import HyperlinkSpec


class TestMapperResultHyperlinkExtensions:
    """Test hyperlink extensions to MapperResult."""

    def create_basic_mapper_result(self, **kwargs):
        """Helper to create a basic MapperResult with required fields."""
        defaults = {
            'element': None,
            'output_format': OutputFormat.NATIVE_DML,
            'xml_content': '<test/>',
            'policy_decision': PolicyDecision(use_native=True, reasons=[]),
            'metadata': {}
        }
        defaults.update(kwargs)
        return MapperResult(**defaults)

    def test_backward_compatibility_no_hyperlinks(self):
        """Test that MapperResult works without hyperlink fields (backward compatibility)."""
        result = self.create_basic_mapper_result()

        # All hyperlink fields should default to None
        assert result.hyperlinks is None
        assert result.shape_id is None
        assert result.linked_runs is None

        # Original fields should still work
        assert result.output_format == OutputFormat.NATIVE_DML
        assert result.xml_content == '<test/>'
        assert result.policy_decision.use_native is True

    def test_single_hyperlink_attachment(self):
        """Test MapperResult with a single hyperlink."""
        hyperlink = HyperlinkSpec(href="https://example.com", tooltip="Visit our site")

        result = self.create_basic_mapper_result(
            hyperlinks=[hyperlink],
            shape_id="shape123"
        )

        assert len(result.hyperlinks) == 1
        assert result.hyperlinks[0].href == "https://example.com"
        assert result.hyperlinks[0].tooltip == "Visit our site"
        assert result.shape_id == "shape123"
        assert result.linked_runs is None

    def test_multiple_hyperlinks_attachment(self):
        """Test MapperResult with multiple hyperlinks."""
        hyperlinks = [
            HyperlinkSpec(href="https://example.com", tooltip="External link"),
            HyperlinkSpec(href="slide:5", tooltip="Go to slide 5"),
            HyperlinkSpec(href="mailto:contact@example.com")
        ]

        result = self.create_basic_mapper_result(
            hyperlinks=hyperlinks,
            shape_id="multi_shape"
        )

        assert len(result.hyperlinks) == 3
        assert result.hyperlinks[0].href == "https://example.com"
        assert result.hyperlinks[1].href == "slide:5"
        assert result.hyperlinks[2].href == "mailto:contact@example.com"
        assert result.shape_id == "multi_shape"

    def test_text_run_hyperlinks(self):
        """Test MapperResult with text-level hyperlinks."""
        hyperlinks = [
            HyperlinkSpec(href="https://example.com"),
            HyperlinkSpec(href="mailto:test@example.com")
        ]

        linked_runs = [
            {'start': 0, 'end': 10, 'hyperlink_index': 0, 'text': 'click here'},
            {'start': 15, 'end': 30, 'hyperlink_index': 1, 'text': 'email us'}
        ]

        result = self.create_basic_mapper_result(
            hyperlinks=hyperlinks,
            shape_id="text_shape",
            linked_runs=linked_runs
        )

        assert len(result.hyperlinks) == 2
        assert len(result.linked_runs) == 2
        assert result.linked_runs[0]['hyperlink_index'] == 0
        assert result.linked_runs[1]['hyperlink_index'] == 1
        assert result.shape_id == "text_shape"

    def test_complex_hyperlink_scenario(self):
        """Test MapperResult with complex hyperlink setup."""
        # External and internal links
        hyperlinks = [
            HyperlinkSpec(href="https://docs.example.com", tooltip="Documentation"),
            HyperlinkSpec(href="slide:3", tooltip="Next slide"),
            HyperlinkSpec(href="tel:+1-555-0123", tooltip="Call us")
        ]

        # Multiple text runs with different hyperlinks
        linked_runs = [
            {'start': 0, 'end': 4, 'hyperlink_index': 0},   # "docs"
            {'start': 10, 'end': 14, 'hyperlink_index': 1}, # "next"
            {'start': 20, 'end': 24, 'hyperlink_index': 2}  # "call"
        ]

        result = self.create_basic_mapper_result(
            xml_content='<p:sp><p:nvSpPr><p:cNvPr id="5" name="complex_shape"/></p:nvSpPr></p:sp>',
            hyperlinks=hyperlinks,
            shape_id="complex_shape",
            linked_runs=linked_runs,
            metadata={'element_type': 'text_with_links'}
        )

        # Verify all hyperlinks
        assert len(result.hyperlinks) == 3
        assert result.hyperlinks[0].is_external_link() is True
        assert result.hyperlinks[1].is_internal_slide_link() is True
        assert result.hyperlinks[2].get_link_type().value == "external_tel"

        # Verify text run mapping
        assert len(result.linked_runs) == 3
        assert all('hyperlink_index' in run for run in result.linked_runs)

        # Verify shape identification
        assert result.shape_id == "complex_shape"
        assert 'complex_shape' in result.xml_content

    def test_hyperlink_fields_are_optional(self):
        """Test that all hyperlink fields are truly optional."""
        # Test with only hyperlinks
        result1 = self.create_basic_mapper_result(
            hyperlinks=[HyperlinkSpec(href="https://example.com")]
        )
        assert result1.hyperlinks is not None
        assert result1.shape_id is None
        assert result1.linked_runs is None

        # Test with only shape_id
        result2 = self.create_basic_mapper_result(
            shape_id="lone_shape"
        )
        assert result2.hyperlinks is None
        assert result2.shape_id == "lone_shape"
        assert result2.linked_runs is None

        # Test with only linked_runs
        result3 = self.create_basic_mapper_result(
            linked_runs=[{'start': 0, 'end': 5}]
        )
        assert result3.hyperlinks is None
        assert result3.shape_id is None
        assert result3.linked_runs is not None

    def test_empty_hyperlinks_list(self):
        """Test behavior with empty hyperlinks list."""
        result = self.create_basic_mapper_result(
            hyperlinks=[],  # Empty list
            shape_id="empty_links"
        )

        assert result.hyperlinks == []
        assert len(result.hyperlinks) == 0
        assert result.shape_id == "empty_links"

    def test_validation_still_works(self):
        """Test that existing validation still works with hyperlink fields."""
        # Test that quality validation still works
        with pytest.raises(ValueError, match="Quality must be 0.0-1.0"):
            self.create_basic_mapper_result(
                estimated_quality=1.5,  # Invalid
                hyperlinks=[HyperlinkSpec(href="https://example.com")]
            )

        # Test that performance validation still works
        with pytest.raises(ValueError, match="Performance must be 0.0-1.0"):
            self.create_basic_mapper_result(
                estimated_performance=-0.1,  # Invalid
                shape_id="test_shape"
            )

    def test_hyperlink_spec_integration(self):
        """Test that HyperlinkSpec objects work properly in MapperResult."""
        # Create various types of hyperlinks
        external_link = HyperlinkSpec(href="https://example.com", tooltip="External")
        internal_link = HyperlinkSpec(href="slide:10", tooltip="Internal")
        mailto_link = HyperlinkSpec(href="mailto:test@example.com", visited=False)

        result = self.create_basic_mapper_result(
            hyperlinks=[external_link, internal_link, mailto_link]
        )

        # Test that all hyperlink methods work
        assert result.hyperlinks[0].is_external_link() is True
        assert result.hyperlinks[1].is_internal_slide_link() is True
        assert result.hyperlinks[1].get_slide_number() == 10
        assert result.hyperlinks[2].visited is False

        # Test PowerPoint target generation
        assert result.hyperlinks[0].get_powerpoint_target() == "https://example.com"
        assert result.hyperlinks[1].get_powerpoint_target() == "../slides/slide10.xml"
        assert result.hyperlinks[2].get_powerpoint_target() == "mailto:test@example.com"

    def test_shape_id_for_linking(self):
        """Test shape ID usage for linking purposes."""
        # Test various shape ID formats
        shape_ids = [
            "shape1",           # Simple name
            "rect_123",         # Descriptive name
            "5",                # Numeric ID
            "group_item_2_3"    # Complex name
        ]

        for shape_id in shape_ids:
            result = self.create_basic_mapper_result(
                shape_id=shape_id,
                hyperlinks=[HyperlinkSpec(href="https://example.com")]
            )
            assert result.shape_id == shape_id

    def test_linked_runs_structure(self):
        """Test the structure and validation of linked_runs."""
        # Test typical linked runs structure
        linked_runs = [
            {
                'start': 0,
                'end': 10,
                'hyperlink_index': 0,
                'text': 'Click here',
                'style': {'bold': True}
            },
            {
                'start': 15,
                'end': 25,
                'hyperlink_index': 1,
                'text': 'or here',
                'style': {'underline': True}
            }
        ]

        result = self.create_basic_mapper_result(
            hyperlinks=[
                HyperlinkSpec(href="https://first.com"),
                HyperlinkSpec(href="https://second.com")
            ],
            linked_runs=linked_runs
        )

        assert len(result.linked_runs) == 2
        assert result.linked_runs[0]['start'] == 0
        assert result.linked_runs[0]['end'] == 10
        assert result.linked_runs[0]['hyperlink_index'] == 0
        assert 'text' in result.linked_runs[0]
        assert 'style' in result.linked_runs[0]

    def test_all_fields_combination(self):
        """Test MapperResult with all possible fields including hyperlinks."""
        hyperlinks = [HyperlinkSpec(href="https://example.com", tooltip="Test")]
        linked_runs = [{'start': 0, 'end': 5, 'hyperlink_index': 0}]
        media_files = [{'filename': 'test.emf', 'data': b'fake_data'}]

        result = MapperResult(
            element=Mock(),
            output_format=OutputFormat.EMF_VECTOR,
            xml_content='<complex_xml/>',
            policy_decision=PolicyDecision(use_native=False, reasons=[]),
            metadata={'complex': True},
            estimated_quality=0.8,
            estimated_performance=0.9,
            processing_time_ms=150.0,
            output_size_bytes=2048,
            compression_ratio=0.75,
            media_files=media_files,
            hyperlinks=hyperlinks,
            shape_id="comprehensive_shape",
            linked_runs=linked_runs
        )

        # Verify all fields work together
        assert result.element is not None
        assert result.output_format == OutputFormat.EMF_VECTOR
        assert result.policy_decision.use_native is False
        assert result.estimated_quality == 0.8
        assert result.estimated_performance == 0.9
        assert result.processing_time_ms == 150.0
        assert result.output_size_bytes == 2048
        assert result.compression_ratio == 0.75
        assert len(result.media_files) == 1
        assert len(result.hyperlinks) == 1
        assert result.shape_id == "comprehensive_shape"
        assert len(result.linked_runs) == 1
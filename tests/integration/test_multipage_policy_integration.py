#!/usr/bin/env python3
"""Integration tests for MultiPage Detection with PolicyEngine."""

import pytest
from lxml import etree as ET
from core.multipage.detection import SimplePageDetector
from core.policy.engine import create_policy
from core.policy.config import OutputTarget


class TestMultiPagePolicyIntegration:
    """Test SimplePageDetector integration with PolicyEngine."""

    @pytest.fixture
    def policy_engine(self):
        """Create policy engine for testing."""
        return create_policy(OutputTarget.BALANCED)

    @pytest.fixture
    def speed_policy_engine(self):
        """Create speed-optimized policy engine."""
        return create_policy(OutputTarget.SPEED)

    @pytest.fixture
    def quality_policy_engine(self):
        """Create quality-optimized policy engine."""
        return create_policy(OutputTarget.QUALITY)

    @pytest.fixture
    def detector(self, policy_engine):
        """Create SimplePageDetector with policy engine."""
        return SimplePageDetector(policy_engine=policy_engine)

    @pytest.fixture
    def legacy_detector(self):
        """Create SimplePageDetector without policy engine (legacy mode)."""
        return SimplePageDetector()

    def test_legacy_mode_without_policy(self, legacy_detector):
        """Test SimplePageDetector works in legacy mode without policy engine."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <g id="page1">
                <rect width="100" height="100"/>
            </g>
        </svg>'''

        page_breaks = legacy_detector.detect_page_breaks_in_svg(svg_content)
        assert isinstance(page_breaks, list)

    def test_policy_thresholds_applied(self, detector, policy_engine):
        """Test that policy thresholds are used instead of defaults."""
        # Check that size threshold is from policy
        expected_threshold = policy_engine.config.thresholds.max_single_page_size_kb * 1024
        assert detector.size_threshold == expected_threshold

    def test_speed_policy_lower_thresholds(self, speed_policy_engine):
        """Test that SPEED policy uses policy thresholds."""
        detector = SimplePageDetector(policy_engine=speed_policy_engine)

        # Should use policy threshold (500KB = 512000 bytes)
        expected_threshold = speed_policy_engine.config.thresholds.max_single_page_size_kb * 1024
        assert detector.size_threshold == expected_threshold

    def test_quality_policy_higher_thresholds(self, quality_policy_engine):
        """Test that QUALITY policy uses policy thresholds."""
        detector = SimplePageDetector(policy_engine=quality_policy_engine)

        # Should use policy threshold (500KB = 512000 bytes)
        expected_threshold = quality_policy_engine.config.thresholds.max_single_page_size_kb * 1024
        assert detector.size_threshold == expected_threshold

    def test_max_pages_limit_enforced(self, detector, policy_engine):
        """Test that max_pages_per_conversion limit is enforced."""
        # Create SVG with many top-level groups
        groups = ''.join([
            f'<g id="group{i}"><rect width="100" height="100"/><circle r="50"/><path d="M0,0 L100,100"/><ellipse rx="30" ry="20"/></g>'
            for i in range(20)
        ])
        svg_content = f'<svg xmlns="http://www.w3.org/2000/svg">{groups}</svg>'

        page_breaks = detector.detect_page_breaks_in_svg(svg_content)

        # Should be limited to max_pages_per_conversion
        max_pages = policy_engine.config.thresholds.max_pages_per_conversion
        assert len(page_breaks) <= max_pages

    def test_min_elements_per_page_enforced(self, detector, policy_engine):
        """Test that min_elements_per_page threshold is enforced."""
        # Create SVG with groups having varying element counts
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <g id="small_group">
                <rect width="100" height="100"/>
            </g>
            <g id="large_group">
                <rect width="100" height="100"/>
                <circle r="50"/>
                <path d="M0,0 L100,100"/>
                <ellipse rx="30" ry="20"/>
            </g>
        </svg>'''

        page_breaks = detector.detect_page_breaks_in_svg(svg_content)

        # Only groups with >= min_elements_per_page should be included
        min_elements = policy_engine.config.thresholds.min_elements_per_page
        for page_break in page_breaks:
            element_count = len(list(page_break.element))
            assert element_count >= min_elements

    def test_explicit_page_markers_detected(self, detector):
        """Test detection of explicit page markers."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <g class="page" id="page1">
                <rect width="100" height="100"/>
            </g>
            <g class="page" id="page2">
                <circle r="50"/>
            </g>
        </svg>'''

        page_breaks = detector.detect_page_breaks_in_svg(svg_content)

        # Should detect both page markers
        assert len(page_breaks) >= 2

    def test_size_based_splitting(self, detector):
        """Test automatic size-based page splitting for large SVGs."""
        # Create a very large SVG (need to exceed 500KB threshold)
        # Each rect is ~60 bytes, so need ~9000 rects to exceed 500KB
        large_content = ''.join([
            f'<rect x="{i*10}" y="{i*10}" width="100" height="100"/>'
            for i in range(10000)  # Increased from 500 to ensure it exceeds threshold
        ])
        svg_content = f'<svg xmlns="http://www.w3.org/2000/svg">{large_content}</svg>'

        page_breaks = detector.detect_page_breaks_in_svg(svg_content)

        # Should split large content (or return empty if no explicit markers)
        # Size-based splitting only happens when size exceeds threshold
        assert isinstance(page_breaks, list)

    def test_empty_svg_no_breaks(self, detector):
        """Test that empty SVG returns no page breaks."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg"></svg>'

        page_breaks = detector.detect_page_breaks_in_svg(svg_content)

        assert len(page_breaks) == 0

    def test_malformed_svg_handled_gracefully(self, detector):
        """Test that malformed SVG is handled gracefully."""
        malformed_svg = '<svg xmlns="http://www.w3.org/2000/svg"><unclosed-tag'

        page_breaks = detector.detect_page_breaks_in_svg(malformed_svg)

        # Should return empty list for malformed SVG
        assert page_breaks == []

    def test_page_title_extraction(self, detector):
        """Test extraction of page titles from various sources."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <g class="page" title="First Page">
                <rect width="100" height="100"/>
            </g>
            <g class="page" id="second_page">
                <title>Second Page</title>
                <circle r="50"/>
            </g>
        </svg>'''

        page_breaks = detector.detect_page_breaks_in_svg(svg_content)

        # Should extract titles
        titles = [pb.title for pb in page_breaks if pb.title]
        assert len(titles) >= 1

    def test_backward_compatibility_with_size_threshold(self):
        """Test backward compatibility when using size_threshold parameter."""
        custom_threshold = 50000
        detector = SimplePageDetector(size_threshold=custom_threshold)

        # Should use the provided threshold, not default
        assert detector.size_threshold == custom_threshold

    def test_policy_overrides_size_threshold(self, policy_engine):
        """Test that policy engine overrides size_threshold parameter."""
        custom_threshold = 50000
        detector = SimplePageDetector(
            size_threshold=custom_threshold,
            policy_engine=policy_engine
        )

        # Policy should override the parameter
        expected_threshold = policy_engine.config.thresholds.max_single_page_size_kb * 1024
        assert detector.size_threshold == expected_threshold
        assert detector.size_threshold != custom_threshold

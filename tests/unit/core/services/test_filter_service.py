#!/usr/bin/env python3
"""Unit tests for FilterService drop shadow handling."""

import math

import pytest
from lxml import etree as ET

from core.css.resolver import StyleContext
from core.services.filter_service import FilterService
from core.units import ConversionContext
from core.ir.effects import ShadowEffect


class TestFilterServiceDropShadow:
    """Tests for feDropShadow conversion via FilterService."""

    @pytest.fixture
    def style_context(self) -> StyleContext:
        """Provide a basic style context with default DPI."""
        return StyleContext(
            conversion=ConversionContext(dpi=96.0, width=800.0, height=600.0),
            viewport_width=800.0,
            viewport_height=600.0,
        )

    def test_resolve_effects_returns_shadow_effect(self, style_context: StyleContext):
        """FilterService should resolve feDropShadow into ShadowEffect IR."""
        filter_service = FilterService()
        filter_xml = ET.fromstring(
            '''
            <filter id="shadow1" xmlns="http://www.w3.org/2000/svg">
                <feDropShadow dx="4" dy="3" stdDeviation="2"
                              flood-color="#123456" flood-opacity="0.4"/>
            </filter>
            '''
        )

        filter_service.register_filter('shadow1', filter_xml)
        effects = filter_service.resolve_effects('url(#shadow1)', style_context)

        assert len(effects) == 1
        shadow = effects[0]
        assert isinstance(shadow, ShadowEffect)
        assert shadow.color == "123456"
        assert shadow.alpha == pytest.approx(0.4)

        # 2px blur → 1.5pt at 96 DPI
        assert shadow.blur_radius == pytest.approx(1.5)

        # dx=4, dy=3 → 3.75pt distance with ~36.87° angle
        assert shadow.distance == pytest.approx(math.hypot(3.0, 2.25))
        assert shadow.angle == pytest.approx(36.8698976, abs=1e-6)

    def test_get_filter_content_emits_outer_shadow(self, style_context: StyleContext):
        """Native conversion should emit outer shadow DrawingML."""
        filter_service = FilterService()
        filter_xml = ET.fromstring(
            '''
            <filter id="shadow2" xmlns="http://www.w3.org/2000/svg">
                <feDropShadow dx="4" dy="3" stdDeviation="2"
                              flood-color="#123456" flood-opacity="0.4"/>
            </filter>
            '''
        )

        filter_service.register_filter('shadow2', filter_xml)
        drawingml = filter_service.get_filter_content('shadow2', style_context)

        assert drawingml is not None
        assert '<a:outerShdw' in drawingml

        # Validate numeric conversions
        assert 'blurRad="19050"' in drawingml  # 1.5pt → 19050 EMU
        assert 'dist="47625"' in drawingml     # 3.75pt → 47625 EMU
        assert 'dir="2212193"' in drawingml    # ~36.87° → 2,212,193
        assert 'val="123456"' in drawingml
        assert 'val="40000"' in drawingml      # 0.4 opacity

    def test_style_declarations_used_for_color_and_opacity(self, style_context: StyleContext):
        """Style attribute fallback should be respected for drop shadow styling."""
        filter_service = FilterService()
        filter_xml = ET.fromstring(
            '''
            <filter id="shadow3" xmlns="http://www.w3.org/2000/svg">
                <feDropShadow dx="-2" dy="0" stdDeviation="1.5"
                              style="flood-color: rgba(255, 0, 0, 0.5); flood-opacity: 65%;"/>
            </filter>
            '''
        )

        filter_service.register_filter('shadow3', filter_xml)
        effects = filter_service.resolve_effects('url(#shadow3)', style_context)

        assert len(effects) == 1
        shadow = effects[0]
        assert shadow.color == "FF0000"
        assert shadow.alpha == pytest.approx(0.65)

        # Direction should reflect negative dx (shadow to the left)
        assert shadow.angle == pytest.approx(180.0)

#!/usr/bin/env python3
"""Unit tests for effect XML generation"""

import pytest
from lxml import etree as ET

from core.ir.effects import (
    BlurEffect,
    ShadowEffect,
    GlowEffect,
    SoftEdgeEffect,
    ReflectionEffect,
)
from core.map.shape_helpers import generate_effects_xml, generate_shape_properties_xml


class TestGenerateEffectsXML:
    """Tests for generate_effects_xml()"""

    def test_empty_effects_list(self):
        """Test that empty effects list returns empty string"""
        xml = generate_effects_xml([])
        assert xml == ''

    def test_none_effects_list(self):
        """Test that None effects list returns empty string"""
        xml = generate_effects_xml(None)
        assert xml == ''

    def test_blur_effect_xml(self):
        """Test BlurEffect XML generation"""
        effects = [BlurEffect(radius=5.0)]
        xml = generate_effects_xml(effects)

        assert '<a:effectLst>' in xml
        assert '<a:blur rad="63500"/>' in xml  # 5.0 * 12700
        assert '</a:effectLst>' in xml

    def test_shadow_effect_xml(self):
        """Test ShadowEffect XML generation"""
        effects = [ShadowEffect(
            blur_radius=3.0,
            distance=2.0,
            angle=45.0,
            color="FF0000",
            alpha=0.75
        )]
        xml = generate_effects_xml(effects)

        assert '<a:effectLst>' in xml
        assert '<a:outerShdw' in xml
        assert 'blurRad="38100"' in xml  # 3.0 * 12700
        assert 'dist="25400"' in xml     # 2.0 * 12700
        assert 'dir="2700000"' in xml    # 45 * 60000
        assert 'rotWithShape="0"' in xml
        assert 'val="FF0000"' in xml
        assert 'val="75000"' in xml      # 0.75 * 100000

    def test_glow_effect_xml(self):
        """Test GlowEffect XML generation"""
        effects = [GlowEffect(radius=4.0, color="00FF00")]
        xml = generate_effects_xml(effects)

        assert '<a:glow rad="50800">' in xml  # 4.0 * 12700
        assert 'val="00FF00"' in xml

    def test_soft_edge_effect_xml(self):
        """Test SoftEdgeEffect XML generation"""
        effects = [SoftEdgeEffect(radius=2.5)]
        xml = generate_effects_xml(effects)

        assert '<a:softEdge rad="31750"/>' in xml  # 2.5 * 12700

    def test_reflection_effect_xml(self):
        """Test ReflectionEffect XML generation"""
        effects = [ReflectionEffect(
            blur_radius=3.0,
            start_alpha=0.5,
            end_alpha=0.1,
            distance=1.0
        )]
        xml = generate_effects_xml(effects)

        assert '<a:reflection' in xml
        assert 'blurRad="38100"' in xml  # 3.0 * 12700
        assert 'stA="50000"' in xml      # 0.5 * 100000
        assert 'endA="10000"' in xml     # 0.1 * 100000
        assert 'dist="12700"' in xml     # 1.0 * 12700

    def test_multiple_effects(self):
        """Test multiple effects in single list"""
        effects = [
            BlurEffect(radius=2.0),
            ShadowEffect(blur_radius=1, distance=1, angle=90),
            GlowEffect(radius=3.0),
        ]
        xml = generate_effects_xml(effects)

        assert '<a:effectLst>' in xml
        assert '<a:blur rad="25400"/>' in xml
        assert '<a:outerShdw' in xml
        assert '<a:glow rad="38100">' in xml
        assert '</a:effectLst>' in xml

    def test_all_effect_types(self):
        """Test all 5 effect types together"""
        effects = [
            BlurEffect(radius=1.0),
            ShadowEffect(blur_radius=1, distance=0.5, angle=0),
            GlowEffect(radius=2.0),
            SoftEdgeEffect(radius=1.5),
            ReflectionEffect(),
        ]
        xml = generate_effects_xml(effects)

        assert '<a:blur' in xml
        assert '<a:outerShdw' in xml
        assert '<a:glow' in xml
        assert '<a:softEdge' in xml
        assert '<a:reflection' in xml

    def test_xml_well_formed(self):
        """Test that generated XML is well-formed"""
        effects = [
            BlurEffect(radius=5.0),
            ShadowEffect(blur_radius=2, distance=1, angle=45),
        ]
        xml = generate_effects_xml(effects)

        # Wrap in root element with namespace for parsing
        wrapped = f'<root xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">{xml}</root>'
        root = ET.fromstring(wrapped)

        # Should have effectLst element
        ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
        effect_lst = root.find('.//a:effectLst', ns)
        assert effect_lst is not None

        # Should have 2 effect elements
        effects_found = len(effect_lst)
        assert effects_found == 2


class TestGenerateShapePropertiesWithEffects:
    """Tests for generate_shape_properties_xml() with effects"""

    def test_shape_properties_without_effects(self):
        """Test backward compatibility - no effects"""
        xml = generate_shape_properties_xml(
            x_emu=0,
            y_emu=0,
            width_emu=100000,
            height_emu=100000,
            preset_name='ellipse'
        )

        assert '<p:spPr>' in xml
        assert '<a:prstGeom prst="ellipse">' in xml
        assert '<a:effectLst>' not in xml  # No effects

    def test_shape_properties_with_blur(self):
        """Test shape properties with blur effect"""
        effects = [BlurEffect(radius=3.0)]
        xml = generate_shape_properties_xml(
            x_emu=0,
            y_emu=0,
            width_emu=100000,
            height_emu=100000,
            preset_name='rect',
            effects=effects
        )

        assert '<a:prstGeom prst="rect">' in xml
        assert '<a:effectLst>' in xml
        assert '<a:blur rad="38100"/>' in xml

        # Verify ordering: xfrm → prstGeom → effectLst → fill → stroke
        assert xml.index('<a:prstGeom') < xml.index('<a:effectLst')
        assert xml.index('<a:effectLst') < xml.index('<a:noFill')

    def test_shape_properties_with_multiple_effects(self):
        """Test shape properties with multiple effects"""
        effects = [
            BlurEffect(radius=2.0),
            ShadowEffect(blur_radius=1, distance=1, angle=45),
        ]
        xml = generate_shape_properties_xml(
            x_emu=0,
            y_emu=0,
            width_emu=100000,
            height_emu=100000,
            preset_name='roundRect',
            effects=effects
        )

        assert '<a:blur' in xml
        assert '<a:outerShdw' in xml

    def test_shape_properties_xml_well_formed(self):
        """Test that shape properties XML is well-formed"""
        effects = [GlowEffect(radius=3.0, color="FFFF00")]
        xml = generate_shape_properties_xml(
            x_emu=100000,
            y_emu=200000,
            width_emu=500000,
            height_emu=300000,
            preset_name='ellipse',
            effects=effects
        )

        # Wrap in presentation namespace
        wrapped = f'''<root xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                            xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
            {xml}
        </root>'''
        root = ET.fromstring(wrapped)

        ns = {
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
        }

        # Verify structure
        sp_pr = root.find('.//p:spPr', ns)
        assert sp_pr is not None

        xfrm = sp_pr.find('.//a:xfrm', ns)
        assert xfrm is not None

        prst_geom = sp_pr.find('.//a:prstGeom', ns)
        assert prst_geom is not None
        assert prst_geom.get('prst') == 'ellipse'

        effect_lst = sp_pr.find('.//a:effectLst', ns)
        assert effect_lst is not None

        glow = effect_lst.find('.//a:glow', ns)
        assert glow is not None


class TestEffectXMLEdgeCases:
    """Edge case tests for effect XML generation"""

    def test_zero_radius_blur(self):
        """Test blur with zero radius"""
        effects = [BlurEffect(radius=0.0)]
        xml = generate_effects_xml(effects)
        assert '<a:blur rad="0"/>' in xml

    def test_shadow_with_zero_alpha(self):
        """Test shadow with zero alpha (invisible)"""
        effects = [ShadowEffect(
            blur_radius=1,
            distance=1,
            angle=0,
            alpha=0.0
        )]
        xml = generate_effects_xml(effects)
        assert 'val="0"' in xml  # Alpha value

    def test_shadow_with_360_degree_angle(self):
        """Test shadow with 360° angle (wraps to 0°)"""
        effects = [ShadowEffect(blur_radius=1, distance=1, angle=360)]
        xml = generate_effects_xml(effects)
        # 360 * 60000 % 21600000 = 0
        assert 'dir="0"' in xml or 'dir="21600000"' in xml

    def test_large_effect_values(self):
        """Test with large effect values"""
        effects = [
            BlurEffect(radius=100.0),
            ShadowEffect(blur_radius=50, distance=50, angle=180),
        ]
        xml = generate_effects_xml(effects)
        assert '<a:blur rad="1270000"/>' in xml  # 100 * 12700
        assert 'blurRad="635000"' in xml         # 50 * 12700
        assert 'dist="635000"' in xml

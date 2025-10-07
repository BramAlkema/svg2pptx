#!/usr/bin/env python3
"""
E2E Test: Native Shapes with DrawingML Effects

Validates that DrawingML effects (blur, shadow, glow, soft edge, reflection)
are correctly applied to native PowerPoint shapes and render in PPTX output.

Tests:
1. Single effect on each shape type
2. Multiple effects combined
3. Effect XML structure and values
4. Policy clamping and governance
"""

import pytest
from pathlib import Path
from lxml import etree as ET

from core.ir.shapes import Circle, Ellipse, Rectangle
from core.ir.geometry import Point, Rect
from core.ir.paint import SolidPaint
from core.ir.effects import (
    BlurEffect, ShadowEffect, GlowEffect,
    SoftEdgeEffect, ReflectionEffect
)
from core.map.circle_mapper import CircleMapper
from core.map.ellipse_mapper import EllipseMapper
from core.map.rect_mapper import RectangleMapper


class TestNativeShapesWithEffects:
    """E2E validation of DrawingML effects on native shapes"""

    def test_circle_with_blur_effect(self):
        """Test circle with blur effect generates correct DrawingML"""
        circle = Circle(
            center=Point(100, 100),
            radius=50,
            fill=SolidPaint(rgb="FF0000"),
            effects=[BlurEffect(radius=5.0)]
        )

        mapper = CircleMapper()
        result = mapper.map(circle)

        assert result.output_format.value == "native_dml"
        assert '<a:effectLst>' in result.xml_content
        assert '<a:blur rad="63500"/>' in result.xml_content  # 5.0pt * 12700

    def test_ellipse_with_shadow_effect(self):
        """Test ellipse with drop shadow effect"""
        ellipse = Ellipse(
            center=Point(200, 150),
            radius_x=80,
            radius_y=50,
            fill=SolidPaint(rgb="00FF00"),
            effects=[ShadowEffect(
                blur_radius=3.0,
                distance=4.0,
                angle=45.0,
                color="000000",
                alpha=0.5
            )]
        )

        mapper = EllipseMapper()
        result = mapper.map(ellipse)

        assert '<a:effectLst>' in result.xml_content
        assert '<a:outerShdw' in result.xml_content
        assert 'blurRad="38100"' in result.xml_content  # 3.0pt * 12700
        assert 'dist="50800"' in result.xml_content     # 4.0pt * 12700
        assert 'dir="2700000"' in result.xml_content    # 45° * 60000
        assert '<a:srgbClr val="000000">' in result.xml_content
        assert '<a:alpha val="50000"/>' in result.xml_content  # 0.5 * 100000

    def test_rectangle_with_glow_effect(self):
        """Test rectangle with glow effect"""
        rect = Rectangle(
            bounds=Rect(x=50, y=50, width=200, height=100),
            fill=SolidPaint(rgb="0000FF"),
            effects=[GlowEffect(radius=6.0, color="FFFFFF")]
        )

        mapper = RectangleMapper()
        result = mapper.map(rect)

        assert '<a:effectLst>' in result.xml_content
        assert '<a:glow rad="76200">' in result.xml_content  # 6.0pt * 12700
        assert '<a:srgbClr val="FFFFFF"/>' in result.xml_content

    def test_circle_with_soft_edge_effect(self):
        """Test circle with soft edge (feathered edge) effect"""
        circle = Circle(
            center=Point(150, 150),
            radius=60,
            fill=SolidPaint(rgb="FFFF00"),
            effects=[SoftEdgeEffect(radius=4.0)]
        )

        mapper = CircleMapper()
        result = mapper.map(circle)

        assert '<a:effectLst>' in result.xml_content
        assert '<a:softEdge rad="50800"/>' in result.xml_content  # 4.0pt * 12700

    def test_rectangle_with_reflection_effect(self):
        """Test rectangle with reflection effect"""
        rect = Rectangle(
            bounds=Rect(x=100, y=100, width=150, height=80),
            fill=SolidPaint(rgb="FF00FF"),
            effects=[ReflectionEffect(
                blur_radius=2.0,
                start_alpha=0.6,
                end_alpha=0.0,
                distance=3.0
            )]
        )

        mapper = RectangleMapper()
        result = mapper.map(rect)

        assert '<a:effectLst>' in result.xml_content
        assert '<a:reflection' in result.xml_content
        assert 'blurRad="25400"' in result.xml_content  # 2.0pt * 12700
        assert 'stA="60000"' in result.xml_content      # 0.6 * 100000
        assert 'endA="0"' in result.xml_content         # 0.0 * 100000
        assert 'dist="38100"' in result.xml_content     # 3.0pt * 12700

    def test_ellipse_with_multiple_effects(self):
        """Test ellipse with multiple effects combined"""
        ellipse = Ellipse(
            center=Point(250, 200),
            radius_x=100,
            radius_y=60,
            fill=SolidPaint(rgb="00FFFF"),
            effects=[
                BlurEffect(radius=2.0),
                ShadowEffect(
                    blur_radius=3.0,
                    distance=5.0,
                    angle=90.0,
                    color="808080",
                    alpha=0.4
                ),
                GlowEffect(radius=4.0, color="FFFF00")
            ]
        )

        mapper = EllipseMapper()
        result = mapper.map(ellipse)

        # Verify all three effects present
        assert '<a:effectLst>' in result.xml_content
        assert '<a:blur rad="25400"/>' in result.xml_content  # 2.0pt
        assert '<a:outerShdw' in result.xml_content
        assert 'blurRad="38100"' in result.xml_content  # 3.0pt
        assert 'dist="63500"' in result.xml_content     # 5.0pt
        assert '<a:glow rad="50800">' in result.xml_content  # 4.0pt

    def test_shape_without_effects(self):
        """Test that shapes without effects don't generate effectLst"""
        circle = Circle(
            center=Point(100, 100),
            radius=50,
            fill=SolidPaint(rgb="FF0000"),
            effects=[]  # No effects
        )

        mapper = CircleMapper()
        result = mapper.map(circle)

        # Should not have effectLst element
        assert '<a:effectLst>' not in result.xml_content

    def test_effect_xml_element_ordering(self):
        """Test that effects appear in correct position (after geometry, before fill/stroke)"""
        rect = Rectangle(
            bounds=Rect(x=50, y=50, width=100, height=100),
            fill=SolidPaint(rgb="FF0000"),
            effects=[BlurEffect(radius=3.0)]
        )

        mapper = RectangleMapper()
        result = mapper.map(rect)

        # Parse XML to verify element ordering
        xml_fragment = f'<root xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">{result.xml_content}</root>'
        root = ET.fromstring(xml_fragment.encode('utf-8'))

        # Find spPr element
        ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
              'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}
        sp_pr = root.find('.//p:spPr', ns)
        assert sp_pr is not None

        # Check child element ordering
        children = list(sp_pr)
        tags = [child.tag for child in children]

        # Extract local names (remove namespace)
        local_tags = [tag.split('}')[-1] for tag in tags]

        # Expected order: xfrm, prstGeom, effectLst, (fill), (stroke)
        assert 'xfrm' in local_tags
        assert 'prstGeom' in local_tags
        assert 'effectLst' in local_tags

        # effectLst should come after prstGeom
        xfrm_idx = local_tags.index('xfrm')
        geom_idx = local_tags.index('prstGeom')
        effect_idx = local_tags.index('effectLst')

        assert xfrm_idx < geom_idx < effect_idx

    def test_shadow_angle_conversion(self):
        """Test that shadow angles are correctly converted to DrawingML direction values"""
        test_cases = [
            (0.0, 0),           # 0° → 0
            (45.0, 2700000),    # 45° * 60000
            (90.0, 5400000),    # 90° * 60000
            (180.0, 10800000),  # 180° * 60000
            (270.0, 16200000),  # 270° * 60000
            (360.0, 0),         # 360° wraps to 0°
        ]

        for angle, expected_dir in test_cases:
            circle = Circle(
                center=Point(100, 100),
                radius=50,
                fill=SolidPaint(rgb="FF0000"),
                effects=[ShadowEffect(
                    blur_radius=2.0,
                    distance=3.0,
                    angle=angle,
                    color="000000",
                    alpha=0.5
                )]
            )

            mapper = CircleMapper()
            result = mapper.map(circle)

            assert f'dir="{expected_dir}"' in result.xml_content

    def test_effect_emu_precision(self):
        """Test that EMU conversions maintain precision"""
        # Test fractional point values
        circle = Circle(
            center=Point(100, 100),
            radius=50,
            fill=SolidPaint(rgb="FF0000"),
            effects=[
                BlurEffect(radius=2.5),      # 2.5pt → 31750 EMU
                ShadowEffect(
                    blur_radius=3.75,        # 3.75pt → 47625 EMU
                    distance=1.25,           # 1.25pt → 15875 EMU
                    angle=45.0,
                    color="000000",
                    alpha=0.5
                )
            ]
        )

        mapper = CircleMapper()
        result = mapper.map(circle)

        assert '<a:blur rad="31750"/>' in result.xml_content
        assert 'blurRad="47625"' in result.xml_content
        assert 'dist="15875"' in result.xml_content


class TestEffectPolicyIntegration:
    """Test that effects policy can be integrated (framework test)"""

    def test_effects_policy_can_process_effects(self):
        """Framework test: verify EffectsPolicy can process effect lists"""
        from core.policy.effects_policy import EffectsPolicy, EffectCaps

        effects = [
            BlurEffect(radius=5.0),
            ShadowEffect(blur_radius=3.0, distance=4.0, angle=45.0),
            GlowEffect(radius=6.0)
        ]

        policy = EffectsPolicy()
        decided_effects = policy.decide_effects(effects, shape_type="Circle")

        # All effects should be allowed with default caps
        assert len(decided_effects) == 3
        assert isinstance(decided_effects[0], BlurEffect)
        assert isinstance(decided_effects[1], ShadowEffect)
        assert isinstance(decided_effects[2], GlowEffect)

    def test_effects_policy_clamping(self):
        """Framework test: verify policy clamps oversized effects"""
        from core.policy.effects_policy import EffectsPolicy, EffectCaps

        # Create effect exceeding default caps
        effects = [
            BlurEffect(radius=15.0),  # Exceeds max_blur_pt=8.0
        ]

        policy = EffectsPolicy()
        decided_effects = policy.decide_effects(effects)

        # Should be clamped to max
        assert len(decided_effects) == 1
        assert decided_effects[0].radius == 8.0  # Clamped

    def test_conservative_mode_drops_all_effects(self):
        """Framework test: verify conservative mode drops all effects"""
        from core.policy.effects_policy import EffectsPolicy, EffectCaps

        effects = [
            BlurEffect(radius=5.0),
            ShadowEffect(blur_radius=3.0, distance=4.0, angle=45.0),
        ]

        caps = EffectCaps(conservative_mode=True)
        policy = EffectsPolicy(caps=caps)
        decided_effects = policy.decide_effects(effects)

        # All effects should be dropped
        assert len(decided_effects) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

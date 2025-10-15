#!/usr/bin/env python3
"""Coverage for lighting/filter animation helpers in xml_builder."""

from __future__ import annotations

from textwrap import dedent

import pytest
from lxml import etree as ET

from core.utils.xml_builder.animation import AnimationGenerator
from core.utils.xml_builder.effects.filters import FilterEffectGenerator
from core.utils.xml_builder.effects.lighting import LightingEffectGenerator


class StubBuilder:
    """Minimal builder stub providing template access and serialization."""

    def __init__(self) -> None:
        self.templates = {
            "diffuse_lighting_3d.xml": dedent(
                """
                <a:scene3d xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                    <a:sp3d>
                        <a:bevelT w="1" h="1"/>
                        <a:lightRig rig="tl"/>
                    </a:sp3d>
                </a:scene3d>
                """
            ).strip(),
            "diffuse_lighting_with_shadow.xml": dedent(
                """
                <a:scene3d xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                    <a:sp3d>
                        <a:bevelT w="1" h="1"/>
                        <a:lightRig rig="tl"/>
                    </a:sp3d>
                    <a:innerShdw blurRad="1">
                        <a:alpha val="10000"/>
                    </a:innerShdw>
                </a:scene3d>
                """
            ).strip(),
            "specular_highlight.xml": dedent(
                """
                <a:scene3d xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                    <a:sp3d extrusionH="1" contourW="1" prstMaterial="plastic">
                        <a:lightRig dir="tl"/>
                    </a:sp3d>
                    <a:outerShdw blurRad="1">
                        <a:srgbClr val="FFFFFF"><a:alpha val="60000"/></a:srgbClr>
                    </a:outerShdw>
                </a:scene3d>
                """
            ).strip(),
            "reflection_effect.xml": dedent(
                """
                <a:scene3d xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                    <a:sp3d extrusionH="1" contourW="1" prstMaterial="metal">
                        <a:lightRig dir="tl"/>
                    </a:sp3d>
                    <a:reflection blurRad="1" stA="50000"/>
                </a:scene3d>
                """
            ).strip(),
        }
        self.next_id = 1

    def load_template(self, name: str) -> ET._Element:
        try:
            return ET.fromstring(self.templates[name])
        except KeyError as exc:
            raise FileNotFoundError(name) from exc

    @staticmethod
    def element_to_string(element: ET._Element) -> str:
        return ET.tostring(element, encoding="unicode")

    def get_next_id(self) -> int:
        value = self.next_id
        self.next_id += 1
        return value


@pytest.fixture()
def lighting_builder() -> StubBuilder:
    return StubBuilder()


def test_generate_diffuse_lighting_with_shadow(lighting_builder):
    generator = LightingEffectGenerator(lighting_builder)
    element = generator.generate_diffuse_lighting_3d(
        light_direction="br",
        bevel_width=32000,
        bevel_height=16000,
        with_shadow=True,
        shadow_blur=50000,
        shadow_alpha=20000,
    )

    bevel = element.find(".//a:bevelT", namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"})
    assert bevel.get("w") == "32000"
    assert bevel.get("h") == "16000"

    light_rig = element.find(".//a:lightRig", namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"})
    assert light_rig.get("rig") == "br"

    inner_shadow = element.find(".//a:innerShdw", namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"})
    assert inner_shadow.get("blurRad") == "50000"
    alpha = inner_shadow.find(".//a:alpha", namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"})
    assert alpha.get("val") == "20000"


def test_generate_diffuse_lighting_without_shadow(lighting_builder):
    generator = LightingEffectGenerator(lighting_builder)
    element = generator.generate_diffuse_lighting_3d(
        light_direction="l",
        bevel_width=21000,
        bevel_height=11000,
        with_shadow=False,
    )

    light_rig = element.find(".//a:lightRig", namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"})
    assert light_rig.get("rig") == "l"
    assert element.find(".//a:innerShdw", namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}) is None


@pytest.mark.parametrize(
    ("shininess", "expected"),
    [
        (0.5, "flat"),
        (2.0, "matte"),
        (8.0, "plastic"),
        (24.0, "softEdge"),
        (48.0, "metal"),
        (90.0, "warmMatte"),
        (200.0, "clear"),
    ],
)
def test_map_shininess_to_material(shininess, expected):
    assert LightingEffectGenerator.map_shininess_to_material(shininess) == expected


def test_specular_highlight_updates_material_and_color(lighting_builder):
    generator = LightingEffectGenerator(lighting_builder)
    element = generator.generate_specular_highlight_3d(
        light_direction="t",
        bevel_width=10000,
        bevel_height=5000,
        material="plastic",
        highlight_blur=7000,
        highlight_alpha=42000,
        highlight_color="ABCDEF",
    )

    sp3d = element.find(".//a:sp3d", namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"})
    assert sp3d.get("prstMaterial") == "plastic"
    assert sp3d.get("extrusionH") == "10000"

    srgb = element.find(".//a:srgbClr", namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"})
    assert srgb.get("val") == "ABCDEF"


def test_reflection_effect_adjusts_blur_and_material(lighting_builder):
    generator = LightingEffectGenerator(lighting_builder)
    element = generator.generate_reflection_effect_3d(
        light_direction="r",
        bevel_width=40000,
        bevel_height=20000,
        material="clear",
        reflection_blur=1234,
        reflection_alpha=56789,
    )

    reflection = element.find(".//a:reflection", namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"})
    assert reflection.get("blurRad") == "1234"
    assert reflection.get("stA") == "56789"


def test_filter_generator_selects_shadow_based_on_surface_scale(lighting_builder):
    lighting = LightingEffectGenerator(lighting_builder)
    filter_gen = FilterEffectGenerator(lighting_builder, lighting)

    xml = filter_gen.generate_diffuse_lighting_for_filter(
        light_type="distant",
        light_params={"azimuth": 180},
        surface_scale=2.5,
        diffuse_constant=0.75,
    )

    assert 'rig="r"' in xml  # light direction mapping
    assert "innerShdw" in xml  # with_shadow path


def test_filter_generator_chooses_reflection_for_high_exponent(lighting_builder):
    lighting = LightingEffectGenerator(lighting_builder)
    filter_gen = FilterEffectGenerator(lighting_builder, lighting)

    xml = filter_gen.generate_specular_lighting_for_filter(
        light_type="distant",
        light_params={"azimuth": 10},
        surface_scale=1.2,
        specular_constant=2.0,
        specular_exponent=128.0,
        lighting_color="00FF00",
    )

    assert "reflection" in xml
    assert 'prstMaterial="warmMatte"' in xml
    assert 'blurRad="3810"' in xml


def test_filter_generator_uses_highlight_for_moderate_exponent(lighting_builder):
    lighting = LightingEffectGenerator(lighting_builder)
    filter_gen = FilterEffectGenerator(lighting_builder, lighting)

    xml = filter_gen.generate_specular_lighting_for_filter(
        light_type="distant",
        light_params={"azimuth": 200},
        surface_scale=0.5,
        specular_constant=1.5,
        specular_exponent=32.0,
        lighting_color="112233",
    )

    assert "outerShdw" in xml
    assert "112233" in xml


def test_filter_generator_diffuse_without_shadow(lighting_builder):
    lighting = LightingEffectGenerator(lighting_builder)
    filter_gen = FilterEffectGenerator(lighting_builder, lighting)

    xml = filter_gen.generate_diffuse_lighting_for_filter(
        light_type=None,
        light_params={},
        surface_scale=0.5,
        diffuse_constant=0.25,
    )

    assert 'rig="tl"' in xml  # default direction
    assert "innerShdw" not in xml  # no shadow path


def test_filter_generator_diffuse_direction_variants(lighting_builder):
    lighting = LightingEffectGenerator(lighting_builder)
    filter_gen = FilterEffectGenerator(lighting_builder, lighting)

    xml_t = filter_gen.generate_diffuse_lighting_for_filter(
        light_type="distant",
        light_params={"azimuth": 10},
        surface_scale=1.3,
        diffuse_constant=1.5,
    )
    assert 'rig="t"' in xml_t

    xml_tr = filter_gen.generate_diffuse_lighting_for_filter(
        light_type="distant",
        light_params={"azimuth": 60},
        surface_scale=1.2,
        diffuse_constant=2.0,
    )
    assert 'rig="tr"' in xml_tr
    assert 'w="30480"' in xml_tr
    assert 'val="25000"' in xml_tr  # shadow alpha capped

    xml_br = filter_gen.generate_diffuse_lighting_for_filter(
        light_type="distant",
        light_params={"azimuth": 270},
        surface_scale=1.5,
        diffuse_constant=0.5,
    )
    assert 'rig="br"' in xml_br


def test_animation_generator_creates_sequence():
    builder = StubBuilder()
    generator = AnimationGenerator(builder)  # type: ignore[arg-type]

    anim = generator.create_animation_element(
        "fade",
        target_shape_id=42,
        duration=1.5,
        delay=0.25,
    )

    assert anim.tag.endswith("par")
    child = anim.find(".//{http://schemas.openxmlformats.org/presentationml/2006/main}animEffect")
    assert child is not None
    assert child.get("filter") == "fade"
    tgt = anim.find(".//{http://schemas.openxmlformats.org/presentationml/2006/main}spTgt")
    assert tgt.get("spid") == "42"


def test_filter_generator_specular_low_exponent(lighting_builder):
    lighting = LightingEffectGenerator(lighting_builder)
    filter_gen = FilterEffectGenerator(lighting_builder, lighting)

    xml = filter_gen.generate_specular_lighting_for_filter(
        light_type="distant",
        light_params={"azimuth": 350},
        surface_scale=0.25,
        specular_constant=0.5,
        specular_exponent=4.0,
        lighting_color="445566",
    )

    assert 'dir="t"' in xml  # azimuth -> top
    assert "reflection" not in xml  # highlight branch
    assert "445566" in xml


def test_filter_generator_specular_alpha_cap(lighting_builder):
    lighting = LightingEffectGenerator(lighting_builder)
    filter_gen = FilterEffectGenerator(lighting_builder, lighting)

    xml = filter_gen.generate_specular_lighting_for_filter(
        light_type="distant",
        light_params={"azimuth": 140},
        surface_scale=3.0,
        specular_constant=3.5,
        specular_exponent=120.0,
        lighting_color="AA5500",
    )

    assert "reflection" in xml
    assert 'stA="80000"' in xml  # alpha capped


def test_filter_generator_specular_default_direction(lighting_builder):
    lighting = LightingEffectGenerator(lighting_builder)
    filter_gen = FilterEffectGenerator(lighting_builder, lighting)

    xml = filter_gen.generate_specular_lighting_for_filter(
        light_type=None,
        light_params={},
        surface_scale=-0.75,
        specular_constant=0.8,
        specular_exponent=20.0,
    )

    assert 'dir="tl"' in xml  # fallback direction for non-distant light


def test_filter_generator_specular_direction_variants(lighting_builder):
    lighting = LightingEffectGenerator(lighting_builder)
    filter_gen = FilterEffectGenerator(lighting_builder, lighting)

    xml_tr = filter_gen.generate_specular_lighting_for_filter(
        light_type="distant",
        light_params={"azimuth": 80},
        surface_scale=0.9,
        specular_constant=1.0,
        specular_exponent=48.0,
    )
    assert 'dir="tr"' in xml_tr

    xml_br = filter_gen.generate_specular_lighting_for_filter(
        light_type="distant",
        light_params={"azimuth": 260},
        surface_scale=1.1,
        specular_constant=0.9,
        specular_exponent=18.0,
    )
    assert 'dir="br"' in xml_br

"""Lighting effect generator helpers."""

from __future__ import annotations

from lxml.etree import Element

from ..constants import A_URI, NSMAP


class LightingEffectGenerator:
    """Generate lighting/effects elements from templates."""

    def __init__(self, builder) -> None:
        self.builder = builder

    def generate_diffuse_lighting_3d(
        self,
        light_direction: str = "tl",
        bevel_width: int = 50800,
        bevel_height: int = 25400,
        *,
        with_shadow: bool = False,
        shadow_blur: int = 25400,
        shadow_alpha: int = 25000,
    ) -> Element:
        template_name = (
            "diffuse_lighting_with_shadow.xml"
            if with_shadow
            else "diffuse_lighting_3d.xml"
        )
        lighting_element = self.builder.load_template(template_name)

        bevel_t = lighting_element.find(".//a:bevelT", NSMAP)
        if bevel_t is not None:
            bevel_t.set("w", str(bevel_width))
            bevel_t.set("h", str(bevel_height))

        light_rig = lighting_element.find(".//a:lightRig", NSMAP)
        if light_rig is not None:
            light_rig.set("rig", light_direction)

        if with_shadow:
            inner_shdw = lighting_element.find(".//a:innerShdw", NSMAP)
            if inner_shdw is not None:
                inner_shdw.set("blurRad", str(shadow_blur))
                alpha_elem = inner_shdw.find(".//a:alpha", NSMAP)
                if alpha_elem is not None:
                    alpha_elem.set("val", str(shadow_alpha))

        return lighting_element

    def generate_specular_highlight_3d(
        self,
        light_direction: str = "tl",
        bevel_width: int = 50800,
        bevel_height: int = 25400,
        *,
        material: str = "metal",
        highlight_blur: int = 25400,
        highlight_alpha: int = 60000,
        highlight_color: str = "FFFFFF",
    ) -> Element:
        highlight_element = self.builder.load_template("specular_highlight.xml")

        sp3d = highlight_element.find(".//a:sp3d", {"a": A_URI})
        if sp3d is not None:
            sp3d.set("extrusionH", str(bevel_width))
            sp3d.set("contourW", str(bevel_height))
            sp3d.set("prstMaterial", material)

            lightrig = sp3d.find(".//a:lightRig", {"a": A_URI})
            if lightrig is not None:
                lightrig.set("dir", light_direction)

        outer_shadow = highlight_element.find(".//a:outerShdw", {"a": A_URI})
        if outer_shadow is not None:
            outer_shadow.set("blurRad", str(highlight_blur))
            srgb_clr = outer_shadow.find(".//a:srgbClr", {"a": A_URI})
            if srgb_clr is not None:
                srgb_clr.set("val", highlight_color)
                alpha = srgb_clr.find(".//a:alpha", {"a": A_URI})
                if alpha is not None:
                    alpha.set("val", str(highlight_alpha))

        return highlight_element

    def generate_reflection_effect_3d(
        self,
        light_direction: str = "tl",
        bevel_width: int = 76200,
        bevel_height: int = 38100,
        *,
        material: str = "clear",
        reflection_blur: int = 6350,
        reflection_alpha: int = 50000,
    ) -> Element:
        reflection_element = self.builder.load_template("reflection_effect.xml")

        sp3d = reflection_element.find(".//a:sp3d", {"a": A_URI})
        if sp3d is not None:
            sp3d.set("extrusionH", str(bevel_width))
            sp3d.set("contourW", str(bevel_height))
            sp3d.set("prstMaterial", material)

            lightrig = sp3d.find(".//a:lightRig", {"a": A_URI})
            if lightrig is not None:
                lightrig.set("dir", light_direction)

        reflection = reflection_element.find(".//a:reflection", {"a": A_URI})
        if reflection is not None:
            reflection.set("blurRad", str(reflection_blur))
            reflection.set("stA", str(reflection_alpha))

        return reflection_element

    @staticmethod
    def map_shininess_to_material(specular_exponent: float) -> str:
        """Map specular exponent (shininess) to OpenXML material presets."""
        if specular_exponent <= 1.0:
            return "flat"
        if specular_exponent <= 4.0:
            return "matte"
        if specular_exponent <= 16.0:
            return "plastic"
        if specular_exponent <= 32.0:
            return "softEdge"
        if specular_exponent <= 64.0:
            return "metal"
        if specular_exponent <= 128.0:
            return "warmMatte"
        return "clear"

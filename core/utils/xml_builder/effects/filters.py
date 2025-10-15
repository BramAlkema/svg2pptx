"""Filter effect generator helpers built on top of lighting primitives."""

from __future__ import annotations

from .lighting import LightingEffectGenerator


class FilterEffectGenerator:
    """Produce lighting XML fragments for SVG filter translation."""

    def __init__(self, builder, lighting: LightingEffectGenerator) -> None:
        self.builder = builder
        self.lighting = lighting

    def generate_diffuse_lighting_for_filter(
        self,
        light_type: str | None,
        light_params: dict[str, float],
        surface_scale: float,
        diffuse_constant: float,
    ) -> str:
        bevel_width = min(int(surface_scale * 25400), 2_540_000)
        bevel_height = bevel_width // 2

        light_intensity = min(int(diffuse_constant * 100000), 100000)

        light_direction = "tl"
        if light_type == "distant" and light_params:
            azimuth = light_params.get("azimuth", 0)
            if 0 <= azimuth < 45 or 315 <= azimuth < 360:
                light_direction = "t"
            elif 45 <= azimuth < 135:
                light_direction = "tr"
            elif 135 <= azimuth < 225:
                light_direction = "r"
            elif 225 <= azimuth < 315:
                light_direction = "br"

        with_shadow = surface_scale > 1.0
        shadow_blur = min(int(surface_scale * 12700), 127000) if with_shadow else 25400
        shadow_alpha = min(light_intensity // 2, 25000) if with_shadow else 25000

        lighting_element = self.lighting.generate_diffuse_lighting_3d(
            light_direction=light_direction,
            bevel_width=bevel_width,
            bevel_height=bevel_height,
            with_shadow=with_shadow,
            shadow_blur=shadow_blur,
            shadow_alpha=shadow_alpha,
        )

        return self.builder.element_to_string(lighting_element)

    def generate_specular_lighting_for_filter(
        self,
        light_type: str | None,
        light_params: dict[str, float],
        surface_scale: float,
        specular_constant: float,
        specular_exponent: float,
        *,
        lighting_color: str = "FFFFFF",
    ) -> str:
        bevel_width = min(int(abs(surface_scale) * 25400), 2_540_000)
        bevel_height = bevel_width // 2
        material = self.lighting.map_shininess_to_material(specular_exponent)

        light_direction = "tl"
        if light_type == "distant" and light_params:
            azimuth = light_params.get("azimuth", 0)
            if 0 <= azimuth < 45 or 315 <= azimuth < 360:
                light_direction = "t"
            elif 45 <= azimuth < 135:
                light_direction = "tr"
            elif 135 <= azimuth < 225:
                light_direction = "r"
            elif 225 <= azimuth < 315:
                light_direction = "br"

        if specular_exponent >= 64.0:
            highlight_blur = int(surface_scale * 12700)
            highlight_alpha = 80000
        elif specular_exponent >= 16.0:
            highlight_blur = int(surface_scale * 25400)
            highlight_alpha = 60000
        else:
            highlight_blur = int(surface_scale * 50800)
            highlight_alpha = 40000

        highlight_alpha = min(80000, int(specular_constant * 30000))

        if specular_exponent > 100.0:
            lighting_element = self.lighting.generate_reflection_effect_3d(
                light_direction=light_direction,
                bevel_width=bevel_width,
                bevel_height=bevel_height,
                material=material,
                reflection_blur=highlight_blur // 4,
                reflection_alpha=highlight_alpha,
            )
        else:
            lighting_element = self.lighting.generate_specular_highlight_3d(
                light_direction=light_direction,
                bevel_width=bevel_width,
                bevel_height=bevel_height,
                material=material,
                highlight_blur=highlight_blur,
                highlight_alpha=highlight_alpha,
                highlight_color=lighting_color,
            )

        return self.builder.element_to_string(lighting_element)

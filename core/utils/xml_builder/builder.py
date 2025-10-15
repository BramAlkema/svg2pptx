"""Template-driven XML builder composition."""

from __future__ import annotations

from typing import Dict, List, TYPE_CHECKING

from lxml.etree import Element, QName, SubElement

from .base import XMLBuilderBase
from .animation import AnimationGenerator
from .constants import (
    A_URI,
    CONTENT_TYPES_URI,
    NSMAP,
    P_URI,
    R_URI,
    RELATIONSHIPS_NSMAP,
    RELATIONSHIPS_URI,
)
from .effects.filters import FilterEffectGenerator
from .effects.lighting import LightingEffectGenerator
from .fluent import FluentShapeBuilder  # noqa: F401  # re-export for legacy imports
from .shapes import (
    GroupShapeGenerator,
    ImageShapeGenerator,
    PathShapeGenerator,
    TextShapeGenerator,
)
if TYPE_CHECKING:  # pragma: no cover
    from ...io.template_loader import TemplateLoader


class EnhancedXMLBuilder(XMLBuilderBase):
    """High-level XML builder that composes specialized generators."""

    def __init__(self, template_loader: "TemplateLoader" | None = None) -> None:
        super().__init__(template_loader=template_loader)

        # Generators wired for delegation
        self.group_shapes = GroupShapeGenerator(self)
        self.path_shapes = PathShapeGenerator(self)
        self.text_shapes = TextShapeGenerator(self)
        self.image_shapes = ImageShapeGenerator(self)
        self.lighting_effects = LightingEffectGenerator(self)
        self.filter_effects = FilterEffectGenerator(self, self.lighting_effects)
        self.animations = AnimationGenerator(self)

        self._validate_templates()

    def _validate_templates(self) -> None:
        """Ensure required templates exist before generation starts."""
        critical_templates = (
            "presentation.xml",
            "slide_template.xml",
            "content_types.xml",
            "group_shape.xml",
            "group_picture.xml",
            "path_shape.xml",
            "path_emf_picture.xml",
            "path_emf_placeholder.xml",
            "text_shape.xml",
            "text_emf_picture.xml",
            "text_paragraph.xml",
            "text_run.xml",
        )

        for template_name in critical_templates:
            try:
                self.load_template(template_name)
            except Exception as exc:  # noqa: BLE001
                self.logger.error(
                    "Critical template validation failed: %s - %s",
                    template_name,
                    exc,
                )
                raise

    # ------------------------------------------------------------------ #
    # Presentation/scenario helpers
    # ------------------------------------------------------------------ #
    def create_presentation_element(
        self,
        width_emu: int,
        height_emu: int,
        *,
        slide_type: str = "screen4x3",
    ) -> Element:
        presentation = self.load_template("presentation.xml")

        slide_size = presentation.find(".//p:sldSz", namespaces={"p": P_URI})
        if slide_size is not None:
            slide_size.set("cx", str(width_emu))
            slide_size.set("cy", str(height_emu))
            slide_size.set("type", slide_type)

        notes_width = height_emu
        notes_height = int(height_emu * 4 / 3)
        notes_size = presentation.find(".//p:notesSz", namespaces={"p": P_URI})
        if notes_size is not None:
            notes_size.set("cx", str(notes_width))
            notes_size.set("cy", str(notes_height))

        slide_list = presentation.find(".//p:sldIdLst", namespaces={"p": P_URI})
        if slide_list is not None:
            slide_list.clear()

        return presentation

    def add_slide_to_presentation(
        self,
        presentation: Element,
        slide_id: int,
        rel_id: str,
    ) -> None:
        slide_list = presentation.find(".//p:sldIdLst", NSMAP)
        if slide_list is None:
            raise ValueError("Presentation element missing slide ID list")

        slide_ref = SubElement(slide_list, QName(P_URI, "sldId"))
        slide_ref.set("id", str(slide_id))
        slide_ref.set(QName(R_URI, "id"), rel_id)

    def create_slide_element(self, layout_id: int = 1) -> Element:  # noqa: ARG002 - maintain signature
        slide = self.load_template("slide_template.xml")

        sp_tree = slide.find(".//p:spTree", namespaces={"p": P_URI})
        if sp_tree is not None:
            for comment in sp_tree.xpath(
                '//comment()[contains(., "SHAPES WILL BE INSERTED HERE")]'
            ):
                parent = comment.getparent()
                if parent is not None:
                    parent.remove(comment)

        return slide

    def add_shape_to_slide(self, slide: Element, shape_element: Element) -> None:
        sp_tree = slide.find(".//p:spTree", NSMAP)
        if sp_tree is None:
            raise ValueError("Slide element missing shape tree")

        sp_tree.append(shape_element)

    def create_shape_element(
        self,
        shape_id: int,
        name: str,
        *,
        x: int = 0,
        y: int = 0,
        width: int = 914400,
        height: int = 914400,
    ) -> Element:
        shape = Element(QName(P_URI, "sp"))

        nv_sp_pr = SubElement(shape, QName(P_URI, "nvSpPr"))
        c_nv_pr = SubElement(nv_sp_pr, QName(P_URI, "cNvPr"))
        c_nv_pr.set("id", str(shape_id))
        c_nv_pr.set("name", name)
        SubElement(nv_sp_pr, QName(P_URI, "cNvSpPr"))
        SubElement(nv_sp_pr, QName(P_URI, "nvPr"))

        sp_pr = SubElement(shape, QName(P_URI, "spPr"))

        xfrm = SubElement(sp_pr, QName(A_URI, "xfrm"))
        off = SubElement(xfrm, QName(A_URI, "off"))
        off.set("x", str(x))
        off.set("y", str(y))
        ext = SubElement(xfrm, QName(A_URI, "ext"))
        ext.set("cx", str(width))
        ext.set("cy", str(height))

        return shape

    def add_geometry_to_shape(self, shape: Element, geometry_element: Element) -> None:
        sp_pr = shape.find(".//p:spPr", NSMAP)
        if sp_pr is None:
            raise ValueError("Shape element missing spPr")

        sp_pr.append(geometry_element)

    def create_content_types_element(
        self,
        additional_overrides: List[Dict[str, str]] | None = None,
    ) -> Element:
        types = self.load_template("content_types.xml")

        if additional_overrides:
            for override_data in additional_overrides:
                override = SubElement(types, QName(CONTENT_TYPES_URI, "Override"))
                override.set("PartName", override_data["PartName"])
                override.set("ContentType", override_data["ContentType"])

        return types

    def create_relationships_element(
        self,
        relationships: List[Dict[str, str]],
    ) -> Element:
        rels = Element(
            QName(RELATIONSHIPS_URI, "Relationships"),
            nsmap=RELATIONSHIPS_NSMAP,
        )

        for rel_data in relationships:
            relationship = SubElement(rels, QName(RELATIONSHIPS_URI, "Relationship"))
            relationship.set("Id", rel_data["Id"])
            relationship.set("Type", rel_data["Type"])
            relationship.set("Target", rel_data["Target"])

        return rels

    def create_animation_element(
        self,
        effect_type: str,
        target_shape_id: int,
        *,
        duration: float = 1.0,
        delay: float = 0.0,
    ) -> Element:
        return self.animations.create_animation_element(
            effect_type,
            target_shape_id,
            duration=duration,
            delay=delay,
        )

    # ------------------------------------------------------------------ #
    # Delegated generation helpers
    # ------------------------------------------------------------------ #
    def generate_group_shape(
        self,
        group_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        child_elements: List[Element],
        *,
        opacity: float | None = None,
        clip_xml: str | None = None,
    ) -> Element:
        return self.group_shapes.generate_group_shape(
            group_id,
            x_emu,
            y_emu,
            width_emu,
            height_emu,
            child_elements,
            opacity=opacity,
            clip_xml=clip_xml,
        )

    def generate_group_picture(
        self,
        group_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        embed_id: str,
        *,
        opacity: float | None = None,
        clip_xml: str | None = None,
    ) -> Element:
        return self.group_shapes.generate_group_picture(
            group_id,
            x_emu,
            y_emu,
            width_emu,
            height_emu,
            embed_id,
            opacity=opacity,
            clip_xml=clip_xml,
        )

    def generate_path_shape(
        self,
        path_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        path_data: str,
        *,
        fill_xml: str | None = None,
        stroke_xml: str | None = None,
        clip_xml: str | None = None,
    ) -> Element:
        return self.path_shapes.generate_path_shape(
            path_id,
            x_emu,
            y_emu,
            width_emu,
            height_emu,
            path_data,
            fill_xml=fill_xml,
            stroke_xml=stroke_xml,
            clip_xml=clip_xml,
        )

    def generate_path_emf_picture(
        self,
        path_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        embed_id: str,
        *,
        opacity: float | None = None,
        clip_xml: str | None = None,
    ) -> Element:
        return self.path_shapes.generate_path_emf_picture(
            path_id,
            x_emu,
            y_emu,
            width_emu,
            height_emu,
            embed_id,
            opacity=opacity,
            clip_xml=clip_xml,
        )

    def generate_path_emf_placeholder(
        self,
        path_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        embed_id: str,
        *,
        fill_xml: str | None = None,
        stroke_xml: str | None = None,
        clip_xml: str | None = None,
    ) -> Element:
        return self.path_shapes.generate_path_emf_placeholder(
            path_id,
            x_emu,
            y_emu,
            width_emu,
            height_emu,
            embed_id,
            fill_xml=fill_xml,
            stroke_xml=stroke_xml,
            clip_xml=clip_xml,
        )

    def generate_text_shape(
        self,
        text_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        paragraphs_xml: str,
        *,
        effects_xml: str | None = None,
    ) -> Element:
        return self.text_shapes.generate_text_shape(
            text_id,
            x_emu,
            y_emu,
            width_emu,
            height_emu,
            paragraphs_xml,
            effects_xml=effects_xml,
        )

    def generate_text_emf_picture(
        self,
        text_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        embed_id: str,
        *,
        effects_xml: str | None = None,
    ) -> Element:
        return self.text_shapes.generate_text_emf_picture(
            text_id,
            x_emu,
            y_emu,
            width_emu,
            height_emu,
            embed_id,
            effects_xml=effects_xml,
        )

    def generate_text_paragraph(self, runs_xml: str) -> Element:
        return self.text_shapes.generate_text_paragraph(runs_xml)

    def generate_text_run(
        self,
        text_content: str,
        font_family: str = "Arial",
        font_size: float = 12.0,
        *,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        rgb: str = "000000",
        formatting_xml: str | None = None,
    ) -> Element:
        return self.text_shapes.generate_text_run(
            text_content,
            font_family,
            font_size,
            bold=bold,
            italic=italic,
            underline=underline,
            rgb=rgb,
            formatting_xml=formatting_xml,
        )

    def generate_image_raster_picture(
        self,
        image_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        rel_id: str,
        *,
        effects_xml: str | None = None,
    ) -> Element:
        return self.image_shapes.generate_image_raster_picture(
            image_id,
            x_emu,
            y_emu,
            width_emu,
            height_emu,
            rel_id,
            effects_xml=effects_xml,
        )

    def generate_image_vector_picture(
        self,
        image_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        rel_id: str,
        *,
        effects_xml: str | None = None,
    ) -> Element:
        return self.image_shapes.generate_image_vector_picture(
            image_id,
            x_emu,
            y_emu,
            width_emu,
            height_emu,
            rel_id,
            effects_xml=effects_xml,
        )

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
        return self.lighting_effects.generate_diffuse_lighting_3d(
            light_direction=light_direction,
            bevel_width=bevel_width,
            bevel_height=bevel_height,
            with_shadow=with_shadow,
            shadow_blur=shadow_blur,
            shadow_alpha=shadow_alpha,
        )

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
        return self.lighting_effects.generate_specular_highlight_3d(
            light_direction=light_direction,
            bevel_width=bevel_width,
            bevel_height=bevel_height,
            material=material,
            highlight_blur=highlight_blur,
            highlight_alpha=highlight_alpha,
            highlight_color=highlight_color,
        )

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
        return self.lighting_effects.generate_reflection_effect_3d(
            light_direction=light_direction,
            bevel_width=bevel_width,
            bevel_height=bevel_height,
            material=material,
            reflection_blur=reflection_blur,
            reflection_alpha=reflection_alpha,
        )

    def generate_diffuse_lighting_for_filter(
        self,
        light_type: str | None,
        light_params: Dict[str, float],
        surface_scale: float,
        diffuse_constant: float,
    ) -> str:
        return self.filter_effects.generate_diffuse_lighting_for_filter(
            light_type,
            light_params,
            surface_scale,
            diffuse_constant,
        )

    def generate_specular_lighting_for_filter(
        self,
        light_type: str | None,
        light_params: Dict[str, float],
        surface_scale: float,
        specular_constant: float,
        specular_exponent: float,
        *,
        lighting_color: str = "FFFFFF",
    ) -> str:
        return self.filter_effects.generate_specular_lighting_for_filter(
            light_type,
            light_params,
            surface_scale,
            specular_constant,
            specular_exponent,
            lighting_color=lighting_color,
        )


# Singleton accessor with lazy instantiation to avoid circular imports
_ENHANCED_XML_BUILDER: EnhancedXMLBuilder | None = None


def _get_or_create_builder() -> EnhancedXMLBuilder:
    global _ENHANCED_XML_BUILDER
    if _ENHANCED_XML_BUILDER is None:
        _ENHANCED_XML_BUILDER = EnhancedXMLBuilder()
    return _ENHANCED_XML_BUILDER


class _BuilderProxy:
    def __getattr__(self, item):
        return getattr(_get_or_create_builder(), item)

    def __setattr__(self, key, value):
        setattr(_get_or_create_builder(), key, value)

    def __delattr__(self, item):
        delattr(_get_or_create_builder(), item)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return repr(_get_or_create_builder())


enhanced_xml_builder = _BuilderProxy()


def get_enhanced_xml_builder() -> EnhancedXMLBuilder:
    """Return the shared enhanced XML builder instance."""
    return _get_or_create_builder()


# Backwards-compatible alias used widely in the codebase
XMLBuilder = EnhancedXMLBuilder

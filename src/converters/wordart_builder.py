#!/usr/bin/env python3
"""
WordArt Transform Builder

Generates PowerPoint-compatible WordArt shapes with native transform support.
Integrates SVG transform decomposition with DrawingML generation.
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from lxml import etree as ET

from ..services.wordart_transform_service import (
    SVGTransformDecomposer, TransformComponents, create_transform_decomposer
)
from ..utils.ooxml_transform_utils import (
    OOXMLTransformUtils, OOXMLTransform, create_ooxml_transform_utils
)
from ..utils.xml_builder import XMLBuilder


@dataclass
class WordArtShapeConfig:
    """Configuration for WordArt shape generation."""

    # Text content
    text: str = ""
    font_family: str = "Arial"
    font_size: float = 24.0

    # Shape dimensions (in pixels)
    width: float = 200.0
    height: float = 50.0

    # Position (in pixels)
    x: float = 0.0
    y: float = 0.0

    # Transform string or matrix
    transform: Optional[Union[str, Any]] = None

    # WordArt preset (if applicable)
    wordart_preset: Optional[str] = None
    wordart_parameters: Optional[Dict[str, Any]] = None

    # Style properties
    fill_color: str = "#000000"
    stroke_color: Optional[str] = None
    stroke_width: float = 0.0


class WordArtTransformBuilder:
    """
    Builds PowerPoint WordArt shapes with native transform support.

    Integrates SVG transform decomposition with PowerPoint DrawingML generation
    to create native WordArt shapes that maintain high fidelity and performance.
    """

    def __init__(self):
        """Initialize WordArt builder with required services."""
        self.decomposer = create_transform_decomposer()
        self.ooxml_utils = create_ooxml_transform_utils()
        self.xml_builder = XMLBuilder()

    def build_wordart_shape(self, config: WordArtShapeConfig) -> ET.Element:
        """
        Build complete WordArt shape with transform.

        Args:
            config: WordArt shape configuration

        Returns:
            XML element for complete WordArt shape
        """
        # Decompose transform if provided
        transform_components = None
        if config.transform is not None:
            transform_components = self._decompose_transform(config.transform)

        # Create OOXML transform
        ooxml_transform = self._create_ooxml_transform(config, transform_components)

        # Generate shape XML
        shape = self._generate_shape_xml(config, ooxml_transform, transform_components)

        return shape

    def _decompose_transform(self, transform: Union[str, Any]) -> TransformComponents:
        """
        Decompose SVG transform into components.

        Args:
            transform: Transform string or matrix

        Returns:
            Decomposed transform components
        """
        if isinstance(transform, str):
            return self.decomposer.decompose_transform_string(transform)
        else:
            return self.decomposer.decompose_matrix(transform)

    def _create_ooxml_transform(
        self,
        config: WordArtShapeConfig,
        components: Optional[TransformComponents]
    ) -> OOXMLTransform:
        """
        Create OOXML transform from config and decomposed components.

        Args:
            config: Shape configuration
            components: Decomposed transform components (optional)

        Returns:
            OOXML transform object
        """
        if components:
            # Use decomposed transform components
            return self.ooxml_utils.create_ooxml_transform(
                translate_x=config.x + components.translate_x,
                translate_y=config.y + components.translate_y,
                width=config.width * components.scale_x,
                height=config.height * components.scale_y,
                rotation_deg=components.rotation_deg,
                flip_h=components.flip_h,
                flip_v=components.flip_v,
                input_unit="px"
            )
        else:
            # Use basic configuration
            return self.ooxml_utils.create_ooxml_transform(
                translate_x=config.x,
                translate_y=config.y,
                width=config.width,
                height=config.height,
                rotation_deg=0.0,
                flip_h=False,
                flip_v=False,
                input_unit="px"
            )

    def _generate_shape_xml(
        self,
        config: WordArtShapeConfig,
        ooxml_transform: OOXMLTransform,
        components: Optional[TransformComponents]
    ) -> ET.Element:
        """
        Generate complete shape XML element.

        Args:
            config: Shape configuration
            ooxml_transform: OOXML transform
            components: Transform components (optional)

        Returns:
            Complete shape XML element
        """
        # Define namespaces
        p_ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Create shape container
        shape = ET.Element(f"{p_ns}sp")

        # Add non-visual properties
        nvpr = ET.SubElement(shape, f"{p_ns}nvSpPr")
        cnvpr = ET.SubElement(nvpr, f"{p_ns}cNvPr")
        cnvpr.set("id", str(self.xml_builder.get_next_id()))
        cnvpr.set("name", f"WordArt {cnvpr.get('id')}")

        cnvsppr = ET.SubElement(nvpr, f"{p_ns}cNvSpPr")
        # Mark as text shape for WordArt
        cnvsppr.set("txBox", "1")

        nvpr_app = ET.SubElement(nvpr, f"{p_ns}nvPr")

        # Add shape properties
        sppr = ET.SubElement(shape, f"{p_ns}spPr")

        # Add transform
        xfrm_element = self.ooxml_utils.generate_xfrm_xml(ooxml_transform)
        sppr.append(xfrm_element)

        # Add geometry (rectangle for text)
        prstgeom = ET.SubElement(sppr, f"{a_ns}prstGeom")
        prstgeom.set("prst", "rect")
        avlst = ET.SubElement(prstgeom, f"{a_ns}avLst")

        # Add fill properties
        if config.fill_color:
            self._add_fill_properties(sppr, config.fill_color)

        # Add stroke properties
        if config.stroke_color and config.stroke_width > 0:
            self._add_stroke_properties(sppr, config.stroke_color, config.stroke_width)

        # Add text body
        txbody = self._generate_text_body(config, components, p_ns, a_ns)
        shape.append(txbody)

        return shape

    def _add_fill_properties(self, sppr: ET.Element, color: str) -> None:
        """
        Add fill properties to shape.

        Args:
            sppr: Shape properties element
            color: Fill color (hex format)
        """
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        solidfill = ET.SubElement(sppr, f"{a_ns}solidFill")
        srgbclr = ET.SubElement(solidfill, f"{a_ns}srgbClr")
        # Remove # prefix if present
        color_val = color.lstrip('#')
        srgbclr.set("val", color_val.upper())

    def _add_stroke_properties(self, sppr: ET.Element, color: str, width: float) -> None:
        """
        Add stroke properties to shape.

        Args:
            sppr: Shape properties element
            color: Stroke color (hex format)
            width: Stroke width in pixels
        """
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        ln = ET.SubElement(sppr, f"{a_ns}ln")
        # Convert pixels to EMU for stroke width
        width_emu = self.ooxml_utils.pixels_to_emu(width)
        ln.set("w", str(width_emu))

        solidfill = ET.SubElement(ln, f"{a_ns}solidFill")
        srgbclr = ET.SubElement(solidfill, f"{a_ns}srgbClr")
        color_val = color.lstrip('#')
        srgbclr.set("val", color_val.upper())

    def _generate_text_body(
        self,
        config: WordArtShapeConfig,
        components: Optional[TransformComponents],
        p_ns: str,
        a_ns: str
    ) -> ET.Element:
        """
        Generate text body with WordArt formatting.

        Args:
            config: Shape configuration
            components: Transform components (optional)

        Returns:
            Text body XML element
        """
        txbody = ET.Element(f"{p_ns}txBody")

        # Body properties
        bodypr = ET.SubElement(txbody, f"{a_ns}bodyPr")
        bodypr.set("wrap", "none")
        bodypr.set("rtlCol", "0")

        # List style (empty for WordArt)
        lststyle = ET.SubElement(txbody, f"{a_ns}lstStyle")

        # Paragraph
        p = ET.SubElement(txbody, f"{a_ns}p")

        # Run
        r = ET.SubElement(p, f"{a_ns}r")

        # Run properties
        rpr = ET.SubElement(r, f"{a_ns}rPr")
        rpr.set("lang", "en-US")

        # Font size in points * 100 (PowerPoint format)
        font_size_ooxml = int(config.font_size * 100)
        rpr.set("sz", str(font_size_ooxml))

        # Font family
        latin = ET.SubElement(rpr, f"{a_ns}latin")
        latin.set("typeface", config.font_family)

        # Add WordArt effects if components indicate complex transform
        if components and (components.has_skew or components.scale_ratio > 1.5):
            self._add_wordart_effects(rpr, config, components, a_ns)

        # Text content
        t = ET.SubElement(r, f"{a_ns}t")
        t.text = config.text

        # End paragraph properties
        endparapr = ET.SubElement(p, f"{a_ns}endParaRPr")
        endparapr.set("lang", "en-US")

        return txbody

    def _add_wordart_effects(
        self,
        rpr: ET.Element,
        config: WordArtShapeConfig,
        components: TransformComponents,
        a_ns: str
    ) -> None:
        """
        Add WordArt visual effects based on transform complexity.

        Args:
            rpr: Run properties element
            config: Shape configuration
            components: Transform components
        """
        # Add text outline for complex transforms
        ln = ET.SubElement(rpr, f"{a_ns}ln")
        ln.set("w", "12700")  # 1 point outline

        solidfill = ET.SubElement(ln, f"{a_ns}solidFill")
        srgbclr = ET.SubElement(solidfill, f"{a_ns}srgbClr")
        srgbclr.set("val", "000000")  # Black outline

        # Add subtle shadow for skewed text
        if components.has_skew:
            effectlst = ET.SubElement(rpr, f"{a_ns}effectLst")
            outershdw = ET.SubElement(effectlst, f"{a_ns}outerShdw")
            outershdw.set("blurRad", "38100")  # 3 points blur
            outershdw.set("dist", "38100")     # 3 points distance
            outershdw.set("dir", "2700000")   # 45 degrees

            srgbclr_shadow = ET.SubElement(outershdw, f"{a_ns}srgbClr")
            srgbclr_shadow.set("val", "808080")  # Gray shadow
            alpha = ET.SubElement(srgbclr_shadow, f"{a_ns}alpha")
            alpha.set("val", "50000")  # 50% opacity

    def validate_wordart_compatibility(self, config: WordArtShapeConfig) -> Dict[str, Any]:
        """
        Validate configuration for WordArt compatibility.

        Args:
            config: Shape configuration

        Returns:
            Validation result
        """
        result = {
            'compatible': True,
            'warnings': [],
            'errors': []
        }

        # Check text content
        if not config.text:
            result['errors'].append("Text content is required")
            result['compatible'] = False

        if len(config.text) > 1000:  # Practical limit
            result['warnings'].append("Text is very long, may impact performance")

        # Check dimensions
        if config.width <= 0 or config.height <= 0:
            result['errors'].append("Width and height must be positive")
            result['compatible'] = False

        # Check font size
        if config.font_size < 1.0:
            result['warnings'].append("Font size is very small")
        elif config.font_size > 1000.0:
            result['warnings'].append("Font size is very large")

        # Validate transform if present
        if config.transform is not None:
            try:
                components = self._decompose_transform(config.transform)
                ooxml_transform = self._create_ooxml_transform(config, components)
                transform_validation = self.ooxml_utils.validate_transform_limits(ooxml_transform)

                if not transform_validation['valid']:
                    result['errors'].extend(transform_validation['errors'])
                    result['compatible'] = False

                result['warnings'].extend(transform_validation['warnings'])

            except Exception as e:
                result['errors'].append(f"Transform analysis failed: {e}")
                result['compatible'] = False

        return result


def create_wordart_builder() -> WordArtTransformBuilder:
    """
    Factory function to create WordArt transform builder.

    Returns:
        WordArtTransformBuilder instance
    """
    return WordArtTransformBuilder()
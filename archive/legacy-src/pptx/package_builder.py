"""
PPTX Package Builder with Font Embedding Support

This module extends the minimal PPTX generation to support embedded fonts
in OOXML packages with proper relationship management and content type registration.
"""

import zipfile
import io
import uuid
from pathlib import Path
from typing import Union, List, Dict, Optional, Tuple
from lxml import etree as ET

from ..data.embedded_font import EmbeddedFont


class PPTXPackageBuilder:
    """
    Enhanced PPTX package builder with font embedding capabilities.

    Supports embedding subset fonts directly in PPTX packages with proper
    OOXML relationship management and content type registration.
    """

    def __init__(self):
        """Initialize PPTX package builder."""
        self.emu_per_inch = 914400  # EMU (English Metric Units) per inch
        self._embedded_fonts: List[EmbeddedFont] = []
        self._font_relationships: Dict[str, str] = {}  # font_name -> relationship_id
        self._relationship_counter = 3  # Start after standard relationships (rId1, rId2)

    def add_embedded_font(self, embedded_font: EmbeddedFont) -> str:
        """
        Add an embedded font to the package.

        Args:
            embedded_font: EmbeddedFont instance with font data and metadata

        Returns:
            Relationship ID for the embedded font
        """
        # Generate unique relationship ID
        relationship_id = f"rId{self._relationship_counter}"
        self._relationship_counter += 1

        # Create a new EmbeddedFont instance with the relationship ID
        # (needed because EmbeddedFont is frozen)
        updated_font = EmbeddedFont(
            font_name=embedded_font.font_name,
            font_data=embedded_font.font_data,
            subset_characters=embedded_font.subset_characters,
            original_size=embedded_font.original_size,
            embedded_size=embedded_font.embedded_size,
            embedding_allowed=embedded_font.embedding_allowed,
            embedding_permission=embedded_font.embedding_permission,
            font_family=embedded_font.font_family,
            font_weight=embedded_font.font_weight,
            font_style=embedded_font.font_style,
            units_per_em=embedded_font.units_per_em,
            file_format=embedded_font.file_format,
            relationship_id=relationship_id,
            content_type=embedded_font.content_type
        )

        self._embedded_fonts.append(updated_font)
        self._font_relationships[embedded_font.font_name] = relationship_id

        return relationship_id

    def get_embedded_font_by_name(self, font_name: str) -> Optional[EmbeddedFont]:
        """
        Get embedded font by name.

        Args:
            font_name: Name of the font to retrieve

        Returns:
            EmbeddedFont instance if found, None otherwise
        """
        for font in self._embedded_fonts:
            if font.font_name == font_name:
                return font
        return None

    def get_font_relationship_id(self, font_name: str) -> Optional[str]:
        """
        Get relationship ID for embedded font by name.

        Args:
            font_name: Name of the font

        Returns:
            Relationship ID if font is embedded, None otherwise
        """
        return self._font_relationships.get(font_name)

    def create_pptx_from_svg(self, svg_content: str, output_path: Union[str, Path],
                           drawingml_content: str = None, embed_fonts: bool = None) -> None:
        """
        Create complete PPTX file from SVG content with conditional font embedding.

        Args:
            svg_content: SVG content as string
            output_path: Path where PPTX file should be saved
            drawingml_content: Optional pre-converted DrawingML content
            embed_fonts: Whether to embed fonts. If None, auto-detect based on SVG text elements
        """
        # Parse SVG to get viewBox dimensions
        try:
            if isinstance(svg_content, str):
                if svg_content.strip().startswith('<?xml'):
                    svg_bytes = svg_content.encode('utf-8')
                    svg_root = ET.fromstring(svg_bytes)
                else:
                    svg_root = ET.fromstring(svg_content)
            else:
                svg_root = ET.fromstring(svg_content)
        except ET.XMLSyntaxError:
            # For malformed XML, create a minimal valid SVG
            svg_root = ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"></svg>')

        viewbox = self._parse_viewbox(svg_root)
        width_emu, height_emu = self._calculate_slide_dimensions(viewbox)

        # Auto-detect font embedding requirements if not specified
        if embed_fonts is None:
            from ..services.svg_font_analyzer import SVGFontAnalyzer
            analyzer = SVGFontAnalyzer()
            font_analysis = analyzer.analyze_svg_fonts(svg_content)
            embed_fonts = font_analysis['should_embed_fonts']

        # Use provided DrawingML content or convert SVG
        if drawingml_content is None:
            drawingml_content = self._convert_svg_to_drawingml(svg_content, viewbox)

        # Create slide XML with DrawingML content
        slide_xml = self._create_slide_xml(drawingml_content)

        # Generate dynamic presentation.xml with calculated dimensions
        presentation_xml = self._create_presentation_xml(width_emu, height_emu)

        # Create content types and relationships based on font embedding
        if embed_fonts and self._embedded_fonts:
            # Create enhanced content types with font support
            content_types_xml = self._create_content_types_xml()
            # Create presentation relationships with font relationships
            presentation_rels_xml = self._create_presentation_relationships_xml()
        else:
            # Use simple content types without font support
            content_types_xml = self._create_simple_content_types_xml()
            presentation_rels_xml = self._create_simple_presentation_relationships_xml()

        # Create PPTX ZIP file
        self._create_pptx_zip_with_fonts(
            slide_xml, presentation_xml, content_types_xml,
            presentation_rels_xml, output_path
        )

    def _parse_viewbox(self, svg_root: ET.Element) -> Tuple[float, float, float, float]:
        """
        Parse SVG viewBox to get dimensions using canonical ViewportEngine.

        Args:
            svg_root: Parsed SVG root element

        Returns:
            Tuple of (x, y, width, height) from viewBox
        """
        viewbox = svg_root.get('viewBox')
        if viewbox:
            try:
                # Use ConversionServices for dependency injection
                import numpy as np

                try:
                    from ..services.conversion_services import ConversionServices
                    services = ConversionServices.create_default()
                    resolver = services.viewport_resolver
                except ImportError:
                    # Fallback to direct import
                    from ..viewbox import ViewportEngine
                    resolver = ViewportEngine()

                parsed = resolver.parse_viewbox_strings(np.array([viewbox]))
                if len(parsed) > 0 and len(parsed[0]) >= 4:
                    return tuple(parsed[0][:4])
            except ImportError:
                # Fallback to legacy parsing if ViewportEngine not available
                pass
            except Exception:
                # Fallback on any parsing error
                pass

            # Legacy fallback - enhanced to handle commas
            try:
                cleaned = viewbox.strip().replace(',', ' ')
                values = [float(v) for v in cleaned.split()]
                if len(values) >= 4:
                    return tuple(values[:4])
            except (ValueError, IndexError):
                pass

        # Fallback: try width/height attributes
        width = self._parse_length(svg_root.get('width', '100'))
        height = self._parse_length(svg_root.get('height', '100'))
        return (0, 0, width, height)

    def _parse_length(self, length_str: str) -> float:
        """Parse SVG length values, removing units."""
        if not length_str:
            return 100.0

        # Extract numeric value, ignore units
        import re
        match = re.match(r'([0-9.]+)', str(length_str))
        if match:
            return float(match.group(1))
        return 100.0

    def _calculate_slide_dimensions(self, viewbox: Tuple[float, float, float, float]) -> Tuple[int, int]:
        """
        Calculate PowerPoint slide dimensions from SVG viewBox.

        Args:
            viewbox: SVG viewBox (x, y, width, height)

        Returns:
            Tuple of (width_emu, height_emu) for PowerPoint slide
        """
        _, _, vb_width, vb_height = viewbox

        # Calculate aspect ratio with safety checks
        if vb_width <= 0 or vb_height <= 0:
            # Default to 16:9 aspect ratio for invalid dimensions
            aspect_ratio = 16/9
        else:
            aspect_ratio = vb_width / vb_height

        # Set reasonable slide size: aim for ~10 inches width, scale height proportionally
        target_width_inches = 10.0
        target_height_inches = target_width_inches / aspect_ratio

        # Convert to EMU (English Metric Units)
        width_emu = int(target_width_inches * self.emu_per_inch)
        height_emu = int(target_height_inches * self.emu_per_inch)

        return width_emu, height_emu

    def _create_presentation_xml(self, width_emu: int, height_emu: int) -> str:
        """
        Create presentation.xml with dynamic slide dimensions.

        Args:
            width_emu: Slide width in EMU
            height_emu: Slide height in EMU

        Returns:
            Complete presentation.xml as string
        """
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:sldMasterIdLst>
        <p:sldMasterId id="2147483648" r:id="rId1"/>
    </p:sldMasterIdLst>
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId2"/>
    </p:sldIdLst>
    <p:sldSz cx="{width_emu}" cy="{height_emu}"/>
    <p:notesSz cx="{height_emu}" cy="{width_emu}"/>
    <p:defaultTextStyle>
        <a:defPPr>
            <a:defRPr lang="en-US"/>
        </a:defPPr>
    </p:defaultTextStyle>
</p:presentation>'''

    def _create_content_types_xml(self) -> str:
        """
        Create [Content_Types].xml with embedded font content types.

        Returns:
            Complete content types XML with font declarations
        """
        base_content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Default Extension="ttf" ContentType="application/vnd.ms-fontobject"/>
    <Default Extension="otf" ContentType="application/vnd.ms-fontobject"/>
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-presentationml.presentation.main+xml"/>
    <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-presentationml.slide+xml"/>
    <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-presentationml.slideMaster+xml"/>
    <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-presentationml.slideLayout+xml"/>'''

        # Add content type overrides for embedded fonts
        font_overrides = []
        for font in self._embedded_fonts:
            font_path = f"/ppt/fonts/{self._sanitize_font_filename(font.font_name)}"
            font_overrides.append(
                f'    <Override PartName="{font_path}" ContentType="{font.content_type}"/>'
            )

        if font_overrides:
            base_content_types += '\n' + '\n'.join(font_overrides)

        base_content_types += '\n</Types>'
        return base_content_types

    def _create_presentation_relationships_xml(self) -> str:
        """
        Create presentation relationships with embedded font relationships.

        Returns:
            Complete presentation relationships XML
        """
        base_relationships = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>'''

        # Add font relationships
        font_relationships = []
        for font in self._embedded_fonts:
            font_filename = self._sanitize_font_filename(font.font_name)
            font_relationships.append(
                f'    <Relationship Id="{font.relationship_id}" '
                f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/font" '
                f'Target="fonts/{font_filename}"/>'
            )

        if font_relationships:
            base_relationships += '\n' + '\n'.join(font_relationships)

        base_relationships += '\n</Relationships>'
        return base_relationships

    def _create_simple_content_types_xml(self) -> str:
        """
        Create basic [Content_Types].xml without font support.

        Returns:
            Basic content types XML
        """
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-presentationml.presentation.main+xml"/>
    <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-presentationml.slide+xml"/>
    <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-presentationml.slideMaster+xml"/>
    <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-presentationml.slideLayout+xml"/>
</Types>'''

    def _create_simple_presentation_relationships_xml(self) -> str:
        """
        Create basic presentation relationships without fonts.

        Returns:
            Basic presentation relationships XML
        """
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>'''

    def _create_slide_xml(self, drawingml_content: str) -> str:
        """
        Create a complete slide XML with embedded DrawingML content.

        Args:
            drawingml_content: DrawingML XML content to embed in slide

        Returns:
            Complete slide XML as string
        """
        slide_template = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="0" cy="0"/>
                </a:xfrm>
            </p:grpSpPr>

            {drawingml_content}

        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sld>'''
        return slide_template.format(drawingml_content=drawingml_content)

    def _convert_svg_to_drawingml(self, svg_content: str, viewbox: Tuple[float, float, float, float]) -> str:
        """
        Convert SVG content to DrawingML using the conversion pipeline.

        Args:
            svg_content: SVG content as string
            viewbox: SVG viewBox for coordinate mapping

        Returns:
            DrawingML XML content
        """
        try:
            from lxml import etree as ET
            from ..services.conversion_services import ConversionServices
            from ..converters.base import ConversionContext, ConverterRegistry

            # Parse SVG content
            try:
                svg_root = ET.fromstring(svg_content)
            except ET.ParseError as e:
                logger.warning(f"Failed to parse SVG content: {e}")
                return self._create_fallback_drawingml(viewbox)

            # Create conversion services and context
            services = ConversionServices.create_default()
            context = ConversionContext(svg_root=svg_root, services=services)

            # Initialize converter registry
            registry = ConverterRegistry()
            registry.register_default_converters(services)
            context.converter_registry = registry

            # Convert SVG elements to DrawingML shapes
            shapes_xml_parts = []
            shape_id = 1000

            for element in svg_root:
                try:
                    converter = registry.get_converter(element)
                    if converter:
                        # Set unique shape ID
                        shape_xml = converter.convert(element, context)
                        if shape_xml:
                            shapes_xml_parts.append(shape_xml)
                            shape_id += 1
                except Exception as conv_e:
                    logger.warning(f"Failed to convert element {element.tag}: {conv_e}")

            # Combine all shapes
            if shapes_xml_parts:
                return ''.join(shapes_xml_parts)
            else:
                return self._create_fallback_drawingml(viewbox)

        except Exception as e:
            logger.error(f"SVG to DrawingML conversion failed: {e}")
            return self._create_fallback_drawingml(viewbox)

    def _create_fallback_drawingml(self, viewbox: Tuple[float, float, float, float]) -> str:
        """Create fallback DrawingML when conversion fails."""
        _, _, vb_width, vb_height = viewbox

        # Calculate slide-relative dimensions (simplified)
        slide_width_emu = 9144000  # ~10 inches
        slide_height_emu = int(slide_width_emu * vb_height / vb_width) if vb_width > 0 else 5143000

        return f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="2" name="SVG Content (viewBox: {vb_width}x{vb_height})"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="914400" y="914400"/>
                    <a:ext cx="{slide_width_emu-1828800}" cy="{slide_height_emu-1828800}"/>
                </a:xfrm>
                <a:prstGeom prst="rect">
                    <a:avLst/>
                </a:prstGeom>
                <a:solidFill>
                    <a:srgbClr val="4472C4"/>
                </a:solidFill>
                <a:stroke>
                    <a:solidFill>
                        <a:srgbClr val="2F5597"/>
                    </a:solidFill>
                    <a:width val="19050"/>
                </a:stroke>
            </p:spPr>
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:r>
                        <a:rPr lang="en-US" sz="1200"/>
                        <a:t>SVG Content with {len(self._embedded_fonts)} embedded fonts</a:t>
                    </a:r>
                </a:p>
            </p:txBody>
        </p:sp>'''

    def _sanitize_font_filename(self, font_name: str) -> str:
        """
        Sanitize font name for use as filename in PPTX package.

        Args:
            font_name: Original font name

        Returns:
            Sanitized filename safe for ZIP entry
        """
        # Replace spaces and special characters with underscores
        import re
        sanitized = re.sub(r'[^\w\-.]', '_', font_name)

        # Ensure it has a proper extension
        if not sanitized.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
            sanitized += '.ttf'

        return sanitized

    def _create_pptx_zip_with_fonts(self, slide_xml: str, presentation_xml: str,
                                  content_types_xml: str, presentation_rels_xml: str,
                                  output_path: Union[str, Path]) -> None:
        """
        Create PPTX ZIP file with all required components including embedded fonts.

        Args:
            slide_xml: Complete slide XML content
            presentation_xml: Complete presentation XML content
            content_types_xml: Content types XML with font declarations
            presentation_rels_xml: Presentation relationships XML with font relationships
            output_path: Path where PPTX file should be saved
        """
        output_path = Path(output_path)

        # Create ZIP file
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as pptx_zip:

            # Add content types with font support
            pptx_zip.writestr('[Content_Types].xml', content_types_xml)

            # Add main relationships
            pptx_zip.writestr('_rels/.rels', self._get_main_rels_xml())

            # Add presentation document with dynamic dimensions
            pptx_zip.writestr('ppt/presentation.xml', presentation_xml)
            pptx_zip.writestr('ppt/_rels/presentation.xml.rels', presentation_rels_xml)

            # Add slide master
            pptx_zip.writestr('ppt/slideMasters/slideMaster1.xml', self._get_slide_master_xml())
            pptx_zip.writestr('ppt/slideMasters/_rels/slideMaster1.xml.rels', self._get_slide_master_rels_xml())

            # Add slide layout
            pptx_zip.writestr('ppt/slideLayouts/slideLayout1.xml', self._get_slide_layout_xml())
            pptx_zip.writestr('ppt/slideLayouts/_rels/slideLayout1.xml.rels', self._get_slide_layout_rels_xml())

            # Add slide with SVG content
            pptx_zip.writestr('ppt/slides/slide1.xml', slide_xml)
            pptx_zip.writestr('ppt/slides/_rels/slide1.xml.rels', self._get_slide_rels_xml())

            # Add embedded fonts
            self._add_embedded_fonts_to_zip(pptx_zip)

    def _add_embedded_fonts_to_zip(self, pptx_zip: zipfile.ZipFile) -> None:
        """
        Add embedded font files to the PPTX ZIP package.

        Args:
            pptx_zip: Open ZipFile object to add fonts to
        """
        for font in self._embedded_fonts:
            font_filename = self._sanitize_font_filename(font.font_name)
            font_path = f"ppt/fonts/{font_filename}"

            # Add font data to ZIP
            pptx_zip.writestr(font_path, font.font_data)

    def get_package_statistics(self) -> Dict[str, any]:
        """
        Get statistics about the package including embedded fonts.

        Returns:
            Dictionary with package statistics
        """
        total_font_size = sum(len(font.font_data) for font in self._embedded_fonts)

        return {
            'embedded_fonts_count': len(self._embedded_fonts),
            'total_font_size_bytes': total_font_size,
            'total_font_size_mb': total_font_size / (1024 * 1024),
            'font_names': [font.font_name for font in self._embedded_fonts],
            'font_relationships': dict(self._font_relationships),
            'average_compression_ratio': (
                sum(font.compression_ratio for font in self._embedded_fonts) / len(self._embedded_fonts)
                if self._embedded_fonts else 0.0
            )
        }

    def clear_embedded_fonts(self) -> None:
        """Clear all embedded fonts from the package."""
        self._embedded_fonts.clear()
        self._font_relationships.clear()
        self._relationship_counter = 3

    # Standard XML templates (moved from ooxml_templates.py for embedding support)

    def _get_main_rels_xml(self) -> str:
        """Get main package relationships XML."""
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>'''

    def _get_slide_master_xml(self) -> str:
        """Get slide master XML."""
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
             xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="0" cy="0"/>
                </a:xfrm>
            </p:grpSpPr>
        </p:spTree>
    </p:cSld>
    <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
    <p:sldLayoutIdLst>
        <p:sldLayoutId id="2147483649" r:id="rId1"/>
    </p:sldLayoutIdLst>
    <p:txStyles>
        <p:titleStyle>
            <a:lvl1pPr>
                <a:defRPr lang="en-US"/>
            </a:lvl1pPr>
        </p:titleStyle>
        <p:bodyStyle>
            <a:lvl1pPr>
                <a:defRPr lang="en-US"/>
            </a:lvl1pPr>
        </p:bodyStyle>
        <p:otherStyle>
            <a:lvl1pPr>
                <a:defRPr lang="en-US"/>
            </a:lvl1pPr>
        </p:otherStyle>
    </p:txStyles>
</p:sldMaster>'''

    def _get_slide_master_rels_xml(self) -> str:
        """Get slide master relationships XML."""
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>'''

    def _get_slide_layout_xml(self) -> str:
        """Get slide layout XML."""
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
             xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             type="blank" preserve="1">
    <p:cSld name="Blank">
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="0" cy="0"/>
                </a:xfrm>
            </p:grpSpPr>
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sldLayout>'''

    def _get_slide_layout_rels_xml(self) -> str:
        """Get slide layout relationships XML."""
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>'''

    def _get_slide_rels_xml(self) -> str:
        """Get slide relationships XML."""
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>'''


def create_pptx_with_embedded_fonts(svg_content: str, output_path: Union[str, Path],
                                   embedded_fonts: List[EmbeddedFont] = None) -> PPTXPackageBuilder:
    """
    Simple API function to create PPTX with embedded fonts.

    Args:
        svg_content: SVG content as string
        output_path: Path where PPTX file should be saved
        embedded_fonts: List of EmbeddedFont instances to embed

    Returns:
        PPTXPackageBuilder instance for further manipulation
    """
    builder = PPTXPackageBuilder()

    # Add embedded fonts if provided
    if embedded_fonts:
        for font in embedded_fonts:
            builder.add_embedded_font(font)

    # Create PPTX file
    builder.create_pptx_from_svg(svg_content, output_path)

    return builder
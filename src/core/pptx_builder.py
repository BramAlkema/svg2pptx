#!/usr/bin/env python3
"""
PPTXBuilder - Direct PPTX File Creation

Creates PPTX files by manually building the ZIP structure
and injecting DrawingML shapes directly into slide XML.
"""

import os
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..units import UnitConverter
else:
    try:
        from ..units import UnitConverter
    except ImportError:
        UnitConverter = None


class PPTXBuilder:
    """Build PPTX files from scratch with direct XML manipulation."""

    def __init__(self, unit_converter: Optional['UnitConverter'] = None):
        # Initialize with unit converter for proper unit handling
        self.unit_converter = unit_converter

        # Default slide dimensions (10" x 7.5" converted to EMUs)
        if self.unit_converter:
            self.slide_width = self.unit_converter.to_emu('10in')
            self.slide_height = self.unit_converter.to_emu('7.5in')
        else:
            # Fallback to hardcoded EMUs if no unit converter
            self.slide_width = 9144000   # 10 inches in EMUs
            self.slide_height = 6858000  # 7.5 inches in EMUs

        self.images: List[Tuple[str, str, str]] = []  # (embed_id, file_path, extension)
        self.next_rel_id = 10  # Start relationship IDs from rId10
        self._next_shape_id = 1000  # simple local id counter for shapes

    def create_minimal_pptx(self, drawingml_shapes: str, output_path: str):
        """Create a minimal PPTX file with DrawingML shapes."""

        # Create temporary directory for PPTX structure
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Copy images to media directory first
            if self.images:
                self._copy_images_to_media(temp_path)

            # Create PPTX directory structure (now with correct image paths)
            self._create_pptx_structure(temp_path)

            # Create slide with our DrawingML shapes
            slide_xml = self._create_slide_xml(drawingml_shapes)
            (temp_path / 'ppt' / 'slides' / 'slide1.xml').write_text(slide_xml, encoding='utf-8')

            # Create ZIP archive
            self._zip_pptx_structure(temp_path, output_path)

    def _create_pptx_structure(self, base_path: Path):
        """Create the basic PPTX directory structure and required files."""

        # Create directories
        (base_path / 'ppt' / 'slides').mkdir(parents=True)
        (base_path / 'ppt' / 'slideLayouts').mkdir(parents=True)
        (base_path / 'ppt' / 'slideMasters').mkdir(parents=True)
        (base_path / 'ppt' / 'theme').mkdir(parents=True)
        (base_path / '_rels').mkdir(parents=True)
        (base_path / 'ppt' / '_rels').mkdir(parents=True)
        (base_path / 'ppt' / 'slides' / '_rels').mkdir(parents=True)
        # Media directory is created by _copy_images_to_media if needed

        # Create docProps for better Office compatibility (optional but nice)
        (base_path / 'docProps').mkdir(parents=True, exist_ok=True)
        core_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>SVG2PPTX</dc:title>
  <dc:creator>SVG2PPTX</dc:creator>
  <cp:lastModifiedBy>SVG2PPTX</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">2025-01-01T00:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2025-01-01T00:00:00Z</dcterms:modified>
</cp:coreProperties>'''
        (base_path / 'docProps' / 'core.xml').write_text(core_xml, encoding='utf-8')

        app_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>SVG2PPTX</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <HeadingPairs><vt:vector size="2" baseType="variant">
    <vt:variant><vt:lpstr>Slides</vt:lpstr></vt:variant>
    <vt:variant><vt:i4>1</vt:i4></vt:variant>
  </vt:vector></HeadingPairs>
  <TitlesOfParts><vt:vector size="1" baseType="lpstr"><vt:lpstr>Slide 1</vt:lpstr></vt:vector></TitlesOfParts>
</Properties>'''
        (base_path / 'docProps' / 'app.xml').write_text(app_xml, encoding='utf-8')

        # Create [Content_Types].xml with image types and docProps
        image_content_types = ""
        if self.images:
            image_content_types = '''
    <Default Extension="png" ContentType="image/png"/>
    <Default Extension="jpg" ContentType="image/jpeg"/>
    <Default Extension="jpeg" ContentType="image/jpeg"/>
    <Default Extension="gif" ContentType="image/gif"/>
    <Default Extension="bmp" ContentType="image/bmp"/>
    <Default Extension="webp" ContentType="image/webp"/>'''

        content_types = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>{image_content_types}
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
    <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
    <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
    <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
    <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
    <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
    <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''
        (base_path / '[Content_Types].xml').write_text(content_types, encoding='utf-8')

        # Create main .rels file
        main_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>'''
        (base_path / '_rels' / '.rels').write_text(main_rels, encoding='utf-8')

        # Create presentation.xml
        presentation_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:sldMasterIdLst>
        <p:sldMasterId id="2147483648" r:id="rId1"/>
    </p:sldMasterIdLst>
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId2"/>
    </p:sldIdLst>
    <p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>
    <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''
        (base_path / 'ppt' / 'presentation.xml').write_text(presentation_xml, encoding='utf-8')

        # Create presentation _rels
        pres_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>'''
        (base_path / 'ppt' / '_rels' / 'presentation.xml.rels').write_text(pres_rels, encoding='utf-8')

        # Create slide1 _rels (including image relationships)
        slide_rels = self._create_slide_relationships()
        (base_path / 'ppt' / 'slides' / '_rels' / 'slide1.xml.rels').write_text(slide_rels, encoding='utf-8')

        # Create minimal theme
        theme_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">
    <a:themeElements>
        <a:clrScheme name="Office">
            <a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
            <a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
            <a:dk2><a:srgbClr val="1F497D"/></a:dk2>
            <a:lt2><a:srgbClr val="EEECE1"/></a:lt2>
            <a:accent1><a:srgbClr val="4F81BD"/></a:accent1>
            <a:accent2><a:srgbClr val="F79646"/></a:accent2>
            <a:accent3><a:srgbClr val="9BBB59"/></a:accent3>
            <a:accent4><a:srgbClr val="8064A2"/></a:accent4>
            <a:accent5><a:srgbClr val="4BACC6"/></a:accent5>
            <a:accent6><a:srgbClr val="F79646"/></a:accent6>
            <a:hlink><a:srgbClr val="0000FF"/></a:hlink>
            <a:folHlink><a:srgbClr val="800080"/></a:folHlink>
        </a:clrScheme>
        <a:fontScheme name="Office">
            <a:majorFont>
                <a:latin typeface="Calibri"/>
                <a:ea typeface=""/>
                <a:cs typeface=""/>
            </a:majorFont>
            <a:minorFont>
                <a:latin typeface="Calibri"/>
                <a:ea typeface=""/>
                <a:cs typeface=""/>
            </a:minorFont>
        </a:fontScheme>
        <a:fmtScheme name="Office">
            <a:fillStyleLst>
                <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                <a:gradFill rotWithShape="1">
                    <a:gsLst>
                        <a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="50000"/><a:satMod val="300000"/></a:schemeClr></a:gs>
                        <a:gs pos="35000"><a:schemeClr val="phClr"><a:tint val="37000"/><a:satMod val="300000"/></a:schemeClr></a:gs>
                        <a:gs pos="100000"><a:schemeClr val="phClr"><a:tint val="15000"/><a:satMod val="350000"/></a:schemeClr></a:gs>
                    </a:gsLst>
                    <a:lin ang="16200000" scaled="1"/>
                </a:gradFill>
                <a:gradFill rotWithShape="1">
                    <a:gsLst>
                        <a:gs pos="0"><a:schemeClr val="phClr"><a:shade val="51000"/><a:satMod val="130000"/></a:schemeClr></a:gs>
                        <a:gs pos="80000"><a:schemeClr val="phClr"><a:shade val="93000"/><a:satMod val="130000"/></a:schemeClr></a:gs>
                        <a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="94000"/><a:satMod val="135000"/></a:schemeClr></a:gs>
                    </a:gsLst>
                    <a:lin ang="16200000" scaled="0"/>
                </a:gradFill>
            </a:fillStyleLst>
            <a:lnStyleLst>
                <a:ln w="9525" cap="flat" cmpd="sng" algn="ctr">
                    <a:solidFill><a:schemeClr val="phClr"><a:shade val="95000"/><a:satMod val="105000"/></a:schemeClr></a:solidFill>
                    <a:prstDash val="solid"/>
                </a:ln>
                <a:ln w="25400" cap="flat" cmpd="sng" algn="ctr">
                    <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                    <a:prstDash val="solid"/>
                </a:ln>
                <a:ln w="38100" cap="flat" cmpd="sng" algn="ctr">
                    <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                    <a:prstDash val="solid"/>
                </a:ln>
            </a:lnStyleLst>
            <a:effectStyleLst>
                <a:effectStyle>
                    <a:effectLst>
                        <a:outerShdw blurRad="40000" dist="20000" dir="5400000" rotWithShape="0">
                            <a:srgbClr val="000000"><a:alpha val="38000"/></a:srgbClr>
                        </a:outerShdw>
                    </a:effectLst>
                </a:effectStyle>
                <a:effectStyle>
                    <a:effectLst>
                        <a:outerShdw blurRad="40000" dist="23000" dir="5400000" rotWithShape="0">
                            <a:srgbClr val="000000"><a:alpha val="35000"/></a:srgbClr>
                        </a:outerShdw>
                    </a:effectLst>
                </a:effectStyle>
                <a:effectStyle>
                    <a:effectLst>
                        <a:outerShdw blurRad="40000" dist="23000" dir="5400000" rotWithShape="0">
                            <a:srgbClr val="000000"><a:alpha val="35000"/></a:srgbClr>
                        </a:outerShdw>
                    </a:effectLst>
                </a:effectStyle>
            </a:effectStyleLst>
            <a:bgFillStyleLst>
                <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                <a:gradFill rotWithShape="1">
                    <a:gsLst>
                        <a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="40000"/><a:satMod val="350000"/></a:schemeClr></a:gs>
                        <a:gs pos="40000"><a:schemeClr val="phClr"><a:tint val="45000"/><a:shade val="99000"/><a:satMod val="350000"/></a:schemeClr></a:gs>
                        <a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="20000"/><a:satMod val="255000"/></a:schemeClr></a:gs>
                    </a:gsLst>
                    <a:path path="circle">
                        <a:fillToRect l="50000" t="-80000" r="50000" b="180000"/>
                    </a:path>
                </a:gradFill>
                <a:gradFill rotWithShape="1">
                    <a:gsLst>
                        <a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="80000"/><a:satMod val="300000"/></a:schemeClr></a:gs>
                        <a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="30000"/><a:satMod val="200000"/></a:schemeClr></a:gs>
                    </a:gsLst>
                    <a:path path="circle">
                        <a:fillToRect l="50000" t="50000" r="50000" b="50000"/>
                    </a:path>
                </a:gradFill>
            </a:bgFillStyleLst>
        </a:fmtScheme>
    </a:themeElements>
</a:theme>'''
        (base_path / 'ppt' / 'theme' / 'theme1.xml').write_text(theme_xml, encoding='utf-8')

        # Create minimal slide layout
        layout_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" preserve="1">
    <p:cSld name="Blank">
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm/>
            </p:grpSpPr>
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sldLayout>'''
        (base_path / 'ppt' / 'slideLayouts' / 'slideLayout1.xml').write_text(layout_xml, encoding='utf-8')

        # Create minimal slide master
        master_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:cSld>
        <p:bg>
            <p:bgRef idx="1001">
                <a:schemeClr val="bg1"/>
            </p:bgRef>
        </p:bg>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm/>
            </p:grpSpPr>
        </p:spTree>
    </p:cSld>
    <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
    <p:sldLayoutIdLst>
        <p:sldLayoutId id="2147483649" r:id="rId1"/>
    </p:sldLayoutIdLst>
    <p:txStyles>
        <p:titleStyle>
            <a:lvl1pPr marL="0" algn="ctr" defTabSz="914400" rtl="0" eaLnBrk="1" latinLnBrk="0" hangingPunct="1">
                <a:defRPr sz="4400" kern="1200">
                    <a:solidFill><a:schemeClr val="tx1"/></a:solidFill>
                    <a:latin typeface="+mj-lt"/>
                    <a:ea typeface="+mj-ea"/>
                    <a:cs typeface="+mj-cs"/>
                </a:defRPr>
            </a:lvl1pPr>
        </p:titleStyle>
        <p:bodyStyle>
            <a:lvl1pPr marL="342900" indent="-342900" algn="l" defTabSz="914400" rtl="0" eaLnBrk="1" latinLnBrk="0" hangingPunct="1">
                <a:defRPr sz="1800" kern="1200">
                    <a:solidFill><a:schemeClr val="tx1"/></a:solidFill>
                    <a:latin typeface="+mn-lt"/>
                    <a:ea typeface="+mn-ea"/>
                    <a:cs typeface="+mn-cs"/>
                </a:defRPr>
            </a:lvl1pPr>
        </p:bodyStyle>
        <p:otherStyle>
            <a:defPPr>
                <a:defRPr lang="en-US"/>
            </a:defPPr>
        </p:otherStyle>
    </p:txStyles>
</p:sldMaster>'''
        (base_path / 'ppt' / 'slideMasters' / 'slideMaster1.xml').write_text(master_xml, encoding='utf-8')

        # Create relationships for master and layout (required to prevent PowerPoint from sulking)
        master_rels = self._create_master_relationships()
        (base_path / 'ppt' / 'slideMasters' / '_rels').mkdir(parents=True, exist_ok=True)
        (base_path / 'ppt' / 'slideMasters' / '_rels' / 'slideMaster1.xml.rels').write_text(master_rels, encoding='utf-8')

        layout_rels = self._create_layout_relationships()
        (base_path / 'ppt' / 'slideLayouts' / '_rels').mkdir(parents=True, exist_ok=True)
        (base_path / 'ppt' / 'slideLayouts' / '_rels' / 'slideLayout1.xml.rels').write_text(layout_rels, encoding='utf-8')

    def _create_slide_xml(self, drawingml_shapes: str) -> str:
        """Create slide XML with embedded DrawingML shapes."""

        # Clean up the DrawingML shapes - remove leading whitespace
        shapes_clean = '\n'.join([line.strip() for line in drawingml_shapes.split('\n') if line.strip()])

        slide_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
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
                    <a:ext cx="{self.slide_width}" cy="{self.slide_height}"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="{self.slide_width}" cy="{self.slide_height}"/>
                </a:xfrm>
            </p:grpSpPr>
            {shapes_clean}
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sld>'''

        return slide_xml

    def add_image(self, image_path: str) -> str:
        """Add image to PPTX and return embed ID."""
        file_ext = Path(image_path).suffix.lower().lstrip('.')
        embed_id = f"rId{self.next_rel_id}"
        self.next_rel_id += 1

        self.images.append((embed_id, image_path, file_ext))
        return embed_id

    def _copy_images_to_media(self, base_path: Path):
        """Copy all registered images to the media directory."""
        media_dir = base_path / 'ppt' / 'media'
        media_dir.mkdir(parents=True, exist_ok=True)

        for i, (embed_id, image_path, file_ext) in enumerate(self.images):
            target_name = f"image{i+1}.{file_ext}"
            target_path = media_dir / target_name

            # Copy image file
            shutil.copy2(image_path, target_path)

            # Update the images list with the final media path
            self.images[i] = (embed_id, f"media/{target_name}", file_ext)

    def _create_slide_relationships(self) -> str:
        """Create slide relationships XML including image relationships."""
        relationships = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
                        '    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>']

        # Add image relationships
        for embed_id, media_path, _ in self.images:
            relationships.append(f'    <Relationship Id="{embed_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../{media_path}"/>')

        relationships.append('</Relationships>')
        return '\n'.join(relationships)

    def _create_master_relationships(self) -> str:
        """slideMaster1.xml.rels: links to theme and layout."""
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>'''

    def _create_layout_relationships(self) -> str:
        """slideLayout1.xml.rels: back-link to its slideMaster."""
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>'''

    def _next_id(self) -> int:
        """Generate next unique shape ID."""
        self._next_shape_id += 1
        return self._next_shape_id

    def add_picture(self, embed_id: str, x: str, y: str, width: str, height: str,
                    name: str = "Picture") -> str:
        """
        Return a <p:pic> DrawingML block that references an image relationship (embed_id).
        Coordinates and size support unit strings (e.g., '1in', '2.5cm', '100px').

        Args:
            embed_id: Relationship ID from add_image()
            x: X position with units (e.g., '1in', '2.54cm')
            y: Y position with units (e.g., '1in', '2.54cm')
            width: Width with units (e.g., '3in', '7.62cm')
            height: Height with units (e.g., '2in', '5.08cm')
            name: Display name for the picture

        Returns:
            DrawingML XML for the picture shape

        NOTE: You must have called add_image(path) beforehand to allocate the embed_id
        and to inject the slide relationship in slide1.xml.rels.
        """
        # Convert units to EMUs
        if self.unit_converter:
            x_emu = int(self.unit_converter.to_emu(x))
            y_emu = int(self.unit_converter.to_emu(y))
            w_emu = int(self.unit_converter.to_emu(width))
            h_emu = int(self.unit_converter.to_emu(height))
        else:
            # Fallback: assume values are already in EMUs if no converter
            try:
                x_emu = int(float(x))
                y_emu = int(float(y))
                w_emu = int(float(width))
                h_emu = int(float(height))
            except ValueError:
                raise ValueError(
                    f"No unit converter available and values are not numeric: "
                    f"x='{x}', y='{y}', width='{width}', height='{height}'. "
                    f"Either provide a UnitConverter or use numeric EMU values."
                )

        # PowerPoint wants a unique shape id per picture
        shape_id = self._next_id()

        return f'''<p:pic xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                         xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                         xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:nvPicPr>
    <p:cNvPr id="{shape_id}" name="{name} {shape_id}"/>
    <p:cNvPicPr>
      <a:picLocks noChangeAspect="1"/>
    </p:cNvPicPr>
    <p:nvPr/>
  </p:nvPicPr>
  <p:blipFill>
    <a:blip r:embed="{embed_id}"/>
    <a:stretch><a:fillRect/></a:stretch>
  </a:blipFill>
  <p:spPr>
    <a:xfrm>
      <a:off x="{x_emu}" y="{y_emu}"/>
      <a:ext cx="{w_emu}" cy="{h_emu}"/>
    </a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
</p:pic>'''

    def _zip_pptx_structure(self, temp_path: Path, output_path: str):
        """Create ZIP archive from PPTX directory structure."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(temp_path))
                    zipf.write(file_path, arcname)


# Smoke test and usage examples
if __name__ == "__main__":
    # Test 1: Rectangle only (no repair dialogs, visible shape)
    rect = """
    <p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
          xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
      <p:nvSpPr>
        <p:cNvPr id="1001" name="Rect 1001"/>
        <p:cNvSpPr/>
        <p:nvPr/>
      </p:nvSpPr>
      <p:spPr>
        <a:xfrm>
          <a:off x="1143000" y="1143000"/>
          <a:ext cx="2286000" cy="1143000"/>
        </a:xfrm>
        <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        <a:solidFill><a:srgbClr val="24394B"/></a:solidFill>
        <a:ln><a:noFill/></a:ln>
      </p:spPr>
      <p:txBody>
        <a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p>
      </p:txBody>
    </p:sp>
    """.strip()

    out = "minimal_demo.pptx"
    PPTXBuilder().create_minimal_pptx(rect, out)
    print(f"wrote {out} - rectangle at ~1.25\" from top-left")

    # Test 2: Picture example with units system (requires an image file)
    # Uncomment if you have an image to test:
    """
    from src.services.conversion_services import ConversionServices

    # Create services with unit converter
    services = ConversionServices.create_default()
    builder = services.pptx_builder

    # 1) Register an image file → get rId (also wires slide1.xml.rels)
    # rid = builder.add_image("logo.png")  # Replace with actual image path

    # 2) Create picture shape XML (position 1" x 1", size 3" x 2") - now with unit strings!
    # pic = builder.add_picture(rid, "1in", "1in", "3in", "2in")

    # 3) Build PPTX with this shape
    # builder.create_minimal_pptx(pic, "picture_demo.pptx")
    # print("wrote picture_demo.pptx - image at 1\" x 1\" position using units!")
    """
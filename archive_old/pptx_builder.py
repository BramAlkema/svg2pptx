#!/usr/bin/env python3
"""Build valid PPTX files using XML templates and lxml manipulation."""

import zipfile
import sys
from pathlib import Path
from lxml import etree as ET

sys.path.append('.')
from src.units import unit

class PPTXBuilder:
    def __init__(self, template_dir="pptx_templates"):
        self.template_dir = Path(template_dir)
        self.shapes = []
        self.shape_id_counter = 2  # Start at 2 (1 is reserved for group)

    def load_template(self, filename):
        """Load an XML template file"""
        template_path = self.template_dir / filename
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def add_text(self, text, x, y, font_size=24, color="000000", align="ctr"):
        """Add a text element to the slide"""
        # Load the real PowerPoint text template
        text_template = self.load_template("real_text_template.xml")

        # Calculate EMU coordinates (center the text)
        slide_width_emu = unit("10in").to_emu()
        slide_height_emu = unit("7.5in").to_emu()

        # Convert SVG coordinates to EMU
        x_emu = int((x / 400) * slide_width_emu)  # Assuming 400px wide SVG
        y_emu = int((y / 300) * slide_height_emu)  # Assuming 300px tall SVG

        # Text box dimensions (make generous for now)
        width_emu = unit("4in").to_emu()
        height_emu = unit("1in").to_emu()

        # Center the text box around the coordinate
        x_emu -= width_emu // 2
        y_emu -= height_emu // 2

        # Fill in template variables (no font size - PowerPoint handles it)
        text_xml = text_template.format(
            SHAPE_ID=self.shape_id_counter,
            X_EMU=x_emu,
            Y_EMU=y_emu,
            WIDTH_EMU=width_emu,
            HEIGHT_EMU=height_emu,
            TEXT_COLOR=color,
            TEXT_CONTENT=self._escape_xml(text)
        )

        self.shapes.append(text_xml)
        self.shape_id_counter += 1

    def _escape_xml(self, text):
        """Escape XML special characters"""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))

    def build_slide_xml(self):
        """Build the complete slide XML"""
        # Load slide template
        slide_template = self.load_template("slide_template.xml")

        # Parse the slide template
        slide_root = ET.fromstring(slide_template.encode('utf-8'))

        # Find the spTree element
        spTree = slide_root.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}spTree')

        # Add all shapes to spTree
        for shape_xml in self.shapes:
            shape_element = ET.fromstring(shape_xml.encode('utf-8'))
            spTree.append(shape_element)

        # Return the complete slide XML
        return ET.tostring(slide_root, encoding='utf-8', xml_declaration=True, pretty_print=True)

    def create_pptx(self, filename):
        """Create the complete PPTX file"""
        with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as pptx:
            # Content types
            pptx.writestr('[Content_Types].xml', self.load_template("content_types.xml"))

            # Main relationships
            pptx.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>''')

            # Presentation
            pptx.writestr('ppt/presentation.xml', self.load_template("presentation.xml"))

            # Presentation relationships
            pptx.writestr('ppt/_rels/presentation.xml.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>''')

            # Slide relationships
            pptx.writestr('ppt/slides/_rels/slide1.xml.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>''')

            # Simple slide master
            pptx.writestr('ppt/slideMasters/slideMaster1.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
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
                    <a:ext cx="9144000" cy="6858000"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="9144000" cy="6858000"/>
                </a:xfrm>
            </p:grpSpPr>
        </p:spTree>
    </p:cSld>
    <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
    <p:sldLayoutIdLst>
        <p:sldLayoutId id="2147483649" r:id="rId1"/>
    </p:sldLayoutIdLst>
</p:sldMaster>''')

            # Simple slide layout
            pptx.writestr('ppt/slideLayouts/slideLayout1.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" type="blank" preserve="1">
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
                    <a:ext cx="9144000" cy="6858000"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="9144000" cy="6858000"/>
                </a:xfrm>
            </p:grpSpPr>
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sldLayout>''')

            # Our slide with content
            slide_xml = self.build_slide_xml()
            pptx.writestr('ppt/slides/slide1.xml', slide_xml)

if __name__ == "__main__":
    # Test the builder
    builder = PPTXBuilder()

    # Add some test text
    builder.add_text("BIG RED TEXT", 200, 150, font_size=48, color="FF0000", align="ctr")

    # Create the PPTX
    builder.create_pptx("debug_template_based.pptx")
    print("✅ Created debug_template_based.pptx using XML templates and lxml")
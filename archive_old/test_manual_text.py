#!/usr/bin/env python3
"""Manually create a text-containing rectangle using the exact working XML structure."""

import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO

# Copy the working rectangle structure and modify it to contain text
slide_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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
                    <a:ext cx="9144000" cy="6858000"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="9144000" cy="6858000"/>
                </a:xfrm>
            </p:grpSpPr>
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="1000" name="Rectangle 1000"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="3429000" y="2286000"/>
                        <a:ext cx="2286000" cy="1143000"/>
                    </a:xfrm>
                    <a:prstGeom prst="rect">
                        <a:avLst/>
                    </a:prstGeom>
                    <a:solidFill><a:srgbClr val="FF0000"/></a:solidFill>
                </p:spPr>
                <p:txBody>
                    <a:bodyPr/>
                    <a:lstStyle/>
                    <a:p>
                        <a:pPr/>
                        <a:r>
                            <a:rPr sz="96">
                                <a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>
                            </a:rPr>
                            <a:t>TEST TEXT</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sld>'''

# Extract other files from working rectangle PPTX
with zipfile.ZipFile('debug_shape_test.pptx', 'r') as src_zip:
    # Create new PPTX with modified slide
    with zipfile.ZipFile('debug_manual_text.pptx', 'w') as new_zip:
        # Copy all files except slide1.xml
        for item in src_zip.infolist():
            if item.filename != 'ppt/slides/slide1.xml':
                data = src_zip.read(item.filename)
                new_zip.writestr(item, data)

        # Add our modified slide
        new_zip.writestr('ppt/slides/slide1.xml', slide_xml)

print("✅ Created debug_manual_text.pptx with manually crafted text")
print("This uses the exact working rectangle structure but adds text content")
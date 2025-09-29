#!/usr/bin/env python3
"""Create a valid PPTX from scratch using proper XML structure and lxml."""

import zipfile
from lxml import etree as ET
from datetime import datetime

def create_content_types():
    """Create [Content_Types].xml"""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-presentationml.presentation.main+xml"/>
    <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-presentationml.slideMaster+xml"/>
    <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-presentationml.slideLayout+xml"/>
    <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-presentationml.slide+xml"/>
    <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-drawingml.theme+xml"/>
</Types>'''

def create_main_rels():
    """Create _rels/.rels"""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>'''

def create_presentation_xml():
    """Create ppt/presentation.xml"""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" saveSubsetFonts="1">
    <p:sldMasterIdLst>
        <p:sldMasterId id="2147483648" r:id="rId1"/>
    </p:sldMasterIdLst>
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId2"/>
    </p:sldIdLst>
    <p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>
    <p:notesSz cx="6858000" cy="9144000"/>
    <p:defaultTextStyle>
        <a:defPPr>
            <a:defRPr lang="en-US"/>
        </a:defPPr>
    </p:defaultTextStyle>
</p:presentation>'''

def create_presentation_rels():
    """Create ppt/_rels/presentation.xml.rels"""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>'''

def create_slide_rels():
    """Create ppt/slides/_rels/slide1.xml.rels"""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>'''

def create_slide_master():
    """Create ppt/slideMasters/slideMaster1.xml"""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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
    <p:txStyles>
        <p:titleStyle>
            <a:lvl1pPr>
                <a:defRPr sz="4400"/>
            </a:lvl1pPr>
        </p:titleStyle>
        <p:bodyStyle>
            <a:lvl1pPr>
                <a:defRPr sz="2800"/>
            </a:lvl1pPr>
        </p:bodyStyle>
        <p:otherStyle>
            <a:lvl1pPr>
                <a:defRPr sz="1800"/>
            </a:lvl1pPr>
        </p:otherStyle>
    </p:txStyles>
</p:sldMaster>'''

def create_slide_layout():
    """Create ppt/slideLayouts/slideLayout1.xml"""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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
</p:sldLayout>'''

def create_theme():
    """Create ppt/theme/theme1.xml"""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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
            <a:accent6><a:srgbClr val="F366A7"/></a:accent6>
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

def create_slide_with_text():
    """Create slide1.xml with proper text using lxml"""
    # Create the slide structure using lxml with namespaces
    nsmap = {
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    }

    slide = ET.Element("{http://schemas.openxmlformats.org/presentationml/2006/main}sld", nsmap=nsmap)

    # Create cSld
    cSld = ET.SubElement(slide, "{http://schemas.openxmlformats.org/presentationml/2006/main}cSld")

    # Create spTree
    spTree = ET.SubElement(cSld, "{http://schemas.openxmlformats.org/presentationml/2006/main}spTree")

    # Group shape properties
    nvGrpSpPr = ET.SubElement(spTree, "{http://schemas.openxmlformats.org/presentationml/2006/main}nvGrpSpPr")
    cNvPr = ET.SubElement(nvGrpSpPr, "{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr")
    cNvPr.set("id", "1")
    cNvPr.set("name", "")
    ET.SubElement(nvGrpSpPr, "{http://schemas.openxmlformats.org/presentationml/2006/main}cNvGrpSpPr")
    ET.SubElement(nvGrpSpPr, "{http://schemas.openxmlformats.org/presentationml/2006/main}nvPr")

    # Group transform
    grpSpPr = ET.SubElement(spTree, "{http://schemas.openxmlformats.org/presentationml/2006/main}grpSpPr")
    xfrm = ET.SubElement(grpSpPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm")
    off = ET.SubElement(xfrm, "{http://schemas.openxmlformats.org/drawingml/2006/main}off")
    off.set("x", "0")
    off.set("y", "0")
    ext = ET.SubElement(xfrm, "{http://schemas.openxmlformats.org/drawingml/2006/main}ext")
    ext.set("cx", "9144000")
    ext.set("cy", "6858000")
    chOff = ET.SubElement(xfrm, "{http://schemas.openxmlformats.org/drawingml/2006/main}chOff")
    chOff.set("x", "0")
    chOff.set("y", "0")
    chExt = ET.SubElement(xfrm, "{http://schemas.openxmlformats.org/drawingml/2006/main}chExt")
    chExt.set("cx", "9144000")
    chExt.set("cy", "6858000")

    # Text shape
    sp = ET.SubElement(spTree, "{http://schemas.openxmlformats.org/presentationml/2006/main}sp")

    # Shape non-visual properties
    nvSpPr = ET.SubElement(sp, "{http://schemas.openxmlformats.org/presentationml/2006/main}nvSpPr")
    cNvPr = ET.SubElement(nvSpPr, "{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr")
    cNvPr.set("id", "2")
    cNvPr.set("name", "Text 2")
    ET.SubElement(nvSpPr, "{http://schemas.openxmlformats.org/presentationml/2006/main}cNvSpPr")
    ET.SubElement(nvSpPr, "{http://schemas.openxmlformats.org/presentationml/2006/main}nvPr")

    # Shape properties
    spPr = ET.SubElement(sp, "{http://schemas.openxmlformats.org/presentationml/2006/main}spPr")
    xfrm = ET.SubElement(spPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm")
    off = ET.SubElement(xfrm, "{http://schemas.openxmlformats.org/drawingml/2006/main}off")
    off.set("x", "4572000")  # Center X
    off.set("y", "3429000")  # Center Y
    ext = ET.SubElement(xfrm, "{http://schemas.openxmlformats.org/drawingml/2006/main}ext")
    ext.set("cx", "2286000")  # Width
    ext.set("cy", "914400")   # Height

    # Geometry
    prstGeom = ET.SubElement(spPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}prstGeom")
    prstGeom.set("prst", "rect")
    ET.SubElement(prstGeom, "{http://schemas.openxmlformats.org/drawingml/2006/main}avLst")

    # No fill for text box
    ET.SubElement(spPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}noFill")

    # Text body
    txBody = ET.SubElement(sp, "{http://schemas.openxmlformats.org/presentationml/2006/main}txBody")
    ET.SubElement(txBody, "{http://schemas.openxmlformats.org/drawingml/2006/main}bodyPr")
    ET.SubElement(txBody, "{http://schemas.openxmlformats.org/drawingml/2006/main}lstStyle")

    # Paragraph
    p = ET.SubElement(txBody, "{http://schemas.openxmlformats.org/drawingml/2006/main}p")
    pPr = ET.SubElement(p, "{http://schemas.openxmlformats.org/drawingml/2006/main}pPr")
    pPr.set("algn", "ctr")

    # Run
    r = ET.SubElement(p, "{http://schemas.openxmlformats.org/drawingml/2006/main}r")
    rPr = ET.SubElement(r, "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr")
    rPr.set("sz", "4400")  # 44pt
    rPr.set("b", "1")      # Bold

    # Text color
    solidFill = ET.SubElement(rPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill")
    srgbClr = ET.SubElement(solidFill, "{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr")
    srgbClr.set("val", "FF0000")  # Red

    # Text content
    t = ET.SubElement(r, "{http://schemas.openxmlformats.org/drawingml/2006/main}t")
    t.text = "HELLO WORLD"

    # Color map override
    clrMapOvr = ET.SubElement(slide, "{http://schemas.openxmlformats.org/presentationml/2006/main}clrMapOvr")
    ET.SubElement(clrMapOvr, "{http://schemas.openxmlformats.org/drawingml/2006/main}masterClrMapping")

    return ET.tostring(slide, encoding='utf-8', xml_declaration=True, pretty_print=True).decode('utf-8')

def create_pptx():
    """Create a complete valid PPTX file"""
    with zipfile.ZipFile('debug_valid_structure.pptx', 'w', zipfile.ZIP_DEFLATED) as pptx:
        # Content types
        pptx.writestr('[Content_Types].xml', create_content_types())

        # Main relationships
        pptx.writestr('_rels/.rels', create_main_rels())

        # Presentation files
        pptx.writestr('ppt/presentation.xml', create_presentation_xml())
        pptx.writestr('ppt/_rels/presentation.xml.rels', create_presentation_rels())

        # Slide master and layout
        pptx.writestr('ppt/slideMasters/slideMaster1.xml', create_slide_master())
        pptx.writestr('ppt/slideLayouts/slideLayout1.xml', create_slide_layout())

        # Theme
        pptx.writestr('ppt/theme/theme1.xml', create_theme())

        # Slide with text
        pptx.writestr('ppt/slides/slide1.xml', create_slide_with_text())
        pptx.writestr('ppt/slides/_rels/slide1.xml.rels', create_slide_rels())

if __name__ == "__main__":
    create_pptx()
    print("✅ Created debug_valid_structure.pptx using proper XML templates and lxml")
    print("This file should be completely valid PowerPoint format")
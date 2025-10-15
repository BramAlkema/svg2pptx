"""
Utilities for constructing the PPTX directory structure and content types.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


class PPTXManifestBuilder:
    """Create the static PPTX package manifest (content types and relationship files)."""

    def __init__(self, image_extensions: Iterable[str] | None = None):
        self.image_extensions = set(image_extensions or [])

    def write_manifest(self, base_path: Path) -> None:
        self._write_content_types(base_path)
        self._write_root_rels(base_path)
        self._write_presentation(base_path)
        self._write_presentation_rels(base_path)

    def write_theme(self, base_path: Path) -> None:
        (base_path / 'ppt' / 'theme').mkdir(parents=True, exist_ok=True)
        (base_path / 'ppt' / 'theme' / 'theme1.xml').write_text(self._theme_xml(), encoding='utf-8')

    def write_layout_and_master(self, base_path: Path) -> None:
        layout_dir = base_path / 'ppt' / 'slideLayouts'
        master_dir = base_path / 'ppt' / 'slideMasters'
        layout_dir.mkdir(parents=True, exist_ok=True)
        master_dir.mkdir(parents=True, exist_ok=True)

        (layout_dir / 'slideLayout1.xml').write_text(self._layout_xml(), encoding='utf-8')
        (master_dir / 'slideMaster1.xml').write_text(self._master_xml(), encoding='utf-8')

        (layout_dir / '_rels').mkdir(exist_ok=True)
        (layout_dir / '_rels' / 'slideLayout1.xml.rels').write_text(self._layout_rels(), encoding='utf-8')

        (master_dir / '_rels').mkdir(exist_ok=True)
        (master_dir / '_rels' / 'slideMaster1.xml.rels').write_text(self._master_rels(), encoding='utf-8')

    def write_doc_props(self, base_path: Path) -> None:
        doc_props_dir = base_path / 'docProps'
        doc_props_dir.mkdir(parents=True, exist_ok=True)
        (doc_props_dir / 'core.xml').write_text(self._core_xml(), encoding='utf-8')
        (doc_props_dir / 'app.xml').write_text(self._app_xml(), encoding='utf-8')

    def _write_content_types(self, base_path: Path) -> None:
        image_types = '\n'.join(
            f'    <Default Extension="{ext}" ContentType="image/{self._content_type_for_extension(ext)}"/>'
            for ext in sorted(self.image_extensions)
        )

        content_types = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
{image_types}
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
    <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
    <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
    <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
    <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
    <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
    <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''
        (base_path / '[Content_Types].xml').write_text(content_types, encoding='utf-8')

    def _write_root_rels(self, base_path: Path) -> None:
        main_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>'''
        (base_path / '_rels').mkdir(parents=True, exist_ok=True)
        (base_path / '_rels' / '.rels').write_text(main_rels, encoding='utf-8')

    def _write_presentation(self, base_path: Path) -> None:
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

        ppt_dir = base_path / 'ppt'
        ppt_dir.mkdir(parents=True, exist_ok=True)
        (ppt_dir / 'presentation.xml').write_text(presentation_xml, encoding='utf-8')

    def _write_presentation_rels(self, base_path: Path) -> None:
        pres_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>'''
        rels_dir = base_path / 'ppt' / '_rels'
        rels_dir.mkdir(parents=True, exist_ok=True)
        (rels_dir / 'presentation.xml.rels').write_text(pres_rels, encoding='utf-8')

    def _content_type_for_extension(self, ext: str) -> str:
        if ext in {'jpg', 'jpeg'}:
            return 'jpeg'
        return ext

    @staticmethod
    def _core_xml() -> str:
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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

    @staticmethod
    def _app_xml() -> str:
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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

    @staticmethod
    def _theme_xml() -> str:
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

    @staticmethod
    def _layout_xml() -> str:
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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

    @staticmethod
    def _master_xml() -> str:
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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

    @staticmethod
    def _master_rels() -> str:
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>'''

    @staticmethod
    def _layout_rels() -> str:
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>'''


__all__ = ["PPTXManifestBuilder"]

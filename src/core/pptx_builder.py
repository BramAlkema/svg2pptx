"""Utilities for programmatically constructing minimal PPTX packages."""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path
from typing import Union


PathLike = Union[str, os.PathLike[str]]


class PPTXBuilder:
    """Build PPTX files with handwritten XML and package structure."""

    def __init__(self, slide_width: int = 9_144_000, slide_height: int = 6_858_000) -> None:
        """Create a builder configured for a given slide size.

        Args:
            slide_width: Slide width in English Metric Units (EMU).
            slide_height: Slide height in English Metric Units (EMU).
        """
        self.slide_width = slide_width
        self.slide_height = slide_height

    def create_minimal_pptx(self, drawingml_shapes: str, output_path: PathLike) -> None:
        """Create a PPTX that embeds the provided DrawingML markup."""
        output_path = Path(output_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self._create_pptx_structure(temp_path)

            slide_xml = self._create_slide_xml(drawingml_shapes)
            (temp_path / "ppt" / "slides" / "slide1.xml").write_text(slide_xml, encoding="utf-8")

            self._zip_pptx_structure(temp_path, output_path)

    def _create_pptx_structure(self, base_path: Path) -> None:
        """Create the PowerPoint package directory structure and boilerplate files."""
        (base_path / "ppt" / "slides").mkdir(parents=True)
        (base_path / "ppt" / "slideLayouts").mkdir(parents=True)
        (base_path / "ppt" / "slideMasters").mkdir(parents=True)
        (base_path / "ppt" / "theme").mkdir(parents=True)
        (base_path / "_rels").mkdir(parents=True)
        (base_path / "ppt" / "_rels").mkdir(parents=True)
        (base_path / "ppt" / "slides" / "_rels").mkdir(parents=True)

        content_types = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">\n"
            "    <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>\n"
            "    <Default Extension=\"xml\" ContentType=\"application/xml\"/>\n"
            "    <Override PartName=\"/ppt/presentation.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml\"/>\n"
            "    <Override PartName=\"/ppt/slides/slide1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slide+xml\"/>\n"
            "    <Override PartName=\"/ppt/theme/theme1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.theme+xml\"/>\n"
            "    <Override PartName=\"/ppt/slideLayouts/slideLayout1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml\"/>\n"
            "    <Override PartName=\"/ppt/slideMasters/slideMaster1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml\"/>\n"
            "</Types>"
        )
        (base_path / "[Content_Types].xml").write_text(content_types, encoding="utf-8")

        main_rels = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n"
            "    <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"ppt/presentation.xml\"/>\n"
            "</Relationships>"
        )
        (base_path / "_rels" / ".rels").write_text(main_rels, encoding="utf-8")

        presentation_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            "<p:presentation xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\" xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">\n"
            "    <p:sldMasterIdLst>\n"
            "        <p:sldMasterId id=\"2147483648\" r:id=\"rId1\"/>\n"
            "    </p:sldMasterIdLst>\n"
            "    <p:sldIdLst>\n"
            "        <p:sldId id=\"256\" r:id=\"rId2\"/>\n"
            "    </p:sldIdLst>\n"
            f"    <p:sldSz cx=\"{self.slide_width}\" cy=\"{self.slide_height}\"/>\n"
            "    <p:notesSz cx=\"6858000\" cy=\"9144000\"/>\n"
            "</p:presentation>"
        )
        (base_path / "ppt" / "presentation.xml").write_text(presentation_xml, encoding="utf-8")

        ppt_rels = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n"
            "    <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster\" Target=\"slideMasters/slideMaster1.xml\"/>\n"
            "    <Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide\" Target=\"slides/slide1.xml\"/>\n"
            "    <Relationship Id=\"rId3\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme\" Target=\"theme/theme1.xml\"/>\n"
            "</Relationships>"
        )
        (base_path / "ppt" / "_rels" / "presentation.xml.rels").write_text(ppt_rels, encoding="utf-8")

        slide_rels = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n"
            "    <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout1.xml\"/>\n"
            "</Relationships>"
        )
        (base_path / "ppt" / "slides" / "_rels" / "slide1.xml.rels").write_text(slide_rels, encoding="utf-8")

        theme_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            "<a:theme xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" name=\"Office Theme\">\n"
            "    <a:themeElements>\n"
            "        <a:clrScheme name=\"Office\">\n"
            "            <a:dk1><a:sysClr val=\"windowText\" lastClr=\"000000\"/></a:dk1>\n"
            "            <a:lt1><a:sysClr val=\"window\" lastClr=\"FFFFFF\"/></a:lt1>\n"
            "            <a:dk2><a:srgbClr val=\"1F497D\"/></a:dk2>\n"
            "            <a:lt2><a:srgbClr val=\"EEECE1\"/></a:lt2>\n"
            "            <a:accent1><a:srgbClr val=\"4F81BD\"/></a:accent1>\n"
            "            <a:accent2><a:srgbClr val=\"F79646\"/></a:accent2>\n"
            "            <a:accent3><a:srgbClr val=\"9BBB59\"/></a:accent3>\n"
            "            <a:accent4><a:srgbClr val=\"8064A2\"/></a:accent4>\n"
            "            <a:accent5><a:srgbClr val=\"4BACC6\"/></a:accent5>\n"
            "            <a:accent6><a:srgbClr val=\"F79646\"/></a:accent6>\n"
            "            <a:hlink><a:srgbClr val=\"0000FF\"/></a:hlink>\n"
            "            <a:folHlink><a:srgbClr val=\"800080\"/></a:folHlink>\n"
            "        </a:clrScheme>\n"
            "        <a:fontScheme name=\"Office\">\n"
            "            <a:majorFont>\n"
            "                <a:latin typeface=\"Calibri\"/>\n"
            "                <a:ea typeface=\"\"/>\n"
            "                <a:cs typeface=\"\"/>\n"
            "            </a:majorFont>\n"
            "            <a:minorFont>\n"
            "                <a:latin typeface=\"Calibri\"/>\n"
            "                <a:ea typeface=\"\"/>\n"
            "                <a:cs typeface=\"\"/>\n"
            "            </a:minorFont>\n"
            "        </a:fontScheme>\n"
            "        <a:fmtScheme name=\"Office\">\n"
            "            <a:fillStyleLst>\n"
            "                <a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>\n"
            "                <a:gradFill rotWithShape=\"1\">\n"
            "                    <a:gsLst>\n"
            "                        <a:gs pos=\"0\"><a:schemeClr val=\"phClr\"><a:tint val=\"50000\"/><a:satMod val=\"300000\"/></a:schemeClr></a:gs>\n"
            "                        <a:gs pos=\"35000\"><a:schemeClr val=\"phClr\"><a:tint val=\"37000\"/><a:satMod val=\"300000\"/></a:schemeClr></a:gs>\n"
            "                        <a:gs pos=\"100000\"><a:schemeClr val=\"phClr\"><a:tint val=\"15000\"/><a:satMod val=\"350000\"/></a:schemeClr></a:gs>\n"
            "                    </a:gsLst>\n"
            "                    <a:lin ang=\"16200000\" scaled=\"1\"/>\n"
            "                </a:gradFill>\n"
            "                <a:gradFill rotWithShape=\"1\">\n"
            "                    <a:gsLst>\n"
            "                        <a:gs pos=\"0\"><a:schemeClr val=\"phClr\"><a:shade val=\"51000\"/><a:satMod val=\"130000\"/></a:schemeClr></a:gs>\n"
            "                        <a:gs pos=\"80000\"><a:schemeClr val=\"phClr\"><a:shade val=\"93000\"/><a:satMod val=\"130000\"/></a:schemeClr></a:gs>\n"
            "                        <a:gs pos=\"100000\"><a:schemeClr val=\"phClr\"><a:shade val=\"94000\"/><a:satMod val=\"135000\"/></a:schemeClr></a:gs>\n"
            "                    </a:gsLst>\n"
            "                    <a:lin ang=\"16200000\" scaled=\"0\"/>\n"
            "                </a:gradFill>\n"
            "            </a:fillStyleLst>\n"
            "            <a:lnStyleLst>\n"
            "                <a:ln w=\"9525\" cap=\"flat\" cmpd=\"sng\" algn=\"ctr\">\n"
            "                    <a:solidFill><a:schemeClr val=\"phClr\"><a:shade val=\"95000\"/><a:satMod val=\"105000\"/></a:schemeClr></a:solidFill>\n"
            "                    <a:prstDash val=\"solid\"/>\n"
            "                </a:ln>\n"
            "                <a:ln w=\"25400\" cap=\"flat\" cmpd=\"sng\" algn=\"ctr\">\n"
            "                    <a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>\n"
            "                    <a:prstDash val=\"solid\"/>\n"
            "                </a:ln>\n"
            "                <a:ln w=\"38100\" cap=\"flat\" cmpd=\"sng\" algn=\"ctr\">\n"
            "                    <a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>\n"
            "                    <a:prstDash val=\"solid\"/>\n"
            "                </a:ln>\n"
            "            </a:lnStyleLst>\n"
            "            <a:effectStyleLst>\n"
            "                <a:effectStyle>\n"
            "                    <a:effectLst>\n"
            "                        <a:outerShdw blurRad=\"40000\" dist=\"20000\" dir=\"5400000\" rotWithShape=\"0\">\n"
            "                            <a:srgbClr val=\"000000\"><a:alpha val=\"38000\"/></a:srgbClr>\n"
            "                        </a:outerShdw>\n"
            "                    </a:effectLst>\n"
            "                </a:effectStyle>\n"
            "                <a:effectStyle>\n"
            "                    <a:effectLst>\n"
            "                        <a:outerShdw blurRad=\"40000\" dist=\"23000\" dir=\"5400000\" rotWithShape=\"0\">\n"
            "                            <a:srgbClr val=\"000000\"><a:alpha val=\"35000\"/></a:srgbClr>\n"
            "                        </a:outerShdw>\n"
            "                    </a:effectLst>\n"
            "                </a:effectStyle>\n"
            "                <a:effectStyle>\n"
            "                    <a:effectLst>\n"
            "                        <a:outerShdw blurRad=\"40000\" dist=\"23000\" dir=\"5400000\" rotWithShape=\"0\">\n"
            "                            <a:srgbClr val=\"000000\"><a:alpha val=\"35000\"/></a:srgbClr>\n"
            "                        </a:outerShdw>\n"
            "                    </a:effectLst>\n"
            "                </a:effectStyle>\n"
            "            </a:effectStyleLst>\n"
            "            <a:bgFillStyleLst>\n"
            "                <a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>\n"
            "                <a:gradFill rotWithShape=\"1\">\n"
            "                    <a:gsLst>\n"
            "                        <a:gs pos=\"0\"><a:schemeClr val=\"phClr\"><a:tint val=\"40000\"/><a:satMod val=\"350000\"/></a:schemeClr></a:gs>\n"
            "                        <a:gs pos=\"40000\"><a:schemeClr val=\"phClr\"><a:tint val=\"45000\"/><a:shade val=\"99000\"/><a:satMod val=\"350000\"/></a:schemeClr></a:gs>\n"
            "                        <a:gs pos=\"100000\"><a:schemeClr val=\"phClr\"><a:shade val=\"20000\"/><a:satMod val=\"255000\"/></a:schemeClr></a:gs>\n"
            "                    </a:gsLst>\n"
            "                    <a:path path=\"circle\">\n"
            "                        <a:fillToRect l=\"50000\" t=\"-80000\" r=\"50000\" b=\"180000\"/>\n"
            "                    </a:path>\n"
            "                </a:gradFill>\n"
            "                <a:gradFill rotWithShape=\"1\">\n"
            "                    <a:gsLst>\n"
            "                        <a:gs pos=\"0\"><a:schemeClr val=\"phClr\"><a:tint val=\"80000\"/><a:satMod val=\"300000\"/></a:schemeClr></a:gs>\n"
            "                        <a:gs pos=\"100000\"><a:schemeClr val=\"phClr\"><a:shade val=\"30000\"/><a:satMod val=\"200000\"/></a:schemeClr></a:gs>\n"
            "                    </a:gsLst>\n"
            "                    <a:path path=\"circle\">\n"
            "                        <a:fillToRect l=\"50000\" t=\"50000\" r=\"50000\" b=\"50000\"/>\n"
            "                    </a:path>\n"
            "                </a:gradFill>\n"
            "            </a:bgFillStyleLst>\n"
            "        </a:fmtScheme>\n"
            "    </a:themeElements>\n"
            "</a:theme>"
        )
        (base_path / "ppt" / "theme" / "theme1.xml").write_text(theme_xml, encoding="utf-8")

        layout_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            "<p:sldLayout xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\" xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" preserve=\"1\">\n"
            "    <p:cSld name=\"Blank\">\n"
            "        <p:spTree>\n"
            "            <p:nvGrpSpPr>\n"
            "                <p:cNvPr id=\"1\" name=\"\"/>\n"
            "                <p:cNvGrpSpPr/>\n"
            "                <p:nvPr/>\n"
            "            </p:nvGrpSpPr>\n"
            "            <p:grpSpPr>\n"
            "                <a:xfrm/>\n"
            "            </p:grpSpPr>\n"
            "        </p:spTree>\n"
            "    </p:cSld>\n"
            "    <p:clrMapOvr>\n"
            "        <a:masterClrMapping/>\n"
            "    </p:clrMapOvr>\n"
            "</p:sldLayout>"
        )
        (base_path / "ppt" / "slideLayouts" / "slideLayout1.xml").write_text(layout_xml, encoding="utf-8")

        master_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            "<p:sldMaster xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\" xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">\n"
            "    <p:cSld>\n"
            "        <p:bg>\n"
            "            <p:bgRef idx=\"1001\">\n"
            "                <a:schemeClr val=\"bg1\"/>\n"
            "            </p:bgRef>\n"
            "        </p:bg>\n"
            "        <p:spTree>\n"
            "            <p:nvGrpSpPr>\n"
            "                <p:cNvPr id=\"1\" name=\"\"/>\n"
            "                <p:cNvGrpSpPr/>\n"
            "                <p:nvPr/>\n"
            "            </p:nvGrpSpPr>\n"
            "            <p:grpSpPr>\n"
            "                <a:xfrm/>\n"
            "            </p:grpSpPr>\n"
            "        </p:spTree>\n"
            "    </p:cSld>\n"
            "    <p:clrMap bg1=\"lt1\" tx1=\"dk1\" bg2=\"lt2\" tx2=\"dk2\" accent1=\"accent1\" accent2=\"accent2\" accent3=\"accent3\" accent4=\"accent4\" accent5=\"accent5\" accent6=\"accent6\" hlink=\"hlink\" folHlink=\"folHlink\"/>\n"
            "    <p:sldLayoutIdLst>\n"
            "        <p:sldLayoutId id=\"2147483649\" r:id=\"rId1\"/>\n"
            "    </p:sldLayoutIdLst>\n"
            "    <p:txStyles>\n"
            "        <p:titleStyle>\n"
            "            <a:lvl1pPr marL=\"0\" algn=\"ctr\" defTabSz=\"914400\" rtl=\"0\" eaLnBrk=\"1\" latinLnBrk=\"0\" hangingPunct=\"1\">\n"
            "                <a:defRPr sz=\"4400\" kern=\"1200\">\n"
            "                    <a:solidFill><a:schemeClr val=\"tx1\"/></a:solidFill>\n"
            "                    <a:latin typeface=\"+mj-lt\"/>\n"
            "                    <a:ea typeface=\"+mj-ea\"/>\n"
            "                    <a:cs typeface=\"+mj-cs\"/>\n"
            "                </a:defRPr>\n"
            "            </a:lvl1pPr>\n"
            "        </p:titleStyle>\n"
            "        <p:bodyStyle>\n"
            "            <a:lvl1pPr marL=\"342900\" indent=\"-342900\" algn=\"l\" defTabSz=\"914400\" rtl=\"0\" eaLnBrk=\"1\" latinLnBrk=\"0\" hangingPunct=\"1\">\n"
            "                <a:defRPr sz=\"1800\" kern=\"1200\">\n"
            "                    <a:solidFill><a:schemeClr val=\"tx1\"/></a:solidFill>\n"
            "                    <a:latin typeface=\"+mn-lt\"/>\n"
            "                    <a:ea typeface=\"+mn-ea\"/>\n"
            "                    <a:cs typeface=\"+mn-cs\"/>\n"
            "                </a:defRPr>\n"
            "            </a:lvl1pPr>\n"
            "        </p:bodyStyle>\n"
            "    </p:txStyles>\n"
            "</p:sldMaster>"
        )
        (base_path / "ppt" / "slideMasters" / "slideMaster1.xml").write_text(master_xml, encoding="utf-8")

    def _create_slide_xml(self, drawingml_shapes: str) -> str:
        """Build the slide XML for embedding DrawingML shapes."""
        lines = (line.strip() for line in drawingml_shapes.splitlines())
        shapes_clean = "\n".join(line for line in lines if line)

        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            "<p:sld xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\" xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">\n"
            "    <p:cSld>\n"
            "        <p:spTree>\n"
            "            <p:nvGrpSpPr>\n"
            "                <p:cNvPr id=\"1\" name=\"\"/>\n"
            "                <p:cNvGrpSpPr/>\n"
            "                <p:nvPr/>\n"
            "            </p:nvGrpSpPr>\n"
            "            <p:grpSpPr>\n"
            "                <a:xfrm>\n"
            "                    <a:off x=\"0\" y=\"0\"/>\n"
            f"                    <a:ext cx=\"{self.slide_width}\" cy=\"{self.slide_height}\"/>\n"
            "                    <a:chOff x=\"0\" y=\"0\"/>\n"
            f"                    <a:chExt cx=\"{self.slide_width}\" cy=\"{self.slide_height}\"/>\n"
            "                </a:xfrm>\n"
            "            </p:grpSpPr>\n"
            f"            {shapes_clean}\n"
            "        </p:spTree>\n"
            "    </p:cSld>\n"
            "    <p:clrMapOvr>\n"
            "        <a:masterClrMapping/>\n"
            "    </p:clrMapOvr>\n"
            "</p:sld>"
        )

    def _zip_pptx_structure(self, temp_path: Path, output_path: Path) -> None:
        """Package the PPTX directory structure into a zip archive."""
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_path in temp_path.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(temp_path))

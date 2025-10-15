from pathlib import Path
import zipfile

from lxml import etree as ET

from core.io.package_writer import PackageWriter
from core.io.template_store import TemplateStore
from core.io.embedder import EmbedderResult


NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def test_template_store_and_package_writer_workflow(tmp_path: Path) -> None:
    store = TemplateStore()
    writer = PackageWriter(template_store=store)

    # Minimal slide with no additional relationships or media
    slide = EmbedderResult(
        slide_xml="""<?xml version='1.0' encoding='UTF-8' standalone='yes'?><p:sld xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id='1' name=''/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld></p:sld>""",
        relationship_data=[],
        media_files=[],
    )

    output = tmp_path / "template_package.pptx"
    writer.write_package([slide], str(output))

    assert output.exists()

    with zipfile.ZipFile(output, "r") as archive:
        presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
        slide_ids = presentation.find("p:sldIdLst", namespaces=NS)
        assert len(slide_ids) == 1
        assert slide_ids[0].attrib[f"{{{NS['r']}}}id"] == "rId2"

        core_props = ET.fromstring(archive.read("docProps/core.xml"))
        title = core_props.find("dc:title", namespaces=NS)
        assert title is not None and title.text

        master_rels = ET.fromstring(archive.read("ppt/slideMasters/_rels/slideMaster1.xml.rels"))
        targets = {child.attrib["Target"] for child in master_rels}
        assert "../slideLayouts/slideLayout1.xml" in targets
        assert "../slideLayouts/slideLayout2.xml" in targets
        assert "../theme/theme1.xml" in targets

        files = set(archive.namelist())
        assert "ppt/slideLayouts/slideLayout2.xml" in files

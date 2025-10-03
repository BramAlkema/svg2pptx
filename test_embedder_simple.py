#!/usr/bin/env python3
"""
Simple Embedder Integration Test

Tests the MediaRequest processing without full IR dependencies.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent))

# Import directly from module files to avoid __init__.py import chains
import importlib
base_mod = importlib.import_module("core.map.base")
MediaRequest = base_mod.MediaRequest
MapperResult = base_mod.MapperResult
OutputFormat = base_mod.OutputFormat

embedder_mod = importlib.import_module("core.io.embedder")
DrawingMLEmbedder = embedder_mod.DrawingMLEmbedder

rel_mod = importlib.import_module("core.io.relationship_manager")
RelationshipManager = rel_mod.RelationshipManager

ct_mod = importlib.import_module("core.io.content_types")
ContentTypesManager = ct_mod.ContentTypesManager

from lxml import etree as ET

# Mock package writer
class MockPackageWriter:
    def __init__(self):
        self.files = {}

    def write_file(self, path: str, data: bytes):
        self.files[path] = data
        print(f"  📝 Wrote {path}: {len(data)} bytes")

# Minimal mock IR element
@dataclass
class MockElement:
    id: str = "test-image-1"

# Minimal mock scene
@dataclass
class MockScene:
    elements: List = None

    def __post_init__(self):
        if self.elements is None:
            self.elements = []

def main():
    print("=" * 60)
    print("SIMPLE EMBEDDER INTEGRATION TEST")
    print("=" * 60)

    # Create test image data
    png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100

    # Create sample <p:pic> XML (what ImageMapper would generate)
    print("\n1. Creating sample <p:pic> XML (ImageMapper output)...")
    pic_xml = """<p:pic xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                        xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                        xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:nvPicPr>
    <p:cNvPr id="1" name="Test Image"/>
    <p:cNvPicPr/>
    <p:nvPr/>
  </p:nvPicPr>
  <p:blipFill>
    <a:blip/>
    <a:stretch>
      <a:fillRect/>
    </a:stretch>
  </p:blipFill>
  <p:spPr>
    <a:xfrm>
      <a:off x="952500" y="1905000"/>
      <a:ext cx="2857500" cy="3810000"/>
    </a:xfrm>
    <a:prstGeom prst="rect">
      <a:avLst/>
    </a:prstGeom>
  </p:spPr>
</p:pic>"""
    print("  ✅ Sample XML created")
    print("     Note: <a:blip/> has NO r:embed attribute")

    # Create MediaRequest
    print("\n2. Creating MediaRequest...")
    media_req = MediaRequest(
        filename="image1.png",
        mime_type="image/png",
        bytes_data=png_data,
        content_type_ext="png",
        bind_xpath=".//a:blip",
        bind_attr="{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed",
        sha256="abc123def456"
    )
    print(f"  ✅ MediaRequest created: {media_req.filename}")

    # Create MapperResult
    print("\n3. Creating MapperResult...")
    mock_element = MockElement()
    mapper_result = MapperResult(
        element=mock_element,
        output_format=OutputFormat.NATIVE_DML,
        xml_content=pic_xml,
        media_requests=[media_req]
    )
    print("  ✅ MapperResult created with MediaRequest")

    # Create embedder with mock package writer
    print("\n4. Creating Embedder...")
    package_writer = MockPackageWriter()
    content_types = ContentTypesManager()
    embedder = DrawingMLEmbedder(
        package_writer=package_writer,
        content_types=content_types
    )
    print("  ✅ Embedder created")

    # Create mock scene
    print("\n5. Creating mock scene...")
    scene = MockScene()
    print("  ✅ Scene created")

    # Embed scene
    print("\n6. Embedding scene with MediaRequest processing...")
    try:
        result = embedder.embed_scene(scene, [mapper_result])
        print(f"  ✅ Embedding successful")
        print(f"     Processing time: {result.processing_time_ms:.2f}ms")
    except Exception as e:
        print(f"  ❌ Embedding failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Check relationships XML
    print("\n7. Checking relationships XML...")
    if result.relationships_xml:
        print(f"  ✅ Relationships XML: {len(result.relationships_xml)} bytes")
        rels_root = ET.fromstring(result.relationships_xml)
        rels = rels_root.findall(".//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
        print(f"     Relationships: {len(rels)}")
        for rel in rels:
            print(f"       {rel.get('Id')}: {rel.get('Type').split('/')[-1]} -> {rel.get('Target')}")
    else:
        print("  ❌ No relationships XML")

    # Check media files
    print("\n8. Checking media files...")
    if package_writer.files:
        print(f"  ✅ Files written: {len(package_writer.files)}")
    else:
        print("  ⚠️  No files written")

    # Check r:embed patching
    print("\n9. Checking r:embed patching...")
    slide_xml = result.slide_xml
    if 'r:embed="rId' in slide_xml:
        print("  ✅ r:embed attribute patched")
        import re
        match = re.search(r'r:embed="(rId\d+)"', slide_xml)
        if match:
            print(f"     Value: {match.group(1)}")
    else:
        print("  ❌ r:embed NOT patched")

    # Validate XML
    print("\n10. Validating slide XML...")
    try:
        parsed = ET.fromstring(slide_xml.encode('utf-8'))
        print("  ✅ Slide XML is well-formed")

        # Check blip element
        blip = parsed.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip")
        if blip is not None:
            r_embed = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
            if r_embed:
                print(f"  ✅ <a:blip r:embed=\"{r_embed}\"/>")
            else:
                print("  ❌ <a:blip> missing r:embed")
    except ET.XMLSyntaxError as e:
        print(f"  ❌ Invalid XML: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())

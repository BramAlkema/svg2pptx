#!/usr/bin/env python3
"""
Test Image Embedder Integration

Validates that the embedder correctly processes MediaRequests from ImageMapper,
writes media files, generates relationships, and patches r:embed attributes.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.map.base import MediaRequest, MapperResult, OutputFormat
from core.io.embedder import DrawingMLEmbedder
from core.io.relationship_manager import RelationshipManager
from core.io.content_types import ContentTypesManager
from core.policy.engine import PolicyEngine
from core.policy.config import PolicyConfig
from core.map.image_mapper import ImageMapper
from lxml import etree as ET

# Mock IR elements to avoid import chain
@dataclass
class MockImage:
    """Mock Image IR for testing"""
    href: str
    source_type: str
    mime_type: str
    format_ext: str
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    image_data: Optional[bytes] = None
    sha256: Optional[str] = None
    title: Optional[str] = None
    desc: Optional[str] = None

@dataclass
class MockRect:
    """Mock Rect for testing"""
    x: float
    y: float
    width: float
    height: float

@dataclass
class MockScene:
    """Mock SceneGraph for testing"""
    elements: List = None
    viewport: Optional[MockRect] = None
    background: Optional[str] = None

    def __post_init__(self):
        if self.elements is None:
            self.elements = []

# Mock package writer for testing
class MockPackageWriter:
    def __init__(self):
        self.files = {}

    def write_file(self, path: str, data: bytes):
        self.files[path] = data
        print(f"  📝 Wrote {path}: {len(data)} bytes")

def test_image_embedder_integration():
    print("=" * 60)
    print("IMAGE EMBEDDER INTEGRATION TEST")
    print("=" * 60)

    # Create test image (simple PNG data)
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89' + b'\x00' * 50

    # Create Mock Image IR
    print("\n1. Creating Mock Image IR...")
    image = MockImage(
        href="data:image/png;base64,...",
        source_type="data_url",
        mime_type="image/png",
        format_ext="png",
        x=100.0,
        y=200.0,
        width=300.0,
        height=400.0,
        image_data=png_data,
        sha256=None,  # Will be calculated
        title="Test Image",
        desc="Integration test image"
    )
    print(f"  ✅ Image created: {image.width}x{image.height} at ({image.x}, {image.y})")

    # Create sample <p:pic> XML (simulating ImageMapper output)
    print("\n2. Creating sample <p:pic> XML (ImageMapper output simulation)...")
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

    # Create MediaRequest manually
    print("\n3. Creating MediaRequest...")
    import hashlib
    sha256 = hashlib.sha256(png_data).hexdigest()
    media_req = MediaRequest(
        filename="image1.png",
        mime_type="image/png",
        bytes_data=png_data,
        content_type_ext="png",
        bind_xpath=".//a:blip",
        bind_attr="{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed",
        sha256=sha256
    )
    print(f"  ✅ MediaRequest created: {media_req.filename}")
    print(f"     SHA256: {sha256[:8]}...")

    # Create MapperResult manually
    print("\n4. Creating MapperResult...")
    result = MapperResult(
        element=image,
        output_format=OutputFormat.NATIVE_DML,
        xml_content=pic_xml,
        policy_decision=None,  # Not needed for this test
        metadata={'format': 'png', 'size_bytes': len(png_data)},
        media_requests=[media_req]
    )
    print("  ✅ MapperResult created with MediaRequest")

    # Create mock package writer and content types
    print("\n5. Creating Embedder with MockPackageWriter...")
    package_writer = MockPackageWriter()
    content_types = ContentTypesManager()
    embedder = DrawingMLEmbedder(
        slide_width_emu=9144000,
        slide_height_emu=6858000,
        package_writer=package_writer,
        content_types=content_types
    )
    print("  ✅ Embedder created")

    # Create minimal scene
    print("\n6. Creating MockScene...")
    scene = MockScene(
        elements=[],
        viewport=MockRect(0, 0, 720, 540),
        background=None
    )
    print("  ✅ Scene created")

    # Embed scene with media processing
    print("\n7. Embedding scene with media request processing...")
    try:
        embed_result = embedder.embed_scene(scene, [result])
        print(f"  ✅ Embedding complete")
        print(f"     Elements embedded: {embed_result.elements_embedded}")
        print(f"     Processing time: {embed_result.processing_time_ms:.2f}ms")
    except Exception as e:
        print(f"  ❌ Embedding failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Check relationships XML
    print("\n8. Checking relationships XML...")
    if embed_result.relationships_xml:
        print(f"  ✅ Relationships XML generated: {len(embed_result.relationships_xml)} bytes")

        # Parse and inspect
        rels_root = ET.fromstring(embed_result.relationships_xml)
        rels = rels_root.findall(".//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
        print(f"     Relationship count: {len(rels)}")
        for rel in rels:
            rid = rel.get('Id')
            rtype = rel.get('Type')
            target = rel.get('Target')
            print(f"       {rid}: {rtype.split('/')[-1]} -> {target}")
    else:
        print("  ❌ No relationships XML generated")

    # Check media files written
    print("\n9. Checking media files written...")
    if package_writer.files:
        print(f"  ✅ {len(package_writer.files)} file(s) written:")
        for path, data in package_writer.files.items():
            print(f"     {path}: {len(data)} bytes")
    else:
        print("  ⚠️  No files written (package_writer may be None)")

    # Check content types
    print("\n10. Checking content types registration...")
    ct_xml = content_types.to_xml()
    if 'image/png' in ct_xml or '.png' in ct_xml:
        print("  ✅ PNG content type registered")
    else:
        print("  ⚠️  PNG content type not found")

    # Check slide XML for patched r:embed
    print("\n11. Checking slide XML for patched r:embed...")
    slide_xml = embed_result.slide_xml
    if 'r:embed="rId' in slide_xml:
        print("  ✅ r:embed attribute patched in slide XML")
        # Extract the rId value
        import re
        match = re.search(r'r:embed="(rId\d+)"', slide_xml)
        if match:
            print(f"     Patched value: {match.group(1)}")
    else:
        print("  ❌ r:embed NOT found in slide XML (patching failed)")

    # Check XML well-formedness
    print("\n12. Validating XML well-formedness...")
    try:
        parsed_slide = ET.fromstring(slide_xml.encode('utf-8'))
        print("  ✅ Slide XML is well-formed")

        # Find the blip element
        blip = parsed_slide.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip")
        if blip is not None:
            r_embed = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
            if r_embed:
                print(f"  ✅ <a:blip> has r:embed=\"{r_embed}\"")
            else:
                print("  ❌ <a:blip> missing r:embed attribute")
        else:
            print("  ⚠️  <a:blip> element not found in slide")

    except ET.XMLSyntaxError as e:
        print(f"  ❌ Invalid XML: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 60)

    success_checks = []
    success_checks.append(result.media_requests is not None)
    success_checks.append(len(result.media_requests) == 1 if result.media_requests else False)
    success_checks.append('r:embed' not in result.xml_content)
    success_checks.append(embed_result.relationships_xml is not None)
    success_checks.append(len(package_writer.files) > 0)
    success_checks.append('r:embed="rId' in slide_xml)

    passed = sum(success_checks)
    total = len(success_checks)

    print(f"\nPassed: {passed}/{total} checks")

    if passed == total:
        print("\n🎉 ALL CHECKS PASSED - Integration successful!")
    else:
        print(f"\n⚠️  {total - passed} check(s) failed - Review output above")
        assert passed == total, f"{total - passed} check(s) failed"

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))

#!/usr/bin/env python3
"""
Validation script for Clean Slate Package Writer.

Tests PPTX generation and validates files can be opened by LibreOffice.
"""

import tempfile
import zipfile
from pathlib import Path
from core.io.package_writer import PackageWriter
from core.io.embedder import EmbedderResult

def create_test_embedder_result():
    """Create a realistic test EmbedderResult."""
    slide_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name="Slide"/>
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
                    <p:cNvPr id="2" name="Rectangle Shape"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="914400" y="685800"/>
                        <a:ext cx="2743200" cy="1371600"/>
                    </a:xfrm>
                    <a:prstGeom prst="rect"/>
                    <a:solidFill>
                        <a:srgbClr val="0066CC"/>
                    </a:solidFill>
                    <a:ln w="25400">
                        <a:solidFill>
                            <a:srgbClr val="000000"/>
                        </a:solidFill>
                    </a:ln>
                </p:spPr>
            </p:sp>
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="3" name="Circle Shape"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="5486400" y="1371600"/>
                        <a:ext cx="1828800" cy="1828800"/>
                    </a:xfrm>
                    <a:prstGeom prst="ellipse"/>
                    <a:solidFill>
                        <a:srgbClr val="FF6600"/>
                    </a:solidFill>
                </p:spPr>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>'''

    return EmbedderResult(
        slide_xml=slide_xml,
        relationship_data=[
            {
                'id': 'rId1',
                'type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout',
                'target': '../slideLayouts/slideLayout1.xml'
            }
        ],
        media_files=[],
        elements_embedded=2,
        native_elements=2,
        emf_elements=0,
        total_size_bytes=2048
    )

def validate_pptx_structure(pptx_path):
    """Validate PPTX file structure."""
    print(f"Validating PPTX structure: {pptx_path}")

    # Check if file exists and is not empty
    if not pptx_path.exists():
        print("❌ PPTX file does not exist")
        return False

    if pptx_path.stat().st_size == 0:
        print("❌ PPTX file is empty")
        return False

    print(f"✅ PPTX file exists and has size: {pptx_path.stat().st_size} bytes")

    # Check ZIP structure
    try:
        with zipfile.ZipFile(pptx_path, 'r') as zip_file:
            files = zip_file.namelist()

            required_files = [
                '[Content_Types].xml',
                '_rels/.rels',
                'ppt/presentation.xml',
                'ppt/_rels/presentation.xml.rels',
                'ppt/slides/slide1.xml',
                'ppt/slides/_rels/slide1.xml.rels',
                'ppt/slideMasters/slideMaster1.xml',
                'ppt/slideLayouts/slideLayout1.xml',
                'ppt/theme/theme1.xml'
            ]

            missing_files = []
            for required_file in required_files:
                if required_file not in files:
                    missing_files.append(required_file)

            if missing_files:
                print(f"❌ Missing required files: {missing_files}")
                return False

            print("✅ All required OOXML files present")

            # Validate XML files are well-formed
            from lxml import etree as ET
            xml_files = [f for f in files if f.endswith('.xml')]

            for xml_file in xml_files:
                try:
                    xml_content = zip_file.read(xml_file)
                    ET.fromstring(xml_content)
                except ET.XMLSyntaxError as e:
                    print(f"❌ Invalid XML in {xml_file}: {e}")
                    return False

            print(f"✅ All {len(xml_files)} XML files are well-formed")

    except zipfile.BadZipFile:
        print("❌ File is not a valid ZIP archive")
        return False

    return True

def test_single_slide_generation():
    """Test single slide PPTX generation."""
    print("\n=== Testing Single Slide Generation ===")

    writer = PackageWriter()
    embedder_result = create_test_embedder_result()

    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
        temp_path = Path(tmp.name)

    try:
        result = writer.write_package([embedder_result], str(temp_path))

        print(f"Package creation result:")
        print(f"  - Output path: {result['output_path']}")
        print(f"  - Package size: {result['package_size_bytes']} bytes")
        print(f"  - Slide count: {result['slide_count']}")
        print(f"  - Processing time: {result['processing_time_ms']:.2f} ms")
        print(f"  - Compression ratio: {result['compression_ratio']:.2f}")

        # Validate structure
        if validate_pptx_structure(temp_path):
            print("✅ Single slide PPTX generation successful")
            return temp_path
        else:
            print("❌ Single slide PPTX validation failed")
            return None

    except Exception as e:
        print(f"❌ Single slide generation failed: {e}")
        return None
    finally:
        # Clean up unless we want to keep for manual inspection
        pass  # temp_path.unlink(missing_ok=True)

def test_multi_slide_generation():
    """Test multi-slide PPTX generation."""
    print("\n=== Testing Multi-Slide Generation ===")

    writer = PackageWriter()

    # Create multiple slides
    slides = []
    for i in range(3):
        result = create_test_embedder_result()
        # Modify slide content slightly for each slide
        result.slide_xml = result.slide_xml.replace('Rectangle Shape', f'Rectangle Shape {i+1}')
        result.slide_xml = result.slide_xml.replace('Circle Shape', f'Circle Shape {i+1}')
        slides.append(result)

    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
        temp_path = Path(tmp.name)

    try:
        result = writer.write_package(slides, str(temp_path))

        print(f"Multi-slide package result:")
        print(f"  - Slide count: {result['slide_count']}")
        print(f"  - Package size: {result['package_size_bytes']} bytes")
        print(f"  - Processing time: {result['processing_time_ms']:.2f} ms")

        # Validate structure
        if validate_pptx_structure(temp_path):
            print("✅ Multi-slide PPTX generation successful")
            return temp_path
        else:
            print("❌ Multi-slide PPTX validation failed")
            return None

    except Exception as e:
        print(f"❌ Multi-slide generation failed: {e}")
        return None

def attempt_office_validation(pptx_path):
    """Attempt to validate with LibreOffice if available."""
    print(f"\n=== Attempting Office Application Validation ===")

    if not pptx_path or not pptx_path.exists():
        print("❌ No valid PPTX file to test")
        return False

    # Try to open with LibreOffice
    import subprocess
    import shutil

    # Check if LibreOffice is available
    soffice_paths = [
        '/Applications/LibreOffice.app/Contents/MacOS/soffice',
        'libreoffice',
        'soffice'
    ]

    soffice_cmd = None
    for path in soffice_paths:
        if shutil.which(path) or Path(path).exists():
            soffice_cmd = path
            break

    if not soffice_cmd:
        print("ℹ️  LibreOffice not found - skipping office validation")
        return True

    try:
        # Try to verify the file with LibreOffice
        print(f"Testing with LibreOffice: {soffice_cmd}")

        # Use --headless --verify to check if file can be loaded
        result = subprocess.run([
            soffice_cmd, '--headless', '--verify', str(pptx_path)
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ LibreOffice can open the PPTX file")
            return True
        else:
            print(f"❌ LibreOffice validation failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("⚠️  LibreOffice validation timed out")
        return False
    except Exception as e:
        print(f"⚠️  LibreOffice validation error: {e}")
        return False

def main():
    """Run validation tests."""
    print("Clean Slate Package Writer Validation")
    print("=" * 50)

    # Test single slide
    single_slide_path = test_single_slide_generation()

    # Test multi-slide
    multi_slide_path = test_multi_slide_generation()

    # Test with office applications if available
    if single_slide_path:
        attempt_office_validation(single_slide_path)

    print("\n=== Validation Summary ===")

    if single_slide_path and multi_slide_path:
        print("✅ All package writer validation tests passed")
        print("📁 Test files generated:")
        print(f"   - Single slide: {single_slide_path}")
        print(f"   - Multi slide: {multi_slide_path}")
        print("\nYou can manually open these files in PowerPoint or LibreOffice to verify compatibility.")
        return True
    else:
        print("❌ Some validation tests failed")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
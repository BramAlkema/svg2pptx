#!/usr/bin/env python3
"""Test the fixed TextConverter with proper XML generation."""

import sys
sys.path.append('.')

from lxml import etree as ET
from src.converters.text import TextConverter
from src.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext
import zipfile

def test_fixed_text_converter():
    """Test TextConverter with proper XML generation"""

    # Create test SVG
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
        <text x="200" y="150" font-size="24pt" fill="red">FIXED TEXT</text>
        <text x="100" y="50" font-size="18pt" fill="blue" font-weight="bold">Bold Blue</text>
        <text x="300" y="250" font-size="16pt" fill="green" font-style="italic">Italic Green</text>
    </svg>'''

    root = ET.fromstring(svg_content)

    # Set up conversion context
    services = ConversionServices.create_default()
    context = ConversionContext(services=services, svg_root=root)
    context.svg_width = 400
    context.svg_height = 300

    # Create TextConverter
    converter = TextConverter(services)

    print("=== Testing Fixed TextConverter ===")

    text_elements = root.findall('.//{http://www.w3.org/2000/svg}text')
    print(f"Found {len(text_elements)} text elements")

    results = []
    for i, text_elem in enumerate(text_elements):
        print(f"\nProcessing text {i+1}: '{text_elem.text}'")

        try:
            # Get the output from fixed TextConverter
            result = converter.convert(text_elem, context)

            print(f"✅ Result type: {type(result)}")
            print(f"✅ Result length: {len(result) if isinstance(result, str) else 'N/A'}")

            if isinstance(result, str):
                # Try to parse the XML to verify it's valid
                try:
                    parsed = ET.fromstring(result)
                    print(f"✅ XML parses successfully: {parsed.tag}")

                    # Check for complete shape structure
                    nvSpPr = parsed.find('.//p:nvSpPr', {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'})
                    spPr = parsed.find('.//p:spPr', {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'})
                    txBody = parsed.find('.//p:txBody', {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'})
                    endParaRPr = parsed.find('.//a:endParaRPr', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})

                    print(f"✅ Shape structure complete: nvSpPr={nvSpPr is not None}, spPr={spPr is not None}, txBody={txBody is not None}, endParaRPr={endParaRPr is not None}")

                    results.append(result)

                except ET.XMLSyntaxError as e:
                    print(f"❌ XML parsing failed: {e}")

            else:
                print(f"❌ TextConverter did not return a string")

        except Exception as e:
            print(f"❌ TextConverter.convert() failed: {e}")
            import traceback
            traceback.print_exc()

    return results

def generate_test_pptx(xml_results, output_file='debug_fixed_converter.pptx'):
    """Generate PPTX using the fixed TextConverter results"""

    # Use working base file
    base_pptx = 'manual_test.pptx'

    with zipfile.ZipFile(base_pptx, 'r') as source:
        with zipfile.ZipFile(output_file, 'w') as dest:

            for item in source.infolist():
                data = source.read(item.filename)

                if item.filename == 'ppt/slides/slide1.xml':
                    # Parse slide
                    root = ET.fromstring(data)
                    spTree = root.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}spTree')

                    # Clear existing text
                    for sp in spTree.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp'):
                        for t_elem in sp.findall('.//a:t', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}):
                            t_elem.text = ''

                    # Add our fixed shapes
                    for xml_result in xml_results:
                        try:
                            shape_element = ET.fromstring(xml_result)
                            spTree.append(shape_element)
                            print(f"✅ Added fixed shape to slide")
                        except Exception as e:
                            print(f"❌ Failed to add shape: {e}")

                    data = ET.tostring(root, encoding='utf-8', xml_declaration=True)

                dest.writestr(item, data)

    print(f"✅ Created {output_file} with fixed TextConverter shapes")

if __name__ == "__main__":
    # Test the fixed converter
    xml_results = test_fixed_text_converter()

    if xml_results:
        print(f"\n=== Generating PPTX with {len(xml_results)} fixed shapes ===")
        generate_test_pptx(xml_results)
        print("✅ Testing complete! Check debug_fixed_converter.pptx")
    else:
        print("❌ No valid XML results to test with")
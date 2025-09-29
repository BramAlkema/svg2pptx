#!/usr/bin/env python3
"""
Debug text XML generation to identify PPTX corruption issues.
"""

import sys
sys.path.append('.')

from lxml import etree as ET
from src.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext
from src.converters.text import TextConverter

def debug_text_xml():
    """Debug the XML generation for the basic shapes text element."""

    # Create the text element from basic_shapes.svg
    svg_text = '''<text x="200" y="200" text-anchor="middle" font-family="Arial" font-size="18" fill="darkblue" xmlns="http://www.w3.org/2000/svg">Basic Shapes Test</text>'''

    text_element = ET.fromstring(svg_text)

    # Create services and context
    services = ConversionServices.create_default()

    # Create minimal SVG root for context
    svg_root = ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"></svg>')
    context = ConversionContext(services=services, svg_root=svg_root)

    # Create text converter
    text_converter = TextConverter(services=services)

    try:
        # Generate the XML
        result_xml = text_converter.convert(text_element, context)

        print("=== Generated Text XML ===")
        print(result_xml)
        print("\n=== XML Validation ===")

        # Try to parse the generated XML to check for malformation
        try:
            parsed = ET.fromstring(f"<root>{result_xml}</root>")
            print("✅ XML is well-formed")

            # Check for specific issues
            rpr_elements = parsed.xpath('.//a:rPr', namespaces={'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
            if rpr_elements:
                rpr = rpr_elements[0]
                print(f"📝 Font size (sz): {rpr.get('sz', 'MISSING')}")
                print(f"📝 Language (lang): {rpr.get('lang', 'MISSING')}")
                print(f"📝 Bold (b): {rpr.get('b', 'MISSING')}")
                print(f"📝 Italic (i): {rpr.get('i', 'MISSING')}")

                # Check for font family
                latin_elements = rpr.xpath('.//a:latin', namespaces={'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
                if latin_elements:
                    print(f"📝 Font family: {latin_elements[0].get('typeface', 'MISSING')}")
                else:
                    print("❌ Missing font family element")
            else:
                print("❌ Missing rPr element")

        except ET.XMLSyntaxError as e:
            print(f"❌ XML Syntax Error: {e}")

    except Exception as e:
        print(f"❌ Error generating XML: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_text_xml()
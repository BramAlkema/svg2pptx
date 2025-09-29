#!/usr/bin/env python3
"""Debug the namespace issue in TextConverter output."""

import sys
sys.path.append('.')

from lxml import etree as ET
from src.converters.text import TextConverter
from core.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext

def debug_text_converter_output():
    """Debug what the TextConverter actually outputs"""

    # Create test SVG
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
        <text x="200" y="150" font-size="24pt" fill="red">DEBUG TEXT</text>
    </svg>'''

    root = ET.fromstring(svg_content)
    text_element = root.find('.//{http://www.w3.org/2000/svg}text')

    # Set up conversion context
    services = ConversionServices.create_default()
    context = ConversionContext(services=services, svg_root=root)
    context.svg_width = 400
    context.svg_height = 300

    # Create TextConverter
    converter = TextConverter(services)

    print("=== TextConverter Output Analysis ===")

    try:
        # Get the raw output
        result = converter.convert(text_element, context)

        print(f"Output type: {type(result)}")
        print(f"Output length: {len(result) if isinstance(result, str) else 'N/A'}")

        if isinstance(result, str):
            print(f"\n=== Raw XML Output ===")
            print(result[:500] + "..." if len(result) > 500 else result)

            print(f"\n=== Namespace Analysis ===")
            # Check what namespaces are declared
            lines = result.split('\n')
            for i, line in enumerate(lines[:10]):  # First 10 lines
                if 'xmlns' in line or 'p:' in line or 'a:' in line:
                    print(f"Line {i+1}: {line.strip()}")

            print(f"\n=== Parsing Test ===")
            try:
                # Try to parse the XML
                parsed = ET.fromstring(result)
                print(f"✅ XML parses successfully")
                print(f"Root tag: {parsed.tag}")
                print(f"Root attributes: {parsed.attrib}")

                # Check for namespace declarations
                if hasattr(parsed, 'nsmap'):
                    print(f"Namespace map: {parsed.nsmap}")

            except ET.XMLSyntaxError as e:
                print(f"❌ XML parsing failed: {e}")

                # Try to identify the issue
                print(f"\n=== Attempting to Fix Namespace Issue ===")

                # Common namespace declarations
                namespace_declarations = '''xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'''

                # Try adding namespaces to the root element
                if result.startswith('<p:sp>'):
                    fixed_result = result.replace('<p:sp>', f'<p:sp {namespace_declarations}>')
                    print(f"Attempting fix by adding namespaces to <p:sp>")

                    try:
                        fixed_parsed = ET.fromstring(fixed_result)
                        print(f"✅ Fixed XML parses successfully!")
                        print(f"Fixed root tag: {fixed_parsed.tag}")
                    except ET.XMLSyntaxError as fix_error:
                        print(f"❌ Fix failed: {fix_error}")

        else:
            print("❌ TextConverter did not return a string")

    except Exception as e:
        print(f"❌ TextConverter.convert() failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_text_converter_output()
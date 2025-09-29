#!/usr/bin/env python3
"""
Debug PPTX Content

Debug tool to examine the actual content being generated in the PPTX file
and understand why LibreOffice screenshot is mostly empty.
"""

import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

def debug_pptx_content(pptx_file):
    """Debug the content of a PPTX file."""
    print(f"🔍 Debugging PPTX content: {pptx_file}")
    print("=" * 60)

    try:
        with zipfile.ZipFile(pptx_file, 'r') as zip_file:
            # Read slide content
            slide_xml = zip_file.read('ppt/slides/slide1.xml').decode('utf-8')

            print(f"📊 Slide XML size: {len(slide_xml):,} bytes")

            # Parse XML
            root = ET.fromstring(slide_xml)

            # Count different types of elements
            namespaces = {
                'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
                'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
            }

            shapes = root.findall('.//p:sp', namespaces)
            print(f"📐 Total shapes found: {len(shapes)}")

            # Analyze each shape
            for i, shape in enumerate(shapes):
                print(f"\n🔹 Shape {i+1}:")

                # Get name
                name_elem = shape.find('.//p:cNvPr', namespaces)
                name = name_elem.get('name') if name_elem is not None else 'Unknown'
                print(f"   Name: {name}")

                # Check for geometry
                geom = shape.find('.//a:prstGeom', namespaces)
                custom_geom = shape.find('.//a:custGeom', namespaces)

                if geom is not None:
                    prst = geom.get('prst')
                    print(f"   Geometry: Preset '{prst}'")
                elif custom_geom is not None:
                    paths = custom_geom.findall('.//a:path', namespaces)
                    print(f"   Geometry: Custom with {len(paths)} paths")

                    # Show path details
                    for j, path in enumerate(paths):
                        path_cmds = path.findall('.//a:*', namespaces)
                        print(f"     Path {j+1}: {len(path_cmds)} commands")

                        # Show first few commands
                        for k, cmd in enumerate(path_cmds[:3]):
                            cmd_name = cmd.tag.split('}')[-1] if '}' in cmd.tag else cmd.tag
                            print(f"       {cmd_name}: {cmd.attrib}")

                        if len(path_cmds) > 3:
                            print(f"       ... and {len(path_cmds) - 3} more commands")
                else:
                    print("   Geometry: None found")

                # Check for fill
                fills = shape.findall('.//a:solidFill', namespaces)
                if fills:
                    for fill in fills:
                        color = fill.find('.//a:srgbClr', namespaces)
                        if color is not None:
                            print(f"   Fill: #{color.get('val')}")
                        else:
                            print("   Fill: Solid (color not found)")
                else:
                    print("   Fill: None")

                # Check for stroke
                strokes = shape.findall('.//a:ln', namespaces)
                if strokes:
                    print(f"   Stroke: Found {len(strokes)} line definitions")
                else:
                    print("   Stroke: None")

                # Check positioning
                xfrm = shape.find('.//a:xfrm', namespaces)
                if xfrm is not None:
                    off = xfrm.find('a:off', namespaces)
                    ext = xfrm.find('a:ext', namespaces)
                    if off is not None and ext is not None:
                        x = int(off.get('x', 0)) / 914400  # Convert EMU to inches
                        y = int(off.get('y', 0)) / 914400
                        w = int(ext.get('cx', 0)) / 914400
                        h = int(ext.get('cy', 0)) / 914400
                        print(f"   Position: ({x:.2f}, {y:.2f}) inches")
                        print(f"   Size: {w:.2f} × {h:.2f} inches")
                    else:
                        print("   Position: Transform data incomplete")
                else:
                    print("   Position: No transform found")

            # Look for text content
            text_runs = root.findall('.//a:t', namespaces)
            print(f"\n📝 Text elements found: {len(text_runs)}")
            for i, text in enumerate(text_runs):
                content = text.text if text.text else "[empty]"
                print(f"   Text {i+1}: '{content}'")

            # Check for any custom geometry paths
            all_paths = root.findall('.//a:path', namespaces)
            print(f"\n🛤️  Custom geometry paths: {len(all_paths)}")

            if all_paths:
                print("   Path commands found:")
                for i, path in enumerate(all_paths):
                    commands = path.findall('.//a:*', namespaces)
                    cmd_types = [cmd.tag.split('}')[-1] for cmd in commands]
                    print(f"     Path {i+1}: {', '.join(cmd_types)}")

            return True

    except Exception as e:
        print(f"❌ Error debugging PPTX: {e}")
        return False

def main():
    """Debug PPTX content."""
    pptx_file = Path(__file__).parent / "debug_attrs_output.pptx"

    if not pptx_file.exists():
        print(f"❌ PPTX file not found: {pptx_file}")
        return False

    return debug_pptx_content(pptx_file)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
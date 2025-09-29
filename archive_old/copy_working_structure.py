#!/usr/bin/env python3
"""Copy the entire working PPTX structure and only modify the text content."""

import zipfile
from lxml import etree as ET

def create_working_pptx():
    """Create a PPTX by copying the working manual file and modifying only the text"""

    # Copy everything from the working manual file
    with zipfile.ZipFile('manual_test.pptx', 'r') as source:
        with zipfile.ZipFile('debug_copied_structure.pptx', 'w') as dest:

            for item in source.infolist():
                data = source.read(item.filename)

                # Only modify the slide with text
                if item.filename == 'ppt/slides/slide1.xml':
                    # Parse the XML
                    root = ET.fromstring(data)

                    # Find the text element and modify it
                    for t_elem in root.xpath('.//a:t', namespaces={'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}):
                        if t_elem.text == 'Big Red Text':
                            t_elem.text = 'MODIFIED TEXT'
                            print(f"✅ Changed text from 'Big Red Text' to 'MODIFIED TEXT'")

                    # Write the modified XML
                    data = ET.tostring(root, encoding='utf-8', xml_declaration=True)

                # Copy file (modified or original)
                dest.writestr(item, data)

if __name__ == "__main__":
    create_working_pptx()
    print("✅ Created debug_copied_structure.pptx by copying working structure and modifying only text")
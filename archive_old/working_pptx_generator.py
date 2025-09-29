#!/usr/bin/env python3
"""Generate PPTX files using the working manual file as foundation."""

import zipfile
import sys
from lxml import etree as ET

sys.path.append('.')
from core.units import unit

class WorkingPPTXGenerator:
    def __init__(self, base_file='manual_test.pptx'):
        self.base_file = base_file
        self.text_elements = []

    def add_text(self, text, x, y, font_size=24, color="FF0000"):
        """Add a text element to be inserted"""
        self.text_elements.append({
            'text': text,
            'x': x,
            'y': y,
            'font_size': font_size,
            'color': color
        })

    def _create_text_shape(self, text_data, shape_id):
        """Create a text shape XML element using the working pattern"""

        # Calculate EMU coordinates
        slide_width_emu = unit("10in").to_emu()
        slide_height_emu = unit("7.5in").to_emu()

        # Convert from SVG coordinates (assuming 400x300 viewbox)
        x_emu = int((text_data['x'] / 400) * slide_width_emu)
        y_emu = int((text_data['y'] / 300) * slide_height_emu)

        # Text box dimensions - make them generous to fit content
        # Estimate width based on text length (rough approximation)
        char_width_pt = text_data.get('font_size', 24) * 0.6  # Rough character width
        text_width_pt = len(text_data['text']) * char_width_pt / 72  # Convert to inches
        text_height_pt = text_data.get('font_size', 24) * 1.5 / 72  # Line height in inches

        # Make bounding box at least this big, with padding
        min_width = max(text_width_pt + 1, 2)  # At least 2 inches wide
        min_height = max(text_height_pt + 0.5, 1)  # At least 1 inch tall

        width_emu = unit(f"{min_width}in").to_emu()
        height_emu = unit(f"{min_height}in").to_emu()

        # Center text box on coordinates
        x_emu -= width_emu // 2
        y_emu -= height_emu // 2

        # Create the shape element using the exact working pattern
        shape_xml = f'''<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="Text {shape_id}">
                    <a:extLst>
                        <a:ext uri="{{FF2B5EF4-FFF2-40B4-BE49-F238E27FC236}}">
                            <a16:creationId xmlns:a16="http://schemas.microsoft.com/office/drawing/2014/main" id="{{7521BD15-4617-B93B-178A-EDC035992741}}"/>
                        </a:ext>
                    </a:extLst>
                </p:cNvPr>
                <p:cNvSpPr>
                    <a:spLocks noGrp="1"/>
                </p:cNvSpPr>
                <p:nvPr>
                    <p:ph type="obj"/>
                </p:nvPr>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{x_emu}" y="{y_emu}"/>
                    <a:ext cx="{width_emu}" cy="{height_emu}"/>
                </a:xfrm>
            </p:spPr>
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:r>
                        <a:rPr lang="en-US" dirty="0" sz="{int(text_data['font_size'] * 100)}">
                            <a:solidFill>
                                <a:srgbClr val="{text_data['color']}"/>
                            </a:solidFill>
                        </a:rPr>
                        <a:t>{self._escape_xml(text_data['text'])}</a:t>
                    </a:r>
                </a:p>
            </p:txBody>
        </p:sp>'''

        return ET.fromstring(shape_xml)

    def _escape_xml(self, text):
        """Escape XML special characters"""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))

    def generate(self, output_file):
        """Generate the PPTX file"""

        with zipfile.ZipFile(self.base_file, 'r') as source:
            with zipfile.ZipFile(output_file, 'w') as dest:

                for item in source.infolist():
                    data = source.read(item.filename)

                    # Modify the slide to add our text elements
                    if item.filename == 'ppt/slides/slide1.xml':
                        # Parse the slide XML
                        root = ET.fromstring(data)

                        # Find the spTree element
                        spTree = root.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}spTree')

                        # Remove existing text shapes (keep the title and subtitle structure but clear content)
                        for sp in spTree.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp'):
                            # Clear existing text content but keep structure
                            for t_elem in sp.findall('.//a:t', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}):
                                t_elem.text = ''

                        # Add our new text elements
                        shape_id = 10  # Start from ID 10 to avoid conflicts
                        for text_data in self.text_elements:
                            new_shape = self._create_text_shape(text_data, shape_id)
                            spTree.append(new_shape)
                            shape_id += 1
                            print(f"✅ Added text: '{text_data['text']}' at ({text_data['x']}, {text_data['y']})")

                        # Convert back to XML
                        data = ET.tostring(root, encoding='utf-8', xml_declaration=True)

                    # Copy file (modified or original)
                    dest.writestr(item, data)

if __name__ == "__main__":
    # Test the generator
    generator = WorkingPPTXGenerator()

    # Add some test text elements
    generator.add_text("HELLO WORLD", 200, 100, color="FF0000")
    generator.add_text("Second Text", 200, 200, color="00FF00")

    # Generate the PPTX
    generator.generate("debug_working_generator.pptx")
    print("✅ Created debug_working_generator.pptx using working file as foundation")
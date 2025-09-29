#!/usr/bin/env python3
"""Clean hybrid approach: Extract properties from TextConverter, generate clean XML."""

import sys
import zipfile
import re
sys.path.append('.')

from lxml import etree as ET
from src.converters.text import TextConverter
from src.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext

class CleanHybridConverter:
    """Extract advanced text properties, generate clean working XML."""

    def __init__(self, base_pptx='manual_test.pptx'):
        self.base_pptx = base_pptx
        self.services = ConversionServices.create_default()
        self.text_converter = TextConverter(self.services)
        self.text_elements = []

    def process_svg_text(self, svg_file):
        """Process SVG text using TextConverter, extract properties only"""

        with open(svg_file, 'r') as f:
            svg_content = f.read()

        root = ET.fromstring(svg_content)
        context = ConversionContext(services=self.services, svg_root=root)

        viewbox = root.get('viewBox', '0 0 400 300')
        _, _, svg_width, svg_height = map(float, viewbox.split())
        context.svg_width = svg_width
        context.svg_height = svg_height

        for text_elem in root.findall('.//{http://www.w3.org/2000/svg}text'):
            print(f"Processing text: '{text_elem.text}'")

            try:
                # Use TextConverter to get advanced processing
                drawingml_xml = self.text_converter.convert(text_elem, context)
                if drawingml_xml and isinstance(drawingml_xml, str):
                    # Extract properties without parsing complex XML
                    self._extract_properties_from_xml_string(drawingml_xml, text_elem)
                else:
                    self._extract_basic_properties(text_elem)
            except Exception as e:
                print(f"  ❌ TextConverter failed: {e}")
                self._extract_basic_properties(text_elem)

    def _extract_properties_from_xml_string(self, xml_string, original_element):
        """Extract properties using regex instead of XML parsing"""
        try:
            # Extract position using regex
            x_match = re.search(r'<a:off x="(\d+)"', xml_string)
            y_match = re.search(r'<a:off x="\d+" y="(\d+)"', xml_string)
            x_emu = int(x_match.group(1)) if x_match else 4572000
            y_emu = int(y_match.group(1)) if y_match else 3429000

            # Extract dimensions
            width_match = re.search(r'<a:ext cx="(\d+)"', xml_string)
            height_match = re.search(r'<a:ext cx="\d+" cy="(\d+)"', xml_string)
            width_emu = int(width_match.group(1)) if width_match else 2286000
            height_emu = int(height_match.group(1)) if height_match else 914400

            # Extract font size
            font_size_match = re.search(r'sz="(\d+)"', xml_string)
            font_size_drawingml = int(font_size_match.group(1)) if font_size_match else 4800

            # Extract color
            color_match = re.search(r'<a:srgbClr val="([A-Fa-f0-9]{6})"', xml_string)
            color = color_match.group(1) if color_match else 'FF0000'

            # Extract text content
            text_match = re.search(r'<a:t>([^<]+)</a:t>', xml_string)
            text_content = text_match.group(1) if text_match else (original_element.text or 'Text')

            self.text_elements.append({
                'text': text_content,
                'x_emu': x_emu,
                'y_emu': y_emu,
                'width_emu': width_emu,
                'height_emu': height_emu,
                'font_size_drawingml': font_size_drawingml,
                'color': color,
                'source': 'advanced'
            })

            print(f"  ✅ Extracted advanced: '{text_content}' at EMU({x_emu}, {y_emu}) size={font_size_drawingml}")

        except Exception as e:
            print(f"  ❌ Regex extraction failed: {e}")
            self._extract_basic_properties(original_element)

    def _extract_basic_properties(self, text_elem):
        """Fallback to basic SVG properties"""
        x = float(text_elem.get('x', 200))
        y = float(text_elem.get('y', 150))
        text_content = text_elem.text or 'Text'

        # Convert SVG coordinates to EMU (rough conversion)
        x_emu = int((x / 400) * 9144000)
        y_emu = int((y / 300) * 6858000)

        self.text_elements.append({
            'text': text_content,
            'x_emu': x_emu,
            'y_emu': y_emu,
            'width_emu': 2286000,
            'height_emu': 914400,
            'font_size_drawingml': 4800,  # 24pt
            'color': 'FF0000',
            'source': 'basic'
        })

        print(f"  ✅ Extracted basic: '{text_content}' at EMU({x_emu}, {y_emu})")

    def generate_pptx(self, output_file):
        """Generate PPTX using clean XML generation"""

        with zipfile.ZipFile(self.base_pptx, 'r') as source:
            with zipfile.ZipFile(output_file, 'w') as dest:

                for item in source.infolist():
                    data = source.read(item.filename)

                    if item.filename == 'ppt/slides/slide1.xml':
                        # Parse slide
                        root = ET.fromstring(data)
                        spTree = root.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}spTree')

                        # Clear existing text content
                        for sp in spTree.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp'):
                            for t_elem in sp.findall('.//a:t', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}):
                                t_elem.text = ''

                        # Add text elements using clean XML generation
                        shape_id = 10
                        for text_data in self.text_elements:
                            self._add_clean_text_shape(spTree, text_data, shape_id)
                            shape_id += 1

                        data = ET.tostring(root, encoding='utf-8', xml_declaration=True)

                    dest.writestr(item, data)

    def _add_clean_text_shape(self, spTree, text_data, shape_id):
        """Add text shape using clean XML generation (no namespace issues)"""

        # Create shape element directly without string parsing
        p_ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Create the shape element
        sp = ET.Element(f"{p_ns}sp")

        # Non-visual properties
        nvSpPr = ET.SubElement(sp, f"{p_ns}nvSpPr")
        cNvPr = ET.SubElement(nvSpPr, f"{p_ns}cNvPr")
        cNvPr.set("id", str(shape_id))
        cNvPr.set("name", f"Text {shape_id}")

        cNvSpPr = ET.SubElement(nvSpPr, f"{p_ns}cNvSpPr")
        spLocks = ET.SubElement(cNvSpPr, f"{a_ns}spLocks")
        spLocks.set("noGrp", "1")

        nvPr = ET.SubElement(nvSpPr, f"{p_ns}nvPr")
        ph = ET.SubElement(nvPr, f"{p_ns}ph")
        ph.set("type", "obj")

        # Shape properties
        spPr = ET.SubElement(sp, f"{p_ns}spPr")
        xfrm = ET.SubElement(spPr, f"{a_ns}xfrm")
        off = ET.SubElement(xfrm, f"{a_ns}off")
        off.set("x", str(text_data['x_emu']))
        off.set("y", str(text_data['y_emu']))
        ext = ET.SubElement(xfrm, f"{a_ns}ext")
        ext.set("cx", str(text_data['width_emu']))
        ext.set("cy", str(text_data['height_emu']))

        # Text body
        txBody = ET.SubElement(sp, f"{p_ns}txBody")
        ET.SubElement(txBody, f"{a_ns}bodyPr")
        ET.SubElement(txBody, f"{a_ns}lstStyle")

        # Paragraph
        p = ET.SubElement(txBody, f"{a_ns}p")

        # Run
        r = ET.SubElement(p, f"{a_ns}r")
        rPr = ET.SubElement(r, f"{a_ns}rPr")
        rPr.set("lang", "en-US")
        rPr.set("dirty", "0")
        rPr.set("sz", str(text_data['font_size_drawingml']))

        # Color
        solidFill = ET.SubElement(rPr, f"{a_ns}solidFill")
        srgbClr = ET.SubElement(solidFill, f"{a_ns}srgbClr")
        srgbClr.set("val", text_data['color'])

        # Text content
        t = ET.SubElement(r, f"{a_ns}t")
        t.text = text_data['text']

        # Add to slide
        spTree.append(sp)
        print(f"  ✅ Added clean {text_data['source']} text: '{text_data['text']}'")

if __name__ == "__main__":
    # Test the clean hybrid converter
    converter = CleanHybridConverter()
    converter.process_svg_text('debug_simple_visible_test.svg')
    converter.generate_pptx('debug_clean_hybrid.pptx')
    print("✅ Created debug_clean_hybrid.pptx with clean XML generation!")
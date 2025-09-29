#!/usr/bin/env python3
"""Hybrid approach: Use advanced TextConverter logic with working PPTX generation."""

import sys
import zipfile
sys.path.append('.')

from lxml import etree as ET
from src.converters.text import TextConverter
from core.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext

class HybridTextConverter:
    """Combines advanced TextConverter features with working PPTX generation."""

    def __init__(self, base_pptx='manual_test.pptx'):
        self.base_pptx = base_pptx
        self.services = ConversionServices.create_default()
        self.text_converter = TextConverter(self.services)
        self.text_elements = []

    def process_svg_text(self, svg_file):
        """Process SVG text elements using the advanced TextConverter"""

        # Parse SVG
        with open(svg_file, 'r') as f:
            svg_content = f.read()

        root = ET.fromstring(svg_content)
        context = ConversionContext(services=self.services, svg_root=root)

        # Extract viewBox
        viewbox = root.get('viewBox', '0 0 400 300')
        _, _, svg_width, svg_height = map(float, viewbox.split())
        context.svg_width = svg_width
        context.svg_height = svg_height

        print(f"Processing SVG: {svg_width} x {svg_height}")

        # Process each text element
        for text_elem in root.findall('.//{http://www.w3.org/2000/svg}text'):
            print(f"Processing text: '{text_elem.text}'")

            # Use the advanced TextConverter to generate DrawingML
            try:
                drawingml_xml = self.text_converter.convert(text_elem, context)
                if drawingml_xml and isinstance(drawingml_xml, str):
                    # Parse the generated XML to extract key information
                    self._extract_text_info(drawingml_xml, text_elem)
                else:
                    print(f"  ⚠️ TextConverter returned: {type(drawingml_xml)}")
            except Exception as e:
                print(f"  ❌ TextConverter failed: {e}")
                # Fallback to basic processing
                self._extract_basic_text_info(text_elem)

    def _extract_text_info(self, drawingml_xml, original_element):
        """Extract information from TextConverter's DrawingML output"""
        try:
            # Fix namespace issue in DrawingML XML
            if drawingml_xml.startswith('<p:sp>'):
                namespace_declarations = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
                drawingml_xml = drawingml_xml.replace('<p:sp>', f'<p:sp {namespace_declarations}>')

            # Parse the fixed DrawingML XML
            shape_root = ET.fromstring(drawingml_xml)

            # Extract position from <a:off>
            off_elem = shape_root.find('.//a:off', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
            if off_elem is not None:
                x_emu = int(off_elem.get('x', 0))
                y_emu = int(off_elem.get('y', 0))
            else:
                x_emu, y_emu = 0, 0

            # Extract dimensions from <a:ext>
            ext_elem = shape_root.find('.//a:ext', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
            if ext_elem is not None:
                width_emu = int(ext_elem.get('cx', 914400))
                height_emu = int(ext_elem.get('cy', 914400))
            else:
                width_emu, height_emu = 914400, 914400

            # Extract text content from <a:t>
            t_elem = shape_root.find('.//a:t', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
            text_content = t_elem.text if t_elem is not None else (original_element.text or '')

            # Extract font size from <a:rPr sz="">
            rpr_elem = shape_root.find('.//a:rPr', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
            font_size_drawingml = 2400  # Default
            if rpr_elem is not None:
                font_size_drawingml = int(rpr_elem.get('sz', 2400))

            # Extract color from <a:srgbClr val="">
            color_elem = shape_root.find('.//a:srgbClr', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
            color = color_elem.get('val', 'FF0000') if color_elem is not None else 'FF0000'

            self.text_elements.append({
                'text': text_content,
                'x_emu': x_emu,
                'y_emu': y_emu,
                'width_emu': width_emu,
                'height_emu': height_emu,
                'font_size_drawingml': font_size_drawingml,
                'color': color,
                'advanced_xml': drawingml_xml  # Keep the full advanced XML
            })

            print(f"  ✅ Extracted: '{text_content}' at EMU({x_emu}, {y_emu}) size={font_size_drawingml}")

        except Exception as e:
            print(f"  ❌ Failed to extract from advanced XML: {e}")
            self._extract_basic_text_info(original_element)

    def _extract_basic_text_info(self, text_elem):
        """Fallback: Extract basic info from SVG element"""
        x = float(text_elem.get('x', 200))
        y = float(text_elem.get('y', 150))
        text_content = text_elem.text or 'Text'

        self.text_elements.append({
            'text': text_content,
            'x_emu': int(x * 9144),  # Rough conversion
            'y_emu': int(y * 9144),
            'width_emu': 2286000,   # 2.5 inches
            'height_emu': 914400,   # 1 inch
            'font_size_drawingml': 4800,  # 24pt
            'color': 'FF0000',
            'advanced_xml': None
        })

    def generate_pptx(self, output_file):
        """Generate PPTX using working structure with advanced text processing"""

        with zipfile.ZipFile(self.base_pptx, 'r') as source:
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

                        # Add our processed text elements
                        shape_id = 10
                        for text_data in self.text_elements:
                            if text_data.get('advanced_xml'):
                                # Use the advanced XML from TextConverter
                                try:
                                    # Fix namespace issue
                                    fixed_xml = text_data['advanced_xml']
                                    if fixed_xml.startswith('<p:sp>'):
                                        namespace_declarations = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
                                        fixed_xml = fixed_xml.replace('<p:sp>', f'<p:sp {namespace_declarations}>')

                                    advanced_shape = ET.fromstring(fixed_xml)

                                    # Fix the shape ID
                                    cNvPr = advanced_shape.find('.//p:cNvPr', {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'})
                                    if cNvPr is not None:
                                        cNvPr.set('id', str(shape_id))

                                    spTree.append(advanced_shape)
                                    print(f"  ✅ Added advanced text: '{text_data['text']}'")
                                except Exception as e:
                                    print(f"  ❌ Failed to add advanced XML: {e}")
                                    self._add_basic_text_shape(spTree, text_data, shape_id)
                            else:
                                # Use basic text shape
                                self._add_basic_text_shape(spTree, text_data, shape_id)

                            shape_id += 1

                        data = ET.tostring(root, encoding='utf-8', xml_declaration=True)

                    dest.writestr(item, data)

    def _add_basic_text_shape(self, spTree, text_data, shape_id):
        """Add a basic text shape (fallback)"""
        shape_xml = f'''<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="Text {shape_id}"/>
                <p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
                <p:nvPr><p:ph type="obj"/></p:nvPr>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{text_data['x_emu']}" y="{text_data['y_emu']}"/>
                    <a:ext cx="{text_data['width_emu']}" cy="{text_data['height_emu']}"/>
                </a:xfrm>
            </p:spPr>
            <p:txBody>
                <a:bodyPr/><a:lstStyle/>
                <a:p>
                    <a:r>
                        <a:rPr lang="en-US" dirty="0" sz="{text_data['font_size_drawingml']}">
                            <a:solidFill><a:srgbClr val="{text_data['color']}"/></a:solidFill>
                        </a:rPr>
                        <a:t>{text_data['text']}</a:t>
                    </a:r>
                </a:p>
            </p:txBody>
        </p:sp>'''

        shape_element = ET.fromstring(shape_xml)
        spTree.append(shape_element)
        print(f"  ✅ Added basic text: '{text_data['text']}'")

if __name__ == "__main__":
    # Test the hybrid converter
    converter = HybridTextConverter()
    converter.process_svg_text('debug_simple_visible_test.svg')
    converter.generate_pptx('debug_hybrid_advanced.pptx')
    print("✅ Created debug_hybrid_advanced.pptx with advanced text processing!")
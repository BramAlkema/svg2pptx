#!/usr/bin/env python3
"""
Test script to generate PowerPoint-compatible DrawingML XML
and identify issues causing repair requirements.
"""

import xml.etree.ElementTree as ET
from src.converters.shapes import RectangleConverter
from src.converters.base import CoordinateSystem, ConversionContext

def create_clean_slide_xml():
    """Create a complete, clean PowerPoint slide with DrawingML shapes"""
    
    # Create modular converter components
    coord_system = CoordinateSystem((0, 0, 800, 600))
    context = ConversionContext()
    context.coordinate_system = coord_system
    
    converter = RectangleConverter()
    
    # Test shapes
    shapes = []
    test_elements = [
        '<rect x="10" y="20" width="100" height="80" fill="red"/>',
        '<rect x="120" y="20" width="100" height="80" fill="green"/>',
        '<rect x="230" y="20" width="100" height="80" fill="blue"/>'
    ]
    
    for rect_xml in test_elements:
        rect_element = ET.fromstring(rect_xml)
        if converter.can_convert(rect_element):
            shape_xml = converter.convert(rect_element, context)
            shapes.append(shape_xml)
    
    # Create complete slide XML with proper namespaces and structure
    slide_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" 
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" 
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="0" cy="0"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="0" cy="0"/>
                </a:xfrm>
            </p:grpSpPr>
            {''.join(shapes)}
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sld>'''
    
    return slide_xml

def validate_xml_structure(xml_content):
    """Validate XML structure and identify potential issues"""
    issues = []
    
    try:
        # Parse XML to check for syntax errors
        root = ET.fromstring(xml_content)
        print("✓ XML syntax is valid")
    except ET.ParseError as e:
        issues.append(f"XML Parse Error: {e}")
        return issues
    
    # Check for required namespaces
    required_namespaces = [
        'http://schemas.openxmlformats.org/drawingml/2006/main',
        'http://schemas.openxmlformats.org/presentationml/2006/main'
    ]
    
    root_attribs = root.attrib
    declared_namespaces = [v for k, v in root_attribs.items() if k.startswith('xmlns')]
    
    for ns in required_namespaces:
        if ns not in declared_namespaces:
            issues.append(f"Missing required namespace: {ns}")
        else:
            print(f"✓ Required namespace present: {ns}")
    
    # Check for required elements
    required_elements = ['p:cSld', 'p:spTree', 'p:clrMapOvr']
    for elem_name in required_elements:
        if root.find(f".//{elem_name}", namespaces={'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}) is not None:
            print(f"✓ Required element present: {elem_name}")
        else:
            issues.append(f"Missing required element: {elem_name}")
    
    # Check shape IDs for uniqueness
    shape_ids = []
    for cNvPr in root.findall(".//p:cNvPr", namespaces={'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}):
        shape_id = cNvPr.get('id')
        if shape_id in shape_ids:
            issues.append(f"Duplicate shape ID: {shape_id}")
        else:
            shape_ids.append(shape_id)
    
    if len(set(shape_ids)) == len(shape_ids):
        print(f"✓ All shape IDs are unique: {shape_ids}")
    
    # Check EMU coordinate values (should be positive integers)
    for xfrm in root.findall(".//a:xfrm", namespaces={'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}):
        for elem in ['a:off', 'a:ext']:
            coord_elem = xfrm.find(elem, namespaces={'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
            if coord_elem is not None:
                x = coord_elem.get('x', '0')
                y = coord_elem.get('y', '0')
                cx = coord_elem.get('cx', '0')
                cy = coord_elem.get('cy', '0')
                
                for coord_name, coord_val in [('x', x), ('y', y), ('cx', cx), ('cy', cy)]:
                    if coord_val and coord_val != '0':
                        try:
                            int_val = int(coord_val)
                            if int_val < 0:
                                issues.append(f"Negative coordinate value: {coord_name}={coord_val}")
                            elif int_val > 50000000:  # Very large EMU values might be problematic
                                issues.append(f"Very large coordinate value: {coord_name}={coord_val}")
                        except ValueError:
                            issues.append(f"Invalid coordinate value: {coord_name}={coord_val}")
    
    return issues

def main():
    print("Testing PowerPoint DrawingML XML Generation...")
    print("=" * 50)
    
    # Generate slide XML
    slide_xml = create_clean_slide_xml()
    
    print(f"Generated XML length: {len(slide_xml)} characters")
    print("\nFirst 500 characters of generated XML:")
    print(slide_xml[:500])
    print("...")
    
    print("\nValidating XML structure:")
    print("-" * 30)
    
    issues = validate_xml_structure(slide_xml)
    
    if issues:
        print("\n❌ ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ No validation issues found!")
    
    # Save to file for inspection
    with open('/Users/ynse/projects/svg2pptx/test_slide.xml', 'w', encoding='utf-8') as f:
        f.write(slide_xml)
    
    print(f"\nGenerated slide XML saved to: test_slide.xml")
    print("\nYou can now test this XML in PowerPoint to see if it requires repair.")

if __name__ == '__main__':
    main()
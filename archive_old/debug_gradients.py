#!/usr/bin/env python3
"""Debug gradient registration and path rendering."""

import sys
sys.path.append('.')

from lxml import etree as ET
from core.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext
from src.converters.groups import GroupHandler

def debug_gradients_and_paths():
    """Debug gradient and path issues."""

    # Test gradient SVG
    gradient_svg = '''<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
                <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
            </linearGradient>
        </defs>
        <rect x="10" y="10" width="180" height="120" fill="url(#grad1)" stroke="black"/>
    </svg>'''

    # Test path SVG
    path_svg = '''<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
        <path d="M 50 150 Q 100 50 150 150 T 250 150" stroke="blue" stroke-width="3" fill="none"/>
    </svg>'''

    # Create services
    services = ConversionServices.create_default()

    print("=== GRADIENT DEBUG ===")

    # Parse gradient SVG
    gradient_root = ET.fromstring(gradient_svg)
    context = ConversionContext(services=services, svg_root=gradient_root)

    # Check if GroupHandler can extract definitions
    group_handler = GroupHandler(services=services)

    # Extract definitions
    definitions = group_handler.extract_definitions(gradient_root)
    print(f"Found {len(definitions)} definitions:")
    for def_id, def_element in definitions.items():
        print(f"  - {def_id}: {def_element.tag}")

        # Register with gradient service
        if 'gradient' in def_element.tag.lower():
            services.gradient_service.register_gradient(def_id, def_element)
            print(f"    Registered with GradientService")

    # Test gradient resolution
    gradient_content = services.gradient_service.get_gradient_content("grad1")
    print(f"Gradient 'grad1' resolved: {gradient_content is not None}")
    if gradient_content:
        print(f"Content preview: {gradient_content[:100]}...")

    print("\n=== PATH DEBUG ===")

    # Parse path SVG
    path_root = ET.fromstring(path_svg)
    path_context = ConversionContext(services=services, svg_root=path_root)

    # Get path element
    path_element = path_root.find('.//{http://www.w3.org/2000/svg}path')
    if path_element is not None:
        print(f"Path element found: {path_element.get('d')}")

        # Check if path converter exists
        path_converter = services.converter_registry.get_converter('path')
        if path_converter:
            print("PathConverter found in registry")
            try:
                path_xml = path_converter.convert(path_element, path_context)
                print(f"Path conversion successful: {len(path_xml)} chars")
                if not path_xml.strip():
                    print("WARNING: Path conversion returned empty result")
            except Exception as e:
                print(f"Path conversion failed: {e}")
        else:
            print("ERROR: No PathConverter found in registry")
    else:
        print("ERROR: Path element not found")

if __name__ == "__main__":
    debug_gradients_and_paths()
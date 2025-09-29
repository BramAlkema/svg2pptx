#!/usr/bin/env python3
"""
Services Bootstrap for SVG2PPTX
===============================

Wire all services properly with DI propagation.
"""

from src.services.conversion_services import ConversionServices
from src.viewbox.core import ViewportEngine
from src.units import UnitConverter

def build_services(svg_root, slide_w_emu, slide_h_emu):
    """
    Build fully wired ConversionServices with proper viewport mapping.

    Args:
        svg_root: SVG root element
        slide_w_emu: Target slide width in EMU
        slide_h_emu: Target slide height in EMU

    Returns:
        ConversionServices: Fully wired services with viewport mapping
    """
    # Create unit converter
    unit_converter = UnitConverter()

    # Create viewport mapping
    viewport_mapping = (ViewportEngine(unit_converter)
                       .for_svg(svg_root)
                       .with_slide_size(slide_w_emu, slide_h_emu)
                       .top_left()
                       .meet()
                       .resolve_single())

    # Create default services with viewport mapping
    services = ConversionServices.create_default()

    # Wire the viewport mapping into the services
    services._viewport_mapping = viewport_mapping

    # Add viewport mapping getter method
    def get_viewport_mapping():
        return viewport_mapping

    services.get_viewport_mapping = get_viewport_mapping

    # Create a ViewportService-compatible coordinate system wrapper
    class ViewportCoordinateSystem:
        """Wrapper that provides both viewport_mapping and svg_to_emu interface."""

        def __init__(self, viewport_mapping):
            self.viewport_mapping = viewport_mapping

        def svg_to_emu(self, x, y):
            """Convert SVG coordinates to EMU using viewport mapping."""
            emu_x = int(x * self.viewport_mapping['scale_x'] + self.viewport_mapping['translate_x'])
            emu_y = int(y * self.viewport_mapping['scale_y'] + self.viewport_mapping['translate_y'])
            return emu_x, emu_y

        def svg_length_to_emu(self, length, direction):
            """Convert SVG length to EMU using viewport scale."""
            if direction == 'x':
                return int(length * self.viewport_mapping['scale_x'])
            else:
                return int(length * self.viewport_mapping['scale_y'])

        def __getitem__(self, key):
            """Support dictionary-style access for backward compatibility."""
            return self.viewport_mapping[key]

        def __setitem__(self, key, value):
            """Support dictionary-style assignment for backward compatibility."""
            self.viewport_mapping[key] = value

        def __contains__(self, key):
            """Support 'in' operator for backward compatibility."""
            return key in self.viewport_mapping

        def get(self, key, default=None):
            """Support .get() method for backward compatibility."""
            return self.viewport_mapping.get(key, default)

    # Create the wrapper coordinate system
    services.coordinate_system = ViewportCoordinateSystem(viewport_mapping)

    # Also create a viewport mapping wrapper for backward compatibility
    services.viewport_mapping_wrapper = ViewportCoordinateSystem(viewport_mapping)

    return services
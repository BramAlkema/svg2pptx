"""Viewport coordinate transformation service."""
from typing import Tuple
from lxml import etree as ET
from ..viewbox.core import ViewportEngine
from ..units import UnitConverter, EMU_PER_POINT


class ViewportService:
    """Centralized viewport coordinate transformation."""

    def __init__(self, svg_root: ET.Element, slide_width_emu: int, slide_height_emu: int, services=None):
        # Use ConversionServices for dependency injection
        if services is not None:
            self.unit_converter = services.unit_converter
            viewport_engine = services.viewport_resolver
        else:
            # Service-aware fallback: try ConversionServices first
            try:
                from .conversion_services import ConversionServices
                fallback_services = ConversionServices.get_default_instance()
                self.unit_converter = fallback_services.unit_converter
                viewport_engine = fallback_services.viewport_resolver
            except (ImportError, RuntimeError, AttributeError):
                # Final fallback to direct instantiation
                self.unit_converter = UnitConverter()
                viewport_engine = ViewportEngine(self.unit_converter)

        # Create viewport mapping using ViewportEngine
        self.viewport_mapping = (viewport_engine
                               .for_svg(svg_root)
                               .with_slide_size(slide_width_emu, slide_height_emu)
                               .top_left()
                               .meet()
                               .resolve_single())

    def svg_to_emu(self, svg_x: float, svg_y: float) -> Tuple[int, int]:
        """Transform SVG coordinates to EMU."""
        emu_x = int(svg_x * self.viewport_mapping['scale_x'] + self.viewport_mapping['translate_x'])
        emu_y = int(svg_y * self.viewport_mapping['scale_y'] + self.viewport_mapping['translate_y'])
        return emu_x, emu_y

    def get_scale_factors(self) -> Tuple[float, float]:
        """Get viewport scale factors."""
        return self.viewport_mapping['scale_x'], self.viewport_mapping['scale_y']
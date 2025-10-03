#!/usr/bin/env python3
"""
FilterService for handling SVG filter definitions and conversions.

Provides filter registration, processing, and conversion to DrawingML.
"""

from typing import Dict, Optional, List, Any, TYPE_CHECKING
from lxml import etree as ET
import logging
import math

from ..utils.enhanced_xml_builder import EnhancedXMLBuilder
from ..filters import (
    FilterFactory,
    FilterContext,
    FilterResult,
    FilterStrategy,
    create_filter_factory,
    create_filter_context
)

if TYPE_CHECKING:
    from ..policy.engine import Policy
    from .conversion_services import ConversionServices

logger = logging.getLogger(__name__)


class FilterService:
    """
    Service for managing SVG filter definitions and conversions.

    Enhanced with FilterFactory integration for policy-driven filter processing
    while maintaining backward compatibility with existing hardcoded filters.
    """

    def __init__(self, policy: Optional['Policy'] = None,
                 services: Optional['ConversionServices'] = None):
        """
        Initialize FilterService with optional policy and services.

        Args:
            policy: Policy engine for filter decisions
            services: ConversionServices container for dependencies
        """
        self._filter_cache: Dict[str, ET.Element] = {}
        self._conversion_cache: Dict[str, str] = {}
        self._xml_builder = EnhancedXMLBuilder()

        # Enhanced filter processing with factory
        self._filter_factory = create_filter_factory(policy)
        self._services = services
        self._policy = policy

        # Track which filters use factory vs legacy processing
        self._factory_filters = set()
        self._legacy_filters = {'feGaussianBlur', 'feDropShadow', 'feDiffuseLighting', 'feSpecularLighting'}

    def register_filter(self, filter_id: str, filter_element: ET.Element) -> None:
        """Register a filter definition for later resolution."""
        self._filter_cache[filter_id] = filter_element

    def get_filter_content(self, filter_id: str, context: Any = None) -> Optional[str]:
        """
        Get filter content by ID.

        Args:
            filter_id: The ID of the filter to resolve
            context: Optional conversion context

        Returns:
            Filter content as DrawingML string, or None if not found
        """
        # Remove url() wrapper if present
        clean_id = filter_id.replace('url(#', '').replace(')', '').replace('#', '')

        # Check cache first
        if clean_id in self._conversion_cache:
            return self._conversion_cache[clean_id]

        # Look for filter in cache
        if clean_id in self._filter_cache:
            filter_element = self._filter_cache[clean_id]

            try:
                content = self._convert_filter_definition(filter_element, context)
                # Cache the result
                self._conversion_cache[clean_id] = content
                return content
            except Exception as e:
                logger.error(f"Filter conversion failed for {filter_id}: {e}")
                return None

        logger.warning(f"Filter not found: {filter_id}")
        return None

    def _convert_filter_definition(self, filter_element: ET.Element, context: Any = None) -> str:
        """
        Convert a filter definition element to DrawingML.

        Enhanced to use FilterFactory for complex filters while maintaining
        backward compatibility for legacy filters.
        """
        filter_id = filter_element.get('id', f'filter_{id(filter_element)}')

        # Process child filter primitives
        drawingml_parts = []

        for child in filter_element:
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            # Try factory-based processing first for supported filters
            if self._should_use_factory(tag_name) and self._services:
                try:
                    factory_result = self._process_with_factory(child, context)
                    if factory_result:
                        drawingml_parts.append(factory_result)
                        continue
                except Exception as e:
                    logger.warning(f"Factory processing failed for {tag_name}: {e}")
                    # Fall through to legacy processing

            # Legacy hardcoded processing for simple filters
            if tag_name == 'feGaussianBlur':
                std_deviation = child.get('stdDeviation', '1')
                try:
                    blur_radius = float(std_deviation) * 12700  # Convert to EMUs
                    drawingml_parts.append(f'<a:effectLst><a:blur rad="{int(blur_radius)}"/></a:effectLst>')
                except ValueError:
                    pass

            elif tag_name == 'feDropShadow':
                dx = child.get('dx', '3')
                dy = child.get('dy', '3')
                std_deviation = child.get('stdDeviation', '1')

                try:
                    dx_emu = int(float(dx) * 12700)
                    dy_emu = int(float(dy) * 12700)
                    blur_emu = int(float(std_deviation) * 12700)

                    drawingml_parts.append(f'''<a:effectLst>
  <a:outerShdw blurRad="{blur_emu}" dist="{int((dx_emu**2 + dy_emu**2)**0.5)}" dir="{int(math.atan2(dy_emu, dx_emu) * 180 / math.pi * 60000) % 21600000}">
    <a:srgbClr val="000000">
      <a:alpha val="50000"/>
    </a:srgbClr>
  </a:outerShdw>
</a:effectLst>''')
                except ValueError:
                    pass

            elif tag_name == 'feDiffuseLighting':
                # Diffuse lighting: convert to PowerPoint 3D effects
                diffuse_xml = self._convert_diffuse_lighting(child)
                if diffuse_xml:
                    drawingml_parts.append(diffuse_xml)

            elif tag_name == 'feSpecularLighting':
                # Specular lighting: convert to PowerPoint highlight effects
                specular_xml = self._convert_specular_lighting(child)
                if specular_xml:
                    drawingml_parts.append(specular_xml)

            else:
                # Unsupported filter - add comment for debugging
                logger.debug(f"Unsupported filter primitive: {tag_name}")
                drawingml_parts.append(f'<!-- Unsupported filter: {tag_name} -->')

        # Combine filter primitives into complete effect
        if drawingml_parts:
            return self._combine_filter_effects(drawingml_parts, filter_id)
        else:
            # Fallback for completely unsupported filter combinations
            return f'<!-- Filter {filter_id}: No supported primitives -->'

    def _combine_filter_effects(self, drawingml_parts: List[str], filter_id: str) -> str:
        """
        Combine multiple filter primitive DrawingML into a complete effect.

        Args:
            drawingml_parts: List of DrawingML strings from filter primitives
            filter_id: Unique identifier for the filter

        Returns:
            Combined DrawingML string
        """
        if not drawingml_parts:
            return ""

        if len(drawingml_parts) == 1:
            return drawingml_parts[0]

        # For multiple effects, wrap in effect group
        combined = f'<a:effectLst>\n'
        for part in drawingml_parts:
            if part and not part.strip().startswith('<!--'):
                combined += f'  {part}\n'
        combined += '</a:effectLst>'

        return combined

    def process_svg_filters(self, svg_root: ET.Element) -> None:
        """Process all filter definitions in an SVG document."""
        # Find and register all filters
        for filter_elem in svg_root.xpath('.//svg:defs//svg:filter',
                                          namespaces={'svg': 'http://www.w3.org/2000/svg'}):
            filter_id = filter_elem.get('id')
            if filter_id:
                self.register_filter(filter_id, filter_elem)

    def extract_filters_from_svg(self, svg_root: ET.Element) -> None:
        """Alias for process_svg_filters for compatibility."""
        self.process_svg_filters(svg_root)

    def _should_use_factory(self, filter_type: str) -> bool:
        """
        Determine if a filter should use factory processing.

        Args:
            filter_type: Filter primitive type (e.g., 'feOffset', 'feBlend')

        Returns:
            True if filter should use factory, False for legacy processing
        """
        # Use factory for filters that have been migrated and registered
        if filter_type in self._factory_filters:
            return True

        # Use factory for any filter that the factory supports but isn't legacy
        if (filter_type not in self._legacy_filters and
            self._filter_factory.is_filter_supported(filter_type)):
            self._factory_filters.add(filter_type)
            return True

        return False

    def _process_with_factory(self, filter_element: ET.Element, context: Any = None) -> Optional[str]:
        """
        Process filter element using FilterFactory.

        Args:
            filter_element: SVG filter primitive element
            context: Optional processing context

        Returns:
            DrawingML string if successful, None otherwise
        """
        if not self._services:
            logger.warning("Cannot use factory processing without ConversionServices")
            return None

        try:
            # Create filter processor
            processor = self._filter_factory.create_filter_for_element(filter_element)
            if not processor:
                return None

            # Create filter context
            # Use a default viewport if none provided in context
            viewport = {'width': 800.0, 'height': 600.0}
            if context and hasattr(context, 'viewport'):
                viewport = context.viewport

            filter_context = create_filter_context(
                element=filter_element,
                services=self._services,
                viewport=viewport
            )

            # Check if processor can handle this element
            if not processor.can_apply(filter_element, filter_context):
                return None

            # Apply filter processing
            result = processor.apply(filter_element, filter_context)

            if result.is_success():
                drawingml = result.get_drawingml()

                # Log strategy used
                strategy = result.get_strategy()
                logger.debug(f"Factory processed {processor.filter_type} using {strategy.value} strategy")

                return drawingml
            else:
                logger.warning(f"Factory processing failed: {result.get_error_message()}")
                return None

        except Exception as e:
            logger.error(f"Factory processing error for {filter_element.tag}: {e}")
            return None

    def register_filter_processor(self, filter_type: str, processor_class) -> None:
        """
        Register a filter processor with the factory.

        Args:
            filter_type: Filter type to register
            processor_class: FilterProcessor subclass
        """
        try:
            self._filter_factory.register_filter(filter_type, processor_class)
            self._factory_filters.add(filter_type)
            logger.info(f"Registered factory processor for {filter_type}")
        except Exception as e:
            logger.error(f"Failed to register filter processor for {filter_type}: {e}")

    def get_filter_coverage(self) -> Dict[str, bool]:
        """
        Get comprehensive filter coverage report.

        Returns:
            Dictionary mapping filter types to support status
        """
        return self._filter_factory.get_filter_coverage()

    def get_filter_factory(self) -> FilterFactory:
        """
        Get the underlying FilterFactory instance.

        Returns:
            FilterFactory instance for advanced usage
        """
        return self._filter_factory

    def clear_cache(self) -> None:
        """Clear all cached filters and conversions."""
        self._filter_cache.clear()
        self._conversion_cache.clear()

    def get_supported_filters(self) -> List[str]:
        """Get list of supported filter types."""
        return ['feGaussianBlur', 'feDropShadow', 'feDiffuseLighting', 'feSpecularLighting']

    def _convert_diffuse_lighting(self, diffuse_element: ET.Element) -> Optional[str]:
        """
        Convert feDiffuseLighting to PowerPoint 3D effects.

        Args:
            diffuse_element: feDiffuseLighting element

        Returns:
            DrawingML string for 3D lighting effects
        """
        try:
            # Extract diffuse lighting parameters
            surface_scale = float(diffuse_element.get('surfaceScale', '1'))
            diffuse_constant = float(diffuse_element.get('diffuseConstant', '1'))
            lighting_color = diffuse_element.get('lighting-color', 'white')

            # Find light source child element
            light_source = None
            light_type = None
            light_params = {}

            for child in diffuse_element:
                tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag

                if tag_name == 'feDistantLight':
                    light_type = 'distant'
                    light_params = {
                        'azimuth': float(child.get('azimuth', '0')),
                        'elevation': float(child.get('elevation', '45'))
                    }
                elif tag_name == 'fePointLight':
                    light_type = 'point'
                    light_params = {
                        'x': float(child.get('x', '0')),
                        'y': float(child.get('y', '0')),
                        'z': float(child.get('z', '0'))
                    }
                elif tag_name == 'feSpotLight':
                    light_type = 'spot'
                    light_params = {
                        'x': float(child.get('x', '0')),
                        'y': float(child.get('y', '0')),
                        'z': float(child.get('z', '0')),
                        'pointsAtX': float(child.get('pointsAtX', '0')),
                        'pointsAtY': float(child.get('pointsAtY', '0')),
                        'pointsAtZ': float(child.get('pointsAtZ', '0')),
                        'specularExponent': float(child.get('specularExponent', '1'))
                    }

            # Generate PowerPoint 3D effects using templates
            return self._generate_template_based_lighting(
                light_type, light_params, surface_scale, diffuse_constant, lighting_color
            )

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse diffuse lighting parameters: {e}")
            return None

    def _generate_template_based_lighting(self, light_type: Optional[str], light_params: Dict[str, float],
                                         surface_scale: float, diffuse_constant: float,
                                         lighting_color: str) -> str:
        """
        Generate PowerPoint 3D lighting effects using XML templates.

        Args:
            light_type: Type of light source (distant, point, spot)
            light_params: Light source parameters
            surface_scale: Surface elevation scaling
            diffuse_constant: Material diffuse reflection constant
            lighting_color: Light color

        Returns:
            DrawingML string for 3D lighting effects
        """
        # Calculate bevel dimensions based on surface scale
        bevel_width = min(int(surface_scale * 25400), 2540000)  # Cap at 100pt in EMU
        bevel_height = bevel_width // 2

        # Determine light direction based on light type
        light_direction = "tl"  # default top-left
        if light_type == 'distant' and light_params:
            azimuth = light_params.get('azimuth', 0)
            elevation = light_params.get('elevation', 45)

            # Map azimuth to PowerPoint light directions
            if 0 <= azimuth < 45 or 315 <= azimuth < 360:
                light_direction = "t"  # top
            elif 45 <= azimuth < 135:
                light_direction = "tr" # top-right
            elif 135 <= azimuth < 225:
                light_direction = "r"  # right
            elif 225 <= azimuth < 315:
                light_direction = "br" # bottom-right

        # Determine if we need shadow based on surface scale
        with_shadow = surface_scale > 1.0
        shadow_blur = min(int(surface_scale * 12700), 127000) if with_shadow else 25400
        shadow_alpha = min(int(diffuse_constant * 12500), 25000) if with_shadow else 25000

        # Use template-based generation
        try:
            lighting_element = self._xml_builder.generate_diffuse_lighting_3d(
                light_direction=light_direction,
                bevel_width=bevel_width,
                bevel_height=bevel_height,
                with_shadow=with_shadow,
                shadow_blur=shadow_blur,
                shadow_alpha=shadow_alpha
            )

            # Convert Element to string
            return ET.tostring(lighting_element, encoding='unicode', pretty_print=True)

        except Exception as e:
            logger.error(f"Template-based lighting generation failed: {e}")
            # Fallback to basic 3D effect
            return '<a:effectLst><a:sp3d><a:bevelT w="50800" h="25400"><a:noFill/></a:bevelT></a:sp3d></a:effectLst>'

    def _convert_specular_lighting(self, specular_element: ET.Element) -> Optional[str]:
        """
        Convert feSpecularLighting to PowerPoint highlight effects.

        Args:
            specular_element: feSpecularLighting element

        Returns:
            DrawingML string for specular lighting effects
        """
        try:
            # Extract specular lighting parameters
            surface_scale = float(specular_element.get('surfaceScale', '1'))
            specular_constant = float(specular_element.get('specularConstant', '1'))
            specular_exponent = float(specular_element.get('specularExponent', '1'))
            lighting_color = specular_element.get('lighting-color', 'white')

            # Find light source child element
            light_type = None
            light_params = {}

            for child in specular_element:
                tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag

                if tag_name == 'feDistantLight':
                    light_type = 'distant'
                    light_params = {
                        'azimuth': float(child.get('azimuth', '0')),
                        'elevation': float(child.get('elevation', '45'))
                    }
                elif tag_name == 'fePointLight':
                    light_type = 'point'
                    light_params = {
                        'x': float(child.get('x', '0')),
                        'y': float(child.get('y', '0')),
                        'z': float(child.get('z', '0'))
                    }
                elif tag_name == 'feSpotLight':
                    light_type = 'spot'
                    light_params = {
                        'x': float(child.get('x', '0')),
                        'y': float(child.get('y', '0')),
                        'z': float(child.get('z', '0')),
                        'pointsAtX': float(child.get('pointsAtX', '0')),
                        'pointsAtY': float(child.get('pointsAtY', '0')),
                        'pointsAtZ': float(child.get('pointsAtZ', '0')),
                        'specularExponent': float(child.get('specularExponent', '1'))
                    }

            # Generate PowerPoint specular effects using templates
            return self._generate_template_based_specular_lighting(
                light_type, light_params, surface_scale, specular_constant,
                specular_exponent, lighting_color
            )

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse specular lighting parameters: {e}")
            return None

    def _generate_template_based_specular_lighting(self, light_type: Optional[str], light_params: Dict[str, float],
                                                  surface_scale: float, specular_constant: float,
                                                  specular_exponent: float, lighting_color: str) -> str:
        """
        Generate PowerPoint specular lighting effects using XML templates.

        Args:
            light_type: Type of light source (distant, point, spot)
            light_params: Light source parameters
            surface_scale: Surface elevation scaling
            specular_constant: Material specular reflection constant
            specular_exponent: Shininess/focus of specular highlights
            lighting_color: Light color

        Returns:
            DrawingML string for specular lighting effects
        """
        # Parse lighting color
        if lighting_color.startswith('#'):
            color_hex = lighting_color[1:]
        elif lighting_color == 'white':
            color_hex = 'FFFFFF'
        else:
            color_hex = 'FFFFFF'  # Default to white

        # Use template-based generation from EnhancedXMLBuilder
        try:
            lighting_xml = self._xml_builder.generate_specular_lighting_for_filter(
                light_type=light_type,
                light_params=light_params,
                surface_scale=surface_scale,
                specular_constant=specular_constant,
                specular_exponent=specular_exponent,
                lighting_color=color_hex
            )

            return lighting_xml

        except Exception as e:
            logger.error(f"Template-based specular lighting generation failed: {e}")
            # Fallback to basic highlight effect
            return '''<a:effectLst>
  <a:sp3d prstMaterial="metal">
    <a:bevelT w="25400" h="12700"/>
  </a:sp3d>
  <a:outerShdw blurRad="25400" dist="38100" dir="5400000">
    <a:srgbClr val="FFFFFF">
      <a:alpha val="60000"/>
    </a:srgbClr>
  </a:outerShdw>
</a:effectLst>'''
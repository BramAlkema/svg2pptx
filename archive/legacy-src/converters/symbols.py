#!/usr/bin/env python3
"""
SVG Symbol and Use Element Converter

This module handles SVG symbol definitions and use element instantiations,
providing comprehensive support for reusable graphics in PowerPoint conversion.

Key Features:
- Symbol definition extraction and storage
- Use element instantiation with proper transforms
- Nested symbol and use element support
- Symbol library management across documents
- ViewBox handling for symbol scaling
- Coordinate system transformation for symbol placement

SVG Symbol Reference:
- <symbol> elements define reusable graphics
- <use> elements instantiate symbols or other elements
- href/xlink:href attributes reference symbol IDs
- Transform attributes control symbol placement
- ViewBox defines symbol coordinate system
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from lxml import etree as ET

from .base import BaseConverter, ConversionContext
from ..transforms import Matrix


@dataclass
class SymbolDefinition:
    """Represents a parsed SVG symbol definition."""
    id: str
    element: ET.Element
    viewBox: Optional[Tuple[float, float, float, float]] = None
    width: Optional[float] = None
    height: Optional[float] = None
    preserve_aspect_ratio: str = "xMidYMid meet"
    content_xml: Optional[str] = None  # Cached converted content


@dataclass
class UseInstance:
    """Represents a use element instance."""
    href: str
    x: float = 0.0
    y: float = 0.0
    width: Optional[float] = None
    height: Optional[float] = None
    transform: Optional[Matrix] = None


class SymbolConverter(BaseConverter):
    """Converts SVG symbol definitions and use element instantiations."""
    
    supported_elements = ['symbol', 'use', 'defs']
    
    def __init__(self, services: 'ConversionServices'):
        super().__init__(services)
        self.symbols: Dict[str, SymbolDefinition] = {}

        # Track use element processing to prevent infinite recursion
        self.use_processing_stack: List[str] = []
        
        # Symbol conversion cache
        self.symbol_content_cache: Dict[str, str] = {}
    
    def can_convert(self, element: ET.Element, context: Optional[ConversionContext] = None) -> bool:
        """Check if element can be converted by this converter."""
        tag = self.get_element_tag(element)
        return tag in self.supported_elements
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert symbol, use, or defs element."""
        tag = self.get_element_tag(element)
        
        if tag == 'symbol':
            return self._process_symbol_definition(element, context)
        elif tag == 'use':
            return self._process_use_element(element, context)
        elif tag == 'defs':
            return self._process_definitions(element, context)
        
        return ""
    
    def _process_definitions(self, defs_element: ET.Element, context: ConversionContext) -> str:
        """Process <defs> section and extract symbol definitions."""
        for child in defs_element:
            if child.tag.endswith('symbol'):
                self._extract_symbol_definition(child)
        
        return ""  # Definitions don't generate direct output
    
    def _process_symbol_definition(self, symbol_element: ET.Element, context: ConversionContext) -> str:
        """Process standalone symbol definition."""
        self._extract_symbol_definition(symbol_element)
        return ""  # Symbol definitions don't generate direct output
    
    def _extract_symbol_definition(self, symbol_element: ET.Element) -> None:
        """Extract and store symbol definition for later use."""
        symbol_id = symbol_element.get('id')
        if not symbol_id:
            return
        
        # Parse viewBox using ConversionServices
        viewbox = None
        viewbox_str = symbol_element.get('viewBox')
        if viewbox_str:
            try:
                import numpy as np

                # Use services for dependency injection
                if hasattr(self, 'services') and self.services and hasattr(self.services, 'viewport_resolver'):
                    resolver = self.services.viewport_resolver
                else:
                    from ..services.conversion_services import ConversionServices
                    services = ConversionServices.create_default()
                    resolver = services.viewport_resolver

                parsed = resolver.parse_viewbox_strings(np.array([viewbox_str]))
                if len(parsed) > 0 and len(parsed[0]) >= 4:
                    viewbox = tuple(parsed[0][:4])
            except ImportError:
                # Fallback to legacy parsing if ViewportEngine not available
                pass
            except Exception:
                # Fallback on any parsing error
                pass

            # Legacy fallback - enhanced to handle commas
            if viewbox is None:
                try:
                    cleaned = viewbox_str.strip().replace(',', ' ')
                    viewbox_values = [float(v) for v in cleaned.split()]
                    if len(viewbox_values) >= 4:
                        viewbox = tuple(viewbox_values[:4])
                except (ValueError, TypeError):
                    viewbox = None
        
        # Parse dimensions
        width = self._parse_dimension(symbol_element.get('width'))
        height = self._parse_dimension(symbol_element.get('height'))
        
        # Get preserve aspect ratio
        preserve_aspect_ratio = symbol_element.get('preserveAspectRatio', 'xMidYMid meet')
        
        # Store symbol definition
        self.symbols[symbol_id] = SymbolDefinition(
            id=symbol_id,
            element=symbol_element,
            viewBox=viewbox,
            width=width,
            height=height,
            preserve_aspect_ratio=preserve_aspect_ratio
        )
    
    def _process_use_element(self, use_element: ET.Element, context: ConversionContext) -> str:
        """Process <use> element that instantiates symbols or elements."""
        # Parse use element attributes
        use_instance = self._parse_use_element(use_element)
        if not use_instance.href:
            return ""
        
        # Check for recursion
        if use_instance.href in self.use_processing_stack:
            return f'<!-- Circular reference detected: {use_instance.href} -->'
        
        # Find referenced element
        referenced_element = self._find_referenced_element(use_instance.href, context)
        if referenced_element is None:
            return f'<!-- Referenced element not found: {use_instance.href} -->'
        
        # Process based on referenced element type
        ref_tag = self.get_element_tag(referenced_element)
        
        if ref_tag == 'symbol':
            return self._instantiate_symbol(use_instance, referenced_element, context)
        else:
            # Use element references another element (not symbol)
            return self._instantiate_element(use_instance, referenced_element, context)
    
    def _parse_use_element(self, use_element: ET.Element) -> UseInstance:
        """Parse use element attributes."""
        # Get href (try both href and xlink:href)
        href = (use_element.get('href') or 
                use_element.get('{http://www.w3.org/1999/xlink}href', ''))
        
        # Remove # prefix if present
        if href.startswith('#'):
            href = href[1:]
        
        # Parse position and dimensions
        x = float(use_element.get('x', '0'))
        y = float(use_element.get('y', '0'))
        width = self._parse_dimension(use_element.get('width'))
        height = self._parse_dimension(use_element.get('height'))
        
        # Parse transform
        transform = None
        transform_str = use_element.get('transform', '')
        if transform_str:
            transform = self.transform_parser.parse_to_matrix(transform_str)
        
        return UseInstance(
            href=href,
            x=x, y=y,
            width=width, height=height,
            transform=transform
        )
    
    def _find_referenced_element(self, element_id: str, context: ConversionContext) -> Optional[ET.Element]:
        """Find element by ID in the SVG document."""
        if context.svg_root is None:
            return None
        
        # Search for element with matching ID
        elements = context.svg_root.xpath(f"//*[@id='{element_id}']")
        if elements:
            return elements[0]
        
        return None
    
    def _instantiate_symbol(self, use_instance: UseInstance, symbol_element: ET.Element, 
                          context: ConversionContext) -> str:
        """Instantiate a symbol using use element parameters."""
        symbol_id = symbol_element.get('id', '')
        
        # Prevent infinite recursion
        self.use_processing_stack.append(use_instance.href)
        
        try:
            # Get or create symbol definition
            if symbol_id not in self.symbols:
                self._extract_symbol_definition(symbol_element)
            
            if symbol_id not in self.symbols:
                return f'<!-- Failed to process symbol: {symbol_id} -->'
            
            symbol_def = self.symbols[symbol_id]
            
            # Check cache first
            cache_key = f"{symbol_id}_{use_instance.x}_{use_instance.y}"
            if cache_key in self.symbol_content_cache:
                return self.symbol_content_cache[cache_key]
            
            # Convert symbol content
            symbol_content = self._convert_symbol_content(symbol_def, use_instance, context)
            
            # Cache the result
            self.symbol_content_cache[cache_key] = symbol_content
            
            return symbol_content
            
        finally:
            # Remove from processing stack
            if use_instance.href in self.use_processing_stack:
                self.use_processing_stack.remove(use_instance.href)
    
    def _instantiate_element(self, use_instance: UseInstance, referenced_element: ET.Element,
                           context: ConversionContext) -> str:
        """Instantiate a regular element (not symbol) using use element."""
        # Create a copy of the element with use transforms applied
        element_copy = self._apply_use_transforms(referenced_element, use_instance)
        
        # Convert using appropriate converter
        if context.converter_registry:
            converter = context.converter_registry.get_converter_for_element(element_copy)
            if converter and converter != self:  # Avoid self-recursion
                return converter.convert(element_copy, context)
        
        return f'<!-- Could not find converter for element: {self.get_element_tag(referenced_element)} -->'
    
    def _convert_symbol_content(self, symbol_def: SymbolDefinition, use_instance: UseInstance,
                              context: ConversionContext) -> str:
        """Convert symbol content to DrawingML."""
        # Calculate transformation matrix
        transform_matrix = self._calculate_symbol_transform(symbol_def, use_instance)
        
        # Process symbol children
        child_elements = []
        for child in symbol_def.element:
            if context.converter_registry:
                converter = context.converter_registry.get_converter_for_element(child)
                if converter and converter != self:  # Avoid self-recursion
                    child_xml = converter.convert(child, context)
                    if child_xml.strip():
                        child_elements.append(child_xml)
        
        if not child_elements:
            return ""
        
        # Wrap in group with proper transformation
        group_id = f"symbol_{symbol_def.id}_{context.get_next_shape_id()}"
        children_xml = '\n    '.join(child_elements)
        
        # Generate transform XML
        transform_xml = ""
        if not transform_matrix.is_identity():
            transform_xml = self.transform_converter.get_drawingml_transform(transform_matrix, context)
        
        return f"""<a:grpSp>
    <a:nvGrpSpPr>
        <a:cNvPr id="{context.get_next_shape_id()}" name="{group_id}"/>
        <a:cNvGrpSpPr/>
    </a:nvGrpSpPr>
    <a:grpSpPr>
        {transform_xml}
    </a:grpSpPr>
    {children_xml}
</a:grpSp>"""
    
    def _calculate_symbol_transform(self, symbol_def: SymbolDefinition, 
                                  use_instance: UseInstance) -> Matrix:
        """Calculate the transformation matrix for symbol instantiation."""
        # Start with identity matrix
        result_matrix = Matrix.identity()
        
        # Apply use element transform if present
        if use_instance.transform:
            result_matrix = result_matrix.multiply(use_instance.transform)
        
        # Apply translation from use x,y
        if use_instance.x != 0 or use_instance.y != 0:
            translation = Matrix.translate(use_instance.x, use_instance.y)
            result_matrix = result_matrix.multiply(translation)
        
        # Apply scaling if use element has different dimensions than symbol
        scale_x, scale_y = self._calculate_symbol_scaling(symbol_def, use_instance)
        if scale_x != 1.0 or scale_y != 1.0:
            scaling = Matrix.scale(scale_x, scale_y)
            result_matrix = result_matrix.multiply(scaling)
        
        return result_matrix
    
    def _calculate_symbol_scaling(self, symbol_def: SymbolDefinition, 
                                use_instance: UseInstance) -> Tuple[float, float]:
        """Calculate scaling factors for symbol instantiation."""
        # If use element doesn't specify dimensions, no scaling needed
        if use_instance.width is None or use_instance.height is None:
            return 1.0, 1.0
        
        # If symbol has explicit dimensions, scale to match use dimensions
        if symbol_def.width and symbol_def.height:
            scale_x = use_instance.width / symbol_def.width
            scale_y = use_instance.height / symbol_def.height
            return scale_x, scale_y
        
        # If symbol has viewBox, scale based on viewBox dimensions
        if symbol_def.viewBox:
            _, _, vb_width, vb_height = symbol_def.viewBox
            if vb_width > 0 and vb_height > 0:
                scale_x = use_instance.width / vb_width
                scale_y = use_instance.height / vb_height
                return scale_x, scale_y
        
        # No scaling information available
        return 1.0, 1.0
    
    def _apply_use_transforms(self, element: ET.Element, use_instance: UseInstance) -> ET.Element:
        """Apply use element transforms to a regular element."""
        # Create a copy of the element
        element_copy = ET.Element(element.tag, element.attrib)
        element_copy.text = element.text
        element_copy.tail = element.tail
        
        # Copy all children
        for child in element:
            element_copy.append(child)
        
        # Apply use transforms
        existing_transform = element_copy.get('transform', '')
        use_transform_parts = []
        
        # Add translation
        if use_instance.x != 0 or use_instance.y != 0:
            use_transform_parts.append(f'translate({use_instance.x},{use_instance.y})')
        
        # Add use element transform
        if use_instance.transform and not use_instance.transform.is_identity():
            matrix = use_instance.transform
            use_transform_parts.append(
                f'matrix({matrix.a},{matrix.b},{matrix.c},{matrix.d},{matrix.e},{matrix.f})'
            )
        
        # Combine transforms
        if use_transform_parts:
            use_transform_str = ' '.join(use_transform_parts)
            if existing_transform:
                combined_transform = f'{use_transform_str} {existing_transform}'
            else:
                combined_transform = use_transform_str
            element_copy.set('transform', combined_transform)
        
        return element_copy
    
    def _parse_dimension(self, dimension_str: Optional[str]) -> Optional[float]:
        """Parse dimension string to float value."""
        if not dimension_str:
            return None
        
        try:
            # Use robust length parsing that handles all units properly
            return self.parse_length(dimension_str)
        except (ValueError, TypeError):
            return None
    
    def get_symbol_definition(self, symbol_id: str) -> Optional[SymbolDefinition]:
        """Get symbol definition by ID."""
        return self.symbols.get(symbol_id)
    
    def has_symbol(self, symbol_id: str) -> bool:
        """Check if symbol is defined."""
        return symbol_id in self.symbols
    
    def clear_cache(self) -> None:
        """Clear symbol content cache."""
        self.symbol_content_cache.clear()
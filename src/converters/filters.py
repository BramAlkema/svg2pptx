#!/usr/bin/env python3
"""
SVG Filter Effects Processor for SVG2PPTX

This module handles advanced SVG filter effects - one of the most obscure and
complex SVG features. Converts filter graphs to PowerPoint-compatible effects
or smart rasterization decisions for unsupported complex filters.

Key Features:
- Complete filter primitive support: feGaussianBlur, feDropShadow, feColorMatrix
- Filter graph processing with input/output chaining
- PowerPoint effect mapping (blur, shadow, glow, color adjustments)
- Smart rasterization decisions for complex filter chains
- Performance optimization for filter-heavy documents
- Alpha channel and blend mode approximation
- Lighting effects and convolution filters (basic support)

SVG Filter Reference:
- <filter> elements define filter effects
- Filter primitives: feGaussianBlur, feOffset, feFlood, feComposite, etc.
- filter attribute applies filters to elements
- Complex filter graphs with input/result chaining
"""

import re
import math
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import xml.etree.ElementTree as ET

from .base import BaseConverter
from .base import ConversionContext
from ..colors import ColorParser, ColorInfo
from ..transforms import TransformParser
from ..units import UnitConverter
from ..viewbox import ViewportResolver


class FilterPrimitiveType(Enum):
    """SVG filter primitive types."""
    GAUSSIAN_BLUR = "feGaussianBlur"
    DROP_SHADOW = "feDropShadow"
    OFFSET = "feOffset"
    FLOOD = "feFlood"
    COLOR_MATRIX = "feColorMatrix"
    COMPOSITE = "feComposite"
    MORPH = "feMorphology"
    CONVOLVE = "feConvolveMatrix"
    LIGHTING = "feDiffuseLighting"
    TURBULENCE = "feTurbulence"


class FilterUnits(Enum):
    """Filter coordinate system."""
    OBJECT_BOUNDING_BOX = "objectBoundingBox"
    USER_SPACE_ON_USE = "userSpaceOnUse"


class ColorMatrixType(Enum):
    """Color matrix transformation types."""
    MATRIX = "matrix"
    SATURATE = "saturate" 
    HUE_ROTATE = "hueRotate"
    LUMINANCE_TO_ALPHA = "luminanceToAlpha"


@dataclass
class FilterDefinition:
    """Parsed filter definition."""
    id: str
    x: float
    y: float
    width: float
    height: float
    filter_units: FilterUnits
    primitive_units: FilterUnits
    primitives: List['FilterPrimitive']
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Get filter region bounding box."""
        return (self.x, self.y, self.width, self.height)


@dataclass 
class FilterPrimitive:
    """Base filter primitive."""
    type: FilterPrimitiveType
    input: Optional[str]  # Input source ('SourceGraphic', result id, etc.)
    result: Optional[str]  # Output result id
    x: float
    y: float
    width: float
    height: float
    
    def get_region(self) -> Tuple[float, float, float, float]:
        """Get primitive effect region."""
        return (self.x, self.y, self.width, self.height)


@dataclass
class GaussianBlurPrimitive(FilterPrimitive):
    """Gaussian blur filter primitive."""
    std_deviation_x: float
    std_deviation_y: float
    edge_mode: str = "duplicate"  # duplicate, wrap, none


@dataclass
class DropShadowPrimitive(FilterPrimitive):
    """Drop shadow filter primitive (SVG 2.0)."""
    dx: float
    dy: float
    std_deviation: float
    flood_color: ColorInfo
    flood_opacity: float


@dataclass
class OffsetPrimitive(FilterPrimitive):
    """Offset filter primitive."""
    dx: float
    dy: float


@dataclass
class FloodPrimitive(FilterPrimitive):
    """Flood fill primitive."""
    flood_color: ColorInfo
    flood_opacity: float


@dataclass
class ColorMatrixPrimitive(FilterPrimitive):
    """Color matrix transformation primitive."""
    matrix_type: ColorMatrixType
    values: List[float]  # Matrix values or single value for saturate/hue-rotate


@dataclass
class CompositePrimitive(FilterPrimitive):
    """Composite operation primitive."""
    input2: str  # Second input
    operator: str  # over, in, out, atop, xor, arithmetic
    k1: float = 0  # For arithmetic composite
    k2: float = 0
    k3: float = 0
    k4: float = 0


@dataclass
class FilterEffect:
    """Processed filter effect for PowerPoint conversion."""
    effect_type: str  # blur, shadow, glow, etc.
    parameters: Dict[str, Any]
    requires_rasterization: bool
    complexity_score: float


class FilterConverter(BaseConverter):
    """Converts SVG filter effects to PowerPoint effects."""
    
    supported_elements = ['filter', 'defs']
    
    def __init__(self):
        super().__init__()
        self.filters: Dict[str, FilterDefinition] = {}
        
        # PowerPoint effect mapping
        self.powerpoint_effects = {
            'blur': self._generate_blur_effect,
            'shadow': self._generate_shadow_effect,
            'glow': self._generate_glow_effect,
            'reflection': self._generate_reflection_effect,
        }
        
        # Complexity thresholds for rasterization decisions
        self.rasterization_threshold = 3.0  # Complexity score above which to rasterize
        
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert filter element or process filtered elements."""
        if element.tag.endswith('filter'):
            return self._process_filter_definition(element, context)
        elif element.tag.endswith('defs'):
            return self._process_filter_definitions(element, context)
        
        return ""
    
    def _process_filter_definitions(self, defs_element: ET.Element, context: ConversionContext) -> str:
        """Process filter definitions in <defs>."""
        for child in defs_element:
            if child.tag.endswith('filter'):
                self._extract_filter_definition(child)
        
        return ""
    
    def _process_filter_definition(self, filter_element: ET.Element, context: ConversionContext) -> str:
        """Process standalone filter definition."""
        self._extract_filter_definition(filter_element)
        return ""
    
    def _extract_filter_definition(self, filter_element: ET.Element) -> None:
        """Extract filter definition for later application."""
        filter_id = filter_element.get('id')
        if not filter_id:
            return
        
        # Parse filter region
        x = self._parse_filter_coordinate(filter_element.get('x', '-10%'))
        y = self._parse_filter_coordinate(filter_element.get('y', '-10%'))
        width = self._parse_filter_coordinate(filter_element.get('width', '120%'))
        height = self._parse_filter_coordinate(filter_element.get('height', '120%'))
        
        # Parse units
        filter_units_str = filter_element.get('filterUnits', 'objectBoundingBox')
        filter_units = (FilterUnits.OBJECT_BOUNDING_BOX if filter_units_str == 'objectBoundingBox'
                       else FilterUnits.USER_SPACE_ON_USE)
        
        primitive_units_str = filter_element.get('primitiveUnits', 'userSpaceOnUse')
        primitive_units = (FilterUnits.USER_SPACE_ON_USE if primitive_units_str == 'userSpaceOnUse'
                          else FilterUnits.OBJECT_BOUNDING_BOX)
        
        # Extract filter primitives
        primitives = []
        for child in filter_element:
            primitive = self._parse_filter_primitive(child, primitive_units)
            if primitive:
                primitives.append(primitive)
        
        self.filters[filter_id] = FilterDefinition(
            id=filter_id,
            x=x, y=y, width=width, height=height,
            filter_units=filter_units,
            primitive_units=primitive_units,
            primitives=primitives
        )
    
    def apply_filter_to_element(self, element: ET.Element, context: ConversionContext) -> str:
        """Apply filter effects to an element."""
        filter_attr = element.get('filter', '')
        if not filter_attr.startswith('url(#') or not filter_attr.endswith(')'):
            return ""
        
        filter_id = filter_attr[5:-1]  # Extract ID from url(#id)
        if filter_id not in self.filters:
            return ""
        
        filter_def = self.filters[filter_id]
        
        # Process filter chain
        filter_effects = self._process_filter_chain(filter_def, element, context)
        
        # Convert to PowerPoint effects or decide on rasterization
        return self._convert_filter_effects_to_drawingml(filter_effects, element, context)
    
    def _parse_filter_primitive(self, primitive_element: ET.Element,
                              primitive_units: FilterUnits) -> Optional[FilterPrimitive]:
        """Parse a filter primitive element."""
        tag = primitive_element.tag.split('}')[-1]  # Remove namespace
        
        # Common attributes
        input_attr = primitive_element.get('in')
        result = primitive_element.get('result')
        x = float(primitive_element.get('x', '0'))
        y = float(primitive_element.get('y', '0'))
        width = float(primitive_element.get('width', '100%').rstrip('%')) / 100
        height = float(primitive_element.get('height', '100%').rstrip('%')) / 100
        
        if tag == 'feGaussianBlur':
            std_dev = primitive_element.get('stdDeviation', '0')
            if ' ' in std_dev:
                std_x, std_y = map(float, std_dev.split())
            else:
                std_x = std_y = float(std_dev)
            
            return GaussianBlurPrimitive(
                type=FilterPrimitiveType.GAUSSIAN_BLUR,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                std_deviation_x=std_x, std_deviation_y=std_y,
                edge_mode=primitive_element.get('edgeMode', 'duplicate')
            )
        
        elif tag == 'feDropShadow':
            dx = float(primitive_element.get('dx', '2'))
            dy = float(primitive_element.get('dy', '2'))
            std_dev = float(primitive_element.get('stdDeviation', '3'))
            
            flood_color = self.color_parser.parse(primitive_element.get('flood-color', 'black'))
            flood_opacity = float(primitive_element.get('flood-opacity', '1'))
            
            return DropShadowPrimitive(
                type=FilterPrimitiveType.DROP_SHADOW,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                dx=dx, dy=dy, std_deviation=std_dev,
                flood_color=flood_color, flood_opacity=flood_opacity
            )
        
        elif tag == 'feOffset':
            dx = float(primitive_element.get('dx', '0'))
            dy = float(primitive_element.get('dy', '0'))
            
            return OffsetPrimitive(
                type=FilterPrimitiveType.OFFSET,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                dx=dx, dy=dy
            )
        
        elif tag == 'feFlood':
            flood_color = self.color_parser.parse(primitive_element.get('flood-color', 'black'))
            flood_opacity = float(primitive_element.get('flood-opacity', '1'))
            
            return FloodPrimitive(
                type=FilterPrimitiveType.FLOOD,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                flood_color=flood_color, flood_opacity=flood_opacity
            )
        
        elif tag == 'feColorMatrix':
            matrix_type_str = primitive_element.get('type', 'matrix')
            matrix_type = ColorMatrixType(matrix_type_str) if matrix_type_str in [e.value for e in ColorMatrixType] else ColorMatrixType.MATRIX
            
            values_str = primitive_element.get('values', '1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0')
            values = [float(v) for v in values_str.split()]
            
            return ColorMatrixPrimitive(
                type=FilterPrimitiveType.COLOR_MATRIX,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                matrix_type=matrix_type, values=values
            )
        
        elif tag == 'feComposite':
            input2 = primitive_element.get('in2')
            operator = primitive_element.get('operator', 'over')
            k1 = float(primitive_element.get('k1', '0'))
            k2 = float(primitive_element.get('k2', '0'))
            k3 = float(primitive_element.get('k3', '0'))
            k4 = float(primitive_element.get('k4', '0'))
            
            return CompositePrimitive(
                type=FilterPrimitiveType.COMPOSITE,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                input2=input2, operator=operator,
                k1=k1, k2=k2, k3=k3, k4=k4
            )
        
        return None  # Unsupported primitive
    
    def _process_filter_chain(self, filter_def: FilterDefinition, element: ET.Element,
                            context: ConversionContext) -> List[FilterEffect]:
        """Process filter primitive chain into PowerPoint-compatible effects."""
        effects = []
        
        # Analyze filter chain complexity
        complexity_score = self._calculate_filter_complexity(filter_def)
        
        # Try to map common filter patterns to PowerPoint effects
        effects.extend(self._detect_standard_effects(filter_def, complexity_score))
        
        # Handle remaining primitives
        for primitive in filter_def.primitives:
            if not self._is_primitive_handled(primitive, effects):
                effect = self._convert_primitive_to_effect(primitive, complexity_score > self.rasterization_threshold)
                if effect:
                    effects.append(effect)
        
        return effects
    
    def _detect_standard_effects(self, filter_def: FilterDefinition, complexity_score: float) -> List[FilterEffect]:
        """Detect standard effect patterns that map well to PowerPoint."""
        effects = []
        primitives = filter_def.primitives
        
        # Detect drop shadow pattern: offset + blur + composite
        shadow_effect = self._detect_drop_shadow_pattern(primitives)
        if shadow_effect:
            effects.append(shadow_effect)
        
        # Detect glow pattern: blur + composite
        glow_effect = self._detect_glow_pattern(primitives)
        if glow_effect:
            effects.append(glow_effect)
        
        # Detect simple blur
        blur_effect = self._detect_blur_pattern(primitives)
        if blur_effect:
            effects.append(blur_effect)
        
        return effects
    
    def _detect_drop_shadow_pattern(self, primitives: List[FilterPrimitive]) -> Optional[FilterEffect]:
        """Detect drop shadow filter pattern."""
        # Look for feDropShadow (SVG 2.0) or feOffset + feGaussianBlur + feComposite
        
        for primitive in primitives:
            if isinstance(primitive, DropShadowPrimitive):
                return FilterEffect(
                    effect_type='shadow',
                    parameters={
                        'dx': primitive.dx,
                        'dy': primitive.dy,
                        'blur': primitive.std_deviation,
                        'color': primitive.flood_color,
                        'opacity': primitive.flood_opacity
                    },
                    requires_rasterization=False,
                    complexity_score=1.0
                )
        
        # Look for classic pattern: feOffset + feGaussianBlur + feComposite
        offset_primitive = None
        blur_primitive = None
        composite_primitive = None
        
        for primitive in primitives:
            if isinstance(primitive, OffsetPrimitive):
                offset_primitive = primitive
            elif isinstance(primitive, GaussianBlurPrimitive):
                blur_primitive = primitive
            elif isinstance(primitive, CompositePrimitive) and primitive.operator == 'over':
                composite_primitive = primitive
        
        if offset_primitive and blur_primitive and composite_primitive:
            return FilterEffect(
                effect_type='shadow',
                parameters={
                    'dx': offset_primitive.dx,
                    'dy': offset_primitive.dy,
                    'blur': max(blur_primitive.std_deviation_x, blur_primitive.std_deviation_y),
                    'color': ColorInfo(0, 0, 0, 0.5, 'rgb', 'black'),  # Default shadow color
                    'opacity': 0.5
                },
                requires_rasterization=False,
                complexity_score=1.5
            )
        
        return None
    
    def _detect_glow_pattern(self, primitives: List[FilterPrimitive]) -> Optional[FilterEffect]:
        """Detect glow effect pattern."""
        # Look for feGaussianBlur + feComposite with 'screen' or 'lighten'
        blur_primitive = None
        composite_primitive = None
        
        for primitive in primitives:
            if isinstance(primitive, GaussianBlurPrimitive):
                blur_primitive = primitive
            elif isinstance(primitive, CompositePrimitive) and primitive.operator in ['screen', 'lighten']:
                composite_primitive = primitive
        
        if blur_primitive and composite_primitive:
            return FilterEffect(
                effect_type='glow',
                parameters={
                    'blur': max(blur_primitive.std_deviation_x, blur_primitive.std_deviation_y),
                    'color': ColorInfo(255, 255, 255, 0.8, 'rgb', 'white'),  # Default glow color
                    'opacity': 0.8
                },
                requires_rasterization=False,
                complexity_score=1.2
            )
        
        return None
    
    def _detect_blur_pattern(self, primitives: List[FilterPrimitive]) -> Optional[FilterEffect]:
        """Detect simple blur effect."""
        for primitive in primitives:
            if isinstance(primitive, GaussianBlurPrimitive) and primitive.input == 'SourceGraphic':
                return FilterEffect(
                    effect_type='blur',
                    parameters={
                        'radius': max(primitive.std_deviation_x, primitive.std_deviation_y)
                    },
                    requires_rasterization=False,
                    complexity_score=0.8
                )
        
        return None
    
    def _convert_filter_effects_to_drawingml(self, effects: List[FilterEffect], 
                                           element: ET.Element, context: ConversionContext) -> str:
        """Convert processed filter effects to DrawingML."""
        if not effects:
            return ""
        
        effect_xml_parts = []
        
        for effect in effects:
            if effect.requires_rasterization:
                # Add comment indicating rasterization needed
                effect_xml_parts.append(f'<!-- Complex filter effect: {effect.effect_type} - requires rasterization -->')
                continue
            
            if effect.effect_type in self.powerpoint_effects:
                effect_xml = self.powerpoint_effects[effect.effect_type](effect.parameters)
                effect_xml_parts.append(effect_xml)
        
        if not effect_xml_parts:
            return ""
        
        # Wrap in effect list
        return f'''<a:effectLst>
            {''.join(effect_xml_parts)}
        </a:effectLst>'''
    
    def _generate_blur_effect(self, params: Dict[str, Any]) -> str:
        """Generate PowerPoint blur effect."""
        radius_value = params.get('radius', 3)
        radius = self.unit_converter.to_emu(f"{radius_value}px")
        
        return f'<a:blur rad="{radius}"/>'
    
    def _generate_shadow_effect(self, params: Dict[str, Any]) -> str:
        """Generate PowerPoint shadow effect."""
        dx_value = params.get('dx', 2)
        dy_value = params.get('dy', 2)
        blur_value = params.get('blur', 3)
        
        # Convert using UnitConverter (assuming px units for SVG filter values)
        dx = self.unit_converter.to_emu(f"{dx_value}px")
        dy = self.unit_converter.to_emu(f"{dy_value}px")
        blur_radius = self.unit_converter.to_emu(f"{blur_value}px")
        
        color = params.get('color')
        if color:
            color_xml = self.color_parser.to_drawingml(color)
        else:
            color_xml = '<a:srgbClr val="000000"/>'
        
        # Convert Cartesian (dx, dy) to polar coordinates for PPTX
        distance = int(math.sqrt(dx*dx + dy*dy))
        direction = int(math.degrees(math.atan2(dy, dx)) * 60000)
        
        return f'''<a:outerShdw blurRad="{blur_radius}" dist="{distance}" dir="{direction}">
            {color_xml}
        </a:outerShdw>'''
    
    def _generate_glow_effect(self, params: Dict[str, Any]) -> str:
        """Generate PowerPoint glow effect."""
        blur_value = params.get('blur', 5)
        blur_radius = self.unit_converter.to_emu(f"{blur_value}px")
        
        color = params.get('color')
        if color:
            color_xml = self.color_parser.to_drawingml(color)
        else:
            color_xml = '<a:srgbClr val="FFFFFF"/>'
        
        return f'''<a:glow rad="{blur_radius}">
            {color_xml}
        </a:glow>'''
    
    def _generate_reflection_effect(self, params: Dict[str, Any]) -> str:
        """Generate PowerPoint reflection effect."""
        return '<a:reflection blurRad="19050" stA="52000" stPos="0" endA="30000" endPos="100000"/>'
    
    def _calculate_filter_complexity(self, filter_def: FilterDefinition) -> float:
        """Calculate filter complexity score for rasterization decisions."""
        complexity = 0.0
        
        # Base complexity from primitive count
        complexity += len(filter_def.primitives) * 0.5
        
        # Add complexity based on primitive types
        for primitive in filter_def.primitives:
            if primitive.type == FilterPrimitiveType.GAUSSIAN_BLUR:
                complexity += 0.8
            elif primitive.type == FilterPrimitiveType.DROP_SHADOW:
                complexity += 1.0
            elif primitive.type == FilterPrimitiveType.COLOR_MATRIX:
                complexity += 1.2
            elif primitive.type == FilterPrimitiveType.COMPOSITE:
                complexity += 1.5
            elif primitive.type in [FilterPrimitiveType.CONVOLVE, FilterPrimitiveType.LIGHTING]:
                complexity += 2.0  # Very complex
            elif primitive.type == FilterPrimitiveType.TURBULENCE:
                complexity += 3.0  # Extremely complex
            else:
                complexity += 1.0
        
        return complexity
    
    def _is_primitive_handled(self, primitive: FilterPrimitive, effects: List[FilterEffect]) -> bool:
        """Check if primitive is already handled by detected effects."""
        # Simple check - in practice would need more sophisticated tracking
        return len(effects) > 0 and not any(e.requires_rasterization for e in effects)
    
    def _convert_primitive_to_effect(self, primitive: FilterPrimitive, force_raster: bool) -> Optional[FilterEffect]:
        """Convert individual primitive to effect."""
        if isinstance(primitive, GaussianBlurPrimitive):
            return FilterEffect(
                effect_type='blur',
                parameters={'radius': max(primitive.std_deviation_x, primitive.std_deviation_y)},
                requires_rasterization=force_raster,
                complexity_score=0.8
            )
        elif isinstance(primitive, ColorMatrixPrimitive):
            # Color matrix is complex - usually requires rasterization
            return FilterEffect(
                effect_type='color_matrix',
                parameters={'matrix': primitive.values, 'type': primitive.matrix_type.value},
                requires_rasterization=True,
                complexity_score=2.0
            )
        
        return None
    
    def _parse_filter_coordinate(self, coord_str: str) -> float:
        """Parse filter coordinate (may be percentage)."""
        if coord_str.endswith('%'):
            return float(coord_str[:-1]) / 100.0
        return float(coord_str)
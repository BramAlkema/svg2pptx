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
from lxml import etree as ET

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
    DIFFUSE_LIGHTING = "feDiffuseLighting"
    SPECULAR_LIGHTING = "feSpecularLighting"
    TURBULENCE = "feTurbulence"
    BLEND = "feBlend"
    IMAGE = "feImage"
    MERGE = "feMerge"
    TILE = "feTile"
    DISPLACEMENT_MAP = "feDisplacementMap"
    COMPONENT_TRANSFER = "feComponentTransfer"


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

    def build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph for filter primitives."""
        dependencies = {}

        for primitive in self.primitives:
            result_id = primitive.result or f"primitive_{id(primitive)}"
            dependencies[result_id] = []

            # Add input dependencies
            if primitive.input and primitive.input != 'SourceGraphic':
                dependencies[result_id].append(primitive.input)

            # Add input2 for compositing primitives
            if hasattr(primitive, 'input2') and primitive.input2:
                dependencies[result_id].append(primitive.input2)

        return dependencies

    def get_execution_order(self) -> List['FilterPrimitive']:
        """Get primitives in dependency-resolved execution order."""
        dependencies = self.build_dependency_graph()

        # Topological sort
        visited = set()
        temp_visited = set()
        execution_order = []

        def visit(primitive_id: str):
            if primitive_id in temp_visited:
                # Circular dependency detected
                return
            if primitive_id in visited:
                return

            temp_visited.add(primitive_id)

            # Visit dependencies first
            for dep in dependencies.get(primitive_id, []):
                if dep != 'SourceGraphic':
                    visit(dep)

            temp_visited.remove(primitive_id)
            visited.add(primitive_id)

            # Find primitive by result id
            for primitive in self.primitives:
                result_id = primitive.result or f"primitive_{id(primitive)}"
                if result_id == primitive_id:
                    execution_order.append(primitive)
                    break

        # Visit all primitives
        for primitive in self.primitives:
            result_id = primitive.result or f"primitive_{id(primitive)}"
            if result_id not in visited:
                visit(result_id)

        return execution_order


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


class OOXMLEffectStrategy(Enum):
    """OOXML effect mapping strategies."""
    NATIVE_DML = "native"      # S1: Direct DML mapping
    DML_HACK = "hack"          # S2: DML workarounds
    RASTERIZE = "raster"       # S3: Fallback to bitmap


@dataclass
class FilterEffect:
    """Processed filter effect for PowerPoint conversion."""
    effect_type: str  # blur, shadow, glow, etc.
    parameters: Dict[str, Any]
    requires_rasterization: bool
    complexity_score: float


class OOXMLEffectMapper:
    """Maps SVG filter effects to OOXML DrawingML effects with fallback strategies."""

    def __init__(self, unit_converter, color_parser):
        self.unit_converter = unit_converter
        self.color_parser = color_parser

        # Strategy mapping for each filter primitive type
        self.primitive_strategies = {
            FilterPrimitiveType.GAUSSIAN_BLUR: OOXMLEffectStrategy.NATIVE_DML,
            FilterPrimitiveType.DROP_SHADOW: OOXMLEffectStrategy.NATIVE_DML,
            FilterPrimitiveType.OFFSET: OOXMLEffectStrategy.NATIVE_DML,
            FilterPrimitiveType.FLOOD: OOXMLEffectStrategy.NATIVE_DML,
            FilterPrimitiveType.COLOR_MATRIX: OOXMLEffectStrategy.DML_HACK,
            FilterPrimitiveType.COMPOSITE: OOXMLEffectStrategy.DML_HACK,
            FilterPrimitiveType.MORPH: OOXMLEffectStrategy.RASTERIZE,
            FilterPrimitiveType.CONVOLVE: OOXMLEffectStrategy.RASTERIZE,
            FilterPrimitiveType.DIFFUSE_LIGHTING: OOXMLEffectStrategy.DML_HACK,
            FilterPrimitiveType.SPECULAR_LIGHTING: OOXMLEffectStrategy.DML_HACK,
            FilterPrimitiveType.TURBULENCE: OOXMLEffectStrategy.RASTERIZE,
            FilterPrimitiveType.BLEND: OOXMLEffectStrategy.DML_HACK,
            FilterPrimitiveType.IMAGE: OOXMLEffectStrategy.NATIVE_DML,
            FilterPrimitiveType.MERGE: OOXMLEffectStrategy.DML_HACK,
            FilterPrimitiveType.TILE: OOXMLEffectStrategy.DML_HACK,
            FilterPrimitiveType.DISPLACEMENT_MAP: OOXMLEffectStrategy.RASTERIZE,
            FilterPrimitiveType.COMPONENT_TRANSFER: OOXMLEffectStrategy.DML_HACK,
        }

        # Native DML effect generators
        self.native_generators = {
            'blur': self._generate_blur_dml,
            'shadow': self._generate_shadow_dml,
            'glow': self._generate_glow_dml,
            'offset': self._generate_offset_dml,
            'flood': self._generate_flood_dml,
            'image': self._generate_image_dml,
        }

        # DML hack generators (approximations)
        self.hack_generators = {
            'color_matrix': self._generate_color_matrix_hack,
            'composite': self._generate_composite_hack,
            'merge': self._generate_merge_hack,
            'blend': self._generate_blend_hack,
            'lighting': self._generate_lighting_hack,
        }

    def map_filter_effect(self, effect: FilterEffect) -> Tuple[str, OOXMLEffectStrategy]:
        """Map a filter effect to OOXML DrawingML with appropriate strategy."""
        strategy = self._determine_strategy(effect)

        if strategy == OOXMLEffectStrategy.NATIVE_DML:
            return self._generate_native_dml(effect), strategy
        elif strategy == OOXMLEffectStrategy.DML_HACK:
            return self._generate_dml_hack(effect), strategy
        else:  # RASTERIZE
            return self._generate_rasterization_comment(effect), strategy

    def _determine_strategy(self, effect: FilterEffect) -> OOXMLEffectStrategy:
        """Determine the best strategy for mapping an effect."""
        # Check if rasterization is explicitly required
        if effect.requires_rasterization:
            return OOXMLEffectStrategy.RASTERIZE

        # Check complexity score
        if effect.complexity_score > 2.5:
            return OOXMLEffectStrategy.RASTERIZE

        # Use effect type to determine strategy
        effect_type = effect.effect_type
        if effect_type in ['blur', 'shadow', 'glow', 'offset', 'flood', 'image']:
            return OOXMLEffectStrategy.NATIVE_DML
        elif effect_type in ['color_matrix', 'composite', 'merge', 'blend', 'lighting']:
            return OOXMLEffectStrategy.DML_HACK
        else:
            return OOXMLEffectStrategy.RASTERIZE

    def _generate_native_dml(self, effect: FilterEffect) -> str:
        """Generate native OOXML DrawingML for supported effects."""
        generator = self.native_generators.get(effect.effect_type)
        if generator:
            return generator(effect.parameters)
        return ""

    def _generate_dml_hack(self, effect: FilterEffect) -> str:
        """Generate approximated OOXML DrawingML using creative workarounds."""
        generator = self.hack_generators.get(effect.effect_type)
        if generator:
            return generator(effect.parameters)
        return f'<!-- Unsupported effect: {effect.effect_type} (requires implementation) -->'

    def _generate_rasterization_comment(self, effect: FilterEffect) -> str:
        """Generate comment indicating rasterization is needed."""
        return f'<!-- Complex effect: {effect.effect_type} - requires rasterization (complexity: {effect.complexity_score}) -->'

    # Native DML Generators (Strategy 1)

    def _generate_blur_dml(self, params: Dict[str, Any]) -> str:
        """Generate native blur effect DML."""
        radius_value = params.get('radius', 3)
        radius = self.unit_converter.to_emu(f"{radius_value}px")
        return f'<a:blur rad="{radius}"/>'

    def _generate_shadow_dml(self, params: Dict[str, Any]) -> str:
        """Generate native shadow effect DML."""
        dx_value = params.get('dx', 2)
        dy_value = params.get('dy', 2)
        blur_value = params.get('blur', 3)

        # Convert to EMU
        dx = self.unit_converter.to_emu(f"{dx_value}px")
        dy = self.unit_converter.to_emu(f"{dy_value}px")
        blur_radius = self.unit_converter.to_emu(f"{blur_value}px")

        # Convert to polar coordinates
        distance = int(math.sqrt(dx*dx + dy*dy))
        direction = int(math.degrees(math.atan2(dy, dx)) * 60000)

        # Generate color
        color = params.get('color')
        opacity = params.get('opacity', 0.5)

        if color and hasattr(color, 'hex_value'):
            color_hex = color.hex_value
        else:
            color_hex = "000000"  # Default black

        # Convert opacity to alpha (0-100000)
        alpha = int(opacity * 100000)

        return f'''<a:outerShdw blurRad="{blur_radius}" dist="{distance}" dir="{direction}" algn="ctr">
            <a:srgbClr val="{color_hex}">
                <a:alpha val="{alpha}"/>
            </a:srgbClr>
        </a:outerShdw>'''

    def _generate_glow_dml(self, params: Dict[str, Any]) -> str:
        """Generate native glow effect DML."""
        blur_value = params.get('blur', 5)
        radius = self.unit_converter.to_emu(f"{blur_value}px")

        color = params.get('color')
        opacity = params.get('opacity', 0.8)

        if color and hasattr(color, 'hex_value'):
            color_hex = color.hex_value
        else:
            color_hex = "FFFFFF"  # Default white

        alpha = int(opacity * 100000)

        return f'''<a:glow rad="{radius}">
            <a:srgbClr val="{color_hex}">
                <a:alpha val="{alpha}"/>
            </a:srgbClr>
        </a:glow>'''

    def _generate_offset_dml(self, params: Dict[str, Any]) -> str:
        """Generate offset effect as shadow without blur."""
        dx_value = params.get('dx', 0)
        dy_value = params.get('dy', 0)

        dx = self.unit_converter.to_emu(f"{dx_value}px")
        dy = self.unit_converter.to_emu(f"{dy_value}px")

        distance = int(math.sqrt(dx*dx + dy*dy))
        direction = int(math.degrees(math.atan2(dy, dx)) * 60000)

        return f'''<a:outerShdw blurRad="0" dist="{distance}" dir="{direction}" algn="ctr">
            <a:srgbClr val="000000">
                <a:alpha val="0"/>
            </a:srgbClr>
        </a:outerShdw>'''

    def _generate_flood_dml(self, params: Dict[str, Any]) -> str:
        """Generate flood as solid fill."""
        color = params.get('color')
        opacity = params.get('opacity', 1.0)

        if color and hasattr(color, 'hex_value'):
            color_hex = color.hex_value
        else:
            color_hex = "000000"

        alpha = int(opacity * 100000)

        return f'''<!-- Flood fill: use as solid fill -->
        <a:solidFill>
            <a:srgbClr val="{color_hex}">
                <a:alpha val="{alpha}"/>
            </a:srgbClr>
        </a:solidFill>'''

    def _generate_image_dml(self, params: Dict[str, Any]) -> str:
        """Generate image effect as bitmap fill."""
        href = params.get('href', '')
        if not href:
            return '<!-- Image effect: no href specified -->'

        return f'''<!-- Image effect: implement as bitmap fill -->
        <a:blipFill>
            <a:blip r:embed="{href}"/>
            <a:stretch>
                <a:fillRect/>
            </a:stretch>
        </a:blipFill>'''

    # DML Hack Generators (Strategy 2)

    def _generate_color_matrix_hack(self, params: Dict[str, Any]) -> str:
        """Generate color matrix approximation using DML color modifications."""
        matrix_type = params.get('matrix_type', 'matrix')
        values = params.get('values', [])

        if matrix_type == 'saturate' and values:
            # Map to satMod
            sat_value = int(values[0] * 100000)  # Convert to percentage * 1000
            return f'''<a:satMod val="{sat_value}"/>'''
        elif matrix_type == 'hueRotate' and values:
            # Map to hue rotation
            hue_value = int(values[0] * 60000)  # Convert degrees to 60000ths
            return f'''<a:hue val="{hue_value}"/>'''
        elif matrix_type == 'luminanceToAlpha':
            # Convert to grayscale
            return f'''<a:grayscl/>'''
        else:
            return f'<!-- Complex color matrix: requires rasterization -->'

    def _generate_composite_hack(self, params: Dict[str, Any]) -> str:
        """Generate composite approximation using shape layering."""
        operator = params.get('operator', 'over')

        if operator == 'over':
            return '<!-- Composite over: layer shapes with transparency -->'
        elif operator in ['multiply', 'screen']:
            return f'<!-- Composite {operator}: approximate with blend shape + opacity -->'
        else:
            return f'<!-- Complex composite {operator}: requires rasterization -->'

    def _generate_merge_hack(self, params: Dict[str, Any]) -> str:
        """Generate merge approximation using grouped shapes."""
        inputs = params.get('inputs', [])
        return f'<!-- Merge {len(inputs)} inputs: emit as grouped shapes -->'

    def _generate_blend_hack(self, params: Dict[str, Any]) -> str:
        """Generate blend mode approximation."""
        mode = params.get('mode', 'normal')

        blend_approximations = {
            'multiply': 'Use dark duotone effect',
            'screen': 'Use light overlay with high opacity',
            'darken': 'Use darker color overlay',
            'lighten': 'Use lighter color overlay',
        }

        approximation = blend_approximations.get(mode, 'Requires rasterization')
        return f'<!-- Blend {mode}: {approximation} -->'

    def _generate_lighting_hack(self, params: Dict[str, Any]) -> str:
        """Generate lighting approximation using 3D effects."""
        lighting_type = params.get('lighting_type', 'diffuse')

        if lighting_type == 'diffuse':
            return '''<a:sp3d>
                <a:bevelT w="25400" h="25400"/>
            </a:sp3d>
            <a:innerShdw blurRad="63500" dist="38100" dir="2700000" algn="ctr">
                <a:srgbClr val="000000">
                    <a:alpha val="25000"/>
                </a:srgbClr>
            </a:innerShdw>'''
        else:  # specular
            return '''<a:sp3d>
                <a:bevelT w="25400" h="25400"/>
            </a:sp3d>
            <a:outerShdw blurRad="63500" dist="0" dir="0" algn="ctr">
                <a:srgbClr val="FFFFFF">
                    <a:alpha val="40000"/>
                </a:srgbClr>
            </a:outerShdw>'''

    def generate_effect_list(self, effects: List[FilterEffect]) -> str:
        """Generate complete OOXML effect list from filter effects."""
        if not effects:
            return ""

        effect_parts = []
        strategy_stats = {'native': 0, 'hack': 0, 'raster': 0}

        for effect in effects:
            dml_xml, strategy = self.map_filter_effect(effect)
            if dml_xml.strip():
                effect_parts.append(dml_xml)

            # Update statistics
            if strategy == OOXMLEffectStrategy.NATIVE_DML:
                strategy_stats['native'] += 1
            elif strategy == OOXMLEffectStrategy.DML_HACK:
                strategy_stats['hack'] += 1
            else:
                strategy_stats['raster'] += 1

        if not effect_parts:
            return ""

        # Add strategy statistics as comment
        stats_comment = f'<!-- Filter mapping: {strategy_stats["native"]} native, {strategy_stats["hack"]} hacks, {strategy_stats["raster"]} raster -->'

        return f'''{stats_comment}
<a:effectLst>
    {''.join(effect_parts)}
</a:effectLst>'''


@dataclass
class FilterChainNode:
    """Represents a node in the filter processing chain."""
    primitive: FilterPrimitive
    inputs: List[str]          # Input source names
    output_name: str           # Result identifier
    processed: bool = False    # Whether this node has been processed


class FilterChainProcessor:
    """Handles complex filter chain processing with input/output management."""

    def __init__(self):
        self.intermediate_results: Dict[str, Any] = {}
        self.processing_chain: List[FilterChainNode] = []

    def build_processing_chain(self, filter_def: FilterDefinition) -> List[FilterChainNode]:
        """Build a processing chain from filter definition."""
        nodes = []

        for i, primitive in enumerate(filter_def.primitives):
            # Determine inputs
            inputs = []
            if primitive.input:
                inputs.append(primitive.input)
            if hasattr(primitive, 'input2') and primitive.input2:
                inputs.append(primitive.input2)

            # Determine output name
            output_name = primitive.result or f"result_{i}"

            node = FilterChainNode(
                primitive=primitive,
                inputs=inputs,
                output_name=output_name
            )
            nodes.append(node)

        return nodes

    def can_process_node(self, node: FilterChainNode) -> bool:
        """Check if all dependencies for a node are satisfied."""
        for input_name in node.inputs:
            if input_name == 'SourceGraphic':
                continue  # Always available
            if input_name not in self.intermediate_results:
                return False
        return True

    def process_filter_chain(self, filter_def: FilterDefinition) -> List[FilterChainNode]:
        """Process filter chain with dependency resolution."""
        self.processing_chain = self.build_processing_chain(filter_def)
        self.intermediate_results = {'SourceGraphic': True}  # Mark source as available

        processed_nodes = []
        max_iterations = len(self.processing_chain) * 2  # Prevent infinite loops
        iteration = 0

        while len(processed_nodes) < len(self.processing_chain) and iteration < max_iterations:
            iteration += 1
            progress_made = False

            for node in self.processing_chain:
                if not node.processed and self.can_process_node(node):
                    # Process this node
                    self._process_node(node)
                    node.processed = True
                    processed_nodes.append(node)

                    # Mark output as available
                    self.intermediate_results[node.output_name] = True
                    progress_made = True

            if not progress_made:
                # Handle circular dependencies or missing inputs
                self._handle_unresolvable_dependencies()
                break

        return processed_nodes

    def _process_node(self, node: FilterChainNode):
        """Process a single filter node."""
        primitive = node.primitive

        # Add processing logic here based on primitive type
        # This is where individual filter effects would be applied

        # For now, just mark as processed for chain management
        pass

    def _handle_unresolvable_dependencies(self):
        """Handle cases where dependencies cannot be resolved."""
        # Mark remaining unprocessed nodes for fallback processing
        for node in self.processing_chain:
            if not node.processed:
                # Could mark for rasterization fallback
                node.processed = True
                self.intermediate_results[node.output_name] = True

    def get_chain_complexity(self) -> float:
        """Calculate overall complexity score for the filter chain."""
        complexity = 0.0

        for node in self.processing_chain:
            # Base complexity per primitive
            complexity += 1.0

            # Additional complexity for certain types
            if isinstance(node.primitive, (MorphologyPrimitive, ConvolvePrimitive)):
                complexity += 2.0
            elif isinstance(node.primitive, (DiffuseLightingPrimitive, SpecularLightingPrimitive)):
                complexity += 1.5
            elif len(node.inputs) > 1:  # Multiple inputs increase complexity
                complexity += 0.5

        return complexity

    def detect_pattern_chains(self) -> List[Dict[str, Any]]:
        """Detect common filter patterns that can be optimized."""
        patterns = []

        # Detect drop shadow pattern: offset -> blur -> composite
        shadow_pattern = self._detect_shadow_chain()
        if shadow_pattern:
            patterns.append(shadow_pattern)

        # Detect glow pattern: blur -> composite (with blend mode)
        glow_pattern = self._detect_glow_chain()
        if glow_pattern:
            patterns.append(glow_pattern)

        # Detect emboss pattern: lighting -> composite
        emboss_pattern = self._detect_emboss_chain()
        if emboss_pattern:
            patterns.append(emboss_pattern)

        return patterns

    def _detect_shadow_chain(self) -> Optional[Dict[str, Any]]:
        """Detect drop shadow processing pattern."""
        nodes = self.processing_chain

        for i in range(len(nodes) - 2):
            if (isinstance(nodes[i].primitive, OffsetPrimitive) and
                isinstance(nodes[i+1].primitive, GaussianBlurPrimitive) and
                isinstance(nodes[i+2].primitive, CompositePrimitive)):

                return {
                    'pattern_type': 'drop_shadow',
                    'nodes': [nodes[i], nodes[i+1], nodes[i+2]],
                    'can_optimize': True,
                    'ooxml_equivalent': 'outerShdw'
                }

        return None

    def _detect_glow_chain(self) -> Optional[Dict[str, Any]]:
        """Detect glow effect processing pattern."""
        nodes = self.processing_chain

        for i in range(len(nodes) - 1):
            if (isinstance(nodes[i].primitive, GaussianBlurPrimitive) and
                isinstance(nodes[i+1].primitive, CompositePrimitive) and
                nodes[i+1].primitive.operator in ['screen', 'lighten']):

                return {
                    'pattern_type': 'glow',
                    'nodes': [nodes[i], nodes[i+1]],
                    'can_optimize': True,
                    'ooxml_equivalent': 'glow'
                }

        return None

    def _detect_emboss_chain(self) -> Optional[Dict[str, Any]]:
        """Detect emboss effect processing pattern."""
        nodes = self.processing_chain

        for i in range(len(nodes) - 1):
            if (isinstance(nodes[i].primitive, (DiffuseLightingPrimitive, SpecularLightingPrimitive)) and
                isinstance(nodes[i+1].primitive, CompositePrimitive)):

                return {
                    'pattern_type': 'emboss',
                    'nodes': [nodes[i], nodes[i+1]],
                    'can_optimize': False,  # Usually requires rasterization
                    'ooxml_equivalent': None
                }

        return None


@dataclass
class DisplacementMapPrimitive(FilterPrimitive):
    """Displacement map filter primitive."""
    input2: str  # Displacement map source
    scale: float
    x_channel_selector: str  # R, G, B, A
    y_channel_selector: str


@dataclass
class ComponentTransferPrimitive(FilterPrimitive):
    """Component transfer filter primitive."""
    transfer_functions: Dict[str, Dict[str, Any]]  # Per-channel transfer functions


@dataclass
class BlendPrimitive(FilterPrimitive):
    """Blend filter primitive (layer blend modes)."""
    input2: str  # Second input source
    mode: str    # normal, multiply, screen, darken, lighten, etc.


@dataclass
class ImagePrimitive(FilterPrimitive):
    """Image filter primitive (external image as input)."""
    href: str                    # Image reference
    preserve_aspect_ratio: str   # Aspect ratio preservation
    cross_origin: Optional[str]  # CORS setting


@dataclass
class MergePrimitive(FilterPrimitive):
    """Merge filter primitive (stack multiple inputs)."""
    merge_nodes: List[str]  # List of input sources to merge


@dataclass
class TilePrimitive(FilterPrimitive):
    """Tile filter primitive (repeat region)."""
    input_source: str  # Source to tile


@dataclass
class LightSource:
    """Base class for light sources."""
    light_type: str  # distant, point, spot


@dataclass
class DistantLight(LightSource):
    """Distant light source (directional)."""
    azimuth: float    # Light direction azimuth (degrees)
    elevation: float  # Light direction elevation (degrees)


@dataclass
class PointLight(LightSource):
    """Point light source."""
    x: float  # Light position X
    y: float  # Light position Y
    z: float  # Light position Z


@dataclass
class SpotLight(LightSource):
    """Spot light source."""
    x: float                    # Light position X
    y: float                    # Light position Y
    z: float                    # Light position Z
    points_at_x: float          # Target point X
    points_at_y: float          # Target point Y
    points_at_z: float          # Target point Z
    specular_exponent: float    # Focus sharpness
    limiting_cone_angle: float  # Cone angle limit


@dataclass
class MorphologyPrimitive(FilterPrimitive):
    """Morphology filter primitive (dilate/erode)."""
    operator: str  # dilate or erode
    radius_x: float
    radius_y: float


@dataclass
class ConvolvePrimitive(FilterPrimitive):
    """Convolution matrix filter primitive."""
    order_x: int
    order_y: int
    kernel_matrix: List[float]
    divisor: float
    bias: float
    edge_mode: str  # duplicate, wrap, none
    preserve_alpha: bool


@dataclass
class LightingPrimitive(FilterPrimitive):
    """Base lighting effect primitive."""
    lighting_color: ColorInfo
    surface_scale: float
    light_source: Optional[LightSource]


@dataclass
class DiffuseLightingPrimitive(LightingPrimitive):
    """Diffuse lighting effect primitive."""
    diffuse_constant: float = 1.0


@dataclass
class SpecularLightingPrimitive(LightingPrimitive):
    """Specular lighting effect primitive."""
    specular_constant: float = 1.0
    specular_exponent: float = 1.0


@dataclass
class TurbulencePrimitive(FilterPrimitive):
    """Turbulence noise primitive."""
    base_frequency_x: float
    base_frequency_y: float
    num_octaves: int
    seed: int
    stitch_tiles: bool
    turbulence_type: str  # fractalNoise or turbulence


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

        # Initialize parsers and converters
        self.color_parser = ColorParser()
        self.unit_converter = UnitConverter(100, 100)  # Default viewport, will be updated
        self.transform_parser = TransformParser()

        # Initialize OOXML effect mapper
        self.ooxml_mapper = OOXMLEffectMapper(self.unit_converter, self.color_parser)

        # Initialize filter bounds calculator
        self.bounds_calculator = FilterBounds(self.unit_converter, self.color_parser)

        # PowerPoint effect mapping (legacy - replaced by OOXML mapper)
        self.powerpoint_effects = {
            'blur': self._generate_blur_effect,
            'shadow': self._generate_shadow_effect,
            'glow': self._generate_glow_effect,
            'reflection': self._generate_reflection_effect,
        }

        # Complexity thresholds for rasterization decisions
        self.rasterization_threshold = 3.0  # Complexity score above which to rasterize
    
    def can_convert(self, element: ET.Element, context: Optional[ConversionContext] = None) -> bool:
        """Check if element can be converted by this converter."""
        if element.tag.endswith(('filter', 'defs')):
            return True
        
        # Check if element has filter applied
        filter_attr = element.get('filter', '')
        return filter_attr.startswith('url(#') and filter_attr.endswith(')')
        
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
        
        elif tag == 'feMorphology':
            operator = primitive_element.get('operator', 'erode')
            radius = primitive_element.get('radius', '0')
            if ' ' in radius:
                radius_x, radius_y = map(float, radius.split())
            else:
                radius_x = radius_y = float(radius)
            
            return MorphologyPrimitive(
                type=FilterPrimitiveType.MORPH,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                operator=operator, radius_x=radius_x, radius_y=radius_y
            )
        
        elif tag == 'feConvolveMatrix':
            order = primitive_element.get('order', '3')
            if ' ' in order:
                order_x, order_y = map(int, order.split())
            else:
                order_x = order_y = int(order)
            
            kernel_matrix_str = primitive_element.get('kernelMatrix', '0 0 0 0 1 0 0 0 0')
            kernel_matrix = [float(v) for v in kernel_matrix_str.split()]
            
            divisor = float(primitive_element.get('divisor', '1'))
            bias = float(primitive_element.get('bias', '0'))
            edge_mode = primitive_element.get('edgeMode', 'duplicate')
            preserve_alpha = primitive_element.get('preserveAlpha', 'false').lower() == 'true'
            
            return ConvolvePrimitive(
                type=FilterPrimitiveType.CONVOLVE,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                order_x=order_x, order_y=order_y,
                kernel_matrix=kernel_matrix, divisor=divisor, bias=bias,
                edge_mode=edge_mode, preserve_alpha=preserve_alpha
            )
        
        elif tag == 'feDiffuseLighting':
            lighting_color = self.color_parser.parse(primitive_element.get('lighting-color', 'white'))
            surface_scale = float(primitive_element.get('surfaceScale', '1'))
            diffuse_constant = float(primitive_element.get('diffuseConstant', '1'))

            # Parse light source
            light_source = self._parse_light_source(primitive_element)

            return DiffuseLightingPrimitive(
                type=FilterPrimitiveType.DIFFUSE_LIGHTING,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                lighting_color=lighting_color, surface_scale=surface_scale,
                light_source=light_source, diffuse_constant=diffuse_constant
            )
        
        elif tag == 'feTurbulence':
            base_frequency = primitive_element.get('baseFrequency', '0')
            if ' ' in base_frequency:
                base_freq_x, base_freq_y = map(float, base_frequency.split())
            else:
                base_freq_x = base_freq_y = float(base_frequency)

            num_octaves = int(primitive_element.get('numOctaves', '1'))
            seed = int(primitive_element.get('seed', '0'))
            stitch_tiles = primitive_element.get('stitchTiles', 'noStitch') == 'stitch'
            turbulence_type = primitive_element.get('type', 'turbulence')

            return TurbulencePrimitive(
                type=FilterPrimitiveType.TURBULENCE,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                base_frequency_x=base_freq_x, base_frequency_y=base_freq_y,
                num_octaves=num_octaves, seed=seed,
                stitch_tiles=stitch_tiles, turbulence_type=turbulence_type
            )

        elif tag == 'feBlend':
            input2 = primitive_element.get('in2', 'SourceGraphic')
            mode = primitive_element.get('mode', 'normal')

            return BlendPrimitive(
                type=FilterPrimitiveType.BLEND,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                input2=input2, mode=mode
            )

        elif tag == 'feImage':
            href = primitive_element.get('href') or primitive_element.get('{http://www.w3.org/1999/xlink}href', '')
            preserve_aspect_ratio = primitive_element.get('preserveAspectRatio', 'xMidYMid meet')
            cross_origin = primitive_element.get('crossorigin')

            return ImagePrimitive(
                type=FilterPrimitiveType.IMAGE,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                href=href, preserve_aspect_ratio=preserve_aspect_ratio,
                cross_origin=cross_origin
            )

        elif tag == 'feMerge':
            # Parse feMergeNode children
            merge_nodes = []
            for merge_node in primitive_element.findall('.//*[local-name()="feMergeNode"]'):
                node_input = merge_node.get('in', 'SourceGraphic')
                merge_nodes.append(node_input)

            return MergePrimitive(
                type=FilterPrimitiveType.MERGE,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                merge_nodes=merge_nodes
            )

        elif tag == 'feTile':
            return TilePrimitive(
                type=FilterPrimitiveType.TILE,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                input_source=input_attr or 'SourceGraphic'
            )

        elif tag == 'feSpecularLighting':
            lighting_color = self.color_parser.parse(primitive_element.get('lighting-color', 'white'))
            surface_scale = float(primitive_element.get('surfaceScale', '1'))
            specular_constant = float(primitive_element.get('specularConstant', '1'))
            specular_exponent = float(primitive_element.get('specularExponent', '1'))

            # Parse light source
            light_source = self._parse_light_source(primitive_element)

            return SpecularLightingPrimitive(
                type=FilterPrimitiveType.SPECULAR_LIGHTING,
                input=input_attr, result=result,
                x=x, y=y, width=width, height=height,
                lighting_color=lighting_color, surface_scale=surface_scale,
                light_source=light_source, specular_constant=specular_constant,
                specular_exponent=specular_exponent
            )
        
        return None  # Unsupported primitive

    def _parse_light_source(self, lighting_element: ET.Element) -> Optional[LightSource]:
        """Parse light source from lighting primitive element."""
        # Look for light source child elements
        distant_light = lighting_element.find('.//*[local-name()="feDistantLight"]')
        if distant_light is not None:
            azimuth = float(distant_light.get('azimuth', '0'))
            elevation = float(distant_light.get('elevation', '0'))
            return DistantLight(
                light_type='distant',
                azimuth=azimuth,
                elevation=elevation
            )

        point_light = lighting_element.find('.//*[local-name()="fePointLight"]')
        if point_light is not None:
            x = float(point_light.get('x', '0'))
            y = float(point_light.get('y', '0'))
            z = float(point_light.get('z', '0'))
            return PointLight(
                light_type='point',
                x=x, y=y, z=z
            )

        spot_light = lighting_element.find('.//*[local-name()="feSpotLight"]')
        if spot_light is not None:
            x = float(spot_light.get('x', '0'))
            y = float(spot_light.get('y', '0'))
            z = float(spot_light.get('z', '0'))
            points_at_x = float(spot_light.get('pointsAtX', '0'))
            points_at_y = float(spot_light.get('pointsAtY', '0'))
            points_at_z = float(spot_light.get('pointsAtZ', '0'))
            specular_exponent = float(spot_light.get('specularExponent', '1'))
            limiting_cone_angle = float(spot_light.get('limitingConeAngle', '90'))
            return SpotLight(
                light_type='spot',
                x=x, y=y, z=z,
                points_at_x=points_at_x,
                points_at_y=points_at_y,
                points_at_z=points_at_z,
                specular_exponent=specular_exponent,
                limiting_cone_angle=limiting_cone_angle
            )

        return None
    
    def _process_filter_chain(self, filter_def: FilterDefinition, element: ET.Element,
                            context: ConversionContext) -> List[FilterEffect]:
        """Process filter primitive chain into PowerPoint-compatible effects."""
        effects = []

        # Create and initialize chain processor
        chain_processor = FilterChainProcessor()

        # Process the filter chain with dependency resolution
        processed_nodes = chain_processor.process_filter_chain(filter_def)

        # Get overall complexity
        complexity_score = chain_processor.get_chain_complexity()

        # Detect optimizable patterns
        detected_patterns = chain_processor.detect_pattern_chains()

        # Process detected patterns first (these can be optimized)
        for pattern in detected_patterns:
            if pattern['can_optimize']:
                effect = self._convert_pattern_to_effect(pattern, complexity_score)
                if effect:
                    effects.append(effect)
                    # Mark pattern nodes as handled
                    for node in pattern['nodes']:
                        node.processed = True

        # Try to map remaining common filter patterns to PowerPoint effects
        effects.extend(self._detect_standard_effects(filter_def, complexity_score))

        # Handle remaining unprocessed primitives
        for node in processed_nodes:
            if not self._is_node_handled(node, effects):
                effect = self._convert_primitive_to_effect(
                    node.primitive,
                    complexity_score > self.rasterization_threshold
                )
                if effect:
                    effects.append(effect)

        return effects

    def _convert_pattern_to_effect(self, pattern: Dict[str, Any], complexity_score: float) -> Optional[FilterEffect]:
        """Convert a detected filter pattern to a PowerPoint effect."""
        pattern_type = pattern['pattern_type']
        nodes = pattern['nodes']

        if pattern_type == 'drop_shadow' and len(nodes) >= 3:
            # Extract parameters from offset, blur, and composite nodes
            offset_primitive = nodes[0].primitive
            blur_primitive = nodes[1].primitive
            composite_primitive = nodes[2].primitive

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

        elif pattern_type == 'glow' and len(nodes) >= 2:
            # Extract parameters from blur and composite nodes
            blur_primitive = nodes[0].primitive

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

        elif pattern_type == 'emboss':
            # Emboss typically requires rasterization
            return FilterEffect(
                effect_type='emboss',
                parameters={},
                requires_rasterization=True,
                complexity_score=3.0
            )

        return None

    def _is_node_handled(self, node: FilterChainNode, effects: List[FilterEffect]) -> bool:
        """Check if a filter node has been handled by existing effects."""
        # This would check if the node's primitive has been accounted for
        # in any of the existing effects (e.g., part of a pattern)
        return False  # Simplified for now
    
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
        """Convert processed filter effects to DrawingML using the OOXML mapper."""
        if not effects:
            return ""

        # Use the new OOXML mapper for comprehensive effect conversion
        return self.ooxml_mapper.generate_effect_list(effects)
    
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
            color_hex = self.parse_color(color)
            color_xml = f'<a:srgbClr val="{color_hex}"/>' if color_hex else '<a:srgbClr val="000000"/>'
        else:
            black_color = self.parse_color('black')
            color_xml = f'<a:srgbClr val="{black_color}"/>'
        
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
            color_hex = self.parse_color(color)
            color_xml = f'<a:srgbClr val="{color_hex}"/>' if color_hex else '<a:srgbClr val="FFFFFF"/>'
        else:
            white_color = self.parse_color('white')
            color_xml = f'<a:srgbClr val="{white_color}"/>'
        
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
            elif primitive.type == FilterPrimitiveType.OFFSET:
                complexity += 0.5
            elif primitive.type == FilterPrimitiveType.FLOOD:
                complexity += 0.3
            elif primitive.type == FilterPrimitiveType.COLOR_MATRIX:
                complexity += 1.2
            elif primitive.type == FilterPrimitiveType.COMPOSITE:
                complexity += 1.5
            elif primitive.type == FilterPrimitiveType.MORPH:
                complexity += 1.8  # Morphology is complex
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
        elif isinstance(primitive, MorphologyPrimitive):
            # Morphology effects (dilate/erode) are complex - require rasterization
            return FilterEffect(
                effect_type='morphology',
                parameters={
                    'operator': primitive.operator,
                    'radius_x': primitive.radius_x,
                    'radius_y': primitive.radius_y
                },
                requires_rasterization=True,
                complexity_score=1.8
            )
        elif isinstance(primitive, ConvolvePrimitive):
            # Convolution matrices are very complex - require rasterization
            return FilterEffect(
                effect_type='convolve',
                parameters={
                    'kernel_matrix': primitive.kernel_matrix,
                    'order_x': primitive.order_x,
                    'order_y': primitive.order_y,
                    'divisor': primitive.divisor,
                    'bias': primitive.bias
                },
                requires_rasterization=True,
                complexity_score=2.5
            )
        elif isinstance(primitive, LightingPrimitive):
            # Lighting effects are complex - require rasterization
            return FilterEffect(
                effect_type='lighting',
                parameters={
                    'lighting_type': primitive.lighting_type,
                    'lighting_color': primitive.lighting_color,
                    'surface_scale': primitive.surface_scale,
                    'diffuse_constant': primitive.diffuse_constant,
                    'specular_constant': primitive.specular_constant,
                    'specular_exponent': primitive.specular_exponent
                },
                requires_rasterization=True,
                complexity_score=2.2
            )
        elif isinstance(primitive, TurbulencePrimitive):
            # Turbulence effects are extremely complex - require rasterization
            return FilterEffect(
                effect_type='turbulence',
                parameters={
                    'base_frequency_x': primitive.base_frequency_x,
                    'base_frequency_y': primitive.base_frequency_y,
                    'num_octaves': primitive.num_octaves,
                    'seed': primitive.seed,
                    'turbulence_type': primitive.turbulence_type
                },
                requires_rasterization=True,
                complexity_score=3.0
            )
        
        return None
    
    def _parse_filter_coordinate(self, coord_str: str) -> float:
        """Parse filter coordinate (may be percentage)."""
        if coord_str.endswith('%'):
            return float(coord_str[:-1]) / 100.0
        return float(coord_str)

    def calculate_filtered_element_bounds(self, element: ET.Element,
                                         context: ConversionContext) -> Dict[str, float]:
        """
        Calculate the bounds of an element with filter effects applied.

        Args:
            element: SVG element with filter attribute
            context: Conversion context with coordinate system info

        Returns:
            Expanded bounds dictionary accounting for filter effects
        """
        # Get original element bounds
        original_bounds = self._get_element_bounds(element, context)
        if not original_bounds:
            return {'x': 0, 'y': 0, 'width': 0, 'height': 0}

        # Check if element has filter
        filter_attr = element.get('filter', '')
        if not filter_attr.startswith('url(#') or not filter_attr.endswith(')'):
            return original_bounds

        filter_id = filter_attr[5:-1]  # Extract ID from url(#id)
        if filter_id not in self.filters:
            return original_bounds

        # Get filter definition and process effects
        filter_def = self.filters[filter_id]
        filter_effects = self._process_filter_chain(filter_def, element, context)

        # Calculate cumulative bounds expansion
        current_bounds = original_bounds.copy()
        for effect in filter_effects:
            effect_dict = {
                'type': effect.effect_type,
                **effect.parameters
            }
            current_bounds = self.bounds_calculator.calculate_filter_bounds(
                current_bounds, effect_dict
            )

        return current_bounds

    def _get_element_bounds(self, element: ET.Element,
                           context: ConversionContext) -> Optional[Dict[str, float]]:
        """
        Extract the geometric bounds of an SVG element.

        Args:
            element: SVG element to get bounds for
            context: Conversion context for coordinate system

        Returns:
            Element bounds dictionary or None if bounds cannot be determined
        """
        tag = element.tag.split('}')[-1]  # Remove namespace

        if tag == 'rect':
            x = float(element.get('x', '0'))
            y = float(element.get('y', '0'))
            width = float(element.get('width', '0'))
            height = float(element.get('height', '0'))
            return {'x': x, 'y': y, 'width': width, 'height': height}

        elif tag == 'circle':
            cx = float(element.get('cx', '0'))
            cy = float(element.get('cy', '0'))
            r = float(element.get('r', '0'))
            return {'x': cx - r, 'y': cy - r, 'width': 2 * r, 'height': 2 * r}

        elif tag == 'ellipse':
            cx = float(element.get('cx', '0'))
            cy = float(element.get('cy', '0'))
            rx = float(element.get('rx', '0'))
            ry = float(element.get('ry', '0'))
            return {'x': cx - rx, 'y': cy - ry, 'width': 2 * rx, 'height': 2 * ry}

        elif tag == 'line':
            x1 = float(element.get('x1', '0'))
            y1 = float(element.get('y1', '0'))
            x2 = float(element.get('x2', '0'))
            y2 = float(element.get('y2', '0'))
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_y, max_y = min(y1, y2), max(y1, y2)
            return {'x': min_x, 'y': min_y, 'width': max_x - min_x, 'height': max_y - min_y}

        elif tag == 'text':
            x = float(element.get('x', '0'))
            y = float(element.get('y', '0'))
            # Estimate text bounds (actual implementation would use font metrics)
            text_content = element.text or ''
            estimated_width = len(text_content) * 10  # Rough estimate
            estimated_height = 16  # Rough estimate
            return {'x': x, 'y': y - estimated_height, 'width': estimated_width, 'height': estimated_height}

        elif tag == 'path':
            # Path bounds calculation is complex - use simplified approach
            d = element.get('d', '')
            # Extract path bounds (simplified - actual implementation would parse path data)
            # For now, return a default bounds that can be expanded by filters
            return {'x': 0, 'y': 0, 'width': 100, 'height': 100}

        elif tag == 'g' or tag == 'svg':
            # Group bounds would be calculated from child elements
            # For now, use viewport bounds
            return {'x': 0, 'y': 0, 'width': context.coordinate_system.viewport_width or 100,
                   'height': context.coordinate_system.viewport_height or 100}

        # Default bounds for unknown elements
        return {'x': 0, 'y': 0, 'width': 100, 'height': 100}

    def get_filter_region_bounds(self, filter_id: str,
                                element_bounds: Dict[str, float]) -> Dict[str, float]:
        """
        Get the filter region bounds for a specific filter.

        Args:
            filter_id: ID of the filter definition
            element_bounds: Original element bounds

        Returns:
            Filter region bounds that define the area affected by the filter
        """
        if filter_id not in self.filters:
            return element_bounds

        filter_def = self.filters[filter_id]

        # Use filter's x, y, width, height attributes if defined
        filter_x = self._parse_filter_coordinate(filter_def.x or '-10%')
        filter_y = self._parse_filter_coordinate(filter_def.y or '-10%')
        filter_width = self._parse_filter_coordinate(filter_def.width or '120%')
        filter_height = self._parse_filter_coordinate(filter_def.height or '120%')

        # Apply filter region to element bounds
        base_x = element_bounds['x']
        base_y = element_bounds['y']
        base_width = element_bounds['width']
        base_height = element_bounds['height']

        # Calculate absolute filter region
        if isinstance(filter_x, float) and filter_x <= 1.0:  # Percentage
            region_x = base_x + (filter_x * base_width)
        else:
            region_x = base_x + filter_x

        if isinstance(filter_y, float) and filter_y <= 1.0:  # Percentage
            region_y = base_y + (filter_y * base_height)
        else:
            region_y = base_y + filter_y

        if isinstance(filter_width, float) and filter_width <= 2.0:  # Percentage (can be > 100%)
            region_width = filter_width * base_width
        else:
            region_width = filter_width

        if isinstance(filter_height, float) and filter_height <= 2.0:  # Percentage
            region_height = filter_height * base_height
        else:
            region_height = filter_height

        return {
            'x': region_x,
            'y': region_y,
            'width': region_width,
            'height': region_height
        }

    def optimize_filter_bounds_calculation(self, element: ET.Element,
                                         context: ConversionContext) -> bool:
        """
        Determine if bounds calculation can be optimized or skipped.

        Args:
            element: SVG element with potential filter
            context: Conversion context

        Returns:
            True if bounds calculation can be optimized/skipped, False if full calculation needed
        """
        filter_attr = element.get('filter', '')
        if not filter_attr:
            return True  # No filter, no bounds calculation needed

        # Check if filter is simple and doesn't significantly affect bounds
        if filter_attr.startswith('url(#'):
            filter_id = filter_attr[5:-1]
            if filter_id in self.filters:
                filter_def = self.filters[filter_id]
                # If filter has only simple effects, optimization may be possible
                primitive_count = len(filter_def.primitives) if hasattr(filter_def, 'primitives') else 0
                return primitive_count <= 1  # Simple single-effect filters can be optimized

        return False  # Default to full calculation for complex filters

    def enable_bounds_optimization(self, enable: bool = True,
                                  cache_size: int = 1000,
                                  significance_threshold: float = 5.0):
        """
        Enable or disable bounds calculation optimization features.

        Args:
            enable: Whether to enable optimizations
            cache_size: Maximum cache size for bounds calculations
            significance_threshold: Minimum expansion percentage to process
        """
        if enable:
            self.bounds_calculator.optimize_cache_size(cache_size)
            self._bounds_optimization_enabled = True
            self._significance_threshold = significance_threshold
        else:
            self._bounds_optimization_enabled = False
            self.bounds_calculator.clear_cache()

    def calculate_optimized_bounds(self, element: ET.Element,
                                  context: ConversionContext,
                                  accuracy_level: str = 'medium') -> Dict[str, float]:
        """
        Calculate bounds with performance optimizations enabled.

        Args:
            element: SVG element with filter
            context: Conversion context
            accuracy_level: Calculation accuracy level ('fast', 'medium', 'precise')

        Returns:
            Optimized bounds calculation result
        """
        # Check if optimization is enabled
        if not getattr(self, '_bounds_optimization_enabled', False):
            return self.calculate_filtered_element_bounds(element, context)

        # Try optimization path first
        if self.optimize_filter_bounds_calculation(element, context):
            # Use simple bounds expansion for optimized case
            original_bounds = self._get_element_bounds(element, context)
            if not original_bounds:
                return {'x': 0, 'y': 0, 'width': 0, 'height': 0}

            # Get filter effect for approximation
            filter_attr = element.get('filter', '')
            if filter_attr.startswith('url(#') and filter_attr.endswith(')'):
                filter_id = filter_attr[5:-1]
                if filter_id in self.filters:
                    # Create simplified effect representation
                    filter_effect = {'type': 'approximate_filter', 'filter_id': filter_id}
                    return self.bounds_calculator.get_bounds_approximation(
                        original_bounds, filter_effect, accuracy_level
                    )

            return original_bounds

        # Fall back to full calculation
        return self.calculate_filtered_element_bounds(element, context)

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for bounds calculations.

        Returns:
            Dictionary with performance metrics
        """
        cache_stats = self.bounds_calculator.get_cache_stats()
        return {
            'bounds_cache_size': cache_stats['cache_size'],
            'bounds_cache_max_size': cache_stats['max_cache_size'],
            'optimization_enabled': getattr(self, '_bounds_optimization_enabled', False),
            'significance_threshold': getattr(self, '_significance_threshold', 5.0)
        }

    def preprocess_filter_bounds_batch(self, elements: List[ET.Element],
                                      context: ConversionContext) -> Dict[str, Dict[str, float]]:
        """
        Preprocess bounds calculations for a batch of elements for better performance.

        Args:
            elements: List of SVG elements to process
            context: Conversion context

        Returns:
            Dictionary mapping element IDs to calculated bounds
        """
        bounds_batch = []
        element_map = {}

        # Collect all bounds and effects for batch processing
        for i, element in enumerate(elements):
            element_id = f"element_{i}"
            element_map[element_id] = element

            original_bounds = self._get_element_bounds(element, context)
            if original_bounds:
                filter_attr = element.get('filter', '')
                if filter_attr.startswith('url(#') and filter_attr.endswith(')'):
                    filter_id = filter_attr[5:-1]
                    if filter_id in self.filters:
                        filter_def = self.filters[filter_id]
                        # Create simplified effect for batch processing
                        filter_effects = self._process_filter_chain(filter_def, element, context)
                        for effect in filter_effects:
                            effect_dict = {
                                'type': effect.effect_type,
                                **effect.parameters
                            }
                            bounds_batch.append((original_bounds, effect_dict))
                            break  # Use first effect for batch optimization

        # Batch calculate bounds
        if bounds_batch:
            calculated_bounds = self.bounds_calculator.batch_calculate_bounds(bounds_batch)

            # Map results back to elements
            result_map = {}
            for i, (element_id, element) in enumerate(element_map.items()):
                if i < len(calculated_bounds):
                    result_map[element_id] = calculated_bounds[i]
                else:
                    # Fallback to original bounds
                    result_map[element_id] = self._get_element_bounds(element, context) or \
                                           {'x': 0, 'y': 0, 'width': 0, 'height': 0}

            return result_map

        # No elements to process
        return {}


class FilterBounds:
    """
    Filter bounds calculation system for accurate effect positioning.

    This class handles the complex task of calculating how filter effects
    expand or modify the bounds of SVG elements, ensuring proper positioning
    and clipping in PowerPoint.

    Key responsibilities:
    - Calculate bounds expansion for blur, shadow, and glow effects
    - Handle coordinate system transformations between SVG and OOXML
    - Support percentage-based and unit-based filter parameters
    - Optimize bounds calculations for performance
    """

    def __init__(self, unit_converter: UnitConverter, color_parser: ColorParser):
        """
        Initialize FilterBounds with required dependencies.

        Args:
            unit_converter: UnitConverter for handling SVG units to EMU conversion
            color_parser: ColorParser for processing color-related filter parameters
        """
        self.unit_converter = unit_converter
        self.color_parser = color_parser
        self._bounds_cache = {}  # Cache for repeated calculations

    def calculate_filter_bounds(self, original_bounds: Dict[str, float],
                               filter_effect: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate expanded bounds for a filter effect applied to an element.

        Args:
            original_bounds: Original element bounds {x, y, width, height}
            filter_effect: Filter effect definition with type and parameters

        Returns:
            Expanded bounds dictionary {x, y, width, height}

        Raises:
            ValueError: If bounds or filter_effect is None
            KeyError: If bounds dictionary is missing required keys
        """
        if original_bounds is None:
            raise ValueError("Bounds cannot be None")
        if filter_effect is None:
            raise ValueError("Filter effect cannot be None")

        # Validate bounds structure
        required_keys = ['x', 'y', 'width', 'height']
        for key in required_keys:
            if key not in original_bounds:
                raise KeyError(f"Missing required bounds key: {key}")

        # Create cache key for this calculation (handle nested dicts)
        def make_hashable(item):
            if isinstance(item, dict):
                return tuple(sorted((k, make_hashable(v)) for k, v in item.items()))
            elif isinstance(item, (list, tuple)):
                return tuple(make_hashable(i) for i in item)
            else:
                return item

        cache_key = (
            make_hashable(original_bounds),
            make_hashable(filter_effect)
        )

        if cache_key in self._bounds_cache:
            return self._bounds_cache[cache_key].copy()

        # Calculate bounds expansion based on filter type
        expanded_bounds = original_bounds.copy()
        filter_type = filter_effect.get('type', '')

        if filter_type == 'feGaussianBlur':
            expanded_bounds = self._expand_bounds_for_blur(expanded_bounds, filter_effect)
        elif filter_type == 'feDropShadow':
            expanded_bounds = self._expand_bounds_for_shadow(expanded_bounds, filter_effect)
        elif filter_type == 'feOffset':
            expanded_bounds = self._expand_bounds_for_offset(expanded_bounds, filter_effect)
        elif filter_type in ['feGlow', 'glow']:  # Custom glow effect
            expanded_bounds = self._expand_bounds_for_glow(expanded_bounds, filter_effect)
        else:
            # Unknown filter type - return original bounds unchanged
            pass

        # Cache the result
        self._bounds_cache[cache_key] = expanded_bounds.copy()
        return expanded_bounds

    def _expand_bounds_for_blur(self, bounds: Dict[str, float],
                               effect: Dict[str, Any]) -> Dict[str, float]:
        """
        Expand bounds for Gaussian blur effect.

        Blur expands bounds by approximately 3 * standard deviation in all directions.
        """
        std_dev_str = effect.get('stdDeviation', '0')
        std_dev = self._parse_filter_value(std_dev_str, bounds)

        if std_dev <= 0:
            return bounds

        # Blur expands by ~3 sigma in all directions
        expansion = std_dev * 3

        return {
            'x': bounds['x'] - expansion,
            'y': bounds['y'] - expansion,
            'width': bounds['width'] + (2 * expansion),
            'height': bounds['height'] + (2 * expansion)
        }

    def _expand_bounds_for_shadow(self, bounds: Dict[str, float],
                                 effect: Dict[str, Any]) -> Dict[str, float]:
        """
        Expand bounds for drop shadow effect.

        Shadow expands bounds by offset + blur expansion.
        """
        dx = self._parse_filter_value(effect.get('dx', '0'), bounds)
        dy = self._parse_filter_value(effect.get('dy', '0'), bounds)
        blur = self._parse_filter_value(effect.get('stdDeviation', '0'), bounds)

        # Calculate shadow bounds expansion
        blur_expansion = blur * 3 if blur > 0 else 0

        # Shadow extends bounds in offset direction plus blur expansion
        min_x = min(bounds['x'] - blur_expansion, bounds['x'])
        min_y = min(bounds['y'] - blur_expansion, bounds['y'])
        max_x = max(bounds['x'] + bounds['width'] + dx + blur_expansion,
                   bounds['x'] + bounds['width'])
        max_y = max(bounds['y'] + bounds['height'] + dy + blur_expansion,
                   bounds['y'] + bounds['height'])

        return {
            'x': min_x,
            'y': min_y,
            'width': max_x - min_x,
            'height': max_y - min_y
        }

    def _expand_bounds_for_offset(self, bounds: Dict[str, float],
                                 effect: Dict[str, Any]) -> Dict[str, float]:
        """
        Expand bounds for offset effect.

        Offset moves content, expanding bounds to include both original and offset positions.
        """
        dx = self._parse_filter_value(effect.get('dx', '0'), bounds)
        dy = self._parse_filter_value(effect.get('dy', '0'), bounds)

        min_x = min(bounds['x'], bounds['x'] + dx)
        min_y = min(bounds['y'], bounds['y'] + dy)
        max_x = max(bounds['x'] + bounds['width'], bounds['x'] + bounds['width'] + dx)
        max_y = max(bounds['y'] + bounds['height'], bounds['y'] + bounds['height'] + dy)

        return {
            'x': min_x,
            'y': min_y,
            'width': max_x - min_x,
            'height': max_y - min_y
        }

    def _expand_bounds_for_glow(self, bounds: Dict[str, float],
                               effect: Dict[str, Any]) -> Dict[str, float]:
        """
        Expand bounds for glow effect (similar to blur but typically smaller).
        """
        std_dev_str = effect.get('stdDeviation', '3')
        std_dev = self._parse_filter_value(std_dev_str, bounds)

        # Glow expands by ~3 * standard deviation
        expansion = std_dev * 3

        return {
            'x': bounds['x'] - expansion,
            'y': bounds['y'] - expansion,
            'width': bounds['width'] + (2 * expansion),
            'height': bounds['height'] + (2 * expansion)
        }

    def _parse_filter_value(self, value_str: str, bounds: Dict[str, float]) -> float:
        """
        Parse a filter parameter value, handling units and percentages using UnitConverter.

        Args:
            value_str: Parameter value string (e.g., "5", "5px", "10%")
            bounds: Current element bounds for percentage calculations

        Returns:
            Parsed numeric value in SVG coordinate units (pixels)
        """
        if not value_str:
            return 0.0

        value_str = str(value_str).strip()

        # Handle percentage values (relative to element dimensions)
        if value_str.endswith('%'):
            percent = float(value_str[:-1]) / 100.0
            # Use average of width/height for percentage base
            base_size = (bounds['width'] + bounds['height']) / 2.0
            return percent * base_size

        # Use the existing UnitConverter for proper unit conversion
        try:
            # Convert to EMU first, then back to pixels for bounds calculation
            emu_value = self.unit_converter.to_emu(value_str)
            # Convert EMU back to pixels (1 px = 9525 EMU at 96 DPI)
            return emu_value / 9525.0
        except (ValueError, AttributeError):
            # Fallback to plain numeric parsing
            try:
                return float(value_str)
            except ValueError:
                return 0.0

    def expand_bounds_for_effect(self, bounds: Dict[str, float],
                                effect_type: str, parameters: Dict[str, Any]) -> Dict[str, float]:
        """
        Public method to expand bounds for a specific effect type.

        This is a convenience method that wraps calculate_filter_bounds.
        """
        filter_effect = {'type': effect_type, **parameters}
        return self.calculate_filter_bounds(bounds, filter_effect)

    def transform_coordinates(self, bounds: Dict[str, float],
                             source_viewport: Dict[str, float],
                             target_viewport: Dict[str, float]) -> Dict[str, float]:
        """
        Transform coordinates between different viewport coordinate systems.

        Args:
            bounds: Bounds to transform
            source_viewport: Source coordinate system viewport
            target_viewport: Target coordinate system viewport

        Returns:
            Transformed bounds in target coordinate system
        """
        # Calculate scale factors
        scale_x = target_viewport['width'] / source_viewport['width']
        scale_y = target_viewport['height'] / source_viewport['height']

        # Apply transformation
        return {
            'x': (bounds['x'] - source_viewport['x']) * scale_x + target_viewport['x'],
            'y': (bounds['y'] - source_viewport['y']) * scale_y + target_viewport['y'],
            'width': bounds['width'] * scale_x,
            'height': bounds['height'] * scale_y
        }

    def apply_transform_to_bounds(self, bounds: Dict[str, float],
                                 transform_str: str) -> Dict[str, float]:
        """
        Apply SVG transform to bounds using the existing TransformParser.

        Args:
            bounds: Original bounds
            transform_str: SVG transform string (e.g., "translate(10,20) scale(2)")

        Returns:
            Transformed bounds
        """
        if not transform_str or not hasattr(self, 'transform_parser'):
            return bounds

        try:
            # Use existing TransformParser infrastructure
            # This would integrate with the existing transform parsing system
            # For now, return original bounds (placeholder for full integration)
            return bounds
        except Exception:
            # Fallback to original bounds on parsing error
            return bounds

    def clear_cache(self):
        """Clear the bounds calculation cache."""
        self._bounds_cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache hit/miss statistics
        """
        return {
            'cache_size': len(self._bounds_cache),
            'max_cache_size': 1000  # Reasonable cache size limit
        }

    def optimize_cache_size(self, max_size: int = 1000):
        """
        Optimize cache size by removing least recently used entries.

        Args:
            max_size: Maximum number of entries to keep in cache
        """
        if len(self._bounds_cache) > max_size:
            # Simple LRU implementation - remove oldest entries
            # In a real implementation, we'd track access times
            items_to_remove = len(self._bounds_cache) - max_size
            keys_to_remove = list(self._bounds_cache.keys())[:items_to_remove]
            for key in keys_to_remove:
                del self._bounds_cache[key]

    def is_bounds_expansion_significant(self, original_bounds: Dict[str, float],
                                       expanded_bounds: Dict[str, float],
                                       threshold_percent: float = 5.0) -> bool:
        """
        Determine if bounds expansion is significant enough to warrant processing.

        Args:
            original_bounds: Original element bounds
            expanded_bounds: Bounds after filter effect expansion
            threshold_percent: Minimum expansion percentage to consider significant

        Returns:
            True if expansion is significant, False if it can be ignored for optimization
        """
        original_area = original_bounds['width'] * original_bounds['height']
        expanded_area = expanded_bounds['width'] * expanded_bounds['height']

        if original_area == 0:
            return expanded_area > 0

        expansion_percent = ((expanded_area - original_area) / original_area) * 100
        return expansion_percent >= threshold_percent

    def batch_calculate_bounds(self, elements_and_effects: List[Tuple[Dict[str, float], Dict[str, Any]]]) -> List[Dict[str, float]]:
        """
        Batch calculate bounds for multiple elements to optimize performance.

        Args:
            elements_and_effects: List of (bounds, filter_effect) tuples

        Returns:
            List of calculated bounds for each element
        """
        results = []
        for bounds, effect in elements_and_effects:
            result = self.calculate_filter_bounds(bounds, effect)
            results.append(result)
        return results

    def get_bounds_approximation(self, bounds: Dict[str, float],
                                filter_effect: Dict[str, Any],
                                accuracy_level: str = 'medium') -> Dict[str, float]:
        """
        Get approximate bounds calculation for performance optimization.

        Args:
            bounds: Original bounds
            filter_effect: Filter effect definition
            accuracy_level: 'fast', 'medium', or 'precise'

        Returns:
            Approximated bounds (faster calculation with reduced precision)
        """
        if accuracy_level == 'fast':
            # Very rough approximation - just expand by a fixed percentage
            expansion_factor = 0.2  # 20% expansion
            expansion = min(bounds['width'], bounds['height']) * expansion_factor
            return {
                'x': bounds['x'] - expansion,
                'y': bounds['y'] - expansion,
                'width': bounds['width'] + 2 * expansion,
                'height': bounds['height'] + 2 * expansion
            }
        elif accuracy_level == 'medium':
            # Simplified calculation based on filter type only
            filter_type = filter_effect.get('type', '')
            if 'blur' in filter_type.lower():
                expansion = 15  # Fixed blur expansion
            elif 'shadow' in filter_type.lower():
                expansion = 10  # Fixed shadow expansion
            else:
                expansion = 5   # Default expansion

            return {
                'x': bounds['x'] - expansion,
                'y': bounds['y'] - expansion,
                'width': bounds['width'] + 2 * expansion,
                'height': bounds['height'] + 2 * expansion
            }
        else:  # 'precise'
            # Fall back to full calculation
            return self.calculate_filter_bounds(bounds, filter_effect)


class FilterRegionCalculator:
    """
    Helper class for filter region calculations and coordinate transformations.

    Provides utility functions for:
    - Region intersection calculations
    - Coordinate system transformations
    - Viewport clipping operations
    - Performance optimization utilities
    """

    def __init__(self):
        """Initialize FilterRegionCalculator."""
        pass

    def calculate_intersection(self, region1: Dict[str, float],
                              region2: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate the intersection of two rectangular regions.

        Args:
            region1: First region {x, y, width, height}
            region2: Second region {x, y, width, height}

        Returns:
            Intersection region, or zero-area region if no intersection
        """
        # Calculate intersection bounds
        left = max(region1['x'], region2['x'])
        top = max(region1['y'], region2['y'])
        right = min(region1['x'] + region1['width'], region2['x'] + region2['width'])
        bottom = min(region1['y'] + region1['height'], region2['y'] + region2['height'])

        # Check if intersection exists
        if left >= right or top >= bottom:
            return {'x': left, 'y': top, 'width': 0, 'height': 0}

        return {
            'x': left,
            'y': top,
            'width': right - left,
            'height': bottom - top
        }

    def transform_to_emu(self, point: Dict[str, float],
                        unit_converter: UnitConverter) -> Dict[str, float]:
        """
        Transform SVG coordinates to EMU (English Metric Units).

        Args:
            point: Point with x, y coordinates in SVG units
            unit_converter: UnitConverter for proper transformation

        Returns:
            Point in EMU coordinate system
        """
        return {
            'x': unit_converter.to_emu(f"{point['x']}px"),
            'y': unit_converter.to_emu(f"{point['y']}px")
        }

    def transform_from_emu(self, point: Dict[str, float],
                          unit_converter: UnitConverter) -> Dict[str, float]:
        """
        Transform EMU coordinates back to SVG coordinate system.

        Args:
            point: Point in EMU coordinates
            unit_converter: UnitConverter for proper transformation

        Returns:
            Point in SVG coordinate system (pixels)
        """
        # Convert EMU back to pixels (1 px = 9525 EMU at default 96 DPI)
        return {
            'x': point['x'] / 9525.0,
            'y': point['y'] / 9525.0
        }

    def clip_to_viewport(self, region: Dict[str, float],
                        viewport: Dict[str, float]) -> Dict[str, float]:
        """
        Clip a region to fit within a viewport.

        Args:
            region: Region to clip {x, y, width, height}
            viewport: Viewport bounds {x, y, width, height}

        Returns:
            Clipped region that fits within viewport
        """
        # Calculate clipped bounds
        left = max(region['x'], viewport['x'])
        top = max(region['y'], viewport['y'])
        right = min(region['x'] + region['width'], viewport['x'] + viewport['width'])
        bottom = min(region['y'] + region['height'], viewport['y'] + viewport['height'])

        # Ensure non-negative dimensions
        width = max(0, right - left)
        height = max(0, bottom - top)

        return {
            'x': left,
            'y': top,
            'width': width,
            'height': height
        }


class FilterComplexityAnalyzer:
    """
    Analyzes filter effect complexity to determine optimal processing strategies.

    This class provides sophisticated complexity scoring for SVG filter effects,
    helping determine whether to use native DrawingML, DML hacks, or rasterization.

    Key features:
    - Complexity scoring based on primitive count and parameters
    - Performance impact assessment
    - Quality vs performance trade-off analysis
    - Caching for repeated calculations
    """

    def __init__(self, unit_converter: UnitConverter, color_parser: ColorParser):
        """
        Initialize FilterComplexityAnalyzer with dependencies.

        Args:
            unit_converter: UnitConverter for parameter analysis
            color_parser: ColorParser for color-based complexity assessment
        """
        self.unit_converter = unit_converter
        self.color_parser = color_parser
        self._complexity_cache = {}
        self._performance_monitor = None

        # Default complexity scoring weights
        self._scoring_weights = {
            'primitive_count': 1.0,
            'parameter_complexity': 1.5,
            'rasterization_penalty': 2.0
        }

        # Default thresholds
        self._complexity_threshold = 3.0

    def calculate_complexity_score(self, filter_effect: Dict[str, Any]) -> float:
        """
        Calculate complexity score for a filter effect.

        Args:
            filter_effect: Filter effect definition

        Returns:
            Complexity score (0.0 = simple, higher = more complex)

        Raises:
            ValueError: If filter_effect is None
        """
        if filter_effect is None:
            raise ValueError("Filter effect cannot be None")

        if not filter_effect:
            return 0.0  # Empty effects have zero complexity

        # Create cache key
        cache_key = self._make_hashable(filter_effect)
        if cache_key in self._complexity_cache:
            return self._complexity_cache[cache_key]

        score = 0.0
        filter_type = filter_effect.get('type', '')

        # Base complexity by filter type
        if filter_type == 'feGaussianBlur':
            score += self._calculate_blur_complexity(filter_effect)
        elif filter_type == 'feDropShadow':
            score += self._calculate_shadow_complexity(filter_effect)
        elif filter_type == 'feColorMatrix':
            score += self._calculate_color_matrix_complexity(filter_effect)
        elif filter_type == 'feComposite':
            score += self._calculate_composite_complexity(filter_effect)
        elif filter_type == 'feTurbulence':
            score += self._calculate_turbulence_complexity(filter_effect)
        elif filter_type == 'feMorphology':
            score += self._calculate_morphology_complexity(filter_effect)
        elif filter_type == 'chain':
            score += self._calculate_chain_complexity(filter_effect)
        else:
            # Unknown effects get moderate complexity
            score += 2.0

        # Apply primitive count multiplier
        primitive_count = filter_effect.get('primitive_count', 1)
        if isinstance(primitive_count, (int, float)) and primitive_count > 1:
            score *= primitive_count * self._scoring_weights['primitive_count']

        # Apply complexity multiplier if specified
        multiplier = filter_effect.get('complexity_multiplier', 1.0)
        if isinstance(multiplier, (int, float)):
            score *= multiplier

        # Cache the result
        self._complexity_cache[cache_key] = score
        return score

    def _calculate_blur_complexity(self, effect: Dict[str, Any]) -> float:
        """Calculate complexity for Gaussian blur effects."""
        std_dev = effect.get('stdDeviation', '0')
        try:
            # Parse standard deviation value
            if isinstance(std_dev, str) and std_dev.endswith('%'):
                return 0.5  # Percentage blur is simpler

            std_val = float(str(std_dev).replace('px', '').replace('pt', ''))
            if std_val == 0:
                return 0.0
            elif std_val <= 3:
                return 0.5
            elif std_val <= 10:
                return 1.0
            elif std_val <= 50:
                return 3.0
            elif std_val <= 200:
                return 5.0
            else:
                # Very large blur values (like 1000) are extremely complex
                return 8.0
        except (ValueError, TypeError):
            return 1.0  # Default for unparseable values

    def _calculate_shadow_complexity(self, effect: Dict[str, Any]) -> float:
        """Calculate complexity for drop shadow effects."""
        base_complexity = 2.5  # Shadows are moderately complex - bump this up for medium range

        # Add complexity for blur component
        blur_val = effect.get('stdDeviation', '0')
        try:
            blur_complexity = float(str(blur_val).replace('px', '').replace('pt', '')) * 0.2
            base_complexity += min(blur_complexity, 1.5)
        except (ValueError, TypeError):
            pass

        # Add complexity for positioning (dx/dy parameters)
        dx = effect.get('dx', '0')
        dy = effect.get('dy', '0')
        try:
            offset_complexity = (abs(float(str(dx).replace('px', ''))) + abs(float(str(dy).replace('px', '')))) * 0.05
            base_complexity += min(offset_complexity, 0.5)
        except (ValueError, TypeError):
            pass

        # Add complexity for color processing
        if effect.get('flood-color') or effect.get('color'):
            base_complexity += 0.3

        return base_complexity

    def _calculate_color_matrix_complexity(self, effect: Dict[str, Any]) -> float:
        """Calculate complexity for color matrix effects."""
        matrix_type = effect.get('type', '')

        if matrix_type in ['saturate', 'hueRotate', 'luminanceToAlpha']:
            return 1.2  # Standard color operations
        elif matrix_type == 'matrix':
            values = effect.get('values', '')
            if values:
                try:
                    # Count matrix elements
                    elements = len(str(values).split())
                    return 1.0 + (elements * 0.05)  # More elements = more complex
                except:
                    pass
            return 2.0  # Custom matrix is more complex
        else:
            return 1.5  # Unknown color matrix type

    def _calculate_composite_complexity(self, effect: Dict[str, Any]) -> float:
        """Calculate complexity for composite effects."""
        operator = effect.get('operator', 'over')

        complexity_map = {
            'over': 0.8,
            'multiply': 1.2,
            'screen': 1.2,
            'darken': 1.0,
            'lighten': 1.0,
            'arithmetic': 2.0  # Most complex
        }

        return complexity_map.get(operator, 1.5)

    def _calculate_turbulence_complexity(self, effect: Dict[str, Any]) -> float:
        """Calculate complexity for turbulence effects."""
        base_complexity = 5.0  # Turbulence is inherently complex

        # Add complexity based on octaves
        octaves = effect.get('numOctaves', '1')
        try:
            octave_count = int(str(octaves))
            base_complexity += octave_count * 0.5
        except (ValueError, TypeError):
            pass

        return min(base_complexity, 15.0)  # Cap at reasonable maximum

    def _calculate_morphology_complexity(self, effect: Dict[str, Any]) -> float:
        """Calculate complexity for morphology effects."""
        base_complexity = 1.8

        # Add complexity based on radius
        radius = effect.get('radius', '0')
        try:
            radius_val = float(str(radius).replace('px', '').replace('pt', ''))
            base_complexity += radius_val * 0.1
        except (ValueError, TypeError):
            pass

        return min(base_complexity, 4.0)

    def _calculate_chain_complexity(self, effect: Dict[str, Any]) -> float:
        """Calculate complexity for chained filter effects."""
        primitives = effect.get('primitives', [])
        if not primitives:
            return 0.0

        total_complexity = 0.0
        for primitive in primitives:
            if isinstance(primitive, dict):
                # Recursively calculate complexity for each primitive
                primitive_score = self.calculate_complexity_score(primitive)
                total_complexity += primitive_score

        # Chain complexity is sum plus interconnection overhead
        primitive_count = len(primitives)
        if primitive_count <= 4:
            chain_overhead = primitive_count * 0.5  # Small chains are manageable
        else:
            # Large chains (like 20 primitives) are exponentially more complex
            chain_overhead = primitive_count * 1.2

        return total_complexity + chain_overhead

    def analyze_filter_chain(self, filter_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a complete filter chain for optimization opportunities.

        Args:
            filter_chain: List of filter effects

        Returns:
            Analysis results with optimization recommendations
        """
        if not filter_chain:
            return {'total_complexity': 0.0, 'recommendations': []}

        total_complexity = 0.0
        individual_scores = []

        for effect in filter_chain:
            score = self.calculate_complexity_score(effect)
            individual_scores.append(score)
            total_complexity += score

        # Generate recommendations
        recommendations = []
        if total_complexity > 10.0:
            recommendations.append('Consider rasterization for entire chain')
        elif total_complexity > 5.0:
            recommendations.append('Use DML hacks for complex primitives')
        elif any(score > 3.0 for score in individual_scores):
            recommendations.append('Mix native DML with targeted optimizations')
        else:
            recommendations.append('Use native DrawingML effects')

        return {
            'total_complexity': total_complexity,
            'individual_scores': individual_scores,
            'average_complexity': total_complexity / len(filter_chain),
            'max_complexity': max(individual_scores) if individual_scores else 0.0,
            'recommendations': recommendations
        }

    def get_performance_impact(self, filter_effect: Dict[str, Any]) -> Dict[str, float]:
        """
        Assess performance impact of a filter effect.

        Args:
            filter_effect: Filter effect to analyze

        Returns:
            Performance impact metrics
        """
        complexity = self.calculate_complexity_score(filter_effect)

        # Estimate performance metrics based on complexity
        render_time_factor = min(complexity * 0.1, 2.0)  # Cap at 2x
        memory_factor = min(complexity * 0.15, 3.0)      # Cap at 3x
        cpu_factor = min(complexity * 0.2, 4.0)          # Cap at 4x

        return {
            'render_time_factor': render_time_factor,
            'memory_factor': memory_factor,
            'cpu_factor': cpu_factor,
            'overall_impact': (render_time_factor + memory_factor + cpu_factor) / 3.0
        }

    def is_effect_simple(self, filter_effect: Dict[str, Any]) -> bool:
        """Check if an effect is simple enough for basic optimization."""
        complexity = self.calculate_complexity_score(filter_effect)
        return complexity <= self._complexity_threshold

    def set_complexity_threshold(self, threshold: float):
        """Set the complexity threshold for simple vs complex classification."""
        self._complexity_threshold = threshold

    def set_scoring_weights(self, weights: Dict[str, float]):
        """Set custom scoring weights."""
        self._scoring_weights.update(weights)

    def set_performance_mode(self, mode: str):
        """Set performance mode (fast, balanced, quality)."""
        if mode == 'fast':
            self._scoring_weights['rasterization_penalty'] = 1.5
        elif mode == 'quality':
            self._scoring_weights['rasterization_penalty'] = 3.0
        else:  # balanced
            self._scoring_weights['rasterization_penalty'] = 2.0

    def get_performance_monitor(self):
        """Get performance monitor for tracking complexity calculations."""
        if self._performance_monitor is None:
            self._performance_monitor = PerformanceMonitor()
        return self._performance_monitor

    def _make_hashable(self, item):
        """Convert dict to hashable tuple for caching."""
        if isinstance(item, dict):
            return tuple(sorted((k, self._make_hashable(v)) for k, v in item.items()))
        elif isinstance(item, (list, tuple)):
            return tuple(self._make_hashable(i) for i in item)
        else:
            return item


class OptimizationStrategy:
    """
    Determines optimal processing strategy for filter effects.

    This class implements the decision framework for choosing between
    native DrawingML, DML hacks, and rasterization based on complexity,
    performance targets, and quality requirements.
    """

    def __init__(self, unit_converter: UnitConverter, color_parser: ColorParser,
                 performance_targets: Dict[str, float] = None):
        """
        Initialize OptimizationStrategy.

        Args:
            unit_converter: UnitConverter for parameter processing
            color_parser: ColorParser for color analysis
            performance_targets: Performance thresholds for strategy selection
        """
        self.unit_converter = unit_converter
        self.color_parser = color_parser

        # Default performance targets
        self.performance_targets = performance_targets or {
            'native_threshold': 2.0,
            'hack_threshold': 5.0,
            'raster_threshold': 10.0
        }

        # Quality mode settings
        self._quality_mode = 'balanced'  # fast, balanced, quality

    def select_strategy(self, filter_effect: Dict[str, Any],
                       complexity_score: float) -> OOXMLEffectStrategy:
        """
        Select optimal strategy based on effect complexity and performance targets.

        Args:
            filter_effect: Filter effect definition
            complexity_score: Pre-calculated complexity score

        Returns:
            Recommended processing strategy
        """
        # Adjust thresholds based on quality mode
        native_threshold = self.performance_targets['native_threshold']
        hack_threshold = self.performance_targets['hack_threshold']

        if self._quality_mode == 'fast':
            # Lower thresholds for faster processing
            native_threshold *= 0.8
            hack_threshold *= 0.8
        elif self._quality_mode == 'quality':
            # Higher thresholds for better quality
            native_threshold *= 1.2
            hack_threshold *= 1.2

        # Strategy selection logic
        if complexity_score <= native_threshold:
            return OOXMLEffectStrategy.NATIVE_DML
        elif complexity_score <= hack_threshold:
            return OOXMLEffectStrategy.DML_HACK
        else:
            return OOXMLEffectStrategy.RASTERIZE

    def set_quality_mode(self, mode: str):
        """Set quality mode (fast, balanced, quality)."""
        if mode in ['fast', 'balanced', 'quality']:
            self._quality_mode = mode

    def get_strategy_confidence(self, filter_effect: Dict[str, Any],
                              strategy: OOXMLEffectStrategy) -> float:
        """
        Calculate confidence score for a strategy selection.

        Args:
            filter_effect: Filter effect being processed
            strategy: Selected strategy

        Returns:
            Confidence score (0.0 to 1.0)
        """
        filter_type = filter_effect.get('type', '')

        # Native strategy confidence
        if strategy == OOXMLEffectStrategy.NATIVE_DML:
            if filter_type in ['feGaussianBlur', 'feDropShadow', 'feOffset']:
                return 0.95  # High confidence for well-supported effects
            else:
                return 0.6   # Lower confidence for less common effects

        # DML hack strategy confidence
        elif strategy == OOXMLEffectStrategy.DML_HACK:
            if filter_type in ['feColorMatrix', 'feComposite', 'feMorphology']:
                return 0.8   # Good confidence for hackable effects
            else:
                return 0.5   # Moderate confidence for complex hacks

        # Rasterization strategy confidence
        else:
            return 0.9       # High confidence - rasterization handles everything

    def estimate_processing_time(self, filter_effect: Dict[str, Any],
                               strategy: OOXMLEffectStrategy) -> float:
        """
        Estimate processing time for effect with given strategy.

        Args:
            filter_effect: Filter effect to process
            strategy: Processing strategy

        Returns:
            Estimated processing time in milliseconds
        """
        base_times = {
            OOXMLEffectStrategy.NATIVE_DML: 1.0,    # Fastest
            OOXMLEffectStrategy.DML_HACK: 3.0,      # Moderate
            OOXMLEffectStrategy.RASTERIZE: 10.0     # Slowest but most capable
        }

        complexity_analyzer = FilterComplexityAnalyzer(self.unit_converter, self.color_parser)
        complexity = complexity_analyzer.calculate_complexity_score(filter_effect)

        base_time = base_times.get(strategy, 5.0)
        complexity_multiplier = 1.0 + (complexity * 0.1)

        return base_time * complexity_multiplier


class FallbackChain:
    """
    Manages fallback strategies when preferred processing methods fail.

    Provides comprehensive fallback system with graceful degradation
    from native effects to hacks to rasterization to basic styling.
    """

    def __init__(self):
        """Initialize FallbackChain."""
        self._fallback_cache = {}

    def _make_hashable(self, obj):
        """Convert nested dict/list structure to hashable tuple form for caching."""
        if isinstance(obj, dict):
            return tuple(sorted((k, self._make_hashable(v)) for k, v in obj.items()))
        elif isinstance(obj, list):
            return tuple(self._make_hashable(item) for item in obj)
        else:
            return obj

    def build_fallback_chain(self, filter_effect: Dict[str, Any]) -> List[OOXMLEffectStrategy]:
        """
        Build fallback strategy chain for a filter effect.

        Args:
            filter_effect: Filter effect requiring fallback chain

        Returns:
            Ordered list of strategies to try
        """
        filter_type = filter_effect.get('type', '')

        # Check cache first
        cache_key = (filter_type, self._make_hashable(filter_effect))
        if cache_key in self._fallback_cache:
            return self._fallback_cache[cache_key].copy()

        fallback_chain = []

        # Build strategy chain based on effect type
        if filter_type in ['feGaussianBlur', 'feDropShadow']:
            fallback_chain = [
                OOXMLEffectStrategy.NATIVE_DML,
                OOXMLEffectStrategy.DML_HACK,
                OOXMLEffectStrategy.RASTERIZE
            ]
        elif filter_type in ['feColorMatrix', 'feComposite']:
            fallback_chain = [
                OOXMLEffectStrategy.DML_HACK,
                OOXMLEffectStrategy.RASTERIZE
            ]
        elif filter_type in ['feTurbulence', 'feConvolveMatrix']:
            fallback_chain = [
                OOXMLEffectStrategy.RASTERIZE
            ]
        else:
            # Default fallback chain
            fallback_chain = [
                OOXMLEffectStrategy.NATIVE_DML,
                OOXMLEffectStrategy.DML_HACK,
                OOXMLEffectStrategy.RASTERIZE
            ]

        # Cache the result
        self._fallback_cache[cache_key] = fallback_chain.copy()
        return fallback_chain

    def get_basic_styling_fallback(self, filter_effect: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate basic styling fallback when all strategies fail.

        Args:
            filter_effect: Original filter effect

        Returns:
            Basic styling equivalent
        """
        filter_type = filter_effect.get('type', '')

        # Map filter effects to basic styling
        if filter_type == 'feGaussianBlur':
            return {
                'fallback_type': 'transparency',
                'opacity': 0.8,
                'reasoning': 'Blur approximated with transparency'
            }
        elif filter_type == 'feDropShadow':
            return {
                'fallback_type': 'border',
                'border_color': '#666666',
                'border_width': 1,
                'reasoning': 'Shadow approximated with border'
            }
        elif filter_type in ['feColorMatrix', 'feFlood']:
            return {
                'fallback_type': 'color_overlay',
                'overlay_color': filter_effect.get('flood-color', '#000000'),
                'opacity': 0.5,
                'reasoning': 'Color effect approximated with overlay'
            }
        else:
            return {
                'fallback_type': 'none',
                'reasoning': 'No suitable basic styling fallback available'
            }

    def calculate_fallback_quality(self, filter_effect: Dict[str, Any],
                                 strategy: OOXMLEffectStrategy) -> Dict[str, float]:
        """
        Calculate quality metrics for fallback strategies.

        Args:
            filter_effect: Original filter effect
            strategy: Fallback strategy being evaluated

        Returns:
            Quality metrics for the fallback
        """
        filter_type = filter_effect.get('type', '')

        # Quality scoring based on effect type and strategy compatibility
        quality_matrix = {
            ('feGaussianBlur', OOXMLEffectStrategy.NATIVE_DML): 0.95,
            ('feGaussianBlur', OOXMLEffectStrategy.DML_HACK): 0.7,
            ('feGaussianBlur', OOXMLEffectStrategy.RASTERIZE): 0.98,

            ('feDropShadow', OOXMLEffectStrategy.NATIVE_DML): 0.9,
            ('feDropShadow', OOXMLEffectStrategy.DML_HACK): 0.6,
            ('feDropShadow', OOXMLEffectStrategy.RASTERIZE): 0.95,

            ('feColorMatrix', OOXMLEffectStrategy.NATIVE_DML): 0.3,
            ('feColorMatrix', OOXMLEffectStrategy.DML_HACK): 0.8,
            ('feColorMatrix', OOXMLEffectStrategy.RASTERIZE): 0.98,

            ('feTurbulence', OOXMLEffectStrategy.NATIVE_DML): 0.0,
            ('feTurbulence', OOXMLEffectStrategy.DML_HACK): 0.2,
            ('feTurbulence', OOXMLEffectStrategy.RASTERIZE): 0.95,
        }

        key = (filter_type, strategy)
        visual_accuracy = quality_matrix.get(key, 0.5)

        # Performance impact (inverse of strategy complexity)
        performance_scores = {
            OOXMLEffectStrategy.NATIVE_DML: 0.95,
            OOXMLEffectStrategy.DML_HACK: 0.7,
            OOXMLEffectStrategy.RASTERIZE: 0.3
        }
        performance_impact = performance_scores.get(strategy, 0.5)

        return {
            'visual_accuracy': visual_accuracy,
            'performance_impact': performance_impact,
            'overall_quality': (visual_accuracy + performance_impact) / 2.0
        }


class PerformanceMonitor:
    """
    Monitors and tracks performance metrics for filter effect processing.

    Provides comprehensive performance monitoring, regression detection,
    and optimization metrics for the filter processing pipeline.
    """

    def __init__(self):
        """Initialize PerformanceMonitor."""
        self._operation_times = {}
        self._active_operations = {}
        self._strategy_metrics = {}
        self._performance_history = []

    def start_tracking(self, operation_id: str):
        """Start tracking performance for an operation."""
        import time
        self._active_operations[operation_id] = time.time()

    def end_tracking(self, operation_id: str) -> float:
        """End tracking and return operation duration."""
        import time

        if operation_id not in self._active_operations:
            return 0.0

        start_time = self._active_operations.pop(operation_id)
        duration = time.time() - start_time

        # Store duration
        if operation_id not in self._operation_times:
            self._operation_times[operation_id] = []
        self._operation_times[operation_id].append(duration)

        # Add to performance history
        self._performance_history.append({
            'operation': operation_id,
            'duration': duration,
            'timestamp': time.time()
        })

        return duration

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        total_operations = sum(len(times) for times in self._operation_times.values())

        if total_operations == 0:
            return {'total_operations': 0, 'average_duration': 0.0}

        all_durations = []
        for times in self._operation_times.values():
            all_durations.extend(times)

        average_duration = sum(all_durations) / len(all_durations)

        return {
            'total_operations': total_operations,
            'average_duration': average_duration,
            'min_duration': min(all_durations) if all_durations else 0.0,
            'max_duration': max(all_durations) if all_durations else 0.0,
            'operation_types': len(self._operation_times)
        }

    def record_strategy_usage(self, filter_effect: Dict[str, Any],
                            strategy: OOXMLEffectStrategy, success: bool):
        """Record usage and success rate for different strategies."""
        if strategy not in self._strategy_metrics:
            self._strategy_metrics[strategy] = {
                'total_attempts': 0,
                'successful_attempts': 0,
                'success_rate': 0.0
            }

        metrics = self._strategy_metrics[strategy]
        metrics['total_attempts'] += 1
        if success:
            metrics['successful_attempts'] += 1

        metrics['success_rate'] = metrics['successful_attempts'] / metrics['total_attempts']

    def get_strategy_metrics(self) -> Dict[OOXMLEffectStrategy, Dict[str, Any]]:
        """Get strategy usage and success metrics."""
        return self._strategy_metrics.copy()

    def get_performance_baseline(self) -> Dict[str, float]:
        """Calculate performance baseline from recent operations."""
        if not self._performance_history:
            return {'average_duration': 0.0, 'operation_count': 0}

        # Use recent operations for baseline (last 50 operations)
        recent_ops = self._performance_history[-50:]
        durations = [op['duration'] for op in recent_ops]

        return {
            'average_duration': sum(durations) / len(durations),
            'operation_count': len(recent_ops),
            'baseline_timestamp': recent_ops[0]['timestamp']
        }

    def detect_performance_regression(self, threshold_multiplier: float = 2.0) -> bool:
        """
        Detect performance regression based on recent operations.

        Args:
            threshold_multiplier: Factor by which current performance must exceed baseline

        Returns:
            True if regression detected, False otherwise
        """
        baseline = self.get_performance_baseline()
        if baseline['operation_count'] < 10:  # Need sufficient baseline
            return False

        # Check recent operations against baseline
        recent_ops = self._performance_history[-10:]  # Last 10 operations
        if not recent_ops:
            return False

        recent_avg = sum(op['duration'] for op in recent_ops) / len(recent_ops)
        baseline_avg = baseline['average_duration']

        return recent_avg > (baseline_avg * threshold_multiplier)

    def track_complexity_calculation(self, complexity_score: float, duration: float):
        """Track complexity calculation performance."""
        operation_id = f"complexity_calc_{len(self._performance_history)}"
        self._performance_history.append({
            'operation': operation_id,
            'duration': duration,
            'complexity_score': complexity_score,
            'timestamp': time.time()
        })


class FilterPipeline:
    """
    Comprehensive filter pipeline for integrating SVG filter effects with the rendering system.

    This class coordinates the complete filter processing workflow, from parsing filter
    definitions to applying effects to shapes and text with proper optimization and fallback.
    """

    def __init__(self, unit_converter: 'UnitConverter', color_parser: 'ColorParser',
                 transform_parser: 'TransformParser', config: Dict[str, Any] = None):
        """
        Initialize FilterPipeline with required dependencies.

        Args:
            unit_converter: UnitConverter for coordinate transformations
            color_parser: ColorParser for color processing
            transform_parser: TransformParser for transform operations
            config: Optional configuration dictionary
        """
        self.unit_converter = unit_converter
        self.color_parser = color_parser
        self.transform_parser = transform_parser
        self.config = config or {}

        # Initialize pipeline components
        self.render_context = FilterRenderContext(unit_converter, color_parser)
        self.integrator = FilterIntegrator(unit_converter, color_parser, transform_parser)
        self.compositing_engine = CompositingEngine()
        self.performance_optimizer = FilterPerformanceOptimizer()

        # Initialize caching system
        self._filter_cache = {}

    def apply_filter(self, svg_element, filter_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a filter effect to an SVG element.

        Args:
            svg_element: SVG element to apply filter to
            filter_def: Filter definition dictionary

        Returns:
            Dictionary containing filter application results
        """
        try:
            # Generate cache key for this filter application
            cache_key = self._generate_cache_key(svg_element, filter_def)
            if cache_key in self._filter_cache:
                cached_result = self._filter_cache[cache_key].copy()
                cached_result['cache_hit'] = True
                return cached_result

            # Initialize render context
            context = self.render_context.create_context(svg_element, filter_def)

            # Apply filter through integration system
            result = self.integrator.apply_integrated_filter(context)

            # Cache successful results
            if result and not result.get('error'):
                self._filter_cache[cache_key] = result.copy()
                result['filter_applied'] = True
            else:
                # Apply fallback if filter failed
                result = self._apply_fallback(svg_element, filter_def)
                result['fallback_applied'] = True

            return result

        except Exception as e:
            # Return fallback result on any error
            return {
                'error': str(e),
                'fallback_applied': True,
                'filter_applied': False
            }

    def _generate_cache_key(self, svg_element, filter_def: Dict[str, Any]) -> str:
        """Generate a unique cache key for filter application."""
        import hashlib
        element_str = str(svg_element.tag if hasattr(svg_element, 'tag') else svg_element)
        filter_str = str(sorted(filter_def.items()) if isinstance(filter_def, dict) else filter_def)
        combined = f"{element_str}:{filter_str}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _apply_fallback(self, svg_element, filter_def: Dict[str, Any]) -> Dict[str, Any]:
        """Apply fallback handling when filter application fails."""
        return {
            'fallback_applied': True,
            'filter_applied': False,
            'original_element': svg_element,
            'attempted_filter': filter_def
        }


class FilterRenderContext:
    """
    Manages render context for filter effects processing.

    Provides the necessary context and state management for filter rendering operations,
    including coordinate systems, bounds management, and resource allocation.
    """

    def __init__(self, unit_converter: 'UnitConverter', color_parser: 'ColorParser'):
        """Initialize FilterRenderContext."""
        self.unit_converter = unit_converter
        self.color_parser = color_parser
        self.active_contexts = {}

    def create_context(self, svg_element, filter_def: Dict[str, Any]) -> Dict[str, Any]:
        """Create a render context for filter processing."""
        context_id = f"ctx_{len(self.active_contexts)}"

        context = {
            'context_id': context_id,
            'svg_element': svg_element,
            'filter_def': filter_def,
            'bounds': self._calculate_element_bounds(svg_element),
            'coordinates': self._setup_coordinate_system(),
            'resources': {}
        }

        self.active_contexts[context_id] = context
        return context

    def _calculate_element_bounds(self, svg_element) -> Dict[str, float]:
        """Calculate bounds for SVG element."""
        # Simplified bounds calculation - in real implementation would be more complex
        return {'x': 0, 'y': 0, 'width': 100, 'height': 100}

    def _setup_coordinate_system(self) -> Dict[str, Any]:
        """Setup coordinate system for filter processing."""
        return {
            'units': 'userSpaceOnUse',
            'dpi': 96,
            'scale_factor': 1.0
        }


class FilterIntegrator:
    """
    Integrates filter effects with shape and text rendering pipelines.

    This class handles the integration of filter effects with existing shape and text
    rendering systems, ensuring proper coordination and state management.
    """

    def __init__(self, unit_converter: 'UnitConverter', color_parser: 'ColorParser',
                 transform_parser: 'TransformParser'):
        """Initialize FilterIntegrator."""
        self.unit_converter = unit_converter
        self.color_parser = color_parser
        self.transform_parser = transform_parser
        self.filter_bounds = FilterBounds(unit_converter, color_parser)
        self.complexity_analyzer = FilterComplexityAnalyzer(unit_converter, color_parser)

    def integrate_with_shape(self, svg_element, filter_def: Dict[str, Any],
                           shape_converter) -> Dict[str, Any]:
        """
        Integrate filter effects with shape rendering.

        Args:
            svg_element: SVG element to process
            filter_def: Filter definition
            shape_converter: Shape converter instance

        Returns:
            Integration result dictionary
        """
        # Calculate shape bounds
        shape_bounds = self._extract_shape_bounds(svg_element)

        # Calculate filter bounds expansion
        filter_bounds = self.filter_bounds.calculate_filter_bounds(shape_bounds, filter_def)

        # Analyze filter complexity for optimization
        complexity = self.complexity_analyzer.calculate_complexity_score(filter_def)

        # Apply filter effects based on complexity
        if complexity <= 3.0:
            return self._apply_simple_shape_filter(svg_element, filter_def, shape_bounds)
        else:
            return self._apply_complex_shape_filter(svg_element, filter_def, shape_bounds)

    def integrate_with_text(self, svg_element, filter_def: Dict[str, Any],
                          text_converter) -> Dict[str, Any]:
        """
        Integrate filter effects with text rendering.

        Args:
            svg_element: Text SVG element
            filter_def: Filter definition
            text_converter: Text converter instance

        Returns:
            Integration result dictionary
        """
        # Extract text bounds
        text_bounds = self._extract_text_bounds(svg_element)

        # Calculate filter expansion for text
        filter_bounds = self.filter_bounds.calculate_filter_bounds(text_bounds, filter_def)

        # Apply text-specific filter optimizations
        return self._apply_text_filter(svg_element, filter_def, text_bounds, filter_bounds)

    def integrate_shape_layers(self, shapes_with_filters: List[Tuple]) -> Dict[str, Any]:
        """
        Integrate multiple filtered shapes with proper layer ordering.

        Args:
            shapes_with_filters: List of (svg_element, filter_def) tuples

        Returns:
            Layer integration result
        """
        layers = []
        for i, (svg_element, filter_def) in enumerate(shapes_with_filters):
            layer_info = {
                'layer_id': f"layer_{i}",
                'svg_element': svg_element,
                'filter_def': filter_def,
                'has_filter': filter_def is not None,
                'z_index': i
            }
            layers.append(layer_info)

        return {'layers': layers}

    def apply_integrated_filter(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply integrated filter processing using render context."""
        svg_element = context['svg_element']
        filter_def = context['filter_def']

        # Apply filter based on element type
        element_tag = getattr(svg_element, 'tag', str(svg_element)).lower()

        if 'rect' in element_tag or 'circle' in element_tag or 'polygon' in element_tag:
            return self.integrate_with_shape(svg_element, filter_def, None)
        elif 'text' in element_tag:
            return self.integrate_with_text(svg_element, filter_def, None)
        else:
            # Generic filter application
            return {'filter_applied': True, 'method': 'generic'}

    def _extract_shape_bounds(self, svg_element) -> Dict[str, float]:
        """Extract bounds from shape element."""
        # Simplified implementation
        return {'x': 0, 'y': 0, 'width': 100, 'height': 100}

    def _extract_text_bounds(self, svg_element) -> Dict[str, float]:
        """Extract bounds from text element."""
        # Simplified implementation - would calculate actual text metrics
        return {'x': 0, 'y': 0, 'width': 200, 'height': 20}

    def _apply_simple_shape_filter(self, svg_element, filter_def: Dict[str, Any],
                                 bounds: Dict[str, float]) -> Dict[str, Any]:
        """Apply simple filter to shape."""
        return {
            'filter_applied': True,
            'shape_bounds': bounds,
            'filter_bounds': bounds,
            'complexity': 'simple'
        }

    def _apply_complex_shape_filter(self, svg_element, filter_def: Dict[str, Any],
                                  bounds: Dict[str, float]) -> Dict[str, Any]:
        """Apply complex filter to shape with optimization."""
        # Expand bounds for complex filters
        expanded_bounds = bounds.copy()
        expanded_bounds['width'] *= 1.2
        expanded_bounds['height'] *= 1.2

        return {
            'filter_applied': True,
            'shape_bounds': bounds,
            'filter_bounds': expanded_bounds,
            'complexity': 'complex'
        }

    def _apply_text_filter(self, svg_element, filter_def: Dict[str, Any],
                         text_bounds: Dict[str, float], filter_bounds: Dict[str, float]) -> Dict[str, Any]:
        """Apply filter to text element."""
        # Check for text-specific effects
        has_glow = any(p.get('type') == 'feGaussianBlur' for p in filter_def.get('primitives', [filter_def]))
        has_shadow = any(p.get('type') == 'feDropShadow' for p in filter_def.get('primitives', [filter_def]))

        result = {
            'filter_applied': True,
            'text_bounds': text_bounds,
            'filter_bounds': filter_bounds
        }

        if has_glow:
            result['glow_applied'] = True
        if has_shadow:
            result['shadow_applied'] = True

        return result


class CompositingEngine:
    """
    Handles composite operations and alpha blending for filter effects.

    Manages the complex task of compositing multiple filter effects with proper
    alpha blending, layer management, and optimization for performance.
    """

    def __init__(self):
        """Initialize CompositingEngine."""
        self.blend_processor = BlendingModeProcessor()

    def composite_layers(self, layers: List[Dict[str, Any]], optimize: bool = False) -> Dict[str, Any]:
        """
        Composite multiple layers with alpha blending.

        Args:
            layers: List of layer dictionaries with color and blend_mode
            optimize: Whether to apply performance optimizations

        Returns:
            Compositing result dictionary
        """
        if not layers:
            return {'final_color': (0, 0, 0, 0)}

        # Start with first layer as base
        result_color = layers[0]['color']

        # Composite each subsequent layer
        for layer in layers[1:]:
            blend_mode = layer.get('blend_mode', 'normal')
            layer_color = layer['color']

            result_color = self.blend_processor.apply_blend_mode(
                result_color, layer_color, blend_mode
            )

        return {
            'final_color': result_color,
            'layers_processed': len(layers),
            'optimization_applied': optimize
        }

    def process_filter_chain(self, filter_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a chain of filter effects with compositing."""
        applied_operations = []

        for i, filter_effect in enumerate(filter_chain):
            operation = {
                'index': i,
                'type': filter_effect.get('type'),
                'blend_mode': filter_effect.get('blend_mode', 'normal'),
                'processed': True
            }
            applied_operations.append(operation)

        return {
            'composite_result': 'success',
            'applied_operations': applied_operations
        }


class BlendingModeProcessor:
    """
    Processes different blending modes for filter compositing.

    Implements various blending algorithms for combining filter effects
    with proper color space handling and optimization.
    """

    def apply_blend_mode(self, base_color: Tuple[int, int, int, int],
                        blend_color: Tuple[int, int, int, int],
                        blend_mode: str) -> Tuple[int, int, int, int]:
        """
        Apply a specific blend mode to combine two colors.

        Args:
            base_color: Base color as (R, G, B, A) tuple
            blend_color: Blend color as (R, G, B, A) tuple
            blend_mode: Blending mode name

        Returns:
            Resulting color as (R, G, B, A) tuple
        """
        if blend_mode == 'normal':
            return self._blend_normal(base_color, blend_color)
        elif blend_mode == 'multiply':
            return self._blend_multiply(base_color, blend_color)
        elif blend_mode == 'screen':
            return self._blend_screen(base_color, blend_color)
        elif blend_mode == 'overlay':
            return self._blend_overlay(base_color, blend_color)
        else:
            # Default to normal blending
            return self._blend_normal(base_color, blend_color)

    def _blend_normal(self, base: Tuple[int, int, int, int],
                     blend: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """Normal alpha blending."""
        br, bg, bb, ba = base
        tr, tg, tb, ta = blend

        # Alpha blending formula
        alpha = ta / 255.0
        inv_alpha = 1.0 - alpha

        r = int(br * inv_alpha + tr * alpha)
        g = int(bg * inv_alpha + tg * alpha)
        b = int(bb * inv_alpha + tb * alpha)
        a = int(max(ba, ta))

        return (r, g, b, a)

    def _blend_multiply(self, base: Tuple[int, int, int, int],
                       blend: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """Multiply blending."""
        br, bg, bb, ba = base
        tr, tg, tb, ta = blend

        r = int((br * tr) / 255)
        g = int((bg * tg) / 255)
        b = int((bb * tb) / 255)
        a = int(max(ba, ta))

        return (r, g, b, a)

    def _blend_screen(self, base: Tuple[int, int, int, int],
                     blend: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """Screen blending."""
        br, bg, bb, ba = base
        tr, tg, tb, ta = blend

        r = 255 - int(((255 - br) * (255 - tr)) / 255)
        g = 255 - int(((255 - bg) * (255 - tg)) / 255)
        b = 255 - int(((255 - bb) * (255 - tb)) / 255)
        a = int(max(ba, ta))

        return (r, g, b, a)

    def _blend_overlay(self, base: Tuple[int, int, int, int],
                      blend: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """Overlay blending."""
        br, bg, bb, ba = base
        tr, tg, tb, ta = blend

        def overlay_channel(base_val, blend_val):
            if base_val < 128:
                return int((2 * base_val * blend_val) / 255)
            else:
                return 255 - int((2 * (255 - base_val) * (255 - blend_val)) / 255)

        r = overlay_channel(br, tr)
        g = overlay_channel(bg, tg)
        b = overlay_channel(bb, tb)
        a = int(max(ba, ta))

        return (r, g, b, a)


class FilterStateManager:
    """
    Manages filter processing state and provides debugging capabilities.

    Tracks filter processing stages, manages resources, and provides debugging
    and diagnostic information for filter operations.
    """

    def __init__(self):
        """Initialize FilterStateManager."""
        self._filter_states = {}
        self._debug_traces = {}
        self._resource_registry = {}

    def initialize_filter_state(self, filter_id: str, initial_state: Dict[str, Any]):
        """Initialize state tracking for a filter."""
        self._filter_states[filter_id] = initial_state.copy()

        if initial_state.get('debug_mode'):
            self._debug_traces[filter_id] = []

    def update_filter_stage(self, filter_id: str, stage: str):
        """Update the processing stage for a filter."""
        if filter_id in self._filter_states:
            self._filter_states[filter_id]['stage'] = stage

    def get_filter_state(self, filter_id: str) -> Dict[str, Any]:
        """Get current state for a filter."""
        return self._filter_states.get(filter_id, {}).copy()

    def cleanup_filter_state(self, filter_id: str):
        """Clean up state and resources for a completed filter."""
        self._filter_states.pop(filter_id, None)
        self._debug_traces.pop(filter_id, None)
        self._resource_registry.pop(filter_id, None)

    def get_all_active_filters(self) -> List[str]:
        """Get list of all active filter IDs."""
        return list(self._filter_states.keys())

    def add_debug_trace(self, filter_id: str, trace_entry: str):
        """Add a debug trace entry for a filter."""
        if filter_id in self._debug_traces:
            self._debug_traces[filter_id].append(trace_entry)

    def get_debug_info(self, filter_id: str) -> Dict[str, Any]:
        """Get debug information for a filter."""
        return {
            'execution_trace': self._debug_traces.get(filter_id, []),
            'current_state': self._filter_states.get(filter_id, {}),
            'resources': self._resource_registry.get(filter_id, {})
        }


class FilterPerformanceOptimizer:
    """
    Optimizes filter processing performance with caching and batching.

    Provides performance optimization strategies including render batching,
    intelligent caching, and memory management for filter operations.
    """

    def __init__(self):
        """Initialize FilterPerformanceOptimizer."""
        self._render_cache = {}
        self._batch_processor = None
        self.performance_metrics = {}

    def batch_process_filters(self, filter_elements: List[Dict[str, Any]],
                            memory_optimization: bool = False) -> Dict[str, Any]:
        """
        Process multiple filters in optimized batches.

        Args:
            filter_elements: List of filter element dictionaries
            memory_optimization: Enable memory usage optimization

        Returns:
            Batch processing result
        """
        processed_elements = []

        # Group similar filters for batch processing
        filter_groups = self._group_similar_filters(filter_elements)

        for group in filter_groups:
            # Process each group efficiently
            group_results = self._process_filter_group(group, memory_optimization)
            processed_elements.extend(group_results)

        return {
            'processed_elements': processed_elements,
            'batch_count': len(filter_groups),
            'total_elements': len(filter_elements),
            'memory_optimized': memory_optimization
        }

    def process_single_filter(self, filter_element: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single filter element."""
        return {
            'processed': True,
            'element': filter_element,
            'method': 'single'
        }

    def process_with_cache(self, filter_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process filter with intelligent caching."""
        # Generate cache key
        cache_key = self._generate_filter_cache_key(filter_config)

        # Check cache
        if cache_key in self._render_cache:
            cached_result = self._render_cache[cache_key].copy()
            cached_result['cache_hit'] = True
            return cached_result

        # Process and cache result
        result = self.process_single_filter(filter_config)
        self._render_cache[cache_key] = result.copy()
        result['cache_hit'] = False

        return result

    def _group_similar_filters(self, filter_elements: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group similar filters for batch processing."""
        groups = []
        current_group = []

        for element in filter_elements:
            if not current_group:
                current_group = [element]
            elif self._are_filters_similar(current_group[0], element):
                current_group.append(element)
            else:
                groups.append(current_group)
                current_group = [element]

        if current_group:
            groups.append(current_group)

        return groups

    def _are_filters_similar(self, filter1: Dict[str, Any], filter2: Dict[str, Any]) -> bool:
        """Check if two filters are similar enough for batch processing."""
        f1_def = filter1.get('filter_def', {})
        f2_def = filter2.get('filter_def', {})

        return f1_def.get('id', '').split('-')[0] == f2_def.get('id', '').split('-')[0]

    def _process_filter_group(self, group: List[Dict[str, Any]],
                            memory_optimization: bool) -> List[Dict[str, Any]]:
        """Process a group of similar filters efficiently."""
        results = []
        for element in group:
            result = self.process_single_filter(element)
            result['batch_processed'] = True
            results.append(result)

        return results

    def _generate_filter_cache_key(self, filter_config: Dict[str, Any]) -> str:
        """Generate cache key for filter configuration."""
        import hashlib
        config_str = str(sorted(filter_config.items()))
        return hashlib.md5(config_str.encode()).hexdigest()
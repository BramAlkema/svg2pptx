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
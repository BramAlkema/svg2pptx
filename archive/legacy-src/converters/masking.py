#!/usr/bin/env python3
"""
SVG Mask and Clipping Path Converter

This module handles SVG masking and clipping path elements for PowerPoint conversion.
Masks and clipping paths are advanced SVG features that define visibility regions
and transparency effects for other elements.

Key Features:
- SVG <mask> element processing with opacity masks
- SVG <clipPath> element processing for geometric clipping
- PowerPoint clipping shape conversion
- Smart rasterization for complex mask patterns
- Alpha channel and transparency handling
- Nested mask and clipping path support
- Path-based and shape-based clipping conversion
"""

from lxml import etree as ET
from typing import Dict, List, Optional, Tuple, Union, NamedTuple
import math
import logging
from dataclasses import dataclass
from enum import Enum

from .base import BaseConverter
from .base import ConversionContext
from ..services.conversion_services import ConversionServices
from .clippath_types import ClipPathDefinition, ClippingType, ClipPathComplexity, ClipPathAnalysis
from .clippath_analyzer import ClipPathAnalyzer
from .boolean_flattener import BooleanFlattener
from .custgeom_generator import CustGeomGenerator
from ..emf_blob import EMFBlob
from ..emf_packaging import EMFRelationshipManager

logger = logging.getLogger(__name__)


class MaskType(Enum):
    """Types of SVG mask content."""
    LUMINANCE = "luminance"
    ALPHA = "alpha"


@dataclass
class MaskDefinition:
    """Definition of an SVG mask element."""
    id: str
    mask_type: MaskType
    units: str  # userSpaceOnUse or objectBoundingBox
    mask_units: str  # userSpaceOnUse or objectBoundingBox
    x: float
    y: float
    width: float
    height: float
    content_elements: List[ET.Element]
    opacity: float = 1.0
    transform: Optional[str] = None


@dataclass
class MaskApplication:
    """Application of a mask to an element."""
    target_element: ET.Element
    mask_definition: MaskDefinition
    resolved_bounds: Tuple[float, float, float, float]  # x, y, width, height
    requires_rasterization: bool = False


@dataclass
class ClipApplication:
    """Application of clipping to an element."""
    target_element: ET.Element
    clip_definition: ClipPathDefinition
    resolved_path: Optional[str] = None
    powerpoint_compatible: bool = True


class MaskingConverter(BaseConverter):
    """
    Converts SVG mask and clipPath elements to PowerPoint equivalents.
    
    This converter handles:
    1. Mask definitions with luminance and alpha masks
    2. ClipPath definitions with geometric clipping
    3. Application of masks and clips to target elements
    4. PowerPoint shape clipping conversion
    5. Complex mask rasterization when needed
    """
    
    supported_elements = ['mask', 'clipPath', 'defs']
    
    def __init__(self, services: ConversionServices):
        """
        Initialize MaskingConverter with dependency injection.

        Args:
            services: ConversionServices container with initialized services
        """
        super().__init__(services)

        # Storage for mask and clipPath definitions
        self.mask_definitions: Dict[str, MaskDefinition] = {}
        self.clippath_definitions: Dict[str, ClipPathDefinition] = {}

        # Track which elements have masks or clipping applied
        self.masked_elements: List[MaskApplication] = []
        self.clipped_elements: List[ClipApplication] = []

        # Initialize clipPath analyzer, boolean flattener, and custGeom generator
        self.clippath_analyzer = ClipPathAnalyzer(services)
        self.boolean_flattener = BooleanFlattener(services)
        self.custgeom_generator = CustGeomGenerator(services)
    
    def can_convert(self, element: ET.Element, context: Optional[ConversionContext] = None) -> bool:
        """Check if element can be converted by this converter."""
        if element.tag.endswith(('mask', 'clipPath')):
            return True
        
        # Check if element references a mask or clipPath
        mask_ref = element.get('mask')
        clip_ref = element.get('clip-path')
        
        return mask_ref is not None or clip_ref is not None
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG mask/clipPath elements or apply masking/clipping."""
        if element.tag.endswith('mask'):
            return self._process_mask_definition(element, context)
        elif element.tag.endswith('clipPath'):
            return self._process_clippath_definition(element, context)
        else:
            # Element with mask or clip-path reference
            return self._apply_masking_clipping(element, context)
    
    def _process_mask_definition(self, mask_element: ET.Element, context: ConversionContext) -> str:
        """Process a mask definition element."""
        mask_id = mask_element.get('id')
        if not mask_id:
            logger.warning("Mask element without id attribute")
            return ""
        
        # Parse mask properties
        mask_type_attr = mask_element.get('mask-type', 'luminance')
        mask_type = MaskType.LUMINANCE if mask_type_attr == 'luminance' else MaskType.ALPHA
        
        units = mask_element.get('maskUnits', 'objectBoundingBox')
        mask_units = mask_element.get('maskContentUnits', 'userSpaceOnUse')
        
        # Parse mask bounds
        x = self._parse_coordinate(mask_element.get('x', '-10%'), units == 'objectBoundingBox')
        y = self._parse_coordinate(mask_element.get('y', '-10%'), units == 'objectBoundingBox')
        width = self._parse_coordinate(mask_element.get('width', '120%'), units == 'objectBoundingBox')
        height = self._parse_coordinate(mask_element.get('height', '120%'), units == 'objectBoundingBox')
        
        opacity = float(mask_element.get('opacity', '1.0'))
        transform = mask_element.get('transform')
        
        # Collect content elements
        content_elements = list(mask_element)
        
        # Store mask definition
        self.mask_definitions[mask_id] = MaskDefinition(
            id=mask_id,
            mask_type=mask_type,
            units=units,
            mask_units=mask_units,
            x=x, y=y, width=width, height=height,
            content_elements=content_elements,
            opacity=opacity,
            transform=transform
        )
        
        logger.info(f"Processed mask definition: {mask_id}")
        return ""  # Definitions don't generate direct output
    
    def _process_clippath_definition(self, clippath_element: ET.Element, context: ConversionContext) -> str:
        """Process a clipPath definition element."""
        clip_id = clippath_element.get('id')
        if not clip_id:
            logger.warning("ClipPath element without id attribute")
            return ""
        
        units = clippath_element.get('clipPathUnits', 'userSpaceOnUse')
        clip_rule = clippath_element.get('clip-rule', 'nonzero')
        transform = clippath_element.get('transform')
        
        # Analyze clipPath content
        shapes = list(clippath_element)
        clipping_type = ClippingType.SHAPE_BASED
        path_data = None
        
        if len(shapes) == 1 and shapes[0].tag.endswith('path'):
            # Single path - can be PowerPoint compatible
            path_data = shapes[0].get('d')
            clipping_type = ClippingType.PATH_BASED
        elif len(shapes) == 1 and shapes[0].tag.endswith(('rect', 'circle', 'ellipse')):
            # Single basic shape - PowerPoint compatible
            clipping_type = ClippingType.SHAPE_BASED
        else:
            # Multiple shapes or complex content
            clipping_type = ClippingType.COMPLEX
        
        # Store clipPath definition
        self.clippath_definitions[clip_id] = ClipPathDefinition(
            id=clip_id,
            units=units,
            clip_rule=clip_rule,
            path_data=path_data,
            shapes=shapes,
            clipping_type=clipping_type,
            transform=transform
        )
        
        logger.info(f"Processed clipPath definition: {clip_id}")
        return ""  # Definitions don't generate direct output
    
    def _apply_masking_clipping(self, element: ET.Element, context: ConversionContext) -> str:
        """Apply masking and clipping to an element."""
        output_parts = []
        
        # Check for mask reference
        mask_ref = element.get('mask')
        if mask_ref:
            mask_output = self._apply_mask(element, mask_ref, context)
            if mask_output:
                output_parts.append(mask_output)
        
        # Check for clipPath reference
        clip_ref = element.get('clip-path')
        if clip_ref:
            clip_output = self._apply_clipping(element, clip_ref, context)
            if clip_output:
                output_parts.append(clip_output)
        
        return '\n'.join(output_parts)
    
    def _apply_mask(self, element: ET.Element, mask_ref: str, context: ConversionContext) -> str:
        """Apply a mask to an element."""
        # Parse mask reference (url(#maskId))
        mask_id = self._extract_reference_id(mask_ref)
        if not mask_id or mask_id not in self.mask_definitions:
            logger.warning(f"Referenced mask not found: {mask_id}")
            return ""
        
        mask_def = self.mask_definitions[mask_id]
        
        # Calculate resolved bounds for the mask
        element_bounds = self._get_element_bounds(element, context)
        if mask_def.units == 'objectBoundingBox':
            # Mask bounds are relative to element bounds
            resolved_bounds = (
                element_bounds[0] + mask_def.x * element_bounds[2],
                element_bounds[1] + mask_def.y * element_bounds[3],
                mask_def.width * element_bounds[2],
                mask_def.height * element_bounds[3]
            )
        else:
            # Mask bounds are in user space
            resolved_bounds = (mask_def.x, mask_def.y, mask_def.width, mask_def.height)
        
        # Determine if rasterization is required
        requires_rasterization = self._mask_requires_rasterization(mask_def)
        
        # Store mask application
        mask_app = MaskApplication(
            target_element=element,
            mask_definition=mask_def,
            resolved_bounds=resolved_bounds,
            requires_rasterization=requires_rasterization
        )
        self.masked_elements.append(mask_app)
        
        if requires_rasterization:
            return self._generate_rasterized_mask_output(mask_app, context)
        else:
            return self._generate_powerpoint_mask_output(mask_app, context)
    
    def _apply_clipping(self, element: ET.Element, clip_ref: str, context: ConversionContext) -> str:
        """Apply clipping to an element using the ClipPathAnalyzer for strategy selection."""
        # Analyze clipPath complexity
        analysis = self.clippath_analyzer.analyze_clippath(element, self.clippath_definitions, clip_ref)

        # Handle unsupported cases
        if analysis.complexity == ClipPathComplexity.UNSUPPORTED:
            logger.warning(f"Unsupported clipPath: {analysis.reason}")
            return self._generate_rasterized_clip_fallback(element, context)

        # Get the primary clipPath definition
        if not analysis.clip_chain:
            logger.warning(f"No valid clipPath chain found for {clip_ref}")
            return ""

        clip_def = analysis.clip_chain[0]
        resolved_path = None

        # Determine conversion strategy based on analysis
        if analysis.complexity == ClipPathComplexity.SIMPLE:
            # Simple case - direct conversion to custGeom
            logger.debug(f"Using simple clipPath conversion for {clip_def.id}")
            resolved_path = self._convert_simple_clippath(clip_def, context)

        elif analysis.complexity == ClipPathComplexity.NESTED:
            # Nested case - flatten with boolean operations
            logger.debug(f"Flattening nested clipPath chain for {clip_def.id}")
            if analysis.can_flatten:
                resolved_path = self.boolean_flattener.flatten_nested_clipaths(analysis.clip_chain)
                # If flattening failed (no boolean engine available), fall back to EMF
                if not resolved_path:
                    logger.warning(f"Boolean flattening failed for {clip_def.id}, falling back to EMF")
                    return self._generate_emf_clip_output(element, analysis, context)
            else:
                # Can't flatten - use EMF
                return self._generate_emf_clip_output(element, analysis, context)

        elif analysis.complexity == ClipPathComplexity.COMPLEX:
            # Complex case - use EMF if possible
            logger.debug(f"Using EMF for complex clipPath {clip_def.id}")
            if analysis.requires_emf:
                return self._generate_emf_clip_output(element, analysis, context)
            else:
                # Fallback to rasterization
                return self._generate_rasterized_clip_output_with_analysis(element, analysis, context)

        # Apply coordinate system transforms if needed
        if resolved_path and clip_def.units == 'objectBoundingBox':
            element_bounds = self._get_element_bounds(element, context)
            resolved_path = self._transform_path_to_object_bounds(resolved_path, element_bounds)

        # Apply clipPath transform if present
        if resolved_path and clip_def.transform:
            if hasattr(self.services, 'transform_parser'):
                matrix = self.services.transform_parser.parse_transform(clip_def.transform)
                resolved_path = self.services.transform_parser.apply_matrix_to_path(resolved_path, matrix)

        # Generate appropriate output based on complexity
        if resolved_path:
            clip_app = ClipApplication(
                target_element=element,
                clip_definition=clip_def,
                resolved_path=resolved_path,
                powerpoint_compatible=(analysis.complexity in [ClipPathComplexity.SIMPLE, ClipPathComplexity.NESTED])
            )
            self.clipped_elements.append(clip_app)

            if clip_app.powerpoint_compatible:
                return self._generate_powerpoint_clip_output(clip_app, context)
            else:
                return self._generate_emf_clip_output(element, analysis, context)

        return ""

    def _generate_powerpoint_clip_output(self, clip_app: 'ClipApplication',
                                        context: ConversionContext) -> str:
        """Generate PowerPoint-compatible clipping output."""
        element = clip_app.target_element
        resolved_path = clip_app.resolved_path

        # Check if resolved_path is custGeom XML
        if resolved_path.strip().startswith('<a:custGeom>'):
            # It's custGeom XML - wrap in shape with clipping
            return f"""<!-- PowerPoint Native CustGeom Clipping -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{context.get_next_shape_id()}" name="ClippedShape"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="0" y="0"/>
            <a:ext cx="914400" cy="914400"/>
        </a:xfrm>
        {resolved_path}
    </p:spPr>
</p:sp>"""

        else:
            # It's simple path data - use basic clipping shape
            return f"""<!-- PowerPoint Simple Path Clipping -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{context.get_next_shape_id()}" name="ClippingShape"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="0" y="0"/>
            <a:ext cx="914400" cy="914400"/>
        </a:xfrm>
        <!-- Path data: {resolved_path[:100]}... -->
    </p:spPr>
</p:sp>"""

    def _mask_requires_rasterization(self, mask_def: MaskDefinition) -> bool:
        """Determine if a mask requires rasterization for PowerPoint conversion."""
        # Check for complex content that can't be converted to PowerPoint masking
        for element in mask_def.content_elements:
            if element.tag.endswith(('image', 'text', 'tspan', 'textPath')):
                return True
            if element.tag.endswith('use'):
                return True
            if element.get('filter'):
                return True
            if self._has_complex_gradient(element):
                return True
        
        # Check for alpha masks (PowerPoint primarily supports luminance masks)
        if mask_def.mask_type == MaskType.ALPHA:
            return True
        
        return False
    
    def _has_complex_gradient(self, element: ET.Element) -> bool:
        """Check if element has complex gradients that require rasterization."""
        fill = element.get('fill', '')
        stroke = element.get('stroke', '')
        
        for color_ref in [fill, stroke]:
            if color_ref.startswith('url('):
                # Complex gradient reference - may need rasterization
                return True
        
        return False
    
    def _generate_powerpoint_mask_output(self, mask_app: MaskApplication, context: ConversionContext) -> str:
        """Generate PowerPoint-compatible mask output."""
        # PowerPoint masking is limited - often need to use shape intersection
        # or create clipping shapes
        
        return f"""<!-- PowerPoint Mask Application -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{context.get_next_shape_id()}" name="MaskedShape"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <!-- Mask bounds: {mask_app.resolved_bounds} -->
        <!-- Note: PowerPoint mask conversion may be approximate -->
        <a:xfrm>
            <a:off x="{int(self.services.unit_converter.convert_to_emu(mask_app.resolved_bounds[0]))}"
                   y="{int(self.services.unit_converter.convert_to_emu(mask_app.resolved_bounds[1]))}"/>
            <a:ext cx="{int(self.services.unit_converter.convert_to_emu(mask_app.resolved_bounds[2]))}"
                   cy="{int(self.services.unit_converter.convert_to_emu(mask_app.resolved_bounds[3]))}"/>
        </a:xfrm>
    </p:spPr>
</p:sp>"""
    
    def _generate_rasterized_mask_output(self, mask_app: MaskApplication, context: ConversionContext) -> str:
        """Generate output for rasterized mask (fallback for complex masks)."""
        return f"""<!-- Rasterized Mask Output -->
<!-- Complex mask requires image rasterization -->
<!-- Mask ID: {mask_app.mask_definition.id} -->
<!-- Target: {mask_app.target_element.tag} -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{context.get_next_shape_id()}" name="RasterizedMask"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <!-- Note: Requires external rasterization for full fidelity -->
</p:sp>"""
    
    def _generate_powerpoint_clip_output(self, clip_app: ClipApplication, context: ConversionContext) -> str:
        """Generate PowerPoint-compatible clipping output."""
        if not clip_app.resolved_path:
            return ""
        
        # Convert path to PowerPoint path format
        pptx_path = self._convert_svg_path_to_pptx(clip_app.resolved_path)
        
        return f"""<!-- PowerPoint Clipping Path -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{context.get_next_shape_id()}" name="ClippingShape"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:custGeom>
            <a:avLst/>
            <a:gdLst/>
            <a:ahLst/>
            <a:cxnLst/>
            <a:rect l="0" t="0" r="21600" b="21600"/>
            <a:pathLst>
                <a:path w="21600" h="21600">
                    {pptx_path}
                </a:path>
            </a:pathLst>
        </a:custGeom>
        <a:solidFill>
            <a:srgbClr val="FF0000"/>
        </a:solidFill>
    </p:spPr>
</p:sp>"""
    
    def _generate_rasterized_clip_output(self, clip_app: ClipApplication, context: ConversionContext) -> str:
        """Generate output for complex clipping that requires rasterization."""
        return f"""<!-- Rasterized Clipping Output -->
<!-- Complex clipping requires rasterization -->
<!-- ClipPath ID: {clip_app.clip_definition.id} -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{context.get_next_shape_id()}" name="ComplexClip"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <!-- Note: Requires external processing for complex clipping -->
</p:sp>"""
    
    def _parse_coordinate(self, value: str, is_percentage: bool) -> float:
        """Parse coordinate value, handling percentages."""
        if value.endswith('%'):
            return float(value[:-1]) / 100.0 if is_percentage else float(value[:-1])
        return self.services.unit_converter.convert_to_user_units(value)
    
    def _extract_reference_id(self, reference: str) -> Optional[str]:
        """Extract ID from URL reference like 'url(#id)'."""
        if reference.startswith('url(#') and reference.endswith(')'):
            return reference[5:-1]
        elif reference.startswith('#'):
            return reference[1:]
        return None
    
    def _get_element_bounds(self, element: ET.Element, context: ConversionContext) -> Tuple[float, float, float, float]:
        """Get bounding box of an element (x, y, width, height)."""
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

        # Extract bounds based on element type
        if tag == 'rect':
            x = float(element.get('x', '0'))
            y = float(element.get('y', '0'))
            width = float(element.get('width', '0'))
            height = float(element.get('height', '0'))
            return (x, y, width, height)

        elif tag == 'circle':
            cx = float(element.get('cx', '0'))
            cy = float(element.get('cy', '0'))
            r = float(element.get('r', '0'))
            return (cx - r, cy - r, 2 * r, 2 * r)

        elif tag == 'ellipse':
            cx = float(element.get('cx', '0'))
            cy = float(element.get('cy', '0'))
            rx = float(element.get('rx', '0'))
            ry = float(element.get('ry', '0'))
            return (cx - rx, cy - ry, 2 * rx, 2 * ry)

        elif tag == 'line':
            x1 = float(element.get('x1', '0'))
            y1 = float(element.get('y1', '0'))
            x2 = float(element.get('x2', '0'))
            y2 = float(element.get('y2', '0'))
            return (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

        elif tag == 'image':
            x = float(element.get('x', '0'))
            y = float(element.get('y', '0'))
            width = float(element.get('width', '0'))
            height = float(element.get('height', '0'))
            return (x, y, width, height)

        elif tag == 'path':
            # For path elements, we'd need to parse the 'd' attribute
            # and calculate actual bounds. For now, return reasonable defaults
            # This is a complex operation that would need proper path parsing
            return (0.0, 0.0, 100.0, 100.0)

        # Default bounding box for unknown elements
        return (0.0, 0.0, 100.0, 100.0)
    
    def _convert_shape_to_path(self, shape_element: ET.Element, context: ConversionContext) -> str:
        """Convert basic shapes to path data."""
        tag = shape_element.tag.split('}')[-1] if '}' in shape_element.tag else shape_element.tag
        
        if tag == 'rect':
            x = float(shape_element.get('x', '0'))
            y = float(shape_element.get('y', '0'))
            width = float(shape_element.get('width', '0'))
            height = float(shape_element.get('height', '0'))
            return f"M {x} {y} L {x+width} {y} L {x+width} {y+height} L {x} {y+height} Z"
        
        elif tag == 'circle':
            cx = float(shape_element.get('cx', '0'))
            cy = float(shape_element.get('cy', '0'))
            r = float(shape_element.get('r', '0'))
            # Create circle path with proper arc commands
            return f"M {cx-r} {cy} A {r} {r} 0 0 1 {cx+r} {cy} A {r} {r} 0 0 1 {cx-r} {cy} Z"
        
        elif tag == 'ellipse':
            cx = float(shape_element.get('cx', '0'))
            cy = float(shape_element.get('cy', '0'))
            rx = float(shape_element.get('rx', '0'))
            ry = float(shape_element.get('ry', '0'))
            return f"M {cx-rx} {cy} A {rx} {ry} 0 1 0 {cx+rx} {cy} A {rx} {ry} 0 1 0 {cx-rx} {cy} Z"
        
        return ""
    
    def _merge_complex_clip_paths(self, shapes: List[ET.Element], context: ConversionContext) -> str:
        """Merge multiple shapes into a single clipping path."""
        path_parts = []
        for shape in shapes:
            if shape.tag.endswith('path'):
                path_data = shape.get('d', '')
                if path_data:
                    path_parts.append(path_data)
            else:
                shape_path = self._convert_shape_to_path(shape, context)
                if shape_path:
                    path_parts.append(shape_path)
        
        return ' '.join(path_parts)
    
    def _transform_path_to_object_bounds(self, path: str, bounds: Tuple[float, float, float, float]) -> str:
        """Transform path coordinates from objectBoundingBox to user space."""
        # This would parse and transform the path coordinates
        # For now, return the path as-is
        return path
    
    def _convert_simple_clippath(self, clip_def: ClipPathDefinition, context: ConversionContext) -> str:
        """Convert a simple clipPath to custGeom or path string."""
        # Try to generate custGeom first (native PowerPoint clipping)
        if self.custgeom_generator.can_generate_custgeom(clip_def):
            try:
                custgeom_xml = self.custgeom_generator.generate_custgeom_xml(clip_def, context)
                logger.info(f"Generated custGeom for simple clipPath {clip_def.id}")
                return custgeom_xml
            except Exception as e:
                logger.warning(f"CustGeom generation failed for {clip_def.id}, falling back to path: {e}")

        # Fallback to simple path conversion
        if clip_def.path_data:
            return clip_def.path_data
        elif clip_def.shapes and len(clip_def.shapes) == 1:
            return self._convert_shape_to_path(clip_def.shapes[0], context)
        return ""

    def _generate_emf_clip_output(self, element: ET.Element, analysis: ClipPathAnalysis,
                                 context: ConversionContext) -> str:
        """Generate EMF output for complex clipping."""
        # Create EMF blob with clipping path
        emf_blob = EMFBlob(width=100, height=100)

        # For now, create a simple rectangle as placeholder
        # TODO: Implement proper path-based clipping when EMFBlob supports paths
        brush_handle = emf_blob.add_hatch("cross", color=0x808080, background=0xFFFFFF)
        emf_blob.fill_rectangle(10, 10, 80, 80, brush_handle)

        # Finalize EMF blob
        emf_data = emf_blob.finalize()

        # Create relationship manager and add EMF blob
        emf_manager = EMFRelationshipManager()
        rel_id = emf_manager.add_emf_blob(emf_data, f"clipPath_{analysis.clip_chain[0].id}.emf")

        logger.info(f"Generated EMF clipping for {analysis.reason} (relationship: {rel_id})")

        return f"""<!-- EMF Vector Clipping -->
<!-- Complexity: {analysis.complexity.value} -->
<!-- Reason: {analysis.reason} -->
<!-- EMF Relationship: {rel_id} -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{context.get_next_shape_id()}" name="EMFClippedShape"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:blipFill>
            <a:blip r:embed="{rel_id}"/>
            <a:stretch>
                <a:fillRect/>
            </a:stretch>
        </a:blipFill>
    </p:spPr>
</p:sp>"""

    def _generate_rasterized_clip_fallback(self, element: ET.Element, context: ConversionContext) -> str:
        """Generate rasterized fallback for unsupported clipping."""
        return f"""<!-- Rasterized Clipping Fallback -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{context.get_next_shape_id()}" name="RasterizedClip"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <!-- Requires external rasterization -->
</p:sp>"""

    def _generate_rasterized_clip_output_with_analysis(self, element: ET.Element,
                                                      analysis: ClipPathAnalysis,
                                                      context: ConversionContext) -> str:
        """Generate rasterized output with analysis details."""
        return f"""<!-- Rasterized Clipping Output -->
<!-- Analysis: {analysis.complexity.value} - {analysis.reason} -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{context.get_next_shape_id()}" name="RasterizedComplexClip"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <!-- Nodes: {analysis.estimated_nodes}, Has Text: {analysis.has_text}, Has Filters: {analysis.has_filters} -->
</p:sp>"""

    def _convert_svg_path_to_pptx(self, svg_path: str) -> str:
        """Convert SVG path commands to PowerPoint path format."""
        if not svg_path:
            return ""

        # PowerPoint uses a coordinate system of 0-21600 for custom geometry
        # We need to parse SVG path data and convert to PowerPoint path elements

        path_elements = []
        import re

        # Simple path parsing - handles M, L, Z commands
        # For production, should use a proper SVG path parser
        commands = re.findall(r'[MmLlHhVvCcSsQqTtAaZz][^MmLlHhVvCcSsQqTtAaZz]*', svg_path)

        current_x, current_y = 0, 0

        for command in commands:
            cmd = command[0]
            params = re.findall(r'-?\d*\.?\d+', command[1:])
            params = [float(p) for p in params]

            if cmd in 'Mm':  # MoveTo
                if len(params) >= 2:
                    if cmd == 'M':  # Absolute
                        current_x, current_y = params[0], params[1]
                    else:  # Relative
                        current_x += params[0]
                        current_y += params[1]

                    # Convert to PowerPoint coordinates (assuming viewBox 0-100 maps to 0-21600)
                    ppt_x = int(current_x * 216)
                    ppt_y = int(current_y * 216)
                    path_elements.append(f'<a:moveTo><a:pt x="{ppt_x}" y="{ppt_y}"/></a:moveTo>')

            elif cmd in 'Ll':  # LineTo
                if len(params) >= 2:
                    if cmd == 'L':  # Absolute
                        current_x, current_y = params[0], params[1]
                    else:  # Relative
                        current_x += params[0]
                        current_y += params[1]

                    ppt_x = int(current_x * 216)
                    ppt_y = int(current_y * 216)
                    path_elements.append(f'<a:lnTo><a:pt x="{ppt_x}" y="{ppt_y}"/></a:lnTo>')

            elif cmd in 'Hh':  # Horizontal LineTo
                if len(params) >= 1:
                    if cmd == 'H':  # Absolute
                        current_x = params[0]
                    else:  # Relative
                        current_x += params[0]

                    ppt_x = int(current_x * 216)
                    ppt_y = int(current_y * 216)
                    path_elements.append(f'<a:lnTo><a:pt x="{ppt_x}" y="{ppt_y}"/></a:lnTo>')

            elif cmd in 'Vv':  # Vertical LineTo
                if len(params) >= 1:
                    if cmd == 'V':  # Absolute
                        current_y = params[0]
                    else:  # Relative
                        current_y += params[0]

                    ppt_x = int(current_x * 216)
                    ppt_y = int(current_y * 216)
                    path_elements.append(f'<a:lnTo><a:pt x="{ppt_x}" y="{ppt_y}"/></a:lnTo>')

            elif cmd in 'Zz':  # ClosePath
                path_elements.append('<a:close/>')

        return ''.join(path_elements)
    
    def get_mask_definitions(self) -> Dict[str, MaskDefinition]:
        """Get all processed mask definitions."""
        return self.mask_definitions.copy()
    
    def get_clippath_definitions(self) -> Dict[str, ClipPathDefinition]:
        """Get all processed clipPath definitions."""
        return self.clippath_definitions.copy()
    
    def get_masked_elements(self) -> List[MaskApplication]:
        """Get all elements with masks applied."""
        return self.masked_elements.copy()
    
    def get_clipped_elements(self) -> List[ClipApplication]:
        """Get all elements with clipping applied."""
        return self.clipped_elements.copy()
    
    def reset(self):
        """Reset converter state for new conversion."""
        self.mask_definitions.clear()
        self.clippath_definitions.clear()
        self.masked_elements.clear()
        self.clipped_elements.clear()
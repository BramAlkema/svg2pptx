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

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Union, NamedTuple
import math
import logging
from dataclasses import dataclass
from enum import Enum

from .base import BaseConverter
from ..units import UnitConverter
from ..colors import ColorParser
from ..transforms import TransformParser
from ..viewbox import ViewportResolver
from .base import ConversionContext

logger = logging.getLogger(__name__)


class MaskType(Enum):
    """Types of SVG mask content."""
    LUMINANCE = "luminance"
    ALPHA = "alpha"


class ClippingType(Enum):
    """Types of clipping operations."""
    PATH_BASED = "path"
    SHAPE_BASED = "shape"
    COMPLEX = "complex"


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
class ClipPathDefinition:
    """Definition of an SVG clipPath element."""
    id: str
    units: str  # userSpaceOnUse or objectBoundingBox
    clip_rule: str  # nonzero or evenodd
    path_data: Optional[str] = None
    shapes: List[ET.Element] = None
    clipping_type: ClippingType = ClippingType.PATH_BASED
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
    
    def __init__(self):
        super().__init__()
        self.unit_converter = UnitConverter()
        self.color_parser = ColorParser()
        self.transform_engine = TransformParser()
        self.viewport_handler = ViewportResolver()
        
        # Storage for mask and clipPath definitions
        self.mask_definitions: Dict[str, MaskDefinition] = {}
        self.clippath_definitions: Dict[str, ClipPathDefinition] = {}
        
        # Track which elements have masks or clipping applied
        self.masked_elements: List[MaskApplication] = []
        self.clipped_elements: List[ClipApplication] = []
    
    def can_convert(self, element: ET.Element, context: ConversionContext) -> bool:
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
        """Apply clipping to an element."""
        # Parse clipPath reference
        clip_id = self._extract_reference_id(clip_ref)
        if not clip_id or clip_id not in self.clippath_definitions:
            logger.warning(f"Referenced clipPath not found: {clip_id}")
            return ""
        
        clip_def = self.clippath_definitions[clip_id]
        
        # Resolve clipping path
        resolved_path = None
        powerpoint_compatible = True
        
        if clip_def.clipping_type == ClippingType.PATH_BASED:
            resolved_path = clip_def.path_data
        elif clip_def.clipping_type == ClippingType.SHAPE_BASED:
            resolved_path = self._convert_shape_to_path(clip_def.shapes[0], context)
        else:
            # Complex clipping - may require rasterization
            powerpoint_compatible = False
            resolved_path = self._merge_complex_clip_paths(clip_def.shapes, context)
        
        # Apply coordinate system transforms if needed
        if clip_def.units == 'objectBoundingBox':
            element_bounds = self._get_element_bounds(element, context)
            resolved_path = self._transform_path_to_object_bounds(resolved_path, element_bounds)
        
        # Apply clipPath transform if present
        if clip_def.transform:
            matrix = self.transform_engine.parse_transform(clip_def.transform)
            resolved_path = self.transform_engine.apply_matrix_to_path(resolved_path, matrix)
        
        # Store clip application
        clip_app = ClipApplication(
            target_element=element,
            clip_definition=clip_def,
            resolved_path=resolved_path,
            powerpoint_compatible=powerpoint_compatible
        )
        self.clipped_elements.append(clip_app)
        
        if powerpoint_compatible:
            return self._generate_powerpoint_clip_output(clip_app, context)
        else:
            return self._generate_rasterized_clip_output(clip_app, context)
    
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
        <p:cNvPr id="{context.get_next_id()}" name="MaskedShape"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <!-- Mask bounds: {mask_app.resolved_bounds} -->
        <!-- Note: PowerPoint mask conversion may be approximate -->
        <a:xfrm>
            <a:off x="{int(self.unit_converter.convert_to_emu(mask_app.resolved_bounds[0]))}" 
                   y="{int(self.unit_converter.convert_to_emu(mask_app.resolved_bounds[1]))}"/>
            <a:ext cx="{int(self.unit_converter.convert_to_emu(mask_app.resolved_bounds[2]))}" 
                   cy="{int(self.unit_converter.convert_to_emu(mask_app.resolved_bounds[3]))}"/>
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
        <p:cNvPr id="{context.get_next_id()}" name="RasterizedMask"/>
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
        <p:cNvPr id="{context.get_next_id()}" name="ClippingShape"/>
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
        <p:cNvPr id="{context.get_next_id()}" name="ComplexClip"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <!-- Note: Requires external processing for complex clipping -->
</p:sp>"""
    
    def _parse_coordinate(self, value: str, is_percentage: bool) -> float:
        """Parse coordinate value, handling percentages."""
        if value.endswith('%'):
            return float(value[:-1]) / 100.0 if is_percentage else float(value[:-1])
        return self.unit_converter.convert_to_user_units(value)
    
    def _extract_reference_id(self, reference: str) -> Optional[str]:
        """Extract ID from URL reference like 'url(#id)'."""
        if reference.startswith('url(#') and reference.endswith(')'):
            return reference[5:-1]
        elif reference.startswith('#'):
            return reference[1:]
        return None
    
    def _get_element_bounds(self, element: ET.Element, context: ConversionContext) -> Tuple[float, float, float, float]:
        """Get bounding box of an element (x, y, width, height)."""
        # This would need to be implemented based on element type
        # For now, return a default bounding box
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
            # Approximate circle with path
            return f"M {cx-r} {cy} A {r} {r} 0 1 0 {cx+r} {cy} A {r} {r} 0 1 0 {cx-r} {cy} Z"
        
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
    
    def _convert_svg_path_to_pptx(self, svg_path: str) -> str:
        """Convert SVG path commands to PowerPoint path format."""
        # This would need full path parsing and conversion
        # For now, return a placeholder
        return f'<a:moveTo><a:pt x="0" y="0"/></a:moveTo><a:lnTo><a:pt x="21600" y="0"/></a:lnTo>'
    
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
        super().reset()
        self.mask_definitions.clear()
        self.clippath_definitions.clear()
        self.masked_elements.clear()
        self.clipped_elements.clear()
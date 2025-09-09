#!/usr/bin/env python3
"""
Universal Viewport & Aspect Ratio Handler for SVG2PPTX

This module provides centralized, robust viewBox and preserveAspectRatio
resolution with EMU viewport mapping. Handles proper scaling and cropping
for all SVG content with crop/fit modes (meet/slice).

Key Features:
- Complete viewBox parsing and validation
- preserveAspectRatio support (meet, slice, none)
- Transform matrix generation for viewport scaling
- EMU coordinate system integration
- Aspect ratio preservation with alignment
- Clipping calculations for slice mode
- Integration with Universal Unit Converter

SVG Viewport Reference:
- viewBox="min-x min-y width height"  
- preserveAspectRatio="align meetOrSlice"
- Default: preserveAspectRatio="xMidYMid meet"
"""

import re
import math
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import xml.etree.ElementTree as ET

from .units import UnitConverter, ViewportContext


class AspectRatioAlign(Enum):
    """Aspect ratio alignment values."""
    NONE = "none"
    X_MIN_Y_MIN = "xMinYMin"
    X_MID_Y_MIN = "xMidYMin"
    X_MAX_Y_MIN = "xMaxYMin"
    X_MIN_Y_MID = "xMinYMid"
    X_MID_Y_MID = "xMidYMid"  # Default
    X_MAX_Y_MID = "xMaxYMid"
    X_MIN_Y_MAX = "xMinYMax"
    X_MID_Y_MAX = "xMidYMax"
    X_MAX_Y_MAX = "xMaxYMax"


class MeetOrSlice(Enum):
    """Meet or slice scaling behavior."""
    MEET = "meet"    # Scale to fit entirely within viewport (letterbox/pillarbox)
    SLICE = "slice"  # Scale to fill entire viewport (crop content)


@dataclass
class ViewBoxInfo:
    """Parsed viewBox information."""
    min_x: float
    min_y: float
    width: float  
    height: float
    
    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio (width/height)."""
        return self.width / self.height if self.height > 0 else 1.0
    
    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Return bounds as (min_x, min_y, max_x, max_y)."""
        return (self.min_x, self.min_y, 
                self.min_x + self.width, self.min_y + self.height)


@dataclass  
class ViewportDimensions:
    """Target viewport dimensions in EMUs."""
    width: int   # EMU width
    height: int  # EMU height
    
    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio (width/height)."""
        return self.width / self.height if self.height > 0 else 1.0


@dataclass
class ViewportMapping:
    """Complete viewport mapping result."""
    # Transform matrix components
    scale_x: float
    scale_y: float
    translate_x: float
    translate_y: float
    
    # Viewport information
    viewport_width: int   # EMU
    viewport_height: int  # EMU
    content_width: int    # EMU (after scaling)
    content_height: int   # EMU (after scaling)
    
    # Clipping information (for slice mode)
    clip_needed: bool
    clip_x: float = 0.0   # SVG coordinates
    clip_y: float = 0.0
    clip_width: float = 0.0
    clip_height: float = 0.0
    
    @property
    def transform_matrix(self) -> Tuple[float, float, float, float, float, float]:
        """Return 2D transform matrix (a, b, c, d, e, f)."""
        return (self.scale_x, 0, 0, self.scale_y, self.translate_x, self.translate_y)
    
    def svg_to_emu(self, x: float, y: float) -> Tuple[int, int]:
        """Transform SVG coordinates to EMU using this mapping."""
        # Apply transform matrix
        transformed_x = x * self.scale_x + self.translate_x
        transformed_y = y * self.scale_y + self.translate_y
        return int(transformed_x), int(transformed_y)


class ViewportResolver:
    """Resolves SVG viewport and aspect ratio calculations."""
    
    def __init__(self, unit_converter: Optional[UnitConverter] = None):
        """
        Initialize viewport resolver.
        
        Args:
            unit_converter: Unit converter instance for dimension parsing
        """
        self.unit_converter = unit_converter or UnitConverter()
    
    def parse_viewbox(self, viewbox_str: str) -> Optional[ViewBoxInfo]:
        """
        Parse SVG viewBox attribute.
        
        Args:
            viewbox_str: viewBox attribute value
            
        Returns:
            ViewBoxInfo or None if invalid
            
        Examples:
            >>> resolver.parse_viewbox("0 0 100 200")
            ViewBoxInfo(min_x=0, min_y=0, width=100, height=200)
            >>> resolver.parse_viewbox("10,20,300,400")  
            ViewBoxInfo(min_x=10, min_y=20, width=300, height=400)
        """
        if not viewbox_str or not viewbox_str.strip():
            return None
        
        # Clean and split viewbox string
        viewbox_str = viewbox_str.strip()
        # Replace commas with spaces for consistent parsing
        parts = re.split(r'[,\s]+', viewbox_str)
        
        if len(parts) != 4:
            return None
        
        try:
            min_x, min_y, width, height = [float(part) for part in parts]
            
            # Validate dimensions
            if width <= 0 or height <= 0:
                return None
                
            return ViewBoxInfo(min_x, min_y, width, height)
            
        except (ValueError, TypeError):
            return None
    
    def parse_preserve_aspect_ratio(self, par_str: str) -> Tuple[AspectRatioAlign, MeetOrSlice]:
        """
        Parse preserveAspectRatio attribute.
        
        Args:
            par_str: preserveAspectRatio attribute value
            
        Returns:
            Tuple of (alignment, meet_or_slice)
            
        Examples:
            >>> resolver.parse_preserve_aspect_ratio("xMidYMid meet")
            (AspectRatioAlign.X_MID_Y_MID, MeetOrSlice.MEET)
            >>> resolver.parse_preserve_aspect_ratio("none")
            (AspectRatioAlign.NONE, MeetOrSlice.MEET)
        """
        if not par_str or not par_str.strip():
            return AspectRatioAlign.X_MID_Y_MID, MeetOrSlice.MEET
        
        parts = par_str.strip().lower().split()
        
        # Parse alignment
        align = AspectRatioAlign.X_MID_Y_MID  # Default
        meet_slice = MeetOrSlice.MEET  # Default
        
        for part in parts:
            # Check for alignment values
            for alignment in AspectRatioAlign:
                if part == alignment.value.lower():
                    align = alignment
                    break
            
            # Check for meet/slice
            if part == "meet":
                meet_slice = MeetOrSlice.MEET
            elif part == "slice":
                meet_slice = MeetOrSlice.SLICE
        
        return align, meet_slice
    
    def extract_viewport_from_svg(self, svg_element: ET.Element,
                                 context: Optional[ViewportContext] = None) -> Tuple[Optional[ViewBoxInfo], ViewportDimensions]:
        """
        Extract viewport information from SVG element.
        
        Args:
            svg_element: SVG root element
            context: Viewport context for unit conversion
            
        Returns:
            Tuple of (viewbox_info, viewport_dimensions_emu)
        """
        if context is None:
            context = ViewportContext()
        
        # Parse viewBox if present
        viewbox_str = svg_element.get('viewBox', '')
        viewbox = self.parse_viewbox(viewbox_str) if viewbox_str else None
        
        # Parse viewport dimensions
        width_str = svg_element.get('width', '800px')
        height_str = svg_element.get('height', '600px')
        
        # Convert to EMU using unit converter
        width_emu = self.unit_converter.to_emu(width_str, context)
        height_emu = self.unit_converter.to_emu(height_str, context)
        
        viewport_dims = ViewportDimensions(width_emu, height_emu)
        
        return viewbox, viewport_dims
    
    def calculate_viewport_mapping(self, 
                                 viewbox: Optional[ViewBoxInfo],
                                 viewport: ViewportDimensions,
                                 align: AspectRatioAlign = AspectRatioAlign.X_MID_Y_MID,
                                 meet_slice: MeetOrSlice = MeetOrSlice.MEET) -> ViewportMapping:
        """
        Calculate complete viewport mapping with transform matrix.
        
        Args:
            viewbox: Parsed viewBox information (None = no viewBox)
            viewport: Target viewport dimensions in EMU
            align: Aspect ratio alignment
            meet_slice: Meet or slice behavior
            
        Returns:
            Complete viewport mapping with transform matrix
        """
        # If no viewBox, assume identity mapping
        if viewbox is None:
            return ViewportMapping(
                scale_x=1.0,
                scale_y=1.0, 
                translate_x=0.0,
                translate_y=0.0,
                viewport_width=viewport.width,
                viewport_height=viewport.height,
                content_width=viewport.width,
                content_height=viewport.height,
                clip_needed=False
            )
        
        # Calculate scale factors for perfect fit
        scale_x = viewport.width / viewbox.width
        scale_y = viewport.height / viewbox.height
        
        # Handle aspect ratio preservation
        if align == AspectRatioAlign.NONE:
            # No aspect ratio preservation - stretch to fill
            final_scale_x = scale_x
            final_scale_y = scale_y
            translate_x = -viewbox.min_x * final_scale_x
            translate_y = -viewbox.min_y * final_scale_y
            content_width = viewport.width
            content_height = viewport.height
            clip_needed = False
            
        else:
            # Preserve aspect ratio
            if meet_slice == MeetOrSlice.MEET:
                # Meet: scale to fit entirely (may have letterbox/pillarbox)
                uniform_scale = min(scale_x, scale_y)
            else:
                # Slice: scale to fill entirely (may crop content)
                uniform_scale = max(scale_x, scale_y)
            
            final_scale_x = uniform_scale
            final_scale_y = uniform_scale
            
            # Calculate content dimensions after scaling
            scaled_width = viewbox.width * uniform_scale
            scaled_height = viewbox.height * uniform_scale
            content_width = int(scaled_width)
            content_height = int(scaled_height)
            
            # Calculate alignment offset
            offset_x, offset_y = self._calculate_alignment_offset(
                viewport.width, viewport.height,
                scaled_width, scaled_height,
                align
            )
            
            # Base translation (viewBox offset)
            translate_x = -viewbox.min_x * uniform_scale + offset_x
            translate_y = -viewbox.min_y * uniform_scale + offset_y
            
            # Determine if clipping is needed (slice mode with overflow)
            clip_needed = (meet_slice == MeetOrSlice.SLICE and 
                          (scaled_width > viewport.width or scaled_height > viewport.height))
        
        return ViewportMapping(
            scale_x=final_scale_x,
            scale_y=final_scale_y,
            translate_x=translate_x,
            translate_y=translate_y,
            viewport_width=viewport.width,
            viewport_height=viewport.height,
            content_width=content_width,
            content_height=content_height,
            clip_needed=clip_needed
        )
    
    def _calculate_alignment_offset(self, viewport_width: int, viewport_height: int,
                                  content_width: float, content_height: float,
                                  align: AspectRatioAlign) -> Tuple[float, float]:
        """Calculate alignment offset for aspect ratio preservation."""
        extra_width = viewport_width - content_width
        extra_height = viewport_height - content_height
        
        # X alignment
        if align.value.startswith('xMin'):
            offset_x = 0
        elif align.value.startswith('xMax'):
            offset_x = extra_width
        else:  # xMid
            offset_x = extra_width / 2
        
        # Y alignment  
        if 'YMin' in align.value:
            offset_y = 0
        elif 'YMax' in align.value:
            offset_y = extra_height
        else:  # YMid
            offset_y = extra_height / 2
        
        return offset_x, offset_y
    
    def resolve_svg_viewport(self, svg_element: ET.Element,
                           target_width_emu: Optional[int] = None,
                           target_height_emu: Optional[int] = None,
                           context: Optional[ViewportContext] = None) -> ViewportMapping:
        """
        Complete SVG viewport resolution pipeline.
        
        Args:
            svg_element: SVG root element
            target_width_emu: Override target width (None = use SVG width)
            target_height_emu: Override target height (None = use SVG height)
            context: Viewport context for unit conversion
            
        Returns:
            Complete viewport mapping ready for use
        """
        # Extract viewport information
        viewbox, viewport_dims = self.extract_viewport_from_svg(svg_element, context)
        
        # Override target dimensions if specified
        if target_width_emu is not None:
            viewport_dims.width = target_width_emu
        if target_height_emu is not None:
            viewport_dims.height = target_height_emu
        
        # Parse preserveAspectRatio
        par_str = svg_element.get('preserveAspectRatio', 'xMidYMid meet')
        align, meet_slice = self.parse_preserve_aspect_ratio(par_str)
        
        # Calculate complete mapping
        return self.calculate_viewport_mapping(viewbox, viewport_dims, align, meet_slice)
    
    def create_clip_path(self, mapping: ViewportMapping) -> Optional[str]:
        """
        Create SVG clipPath definition if clipping is needed.
        
        Args:
            mapping: Viewport mapping result
            
        Returns:
            SVG clipPath element string or None
        """
        if not mapping.clip_needed:
            return None
        
        # Calculate clip rectangle in EMU coordinates
        clip_x = 0  # Clip to viewport bounds
        clip_y = 0
        clip_width = mapping.viewport_width
        clip_height = mapping.viewport_height
        
        return f'''<clipPath id="viewport-clip">
    <rect x="{clip_x}" y="{clip_y}" width="{clip_width}" height="{clip_height}"/>
</clipPath>'''
    
    def debug_viewport_info(self, svg_element: ET.Element,
                          context: Optional[ViewportContext] = None) -> Dict[str, Any]:
        """
        Debug viewport resolution with detailed information.
        
        Returns comprehensive viewport analysis for troubleshooting.
        """
        viewbox, viewport_dims = self.extract_viewport_from_svg(svg_element, context)
        
        par_str = svg_element.get('preserveAspectRatio', 'xMidYMid meet')
        align, meet_slice = self.parse_preserve_aspect_ratio(par_str)
        
        mapping = self.calculate_viewport_mapping(viewbox, viewport_dims, align, meet_slice)
        
        return {
            'svg_attributes': {
                'width': svg_element.get('width'),
                'height': svg_element.get('height'),
                'viewBox': svg_element.get('viewBox'),
                'preserveAspectRatio': svg_element.get('preserveAspectRatio', 'default')
            },
            'parsed_viewbox': {
                'present': viewbox is not None,
                'min_x': viewbox.min_x if viewbox else None,
                'min_y': viewbox.min_y if viewbox else None,
                'width': viewbox.width if viewbox else None,
                'height': viewbox.height if viewbox else None,
                'aspect_ratio': viewbox.aspect_ratio if viewbox else None
            },
            'viewport_dimensions_emu': {
                'width': viewport_dims.width,
                'height': viewport_dims.height,
                'aspect_ratio': viewport_dims.aspect_ratio
            },
            'aspect_ratio_settings': {
                'align': align.value,
                'meet_or_slice': meet_slice.value
            },
            'calculated_mapping': {
                'scale_x': mapping.scale_x,
                'scale_y': mapping.scale_y,
                'translate_x': mapping.translate_x,
                'translate_y': mapping.translate_y,
                'content_size_emu': (mapping.content_width, mapping.content_height),
                'clip_needed': mapping.clip_needed,
                'transform_matrix': mapping.transform_matrix
            }
        }


# Global resolver instance for convenient access  
default_resolver = ViewportResolver()

# Convenience functions for direct usage
def parse_viewbox(viewbox_str: str) -> Optional[ViewBoxInfo]:
    """Parse viewBox using default resolver."""
    return default_resolver.parse_viewbox(viewbox_str)

def resolve_svg_viewport(svg_element: ET.Element, **kwargs) -> ViewportMapping:
    """Resolve SVG viewport using default resolver."""
    return default_resolver.resolve_svg_viewport(svg_element, **kwargs)
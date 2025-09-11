#!/usr/bin/env python3
"""
Enhanced SVG to PowerPoint conversion with multi-slide support.

This module extends the existing svg2pptx functionality to support
multi-slide presentations, animation sequences, and batch conversions
while maintaining backward compatibility.
"""

import json
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Any, Union

from lxml import etree as ET

# Import existing conversion infrastructure
from .svg2drawingml import convert_svg_to_drawingml
from .svg2pptx_json_v2 import convert_svg_to_pptx as convert_single_slide
from .converters.base import ConversionContext

# Import new multi-slide infrastructure
from .multislide.document import MultiSlideDocument, SlideContent, SlideType
from .multislide.detection import SlideDetector, SlideBoundary


class MultiSlideConverter:
    """
    Enhanced SVG to PowerPoint converter with multi-slide support.
    
    This converter can handle:
    - Single SVG files with slide boundary detection
    - Animation sequences converted to slide sequences  
    - Multiple SVG files converted to a single presentation
    - Backward compatibility with existing single-slide conversion
    """
    
    def __init__(self, 
                 enable_multislide_detection: bool = True,
                 animation_threshold: int = 3,
                 template_path: Optional[Path] = None):
        """
        Initialize multi-slide converter.
        
        Args:
            enable_multislide_detection: Enable automatic slide boundary detection
            animation_threshold: Minimum animations for slide sequence conversion
            template_path: Optional PPTX template path
        """
        self.enable_multislide_detection = enable_multislide_detection
        self.template_path = template_path
        
        # Initialize detectors
        self.slide_detector = SlideDetector(
            animation_threshold=animation_threshold
        )
        
        # Conversion statistics
        self.conversion_stats = {}
    
    def convert_svg_to_pptx(self, 
                           svg_input: Union[str, Path, ET.Element, List[Path]],
                           output_path: Path,
                           options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convert SVG(s) to PowerPoint presentation.
        
        Args:
            svg_input: SVG file path, element, or list of SVG files
            output_path: Output PPTX file path
            options: Conversion options
            
        Returns:
            Conversion result with statistics
        """
        options = options or {}
        
        # Initialize statistics
        self.conversion_stats = {
            'input_type': 'unknown',
            'slide_count': 0,
            'conversion_time': 0,
            'multislide_strategy': None,
            'boundaries_detected': 0
        }
        
        # Handle different input types
        if isinstance(svg_input, list):
            return self._convert_multiple_svgs(svg_input, output_path, options)
        elif isinstance(svg_input, (str, Path)):
            return self._convert_single_svg_file(Path(svg_input), output_path, options)
        elif isinstance(svg_input, ET.Element):
            return self._convert_svg_element(svg_input, output_path, options)
        else:
            raise TypeError(f"Unsupported input type: {type(svg_input)}")
    
    def _convert_single_svg_file(self, 
                                svg_path: Path, 
                                output_path: Path,
                                options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert single SVG file to PPTX."""
        self.conversion_stats['input_type'] = 'single_file'
        
        if not svg_path.exists():
            raise FileNotFoundError(f"SVG file not found: {svg_path}")
        
        # Parse SVG
        try:
            tree = ET.parse(svg_path)
            svg_root = tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"Invalid SVG file: {e}")
        
        return self._convert_svg_element(svg_root, output_path, options)
    
    def _convert_svg_element(self, 
                           svg_root: ET.Element,
                           output_path: Path, 
                           options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert SVG element to PPTX with multi-slide detection."""
        self.conversion_stats['input_type'] = 'svg_element'
        
        # Check if multi-slide detection is enabled and needed
        if self.enable_multislide_detection:
            boundaries = self.slide_detector.detect_boundaries(svg_root)
            strategy = self.slide_detector.recommend_conversion_strategy(boundaries)
            
            self.conversion_stats['boundaries_detected'] = len(boundaries)
            self.conversion_stats['multislide_strategy'] = strategy['strategy']
            
            # Decide conversion path
            if boundaries and strategy['confidence'] > 0.7:
                return self._convert_to_multislide(svg_root, output_path, boundaries, options)
        
        # Fall back to single slide conversion
        return self._convert_to_single_slide(svg_root, output_path, options)
    
    def _convert_multiple_svgs(self, 
                              svg_paths: List[Path],
                              output_path: Path,
                              options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert multiple SVG files to single multi-slide PPTX."""
        self.conversion_stats['input_type'] = 'multiple_files'
        
        if not svg_paths:
            raise ValueError("No SVG files provided")
        
        # Initialize multi-slide document
        doc = MultiSlideDocument(
            title=options.get('title', f"SVG Presentation ({len(svg_paths)} slides)"),
            template_path=self.template_path
        )
        
        successful_conversions = 0
        
        # Convert each SVG to a slide
        for i, svg_path in enumerate(svg_paths, 1):
            try:
                if not svg_path.exists():
                    print(f"Warning: SVG file not found: {svg_path}")
                    continue
                
                # Parse SVG
                tree = ET.parse(svg_path)
                svg_root = tree.getroot()
                
                # Add as slide
                slide_title = options.get('slide_titles', {}).get(str(i)) or svg_path.stem
                doc.add_svg_slide(
                    svg_element=svg_root,
                    title=slide_title
                )
                successful_conversions += 1
                
            except Exception as e:
                print(f"Warning: Failed to convert {svg_path}: {e}")
                # Add error slide
                doc.add_slide(
                    content=f'<!-- Conversion failed for {svg_path.name}: {e} -->',
                    title=f"Error - {svg_path.name}"
                )
        
        # Generate PPTX
        doc.generate_pptx(output_path)
        
        self.conversion_stats['slide_count'] = len(doc.slides)
        self.conversion_stats['successful_conversions'] = successful_conversions
        self.conversion_stats['failed_conversions'] = len(svg_paths) - successful_conversions
        
        return {
            'success': True,
            'output_path': str(output_path),
            'slide_count': len(doc.slides),
            'conversion_type': 'multi_file_batch',
            'statistics': self.conversion_stats
        }
    
    def _convert_to_multislide(self, 
                              svg_root: ET.Element,
                              output_path: Path,
                              boundaries: List[SlideBoundary],
                              options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert SVG to multi-slide PPTX using detected boundaries."""
        
        # Initialize multi-slide document
        doc = MultiSlideDocument(
            title=options.get('title', "SVG Multi-Slide Presentation"),
            template_path=self.template_path
        )
        
        # Generate slide plan
        slide_plan = self.slide_detector.generate_slide_plan(svg_root, boundaries)
        
        # Convert based on strategy
        strategy = slide_plan['strategy']['strategy']
        
        if strategy == 'animation_sequence':
            self._convert_animation_sequence(svg_root, doc, boundaries, options)
        elif strategy == 'nested_pages':
            self._convert_nested_pages(svg_root, doc, boundaries, options)
        elif strategy == 'layer_slides':
            self._convert_layer_slides(svg_root, doc, boundaries, options)
        else:
            # Generic boundary-based conversion
            self._convert_generic_boundaries(svg_root, doc, boundaries, options)
        
        # Generate PPTX
        doc.generate_pptx(output_path)
        
        self.conversion_stats['slide_count'] = len(doc.slides)
        
        return {
            'success': True,
            'output_path': str(output_path),
            'slide_count': len(doc.slides),
            'conversion_type': 'multislide',
            'strategy': strategy,
            'boundaries': len(boundaries),
            'statistics': self.conversion_stats
        }
    
    def _convert_to_single_slide(self, 
                               svg_root: ET.Element,
                               output_path: Path,
                               options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert SVG to single-slide PPTX using existing converter."""
        
        # Use existing single-slide conversion
        # Create temporary SVG file for compatibility
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as temp_svg:
            temp_svg_path = Path(temp_svg.name)
            temp_svg.write(ET.tostring(svg_root, encoding='unicode'))
        
        try:
            # Call existing converter
            result = convert_single_slide(temp_svg_path, output_path)
            
            self.conversion_stats['slide_count'] = 1
            
            return {
                'success': True,
                'output_path': str(output_path),
                'slide_count': 1,
                'conversion_type': 'single_slide_fallback',
                'statistics': self.conversion_stats
            }
            
        finally:
            # Clean up temporary file
            if temp_svg_path.exists():
                temp_svg_path.unlink()
    
    def _convert_animation_sequence(self, 
                                  svg_root: ET.Element,
                                  doc: MultiSlideDocument,
                                  boundaries: List[SlideBoundary],
                                  options: Dict[str, Any]):
        """Convert animation sequence to slide sequence."""
        
        # Extract animation keyframes
        animation_boundaries = [b for b in boundaries if b.boundary_type.value == 'animation_keyframe']
        
        if not animation_boundaries:
            # Fallback to single slide
            doc.add_svg_slide(svg_root, title="Animation")
            return
        
        # Create slides for each animation state
        base_title = options.get('base_title', 'Animation')
        
        # Add initial state
        doc.add_svg_slide(svg_root, title=f"{base_title} - Initial")
        
        # Add keyframe states
        for i, boundary in enumerate(animation_boundaries, 1):
            # For now, add the same content with different title
            # Full implementation would extract animation states
            doc.add_svg_slide(
                svg_root, 
                title=f"{base_title} - Frame {i}"
            )
    
    def _convert_nested_pages(self, 
                            svg_root: ET.Element,
                            doc: MultiSlideDocument,
                            boundaries: List[SlideBoundary],
                            options: Dict[str, Any]):
        """Convert nested SVG pages to separate slides."""
        
        nested_boundaries = [b for b in boundaries if b.boundary_type.value == 'nested_svg']
        
        # Add each nested SVG as a slide
        for boundary in nested_boundaries:
            doc.add_svg_slide(
                boundary.element,
                title=boundary.title
            )
    
    def _convert_layer_slides(self, 
                            svg_root: ET.Element,
                            doc: MultiSlideDocument,
                            boundaries: List[SlideBoundary],
                            options: Dict[str, Any]):
        """Convert layer groups to separate slides."""
        
        layer_boundaries = [b for b in boundaries if b.boundary_type.value == 'layer_group']
        
        # Create a slide for each layer group
        for boundary in layer_boundaries:
            # Create temporary SVG with just this layer
            layer_svg = self._create_layer_svg(svg_root, boundary.element)
            doc.add_svg_slide(layer_svg, title=boundary.title)
    
    def _convert_generic_boundaries(self, 
                                  svg_root: ET.Element,
                                  doc: MultiSlideDocument,
                                  boundaries: List[SlideBoundary],
                                  options: Dict[str, Any]):
        """Convert generic slide boundaries."""
        
        # Add full SVG as first slide
        doc.add_svg_slide(svg_root, title="Complete Content")
        
        # Add boundary-specific slides
        for boundary in boundaries:
            if boundary.boundary_type.value == 'section_marker':
                # Create slide with section content
                section_svg = self._create_section_svg(svg_root, boundary.element)
                doc.add_svg_slide(section_svg, title=boundary.title)
    
    def _create_layer_svg(self, svg_root: ET.Element, layer_element: ET.Element) -> ET.Element:
        """Create new SVG containing only specified layer."""
        # Create copy of root SVG
        new_svg = ET.Element(svg_root.tag, svg_root.attrib)
        
        # Copy essential children (defs, etc.)
        for child in svg_root:
            if child.tag.endswith('defs') or child.tag.endswith('style'):
                new_svg.append(child)
        
        # Add the specific layer
        new_svg.append(layer_element)
        
        return new_svg
    
    def _create_section_svg(self, svg_root: ET.Element, section_element: ET.Element) -> ET.Element:
        """Create new SVG focused on section element."""
        # Simplified - copy root structure with section element
        new_svg = ET.Element(svg_root.tag, svg_root.attrib)
        
        # Add essential elements
        for child in svg_root:
            if child.tag.endswith('defs') or child == section_element:
                new_svg.append(child)
        
        return new_svg


# Convenience functions for backward compatibility and ease of use

def convert_svg_to_multislide_pptx(svg_path: Union[str, Path], 
                                  output_path: Union[str, Path],
                                  **options) -> Dict[str, Any]:
    """
    Convert SVG file to multi-slide PPTX with automatic boundary detection.
    
    Args:
        svg_path: Path to SVG file
        output_path: Path for output PPTX file
        **options: Conversion options
        
    Returns:
        Conversion result dictionary
    """
    converter = MultiSlideConverter()
    return converter.convert_svg_to_pptx(
        svg_input=Path(svg_path),
        output_path=Path(output_path),
        options=options
    )


def convert_multiple_svgs_to_pptx(svg_paths: List[Union[str, Path]],
                                 output_path: Union[str, Path],
                                 **options) -> Dict[str, Any]:
    """
    Convert multiple SVG files to single multi-slide PPTX.
    
    Args:
        svg_paths: List of SVG file paths
        output_path: Path for output PPTX file
        **options: Conversion options
        
    Returns:
        Conversion result dictionary
    """
    converter = MultiSlideConverter()
    return converter.convert_svg_to_pptx(
        svg_input=[Path(p) for p in svg_paths],
        output_path=Path(output_path),
        options=options
    )


def detect_slide_boundaries(svg_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """
    Analyze SVG file and detect potential slide boundaries.
    
    Args:
        svg_path: Path to SVG file
        
    Returns:
        List of detected boundaries with metadata
    """
    # Parse SVG
    tree = ET.parse(svg_path)
    svg_root = tree.getroot()
    
    # Detect boundaries
    detector = SlideDetector()
    boundaries = detector.detect_boundaries(svg_root)
    
    # Convert to simple dictionaries
    return [
        {
            'type': boundary.boundary_type.value,
            'title': boundary.title,
            'confidence': boundary.confidence,
            'position': boundary.position,
            'metadata': boundary.metadata
        }
        for boundary in boundaries
    ]
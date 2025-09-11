#!/usr/bin/env python3
"""
Slide boundary detection for multi-slide PowerPoint generation.

This module analyzes SVG documents to detect where slide boundaries should
occur, supporting various scenarios like animation sequences, page breaks,
and nested SVG documents.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path

from lxml import etree as ET


class SlideType(Enum):
    """Types of slide boundaries that can be detected."""
    ANIMATION_KEYFRAME = "animation_keyframe"
    PAGE_BREAK = "page_break"
    NESTED_SVG = "nested_svg"
    LAYER_GROUP = "layer_group"
    SECTION_MARKER = "section_marker"
    TIME_BASED = "time_based"
    SIZE_BASED = "size_based"


@dataclass
class SlideBoundary:
    """Represents a detected slide boundary in an SVG document."""
    
    boundary_type: SlideType
    element: ET.Element
    position: int = 0
    title: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Extract additional information from the boundary element."""
        if self.title is None:
            self.title = self._extract_title()
        
        self.metadata.update(self._extract_metadata())
    
    def _extract_title(self) -> Optional[str]:
        """Extract title from SVG element."""
        # Check for title element
        title_elem = self.element.find('.//{http://www.w3.org/2000/svg}title')
        if title_elem is not None and title_elem.text:
            return title_elem.text.strip()
        
        # Check for common title attributes
        for attr in ['title', 'data-title', 'aria-label', 'id']:
            value = self.element.get(attr)
            if value:
                return value.strip()
        
        # Generate default title
        tag = self.element.tag.split('}')[-1] if '}' in self.element.tag else self.element.tag
        return f"{tag.title()} {self.position}"
    
    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract metadata from SVG element."""
        metadata = {}
        
        # Element information
        tag = self.element.tag.split('}')[-1] if '}' in self.element.tag else self.element.tag
        metadata['element_tag'] = tag
        
        # Dimensional information
        if tag == 'svg':
            metadata['width'] = self.element.get('width')
            metadata['height'] = self.element.get('height')
            metadata['viewBox'] = self.element.get('viewBox')
        
        # Custom attributes
        for attr, value in self.element.attrib.items():
            if attr.startswith('data-slide-') or attr.startswith('data-'):
                metadata[attr] = value
        
        return metadata


class SlideDetector:
    """
    Analyzes SVG documents to detect slide boundaries and recommend
    multi-slide conversion strategies.
    """
    
    def __init__(self, 
                 enable_animation_detection: bool = True,
                 enable_nested_svg_detection: bool = True,
                 enable_layer_detection: bool = True,
                 animation_threshold: int = 3):
        """
        Initialize slide detector.
        
        Args:
            enable_animation_detection: Detect animation keyframes
            enable_nested_svg_detection: Detect nested SVG elements
            enable_layer_detection: Detect layer groups
            animation_threshold: Minimum animations needed for slide sequence
        """
        self.enable_animation_detection = enable_animation_detection
        self.enable_nested_svg_detection = enable_nested_svg_detection
        self.enable_layer_detection = enable_layer_detection
        self.animation_threshold = animation_threshold
        
        # Detection statistics
        self.detection_stats = {}
    
    def detect_boundaries(self, svg_root: ET.Element) -> List[SlideBoundary]:
        """
        Detect all slide boundaries in an SVG document.
        
        Args:
            svg_root: Root SVG element to analyze
            
        Returns:
            List of detected slide boundaries
        """
        boundaries = []
        
        # Reset statistics
        self.detection_stats = {
            'animation_keyframes': 0,
            'nested_svgs': 0,
            'layer_groups': 0,
            'section_markers': 0,
            'explicit_boundaries': 0
        }
        
        # 1. Detect explicit slide markers
        explicit_boundaries = self._detect_explicit_markers(svg_root)
        boundaries.extend(explicit_boundaries)
        
        # 2. Detect animation keyframes
        if self.enable_animation_detection:
            animation_boundaries = self._detect_animation_keyframes(svg_root)
            boundaries.extend(animation_boundaries)
        
        # 3. Detect nested SVG documents
        if self.enable_nested_svg_detection:
            nested_boundaries = self._detect_nested_svgs(svg_root)
            boundaries.extend(nested_boundaries)
        
        # 4. Detect layer groups
        if self.enable_layer_detection:
            layer_boundaries = self._detect_layer_groups(svg_root)
            boundaries.extend(layer_boundaries)
        
        # 5. Detect section markers
        section_boundaries = self._detect_section_markers(svg_root)
        boundaries.extend(section_boundaries)
        
        # Sort boundaries by position and assign positions
        boundaries.sort(key=lambda b: (b.element.sourceline or 0, b.position))
        for i, boundary in enumerate(boundaries):
            boundary.position = i + 1
        
        return boundaries
    
    def _detect_explicit_markers(self, svg_root: ET.Element) -> List[SlideBoundary]:
        """Detect explicit slide boundary markers."""
        boundaries = []
        
        # Look for data-slide-break attributes
        elements = svg_root.xpath('//*[@data-slide-break="true" or @data-slide-break="1"]')
        
        for element in elements:
            boundary = SlideBoundary(
                boundary_type=SlideType.SECTION_MARKER,
                element=element,
                confidence=1.0
            )
            boundaries.append(boundary)
            self.detection_stats['explicit_boundaries'] += 1
        
        return boundaries
    
    def _detect_animation_keyframes(self, svg_root: ET.Element) -> List[SlideBoundary]:
        """Detect animation keyframes that should become separate slides."""
        boundaries = []
        
        # Find animation elements
        animation_elements = svg_root.xpath(
            '//animate | //animateTransform | //animateMotion | '
            '//*[@begin] | //*[@dur] | //*[@repeatCount]'
        )
        
        if len(animation_elements) < self.animation_threshold:
            return boundaries
        
        # Group animations by time
        time_groups = self._group_animations_by_time(animation_elements)
        
        for time_point, animations in time_groups.items():
            if len(animations) >= 2:  # Multiple simultaneous animations
                # Create a boundary for this animation state
                representative_elem = animations[0]
                boundary = SlideBoundary(
                    boundary_type=SlideType.ANIMATION_KEYFRAME,
                    element=representative_elem,
                    confidence=0.8,
                    metadata={'time_point': time_point, 'animation_count': len(animations)}
                )
                boundaries.append(boundary)
                self.detection_stats['animation_keyframes'] += 1
        
        return boundaries
    
    def _detect_nested_svgs(self, svg_root: ET.Element) -> List[SlideBoundary]:
        """Detect nested SVG elements that should become separate slides."""
        boundaries = []
        
        # Find nested SVG elements (not the root)
        nested_svgs = svg_root.xpath('.//svg[@width and @height]')[1:]  # Skip root SVG
        
        for svg_elem in nested_svgs:
            # Check if this looks like a page or slide
            width = svg_elem.get('width', '')
            height = svg_elem.get('height', '')
            
            # Look for page-like dimensions or explicit page indicators
            is_page_like = (
                any(dim in width.lower() for dim in ['in', 'mm', 'cm', 'pt']) or
                any(dim in height.lower() for dim in ['in', 'mm', 'cm', 'pt']) or
                'page' in (svg_elem.get('id', '') + svg_elem.get('class', '')).lower()
            )
            
            confidence = 0.9 if is_page_like else 0.6
            
            boundary = SlideBoundary(
                boundary_type=SlideType.NESTED_SVG,
                element=svg_elem,
                confidence=confidence
            )
            boundaries.append(boundary)
            self.detection_stats['nested_svgs'] += 1
        
        return boundaries
    
    def _detect_layer_groups(self, svg_root: ET.Element) -> List[SlideBoundary]:
        """Detect layer groups that could become separate slides."""
        boundaries = []
        
        # Find groups that look like layers
        groups = svg_root.xpath('//g')
        
        for group in groups:
            group_id = group.get('id', '').lower()
            group_class = group.get('class', '').lower()
            
            # Check if this looks like a layer
            is_layer = any(keyword in group_id + group_class for keyword in [
                'layer', 'slide', 'page', 'step', 'frame'
            ])
            
            # Check if group has significant content
            content_elements = group.xpath('.//rect | .//circle | .//path | .//text')
            has_significant_content = len(content_elements) >= 3
            
            if is_layer and has_significant_content:
                boundary = SlideBoundary(
                    boundary_type=SlideType.LAYER_GROUP,
                    element=group,
                    confidence=0.7,
                    metadata={'content_elements': len(content_elements)}
                )
                boundaries.append(boundary)
                self.detection_stats['layer_groups'] += 1
        
        return boundaries
    
    def _detect_section_markers(self, svg_root: ET.Element) -> List[SlideBoundary]:
        """Detect text elements that look like section markers."""
        boundaries = []
        
        # Find text elements that might be section headers
        text_elements = svg_root.xpath('//text')
        
        for text_elem in text_elements:
            text_content = (text_elem.text or '').strip()
            
            # Look for section-like text patterns
            is_section_marker = (
                len(text_content) < 50 and  # Short text
                any(keyword in text_content.lower() for keyword in [
                    'slide', 'section', 'chapter', 'part', 'step'
                ]) and
                not any(char.isdigit() for char in text_content)  # No numbers (likely not data)
            )
            
            # Check font size (larger text might be headers)
            font_size_attr = text_elem.get('font-size', '')
            is_large_text = False
            try:
                if font_size_attr:
                    font_size = float(font_size_attr.replace('px', '').replace('pt', ''))
                    is_large_text = font_size > 18
            except ValueError:
                pass
            
            if is_section_marker or is_large_text:
                confidence = 0.8 if is_section_marker else 0.5
                boundary = SlideBoundary(
                    boundary_type=SlideType.SECTION_MARKER,
                    element=text_elem,
                    confidence=confidence,
                    metadata={'text_content': text_content}
                )
                boundaries.append(boundary)
                self.detection_stats['section_markers'] += 1
        
        return boundaries
    
    def _group_animations_by_time(self, animation_elements: List[ET.Element]) -> Dict[float, List[ET.Element]]:
        """Group animation elements by their start time."""
        time_groups = {}
        
        for elem in animation_elements:
            # Extract begin time
            begin_attr = elem.get('begin', '0s')
            try:
                # Parse time (simplified - handles "0s", "1s", "2.5s" etc.)
                time_str = begin_attr.replace('s', '').replace('ms', '')
                begin_time = float(time_str)
                
                if begin_time not in time_groups:
                    time_groups[begin_time] = []
                time_groups[begin_time].append(elem)
                
            except (ValueError, TypeError):
                # Default to time 0 if parsing fails
                if 0.0 not in time_groups:
                    time_groups[0.0] = []
                time_groups[0.0].append(elem)
        
        return time_groups
    
    def recommend_conversion_strategy(self, boundaries: List[SlideBoundary]) -> Dict[str, Any]:
        """
        Analyze detected boundaries and recommend conversion strategy.
        
        Args:
            boundaries: List of detected slide boundaries
            
        Returns:
            Dictionary with conversion recommendations
        """
        if not boundaries:
            return {
                'strategy': 'single_slide',
                'reason': 'No slide boundaries detected',
                'confidence': 1.0
            }
        
        # Analyze boundary types
        type_counts = {}
        total_confidence = 0
        
        for boundary in boundaries:
            boundary_type = boundary.boundary_type.value
            type_counts[boundary_type] = type_counts.get(boundary_type, 0) + 1
            total_confidence += boundary.confidence
        
        avg_confidence = total_confidence / len(boundaries)
        
        # Determine strategy based on predominant boundary type
        if type_counts.get('animation_keyframe', 0) >= 3:
            strategy = 'animation_sequence'
            reason = f"Detected {type_counts['animation_keyframe']} animation keyframes"
        
        elif type_counts.get('nested_svg', 0) >= 2:
            strategy = 'nested_pages'
            reason = f"Detected {type_counts['nested_svg']} nested SVG pages"
        
        elif type_counts.get('layer_group', 0) >= 2:
            strategy = 'layer_slides'
            reason = f"Detected {type_counts['layer_group']} layer groups"
        
        elif type_counts.get('section_marker', 0) >= 2:
            strategy = 'section_slides'
            reason = f"Detected {type_counts['section_marker']} section markers"
        
        else:
            strategy = 'content_slides'
            reason = f"Detected {len(boundaries)} mixed slide boundaries"
        
        return {
            'strategy': strategy,
            'reason': reason,
            'confidence': avg_confidence,
            'boundary_count': len(boundaries),
            'boundary_types': type_counts,
            'recommended_slides': len(boundaries) + 1  # +1 for base content
        }
    
    def generate_slide_plan(self, 
                          svg_root: ET.Element,
                          boundaries: Optional[List[SlideBoundary]] = None) -> Dict[str, Any]:
        """
        Generate a complete plan for multi-slide conversion.
        
        Args:
            svg_root: Root SVG element
            boundaries: Pre-detected boundaries (will detect if None)
            
        Returns:
            Complete slide generation plan
        """
        if boundaries is None:
            boundaries = self.detect_boundaries(svg_root)
        
        strategy = self.recommend_conversion_strategy(boundaries)
        
        # Generate slide specifications
        slide_specs = []
        
        if not boundaries:
            # Single slide plan
            slide_specs.append({
                'slide_id': 1,
                'title': 'SVG Content',
                'content_source': 'full_svg',
                'element': svg_root
            })
        else:
            # Multi-slide plan
            for i, boundary in enumerate(boundaries):
                slide_specs.append({
                    'slide_id': i + 1,
                    'title': boundary.title,
                    'content_source': boundary.boundary_type.value,
                    'element': boundary.element,
                    'confidence': boundary.confidence,
                    'metadata': boundary.metadata
                })
        
        return {
            'strategy': strategy,
            'slide_count': len(slide_specs),
            'slides': slide_specs,
            'detection_stats': self.detection_stats,
            'svg_info': {
                'width': svg_root.get('width'),
                'height': svg_root.get('height'),
                'viewBox': svg_root.get('viewBox')
            }
        }
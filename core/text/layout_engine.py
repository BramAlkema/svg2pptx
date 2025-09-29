#!/usr/bin/env python3
"""
Text Layout Engine

Integrates with the preprocessed text metadata to provide enhanced
text layout capabilities for the conversion pipeline.

Features:
- Preprocessed text metadata integration
- Multi-run text layout (tspan processing)
- Baseline adjustment integration
- Font cascade resolution
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from lxml import etree as ET

from ..services.conversion_services import ConversionServices

logger = logging.getLogger(__name__)


class TextLayoutEngine:
    """
    Text layout engine that integrates with preprocessed text metadata.

    Works with the output from TextLayoutPrepPreprocessor to provide
    enhanced text positioning and layout capabilities.
    """

    def __init__(self, services: ConversionServices):
        """
        Initialize text layout engine.

        Args:
            services: ConversionServices container
        """
        self.services = services
        self.logger = logging.getLogger(__name__)

    def process_preprocessed_text(self, text_element: ET.Element, context: Any) -> Dict[str, Any]:
        """
        Process text element that has been prepared by TextLayoutPrepPreprocessor.

        Args:
            text_element: Preprocessed text element with metadata
            context: Conversion context

        Returns:
            Text layout information for DrawingML generation
        """
        # Check if element has preprocessing metadata
        if not self._has_preprocessing_metadata(text_element):
            self.logger.warning("Text element lacks preprocessing metadata")
            return self._create_fallback_layout(text_element, context)

        # Extract preprocessing metadata
        layout_metadata = self._extract_layout_metadata(text_element)

        # Process based on layout type
        if layout_metadata['layout_type'] == 'single-run':
            return self._process_single_run_text(text_element, layout_metadata, context)
        elif layout_metadata['layout_type'] == 'multi-run':
            return self._process_multi_run_text(text_element, layout_metadata, context)
        else:
            self.logger.warning(f"Unknown layout type: {layout_metadata['layout_type']}")
            return self._create_fallback_layout(text_element, context)

    def _has_preprocessing_metadata(self, element: ET.Element) -> bool:
        """Check if element has preprocessing metadata."""
        return element.get('data-text-layout') is not None

    def _extract_layout_metadata(self, element: ET.Element) -> Dict[str, Any]:
        """Extract preprocessing metadata from text element."""
        metadata = {
            'layout_type': element.get('data-text-layout', 'single-run'),
            'original_anchor': element.get('data-original-anchor', 'start'),
            'font_family': element.get('data-font-family', 'Arial'),
            'font_size': float(element.get('data-font-size', '12')),
            'baseline_shift': float(element.get('data-baseline-shift', '0')),
            'complex_positioning': element.get('data-complex-positioning', 'false').lower() == 'true',
            'coord_system': element.get('data-coord-system', 'svg-user'),
            'needs_coord_transform': element.get('data-needs-coord-transform', 'false').lower() == 'true',
            'primary_font': element.get('data-primary-font'),
            'fallback_fonts': element.get('data-fallback-fonts'),
            'font_cascade': element.get('data-font-cascade', 'Arial')
        }

        # Extract line break information for multi-run
        if metadata['layout_type'] == 'multi-run':
            metadata['line_breaks'] = int(element.get('data-line-breaks', '0'))

        return metadata

    def _process_single_run_text(self, element: ET.Element, metadata: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Process single-run text with preprocessing integration."""
        # Get text content
        text_content = self._extract_text_content(element)

        # Get position with coordinate system awareness
        x, y = self._get_text_position(element, metadata, context)

        # Apply baseline adjustment from preprocessing
        y += metadata['baseline_shift']

        # Create layout information
        layout = {
            'type': 'single-run',
            'content': text_content,
            'position': {'x': x, 'y': y},
            'font': {
                'family': metadata['font_family'],
                'size': metadata['font_size'],
                'cascade': metadata['font_cascade'].split(',') if metadata['font_cascade'] else ['Arial']
            },
            'anchor': metadata['original_anchor'],
            'baseline_adjusted': True,
            'runs': [
                {
                    'text': text_content,
                    'font_family': metadata['font_family'],
                    'font_size': metadata['font_size'],
                    'position': {'x': x, 'y': y},
                    'inherited_styles': self._extract_inherited_styles(element)
                }
            ]
        }

        self.logger.debug(f"Single-run text layout: '{text_content[:20]}...' at ({x:.1f}, {y:.1f})")
        return layout

    def _process_multi_run_text(self, element: ET.Element, metadata: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Process multi-run text with tspan elements."""
        # Get base position
        base_x, base_y = self._get_text_position(element, metadata, context)

        # Apply baseline adjustment from preprocessing
        base_y += metadata['baseline_shift']

        # Process tspan elements
        runs = []
        tspan_elements = element.xpath("./svg:tspan", namespaces={'svg': 'http://www.w3.org/2000/svg'})

        current_y = base_y
        line_height = metadata['font_size'] * 1.2  # Default line height

        for tspan in tspan_elements:
            run_info = self._process_tspan_run(tspan, base_x, current_y, metadata, context)
            runs.append(run_info)

            # Check if this tspan creates a line break
            if tspan.get('data-line-break') == 'true':
                current_y += line_height

        # Create complete text content
        full_text = ' '.join(run['text'] for run in runs if run['text'])

        layout = {
            'type': 'multi-run',
            'content': full_text,
            'position': {'x': base_x, 'y': base_y},
            'font': {
                'family': metadata['font_family'],
                'size': metadata['font_size'],
                'cascade': metadata['font_cascade'].split(',') if metadata['font_cascade'] else ['Arial']
            },
            'anchor': metadata['original_anchor'],
            'baseline_adjusted': True,
            'line_breaks': metadata.get('line_breaks', 0),
            'runs': runs
        }

        self.logger.debug(f"Multi-run text layout: {len(runs)} runs, {metadata.get('line_breaks', 0)} line breaks")
        return layout

    def _process_tspan_run(self, tspan: ET.Element, base_x: float, base_y: float,
                          metadata: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Process a single tspan run."""
        # Get tspan content
        text_content = tspan.text or ''
        run_index = int(tspan.get('data-run-index', '0'))

        # Check for explicit positioning
        tspan_x = tspan.get('x')
        tspan_y = tspan.get('y')

        if tspan_x is not None and tspan_y is not None:
            # Use explicit positioning
            x = float(tspan_x)
            y = float(tspan_y) + metadata['baseline_shift']
        else:
            # Use base positioning
            x = base_x
            y = base_y

        # Extract inherited styles
        inherited_styles = self._extract_tspan_styles(tspan)

        # Get font properties for this run
        run_font_family = inherited_styles.get('font-family', metadata['font_family'])
        run_font_size = inherited_styles.get('font-size', metadata['font_size'])

        run_info = {
            'text': text_content,
            'font_family': run_font_family,
            'font_size': run_font_size,
            'position': {'x': x, 'y': y},
            'run_index': run_index,
            'line_break': tspan.get('data-line-break') == 'true',
            'inherited_styles': inherited_styles,
            'explicit_positioning': tspan_x is not None or tspan_y is not None
        }

        return run_info

    def _get_text_position(self, element: ET.Element, metadata: Dict[str, Any], context: Any) -> Tuple[float, float]:
        """Get text position with coordinate system awareness."""
        # Get raw coordinates
        x = float(element.get('x', '0'))
        y = float(element.get('y', '0'))

        # Apply coordinate transformation if needed
        if metadata['needs_coord_transform']:
            # Use coordinate transformer from services
            try:
                transformed = self.services.coordinate_transformer.transform_point(x, y, metadata['coord_system'])
                x, y = transformed['x'], transformed['y']
                self.logger.debug(f"Coordinate transform: ({x:.1f}, {y:.1f})")
            except Exception as e:
                self.logger.debug(f"Coordinate transformation failed: {e}")

        return x, y

    def _extract_text_content(self, element: ET.Element) -> str:
        """Extract complete text content from element."""
        text_parts = []

        # Add direct text content
        if element.text:
            text_parts.append(element.text.strip())

        # Process child elements
        for child in element:
            if child.tag.endswith('tspan'):
                if child.text:
                    text_parts.append(child.text.strip())
            if child.tail:
                text_parts.append(child.tail.strip())

        return ' '.join(text_parts)

    def _extract_inherited_styles(self, element: ET.Element) -> Dict[str, Any]:
        """Extract style properties from element."""
        styles = {}

        # Direct attributes
        style_attrs = ['font-family', 'font-size', 'font-weight', 'font-style', 'fill', 'stroke']
        for attr in style_attrs:
            value = element.get(attr)
            if value:
                styles[attr] = value

        # CSS style attribute
        style_attr = element.get('style', '')
        if style_attr:
            styles.update(self._parse_css_style(style_attr))

        return styles

    def _extract_tspan_styles(self, tspan: ET.Element) -> Dict[str, Any]:
        """Extract styles from tspan element including inherited data."""
        styles = self._extract_inherited_styles(tspan)

        # Check for inherited style data from preprocessing
        inherited_attrs = ['font-family', 'font-size', 'font-weight', 'font-style', 'fill', 'stroke']
        for attr in inherited_attrs:
            inherited_key = f'data-inherited-{attr}'
            inherited_value = tspan.get(inherited_key)
            if inherited_value and attr not in styles:
                styles[attr] = inherited_value

        # Check for inherited CSS style
        inherited_style = tspan.get('data-inherited-style')
        if inherited_style:
            inherited_styles = self._parse_css_style(inherited_style)
            # Only use inherited styles that aren't explicitly set
            for key, value in inherited_styles.items():
                if key not in styles:
                    styles[key] = value

        return styles

    def _parse_css_style(self, style_str: str) -> Dict[str, str]:
        """Parse CSS style string into dictionary."""
        styles = {}
        if not style_str:
            return styles

        for rule in style_str.split(';'):
            if ':' in rule:
                key, value = rule.split(':', 1)
                styles[key.strip()] = value.strip()

        return styles

    def _create_fallback_layout(self, element: ET.Element, context: Any) -> Dict[str, Any]:
        """Create fallback layout for non-preprocessed text."""
        text_content = self._extract_text_content(element)
        x = float(element.get('x', '0'))
        y = float(element.get('y', '0'))

        layout = {
            'type': 'fallback',
            'content': text_content,
            'position': {'x': x, 'y': y},
            'font': {
                'family': 'Arial',
                'size': 12.0,
                'cascade': ['Arial']
            },
            'anchor': 'start',
            'baseline_adjusted': False,
            'runs': [
                {
                    'text': text_content,
                    'font_family': 'Arial',
                    'font_size': 12.0,
                    'position': {'x': x, 'y': y},
                    'inherited_styles': {}
                }
            ]
        }

        self.logger.debug(f"Fallback text layout for non-preprocessed element")
        return layout


def create_text_layout_engine(services: ConversionServices) -> TextLayoutEngine:
    """
    Create a text layout engine with services.

    Args:
        services: ConversionServices container

    Returns:
        Configured TextLayoutEngine
    """
    return TextLayoutEngine(services)
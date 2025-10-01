"""
SVG Font Analyzer

Analyzes SVG content to determine font requirements and whether
font embedding is necessary for accurate text rendering.
"""

import re
from typing import Set, List, Dict, Optional, Tuple
from lxml import etree as ET

from ..data.embedded_font import FontSubsetRequest


class SVGFontAnalyzer:
    """
    Analyzes SVG content to determine font requirements.

    Extracts text elements, font families, and character usage
    to determine optimal font embedding strategy.
    """

    def __init__(self):
        """Initialize SVG font analyzer."""
        self.text_elements_found = []
        self.font_requirements = {}
        self.total_character_count = 0

    def analyze_svg_fonts(self, svg_content: str) -> Dict[str, any]:
        """
        Analyze SVG content for embedded fonts.

        Args:
            svg_content: SVG content as string

        Returns:
            Dictionary with font analysis results
        """
        try:
            # Parse SVG content
            if isinstance(svg_content, str) and svg_content.strip().startswith('<?xml'):
                svg_bytes = svg_content.encode('utf-8')
                svg_root = ET.fromstring(svg_bytes)
            else:
                svg_root = ET.fromstring(svg_content)

            # Look for embedded fonts in SVG
            embedded_fonts = self._extract_embedded_fonts(svg_root)

            # Extract text elements for context
            text_elements = self._extract_text_elements(svg_root)

            # Only recommend embedding if SVG actually contains embedded fonts
            should_embed = len(embedded_fonts) > 0

            # Analyze font requirements only if we have embedded fonts
            font_requirements = {}
            if should_embed:
                font_requirements = self._analyze_embedded_font_requirements(embedded_fonts, text_elements)

            return {
                'has_embedded_fonts': len(embedded_fonts) > 0,
                'embedded_fonts_count': len(embedded_fonts),
                'embedded_fonts': embedded_fonts,
                'has_text_elements': len(text_elements) > 0,
                'text_elements_count': len(text_elements),
                'should_embed_fonts': should_embed,
                'total_characters': sum(len(elem['text']) for elem in text_elements),
                'unique_characters': len(self._get_unique_characters(text_elements)),
                'embedding_recommendation': 'svg_has_embedded_fonts' if should_embed else 'no_embedded_fonts',
                'text_elements': text_elements,
                'font_requirements': font_requirements
            }

        except ET.XMLSyntaxError as e:
            return {
                'has_embedded_fonts': False,
                'has_text_elements': False,
                'error': f'Invalid SVG content: {str(e)}',
                'should_embed_fonts': False,
                'embedded_fonts': [],
                'embedding_recommendation': 'invalid_svg'
            }

    def _extract_text_elements(self, svg_root: ET.Element) -> List[Dict[str, any]]:
        """
        Extract all text elements from SVG.

        Args:
            svg_root: Parsed SVG root element

        Returns:
            List of text element information dictionaries
        """
        text_elements = []

        # Find all text elements (including nested ones)
        # Use both xpath and findall to handle different namespace scenarios
        text_elements_xpath = svg_root.xpath('.//text | .//tspan')
        text_elements_findall = svg_root.findall('.//text') + svg_root.findall('.//{http://www.w3.org/2000/svg}text')

        # Combine and deduplicate
        all_text_elements = list(set(text_elements_xpath + text_elements_findall))

        for text_elem in all_text_elements:
            text_content = self._get_element_text_content(text_elem)

            if text_content.strip():  # Only include non-empty text
                element_info = {
                    'text': text_content,
                    'font_family': self._get_font_family(text_elem),
                    'font_size': self._get_font_size(text_elem),
                    'font_weight': self._get_font_weight(text_elem),
                    'font_style': self._get_font_style(text_elem),
                    'character_count': len(text_content),
                    'unique_characters': set(text_content)
                }
                text_elements.append(element_info)

        return text_elements

    def _get_element_text_content(self, element: ET.Element) -> str:
        """
        Get all text content from element including nested elements.

        Args:
            element: Text element

        Returns:
            Combined text content
        """
        # Get direct text content
        text_parts = []

        if element.text:
            text_parts.append(element.text)

        # Get text from child elements (like tspan)
        for child in element:
            if child.text:
                text_parts.append(child.text)
            if child.tail:
                text_parts.append(child.tail)

        if element.tail:
            text_parts.append(element.tail)

        return ''.join(text_parts)

    def _get_font_family(self, element: ET.Element) -> str:
        """Extract font-family from element or its parents."""
        # Check element's style attribute first
        style = element.get('style', '')
        if 'font-family:' in style:
            match = re.search(r'font-family:\s*([^;]+)', style)
            if match:
                return match.group(1).strip().strip('\'"')

        # Check direct font-family attribute
        font_family = element.get('font-family')
        if font_family:
            return font_family.strip().strip('\'"')

        # Check parent elements
        parent = element.getparent()
        while parent is not None:
            parent_style = parent.get('style', '')
            if 'font-family:' in parent_style:
                match = re.search(r'font-family:\s*([^;]+)', parent_style)
                if match:
                    return match.group(1).strip().strip('\'"')

            parent_font_family = parent.get('font-family')
            if parent_font_family:
                return parent_font_family.strip().strip('\'"')

            parent = parent.getparent()

        return 'sans-serif'  # Default fallback

    def _get_font_size(self, element: ET.Element) -> str:
        """Extract font-size from element or its parents."""
        # Check element's style attribute
        style = element.get('style', '')
        if 'font-size:' in style:
            match = re.search(r'font-size:\s*([^;]+)', style)
            if match:
                return match.group(1).strip()

        # Check direct font-size attribute
        font_size = element.get('font-size')
        if font_size:
            return font_size.strip()

        # Check parent elements
        parent = element.getparent()
        while parent is not None:
            parent_style = parent.get('style', '')
            if 'font-size:' in parent_style:
                match = re.search(r'font-size:\s*([^;]+)', parent_style)
                if match:
                    return match.group(1).strip()

            parent_font_size = parent.get('font-size')
            if parent_font_size:
                return parent_font_size.strip()

            parent = parent.getparent()

        return '12px'  # Default fallback

    def _get_font_weight(self, element: ET.Element) -> str:
        """Extract font-weight from element or its parents."""
        # Check style attribute
        style = element.get('style', '')
        if 'font-weight:' in style:
            match = re.search(r'font-weight:\s*([^;]+)', style)
            if match:
                return match.group(1).strip()

        # Check direct attribute
        font_weight = element.get('font-weight')
        if font_weight:
            return font_weight.strip()

        return 'normal'

    def _get_font_style(self, element: ET.Element) -> str:
        """Extract font-style from element or its parents."""
        # Check style attribute
        style = element.get('style', '')
        if 'font-style:' in style:
            match = re.search(r'font-style:\s*([^;]+)', style)
            if match:
                return match.group(1).strip()

        # Check direct attribute
        font_style = element.get('font-style')
        if font_style:
            return font_style.strip()

        return 'normal'

    def _extract_embedded_fonts(self, svg_root: ET.Element) -> List[Dict[str, any]]:
        """
        Extract embedded fonts from SVG content.

        Looks for actual embedded font data in SVG including:
        - <font> elements (SVG fonts)
        - <font-face> elements
        - CSS @font-face rules in <style> elements
        - Base64 encoded font data in style attributes

        Args:
            svg_root: Parsed SVG root element

        Returns:
            List of embedded font information dictionaries
        """
        embedded_fonts = []

        # Look for SVG font elements
        svg_fonts = self._find_svg_font_elements(svg_root)
        embedded_fonts.extend(svg_fonts)

        # Look for CSS @font-face rules in style elements
        css_fonts = self._find_css_font_face_rules(svg_root)
        embedded_fonts.extend(css_fonts)

        # Look for inline style font-face rules
        inline_fonts = self._find_inline_font_face_rules(svg_root)
        embedded_fonts.extend(inline_fonts)

        return embedded_fonts

    def _find_svg_font_elements(self, svg_root: ET.Element) -> List[Dict[str, any]]:
        """Find SVG font elements (<font>, <font-face>)."""
        fonts = []

        # Find <font> elements
        try:
            font_elements = svg_root.xpath('.//font | .//{http://www.w3.org/2000/svg}font')
        except:
            # Fallback to findall if XPath fails
            font_elements = svg_root.findall('.//font') + svg_root.findall('.//{http://www.w3.org/2000/svg}font')
        for font_elem in font_elements:
            font_info = {
                'type': 'svg_font',
                'font_family': font_elem.get('font-family', 'unknown'),
                'font_face': None,
                'element': font_elem
            }

            # Look for associated font-face
            font_face = font_elem.find('.//{http://www.w3.org/2000/svg}font-face')
            if font_face is None:
                font_face = font_elem.find('.//font-face')
            if font_face is not None:
                font_info['font_face'] = {
                    'font_family': font_face.get('font-family'),
                    'font_style': font_face.get('font-style', 'normal'),
                    'font_weight': font_face.get('font-weight', 'normal'),
                    'unicode_range': font_face.get('unicode-range')
                }

            fonts.append(font_info)

        # Find standalone <font-face> elements
        try:
            font_face_elements = svg_root.xpath('.//font-face | .//{http://www.w3.org/2000/svg}font-face')
        except:
            # Fallback to findall if XPath fails
            font_face_elements = svg_root.findall('.//font-face') + svg_root.findall('.//{http://www.w3.org/2000/svg}font-face')
        for font_face in font_face_elements:
            # Skip if already processed as part of <font> element
            if font_face.getparent() is not None and font_face.getparent().tag.endswith('font'):
                continue

            font_info = {
                'type': 'font_face',
                'font_family': font_face.get('font-family', 'unknown'),
                'font_style': font_face.get('font-style', 'normal'),
                'font_weight': font_face.get('font-weight', 'normal'),
                'unicode_range': font_face.get('unicode-range'),
                'element': font_face
            }
            fonts.append(font_info)

        return fonts

    def _find_css_font_face_rules(self, svg_root: ET.Element) -> List[Dict[str, any]]:
        """Find CSS @font-face rules in <style> elements."""
        fonts = []

        # Find all style elements
        try:
            style_elements = svg_root.xpath('.//style | .//{http://www.w3.org/2000/svg}style')
        except:
            # Fallback to findall if XPath fails
            style_elements = svg_root.findall('.//style') + svg_root.findall('.//{http://www.w3.org/2000/svg}style')

        for style_elem in style_elements:
            if style_elem.text:
                css_fonts = self._parse_css_font_face(style_elem.text)
                fonts.extend(css_fonts)

        return fonts

    def _find_inline_font_face_rules(self, svg_root: ET.Element) -> List[Dict[str, any]]:
        """Find @font-face rules in style attributes."""
        fonts = []

        # Look through all elements for style attributes containing @font-face
        for elem in svg_root.iter():
            style_attr = elem.get('style', '')
            if '@font-face' in style_attr:
                css_fonts = self._parse_css_font_face(style_attr)
                fonts.extend(css_fonts)

        return fonts

    def _parse_css_font_face(self, css_content: str) -> List[Dict[str, any]]:
        """Parse CSS content for @font-face rules."""
        fonts = []

        # Find all @font-face rules
        font_face_pattern = r'@font-face\s*\{([^}]+)\}'
        matches = re.findall(font_face_pattern, css_content, re.DOTALL | re.IGNORECASE)

        for match in matches:
            font_info = {
                'type': 'css_font_face',
                'font_family': None,
                'font_style': 'normal',
                'font_weight': 'normal',
                'src': None,
                'has_embedded_data': False
            }

            # Parse font-family
            family_match = re.search(r'font-family\s*:\s*([^;]+)', match, re.IGNORECASE)
            if family_match:
                font_info['font_family'] = family_match.group(1).strip().strip('\'"')

            # Parse font-style
            style_match = re.search(r'font-style\s*:\s*([^;]+)', match, re.IGNORECASE)
            if style_match:
                font_info['font_style'] = style_match.group(1).strip()

            # Parse font-weight
            weight_match = re.search(r'font-weight\s*:\s*([^;]+)', match, re.IGNORECASE)
            if weight_match:
                font_info['font_weight'] = weight_match.group(1).strip()

            # Parse src and check for embedded data
            src_match = re.search(r'src\s*:\s*([^;]+)', match, re.IGNORECASE)
            if src_match:
                src_value = src_match.group(1).strip()
                font_info['src'] = src_value

                # Check if src contains embedded data (data: URI or base64)
                if 'data:' in src_value or 'base64,' in src_value:
                    font_info['has_embedded_data'] = True

            # Only include fonts that have embedded data or are SVG fonts
            if font_info['has_embedded_data'] or font_info['font_family']:
                fonts.append(font_info)

        return fonts

    def _analyze_embedded_font_requirements(self, embedded_fonts: List[Dict[str, any]],
                                          text_elements: List[Dict[str, any]]) -> Dict[str, Dict[str, any]]:
        """
        Analyze font requirements based on embedded fonts and text usage.

        Args:
            embedded_fonts: List of embedded font information
            text_elements: List of text element information

        Returns:
            Dictionary mapping font identifiers to requirements
        """
        font_requirements = {}

        for embedded_font in embedded_fonts:
            # Create font identifier based on embedded font
            font_family = embedded_font.get('font_family', 'unknown')
            font_style = embedded_font.get('font_style', 'normal')
            font_weight = embedded_font.get('font_weight', 'normal')

            font_id = f"{font_family}:{font_weight}:{font_style}"

            if font_id not in font_requirements:
                font_requirements[font_id] = {
                    'font_family': font_family,
                    'font_weight': font_weight,
                    'font_style': font_style,
                    'embedded_font_type': embedded_font.get('type'),
                    'has_embedded_data': embedded_font.get('has_embedded_data', True),
                    'src': embedded_font.get('src'),
                    'total_character_count': 0,
                    'unique_characters': set(),
                    'usage_count': 0,
                    'text_samples': []
                }

            # Find matching text elements that use this font
            matching_text_elements = [
                elem for elem in text_elements
                if elem['font_family'].lower() == font_family.lower()
            ]

            # Accumulate usage from matching text elements
            req = font_requirements[font_id]
            for text_elem in matching_text_elements:
                req['total_character_count'] += text_elem['character_count']
                req['unique_characters'].update(text_elem['unique_characters'])
                req['usage_count'] += 1
                req['text_samples'].append(text_elem['text'][:50])

        # Convert sets to lists for serialization
        for font_id in font_requirements:
            req = font_requirements[font_id]
            req['unique_characters'] = sorted(list(req['unique_characters']))
            req['unique_character_count'] = len(req['unique_characters'])

        return font_requirements

    def _analyze_font_requirements(self, text_elements: List[Dict[str, any]]) -> Dict[str, Dict[str, any]]:
        """
        Analyze font requirements from text elements.

        Args:
            text_elements: List of text element information

        Returns:
            Dictionary mapping font identifiers to requirements
        """
        font_requirements = {}

        for element in text_elements:
            # Create font identifier
            font_id = f"{element['font_family']}:{element['font_weight']}:{element['font_style']}"

            if font_id not in font_requirements:
                font_requirements[font_id] = {
                    'font_family': element['font_family'],
                    'font_weight': element['font_weight'],
                    'font_style': element['font_style'],
                    'total_character_count': 0,
                    'unique_characters': set(),
                    'usage_count': 0,
                    'text_samples': []
                }

            # Accumulate requirements
            req = font_requirements[font_id]
            req['total_character_count'] += element['character_count']
            req['unique_characters'].update(element['unique_characters'])
            req['usage_count'] += 1
            req['text_samples'].append(element['text'][:50])  # Store sample for debugging

        # Convert sets to lists for serialization
        for font_id in font_requirements:
            req = font_requirements[font_id]
            req['unique_characters'] = sorted(list(req['unique_characters']))
            req['unique_character_count'] = len(req['unique_characters'])

        return font_requirements

    def _get_unique_characters(self, text_elements: List[Dict[str, any]]) -> Set[str]:
        """Get all unique characters across all text elements."""
        all_characters = set()
        for element in text_elements:
            all_characters.update(element['unique_characters'])
        return all_characters

    def _should_embed_fonts(self, font_requirements: Dict[str, Dict[str, any]]) -> bool:
        """
        Determine if fonts should be embedded based on analysis.

        Args:
            font_requirements: Font requirements analysis

        Returns:
            True if font embedding is recommended
        """
        # No fonts needed if no text
        if not font_requirements:
            return False

        # Check for non-standard fonts (not common system fonts)
        common_fonts = {
            'arial', 'helvetica', 'times', 'times new roman', 'courier',
            'courier new', 'verdana', 'georgia', 'tahoma', 'calibri',
            'sans-serif', 'serif', 'monospace'
        }

        for font_id, req in font_requirements.items():
            font_family = req['font_family'].lower()

            # If font is not a common system font, recommend embedding
            if font_family not in common_fonts:
                return True

            # If using special weights/styles, consider embedding
            if req['font_weight'] not in ['normal', '400'] or req['font_style'] != 'normal':
                return True

            # If significant character usage, consider embedding for consistency
            if req['unique_character_count'] > 100:
                return True

        return False

    def _get_embedding_recommendation(self, font_requirements: Dict[str, Dict[str, any]]) -> str:
        """
        Get specific embedding recommendation.

        Args:
            font_requirements: Font requirements analysis

        Returns:
            Recommendation string
        """
        if not font_requirements:
            return 'no_text_content'

        total_fonts = len(font_requirements)
        total_characters = sum(req['unique_character_count'] for req in font_requirements.values())

        if total_characters > 500:
            return 'high_character_usage'
        elif total_fonts > 3:
            return 'multiple_fonts'
        elif any(req['font_family'].lower() not in ['arial', 'helvetica', 'times', 'sans-serif', 'serif']
                 for req in font_requirements.values()):
            return 'custom_fonts_detected'
        elif total_characters > 50:
            return 'moderate_usage'
        else:
            return 'minimal_usage'

    def create_font_subset_requests(self, svg_content: str,
                                   font_service: Optional[object] = None) -> List[FontSubsetRequest]:
        """
        Create font subset requests based on SVG analysis.

        Args:
            svg_content: SVG content to analyze
            font_service: Optional FontService to find font paths

        Returns:
            List of FontSubsetRequest objects for identified fonts
        """
        analysis = self.analyze_svg_fonts(svg_content)

        if not analysis['should_embed_fonts']:
            return []

        subset_requests = []

        # Only process if we have embedded fonts
        if not analysis['has_embedded_fonts']:
            return []

        for font_id, req in analysis['font_requirements'].items():
            # Try to find font file if font_service is provided
            font_path = None
            if font_service:
                font_path = font_service.find_font_file(
                    req['font_family'],
                    req['font_weight'],
                    req['font_style']
                )

            if font_path:  # Only create request if font file is found
                subset_request = FontSubsetRequest(
                    font_path=font_path,
                    characters=set(req['unique_characters']),
                    font_name=req['font_family'],
                    target_format='ttf',
                    optimization_level='basic'
                )
                subset_requests.append(subset_request)

        return subset_requests

    def get_text_content_summary(self, svg_content: str) -> Dict[str, any]:
        """
        Get a summary of text content in SVG.

        Args:
            svg_content: SVG content to analyze

        Returns:
            Summary dictionary
        """
        analysis = self.analyze_svg_fonts(svg_content)

        return {
            'has_text': analysis['has_text_elements'],
            'text_elements_count': analysis.get('text_elements_count', 0),
            'total_characters': analysis.get('total_characters', 0),
            'unique_characters': analysis.get('unique_characters', 0),
            'font_families_used': list(set(
                req['font_family'] for req in analysis.get('font_requirements', {}).values()
            )),
            'embedding_recommended': analysis.get('should_embed_fonts', False),
            'recommendation_reason': analysis.get('embedding_recommendation', 'unknown')
        }


def analyze_svg_for_fonts(svg_content: str) -> Dict[str, any]:
    """
    Convenience function to analyze SVG content for font requirements.

    Args:
        svg_content: SVG content as string

    Returns:
        Font analysis results
    """
    analyzer = SVGFontAnalyzer()
    return analyzer.analyze_svg_fonts(svg_content)
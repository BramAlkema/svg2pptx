"""
SVG helper utilities for multislide testing.

Provides utilities for creating, manipulating, and validating SVG content
in multislide test scenarios.
"""

from typing import Dict, List, Optional, Any, Tuple
from lxml import etree
import re
from pathlib import Path


class SVGTestBuilder:
    """Builder class for creating test SVG documents."""

    NAMESPACES = {
        'svg': 'http://www.w3.org/2000/svg',
        'xlink': 'http://www.w3.org/1999/xlink'
    }

    def __init__(self, width: int = 800, height: int = 600):
        """Initialize SVG builder with dimensions."""
        self.width = width
        self.height = height
        self.root = self._create_root()
        self.current_slide = 0

    def _create_root(self) -> etree.Element:
        """Create SVG root element with proper namespaces."""
        root = etree.Element(
            '{http://www.w3.org/2000/svg}svg',
            nsmap=self.NAMESPACES
        )
        root.set('width', str(self.width))
        root.set('height', str(self.height))
        root.set('viewBox', f'0 0 {self.width} {self.height}')
        return root

    def add_slide_group(
        self,
        slide_id: str,
        content: Optional[List[etree.Element]] = None,
        transform: Optional[str] = None,
        css_class: Optional[str] = None
    ) -> etree.Element:
        """Add a slide group to the SVG."""
        group = etree.SubElement(self.root, '{http://www.w3.org/2000/svg}g')
        group.set('id', slide_id)

        if css_class:
            group.set('class', css_class)

        if transform:
            group.set('transform', transform)

        if content:
            for element in content:
                group.append(element)

        self.current_slide += 1
        return group

    def add_animation(
        self,
        element: etree.Element,
        attribute: str,
        values: str,
        dur: str,
        keyTimes: Optional[str] = None
    ) -> etree.Element:
        """Add animation to an element."""
        anim = etree.SubElement(element, 'animate')
        anim.set('attributeName', attribute)
        anim.set('values', values)
        anim.set('dur', dur)

        if keyTimes:
            anim.set('keyTimes', keyTimes)

        return anim

    def add_nested_svg(
        self,
        parent: etree.Element,
        x: int,
        y: int,
        width: int,
        height: int,
        viewBox: Optional[str] = None
    ) -> etree.Element:
        """Add nested SVG element."""
        nested = etree.SubElement(parent, '{http://www.w3.org/2000/svg}svg')
        nested.set('x', str(x))
        nested.set('y', str(y))
        nested.set('width', str(width))
        nested.set('height', str(height))

        if viewBox:
            nested.set('viewBox', viewBox)
        else:
            nested.set('viewBox', f'0 0 {width} {height}')

        return nested

    def add_rect(
        self,
        parent: etree.Element,
        x: int,
        y: int,
        width: int,
        height: int,
        fill: str = '#000000',
        **kwargs
    ) -> etree.Element:
        """Add rectangle element."""
        rect = etree.SubElement(parent, '{http://www.w3.org/2000/svg}rect')
        rect.set('x', str(x))
        rect.set('y', str(y))
        rect.set('width', str(width))
        rect.set('height', str(height))
        rect.set('fill', fill)

        for key, value in kwargs.items():
            rect.set(key.replace('_', '-'), str(value))

        return rect

    def add_text(
        self,
        parent: etree.Element,
        x: int,
        y: int,
        text: str,
        font_size: int = 16,
        fill: str = '#000000',
        text_anchor: str = 'start',
        **kwargs
    ) -> etree.Element:
        """Add text element."""
        text_elem = etree.SubElement(parent, 'text')
        text_elem.set('x', str(x))
        text_elem.set('y', str(y))
        text_elem.set('font-size', str(font_size))
        text_elem.set('fill', fill)
        text_elem.set('text-anchor', text_anchor)
        text_elem.text = text

        for key, value in kwargs.items():
            text_elem.set(key.replace('_', '-'), str(value))

        return text_elem

    def to_string(self) -> str:
        """Convert SVG to string."""
        return etree.tostring(
            self.root,
            encoding='unicode',
            pretty_print=True
        )

    def to_bytes(self) -> bytes:
        """Convert SVG to bytes."""
        return etree.tostring(
            self.root,
            encoding='utf-8',
            pretty_print=True
        )


class SVGValidator:
    """Validator for SVG multislide structures."""

    @staticmethod
    def validate_slide_count(svg_element: etree.Element, expected: int) -> bool:
        """Validate the number of detected slides."""
        slide_groups = svg_element.xpath(
            "//svg:g[@class='slide-boundary']",
            namespaces={'svg': 'http://www.w3.org/2000/svg'}
        )
        return len(slide_groups) == expected

    @staticmethod
    def validate_animation_timeline(
        svg_element: etree.Element
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Validate animation timeline structure."""
        animations = svg_element.xpath(
            "//svg:animate | //svg:animateTransform",
            namespaces={'svg': 'http://www.w3.org/2000/svg'}
        )

        timeline = []
        for anim in animations:
            dur = anim.get('dur', '0s')
            keyTimes = anim.get('keyTimes', '')
            values = anim.get('values', '')

            # Parse duration
            duration = float(dur.rstrip('s')) if dur.endswith('s') else 0

            # Parse key times
            key_times = [float(kt) for kt in keyTimes.split(';')] if keyTimes else []

            timeline.append({
                'element': anim.getparent().get('id', 'unknown'),
                'attribute': anim.get('attributeName', ''),
                'duration': duration,
                'key_times': key_times,
                'values': values.split(';')
            })

        # Validate timeline consistency
        is_valid = len(timeline) > 0 and all(t['duration'] > 0 for t in timeline)

        return is_valid, timeline

    @staticmethod
    def validate_nested_structure(
        svg_element: etree.Element,
        max_depth: int = 10
    ) -> Tuple[bool, int]:
        """Validate nested SVG structure depth."""
        def get_depth(element, current_depth=0):
            if current_depth > max_depth:
                return current_depth

            nested_svgs = element.xpath(
                "./svg:svg",
                namespaces={'svg': 'http://www.w3.org/2000/svg'}
            )

            if not nested_svgs:
                return current_depth

            max_nested = max(
                get_depth(svg, current_depth + 1)
                for svg in nested_svgs
            )

            return max_nested

        depth = get_depth(svg_element)
        is_valid = depth <= max_depth

        return is_valid, depth

    @staticmethod
    def validate_layer_groups(
        svg_element: etree.Element,
        expected_layers: List[str]
    ) -> Tuple[bool, List[str]]:
        """Validate layer group organization."""
        layer_groups = svg_element.xpath(
            "//svg:g[starts-with(@id, 'layer_') or contains(@class, 'layer')]",
            namespaces={'svg': 'http://www.w3.org/2000/svg'}
        )

        found_layers = []
        for group in layer_groups:
            layer_id = group.get('id', '')
            if layer_id:
                found_layers.append(layer_id)

        is_valid = all(layer in found_layers for layer in expected_layers)

        return is_valid, found_layers

    @staticmethod
    def validate_section_markers(
        svg_element: etree.Element
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Validate section marker structure."""
        sections = []

        # Check for explicit markers
        markers = svg_element.xpath(
            "//svg:g[@data-slide-number or @data-section]",
            namespaces={'svg': 'http://www.w3.org/2000/svg'}
        )

        for marker in markers:
            section_info = {
                'id': marker.get('id', ''),
                'slide_number': marker.get('data-slide-number'),
                'section': marker.get('data-section'),
                'class': marker.get('class', '')
            }
            sections.append(section_info)

        # Check for title-based sections
        titles = svg_element.xpath(
            "//svg:text[@class='section-title']",
            namespaces={'svg': 'http://www.w3.org/2000/svg'}
        )

        for title in titles:
            parent_group = title.getparent()
            sections.append({
                'id': parent_group.get('id', '') if parent_group is not None else '',
                'title': title.text or '',
                'type': 'title-based'
            })

        is_valid = len(sections) > 0

        return is_valid, sections


class SVGTestLoader:
    """Loader for SVG test files."""

    def __init__(self, test_data_dir: Path):
        """Initialize loader with test data directory."""
        self.test_data_dir = Path(test_data_dir)

    def load_sample(self, category: str, filename: str) -> etree.Element:
        """Load SVG sample from category directory."""
        file_path = self.test_data_dir / 'svg_samples' / category / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Test sample not found: {file_path}")

        with open(file_path, 'rb') as f:
            return etree.parse(f).getroot()

    def load_expected_output(self, test_case: str) -> Dict[str, Any]:
        """Load expected output JSON for test case."""
        import json

        file_path = self.test_data_dir / 'expected_outputs' / f'{test_case}_expected.json'

        if not file_path.exists():
            return {}

        with open(file_path, 'r') as f:
            return json.load(f)

    def load_all_samples(self, category: Optional[str] = None) -> Dict[str, etree.Element]:
        """Load all samples from a category or all categories."""
        samples = {}

        if category:
            category_dir = self.test_data_dir / 'svg_samples' / category
            if category_dir.exists():
                for svg_file in category_dir.glob('*.svg'):
                    samples[svg_file.stem] = etree.parse(str(svg_file)).getroot()
        else:
            # Load from all categories
            svg_dir = self.test_data_dir / 'svg_samples'
            for category_dir in svg_dir.iterdir():
                if category_dir.is_dir():
                    for svg_file in category_dir.glob('*.svg'):
                        key = f"{category_dir.name}/{svg_file.stem}"
                        samples[key] = etree.parse(str(svg_file)).getroot()

        return samples


class SVGComparisonHelper:
    """Helper for comparing SVG structures."""

    @staticmethod
    def compare_elements(
        elem1: etree.Element,
        elem2: etree.Element,
        ignore_attrs: Optional[List[str]] = None
    ) -> bool:
        """Compare two SVG elements for structural equality."""
        ignore_attrs = ignore_attrs or []

        # Compare tags
        if elem1.tag != elem2.tag:
            return False

        # Compare attributes (excluding ignored ones)
        attrs1 = {k: v for k, v in elem1.attrib.items() if k not in ignore_attrs}
        attrs2 = {k: v for k, v in elem2.attrib.items() if k not in ignore_attrs}

        if attrs1 != attrs2:
            return False

        # Compare text content
        text1 = (elem1.text or '').strip()
        text2 = (elem2.text or '').strip()

        if text1 != text2:
            return False

        # Compare children
        children1 = list(elem1)
        children2 = list(elem2)

        if len(children1) != len(children2):
            return False

        for child1, child2 in zip(children1, children2):
            if not SVGComparisonHelper.compare_elements(child1, child2, ignore_attrs):
                return False

        return True

    @staticmethod
    def extract_slide_content(
        svg_element: etree.Element,
        slide_id: str
    ) -> Optional[etree.Element]:
        """Extract content for a specific slide."""
        slide = svg_element.xpath(
            f"//svg:g[@id='{slide_id}']",
            namespaces={'svg': 'http://www.w3.org/2000/svg'}
        )

        return slide[0] if slide else None

    @staticmethod
    def diff_slides(
        slide1: etree.Element,
        slide2: etree.Element
    ) -> Dict[str, Any]:
        """Generate diff between two slide elements."""
        diff = {
            'added': [],
            'removed': [],
            'modified': []
        }

        # Create element maps by id
        elements1 = {
            elem.get('id', f'unnamed_{i}'): elem
            for i, elem in enumerate(slide1.iter())
            if elem.tag != etree.Comment
        }

        elements2 = {
            elem.get('id', f'unnamed_{i}'): elem
            for i, elem in enumerate(slide2.iter())
            if elem.tag != etree.Comment
        }

        # Find differences
        ids1 = set(elements1.keys())
        ids2 = set(elements2.keys())

        diff['removed'] = list(ids1 - ids2)
        diff['added'] = list(ids2 - ids1)

        # Check for modifications
        for elem_id in ids1 & ids2:
            if not SVGComparisonHelper.compare_elements(
                elements1[elem_id],
                elements2[elem_id]
            ):
                diff['modified'].append(elem_id)

        return diff
#!/usr/bin/env python3
"""
Clean Slate Page Detection

Simple, focused page boundary detection for multi-page conversion.
Replaces the complex 1700+ line detection system with common use cases.
"""

from typing import List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from lxml import etree as ET
from ..xml.safe_iter import walk

if TYPE_CHECKING:
    from ..policy.engine import PolicyEngine


@dataclass
class PageBreak:
    """Simple page break representation."""
    element: ET.Element
    page_number: int
    title: Optional[str] = None


class SimplePageDetector:
    """
    Simple page boundary detection for common use cases.

    Focuses on the most common scenarios:
    1. Multiple SVG files = multiple pages
    2. SVG elements with specific page break markers
    3. Large SVG documents split by size thresholds
    """

    def __init__(self, size_threshold: int = 10000, policy_engine: Optional['PolicyEngine'] = None):
        """
        Initialize simple page detector.

        Args:
            size_threshold: Content size threshold for automatic page breaks (deprecated - use policy_engine)
            policy_engine: Optional policy engine for threshold configuration
        """
        self._policy_engine = policy_engine

        # Use policy thresholds if available, otherwise use parameter
        if policy_engine:
            # Convert from KB to bytes for backward compatibility
            self.size_threshold = policy_engine.config.thresholds.max_single_page_size_kb * 1024
        else:
            self.size_threshold = size_threshold

    def detect_page_breaks_in_svg(self, svg_content: str) -> List[PageBreak]:
        """
        Detect page breaks within a single SVG document.

        Args:
            svg_content: SVG content to analyze

        Returns:
            List of detected page breaks
        """
        try:
            root = ET.fromstring(svg_content)
            page_breaks = []

            # Method 1: Look for explicit page break markers
            page_breaks.extend(self._find_page_markers(root))

            # Method 2: Look for grouped content that suggests pages
            page_breaks.extend(self._find_grouped_pages(root))

            # Method 3: Split large content by size if no explicit breaks found
            if not page_breaks:
                page_breaks.extend(self._split_by_size(root))

            return page_breaks

        except ET.XMLSyntaxError:
            # If SVG is malformed, treat as single page
            return []

    def _find_page_markers(self, root: ET.Element) -> List[PageBreak]:
        """Find explicit page break markers in SVG."""
        page_breaks = []

        # Look for elements with page-related attributes or classes
        page_markers = [
            ".//*[@class='page']",
            ".//*[@class='slide']",
            ".//*[@id[contains(., 'page')]]",
            ".//*[@id[contains(., 'slide')]]",
            ".//g[contains(@class, 'page')]",
            ".//g[contains(@id, 'page')]"
        ]

        page_number = 1
        for marker_xpath in page_markers:
            try:
                elements = root.xpath(marker_xpath)
                for element in elements:
                    title = self._extract_title(element)
                    page_breaks.append(PageBreak(
                        element=element,
                        page_number=page_number,
                        title=title
                    ))
                    page_number += 1
            except:
                # Skip invalid XPath expressions
                continue

        return page_breaks

    def _find_grouped_pages(self, root: ET.Element) -> List[PageBreak]:
        """Find pages based on grouped content structure."""
        page_breaks = []

        # Look for top-level groups that might represent pages
        top_level_groups = root.findall('.//g')

        # Get max pages from policy or use default
        max_pages = 10
        if self._policy_engine:
            max_pages = self._policy_engine.config.thresholds.max_pages_per_conversion

        if len(top_level_groups) > 1:
            for i, group in enumerate(top_level_groups[:max_pages]):
                # Check if group has substantial content
                children = list(group)
                min_elements = 3
                if self._policy_engine:
                    min_elements = self._policy_engine.config.thresholds.min_elements_per_page

                if len(children) >= min_elements:
                    title = self._extract_title(group) or f"Page {i+1}"
                    page_breaks.append(PageBreak(
                        element=group,
                        page_number=i+1,
                        title=title
                    ))

        return page_breaks

    def _split_by_size(self, root: ET.Element) -> List[PageBreak]:
        """Split content by size threshold if no other breaks found."""
        page_breaks = []

        # Calculate approximate content size
        content_size = len(ET.tostring(root, encoding='unicode'))

        if content_size > self.size_threshold:
            # For very large SVGs, suggest splitting into multiple pages
            estimated_pages = min(5, max(2, content_size // self.size_threshold))

            # Create artificial page breaks based on element distribution
            all_elements = list(walk(root))
            elements_per_page = len(all_elements) // estimated_pages

            for i in range(estimated_pages):
                start_idx = i * elements_per_page
                if start_idx < len(all_elements):
                    element = all_elements[start_idx]
                    page_breaks.append(PageBreak(
                        element=element,
                        page_number=i+1,
                        title=f"Auto Page {i+1}"
                    ))

        return page_breaks

    def _extract_title(self, element: ET.Element) -> Optional[str]:
        """Extract title from element attributes."""
        # Try various title sources
        title_sources = [
            element.get('title'),
            element.get('data-title'),
            element.get('aria-label'),
            element.get('id'),
            element.get('class')
        ]

        for title in title_sources:
            if title and title.strip():
                return title.strip()

        # Look for title or desc child elements
        for child_tag in ['title', 'desc']:
            child = element.find(f'.//{child_tag}')
            if child is not None and child.text:
                return child.text.strip()

        return None


def split_svg_into_pages(svg_content: str) -> List[Tuple[str, Optional[str]]]:
    """
    Split SVG content into multiple pages.

    Args:
        svg_content: Original SVG content

    Returns:
        List of (page_content, page_title) tuples
    """
    detector = SimplePageDetector()
    page_breaks = detector.detect_page_breaks_in_svg(svg_content)

    if not page_breaks:
        # No page breaks found, return as single page
        return [(svg_content, None)]

    pages = []
    try:
        root = ET.fromstring(svg_content)

        for page_break in page_breaks:
            # Create a new SVG document with just this page's content
            page_root = ET.Element("svg")
            page_root.attrib.update(root.attrib)

            # Copy the page break element and its children
            page_root.append(page_break.element)

            # Convert back to string
            page_content = ET.tostring(page_root, encoding='unicode', pretty_print=True)
            pages.append((page_content, page_break.title))

    except ET.XMLSyntaxError:
        # If parsing fails, return original as single page
        return [(svg_content, None)]

    return pages


def detect_multiple_svg_files(file_paths: List[str]) -> List[Tuple[str, str]]:
    """
    Detect pages from multiple SVG files.

    Args:
        file_paths: List of SVG file paths

    Returns:
        List of (file_path, suggested_title) tuples
    """
    pages = []

    for file_path in file_paths:
        try:
            from pathlib import Path
            path = Path(file_path)
            title = path.stem.replace('_', ' ').replace('-', ' ').title()
            pages.append((file_path, title))
        except:
            pages.append((file_path, f"Page {len(pages) + 1}"))

    return pages
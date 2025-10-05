#!/usr/bin/env python3
"""
Preprocessor Chain

Orchestrates multiple preprocessors in the correct order for optimal
SVG normalization before IR conversion.

Features:
- Configurable processor chains
- Error handling and recovery
- Performance monitoring
- Validation integration
"""

import logging
import time
from typing import Any, Dict, List

from lxml import etree as ET

from ..xml.safe_iter import walk
from .base import BasePreprocessor
from .expand_use import ExpandUsePreprocessor
from .normalize_transforms import NormalizeTransformsPreprocessor
from .resolve_clips import ResolveClipsPreprocessor
from .text_layout_prep import TextLayoutPrepPreprocessor


class PreprocessorChain:
    """
    Orchestrates multiple SVG preprocessors in optimal order.

    Ensures preprocessors are applied in the correct sequence
    for maximum effectiveness and minimal conflicts.
    """

    def __init__(self, processors: list[BasePreprocessor] = None):
        """
        Initialize preprocessor chain.

        Args:
            processors: List of preprocessors (None for default chain)
        """
        self.processors = processors or self._create_default_chain()
        self.logger = logging.getLogger(__name__)
        self.metrics: dict[str, Any] = {}

    def process(self, svg_root: ET.Element, validate: bool = True) -> ET.Element:
        """
        Process SVG through the preprocessor chain.

        Args:
            svg_root: SVG root element
            validate: Whether to validate at each step

        Returns:
            Fully preprocessed SVG
        """
        if not self._validate_input(svg_root):
            raise ValueError("Invalid SVG input")

        self.logger.info(f"Starting preprocessor chain with {len(self.processors)} processors")
        start_time = time.perf_counter()

        current_svg = svg_root
        processor_metrics = {}

        for i, processor in enumerate(self.processors):
            processor_name = processor.__class__.__name__
            self.logger.debug(f"Running processor {i+1}/{len(self.processors)}: {processor_name}")

            try:
                # Run processor
                processor_start = time.perf_counter()
                current_svg = processor.process(current_svg)
                processor_duration = time.perf_counter() - processor_start

                # Record metrics
                processor_metrics[processor_name] = {
                    'duration_sec': processor_duration,
                    'success': True,
                    'index': i,
                }

                # Validate after each processor if requested
                if validate and not self._validate_svg_integrity(current_svg):
                    raise ValueError(f"SVG integrity check failed after {processor_name}")

            except Exception as e:
                self.logger.error(f"Processor {processor_name} failed: {e}")
                processor_metrics[processor_name] = {
                    'duration_sec': 0,
                    'success': False,
                    'error': str(e),
                    'index': i,
                }

                # Decide whether to continue or abort
                if self._is_critical_processor(processor):
                    raise
                else:
                    self.logger.warning(f"Continuing chain despite {processor_name} failure")

        # Record overall metrics
        total_duration = time.perf_counter() - start_time
        self.metrics = {
            'total_duration_sec': total_duration,
            'processor_count': len(self.processors),
            'successful_processors': sum(1 for m in processor_metrics.values() if m.get('success', False)),
            'failed_processors': sum(1 for m in processor_metrics.values() if not m.get('success', True)),
            'processors': processor_metrics,
        }

        self.logger.info(f"Preprocessor chain completed in {total_duration:.3f}s")
        return current_svg

    def get_metrics(self) -> dict[str, Any]:
        """Get preprocessing metrics."""
        return self.metrics.copy()

    def _create_default_chain(self) -> list[BasePreprocessor]:
        """Create the default preprocessor chain in optimal order."""
        return [
            # 1. Expand USE elements first (creates new content)
            ExpandUsePreprocessor(),

            # 2. Prepare text layout (before transform normalization)
            TextLayoutPrepPreprocessor(),

            # 3. Normalize transforms (after content expansion)
            NormalizeTransformsPreprocessor(flatten_simple_transforms=True),

            # 4. Resolve clipping last (after all content is finalized)
            ResolveClipsPreprocessor(flatten_nested_clips=True),
        ]

    def _validate_input(self, svg_root: ET.Element) -> bool:
        """Validate input SVG."""
        if svg_root is None:
            return False

        # Check if it's an SVG element
        if not svg_root.tag.endswith('svg'):
            return False

        # Basic structure validation
        try:
            # Check if we can parse namespaces
            nsmap = svg_root.nsmap
            if nsmap is None:
                return False
        except Exception:
            return False

        return True

    def _validate_svg_integrity(self, svg_root: ET.Element) -> bool:
        """Validate SVG integrity after processing."""
        try:
            # Check that root is still valid
            if not svg_root.tag.endswith('svg'):
                return False

            # Check for basic structural integrity
            if svg_root.getparent() is not None:
                # Root should not have a parent
                return False

            # Verify we can still traverse the tree
            element_count = len(list(walk(svg_root)))
            if element_count == 0:
                return False

            return True

        except Exception as e:
            self.logger.warning(f"SVG integrity validation failed: {e}")
            return False

    def _is_critical_processor(self, processor: BasePreprocessor) -> bool:
        """Check if processor failure should abort the chain."""
        # USE expansion and transform normalization are critical
        critical_types = [ExpandUsePreprocessor, NormalizeTransformsPreprocessor]
        return any(isinstance(processor, critical_type) for critical_type in critical_types)


def create_standard_chain() -> PreprocessorChain:
    """
    Create standard preprocessor chain for typical SVG processing.

    Returns:
        Configured preprocessor chain
    """
    return PreprocessorChain()


def create_minimal_chain() -> PreprocessorChain:
    """
    Create minimal preprocessor chain for simple SVGs.

    Returns:
        Minimal preprocessor chain
    """
    return PreprocessorChain([
        NormalizeTransformsPreprocessor(flatten_simple_transforms=True),
        TextLayoutPrepPreprocessor(),
    ])


def create_comprehensive_chain() -> PreprocessorChain:
    """
    Create comprehensive preprocessor chain for complex SVGs.

    Returns:
        Comprehensive preprocessor chain
    """
    return PreprocessorChain([
        ExpandUsePreprocessor(),
        TextLayoutPrepPreprocessor(),
        NormalizeTransformsPreprocessor(flatten_simple_transforms=False),  # Keep complex transforms
        ResolveClipsPreprocessor(flatten_nested_clips=True),
    ])


def preprocess_svg(svg_root: ET.Element, chain_type: str = "standard") -> ET.Element:
    """
    Convenience function to preprocess SVG with specified chain.

    Args:
        svg_root: SVG root element
        chain_type: Chain type ("standard", "minimal", "comprehensive")

    Returns:
        Preprocessed SVG
    """
    chain_factories = {
        "standard": create_standard_chain,
        "minimal": create_minimal_chain,
        "comprehensive": create_comprehensive_chain,
    }

    factory = chain_factories.get(chain_type, create_standard_chain)
    chain = factory()
    return chain.process(svg_root)


def validate_preprocessed_svg(svg_root: ET.Element) -> dict[str, Any]:
    """
    Validate preprocessed SVG and return analysis.

    Args:
        svg_root: Preprocessed SVG root

    Returns:
        Validation analysis
    """
    analysis = {
        'valid': True,
        'issues': [],
        'metrics': {},
        'recommendations': [],
    }

    try:
        # Count elements by type
        element_counts = {}
        for element in walk(svg_root):
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            element_counts[tag] = element_counts.get(tag, 0) + 1

        analysis['metrics']['element_counts'] = element_counts
        analysis['metrics']['total_elements'] = sum(element_counts.values())

        # Check for remaining USE elements
        use_count = element_counts.get('use', 0)
        if use_count > 0:
            analysis['issues'].append(f"Found {use_count} unresolved USE elements")
            analysis['recommendations'].append("Run ExpandUsePreprocessor")

        # Check for clip-path attributes
        clip_refs = svg_root.xpath(".//*[@clip-path]")
        if clip_refs:
            analysis['issues'].append(f"Found {len(clip_refs)} unresolved clip-path references")
            analysis['recommendations'].append("Run ResolveClipsPreprocessor")

        # Check for complex transforms
        complex_transforms = svg_root.xpath(".//*[contains(@transform, 'matrix')]")
        analysis['metrics']['complex_transforms'] = len(complex_transforms)

        # Check text preparation
        unprepared_text = svg_root.xpath(".//svg:text[not(@data-text-layout)]",
                                       namespaces={'svg': 'http://www.w3.org/2000/svg'})
        if unprepared_text:
            analysis['issues'].append(f"Found {len(unprepared_text)} unprepared text elements")
            analysis['recommendations'].append("Run TextLayoutPrepPreprocessor")

        # Overall validation
        if analysis['issues']:
            analysis['valid'] = False

    except Exception as e:
        analysis['valid'] = False
        analysis['issues'].append(f"Validation error: {e}")

    return analysis
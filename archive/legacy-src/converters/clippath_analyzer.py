#!/usr/bin/env python3
"""
ClipPath Complexity Analyzer

This module analyzes SVG clipPath elements to determine the optimal conversion
strategy for PowerPoint compatibility. It categorizes clipPaths by complexity
and provides recommendations for the conversion approach.

Key Features:
- Complexity classification (SIMPLE, NESTED, COMPLEX, UNSUPPORTED)
- Nested clipPath chain resolution
- Content analysis for conversion strategy
- Integration with existing ClipPathDefinition structure
"""

from __future__ import annotations
from typing import List, Dict, Set, Optional, Tuple, Any
from lxml import etree as ET
import logging

from .clippath_types import (
    ClipPathComplexity, ClipPathDefinition, ClipPathAnalysis
)

logger = logging.getLogger(__name__)


class ClipPathAnalyzer:
    """
    Analyzes SVG clipPath elements to determine optimal conversion strategy.

    This analyzer examines clipPath content, nesting, and complexity to recommend
    the best approach for PowerPoint conversion while preserving maximum quality.
    """

    def __init__(self, services=None):
        """
        Initialize ClipPathAnalyzer.

        Args:
            services: ConversionServices for advanced analysis (optional)
        """
        self.services = services
        self._analysis_cache: Dict[str, ClipPathAnalysis] = {}
        self._clippath_definitions: Dict[str, ClipPathDefinition] = {}

    def analyze_clippath(self, element: ET.Element,
                        clippath_definitions: Dict[str, ClipPathDefinition],
                        clip_ref: str) -> ClipPathAnalysis:
        """
        Analyze clipPath complexity and determine conversion strategy.

        Args:
            element: Element with clip-path attribute
            clippath_definitions: Available clipPath definitions
            clip_ref: clipPath reference (e.g., "url(#clip1)")

        Returns:
            ClipPathAnalysis with conversion strategy recommendation
        """
        # Parse clipPath reference
        clip_id = self._parse_clippath_reference(clip_ref)
        if not clip_id:
            return self._create_unsupported_analysis("Invalid clipPath reference")

        # Check cache
        cache_key = f"{clip_id}_{element.tag}"
        if cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]

        # Store definitions for chain resolution
        self._clippath_definitions = clippath_definitions

        try:
            # Resolve clipPath chain
            clip_chain = self._resolve_clippath_chain(clip_id, set())
            if not clip_chain:
                return self._create_unsupported_analysis(f"ClipPath {clip_id} not found")

            # Analyze complexity
            analysis = self._analyze_clip_chain_complexity(clip_chain, element)

            # Cache result
            self._analysis_cache[cache_key] = analysis

            logger.debug(f"ClipPath analysis for {clip_id}: {analysis.complexity.value} - {analysis.reason}")
            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze clipPath {clip_id}: {e}")
            return self._create_unsupported_analysis(f"Analysis error: {e}")

    def _resolve_clippath_chain(self, clip_id: str, visited: Set[str]) -> List[ClipPathDefinition]:
        """
        Resolve nested clipPath references into a chain.

        Args:
            clip_id: ClipPath ID to resolve
            visited: Set of visited IDs to detect circular references

        Returns:
            List of ClipPathDefinition objects in resolution order
        """
        if clip_id in visited:
            logger.warning(f"Circular clipPath reference detected: {clip_id}")
            return []

        if clip_id not in self._clippath_definitions:
            logger.warning(f"ClipPath definition not found: {clip_id}")
            return []

        visited.add(clip_id)
        clip_def = self._clippath_definitions[clip_id]
        chain = [clip_def]

        # Check for nested clipPath references in shapes
        if clip_def.shapes:
            for shape in clip_def.shapes:
                nested_ref = shape.get('clip-path')
                if nested_ref:
                    nested_id = self._parse_clippath_reference(nested_ref)
                    if nested_id:
                        nested_chain = self._resolve_clippath_chain(nested_id, visited.copy())
                        chain.extend(nested_chain)

        visited.discard(clip_id)
        return chain

    def _analyze_clip_chain_complexity(self, clip_chain: List[ClipPathDefinition],
                                     target_element: ET.Element) -> ClipPathAnalysis:
        """
        Analyze the complexity of a resolved clipPath chain.

        Args:
            clip_chain: Resolved clipPath chain
            target_element: Element being clipped

        Returns:
            ClipPathAnalysis with complexity assessment
        """
        # Start with simple assumption
        complexity = ClipPathComplexity.SIMPLE
        reason = "Single simple clipPath"
        can_flatten = True
        requires_emf = False

        # Analyze chain length
        if len(clip_chain) > 1:
            complexity = ClipPathComplexity.NESTED
            reason = f"Nested clipPath chain ({len(clip_chain)} levels)"

        # Analyze content complexity
        total_nodes = 0
        has_text = False
        has_filters = False
        has_animations = False
        transform_complexity = 0

        for clip_def in clip_chain:
            if clip_def.shapes:
                for shape in clip_def.shapes:
                    # Count nodes
                    total_nodes += 1

                    # Check for text content
                    if self._has_text_content(shape):
                        has_text = True
                        complexity = ClipPathComplexity.COMPLEX
                        reason = "Contains text elements"
                        requires_emf = True

                    # Check for filters
                    if self._has_filter_effects(shape):
                        has_filters = True
                        complexity = ClipPathComplexity.COMPLEX
                        reason = "Contains filter effects"
                        requires_emf = True

                    # Check for animations
                    if self._has_animations(shape):
                        has_animations = True
                        complexity = ClipPathComplexity.UNSUPPORTED
                        reason = "Contains animations"
                        can_flatten = False
                        requires_emf = False  # Even EMF can't handle animations

                    # Analyze transform complexity
                    transform_level = self._analyze_transform_complexity(shape)
                    transform_complexity = max(transform_complexity, transform_level)

            # Check clipPath-level transforms
            if clip_def.transform:
                clip_transform_level = self._analyze_transform_complexity_string(clip_def.transform)
                transform_complexity = max(transform_complexity, clip_transform_level)

        # Adjust complexity based on transform complexity
        if transform_complexity >= 2 and complexity == ClipPathComplexity.SIMPLE:
            complexity = ClipPathComplexity.COMPLEX
            reason = "Complex transforms require EMF"
            requires_emf = True

        # Adjust complexity based on multiple shapes in single clipPath
        if total_nodes > 1 and complexity == ClipPathComplexity.SIMPLE:
            complexity = ClipPathComplexity.NESTED
            reason = f"Multiple shapes ({total_nodes}) require flattening"

        # Check if flattening is feasible
        if total_nodes > 10:  # Arbitrary threshold for complexity
            if complexity == ClipPathComplexity.NESTED:
                complexity = ClipPathComplexity.COMPLEX
                reason = f"Too many nodes ({total_nodes}) for efficient flattening"
                requires_emf = True

        # Final validation
        if complexity == ClipPathComplexity.UNSUPPORTED:
            can_flatten = False
            requires_emf = False
        elif complexity == ClipPathComplexity.COMPLEX:
            requires_emf = True

        return ClipPathAnalysis(
            complexity=complexity,
            clip_chain=clip_chain,
            can_flatten=can_flatten,
            requires_emf=requires_emf,
            reason=reason,
            estimated_nodes=total_nodes,
            has_text=has_text,
            has_filters=has_filters,
            has_animations=has_animations,
            transform_complexity=transform_complexity
        )

    def _has_text_content(self, element: ET.Element) -> bool:
        """Check if element contains text content."""
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

        # Direct text elements
        if tag in ['text', 'tspan', 'textPath']:
            return True

        # Check for nested text elements using descendant search
        for descendant in element.iter():
            tag = descendant.tag.split('}')[-1] if '}' in descendant.tag else descendant.tag
            if tag in ['text', 'tspan', 'textPath']:
                return True
        return False

    def _has_filter_effects(self, element: ET.Element) -> bool:
        """Check if element has filter effects."""
        # Check filter attribute
        if element.get('filter'):
            return True

        # Check nested filter elements using descendant search
        for descendant in element.iter():
            if descendant.get('filter'):
                return True
        return False

    def _has_animations(self, element: ET.Element) -> bool:
        """Check if element contains animations."""
        # SMIL animation elements
        animation_tags = ['animate', 'animateTransform', 'animateMotion', 'animateColor', 'set']

        for descendant in element.iter():
            tag = descendant.tag.split('}')[-1] if '}' in descendant.tag else descendant.tag
            if tag in animation_tags:
                return True

        return False

    def _analyze_transform_complexity(self, element: ET.Element) -> int:
        """
        Analyze transform complexity level.

        Returns:
            0: No transform
            1: Simple transform (translate, scale, rotate)
            2: Complex transform (matrix, skew, multiple combined)
        """
        transform = element.get('transform')
        if not transform:
            return 0

        return self._analyze_transform_complexity_string(transform)

    def _analyze_transform_complexity_string(self, transform: str) -> int:
        """Analyze transform string complexity."""
        if not transform:
            return 0

        # Count transform functions
        transform_functions = ['matrix', 'translate', 'scale', 'rotate', 'skewX', 'skewY']
        function_count = 0
        has_matrix = False
        has_skew = False

        for func in transform_functions:
            if func in transform:
                function_count += 1
                if func == 'matrix':
                    has_matrix = True
                elif func.startswith('skew'):
                    has_skew = True

        # Determine complexity
        if function_count == 0:
            return 0
        elif function_count == 1 and not has_matrix and not has_skew:
            return 1  # Simple single transform
        else:
            return 2  # Complex (multiple, matrix, or skew)

    def _parse_clippath_reference(self, clip_ref: str) -> Optional[str]:
        """Parse clipPath reference to extract ID."""
        if not clip_ref:
            return None

        # Handle url(#id) format
        if clip_ref.startswith('url(#') and clip_ref.endswith(')'):
            return clip_ref[5:-1]

        # Handle direct #id reference
        if clip_ref.startswith('#'):
            return clip_ref[1:]

        return None

    def _create_unsupported_analysis(self, reason: str) -> ClipPathAnalysis:
        """Create an unsupported analysis result."""
        return ClipPathAnalysis(
            complexity=ClipPathComplexity.UNSUPPORTED,
            clip_chain=[],
            can_flatten=False,
            requires_emf=False,
            reason=reason
        )

    def clear_cache(self) -> None:
        """Clear analysis cache."""
        self._analysis_cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'cache_size': len(self._analysis_cache),
            'definitions_count': len(self._clippath_definitions)
        }
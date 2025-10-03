#!/usr/bin/env python3
"""
SVG Switch Element Processor for Clean Slate Architecture

Implements conditional rendering support for SVG switch elements.
The switch element evaluates its children in document order and returns
the first child that meets the specified conditions.

SVG Switch Element Specification:
- Tests child elements in document order
- Returns the first child whose conditional attributes evaluate to true
- Supports conditional attributes like requiredFeatures, systemLanguage
- Provides fallback content when no conditions are met
- Container element that affects child rendering logic

This processor provides utilities for other components to handle switch elements.
"""

import logging
from typing import List, Optional, Dict, Any
from lxml import etree as ET
from dataclasses import dataclass

from ..policy import create_policy, Policy, PolicyDecision

logger = logging.getLogger(__name__)


@dataclass
class SwitchResult:
    """Result of processing a switch element"""
    selected_element: Optional[ET.Element]
    matched_conditions: Dict[str, Any]
    fallback_used: bool = False
    policy_decision: Optional[PolicyDecision] = None


class SwitchProcessor:
    """
    Processor for SVG switch elements with conditional rendering.

    The switch element provides conditional rendering based on feature tests
    and system capabilities. This processor evaluates conditions and selects
    the appropriate child element for processing by other components.

    Key Features:
    - Conditional expression evaluation using policy engine
    - Child element selection logic
    - Default fallback content support
    - Integration with existing pipeline components
    """

    def __init__(self, policy: Optional[Policy] = None):
        """
        Initialize switch processor.

        Args:
            policy: Policy engine for feature/extension decisions (defaults to BALANCED)
        """
        self.policy = policy or create_policy()

    def can_process(self, element: ET.Element) -> bool:
        """
        Check if this processor can handle the given element.

        Args:
            element: SVG element to check

        Returns:
            True if element is a switch element, False otherwise
        """
        if element is None:
            return False

        # Handle both namespaced and non-namespaced elements
        tag_name = element.tag
        if tag_name.startswith('{'):
            # Remove namespace
            tag_name = tag_name.split('}')[-1]

        return tag_name == 'switch'

    def process(self, element: ET.Element, context: Any = None) -> SwitchResult:
        """
        Process SVG switch element with conditional rendering.

        Args:
            element: SVG switch element
            context: Optional processing context

        Returns:
            SwitchResult with selected child element or None
        """
        try:
            logger.debug(f"Processing switch element with {len(element)} children")

            # Evaluate child elements in document order
            selected_child = self._select_child_element(element, context)
            matched_conditions = {}

            if selected_child is not None:
                logger.debug(f"Selected child: {selected_child.tag}")

                # Collect the conditions that were matched
                matched_conditions = self._get_matched_conditions(selected_child)

                return SwitchResult(
                    selected_element=selected_child,
                    matched_conditions=matched_conditions,
                    fallback_used=False
                )
            else:
                # No child met conditions
                logger.info("Switch element: no child conditions met")
                return SwitchResult(
                    selected_element=None,
                    matched_conditions={},
                    fallback_used=True
                )

        except Exception as e:
            logger.error(f"Error processing switch element: {e}")
            return SwitchResult(
                selected_element=None,
                matched_conditions={'error': str(e)},
                fallback_used=True
            )

    def _select_child_element(self, switch_element: ET.Element, context: Any) -> Optional[ET.Element]:
        """
        Select the first child element that meets conditional requirements.

        Evaluates children in document order and returns the first one
        whose conditional attributes evaluate to true.

        Args:
            switch_element: SVG switch element
            context: Conversion context

        Returns:
            Selected child element or None if no conditions are met
        """
        for child in switch_element:
            # Skip text nodes and comments
            if not isinstance(child.tag, str):
                continue

            # Check if child meets conditional requirements
            if self._evaluate_conditions(child, context):
                logger.debug(f"Child element {child.tag} meets conditions")
                return child
            else:
                logger.debug(f"Child element {child.tag} conditions not met")

        # No child met conditions
        logger.debug("No child elements met switch conditions")
        return None

    def _evaluate_conditions(self, element: ET.Element, context: Any) -> bool:
        """
        Evaluate conditional attributes for an element using policy engine.

        SVG conditional attributes include:
        - requiredFeatures: Required SVG features
        - systemLanguage: System language preferences
        - requiredExtensions: Required extensions

        Args:
            element: Element to evaluate
            context: Conversion context

        Returns:
            True if all conditions are met, False otherwise
        """
        # Extract conditional attributes
        required_features = element.get('requiredFeatures')
        system_language = element.get('systemLanguage')
        required_extensions = element.get('requiredExtensions')

        # Use policy engine to make decision
        decision = self.policy.decide_svg_switch_conditions(
            required_features=required_features,
            system_language=system_language,
            required_extensions=required_extensions
        )

        # Log decision details
        if decision.reasons:
            logger.debug(f"Switch condition decision: {decision.explain()}")

        return decision.use_native


    def _get_matched_conditions(self, element: ET.Element) -> Dict[str, Any]:
        """
        Get the conditions that were matched for the selected element.

        Args:
            element: Selected element

        Returns:
            Dictionary of matched conditions
        """
        conditions = {}

        required_features = element.get('requiredFeatures')
        if required_features:
            conditions['requiredFeatures'] = required_features

        system_language = element.get('systemLanguage')
        if system_language:
            conditions['systemLanguage'] = system_language

        required_extensions = element.get('requiredExtensions')
        if required_extensions:
            conditions['requiredExtensions'] = required_extensions

        return conditions


def create_switch_processor() -> SwitchProcessor:
    """
    Factory function to create a switch processor instance.

    Returns:
        Configured SwitchProcessor instance
    """
    return SwitchProcessor()
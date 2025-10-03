#!/usr/bin/env python3
"""
Policy-Driven MergeFilter with Fallback Strategies

Provides multiple rendering strategies for feMerge based on policy decisions:
1. LAYER_STACK: Full fidelity - duplicate shapes with z-ordering
2. SINGLE_COMPOSITE: Performance - flatten to single shape with effects
3. EMF_RASTERIZE: Compatibility - render to EMF for complex merges
"""

from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass
from enum import Enum
from lxml import etree
import logging

from ..policy.engine import Policy
from ..policy.config import OutputTarget
from ..policy.targets import PolicyDecision, DecisionReason


class MergeStrategy(Enum):
    """Rendering strategies for feMerge based on policy."""
    LAYER_STACK = "layer_stack"  # Full fidelity: duplicate shapes + z-order
    SINGLE_COMPOSITE = "single_composite"  # Performance: flatten to one shape
    EMF_RASTERIZE = "emf_rasterize"  # Compatibility: rasterize complex merges


@dataclass
class MergeFilterDecision(PolicyDecision):
    """Policy decision for merge filter rendering."""
    strategy: MergeStrategy
    input_count: int
    complexity_score: float
    supports_blending: bool
    requires_compositor: bool


@dataclass
class MergeParameters:
    """Parameters for merge operations."""
    merge_inputs: List[str]
    result_name: str = "merge"
    has_blend_modes: bool = False
    has_opacity: bool = False


class MergeFilter:
    """
    Policy-driven SVG feMerge filter with multiple fallback strategies.

    Strategies based on policy and complexity:
    - QUALITY target: Always use LAYER_STACK for full fidelity
    - BALANCED target: Use LAYER_STACK for <=3 inputs, SINGLE_COMPOSITE for more
    - SPEED target: Always flatten to SINGLE_COMPOSITE
    - COMPATIBILITY target: Use EMF_RASTERIZE for complex blending
    """

    def __init__(self, policy: Optional[Policy] = None):
        """Initialize with policy engine."""
        self.policy = policy or Policy()
        self.logger = logging.getLogger(__name__)

    def decide_strategy(self, params: MergeParameters) -> MergeFilterDecision:
        """
        Make policy-based decision on merge strategy.

        Args:
            params: Merge parameters including inputs and blend info

        Returns:
            MergeFilterDecision with chosen strategy and reasoning
        """
        reasons = []
        input_count = len(params.merge_inputs)

        # Calculate complexity score
        complexity_score = self._calculate_complexity(params)

        # Decision based on output target
        target = self.policy.config.output_target

        if target == OutputTarget.QUALITY:
            # Always use full layer stack for highest quality
            strategy = MergeStrategy.LAYER_STACK
            reasons.append(DecisionReason.QUALITY_PRIORITY)
            requires_compositor = True

        elif target == OutputTarget.SPEED:
            # Always flatten for performance
            strategy = MergeStrategy.SINGLE_COMPOSITE
            reasons.append(DecisionReason.PERFORMANCE_PRIORITY)
            requires_compositor = False

        elif target == OutputTarget.COMPATIBILITY:
            # Use EMF for complex blending that PPTX can't handle
            if params.has_blend_modes or complexity_score > 0.7:
                strategy = MergeStrategy.EMF_RASTERIZE
                reasons.append(DecisionReason.COMPATIBILITY_MODE)
            else:
                strategy = MergeStrategy.SINGLE_COMPOSITE
                reasons.append(DecisionReason.SIMPLE_CONTENT)
            requires_compositor = False

        else:  # OutputTarget.BALANCED (default)
            # Smart decision based on complexity
            if input_count <= 3 and complexity_score < 0.5:
                strategy = MergeStrategy.LAYER_STACK
                reasons.append(DecisionReason.SIMPLE_CONTENT)
                requires_compositor = True
            elif input_count > 6 or complexity_score > 0.8:
                strategy = MergeStrategy.EMF_RASTERIZE
                reasons.append(DecisionReason.COMPLEX_CONTENT)
                requires_compositor = False
            else:
                strategy = MergeStrategy.SINGLE_COMPOSITE
                reasons.append(DecisionReason.BALANCED_MODE)
                requires_compositor = False

        # Log decision if configured
        if self.policy.config.log_decisions:
            self.logger.debug(
                f"feMerge strategy: {strategy.value} for {input_count} inputs "
                f"(complexity: {complexity_score:.2f}, target: {target.value})"
            )

        return MergeFilterDecision(
            use_native=strategy != MergeStrategy.EMF_RASTERIZE,
            reasons=reasons,
            strategy=strategy,
            input_count=input_count,
            complexity_score=complexity_score,
            supports_blending=params.has_blend_modes,
            requires_compositor=requires_compositor,
            confidence=0.9 if strategy == MergeStrategy.LAYER_STACK else 0.7,
            estimated_quality=self._estimate_quality(strategy),
            estimated_performance=self._estimate_performance(strategy, input_count)
        )

    def apply(self, element: etree.Element, context: Any) -> Dict[str, Any]:
        """
        Apply feMerge with policy-driven strategy.

        Returns different results based on chosen strategy:
        - LAYER_STACK: Returns render_plan for compositor
        - SINGLE_COMPOSITE: Returns flattened effect XML
        - EMF_RASTERIZE: Returns EMF generation instructions
        """
        params = self._parse_parameters(element)
        decision = self.decide_strategy(params)

        if decision.strategy == MergeStrategy.LAYER_STACK:
            return self._generate_layer_stack_plan(params, decision)
        elif decision.strategy == MergeStrategy.SINGLE_COMPOSITE:
            return self._generate_composite_effect(params, decision)
        else:  # EMF_RASTERIZE
            return self._generate_emf_instructions(params, decision)

    def _calculate_complexity(self, params: MergeParameters) -> float:
        """Calculate complexity score (0.0 to 1.0)."""
        base = len(params.merge_inputs) / 10.0  # Normalize to 10 as high
        blend_penalty = 0.3 if params.has_blend_modes else 0.0
        opacity_penalty = 0.1 if params.has_opacity else 0.0
        return min(1.0, base + blend_penalty + opacity_penalty)

    def _estimate_quality(self, strategy: MergeStrategy) -> float:
        """Estimate output quality for strategy."""
        return {
            MergeStrategy.LAYER_STACK: 0.95,
            MergeStrategy.SINGLE_COMPOSITE: 0.7,
            MergeStrategy.EMF_RASTERIZE: 0.8
        }.get(strategy, 0.5)

    def _estimate_performance(self, strategy: MergeStrategy, input_count: int) -> float:
        """Estimate performance for strategy."""
        if strategy == MergeStrategy.LAYER_STACK:
            # Performance degrades with more layers
            return max(0.3, 1.0 - (input_count * 0.1))
        elif strategy == MergeStrategy.SINGLE_COMPOSITE:
            return 0.9  # Fast - single shape
        else:  # EMF_RASTERIZE
            return 0.6  # Moderate - rasterization overhead

    def _parse_parameters(self, element: etree.Element) -> MergeParameters:
        """Parse feMerge element parameters."""
        merge_inputs = []
        has_opacity = False

        for child in element:
            if not isinstance(child.tag, str):
                continue
            if self._localname(child.tag) != "feMergeNode":
                continue

            input_name = child.get("in") or "SourceGraphic"
            merge_inputs.append(input_name.strip())

            # Check for opacity hints
            if child.get("opacity"):
                has_opacity = True

        result_name = element.get("result", "merge").strip() or "merge"

        # Check for blend mode hints (would need context about inputs)
        has_blend_modes = self._detect_blend_modes(element)

        return MergeParameters(
            merge_inputs=merge_inputs,
            result_name=result_name,
            has_blend_modes=has_blend_modes,
            has_opacity=has_opacity
        )

    def _generate_layer_stack_plan(self, params: MergeParameters,
                                  decision: MergeFilterDecision) -> Dict[str, Any]:
        """Generate render plan for layer stack compositor."""
        render_plan = [
            {"input": name, "z": idx}
            for idx, name in enumerate(params.merge_inputs)
        ]

        return {
            "strategy": "layer_stack",
            "drawingml": (
                "<a:effectLst>"
                f"<!-- feMerge '{params.result_name}': {len(params.merge_inputs)} layers -->"
                "</a:effectLst>"
            ),
            "metadata": {
                "filter_type": "merge",
                "decision": decision,
                "result_name": params.result_name,
                "layer_count": len(params.merge_inputs),
                "render_plan": render_plan,
                "requires_compositor": True
            }
        }

    def _generate_composite_effect(self, params: MergeParameters,
                                  decision: MergeFilterDecision) -> Dict[str, Any]:
        """Generate single composite effect as fallback."""
        # Create a flattened effect that approximates the merge
        # This is a simplified approach - could be enhanced with blend modes

        return {
            "strategy": "single_composite",
            "drawingml": (
                "<a:effectLst>"
                "  <a:outerShdw blurRad='63500' dist='0' dir='0' algn='ctr'>"
                "    <a:srgbClr val='000000'>"
                "      <a:alpha val='50000'/>"
                "    </a:srgbClr>"
                "  </a:outerShdw>"
                "</a:effectLst>"
            ),
            "metadata": {
                "filter_type": "merge",
                "decision": decision,
                "result_name": params.result_name,
                "flattened_inputs": params.merge_inputs,
                "quality_loss": "blend_modes_approximated"
            }
        }

    def _generate_emf_instructions(self, params: MergeParameters,
                                  decision: MergeFilterDecision) -> Dict[str, Any]:
        """Generate EMF rasterization instructions."""
        return {
            "strategy": "emf_rasterize",
            "drawingml": None,  # Will be replaced by EMF
            "metadata": {
                "filter_type": "merge",
                "decision": decision,
                "result_name": params.result_name,
                "requires_emf": True,
                "emf_config": {
                    "blend_mode": "normal",
                    "preserve_transparency": True,
                    "resolution_dpi": 150
                }
            }
        }

    def _detect_blend_modes(self, element: etree.Element) -> bool:
        """Detect if merge uses blend modes (simplified check)."""
        # Would need to analyze the actual input buffers to determine
        # if they have blend modes applied
        parent = element.getparent()
        if parent is not None:
            for sibling in parent:
                if self._localname(sibling.tag) == "feBlend":
                    return True
        return False

    @staticmethod
    def _localname(tag: str) -> str:
        """Get local name from tag."""
        if tag is None:
            return ""
        if tag.startswith("{"):
            return tag.split("}", 1)[1]
        return tag


# Fallback strategies for when compositor isn't available
class SimplifiedMergeCompositor:
    """
    Simplified compositor that generates single-shape approximations
    when full layer stacking isn't available.
    """

    def compose_simplified(self, params: MergeParameters) -> str:
        """Generate simplified single-shape approximation."""
        if len(params.merge_inputs) == 1:
            # Single input - just pass through
            return "<a:noFill/>"

        elif len(params.merge_inputs) == 2:
            # Two inputs - use shadow to simulate
            return (
                "<a:effectLst>"
                "  <a:outerShdw blurRad='40000' dist='0' dir='0'>"
                "    <a:schemeClr val='accent1'>"
                "      <a:alpha val='40000'/>"
                "    </a:schemeClr>"
                "  </a:outerShdw>"
                "</a:effectLst>"
            )

        else:
            # Multiple inputs - use glow + shadow
            return (
                "<a:effectLst>"
                "  <a:glow rad='63500'>"
                "    <a:schemeClr val='accent2'>"
                "      <a:alpha val='30000'/>"
                "    </a:schemeClr>"
                "  </a:glow>"
                "  <a:outerShdw blurRad='50800' dist='0' dir='0'>"
                "    <a:schemeClr val='accent1'>"
                "      <a:alpha val='50000'/>"
                "    </a:schemeClr>"
                "  </a:outerShdw>"
                "</a:effectLst>"
            )
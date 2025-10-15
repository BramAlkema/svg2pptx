"""
Group policy helper encapsulating nesting and flattening decisions.
"""

from __future__ import annotations

import logging

from .config import PolicyConfig
from ..ir import Group
from .targets import DecisionReason, GroupDecision

MAX_CLIP_COMPLEXITY = 10


class GroupPolicy:
    """Evaluate group structure and determine rendering strategy."""

    def __init__(self, config: PolicyConfig, logger: logging.Logger | None = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def decide(self, group: Group) -> GroupDecision:
        reasons: list[DecisionReason] = []
        element_count = len(group.children)
        nesting_depth = self._calculate_nesting_depth(group)
        group_clip_ready = bool(group.clip and getattr(group.clip, 'path_segments', None))
        has_complex_clipping = group.clip is not None and not group_clip_ready
        should_flatten = self._should_flatten_group(group)

        thresholds = self.config.thresholds

        if element_count > thresholds.max_group_elements:
            reasons.extend([DecisionReason.ABOVE_THRESHOLDS, DecisionReason.COMPLEX_GEOMETRY])
            return GroupDecision.emf(
                reasons=reasons,
                element_count=element_count,
                nesting_depth=nesting_depth,
                should_flatten=should_flatten,
                has_complex_clipping=has_complex_clipping,
                confidence=0.9,
            )

        if nesting_depth > thresholds.max_nesting_depth:
            reasons.extend([DecisionReason.ABOVE_THRESHOLDS, DecisionReason.COMPLEX_GEOMETRY])
            return GroupDecision.emf(
                reasons=reasons,
                element_count=element_count,
                nesting_depth=nesting_depth,
                should_flatten=should_flatten,
                has_complex_clipping=has_complex_clipping,
                confidence=0.85,
            )

        reasons.extend([DecisionReason.BELOW_THRESHOLDS, DecisionReason.SIMPLE_GEOMETRY])
        if group_clip_ready:
            reasons.append(DecisionReason.SUPPORTED_FEATURES)

        return GroupDecision.native(
            reasons=reasons,
            element_count=element_count,
            nesting_depth=nesting_depth,
            should_flatten=should_flatten,
            has_complex_clipping=has_complex_clipping,
            confidence=0.9,
            estimated_quality=0.95,
            estimated_performance=0.85,
        )

    def _calculate_nesting_depth(self, group: Group, current_depth: int = 0) -> int:
        max_depth = current_depth
        for child in group.children:
            if isinstance(child, Group):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        return max_depth

    def _should_flatten_group(self, group: Group) -> bool:
        return (
            self.config.enable_group_flattening
            and group.is_leaf_group
            and len(group.children) < MAX_CLIP_COMPLEXITY
            and group.clip is None
        )


__all__ = ["GroupPolicy"]

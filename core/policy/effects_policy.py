#!/usr/bin/env python3
"""
Effects Policy Engine

Governs DrawingML effect application with caps, clamps, and governance rules.
Ensures brand compliance, performance, and accessibility for blur, shadow, glow, etc.
"""

from dataclasses import dataclass
from typing import Optional

from ..ir.effects import (
    Effect, BlurEffect, ShadowEffect, GlowEffect,
    SoftEdgeEffect, ReflectionEffect
)
from .targets import EffectDecision, DecisionReason


@dataclass
class EffectCaps:
    """Effect capability caps and limits"""
    # Radius caps (points)
    max_blur_pt: float = 8.0
    max_shadow_blur_pt: float = 6.0
    max_shadow_dist_pt: float = 10.0
    max_glow_pt: float = 8.0
    max_soft_edge_pt: float = 5.0
    max_reflection_blur_pt: float = 8.0

    # Alpha limits
    min_alpha: float = 0.15
    max_alpha: float = 0.85

    # Budget limits
    max_effects_per_shape: int = 3
    max_total_effects_per_slide: int = 200

    # Feature toggles
    allow_blur: bool = True
    allow_outer_shadow: bool = True
    allow_inner_shadow: bool = False  # Not yet implemented
    allow_glow: bool = True
    allow_soft_edge: bool = True
    allow_reflection: bool = False  # Rarely used, can be expensive

    # Text-specific restrictions
    forbid_glow_on_text: bool = True
    forbid_reflection_on_text: bool = True

    # Conservative mode
    conservative_mode: bool = False  # Drop all effects if True


class EffectsPolicy:
    """Policy engine for DrawingML effects

    Applies caps, clamps, and governance rules to ensure:
    - Effects stay within performance budgets
    - Brand/accessibility compliance (alpha limits, color governance)
    - Appropriate effect usage (no glow on text, etc.)
    """

    def __init__(self, caps: Optional[EffectCaps] = None):
        """Initialize effects policy

        Args:
            caps: Effect capability caps (uses defaults if None)
        """
        self.caps = caps or EffectCaps()

    def decide_effect(
        self,
        effect: Effect,
        shape_type: str = "shape",
        is_text: bool = False,
        current_effect_count: int = 0
    ) -> EffectDecision:
        """Make policy decision for a single effect

        Args:
            effect: Effect to evaluate
            shape_type: Type of shape ('Circle', 'Rectangle', etc.)
            is_text: Whether this is a text shape
            current_effect_count: Number of effects already on this shape

        Returns:
            EffectDecision with action (allow/clamp/drop) and modified effect
        """
        # Conservative mode: drop all effects
        if self.caps.conservative_mode:
            return EffectDecision.drop(
                effect,
                type(effect).__name__,
                "conservative_mode",
                [DecisionReason.CONSERVATIVE_MODE]
            )

        # Budget check: max effects per shape
        if current_effect_count >= self.caps.max_effects_per_shape:
            return EffectDecision.drop(
                effect,
                type(effect).__name__,
                f"max_effects_per_shape={self.caps.max_effects_per_shape}",
                [DecisionReason.PERFORMANCE_LIMIT]
            )

        # Dispatch by effect type
        if isinstance(effect, BlurEffect):
            return self._decide_blur(effect)
        elif isinstance(effect, ShadowEffect):
            return self._decide_shadow(effect, is_text)
        elif isinstance(effect, GlowEffect):
            return self._decide_glow(effect, is_text)
        elif isinstance(effect, SoftEdgeEffect):
            return self._decide_soft_edge(effect)
        elif isinstance(effect, ReflectionEffect):
            return self._decide_reflection(effect, is_text)
        else:
            # Unknown effect type
            return EffectDecision.drop(
                effect,
                type(effect).__name__,
                "unknown_effect_type",
                [DecisionReason.UNSUPPORTED_FEATURES]
            )

    def _decide_blur(self, effect: BlurEffect) -> EffectDecision:
        """Policy decision for blur effect"""
        if not self.caps.allow_blur:
            return EffectDecision.drop(
                effect, "blur", "blur_disabled",
                [DecisionReason.USER_PREFERENCE]
            )

        # Clamp radius
        if effect.radius > self.caps.max_blur_pt:
            clamped = BlurEffect(radius=self.caps.max_blur_pt)
            return EffectDecision.clamp(
                effect, clamped, "blur",
                f"blur_radius {effect.radius:.1f}pt → {self.caps.max_blur_pt:.1f}pt",
                clamped_blur=True
            )

        return EffectDecision.allow(effect, "blur")

    def _decide_shadow(
        self,
        effect: ShadowEffect,
        is_text: bool
    ) -> EffectDecision:
        """Policy decision for shadow effect"""
        if not self.caps.allow_outer_shadow:
            return EffectDecision.drop(
                effect, "shadow", "shadow_disabled",
                [DecisionReason.USER_PREFERENCE]
            )

        clamped = False
        blur = effect.blur_radius
        dist = effect.distance
        alpha = effect.alpha

        # Clamp blur
        if blur > self.caps.max_shadow_blur_pt:
            blur = self.caps.max_shadow_blur_pt
            clamped = True

        # Clamp distance
        if dist > self.caps.max_shadow_dist_pt:
            dist = self.caps.max_shadow_dist_pt
            clamped = True

        # Clamp alpha
        if alpha < self.caps.min_alpha:
            alpha = self.caps.min_alpha
            clamped = True
        elif alpha > self.caps.max_alpha:
            alpha = self.caps.max_alpha
            clamped = True

        if clamped:
            clamped_effect = ShadowEffect(
                blur_radius=blur,
                distance=dist,
                angle=effect.angle,
                color=effect.color.upper(),  # Normalize to uppercase
                alpha=alpha
            )
            reason_parts = []
            if blur != effect.blur_radius:
                reason_parts.append(f"blur {effect.blur_radius:.1f}→{blur:.1f}pt")
            if dist != effect.distance:
                reason_parts.append(f"dist {effect.distance:.1f}→{dist:.1f}pt")
            if alpha != effect.alpha:
                reason_parts.append(f"alpha {effect.alpha:.2f}→{alpha:.2f}")

            return EffectDecision.clamp(
                effect, clamped_effect, "shadow",
                ", ".join(reason_parts),
                clamped_blur=(blur != effect.blur_radius),
                clamped_distance=(dist != effect.distance),
                clamped_alpha=(alpha != effect.alpha)
            )

        # Just normalize color to uppercase
        if effect.color != effect.color.upper():
            normalized = ShadowEffect(
                blur_radius=blur,
                distance=dist,
                angle=effect.angle,
                color=effect.color.upper(),
                alpha=alpha
            )
            return EffectDecision.allow(normalized, "shadow")

        return EffectDecision.allow(effect, "shadow")

    def _decide_glow(
        self,
        effect: GlowEffect,
        is_text: bool
    ) -> EffectDecision:
        """Policy decision for glow effect"""
        if not self.caps.allow_glow:
            return EffectDecision.drop(
                effect, "glow", "glow_disabled",
                [DecisionReason.USER_PREFERENCE]
            )

        # Forbid glow on text
        if is_text and self.caps.forbid_glow_on_text:
            return EffectDecision.drop(
                effect, "glow", "glow_on_text_forbidden",
                [DecisionReason.UNSUPPORTED_FEATURES]
            )

        # Clamp radius
        if effect.radius > self.caps.max_glow_pt:
            clamped = GlowEffect(
                radius=self.caps.max_glow_pt,
                color=effect.color.upper()
            )
            return EffectDecision.clamp(
                effect, clamped, "glow",
                f"glow_radius {effect.radius:.1f}pt → {self.caps.max_glow_pt:.1f}pt",
                clamped_blur=True
            )

        # Normalize color
        if effect.color != effect.color.upper():
            normalized = GlowEffect(radius=effect.radius, color=effect.color.upper())
            return EffectDecision.allow(normalized, "glow")

        return EffectDecision.allow(effect, "glow")

    def _decide_soft_edge(self, effect: SoftEdgeEffect) -> EffectDecision:
        """Policy decision for soft edge effect"""
        if not self.caps.allow_soft_edge:
            return EffectDecision.drop(
                effect, "soft_edge", "soft_edge_disabled",
                [DecisionReason.USER_PREFERENCE]
            )

        # Clamp radius
        if effect.radius > self.caps.max_soft_edge_pt:
            clamped = SoftEdgeEffect(radius=self.caps.max_soft_edge_pt)
            return EffectDecision.clamp(
                effect, clamped, "soft_edge",
                f"soft_edge_radius {effect.radius:.1f}pt → {self.caps.max_soft_edge_pt:.1f}pt",
                clamped_blur=True
            )

        return EffectDecision.allow(effect, "soft_edge")

    def _decide_reflection(
        self,
        effect: ReflectionEffect,
        is_text: bool
    ) -> EffectDecision:
        """Policy decision for reflection effect"""
        if not self.caps.allow_reflection:
            return EffectDecision.drop(
                effect, "reflection", "reflection_disabled",
                [DecisionReason.USER_PREFERENCE]
            )

        # Forbid reflection on text
        if is_text and self.caps.forbid_reflection_on_text:
            return EffectDecision.drop(
                effect, "reflection", "reflection_on_text_forbidden",
                [DecisionReason.UNSUPPORTED_FEATURES]
            )

        # Clamp blur
        if effect.blur_radius > self.caps.max_reflection_blur_pt:
            clamped = ReflectionEffect(
                blur_radius=self.caps.max_reflection_blur_pt,
                start_alpha=effect.start_alpha,
                end_alpha=effect.end_alpha,
                distance=effect.distance
            )
            return EffectDecision.clamp(
                effect, clamped, "reflection",
                f"reflection_blur {effect.blur_radius:.1f}pt → {self.caps.max_reflection_blur_pt:.1f}pt",
                clamped_blur=True
            )

        return EffectDecision.allow(effect, "reflection")

    def decide_effects(
        self,
        effects: list[Effect],
        shape_type: str = "shape",
        is_text: bool = False
    ) -> list[Effect]:
        """Apply policy to list of effects

        Args:
            effects: List of effects to evaluate
            shape_type: Type of shape
            is_text: Whether this is a text shape

        Returns:
            List of allowed/clamped effects (dropped effects removed)
        """
        decided: list[Effect] = []

        for i, effect in enumerate(effects):
            decision = self.decide_effect(
                effect,
                shape_type=shape_type,
                is_text=is_text,
                current_effect_count=i
            )

            if decision.action in ("allow", "clamp") and decision.modified_effect:
                decided.append(decision.modified_effect)
            # Else: drop or rasterize - don't include in output

        return decided

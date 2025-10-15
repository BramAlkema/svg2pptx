#!/usr/bin/env python3
"""
Animation Converter

Bridges the modular animation system with the Clean Slate pipeline.
Converts SMIL animations detected in the SVG into PowerPoint timing XML.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from lxml import etree as ET

from ..animations import (
    AnimationDefinition,
    AnimationSummary,
    PowerPointAnimationGenerator,
    SMILParser,
    TimelineGenerator,
    TimelineConfig,
    CalcMode,
)


@dataclass
class AnimationConversionResult:
    """Result of converting SVG animations to PowerPoint animations."""
    success: bool
    powerpoint_xml: str
    timeline_scenes: List[Any]
    animations: List[AnimationDefinition]
    summary: AnimationSummary
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "powerpoint_xml": self.powerpoint_xml,
            "timeline_scenes": len(self.timeline_scenes),
             "animation_count": len(self.animations),
            "summary": asdict(self.summary) if self.summary else None,
            "warnings": self.warnings,
            "errors": self.errors,
        }


class AnimationConverter:
    """Converts SMIL animations to PowerPoint drawingML timing XML."""

    def __init__(self, services=None):
        self.services = services
        self.parser = SMILParser()
        self.timeline_generator = TimelineGenerator(TimelineConfig())
        self.powerpoint_generator = PowerPointAnimationGenerator()

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def convert_svg_animations(self, svg_root: ET.Element | None) -> AnimationConversionResult:
        """
        Convert all SMIL animations in an SVG DOM to PowerPoint timing XML.

        Args:
            svg_root: Parsed SVG root element

        Returns:
            AnimationConversionResult describing generated animation XML.
        """
        if svg_root is None:
            summary = AnimationSummary()
            summary.add_warning("SVG root missing, no animations converted")
            return AnimationConversionResult(True, "", [], [], summary, warnings=summary.warnings.copy())

        animations = self.parser.parse_svg_animations(svg_root)
        summary = self.parser.get_animation_summary()

        if not animations:
            warnings = summary.warnings.copy()
            return AnimationConversionResult(True, "", [], animations, summary, warnings=warnings)

        scenes = self.timeline_generator.generate_timeline(animations)
        powerpoint_xml = self.powerpoint_generator.generate_animation_sequence(animations, scenes)

        warnings = self.parser.validate_animation_structure(animations)
        for warning in warnings:
            summary.add_warning(warning)

        summary.total_animations = len(animations)
        summary.element_count = len({anim.element_id for anim in animations})
        summary.duration = scenes[-1].time if scenes else 0.0
        summary.calculate_complexity()

        return AnimationConversionResult(
            success=True,
            powerpoint_xml=powerpoint_xml or "",
            timeline_scenes=scenes,
            animations=animations,
            summary=summary,
            warnings=summary.warnings.copy(),
            errors=[],
        )

    def get_animation_statistics(self, svg_root: ET.Element | None) -> Dict[str, Any]:
        """Return a simple statistics dictionary for animations in the SVG."""
        result = self.convert_svg_animations(svg_root)
        return {
            "total_animations": result.summary.total_animations,
            "unique_elements": result.summary.element_count,
            "duration": result.summary.duration,
            "warnings": result.warnings,
            "complexity": result.summary.complexity.value,
        }

    def validate_svg_for_animations(self, svg_root: ET.Element | None) -> tuple[bool, List[str]]:
        """Validate animations in SVG and return (is_valid, issues)."""
        if svg_root is None:
            return False, ["SVG root missing"]

        animations = self.parser.parse_svg_animations(svg_root)
        issues = self.parser.validate_animation_structure(animations)
        is_valid = not issues or issues == ["No animations found"]

        return is_valid, [] if is_valid else issues

    def build_powerpoint_xml(
        self,
        conversion_result: AnimationConversionResult,
        shape_id_map: dict[str, list[str]] | None = None,
    ) -> str:
        """Render PowerPoint timing XML using the stored animations and shape mapping."""
        return self.powerpoint_generator.generate_animation_sequence(
            conversion_result.animations,
            conversion_result.timeline_scenes,
            shape_id_map=shape_id_map,
        )

    def build_conversion_result(
        self,
        animations: List[AnimationDefinition],
        warnings: Optional[List[str]] = None,
    ) -> AnimationConversionResult:
        """Build an AnimationConversionResult from a supplied animation list."""
        warnings = warnings or []
        summary = AnimationSummary()

        if not animations:
            summary.total_animations = 0
            summary.element_count = 0
            summary.duration = 0.0
            summary.calculate_complexity()
            return AnimationConversionResult(
                success=True,
                powerpoint_xml="",
                timeline_scenes=[],
                animations=[],
                summary=summary,
                warnings=warnings,
                errors=[],
            )

        scenes = self.timeline_generator.generate_timeline(animations)
        powerpoint_xml = self.powerpoint_generator.generate_animation_sequence(animations, scenes)

        summary.total_animations = len(animations)
        summary.element_count = len({anim.element_id for anim in animations})
        summary.duration = scenes[-1].time if scenes else 0.0

        for animation in animations:
            if animation.is_transform_animation():
                summary.has_transforms = True
            if animation.is_motion_animation():
                summary.has_motion_paths = True
            if animation.is_color_animation():
                summary.has_color_animations = True
            if animation.calc_mode == CalcMode.SPLINE and animation.key_splines:
                summary.has_easing = True
            if animation.timing.begin > 0:
                summary.has_sequences = True

        summary.calculate_complexity()

        return AnimationConversionResult(
            success=True,
            powerpoint_xml=powerpoint_xml or "",
            timeline_scenes=scenes,
            animations=animations,
            summary=summary,
            warnings=warnings,
            errors=[],
        )

    def export_animation_data(self, svg_root: ET.Element | None, fmt: str = 'json') -> str:
        """Export animation data for debugging."""
        result = self.convert_svg_animations(svg_root)
        data = result.to_dict()

        if fmt == 'json':
            import json
            return json.dumps(data, indent=2)
        raise ValueError(f"Unsupported export format: {fmt}")

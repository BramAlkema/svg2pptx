#!/usr/bin/env python3
"""
CSS Animation Extractor

Converts CSS @keyframes + animation declarations into AnimationDefinition
objects so they can be consumed by the animation pipeline alongside SMIL.

This module adapts the standalone css_to_smil prototype into a reusable service.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import tinycss2
from cssselect2 import ElementWrapper, Matcher, compile_selector_list

from ..animations import (
    AnimationDefinition,
    AnimationTiming,
    AnimationType,
    CalcMode,
    TransformType,
)
from ..css import StyleResolver, StyleContext

# Supported animation properties for MVP
ANIMATED_PROPERTIES = {
    "opacity": AnimationType.ANIMATE,
    "transform": AnimationType.ANIMATE_TRANSFORM,
}


@dataclass
class KeyframeStep:
    offset: float
    properties: Dict[str, str]
    easing: Optional[str] = None


@dataclass
class CSSAnimation:
    name: str
    duration_ms: float
    delay_ms: float
    timing_function: str
    iteration_count: str
    direction: str
    fill_mode: str
    keyframes: List[KeyframeStep] = field(default_factory=list)


class CSSAnimationExtractor:
    """Extract CSS-based animations from an SVG DOM."""

    def __init__(self, style_resolver: StyleResolver | None = None) -> None:
        self.style_resolver = style_resolver or StyleResolver()

    def extract(self, svg_root, style_context: StyleContext | None = None) -> List[AnimationDefinition]:
        stylesheet_text = self._extract_styles(svg_root)
        sheet = tinycss2.parse_stylesheet(stylesheet_text, skip_whitespace=True, skip_comments=True)
        keyframes = self._parse_keyframes(sheet)
        matcher = self._build_matcher(sheet)
        styles = self._compute_styles(svg_root, matcher)

        animations: list[AnimationDefinition] = []

        for element, props in styles.items():
            animations.extend(
                self._element_animations(element, props, keyframes, style_context),
            )

        return animations

    # ------------------------------------------------------------------ #
    # Stylesheet parsing                                                 #
    # ------------------------------------------------------------------ #

    def _extract_styles(self, root) -> str:
        styles = []
        for style_el in root.findall('.//{http://www.w3.org/2000/svg}style'):
            styles.append("".join(style_el.itertext()) or "")
        return "\n\n".join(styles)

    def _parse_keyframes(self, sheet) -> Dict[str, List[KeyframeStep]]:
        result: Dict[str, List[KeyframeStep]] = {}
        for rule in sheet:
            if rule.type != "at-rule" or rule.at_keyword.lower() != "keyframes":
                continue
            name = tinycss2.serialize(rule.prelude).strip()
            steps: List[KeyframeStep] = []

            if rule.content:
                rule_list = tinycss2.parse_rule_list(rule.content)
                for block in rule_list:
                    if block.type != "qualified-rule":
                        continue
                    selector = tinycss2.serialize(block.prelude).strip().lower()
                    decls = tinycss2.parse_declaration_list(
                        block.content,
                        skip_whitespace=True,
                        skip_comments=True,
                    )
                    props = {
                        d.name.lower(): tinycss2.serialize(d.value).strip()
                        for d in decls
                        if d.type == "declaration" and not d.name.startswith("--")
                    }
                    easing = props.get("animation-timing-function")
                    if selector in ("from", "0%"):
                        offset = 0.0
                    elif selector in ("to", "100%"):
                        offset = 1.0
                    elif selector.endswith("%"):
                        try:
                            offset = float(selector[:-1]) / 100.0
                        except ValueError:
                            continue
                    else:
                        continue
                    steps.append(KeyframeStep(offset=offset, properties=props, easing=easing))

            steps.sort(key=lambda s: s.offset)
            if steps:
                result[name] = steps

        return result

    def _build_matcher(self, sheet) -> Matcher:
        matcher = Matcher()
        for rule in sheet:
            if rule.type != "qualified-rule":
                continue
            selector_text = tinycss2.serialize(rule.prelude).strip()
            try:
                compiled = compile_selector_list(selector_text)
            except Exception:
                continue

            decls = tinycss2.parse_declaration_list(
                rule.content,
                skip_whitespace=True,
                skip_comments=True,
            )
            props = [
                (d.name.lower(), tinycss2.serialize(d.value).strip(), d.important)
                for d in decls
                if d.type == "declaration" and not d.name.startswith("--")
            ]

            for selector in compiled:
                matcher.add_selector(selector, props)

        return matcher

    def _compute_styles(self, root, matcher: Matcher) -> Dict[object, Dict[str, Tuple[str, bool, int]]]:
        styles: Dict[object, Dict[str, Tuple[str, bool, int]]] = {}
        order_counter = 0
        for element in root.iter():
            if not isinstance(element.tag, str):
                continue
            wrapper = ElementWrapper.from_xml_root(element)
            props_for_element: Dict[str, Tuple[str, bool, int]] = {}
            for match in matcher.match(wrapper):
                declarations = match[3]
                for declaration in declarations:
                    name = declaration[0]
                    value = declaration[1]
                    important = declaration[2]
                    order_counter += 1
                    props_for_element[name.lower()] = (value, important, order_counter)

            inline = element.get("style")
            if inline:
                decls = tinycss2.parse_declaration_list(
                    inline,
                    skip_whitespace=True,
                    skip_comments=True,
                )
                for decl in decls:
                    if decl.type != "declaration":
                        continue
                    order_counter += 1
                    props_for_element[decl.name.lower()] = (
                        tinycss2.serialize(decl.value).strip(),
                        bool(decl.important),
                        order_counter,
                    )

            if props_for_element:
                styles[element] = props_for_element

        return styles

    # ------------------------------------------------------------------ #
    # Animation conversion                                               #
    # ------------------------------------------------------------------ #

    def _element_animations(
        self,
        element,
        props: Dict[str, Tuple[str, bool, int]],
        keyframes: Dict[str, List[KeyframeStep]],
        style_context: StyleContext | None,
    ) -> Iterable[AnimationDefinition]:
        def get(name: str, default: str = "") -> str:
            triplet = props.get(name)
            return (triplet[0] if triplet else default).strip()

        names = self._split_list(get("animation-name"))
        durations = self._split_list(get("animation-duration"))
        delays = self._split_list(get("animation-delay"))
        timings = self._split_list(get("animation-timing-function"))
        iterations = self._split_list(get("animation-iteration-count"))
        directions = self._split_list(get("animation-direction"))
        fills = self._split_list(get("animation-fill-mode"))

        if not any((names, durations, delays, timings, iterations, directions, fills)):
            shorthand = get("animation")
            if shorthand:
                parts = shorthand.split()
                if parts:
                    names = [parts[0]]
                if len(parts) > 1:
                    durations = [parts[1]]
                if len(parts) > 2:
                    delays = [parts[2]]
                if len(parts) > 3:
                    timings = [parts[3]]

        if not names:
            return []

        animations: list[AnimationDefinition] = []
        element_id = element.get("id") or self._infer_element_id(element)

        for index, name in enumerate(names):
            key = name.strip()
            if key == "none" or key not in keyframes:
                continue

            duration_ms = self._parse_time_ms(self._value_for_index(durations, index, "0ms"))
            delay_ms = self._parse_time_ms(self._value_for_index(delays, index, "0ms"))
            timing = self._value_for_index(timings, index, "linear")
            iteration_count = self._value_for_index(iterations, index, "1")
            direction = self._value_for_index(directions, index, "normal")
            fill_mode = self._value_for_index(fills, index, "none")

            definitions = self._build_animation_definitions(
                element_id,
                keyframes[key],
                duration_ms,
                delay_ms,
                timing,
                iteration_count,
                direction,
                fill_mode,
                style_context,
            )
            animations.extend(definitions)

        return animations

    def _build_animation_definitions(
        self,
        element_id: str,
        frames: List[KeyframeStep],
        duration_ms: float,
        delay_ms: float,
        timing_function: str,
        iteration_count: str,
        direction: str,
        fill_mode: str,
        style_context: StyleContext | None,
    ) -> List[AnimationDefinition]:
        if duration_ms <= 0.0:
            return []

        # Determine which properties are animated
        animated_props = set()
        for step in frames:
            animated_props.update(step.properties.keys())

        # For now we support opacity + transform
        relevant = [prop for prop in animated_props if prop in ANIMATED_PROPERTIES]
        if not relevant:
            return []

        # Build timing data
        timing = AnimationTiming(
            begin=delay_ms / 1000.0,
            duration=duration_ms / 1000.0,
            repeat_count=iteration_count if iteration_count else "1",
            fill_mode="freeze" if fill_mode.lower() in ("forwards", "both") else "remove",
        )

        key_times = [min(1.0, max(0.0, step.offset))
                     for step in frames]

        key_values = []
        for step in frames:
            values = {}
            if "opacity" in step.properties:
                try:
                    values["opacity"] = float(step.properties["opacity"])
                except ValueError:
                    values["opacity"] = None
            if "transform" in step.properties:
                values["transform"] = step.properties["transform"]
            key_values.append(values)

        # For simplicity, if multiple properties animate, create separate definitions
        definitions: list[AnimationDefinition] = []

        if "opacity" in relevant:
            values = [kv.get("opacity") for kv in key_values]
            if any(v is not None for v in values):
                sanitized = self._fill_numeric(values, default=1.0)
                definitions.append(
                    AnimationDefinition(
                        element_id=element_id,
                        animation_type=AnimationType.ANIMATE,
                        target_attribute="opacity",
                        values=[str(v) for v in sanitized],
                        timing=timing,
                        key_times=key_times,
                        key_splines=self._build_key_splines(frames, timing_function),
                        calc_mode=CalcMode.SPLINE,
                    )
                )

        if "transform" in relevant:
            definitions.extend(
                self._build_transform_definitions(
                    element_id,
                    frames,
                    key_values,
                    key_times,
                    timing,
                    timing_function,
                    style_context,
                ),
            )

        return definitions

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _split_list(raw: str) -> List[str]:
        if not raw:
            return []
        parts = []
        depth = 0
        current = ""
        for ch in raw:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            if ch == "," and depth == 0:
                if current.strip():
                    parts.append(current.strip())
                current = ""
            else:
                current += ch
        if current.strip():
            parts.append(current.strip())
        return parts

    @staticmethod
    def _parse_time_ms(value: str) -> float:
        if value.endswith("ms"):
            return float(value[:-2])
        if value.endswith("s"):
            return float(value[:-1]) * 1000.0
        try:
            return float(value)
        except ValueError:
            return 0.0

    @staticmethod
    def _value_for_index(values: List[str], index: int, default: str) -> str:
        if not values:
            return default
        return values[index % len(values)]

    @staticmethod
    def _build_key_splines(frames: List[KeyframeStep], default_timing: str) -> Optional[List[List[float]]]:
        splines = []
        for i in range(len(frames) - 1):
            easing = frames[i + 1].easing or default_timing
            spline = CSSAnimationExtractor._easing_to_bezier(easing)
            if spline is None:
                return None
            splines.append(list(spline))
        return splines or None

    @staticmethod
    def _easing_to_bezier(easing: str) -> Optional[Tuple[float, float, float, float]]:
        easing = (easing or "linear").strip().lower()
        table = {
            "linear": (0.0, 0.0, 1.0, 1.0),
            "ease": (0.25, 0.1, 0.25, 1.0),
            "ease-in": (0.42, 0.0, 1.0, 1.0),
            "ease-out": (0.0, 0.0, 0.58, 1.0),
            "ease-in-out": (0.42, 0.0, 0.58, 1.0),
        }
        if easing in table:
            return table[easing]
        match = re.match(r"cubic-bezier\(\s*([0-9.+-]+)\s*,\s*([0-9.+-]+)\s*,\s*([0-9.+-]+)\s*,\s*([0-9.+-]+)\s*\)", easing)
        if match:
            return tuple(map(float, match.groups()))  # type: ignore
        return None

    @staticmethod
    def _fill_numeric(values: List[Optional[float]], default: float) -> List[float]:
        result = []
        last = default
        for value in values:
            if value is None or math.isnan(value):
                result.append(last)
            else:
                last = value
                result.append(last)
        return result

    def _build_transform_definitions(
        self,
        element_id: str,
        frames: List[KeyframeStep],
        key_values: List[Dict[str, Optional[float]]],
        key_times: List[float],
        timing: AnimationTiming,
        timing_function: str,
        style_context: StyleContext | None,
    ) -> List[AnimationDefinition]:
        # For MVP handle translate/rotate/scale by decomposing the transform string
        rx = []
        ry = []
        tx = []
        ty = []
        rot = []

        for frame in frames:
            transform = frame.properties.get("transform", "")
            tf = self._parse_transform(transform)
            tx.append(tf[0])
            ty.append(tf[1])
            rot.append(tf[2])
            rx.append(tf[3])
            ry.append(tf[4])

        splines = self._build_key_splines(frames, timing_function)
        definitions = []

        if any(value != tx[0] for value in tx) or any(value != ty[0] for value in ty):
            values = [f"{x:.6g} {y:.6g}" for x, y in zip(tx, ty)]
            definitions.append(
                AnimationDefinition(
                    element_id=element_id,
                    animation_type=AnimationType.ANIMATE_TRANSFORM,
                    target_attribute="transform",
                    values=values,
                    timing=timing,
                    key_times=key_times,
                    key_splines=splines,
                    calc_mode=CalcMode.SPLINE,
                    transform_type=TransformType.TRANSLATE,
                ),
            )

        if any(value != rot[0] for value in rot):
            values = [f"{value:.6g}" for value in rot]
            definitions.append(
                AnimationDefinition(
                    element_id=element_id,
                    animation_type=AnimationType.ANIMATE_TRANSFORM,
                    target_attribute="transform",
                    values=values,
                    timing=timing,
                    key_times=key_times,
                    key_splines=splines,
                    calc_mode=CalcMode.SPLINE,
                    transform_type=TransformType.ROTATE,
                ),
            )

        if any(value != rx[0] for value in rx) or any(value != ry[0] for value in ry):
            values = [f"{sx:.6g} {sy:.6g}" for sx, sy in zip(rx, ry)]
            definitions.append(
                AnimationDefinition(
                    element_id=element_id,
                    animation_type=AnimationType.ANIMATE_TRANSFORM,
                    target_attribute="transform",
                    values=values,
                    timing=timing,
                    key_times=key_times,
                    key_splines=splines,
                    calc_mode=CalcMode.SPLINE,
                    transform_type=TransformType.SCALE,
                ),
            )

        return definitions

    @staticmethod
    def _parse_transform(value: str) -> Tuple[float, float, float, float, float]:
        tx = ty = rot = 0.0
        sx = sy = 1.0
        for fn, args in re.findall(r"([a-zA-Z]+)\(([^)]*)\)", value or ""):
            fn = fn.lower()
            parts = [p.strip() for p in CSSAnimationExtractor._split_list(args)]
            if fn == "translate" and parts:
                tx = CSSAnimationExtractor._safe_float(parts[0], 0.0)
                ty = CSSAnimationExtractor._safe_float(parts[1], 0.0) if len(parts) > 1 else 0.0
            elif fn == "rotate" and parts:
                rot = CSSAnimationExtractor._safe_float(parts[0], 0.0)
            elif fn == "scale" and parts:
                sx = CSSAnimationExtractor._safe_float(parts[0], 1.0)
                sy = CSSAnimationExtractor._safe_float(parts[1], sx) if len(parts) > 1 else sx
        return tx, ty, rot, sx, sy

    @staticmethod
    def _safe_float(value: str, default: float) -> float:
        try:
            match = re.match(r"[-+]?\d+(?:\.\d+)?", value)
            if match:
                return float(match.group(0))
        except Exception:
            pass
        return default

    @staticmethod
    def _infer_element_id(element) -> str:
        # Fallback to generate an ID when one is not present
        return f"auto_{id(element)}"

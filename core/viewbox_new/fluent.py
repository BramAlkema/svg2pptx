"""Fluent builder interfaces for viewbox computations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, TYPE_CHECKING

import numpy as np
from lxml import etree as ET

from .config import AspectAlign, MeetOrSlice, ViewBoxConfig
from .parsing import normalize_inputs, parse_viewbox_token, parse_preserve_aspect_ratio

if TYPE_CHECKING:  # pragma: no cover
    from .core import ViewBoxEngine


@dataclass
class ViewBoxPlan:
    """Structured output produced by the fluent builder."""

    viewboxes: np.ndarray
    alignments: np.ndarray
    meet_or_slice: np.ndarray


@dataclass
class ViewBoxBuilder:
    """Chainable interface used by :class:`~core.viewbox_new.core.ViewBoxEngine`."""

    engine: "ViewBoxEngine | None" = None
    _viewboxes: List[str] = field(default_factory=list)
    _par_values: List[str] = field(default_factory=list)

    def viewbox(self, value: str) -> "ViewBoxBuilder":
        """Add a raw viewBox string to the builder."""
        self._viewboxes.append(value)
        return self

    def viewboxes(self, values: Iterable[str]) -> "ViewBoxBuilder":
        """Add multiple viewBox strings."""
        self._viewboxes.extend(values)
        return self

    def preserve_aspect_ratio(self, value: str) -> "ViewBoxBuilder":
        """Add a preserveAspectRatio value corresponding to the most recent viewBox."""
        self._par_values.append(value)
        return self

    def preserve_aspect_ratios(self, values: Iterable[str]) -> "ViewBoxBuilder":
        """Add multiple preserveAspectRatio values."""
        self._par_values.extend(values)
        return self

    def build(self) -> ViewBoxPlan:
        """Finalize and return structured arrays of parsed viewBox metadata."""
        vb_array, alignments, meet_slices = normalize_inputs(
            self._viewboxes, self._par_values if self._par_values else None
        )
        return ViewBoxPlan(
            viewboxes=vb_array,
            alignments=alignments,
            meet_or_slice=meet_slices,
        )

    def to_config(self, index: int = 0) -> ViewBoxConfig:
        """Return the parsed configuration for a single entry."""
        if not self._viewboxes:
            raise ValueError("No viewBox values have been registered with the builder.")

        viewbox_cfg = parse_viewbox_token(self._viewboxes[index])
        par_value = self._par_values[index] if index < len(self._par_values) else ""
        align, meet = parse_preserve_aspect_ratio(par_value)
        return ViewBoxConfig(
            min_x=viewbox_cfg.min_x,
            min_y=viewbox_cfg.min_y,
            width=viewbox_cfg.width,
            height=viewbox_cfg.height,
            align=align,
            meet_or_slice=meet,
        )

    def commit(self) -> "ViewBoxEngine":
        """Attach parsed inputs to the associated engine and return it."""
        if self.engine is None:
            raise ValueError("ViewBoxBuilder has no associated engine; call via ViewBoxEngine.builder().")

        self.engine.viewbox_strings = list(self._viewboxes)
        self.engine.par_strings = list(self._par_values)
        return self.engine


@dataclass
class ViewportBuilder:
    """Fluent interface for configuring `ViewportEngine` instances."""

    engine: "ViewBoxEngine"

    def for_svg(self, svg_element: ET.Element) -> "ViewportBuilder":
        self.engine._svg_elements = [svg_element]
        return self

    def for_svgs(self, svg_elements: Iterable[ET.Element]) -> "ViewportBuilder":
        self.engine._svg_elements = list(svg_elements)
        return self

    def with_slide_size(self, width: int, height: int) -> "ViewportBuilder":
        self.engine._target_sizes = [(width, height)]
        return self

    def with_slide_sizes(self, sizes: Iterable[tuple[int, int]]) -> "ViewportBuilder":
        self.engine._target_sizes = list(sizes)
        return self

    def center(self) -> "ViewportBuilder":
        self.engine._alignment = AspectAlign.X_MID_Y_MID
        return self

    def top_left(self) -> "ViewportBuilder":
        self.engine._alignment = AspectAlign.X_MIN_Y_MIN
        return self

    def top_right(self) -> "ViewportBuilder":
        self.engine._alignment = AspectAlign.X_MAX_Y_MIN
        return self

    def bottom_left(self) -> "ViewportBuilder":
        self.engine._alignment = AspectAlign.X_MIN_Y_MAX
        return self

    def bottom_right(self) -> "ViewportBuilder":
        self.engine._alignment = AspectAlign.X_MAX_Y_MAX
        return self

    def meet(self) -> "ViewportBuilder":
        self.engine._meet_or_slice = MeetOrSlice.MEET
        return self

    def slice(self) -> "ViewportBuilder":
        self.engine._meet_or_slice = MeetOrSlice.SLICE
        return self

    def with_context(self, context) -> "ViewportBuilder":
        self.engine._contexts = [context]
        return self

    def with_contexts(self, contexts: Iterable) -> "ViewportBuilder":
        self.engine._contexts = list(contexts)
        return self

    def resolve(self):
        return self.engine.resolve()

    def resolve_single(self):
        return self.engine.resolve_single()


__all__ = ["ViewBoxBuilder", "ViewBoxPlan", "ViewportBuilder"]

"""Coordinator façade for the modern viewbox pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, TYPE_CHECKING

from .batch_ops import resolve_svg_viewports
from .config import AspectAlign, MeetOrSlice, ViewBoxConfig
from .fluent import ViewBoxBuilder, ViewBoxPlan, ViewportBuilder
from .parsing import normalize_inputs

if TYPE_CHECKING:  # pragma: no cover
    from core.viewbox.core import ViewportEngine


@dataclass
class ViewBoxEngine:
    """Coordinator that bridges parsing helpers with legacy viewport resolution."""

    backend: "ViewportEngine | None" = None
    viewbox_strings: list[str] | None = None
    par_strings: list[str] | None = None

    def builder(self) -> ViewportBuilder:
        """Return a fluent builder for configuring the engine."""
        return ViewportBuilder(engine=self)

    def viewbox_builder(self) -> ViewBoxBuilder:
        """Return a builder specialised for viewBox parsing flows."""
        return ViewBoxBuilder(engine=self)

    def ensure_backend(self) -> "ViewportEngine":
        if self.backend is None:
            from core.viewbox.core import ViewportEngine as LegacyViewportEngine

            self.backend = LegacyViewportEngine()
        return self.backend

    def from_builder(self, builder: ViewBoxBuilder) -> ViewBoxPlan:
        """Parse values captured by the supplied builder."""
        plan = builder.build()
        self.viewbox_strings = list(builder._viewboxes)  # type: ignore[attr-defined]
        self.par_strings = list(builder._par_values)  # type: ignore[attr-defined]
        return plan

    def resolve(
        self,
        viewbox_strings: Iterable[str] | None = None,
        par_strings: Iterable[str] | None = None,
    ) -> ViewBoxPlan:
        """Parse the supplied inputs (or the engine's stored state) to structured arrays."""
        vb_iterable: Iterable[str] = (
            viewbox_strings if viewbox_strings is not None else self.viewbox_strings or []
        )
        par_iterable = par_strings if par_strings is not None else self.par_strings
        vb_array, alignments, meet_slices = normalize_inputs(vb_iterable, par_iterable)
        return ViewBoxPlan(
            viewboxes=vb_array,
            alignments=alignments,
            meet_or_slice=meet_slices,
        )

    def to_configs(self, plan: ViewBoxPlan) -> Sequence[ViewBoxConfig]:
        """Convert a :class:`ViewBoxPlan` to an iterable of :class:`ViewBoxConfig` instances."""
        configs: list[ViewBoxConfig] = []
        for row, align, meet in zip(plan.viewboxes, plan.alignments, plan.meet_or_slice, strict=False):
            configs.append(
                ViewBoxConfig(
                    min_x=row["min_x"],
                    min_y=row["min_y"],
                    width=row["width"],
                    height=row["height"],
                    align=AspectAlign(int(align)),
                    meet_or_slice=MeetOrSlice(int(meet)),
                )
            )
        return configs

    def resolve_viewports(
        self,
        svg_elements,
        target_sizes: list[tuple[int, int]] | None = None,
        contexts=None,
        *,
        backend: "ViewportEngine | None" = None,
    ):
        """Resolve viewport mappings using the shared batch operations."""
        if backend is not None:
            self.backend = backend
        engine = self.ensure_backend()
        return resolve_svg_viewports(engine, list(svg_elements), target_sizes, contexts)


def resolve_viewports(
    svg_elements,
    target_sizes: list[tuple[int, int]] | None = None,
    contexts=None,
    *,
    engine: "ViewportEngine | None" = None,
):
    """Convenience wrapper for resolving viewport mappings via the new coordinator."""
    coordinator = ViewBoxEngine(backend=engine)
    return coordinator.resolve_viewports(svg_elements, target_sizes, contexts)


__all__ = ["ViewBoxEngine", "ViewBoxPlan", "resolve_viewports"]

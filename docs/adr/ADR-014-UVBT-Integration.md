# ADR-014: Unit/ViewBox/Transform (UVBT) Integration Findings

**Status:** Draft  
**Date:** 2025-10-XX  
**Owner:** UVBT Working Group

## Context

Phase 2 introduced a consolidated Unit → ViewBox → Transform pipeline (UVBT) intended to provide a single source of truth for converting SVG coordinates into PowerPoint EMUs. As of the EMU/Color refactor (Q4 2025) this consolidation is now in place: `ConversionServices.emu()` / `emu_rect()` are the canonical helpers and mappers call them instead of multiplying by `12700`.

Recent cleanup surfaced the remaining limitations to track:

- Active code paths now route through `ConversionServices`; any `* 12700` or `* 9525` multipliers that remain are confined to legacy or archived modules tracked in `reports/uvbt_emu_callsites.csv`.
- Fractional EMU support ships enabled-by-default; set `SVG2PPTX_EMU_PRECISION=round` (or `off`) to opt back into legacy integer rounding when debugging regressions.
- Tracer metadata can now carry `EmuValue` / fractional precision; the next iteration should expose this information in diagnostics dashboards.

## Findings

1. **Central conversion entry point is live.** All Clean Slate mappers and adapters route through `ConversionServices.emu(...)`. Remaining `* 12700` occurrences are confined to legacy fallbacks and are tracked in `reports/uvbt_emu_callsites.csv`.

2. **Transforms/ViewBox alignment is largely complete.** Parsers expose enriched `ClipRef`/geometry and mappers consume them. Legacy preprocessors still need a follow-up pass to strip redundant conversions.

3. **Fractional EMU support is default.** The helpers emit fractional metadata via `EmuValue.used_fractional`; rounding strategy can be forced to legacy mode via `SVG2PPTX_EMU_PRECISION=round|off`.

4. **Testing/tracing surface precision metadata.** `clip_result_to_xml` and mapper metadata carry the structured result (`EmuValue`, strategy, warnings). Dashboards should pull the new fields once we wire the tracer export.

## Decision

Adopt the centralized helpers everywhere, keep fractional mode enabled-by-default (with opt-out env toggles), and retire lingering fallback conversions.

## Consequences

- ClipPath enhancements (CustGeom/EMF fallbacks, transform handling) continue using enriched `ClipRef` data while relying on the standardized ConversionServices pipeline.
- A follow-up initiative will:
  - Harden the ConversionServices API surface (document axis hints, rounding guarantees).
  - Route any remaining legacy preprocessors through services (no manual multipliers).
  - Extend tracer dashboards to visualize fractional usage and rounding strategy.
- Tests and tracer instrumentation should continue to log fractional flags so regressions surface quickly.

## Next Steps

1. Retire / migrate the final fallback conversions highlighted in `reports/uvbt_emu_callsites.csv`.
2. Align legacy preprocessors so they pass contexts instead of re-applying multipliers.
3. Finalise documentation to reflect the new EMU service API (see `docs/fractional-emu-architecture.md`).
4. Wire tracer dashboards and CI alerts to monitor `EmuValue.used_fractional` and rounding strategy drift (propagate `EmuValue` metadata through mapper `_emu_value` helpers, `DrawingMLEmbedder`, and tracer exporters before instrumenting dashboards).

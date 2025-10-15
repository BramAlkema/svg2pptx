# ADR-011: Animation Fidelity Improvements

## Status
Accepted (2025-10-03)

## Context
The clean-slate animation pipeline successfully parses SMIL markup and emits a `<p:timing>` block during conversion, but real PowerPoint playback currently falls short:

- Mapper stages rewrite every `cNvPr@id`, yet the animation generator keeps targeting the original SVG ids (`spid="{element_id}"`). None of the emitted animations bind to an actual slide shape, so PowerPoint silently skips them.
- The `TimelineGenerator` records per-frame property values, but the `PowerPointAnimationGenerator` collapses everything to simple from/to tweens. Discrete steps, custom easing, and multi-keyframe values are dropped, eroding fidelity.
- Tests only assert that some timing XML exists—they never confirm that targets resolve or that keyframes survive the pipeline. This makes regressions easy to ship.

We need to line up the animation stack so the generated PPTX matches the authoring intent and renders inside Office without manual repair.

## Decision
- Persist a mapping from each IR element (via its `source_id`) to the `spid` that the embedder assigns when producing slide XML. Surface that map in `EmbedderResult` so downstream stages can reason about it.
- Delay PPTX animation generation until after embedding. The converter should carry the parsed `AnimationDefinition` objects and `AnimationScene` timeline forward, then ask the animation generator to render XML once the `spid` mapping is known.
- Rework the animation generator to:
  - Resolve every target through the `source_id → spid` map before writing `<a:spTgt>`.
  - Expand property animations into `a:anim` keyframes driven by the timeline, preserving multi-step values and respecting animation delays/durations.
  - Clone animations for every mapped `spid` when an SVG element produces multiple slide shapes.
- Strengthen unit and integration coverage so tests unzip the generated PPTX, confirm that each `<a:spTgt>` references a real `cNvPr@id`, and verify that timeline-driven keyframes make it into the slide XML.

## Implementation Plan
1. **Embedder Mapping**
   - Extend `EmbedderResult` to expose a `shape_id_map` that records `source_id` (string) to one or more assigned `spid` values.
   - Update `_assign_shape_id` to return the generated id and accumulate the mapping while composing slide XML.
   - Add debugging hooks so the converter’s `debug_data` block reports how many shapes were mapped for animations.

2. **Converter & Generator Integration**
   - Teach `AnimationConversionResult` to keep the raw `animations` list and `timeline_scenes`.
   - Modify the pipeline so it calls a new `AnimationConverter.build_powerpoint_xml(...)` helper after embedding, supplying the `shape_id_map` to render the final `<p:timing>` block.
   - Refactor `PowerPointAnimationGenerator` to resolve `spid` targets via the mapping, duplicate animations when necessary, and emit keyframe-based `a:anim` sequences that honor actual delays/durations from the timeline.

3. **Validation & Tests**
   - Update unit tests to use the new generator API and assert both keyframe emission and correct `spid` binding.
   - Expand the pipeline integration test to unzip the produced PPTX, locate `<a:spTgt>` identifiers, and ensure each maps to a `cNvPr@id` present in the slide XML.
   - Document the mapping in `debug_data` so future diagnostics can confirm animation/shape alignment.

## Consequences
- Animations now operate on the shapes that the embedder materializes, so timing XML survives round-tripping through PowerPoint.
- Timeline fidelity increases because discrete steps and multi-keyframe values are preserved instead of collapsing to simplistic from/to fades.
- The additional generator logic and validation make the code more sophisticated, but the stronger tests mitigate regression risk.
- Future animation features (motion paths, trigger conditions) can piggyback on the established mapping contract rather than re-inventing shape resolution.

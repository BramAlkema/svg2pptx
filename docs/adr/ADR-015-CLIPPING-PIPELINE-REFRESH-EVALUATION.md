# ADR-015: Clipping Pipeline Refresh Evaluation

- **Status:** Proposed  
- **Date:** 2024-04-07  
- **Authors:** Codex CLI  
- **Related Work:** Outstanding ClipPath Tasks (CustGeom & EMF fallback initiative)

## Context

Product direction calls for a refreshed clipping pipeline that:

1. Introduces a richer IR (`ClipCustGeom`, `ClipMediaMeta`, etc.) and policy knobs (`ClipPolicy`) to steer between custGeom and EMF fallbacks.
2. Refactors adapters/services to emit structured `ClippingResult` data instead of raw XML.
3. Centralises DrawingML emission through reusable geometry helpers.
4. Guarantees EMF fallbacks integrate cleanly with slide‐level relationship management.
5. Simplifies mapper control flow (`PathMapper`, `GroupMapper`) around the new result model.
6. Lands coverage in unit/E2E suites.

We reviewed the current codebase to gauge the delta required to adopt the proposed design.

## Findings

1. **Existing ClippingResult Contract**
   - `core/map/clipping_adapter.py` already exports a `ClippingResult` dataclass consumed by `PathMapper._generate_clip_xml` and `ImageMapper._generate_image_clip_xml`.
   - Replacing it with the proposed `core/clip/model.ClippingResult` would break mapper integrations and tests (`tests/unit/core/map/test_clipping_adapter_segments.py`). A translation layer or staged migration is needed.

2. **Policy Engine Limitations**
   - Policy decisions flow through `core/policy/engine.create_policy()` and `Policy.decide_path`.
   - There is no standalone `Policy` dataclass; adding `ClipPolicy` requires plumbing through the policy engine, `PipelineFactory.create_policy_engine`, and multiple fixtures that instantiate policies directly (unit tests, mocks). Without these updates the application would fail to construct policies.

3. **Adapter Duplication Risk**
   - `ClippingPathAdapter` already coordinates `ClippingAnalyzer`, `MaskingConverter`, and EMF fallbacks. Introducing `core/clip/adapter.ClippingPathAdapter` without refactoring the existing adapter would duplicate logic and diverge behaviour. The proposed API expects normalised clip geometry and effect stacks that the current pipeline does not expose.

4. **EMF Integration Concerns**
   - EMF fallbacks currently run through `core/map/emf_adapter.py` and are consumed by `PathMapper._map_to_emf`.
   - The embedder (`core/io/embedder.py`) derives relationships/media files from `MapperResult.media_files`. Returning EMF data via `ClipMediaMeta` alone will not be packaged unless mappers convert the metadata back into the existing manifest structure.

5. **DrawingML Emission Overlap**
   - `core/converters/custgeom_generator.generate_custgeom_xml` already emits custGeom XML, including quadratic→cubic conversion and fill-rule handling.
   - A new `CustGeomEmitter` duplicates this capability; keeping both in sync would be error-prone. Reuse or refactor of the existing generator is preferable.

6. **Mapper & Embedder Expectations**
   - `MapperResult.output_format` drives embedder statistics and packaging. Swapping `<p:sp>` for `<p:pic>` requires updating metadata, `output_format`, and media lists so downstream consumers treat EMF fallbacks correctly.
   - Tests and fixtures (e.g. `tests/unit/core/map/conftest.py`) assume the current structures; changing contracts necessitates broad updates to maintain coverage.

## Decision

Document the incompatibilities and required migration steps before implementing the new design. Any adoption effort must include:

1. A compatibility layer or phased rollout from the existing `ClippingResult` to the richer IR.
2. Policy engine enhancements with matching fixture updates.
3. Refactoring the existing `ClippingPathAdapter` rather than introducing a parallel implementation.
4. Extending EMF packaging so the media registry and embedder continue to function.
5. Consolidating custGeom emission logic to avoid duplication.
6. Coordinated test updates spanning unit, integration, and E2E suites.

## Consequences

- Immediate implementation of the proposed clipping refresh without these preparatory changes would break mapper integrations, media packaging, and multiple test suites.
- Capturing these blockers in an ADR provides a roadmap for a staged migration instead of a big-bang refactor.

## Next Steps

1. Design a migration path for the ClippingResult API (adapter façade + mapper updates).
2. Extend `Policy` creation and fixtures to surface `ClipPolicy`.
3. Refactor `ClippingPathAdapter` to emit the richer IR while preserving existing XML helpers until consumers switch over.
4. Update EMF adapters/embedder to accept `ClipMediaMeta` while maintaining current `MapperResult` expectations.
5. Decide whether to wrap or replace `custgeom_generator` when emitting custGeom XML.
6. Plan test updates (unit + golden PPTX) aligned with the new architecture.

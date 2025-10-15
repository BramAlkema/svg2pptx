# Clipping Pipeline Compatibility Plan

**Status:** Draft  
**Updated:** 2024-04-07  
**Owners:** Platform Mapping Team  
**Related ADRs:** [ADR-015](../adr/ADR-015-CLIPPING-PIPELINE-REFRESH-EVALUATION.md)

## 1. Purpose

We need a staged migration path from the current clipping adapter (which returns XML strings) to the proposed structured clipping IR (`ClipCustGeom`, `ClipMediaMeta`, etc.) without breaking existing mappers, embedder logic, or tests. This document captures the compatibility design and the required policy-engine extensions.

## 2. Goals

- Provide a facade that lets the new clipping engine coexist with the current XML-based adapter.
- Preserve existing mapper interfaces (`PathMapper._generate_clip_xml`, `ImageMapper._generate_image_clip_xml`) until they are explicitly migrated.
- Introduce `ClipPolicy` controls without forcing every caller to supply them immediately.
- Allow opt-in experimentation via feature toggles.
- Keep the change surface focused so we can incrementally port mappers/tests.

## 3. Current System Snapshot

- `core/map/clipping_adapter.ClippingPathAdapter.generate_clip_xml` returns a `ClippingResult` containing literal XML + metadata.
- `PathMapper`/`ImageMapper` embed that XML directly (and inspect `strategy`/`complexity` strings).
- `Policy.decide_clippath` exposes coarse thresholds through `PolicyConfig.thresholds`.
- `Embedder` expects EMF fallbacks to show up as `MapperResult.media_files`.

## 4. Migration Architecture

### 4.1 Layered Adapter Stack

```
├── core/clip/model.py          # new structured result types (custGeom, media, etc.)
├── core/clip/service.py        # produces ClipResult (new API)
├── core/clip/translator.py     # maps ClipResult → LegacyClipResult (XML string)
└── core/map/clipping_adapter.py # continues to expose generate_clip_xml()
```

**Key idea:** `ClippingPathAdapter` internally delegates to the new service when the feature flag is enabled, gets back a structured `ClipResult`, then converts it to the legacy `ClippingResult` (XML string). Consumers remain untouched until we migrate them.

### 4.2 Compatibility Facade

- **New type:** `core/clip/translator.LegacyClipBridge`
  - Inputs: `ClipResult`, `CustGeomEmitter`, `EmfPackagingAdapter`.
  - Outputs:
    - Legacy XML string (either `<a:clipPath>` snippet or `<p:pic>`).
    - Metadata map that mirrors current expectations (`strategy`, `complexity`, `media_files` hints).
- **Fallback behaviour:** If the new service returns `None` or raises, fall back to the current logic (`_generate_native_clip_xml`, `_generate_emf_clipping`).
- **Feature flag:** `ClipPolicy.enable_structured_adapter` or env `SVG2PPTX_CLIP_ADAPTER_V2`. Default `False`.

### 4.3 Mapper Strategy

1. **Phase 0 (default):** Bridge disabled → zero behaviour change.
2. **Phase 1:** Enable the bridge in CI (unit tests). New service generates data; bridge emits existing XML and metadata. Observe parity.
3. **Phase 2:** Update mappers (`PathMapper`) to consume `ClipResult` directly, but retain the bridge for other call sites (e.g., `ImageMapper`).
4. **Phase 3:** Remove bridge once all consumers migrated.

### 4.4 EMF Packaging

- `ClipResult.media` will be translated into the legacy `MapperResult.media_files` payload inside the bridge.
- For the interim, `EmfPackagingAdapter` will:
  - Assign temporary relationship placeholders (`bridge.generate_relationship_id()`).
  - Populate `metadata['media_files']` exactly as today so the embedder/package writer keeps working.
- Once mappers consume `ClipResult.media` directly, we can route through the planned `MediaRegistry`.

## 5. Policy Engine Extensions

### 5.1 ClipPolicy Data Class

Introduce:

```python
@dataclass
class ClipPolicy:
    allow_custgeom: bool = True
    force_emf_if_filters: bool = True
    force_emf_if_mask: bool = True
    force_emf_if_text_clip: bool = True
    max_segments_for_custgeom: int = 800
    bbox_placeholder_if_complex: bool = True
    enable_structured_adapter: bool = False  # feature flag
```

### 5.2 PolicyConfig Integration

- Add `clip_policy: ClipPolicy | None = None` to `PolicyConfig`.
- In `PolicyConfig.__post_init__`, instantiate `ClipPolicy()` when absent, deriving defaults from `thresholds` to keep behaviour aligned:
  - e.g. `clip_policy.max_segments_for_custgeom = thresholds.max_clip_path_segments`.
- Add serialization helpers (`to_dict`, `from_dict`) to include clip policy settings.

### 5.3 Policy Engine Exposure

- `Policy` gains `self.clip_policy = config.clip_policy`.
- Provide helper `Policy.get_clip_policy()` returning the dataclass.
- Update `decide_clippath` to annotate decisions with policy context (for tracing), but keep return type unchanged.
- `PipelineFactory.create_policy_engine` threads the config (no extra arguments needed because `ConversionServices.create_default()` already builds `PolicyConfig`).

### 5.4 Fixtures & Tests

- Update tests that instantiate `PolicyConfig()` or `Policy()` directly (`tests/unit/core/policy`, `tests/unit/core/map/conftest.py`) to account for the new field. Default values ensure no param changes are strictly necessary, but fixtures will assert `clip_policy` exists.

## 6. Implementation Steps

1. **Bootstrap Types**
   - Add `ClipPolicy` to `core/policy/config.py`.
   - Add accessor on `Policy`.
2. **Bridge Layer**
   - Implement `core/clip/translator.LegacyClipBridge`.
   - Refactor `core/map/clipping_adapter.ClippingPathAdapter` to optionally delegate.
3. **Feature Flag Wiring**
   - Accept `enable_structured_adapter` via `ClipPolicy`.
   - Add environment-based override for manual testing.
4. **Validation**
   - Write unit tests for the bridge to ensure parity with existing XML.
   - Add regression test verifying fallback behaviour when the new service raises.
5. **Roadmap**
   - Phase-1 toggle in CI.
   - Schedule mapper refactor once parity confirmed.

## 7. Open Questions

- **Effect Stack Source:** The proposed service requires `effect_stack` metadata. We need to define where `ClippingPathAdapter` obtains this today (likely from `element_context`). Further exploration required before Phase 2.
- **custGeom Reuse:** Decide whether the bridge leverages `core/converters/custgeom_generator` or a slim emitter. Reuse minimizes divergence; this design assumes reuse.
- **MediaRegistry Timing:** Aligning with the long-term media registry changes should happen once mappers adopt the new result types.

## 8. Risks

- Dual code paths increase maintenance burden until migration completes.
- Incorrect translation could generate malformed XML; unit tests must cover typical clip scenarios.
- Policy defaults must avoid regressing existing behaviour; integration tests required before flipping the flag.

## 9. Appendix

- **Feature Flag Examples**

  - Python override:
    ```python
    policy.clip_policy.enable_structured_adapter = True
    ```

  - Environment override (read by adapter):
    ```
    export SVG2PPTX_CLIP_ADAPTER_V2=1
    ```

- **Telemetry Hooks**

  - During bridge phase, log decisions when `enable_structured_adapter` is true to compare new vs legacy outputs.

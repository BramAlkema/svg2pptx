# UVBT Precision Follow-up: Centralized EMU Conversion

**Status:** Draft
**Owners:** Clipping & UVBT Working Groups
**Last Updated:** 2025-10-XX

## 1. Problem Statement

Despite the UVBT (Unit → ViewBox → Transform) initiative, most IR→PPT conversions still call `value * 12700` directly. This bypasses the central `ConversionServices` pipeline, blocks fractional-EMU support, and forces each mapper/adapter to re-implement rounding, context lookup, and tracing. ClipPath refactors highlighted the inconsistency and the need to unify conversion logic before dismantling remaining shims.

## 2. Goals & Non-Goals

### Goals
- Provide a single ConversionServices API for converting SVG coordinates to EMUs with UVBT context.
- Retain current integer EMU behavior by default while enabling fractional precision via a feature flag.
- Ensure clipPath, path, image, group, text, EMF adapters, and embedders route through the API.
- Emit tracer metadata that records source units, EMU results, and rounding decisions.
- Update test suites (unit, integration, regression) to validate both legacy and fractional behaviors.

### Non-Goals
- Do not rewrite the UVBT parser. We rely on existing viewBox/transform propagation.
- No legacy archive updates in this phase (legacy code stays untouched).
- Fractional EMU persisted storage or MLS-level features are out-of-scope.

## 3. Proposed Architecture

### 3.1 Conversion API
Introduce helpers in `ConversionServices`:

```python
@dataclass
class EmuValue:
    value: int               # Integer EMU for compatibility
    fractional: float | None # Optional fractional value (EMU precision)
    rounded_from: float      # Original value before rounding
    strategy: str            # "floor", "round", "fractional"
```

```python
class ConversionServices:
    def emu(self, coord: float, axis: Literal['x','y','uniform'], *,
            context: ConversionContext | None = None,
            precision: PrecisionMode = PrecisionMode.INTEGER,
            strategy: Literal['round','floor','fractional']='round') -> EmuValue:
        ...

    def emu_point(self, point: Point, context=None, precision=PrecisionMode.INTEGER) -> tuple[EmuValue, EmuValue]:
        ...

    def emu_rect(self, rect: Rect, context=None, precision=PrecisionMode.INTEGER) -> EmuRect:
        ...
```

Implementation details:
- Delegates to `FractionalEMUConverter` for fractional arithmetic.
- Applies viewBox + transform scaling from provided `ConversionContext`.
- Falls back to default context from the services container when none is given.
- Honors `strategy`: `round` (default, matches current behavior), `floor` (legacy safe guard), `fractional` (return decimals).

### 3.2 Call-Site Migration Strategy
1. **Instrumentation:** Add a lint-style check (e.g., via pre-commit) that warns on new `* 12700` occurrences outside the conversion module.
2. **Phase 1 – Wrapper Adoption:**
   - Introduce the API with identical rounding semantics to current logic.
   - Update key call sites (path mapper, image mapper, clipping adapter `_rect_clip_xml`, embedder viewport conversions) to use `services.conversion.emu()`. Keep the internal rounding to ints for now.
   - Add warnings when the deprecated pattern is used to motivate migrations.
3. **Phase 2 – Full Migration:** Replace remaining occurrences across group mapper, text mapper, EMF adapter, etc.
4. **Phase 3 – Fractional Enablement:** Fractional output ships enabled by default; use the environment flag `SVG2PPTX_EMU_PRECISION=round|off` to temporarily revert to legacy rounding during diagnostics.
5. **Phase 4 – Cleanup:** Remove warnings, enforce lint rule, and delete direct `EMU_PER_UNIT` constants in mappers.

### 3.3 Tracer Integration
- Extend tracer payloads with new fields (e.g., `emu_value`, `fractional`, `rounding_strategy`).
- For clipPath traces, include both the structured result EMUs and the fallback placeholders.
- Ensure analytics dashboards can distinguish between integer and fractional conversions.

## 4. Testing Plan

| Level | Coverage |
|-------|----------|
| Unit  | ConversionServices EMU helpers (px/pt/in/em), fractional rounding, context fallback, rounding strategies |
| Unit  | Mappers exercising new helpers (path bounding boxes, clip rectangles, EMF fallback) |
| Unit  | Tracer metadata serialization with fractional details |
| Integration | `tests/integration/pptx/test_clip_emf_packaging.py` ensuring EMU metadata still produces consistent PPTX |
| Regression | Golden PPTX comparisons for sample SVGs with fractional flag off (no diffs) |
| Feature Toggle | Add targeted test toggling `SVG2PPTX_EMU_PRECISION=fractional` to confirm decimals flow through |

### 4.1 Instrumentation Gaps

- ✅ `core/map/*._emu_value` helpers retain `EmuValue` objects; fractional metadata is preserved in mapper metadata.
- ✅ `DrawingMLEmbedder`, `PackageWriter`, and pipeline debug outputs aggregate the new `emu_trace` payloads for dashboards and tracing exports.
- ✅ `core/performance/filter_emf_cache.EMFFilterCache` and `core/performance/raster_fallback.RasterRenderer` persist EMU/color trace summaries alongside cached fallbacks.

## 5. Rollout Concerns & Mitigations
- **Risk:** Fractional EMUs might shift pixel alignment in PPT. *Mitigation:* fractional is now default; maintain the opt-out flag and continue visual diff monitoring for regressions.
- **Risk:** Missing conversion context at call sites. *Mitigation:* pass existing bounding box/viewBox contexts through element metadata; fallback to default context with warning.
- **Risk:** Coverage failures due to new paths. *Mitigation:* update coverage config; add targeted tests for new code.

## 6. Implementation Checklist
- [ ] Define `EmuValue` and helpers in `ConversionServices`.
- [ ] Update services container to expose conversion helper to mappers.
- [ ] Replace `EMU_PER_UNIT` constants in `clipping_adapter`, `path_mapper`, `image_mapper`, `group_mapper`, `embedder` with helper calls.
- [ ] Add tracer metadata + unit tests.
- [ ] Update documentation (`docs/adr/ADR-014-UVBT-Integration.md`) with new architecture outcomes.
- [ ] Provide migration guide or developer notes with example usage.

## 7. Open Questions
- Do we need axis-specific rounding strategies (e.g., `x` vs `y`)?
- Should fractional EMUs be stored as Decimal to avoid floating-point drift?
- How do we version gate fractional output for downstream consumers (API vs CLI vs SDK)?

---
Assigned To: UVBT Precision Tiger Team

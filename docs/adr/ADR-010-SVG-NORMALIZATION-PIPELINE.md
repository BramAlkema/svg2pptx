# ADR-010: SVG Normalization Pipeline

**Status**: Proposed  
**Date**: 2025-10-11

## Context

Downstream converters expect presentation attributes and deterministic attribute ordering to guarantee reproducible DrawingML output. Incoming SVG assets often contain external `<style>` blocks, mixed inline CSS, and inconsistent attribute orderings that complicate diffing, caching, and policy analysis. We need a single normalization pass that:

- Inlines supported CSS rules into `style=""`
- Promotes supported declarations to SVG presentation attributes
- Preserves authoring metadata such as `viewBox`, `width`, and `height`
- Emits deterministic attribute ordering for stable hashes
- Works even when `tinycss2` is unavailable, while preferring it when present

## Decision

Adopt `svg2pptx/normalize_svg.py` as the canonical pre-processing step before analysis/policy. The module:

1. Parses `<style>` blocks (via `tinycss2` when available, falling back to a minimal parser) and applies cascaded rules to elements.
2. Maps supported CSS properties to presentation attributes using `STYLE_TO_ATTR`, leaving non-mapped declarations in `style`.
3. Sorts element attributes to produce deterministic XML.
4. Retains `viewBox`, explicit dimensions, and other fidelity-critical attributes.

The helper exposes `normalize_svg_string` and `normalize_svg_file` utilities that the pipeline will invoke prior to parsing.

## Consequences

- **Reproducibility**: Deterministic attribute ordering improves cache hits, test snapshots, and diff review.
- **Policy Accuracy**: Promoting CSS to attributes enables existing mappers/policies to read styling without re-implementing CSS cascade.
- **Dependency Footprint**: `tinycss2` remains optional; the fallback parser keeps normalization operational in constrained environments.
- **Future Extensions**: Additional style mappings can be appended to `STYLE_TO_ATTR` as we broaden support (e.g., filter or marker properties).

## Testing & Rollout

- Add unit tests covering selector specificity, style promotion, and attribute ordering.
- Introduce integration snapshots that verify normalized SVG emits unchanged geometry while producing expected attribute sets.
- Wire normalization into the ingest stage and ensure e2e conversion diffs are recorded before/after the change.

## References

- Source implementation: `svg2pptx/normalize_svg.py`
- Existing CSS mapping table: `STYLE_TO_ATTR` within the module.

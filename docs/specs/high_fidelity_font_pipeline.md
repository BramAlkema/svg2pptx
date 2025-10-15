# High-Fidelity Font Pipeline

## Spec Overview

### 1. Discovery Foundation
- Extend `FontService` to crawl config-defined directories (`fonts/`, project root), merge system fonts, and expose an index keyed by `(family, weight, style)`.
- Parse SVG `<style>` and `@font-face` blocks to collect downloadable sources; persist normalized `FontSource` records for later retrieval.
- Surface the catalog via `ConversionServices` (for example, `services.font_registry.find_variant(...)`) with weight/style normalization (numeric weights → CSS keywords).

### 2. Download/Fallback Pipeline
- Add a `FontFetcher` that handles:
  - Google Fonts API (batch download, subsetting if possible).
  - Direct URLs (`url(...)`) with caching under `.cache/fonts/`.
  - Verification (hash/size), sanitization (strip scripts), and trust policy.
- Feed fetched files into `FontService` so subsequent lookups hit the local cache.

### 3. Variant-Accurate Embedding
- During mapping:
  - Annotate runs with target variant (from explicit attributes or CSS resolution).
  - Request the exact variant from discovery/fetcher and subset it.
  - Ensure `TextMapper` uses the embedded variant’s relationship ID and sets accurate font metadata on the XML runs.
- Allow multiple variants of the same family in a presentation; dedupe subset requests across slides.

### 4. Strict vs. Graceful Modes
- Extend `PolicyConfig` with `font_missing_behavior` (`error`, `outline`, `fallback_family`).
- When resolution fails:
  - `error`: throw pipeline error with actionable message.
  - `outline`: render text to EMF or convert to paths (annotate warning).
  - `fallback_family`: map to configured alternative (e.g., “Arial”) and record downgrade.

### 5. Diagnostics & Tests
- Enrich debug JSON with per-font decisions (source, fetched, subset_chars, warnings).
- Integration suites:
  - Multi-weight family (Regular/Bold/Italic) round-trip verifying PPTX embedded fonts.
  - CJK font scenario ensuring remote download/subset works.
  - Missing fonts in strict vs graceful modes.
- Optional visual diff baseline to ensure outlines vs embedded fonts render as expected.

## Task Plan

### 1. Discovery Foundation
- [x] Add font search path configuration (`FontServiceConfig`), include project-local directories.
- [x] Implement SVG `@font-face` parsing with data model + registry.
- [x] Expose normalized `(family, weight, style)` lookup API via `ConversionServices`.

### 2. Download/Fallback Pipeline
- [x] Build `FontFetcher` with Google Fonts + URL support, including caching and sanitization.
- [x] Integrate fetcher with `FontService` so lookup falls back to download when necessary.
- [x] Add configuration flags for network access and cache location.

### 3. Variant-Accurate Embedding
- [x] Propagate run-level font metadata (weight/style) from parsing through mapping.
- [x] Update `_prepare_embedded_fonts` to request precise variants and reuse subsets per presentation.
- [x] Ensure PPTX export references distinct relationships and XML run properties.

### 4. Strict vs. Graceful Modes
- [x] Extend policy/config to accept `font_missing_behavior`.
- [x] Implement branch logic for `error`, `outline`, and `fallback_family`, including EMF/path fallback support.
- [x] Add surfaced warnings/errors to `ConversionResult`.

### 5. Diagnostics & Tests
- [x] Expand debug payloads with font decision logs.
- [x] Write integration tests for multi-weight, CJK, and missing font scenarios (strict vs graceful).
- [x] (Optional) Add visual diff harness for outline fallback verification.

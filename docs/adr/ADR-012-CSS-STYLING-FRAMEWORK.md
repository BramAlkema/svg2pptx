# ADR-012: CSS Styling Framework

## Status
Accepted (2025-10-03)

## Context
Clean Slate currently treats CSS as an afterthought:

- The SVG parser only understands a handful of inline `style="..."` properties (basic font and fill fields). `<style>` blocks, selectors, inheritance, CSS variables, and computed values are ignored.
- Colors rely on ad-hoc helpers; the full CSS Level 4 palette shipped in `core/color/css_colors.py` is not used consistently.
- Font handling scatters logic across multiple modules (`_parse_font_size`, `_normalize_font_weight`, `SVGFontAnalyzer`), making it difficult to reason about cascaded styles or embedded `@font-face` rules.
- Animations driven by CSS (e.g., `@keyframes`, `animation`, `transition`) are invisible to the converter. External tooling such as the `css_to_smil.py` prototype shows demand for bridging CSS animations into SMIL/PowerPoint, but the current architecture cannot ingest that data.

As we expand animation fidelity and want richer styling (gradients, transforms, responsive attributes), we need a dedicated CSS layer that can grow in capability without constantly patching individual parsers.

## Decision
Introduce a reusable CSS styling framework that centralizes parsing, cascading, and normalization for SVG content. Core principles:

1. **Dedicated module** – Create `core/css/` with utilities built on `tinycss2`, `cssselect2`, `webencodings`, and `lxml`. Responsibilities include parsing inline styles, `<style>` blocks, and basic selector matching (element, class, id).
2. **Computed style service** – Expose a `StyleResolver` that returns normalized properties (colors, fonts, numeric units, transforms, opacity, etc.) for any SVG element, including inheritance and specificity handling. Current font/color helpers migrate into this service.
3. **CSS assets ingestion** – Parse `@font-face` and `@keyframes`, retaining structured data that other subsystems can consume (e.g., font embedding, animation timeline). Honor existing data in `SVGFontAnalyzer` but unify under the same parser.
4. **Animation bridge** – Define an extensible contract for extracting CSS animations: translate `@keyframes` + `animation-*` properties into intermediate tracks that the animation pipeline can convert to SMIL or PowerPoint timing. This complements the `css_to_smil.py` proof of concept and paves the way for JS-backed sampling later.
5. **Incremental rollout** – Maintain current behavior initially (inline styles only) but route through the new APIs so we can progressively enable more CSS features without wide refactors.

## Implementation Plan
1. **Foundations (MVP)**  
   - Introduce `StyleResolver` with support for inline styles and the existing property set (font family/size/weight/style, fill color, opacity).  
   - Refactor `SVGParser` to request styles via the resolver; update tests to rely on the new module.  
   - Replace `_parse_color_value` and related helpers with calls into the resolver (which uses `get_css_color` and common numeric parsing).

2. **Stylesheet & Selector Support**  
   - Parse `<style>` blocks using `tinycss2`; build a selector matcher with `cssselect2`.  
   - Implement a minimal cascade: specificity, source order, `!important`, inheritance of standard properties.  
   - Extend the resolver to merge inline and stylesheet declarations, exposing computed values to the rest of the pipeline.

3. **Fonts & Assets Integration**  
   - Move font extraction into the CSS module: parse `@font-face`, track embedded data, normalize font stacks.  
   - Feed computed font data into the font analyzer and policy engine, ensuring consistent fallback rules.

4. **Animation Extraction**  
   - Parse `@keyframes` and `animation-*` properties into structured timelines (target properties, offsets, easing).  
   - Provide adapters so the animation converter can ingest these CSS tracks alongside SMIL animations.  
   - Use the existing headless `css_to_smil.py` script as a reference for property coverage (transform, opacity, direction, fill modes) while designing reusable data structures.

5. **Future Enhancements**  
   - Support additional properties (strokes, gradients, filters, `currentColor`, CSS variables).  
   - Layer in media queries and container queries as needed.  
   - Coordinate with planned JS animation sampling so CSS-resolved styles and runtime overrides share a common model.

## Consequences
- Centralizing CSS handling reduces duplication and makes it easier to extend styling features without spreading logic across parsers and mappers.
- The animation pipeline gains a formal entry point for CSS-driven timelines, enabling future work on `@keyframes`, transitions, and possibly JS-assisted sampling.
- There is an upfront cost in designing the resolver and migrating existing code, but subsequent enhancements (e.g., richer color handling, additional properties) become incremental additions rather than invasive refactors.
- Pulling in `tinycss2`/`cssselect2` introduces new dependencies, but they are lightweight, well-supported, and already used by the standalone `css_to_smil.py` experiment.

# ADR-013: CSS Keyframes to SMIL Conversion Tool

## Status
Accepted (2025-10-03)

## Context
Many SVG animations rely on CSS `@keyframes` and `animation-*` properties rather than SMIL `<animate>` blocks. Our Clean Slate pipeline currently only understands SMIL, so CSS-driven motion is ignored. A standalone script (`css_to_smil.py`) demonstrates how to translate CSS animations into explicit SMIL elements the rest of the converter can consume. The script depends on `tinycss2`, `cssselect2`, `lxml`, and `webencodings` and supports:

- Translate/rotate/scale transforms and opacity tracks
- Basic animation longhands/shorthand (duration, delay, timing-function, iteration-count, direction, fill-mode)
- Cubic-bezier easing
- Simple cascading via cssselect2 matcher

It omits skew/matrix transforms, `steps()` easing, and advanced cascading, but it serves as a bridge for common cases. We need to decide how this utility fits into the broader roadmap.

## Decision
Keep `css_to_smil.py` as an auxiliary tool and formally document its role:

1. **Reference implementation** – Use the script as a living prototype for mapping CSS animations to SMIL. It guides future integration work inside the pipeline and validates that the `tinycss2`/`cssselect2` stack meets our needs.
2. **Opt-in preprocessing** – Teams can run `python css_to_smil.py in.svg out.svg` before conversion to materialize CSS animations into SMIL, enabling the existing animation pipeline without code changes. The script’s README/documentation should note its dependency on the four pip packages.
3. **Future integration path** – As the CSS resolver (ADR-012) matures, migrate the script’s logic into the core pipeline so CSS animations are handled natively. Until then, we ship the script alongside developer tooling and tests to keep coverage possible.

## Consequences
- Developers have an immediate workaround for CSS animations and a spec-compliant example of how to convert them.
- The pipeline remains unchanged for now; integrating CSS animations properly still requires additional engineering (selector cascade, timing orchestration).
- By endorsing `tinycss2` and `cssselect2`, we align the script with the dependencies adopted in ADR-012, easing future consolidation.

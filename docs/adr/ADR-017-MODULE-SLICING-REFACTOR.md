# ADR-017: Parser & Pipeline Module Slicing

**Status**: Accepted  
**Date**: 2025-10-13

## Context
The legacy `core/parse/parser.py` and converter pipeline modules had accrued over a thousand lines of tightly coupled logic. This monolith made it difficult to test IR conversion, clip-path extraction, and font/resource management in isolation. Downstream services (font embedding, resource manager, presentation composer) also relied on implicit behaviours undocumented outside the implementation.

## Decision
1. **Introduce `core.parse_split` helpers** for XML parsing, validation, clip extraction, style context resolution, hyperlink processing, and IR conversion.  
2. **Retain `SVGParser` as orchestration glue**, emitting a deprecation warning and delegating to the new helpers for backwards compatibility.  
3. **Add resource/font managers** (`core/pipeline/resource_manager.py`, `core/pipeline/slide_manager.py`) and route converter orchestration through them.  
4. **Update tests** to cover the sliced parser stack (`tests/unit/core/parse/test_svg_parser_integration.py`) and refresh e2e flows (font service, native shapes).  
5. **Document the changes** across developer guides, metrics summaries, and the changelog so downstream teams can migrate.

## Consequences
- Parser logic is now testable in isolation; clip refs and hyperlink metadata are verified via unit tests.
- `core/parse/parser.py` shrank from ~2,000 lines to ~660 lines, with the heavy lifting owned by the helpers.
- Resource manager and font embedding flows remain hotspots (complexity F), but they are now encapsulated for future extraction.
- Consumers should import new helpers from `core.parse_split` when directly constructing slicing workflows.

# ADR-009: PPTX Package Compliance Hardening

## Status
Accepted (2025-09-29)

## Context
PowerPoint prompted users to "Repair" every PPTX produced by the Clean Slate `PackageWriter`. Inspection showed that the generated archives lacked the mandatory docProps parts, root relationships did not reference metadata, and the slide master had no relationship part to resolve `rId1`/`rId2` bindings. These gaps violate ECMA-376 packaging rules and lead Office to auto-generate replacements, risking lost fidelity and eroding trust in the converter.

## Decision
- Emit `docProps/core.xml` and `docProps/app.xml` during packaging, deriving metadata from the manifest and slide count.
- Expand `[Content_Types].xml` and `_rels/.rels` to register the new parts and ensure Office clients resolve them without repair.
- Write `ppt/slideMasters/_rels/slideMaster1.xml.rels` so layout/theme references resolve cleanly.
- Normalise default content types, propagating media extensions discovered via the manifest so embedded assets retain explicit MIME metadata.
- Back the change with targeted unit tests that unzip the output and assert the presence and wiring of docProps, master relationships, and updated content types.

## Consequences
- Newly generated PPTX files open without the repair warning in PowerPoint/Google Slides, improving perceived quality.
- Packaging becomes more spec-aligned, reducing the likelihood of downstream compatibility regressions.
- Unit coverage now guards the critical OOXML surface; future refactors must preserve these structural guarantees.
- Slightly larger archives due to additional XML parts, but the trade-off favours correctness and interoperability.

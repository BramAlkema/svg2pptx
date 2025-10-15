# PPTX Template Migration TODO

1. **Template Inventory** (✅ initial clean-slate theme/master/layouts captured under `pptx_templates/clean_slate/`)
   - Extract authoritative `presentation.xml`, `slideMaster.xml`, `slideLayout*.xml`, `theme.xml`, `[Content_Types].xml`, `_rels/.rels`, `presentation.xml.rels`, and docProps into a dedicated `pptx_templates/clean_slate/` directory.
   - Capture multiple layout variants (title/content, blank, section headers) from reference decks for future expansion.

2. **Template Loader API** (✅ `core.io.template_store.TemplateStore` implemented with caching/deep copies)
   - Implement `core.io.template_store.TemplateStore` that lazy-loads and caches parsed XML trees.
   - Provide helpers: `get_presentation()`, `get_slide_master()`, `get_slide_layout(name)`, `get_doc_props()`, `get_content_types()`.
   - Ensure deep copies are returned so call sites mutate safely.

3. **Mutation Helpers** (✅ PackageWriter now mutates parsed templates for IDs, metadata, relationships)
   - Add functions to inject dynamic metadata (slide IDs, relationships, titles/authors, timestamps) into cloned templates.
   - Centralise relationship ID sequencing to avoid duplication across slides, masters, and media parts.

4. **PackageWriter Refactor** (✅ switched to template-driven assembly)
   - Replace string-based XML builders with template retrieval + mutation pipeline.
   - Wire PackageWriter to accept a `TemplateStore` dependency (default to shared singleton) for easier testing.

5. **Tests & Tooling** (✅ unit & integration coverage exercising template workflow)
   - Finalise new unit tests that assert template caching, deep-copy behaviour, and required placeholders.
   - Add integration tests that build PPTX via PackageWriter + TemplateStore and snapshot resulting OOXML for regression coverage.
   - Document developer workflow for updating templates (e.g., script to sync from reference PPTX exports).

6. **Follow-up Tasks** (🟡 remaining)
   - Audit other modules (`core/legacy`, `presentationml/`) and delete legacy XML hardcodes replaced by templates.
   - Update ADRs and README sections to reflect template-driven packaging.
   - Extend `core/io/template_constants.py` when expanding template variants (e.g., section headers, custom themes).

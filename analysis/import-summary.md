# Import Usage Summary

- `core.parse.parser.SVGParser` (9 direct imports)  
  - Primary usage in parsing-focused unit tests under `tests/unit/core/parse/` and `tests/unit/parse/`.  
  - Referenced by debugging scripts (`scripts/debugging/` and `debug_path_bug.py`) for IR inspection workflows.
- `core.utils.enhanced_xml_builder` (0 direct imports)  
  - No files import the module via `from ... import ...`; consumers rely on alternative access patterns (likely module-level imports or factory helpers).  
  - Refactor impact: introducing a new package structure should require updating indirect imports only.
- `core.viewbox.core` (2 direct imports)  
  - Used in performance benchmarking (`scripts/benchmark_viewbox_performance_validation.py`) and end-to-end validation (`tests/e2e/core_systems/test_viewbox_system_e2e.py`).  
  - Both consumers access multiple exported helpers via tuple unpacking.

- Module-level imports (`import core.parse.parser`, `import core.utils.enhanced_xml_builder`, `import core.viewbox.core`)  
  - No occurrences found in the repository, reducing surface area for compatibility shims during package extraction.

Next steps: audit wildcard imports (`from core.viewbox import *` / `import core.viewbox as ...`) to ensure the new public API maintains compatibility.

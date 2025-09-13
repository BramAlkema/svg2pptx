# Test File Naming Convention Audit Report

**Generated:** 2025-09-12  
**Purpose:** Document current naming patterns for standardization effort  
**Task:** 1.2 - Audit and document existing test files and naming patterns

## Executive Summary

- **Total Test Files:** 91 files analyzed
- **Compliance Rate:** 92.3% (84/91 files follow basic conventions)
- **Non-compliant Files:** 7 files requiring standardization
- **Primary Pattern:** All files use `test_` prefix pattern (100%)

## Directory Structure Analysis

### ✅ Well-Organized Directories
```
tests/
├── unit/              (34 files) - Unit tests
├── integration/       (9 files)  - Integration tests  
├── e2e_api/          (3 files)  - End-to-end API tests
├── e2e_visual/       (1 file)   - Visual E2E tests
├── e2e_library/      (1 file)   - Library E2E tests
├── architecture/     (2 files)  - Architecture tests
├── visual/           (1 file)   - Visual regression tests
├── coverage/         (1 file)   - Coverage analysis tests
└── benchmarks/       (0 files)  - Performance benchmarks
```

### Files by Category Distribution
- **Unit Tests:** 34 files (37.4%)
- **Miscellaneous/Root:** 35 files (38.5%) - *Needs reorganization*
- **E2E Tests:** 9 files (9.9%)
- **Integration Tests:** 9 files (9.9%)
- **Architecture:** 2 files (2.2%)
- **Visual:** 1 file (1.1%)
- **Coverage:** 1 file (1.1%)

## Naming Pattern Analysis

### Current Patterns
- **test_prefix:** 91 files (100%) - All files use `test_*.py` format
- **test_suffix:** 0 files (0%) - No files use `*_test.py` format

### Compliance Status

#### ✅ Compliant Files (84 files - 92.3%)
Files already following standard `test_[component].py` naming:
- All files in `tests/unit/converters/`
- Most files in `tests/integration/`
- Most root-level test files

#### ❌ Non-compliant Files (7 files - 7.7%)
Files requiring standardization:

1. **tests/test_svg2pptx_json_v2.py**
   - Issue: Complex name with version suffix
   - Suggested: `test_svg2pptx_json_v2.py` (already compliant, may need categorization)

2. **tests/unit/test_svg2pptx_main.py**
   - Issue: Located in unit directory but unclear categorization
   - Suggested: `test_svg2pptx_main.py`

3. **tests/e2e_library/test_svg_test_library.py**
   - Issue: Missing e2e suffix for E2E test
   - Suggested: `test_svg_library_e2e.py`

4. **tests/integration/test_comprehensive_e2e.py**
   - Issue: E2E test in integration directory
   - Suggested: Move to e2e_* directory or rename

5. **tests/integration/test_converter_specific_e2e.py**
   - Issue: E2E test in integration directory
   - Suggested: Move to e2e_* directory or rename

6. **tests/integration/test_core_module_e2e.py**
   - Issue: E2E test in integration directory
   - Suggested: Move to e2e_* directory or rename

7. **tests/visual/test_golden_standards.py**
   - Issue: Missing visual suffix for visual test
   - Suggested: `test_golden_standards_visual.py`

## Detailed File Inventory

### Root Level Tests (35 files)
Files that should be categorized into appropriate subdirectories:

```
test_accuracy_measurement.py
test_animations_converter.py
test_base_converter.py
test_batch_simple_api.py
test_configuration.py
test_coverage_configuration.py
test_dead_code_detection.py
test_end_to_end_verification.py
test_end_to_end_workflow.py
test_filters_converter.py
test_filters_enhancements.py
test_font_embedding_integration.py
test_gradients_converter.py
test_markers_additional.py
test_markers_converter.py
test_markers_final.py
test_masking_converter.py
test_module_imports.py
test_multislide_detection.py
test_patterns_enhancements.py
test_performance_speedrun_benchmark.py
test_performance_speedrun_cache.py
test_performance_speedrun_optimizer.py
test_pptx_validation.py
test_pptx_validation_complete.py
test_pptx_validation_comprehensive.py
test_pptx_validation_final.py
test_styles_processor.py
test_svg2pptx_json_v2.py
test_symbols_converter.py
test_text_path_converter.py
test_viewport_coordinate_integration.py
test_visual_regression.py
test_workflow_validator.py
```

### Unit Tests Structure (34 files)
Well-organized in subdirectories:

```
tests/unit/
├── converters/           (22 files)
│   ├── test_*.py        (Converter-specific tests)
├── utils/               (3 files)  
├── batch/               (8 files)
└── test_svg2pptx_main.py (1 file)
```

### Integration Tests (9 files)
Mixed quality - some have E2E tests misplaced:

```
test_comprehensive_e2e.py        # Should move to e2e_*
test_converter_registry_integration.py
test_converter_specific_e2e.py   # Should move to e2e_*
test_core_module_e2e.py         # Should move to e2e_*
test_end_to_end_conversion.py
test_preprocessing_pipeline.py
```

## Recommended Standardization Actions

### Priority 1: Move Misplaced Files
1. Move E2E tests from `integration/` to appropriate `e2e_*` directories
2. Categorize root-level tests into appropriate subdirectories

### Priority 2: Apply Naming Suffixes
1. Add `_e2e` suffix to E2E tests
2. Add `_visual` suffix to visual regression tests  
3. Add `_benchmark` suffix to performance tests

### Priority 3: Directory Reorganization
1. Create subcategories in root tests:
   - `tests/unit/converters/` (for converter tests)
   - `tests/unit/validation/` (for validation tests)
   - `tests/integration/preprocessing/` (for preprocessing tests)
   - `tests/performance/` (for performance tests)

## Impact Assessment

### Low Risk Changes (84 files)
Files already compliant - no changes needed.

### Medium Risk Changes (7 files)  
Files requiring renaming - need import statement updates.

### High Risk Changes (35 files)
Root-level files requiring directory moves - extensive import updates needed.

## Implementation Strategy

1. **Phase 1:** Fix 7 non-compliant files with simple renames
2. **Phase 2:** Reorganize root-level files by category
3. **Phase 3:** Apply consistent naming suffixes across categories
4. **Phase 4:** Update all import statements and references

## Success Metrics

- [ ] 100% compliance with naming conventions
- [ ] Clear directory structure with proper categorization
- [ ] All tests continue to pass after changes
- [ ] Updated documentation reflects new structure

## Next Steps

Proceed to Task 1.3: Implement standardized naming convention with focus on the 7 identified non-compliant files first, then systematic reorganization of the 35 root-level files.
# Migration Priority Matrix

## Priority Scoring Methodology

Each test file is scored based on multiple factors to determine migration priority:

### Scoring Factors

| Factor | Weight | Scoring |
|--------|--------|---------|
| **Domain Impact** | 40% | Converter (10), API (8), Core (6), Utility (4) |
| **Coverage Impact** | 30% | High coverage modules (10), Medium (6), Low (2) |
| **Migration Complexity** | 20% | Low (10), Medium (6), High (2) |
| **File Size/Effort** | 10% | Small (10), Medium (6), Large (2) |

### Priority Levels
- **Critical (8.0-10.0)**: Immediate migration required
- **High (6.0-7.9)**: Priority batch 1-2
- **Medium (4.0-5.9)**: Standard migration batches
- **Low (0.0-3.9)**: Final cleanup batches

## Migration Priority Matrix

| File | Domain Impact | Coverage Impact | Complexity | Size/Effort | **Total Score** | **Priority** | **Batch** |
|------|---------------|-----------------|------------|-------------|-----------------|--------------|-----------|
| `test_unit_converter_comprehensive.py` | 10 (Converter) | 10 (High) | 10 (Low) | 6 (Medium) | **9.2** | **Critical** | **1** |
| `test_colors.py` | 6 (Core) | 8 (Color module) | 10 (Low) | 2 (Large) | **6.8** | **High** | **2** |
| `test_transforms.py` | 6 (Core) | 8 (Transform module) | 10 (Low) | 2 (Large) | **6.8** | **High** | **2** |
| `test_units.py` | 6 (Core) | 10 (Units module) | 10 (Low) | 2 (Large) | **7.2** | **High** | **2** |
| `test_viewbox.py` | 6 (Core) | 6 (Viewbox module) | 10 (Low) | 6 (Medium) | **6.4** | **High** | **2** |
| `test_preprocessing_integration.py` | 6 (Core) | 6 (Integration) | 10 (Low) | 10 (Small) | **6.8** | **High** | **3** |
| `test_integration_units.py` | 6 (Core) | 6 (Integration) | 10 (Low) | 6 (Medium) | **6.4** | **High** | **3** |
| `test_speedrun.py` | 6 (Core) | 4 (Performance) | 10 (Low) | 6 (Medium) | **5.6** | **Medium** | **4** |
| `test_unit_deployment_simple.py` | 6 (Core) | 4 (Deployment) | 10 (Low) | 6 (Medium) | **5.6** | **Medium** | **4** |
| `test_geometry_simplification.py` | 6 (Core) | 4 (Geometry) | 10 (Low) | 6 (Medium) | **5.6** | **Medium** | **4** |
| `test_advanced_optimizations.py` | 6 (Core) | 4 (Optimization) | 10 (Low) | 6 (Medium) | **5.6** | **Medium** | **4** |
| `src/preprocessing/test_optimizer.py` | 6 (Core) | 4 (Optimization) | 10 (Low) | 10 (Small) | **6.0** | **Medium** | **4** |
| `test_file_analyzer.py` | 4 (Utility) | 2 (Tool) | 6 (Medium) | 2 (Large) | **3.6** | **Low** | **5** |

## Detailed Migration Batches

### Batch 1: Critical Priority (Immediate)
**Target Timeline**: Week 1

| File | Rationale | Estimated Effort | Risk Level |
|------|-----------|------------------|------------|
| `test_unit_converter_comprehensive.py` | Only converter test; highest coverage impact; essential for project goals | 2-3 hours | Low |

**Success Criteria**: Converter test coverage maintained, centralized fixtures working

### Batch 2: High Priority Core Modules (Large Impact)
**Target Timeline**: Week 1-2

| File | Lines | Rationale | Estimated Effort |
|------|-------|-----------|------------------|
| `test_units.py` | 465 | Core unit conversion functionality | 4-5 hours |
| `test_colors.py` | 454 | Color processing (large codebase dependency) | 4-5 hours |
| `test_transforms.py` | 441 | Transform operations (complex math) | 4-5 hours |
| `test_viewbox.py` | 319 | Viewport handling (UI critical) | 3-4 hours |

**Success Criteria**: Core module coverage maintained above 60%, no regression in functionality

### Batch 3: Integration Tests (Cross-Module)
**Target Timeline**: Week 2

| File | Lines | Rationale | Estimated Effort |
|------|-------|-----------|------------------|
| `test_preprocessing_integration.py` | 185 | End-to-end preprocessing flow | 2-3 hours |
| `test_integration_units.py` | 313 | Unit system integration | 3-4 hours |

**Success Criteria**: Integration test coverage maintained, cross-module interactions verified

### Batch 4: Standard Priority (Medium Impact)
**Target Timeline**: Week 3

| File | Lines | Domain | Estimated Effort |
|------|-------|--------|------------------|
| `src/preprocessing/test_optimizer.py` | 108 | Optimization | 1-2 hours |
| `test_speedrun.py` | 236 | Performance | 2-3 hours |
| `test_unit_deployment_simple.py` | 239 | Deployment | 2-3 hours |
| `test_geometry_simplification.py` | 235 | Geometry | 2-3 hours |
| `test_advanced_optimizations.py` | 293 | Optimization | 3-4 hours |

**Success Criteria**: All core functionality tests migrated, performance benchmarks maintained

### Batch 5: Cleanup (Low Priority)
**Target Timeline**: Week 4

| File | Lines | Rationale | Estimated Effort |
|------|-------|-----------|------------------|
| `test_file_analyzer.py` | 495 | Tool script; may need reclassification | 2-3 hours |

**Success Criteria**: All project tests migrated or properly categorized

## Risk Assessment by Batch

### Low Risk (Batches 1, 3, 4)
- **Characteristics**: Simple test structure, minimal mocking, clear dependencies
- **Mitigation**: Standard migration process, backup original files
- **Files**: 10 out of 13

### Medium Risk (Batch 2)
- **Characteristics**: Large files, complex test cases, multiple dependencies
- **Mitigation**: 
  - Break large files into smaller test modules if needed
  - Extensive testing after migration
  - Gradual fixture replacement
- **Files**: 4 out of 13

### High Risk (Batch 5)
- **Characteristics**: Non-standard test file (tool script)
- **Mitigation**: 
  - Evaluate if file should remain as test or become utility script
  - Potential relocation to `scripts/` or `tools/` directory
- **Files**: 1 out of 13

## Success Metrics

### Coverage Targets
- **Overall project coverage**: Maintain current 9.67%, target 50%
- **Converter module coverage**: Maintain current 61.71%, target 60%+
- **Core module coverage**: Target 40%+ for units, colors, transforms

### Quality Metrics
- **Zero regression**: All existing functionality preserved
- **Improved maintainability**: Centralized fixtures reduce duplication
- **Better organization**: Clear test directory structure

### Performance Metrics
- **Test execution time**: Should not increase significantly
- **Development velocity**: Faster test writing with centralized fixtures

## Migration Dependencies

### Prerequisites
1. Centralized fixture system must be complete and tested
2. New test directory structure (`tests/unit/`, `tests/integration/`) must exist
3. Backup strategy for original files

### Fixture Requirements by Batch

#### Batch 1 Fixtures Needed
- `mock_conversion_context`
- `sample_svg_elements`
- `converter_test_data`

#### Batch 2 Fixtures Needed
- `unit_test_data` (various units and conversions)
- `color_test_data` (color formats and values)
- `transform_test_data` (matrices and operations)
- `viewport_test_data` (viewport configurations)

#### Batch 3 Fixtures Needed
- `integration_test_data`
- `preprocessing_test_data`
- `end_to_end_scenarios`

## Timeline Summary

| Week | Batch | Files | Estimated Hours | Cumulative Coverage |
|------|-------|-------|-----------------|-------------------|
| 1 | 1 + Start 2 | 3 files | 12-15 hours | Maintain current |
| 2 | Finish 2 + 3 | 4 files | 15-18 hours | 45%+ target |
| 3 | 4 | 5 files | 12-15 hours | 48%+ target |
| 4 | 5 + Cleanup | 1 file | 5-8 hours | 50%+ target |

**Total Estimated Effort**: 44-56 hours across 4 weeks
**Total Files**: 13 project test files
**Expected Outcome**: Fully migrated, centralized testing system with improved coverage
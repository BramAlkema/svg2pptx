# Test File Naming Conventions

**Version:** 1.0  
**Created:** 2025-09-12  
**Last Updated:** 2025-09-12

## Overview

This document establishes standardized naming conventions for all test files in the SVG2PPTX project. These conventions ensure consistency, clarity, and proper organization across the entire test suite.

## Directory Structure

```
tests/
├── unit/                    # Unit tests (isolated component tests)
│   ├── converters/         # Converter-specific unit tests
│   ├── utils/              # Utility function tests
│   ├── batch/              # Batch processing tests
│   └── api/                # API unit tests
├── integration/            # Integration tests (multiple components)
├── e2e_integration/        # End-to-end integration tests
├── e2e_api/               # End-to-end API tests
├── e2e_library/           # End-to-end library tests  
├── e2e_visual/            # End-to-end visual tests
├── visual/                # Visual regression tests
├── benchmarks/            # Performance benchmark tests
├── architecture/          # Architecture and consistency tests
└── coverage/              # Coverage analysis tests
```

## Naming Patterns

### File Naming Format

All test files MUST follow the pattern: `test_<component>_<suffix>.py`

- **Prefix:** Always `test_`
- **Component:** Descriptive name using snake_case
- **Suffix:** Category-specific suffix (see below)
- **Extension:** Always `.py`

### Category-Specific Suffixes

| Category | Suffix | Example |
|----------|---------|---------|
| **Unit Tests** | _(none)_ | `test_rectangle_converter.py` |
| **Integration Tests** | _(none)_ | `test_svg_to_pptx_pipeline.py` |
| **E2E Tests** | `_e2e` | `test_complete_conversion_e2e.py` |
| **Visual Tests** | `_visual` | `test_golden_standards_visual.py` |
| **Benchmark Tests** | `_benchmark` | `test_performance_benchmark.py` |
| **Architecture Tests** | _(none)_ | `test_codebase_consistency.py` |

## Detailed Naming Rules

### Unit Tests
```
Pattern: test_<component_name>.py
Location: tests/unit/<subcategory>/
Examples:
  - test_rectangle_converter.py
  - test_path_parser.py
  - test_color_utils.py
```

### Integration Tests  
```
Pattern: test_<integration_scenario>.py
Location: tests/integration/
Examples:
  - test_svg_preprocessing_pipeline.py
  - test_converter_registry_integration.py
  - test_end_to_end_conversion.py
```

### End-to-End Tests
```
Pattern: test_<workflow_name>_e2e.py
Locations: 
  - tests/e2e_integration/
  - tests/e2e_api/
  - tests/e2e_library/
  - tests/e2e_visual/
Examples:
  - test_comprehensive_e2e.py
  - test_fastapi_e2e.py
  - test_svg_library_e2e.py
  - test_visual_fidelity_e2e.py
```

### Visual Regression Tests
```
Pattern: test_<visual_aspect>_visual.py
Location: tests/visual/
Examples:
  - test_golden_standards_visual.py
  - test_layout_preservation_visual.py
```

### Performance Tests
```
Pattern: test_<performance_aspect>_benchmark.py
Location: tests/benchmarks/
Examples:
  - test_conversion_speed_benchmark.py
  - test_memory_usage_benchmark.py
```

## Class and Method Naming

### Test Classes
```python
# Pattern: Test<ComponentName>
class TestRectangleConverter:
    """Tests for RectangleConverter functionality."""
    
class TestSVGPreprocessing:
    """Tests for SVG preprocessing pipeline."""
```

### Test Methods
```python
# Pattern: test_<specific_behavior>
def test_converts_rectangle_with_rounded_corners(self):
    """Test that rectangles with rounded corners are converted correctly."""
    
def test_handles_invalid_svg_gracefully(self):
    """Test that invalid SVG input is handled gracefully."""
    
def test_preserves_aspect_ratio_during_conversion(self):
    """Test that aspect ratios are preserved during conversion."""
```

## Implementation Examples

### ✅ Correct Examples

```python
# tests/unit/converters/test_rectangle_converter.py
class TestRectangleConverter:
    def test_basic_rectangle_conversion(self):
        pass
    
    def test_rounded_rectangle_conversion(self):
        pass

# tests/integration/test_svg_preprocessing.py  
class TestSVGPreprocessing:
    def test_preprocessing_pipeline_integration(self):
        pass

# tests/e2e_api/test_conversion_workflow_e2e.py
class TestConversionWorkflowE2E:
    def test_complete_svg_to_pptx_workflow(self):
        pass

# tests/visual/test_golden_standards_visual.py
class TestGoldenStandardsVisual:
    def test_visual_comparison_with_baseline(self):
        pass
```

### ❌ Incorrect Examples

```python
# ❌ Missing test_ prefix
rectangle_converter_tests.py

# ❌ Wrong suffix placement  
test_e2e_conversion_workflow.py  # Should be: test_conversion_workflow_e2e.py

# ❌ Inconsistent naming
test_RectangleConverter.py  # Should be: test_rectangle_converter.py

# ❌ Missing category suffix for E2E
test_complete_workflow.py  # Should be: test_complete_workflow_e2e.py
```

## Directory-Specific Guidelines

### Unit Tests (`tests/unit/`)
- Test individual components in isolation
- Use mocks for external dependencies
- Focus on single responsibility
- No external API calls or file I/O

### Integration Tests (`tests/integration/`)
- Test interaction between multiple components
- May use real external dependencies
- Test data flow and component interaction
- Avoid full end-to-end scenarios

### E2E Tests (`tests/e2e_*/`)
- Test complete user workflows
- Use real services and data
- Test from user's perspective
- Include setup and teardown

### Visual Tests (`tests/visual/`)
- Compare visual output with baselines
- Test rendering accuracy
- Use image comparison tools
- Store reference images

## Enforcement

### Automated Checks
1. **pytest Collection Rules** - Configured in `pytest.ini`
2. **Pre-commit Hooks** - Validate naming before commits
3. **CI Pipeline** - Block PRs with non-compliant naming

### Manual Review
- Code review checklist includes naming validation
- Architecture tests verify compliance
- Regular audits of test file naming

## Migration Guide

### For Existing Files
1. Identify current naming pattern
2. Determine correct category and suffix
3. Rename file following new convention
4. Update any import references
5. Run tests to verify functionality

### For New Files
1. Determine test category (unit, integration, e2e, etc.)
2. Choose appropriate directory
3. Follow naming pattern with required suffix
4. Use standard class and method naming

## Maintenance

### Regular Reviews
- Monthly audit of new test files
- Quarterly review of naming consistency
- Annual review of conventions for updates

### Updates
- Document any changes to this guide
- Communicate changes to development team
- Update automation rules as needed

## Benefits

- **Consistency:** Uniform naming across entire codebase
- **Clarity:** Easy to understand test purpose from filename
- **Organization:** Logical grouping and categorization
- **Automation:** Enables better tooling and CI/CD integration
- **Maintainability:** Easier to locate and maintain tests

## Compliance Checklist

- [ ] File starts with `test_` prefix
- [ ] Uses snake_case for component name
- [ ] Includes appropriate category suffix
- [ ] Located in correct directory
- [ ] Class names use `Test<ComponentName>` pattern
- [ ] Method names use `test_<specific_behavior>` pattern
- [ ] Follows single responsibility principle

---

**For questions or clarifications about naming conventions, refer to this document or consult the development team.**
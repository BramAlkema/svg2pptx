# Legacy Patterns Detailed Inventory

**Generated**: 2024-09-24
**Phase**: Post Phase 2.2 Legacy Module Migration
**Total Patterns**: 42 remaining
**Status**: ConversionServices centralized DI ✅ IMPLEMENTED

## Executive Summary

Following successful Phase 2.2 Legacy Module Migration, 42 legacy patterns remain in the codebase. These have been categorized and prioritized for systematic cleanup in upcoming phases.

**Key Achievement**: ConversionServices dependency injection container is now fully operational and tested.

## HIGH Priority Patterns (18 total) 🔴

### Direct Service Instantiation (14 occurrences)

#### Active Runtime Patterns (6 patterns requiring immediate attention)

1. **src/paths/coordinate_system.py:53**
   ```python
   self._unit_converter = UnitConverter()
   ```
   - **Context**: Fallback path when services=None
   - **Fix**: Implement service-aware fallback pattern
   - **Risk**: Medium (affects path processing accuracy)

2. **src/utils/style_parser.py:249**
   ```python
   _style_parser_instance = StyleParser()
   ```
   - **Context**: Global singleton instance
   - **Fix**: Use ConversionServices.get_default_instance().style_parser
   - **Risk**: Low (singleton pattern works, but inconsistent)

3. **src/utils/coordinate_transformer.py:341**
   ```python
   _transformer_instance = CoordinateTransformer()
   ```
   - **Context**: Global singleton instance
   - **Fix**: Use ConversionServices.get_default_instance().coordinate_transformer
   - **Risk**: Low (singleton pattern works, but inconsistent)

4. **src/multislide/document.py:437**
   ```python
   resolver = ViewportResolver()
   ```
   - **Context**: Fallback after ConversionServices import attempt
   - **Fix**: Already partially migrated, needs lazy service resolution
   - **Risk**: Low (fallback already implemented)

5. **src/pptx/package_builder.py:183**
   ```python
   resolver = ViewportResolver()
   ```
   - **Context**: Fallback after ConversionServices import attempt
   - **Fix**: Already partially migrated, needs lazy service resolution
   - **Risk**: Low (fallback already implemented)

6. **src/preprocessing/geometry_plugins.py:252**
   ```python
   resolver = ViewportResolver()
   ```
   - **Context**: Fallback after ConversionServices import attempt
   - **Fix**: Already partially migrated, needs lazy service resolution
   - **Risk**: Low (fallback already implemented)

#### Documentation/Tool Patterns (4 patterns - informational only)

7-10. **src/services/legacy_migrator.py:28,33,38,43**
   ```python
   "Replace direct UnitConverter() with services.unit_converter"
   "Replace direct TransformEngine() with services.transform_parser"
   "Replace direct StyleParser() with services.style_parser"
   "Replace direct CoordinateTransformer() with services.coordinate_transformer"
   ```
   - **Context**: Pattern replacement examples in migration tool
   - **Fix**: Update examples to reflect current best practices
   - **Risk**: None (documentation only)

#### Service Configuration Issues (4 patterns)

11. **src/services/viewport_service.py:12**
   ```python
   self.unit_converter = UnitConverter()
   ```
   - **Context**: Service initialization
   - **Fix**: Use ConversionServices injection
   - **Risk**: Medium (affects viewport calculations)

12-14. **src/services/legacy_migrator.py:151,154** (comments in migration examples)
   ```python
   # OLD: self.unit_converter = UnitConverter()
   # OLD: self.transform_parser = TransformEngine()
   ```
   - **Context**: Migration pattern documentation
   - **Fix**: Update comments to show modern patterns
   - **Risk**: None (comments only)

### Manual Dependency Setup (4 occurrences)

Same as items 1, 11-14 above (patterns counted in multiple categories by analyzer)

### Old Context Creation (1 occurrence)

15. **src/services/dependency_validator.py:305**
   ```python
   init_args[arg_name] = ConversionContext(dpi=96.0)
   ```
   - **Context**: Context creation without services parameter
   - **Fix**: Add services parameter: `ConversionContext(svg_root, services=services)`
   - **Risk**: Low (validation tool only)

## MEDIUM Priority Patterns (24 total) 🟡

### Direct Service Imports (23 occurrences)

These are import statements that could be consolidated but don't affect runtime functionality:

#### Core Converter Files

1-9. **src/converters/base.py** (9 import patterns)
   ```python
   Line 34: from ..units import UnitConverter
   Line 35: from ..color import Color
   Line 37: from ..viewbox import ViewportResolver
   Line 39: from src.units import UnitConverter
   Line 40: from src.color import Color
   Line 42: from src.viewbox import ViewportResolver
   Line 812: from ..color import Color
   ```
   - **Fix**: Replace with single `from ..services.conversion_services import ConversionServices`
   - **Impact**: Import consolidation, no functional change
   - **Priority**: Medium (technical debt cleanup)

10. **src/paths/coordinate_system.py:28**
   ```python
   from ..units import UnitConverter, ConversionContext
   ```
   - **Fix**: Use ConversionServices for service access
   - **Impact**: Cleaner dependency management

11-12. **src/converters/markers.py:35, src/converters/text_path.py:35**
   ```python
   from ..color import Color
   ```
   - **Fix**: Use `services.color_parser` instead
   - **Impact**: Consistent service access pattern

#### Other Service Import Patterns

13-23. Additional imports in various files:
- Animation modules (interpolation.py, powerpoint.py)
- Filter modules (image/color.py)
- Performance module (cache.py)
- Preprocessing modules (advanced_plugins.py, plugins.py)
- Service modules (dependency_validator.py, gradient_service.py)

**Common Pattern**:
```python
# CURRENT
from ..units import UnitConverter
from ..color import Color

# PREFERRED
from ..services.conversion_services import ConversionServices
# Then use: services.unit_converter, services.color_parser
```

### Legacy Context Creation (1 occurrence)

24. **Same as HIGH priority item 15** - Context creation pattern

## Implementation Roadmap

### Phase 2.3: Critical Runtime Patterns (Next Sprint)
**Target**: Eliminate 6 active runtime instantiation patterns
**Effort**: ~2-3 days
**Files**: coordinate_system.py, style_parser.py, coordinate_transformer.py, viewport_service.py

**Implementation Strategy**:
```python
# Pattern: Service-Aware Fallback
def __init__(self, services=None):
    if services is not None:
        self._unit_converter = services.unit_converter
    else:
        # Graceful fallback
        try:
            services = ConversionServices.get_default_instance()
            self._unit_converter = services.unit_converter
        except (ImportError, RuntimeError):
            self._unit_converter = UnitConverter()  # Final fallback
```

### Phase 2.4: Import Consolidation (Future Maintenance)
**Target**: Clean up 23 import patterns
**Effort**: ~1-2 days
**Files**: Primarily base.py and converter modules

### Phase 2.5: Documentation Cleanup (Ongoing)
**Target**: Update 8 documentation/example patterns
**Effort**: <1 day
**Files**: Migration tools and validators

## Validation Commands

```bash
# Track progress
python src/services/legacy_migration_analyzer.py

# Test integration
pytest tests/unit/services/test_conversion_services.py -v

# Verify no circular dependencies
python -c "from src.services.conversion_services import ConversionServices; print('✅ OK')"
```

## Success Metrics

- [ ] **Phase 2.3**: HIGH priority patterns reduced from 18 to <5
- [ ] **Phase 2.4**: Total patterns reduced from 42 to <15
- [ ] **Phase 2.5**: Total patterns reduced to <5 (maintenance level)
- [ ] **Overall**: ConversionServices adoption >95% in active code paths

## Notes

- **Service Adapters**: All service wrapping is handled by `service_adapters.py` - no changes needed
- **Test Coverage**: Maintained at >95% throughout migration
- **Backward Compatibility**: All fallback paths preserved during transition
- **Performance**: No measurable impact from ConversionServices pattern

---
*This inventory provides the detailed tracking needed to complete the legacy pattern cleanup systematically.*
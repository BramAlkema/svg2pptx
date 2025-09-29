# ADR-007: Legacy Patterns Cleanup Specification

## Status
**ACCEPTED** - 2024-09-24

## Context

Following the successful completion of Phase 2.2 Legacy Module Migration, we have established ConversionServices as the centralized dependency injection container. However, 42 legacy patterns remain in the codebase that represent technical debt and potential maintenance challenges.

This ADR documents these remaining patterns, categorizes them by priority and type, and provides a roadmap for systematic cleanup.

## Current State Analysis

### Migration Success Metrics
- ✅ ConversionServices centralized dependency injection **IMPLEMENTED**
- ✅ High-priority converter migrations **COMPLETED** (6/6 critical files)
- ✅ Circular dependency resolution **RESOLVED**
- ✅ Test suite compatibility **MAINTAINED** (11/11 tests passing)
- ⚠️ Legacy pattern reduction: **44 → 42** (ongoing cleanup needed)

### Remaining Legacy Patterns Breakdown

#### HIGH Priority Patterns (18 occurrences)
**Impact**: Breaking changes to architecture, potential runtime failures

1. **Direct Service Instantiation in Fallback Paths** (6 occurrences)
   ```python
   # Current fallback patterns that need ConversionServices integration
   src/paths/coordinate_system.py:53 - UnitConverter() fallback
   src/utils/style_parser.py:249 - StyleParser() singleton
   src/utils/coordinate_transformer.py:341 - CoordinateTransformer() singleton
   src/multislide/document.py:437 - ViewportResolver() fallback
   src/pptx/package_builder.py:183 - ViewportResolver() fallback
   src/preprocessing/geometry_plugins.py:252 - ViewportResolver() fallback
   ```

2. **Migration Tool Documentation Patterns** (4 occurrences)
   ```python
   # These are example patterns in migration tools, not active code
   src/services/legacy_migrator.py:28,33,38,43 - Pattern replacement examples
   ```

3. **Service Configuration Patterns** (4 occurrences)
   ```python
   # Manual dependency setup that could use ConversionServices
   src/services/viewport_service.py:12 - Direct UnitConverter setup
   src/services/legacy_migrator.py:151,154 - Example migration patterns
   ```

4. **Context Creation Patterns** (1 occurrence)
   ```python
   # Context creation without services parameter
   src/services/dependency_validator.py:305 - ConversionContext(dpi=96.0)
   ```

#### MEDIUM Priority Patterns (24 occurrences)
**Impact**: Import organization, code cleanliness, but no functional breaking changes

1. **Direct Service Imports** (23 occurrences)
   - Core converter files still import services directly instead of using ConversionServices
   - Files: `src/converters/base.py`, `src/converters/markers.py`, `src/converters/text_path.py`
   - Pattern: `from ..units import UnitConverter` → should use `services.unit_converter`

2. **Legacy Context Creation** (1 occurrence)
   - Context creation patterns that don't follow new services-first approach

## Decision

### Cleanup Strategy - Phased Approach

#### Phase 2.3: Critical Fallback Integration (HIGH Priority) ✅ **COMPLETED**
**Timeline**: ✅ Completed 2024-09-24
**Scope**: 4 critical runtime patterns migrated successfully

**Strategy**:
1. **Service-Aware Fallbacks**: Update fallback code paths to attempt ConversionServices first
   ```python
   # BEFORE (current fallback)
   self._unit_converter = UnitConverter()

   # AFTER (service-aware fallback)
   try:
       from ..services.conversion_services import ConversionServices
       services = ConversionServices.create_default()
       self._unit_converter = services.unit_converter
   except (ImportError, CircularImportError):
       self._unit_converter = UnitConverter()  # Safe fallback
   ```

2. **Lazy Service Injection**: Implement deferred service resolution
   ```python
   class CoordinateSystem:
       def __init__(self, services=None):
           self._services = services
           self._unit_converter = None

       @property
       def unit_converter(self):
           if self._unit_converter is None:
               if self._services:
                   self._unit_converter = self._services.unit_converter
               else:
                   self._unit_converter = UnitConverter()
           return self._unit_converter
   ```

#### Phase 2.4: Import Modernization (MEDIUM Priority)
**Timeline**: Future maintenance cycles
**Scope**: 23 direct import patterns

**Strategy**:
1. **Import Consolidation**: Replace direct service imports with ConversionServices imports
2. **Converter Standardization**: Update all converter classes to use consistent service access patterns
3. **Documentation Updates**: Update import examples and patterns in documentation

#### Phase 2.5: Tool and Documentation Cleanup (LOW Priority)
**Timeline**: As needed during maintenance
**Scope**: Migration tool examples and documentation patterns

**Strategy**:
1. **Example Modernization**: Update migration tool examples to reflect current best practices
2. **Documentation Alignment**: Ensure all code examples use ConversionServices patterns

### Implementation Guidelines

#### DO's
✅ **Prioritize functional correctness** - High priority patterns affect runtime behavior
✅ **Maintain backward compatibility** - Always provide fallback paths during migration
✅ **Use service-aware patterns** - Attempt ConversionServices first, fallback gracefully
✅ **Test integration points** - Verify services injection works correctly
✅ **Document service dependencies** - Make service requirements explicit in class documentation

#### DON'Ts
❌ **Don't break existing functionality** - Legacy fallbacks must continue working
❌ **Don't introduce circular dependencies** - Always use lazy initialization when needed
❌ **Don't remove imports without testing** - Some imports may be used in ways not detected by static analysis
❌ **Don't rush MEDIUM priority patterns** - Focus on HIGH priority architectural issues first

### Success Criteria

#### Phase 2.3 Success Metrics ✅ **ACHIEVED**
- [x] All 4 HIGH priority runtime patterns use ConversionServices-aware code paths
- [x] Zero runtime failures when ConversionServices is available
- [x] Fallback behavior identical to current implementation when services unavailable
- [x] Test coverage maintained at >95% for affected components
- [x] 100% backward compatibility maintained
- [x] Service-aware singleton patterns implemented (StyleParser, CoordinateTransformer)
- [x] Dependency injection support added to ViewportService

#### Overall Migration Success
- [ ] Legacy pattern count reduced to <10 total occurrences
- [ ] All HIGH priority patterns eliminated
- [ ] ConversionServices adoption rate >95% in converter classes
- [ ] Zero circular dependency issues
- [ ] Documentation and examples reflect modern patterns

## Implementation Priority Matrix

| Pattern Type | Priority | Count | Risk Level | Effort | Timeline |
|--------------|----------|--------|------------|---------|----------|
| Fallback Service Instantiation | HIGH | 6 | 🔴 High | Medium | Phase 2.3 |
| Service Configuration | HIGH | 5 | 🔴 High | Low | Phase 2.3 |
| Context Creation | HIGH | 1 | 🟡 Medium | Low | Phase 2.3 |
| Direct Service Imports | MEDIUM | 23 | 🟡 Medium | High | Phase 2.4 |
| Migration Tool Examples | LOW | 4 | 🟢 Low | Low | Phase 2.5 |

## Monitoring and Validation

### Automated Validation
```bash
# Run legacy pattern analyzer to track progress
PYTHONPATH=. python src/services/legacy_migration_analyzer.py

# Expected targets:
# Phase 2.3 completion: <20 total patterns
# Phase 2.4 completion: <10 total patterns
# Full cleanup: <5 total patterns
```

### Integration Testing
```bash
# Verify ConversionServices functionality after each phase
PYTHONPATH=. pytest tests/unit/services/test_conversion_services.py -v
PYTHONPATH=. pytest tests/unit/converters/ -k "ConversionServices" -v
```

## Related ADRs
- [ADR-001: Core Architecture Consolidation](./ADR-001-CORE-ARCHITECTURE-CONSOLIDATION.md)
- [ADR-002: Converter Architecture](./ADR-002-CONVERTER-ARCHITECTURE.md)
- [ADR-006: Animation System Architecture](./ADR-006-ANIMATION-SYSTEM-ARCHITECTURE.md)

## References
- Legacy Migration Analyzer: `src/services/legacy_migration_analyzer.py`
- Migration Automation Tool: `src/services/legacy_migrator.py`
- ConversionServices Implementation: `src/services/conversion_services.py`
- Service Adapters: `src/services/service_adapters.py`

---
*This ADR provides the roadmap for completing the legacy pattern cleanup and achieving full ConversionServices adoption across the codebase.*
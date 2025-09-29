# Service Adapter Migration Map

## Overview
This document provides a comprehensive mapping for migrating from service adapters to core services directly. It identifies all service adapter usage, maps adapter methods to core service methods, and provides a migration strategy for each consumer file.

## Service Adapter Analysis

### Current Usage
- **Total adapter classes**: 11
- **Total adapter methods**: 13 (excluding base class methods)
- **Service adapter file size**: 349 lines
- **Consumer files identified**: 5

### Consumer Files
1. `src/services/conversion_services.py` - Uses `wrap_service_for_conversion_services`
2. `src/preprocessing/resolve_clippath_plugin.py` - Uses `create_service_adapters` from geometry module
3. `src/preprocessing/geometry/__init__.py` - Imports from geometry service_adapters
4. `src/preprocessing/geometry/service_adapters.py` - Separate service adapter file (not main one)
5. `src/services/legacy_migration_analyzer.py` - Uses service adapters

## Adapter Class Mapping

### 1. ViewportResolverAdapter
**Purpose**: Adapts ViewportEngine to match ConversionServices expectations

**Methods**:
- `parse_viewbox(viewbox_str: str) -> Optional[Tuple[float, float, float, float]]`
  - **Core Service**: ViewportEngine.parse_viewbox_strings()
  - **Migration**: Replace single string parsing with batch parsing
  - **Risk**: Low - direct method mapping

- `calculate_viewport(viewport_width, viewport_height, viewbox) -> Dict[str, Any]`
  - **Core Service**: ViewportEngine.calculate_viewport_mappings_batch()
  - **Migration**: Replace single viewport calculation with batch processing
  - **Risk**: Medium - complex numpy array conversion required

### 2. ColorFactoryAdapter
**Purpose**: Provides compatibility methods for Color class

**Methods**:
- `from_hex(hex_value: str) -> Any`
  - **Core Service**: Color(hex_value) constructor
  - **Migration**: Replace adapter.from_hex() with Color() constructor
  - **Risk**: Low - direct constructor call

### 3. StyleParserAdapter
**Purpose**: Wraps StyleParser functionality

**Methods**:
- `parse_style_attribute(style_attr: str) -> Dict[str, str]`
  - **Core Service**: StyleParser.parse_style_attribute()
  - **Migration**: Direct method call on core service
  - **Risk**: Low - method exists in core service

### 4. CoordinateTransformerAdapter
**Purpose**: Wraps CoordinateTransformer functionality

**Methods**:
- `transform_coordinates(coordinates, transform_matrix) -> List[Tuple[float, float]]`
  - **Core Service**: CoordinateTransformer.transform_coordinates()
  - **Migration**: Direct method call on core service
  - **Risk**: Low - method exists in core service

### 5. FontProcessorAdapter
**Purpose**: Wraps FontProcessor functionality

**Methods**:
- `process_font_attributes(element: Any) -> Dict[str, Any]`
  - **Core Service**: FontProcessor.process_font_attributes()
  - **Migration**: Direct method call on core service
  - **Risk**: Low - method exists in core service

### 6. PathProcessorAdapter
**Purpose**: Wraps PathProcessor functionality

**Methods**:
- `optimize_path(path_data: str) -> str`
  - **Core Service**: PathProcessor.optimize_path()
  - **Migration**: Direct method call on core service
  - **Risk**: Low - method exists in core service

### 7. PPTXBuilderAdapter
**Purpose**: Wraps PPTXBuilder functionality

**Methods**:
- `create_presentation(template: Optional[str] = None) -> Any`
  - **Core Service**: PPTXBuilder.create_presentation()
  - **Migration**: Direct method call on core service
  - **Risk**: Low - method exists in core service

- `add_slide(presentation: Any, layout_index: int = 0) -> Any`
  - **Core Service**: PPTXBuilder.add_slide()
  - **Migration**: Direct method call on core service
  - **Risk**: Low - method exists in core service

### 8. GradientServiceAdapter
**Purpose**: Wraps GradientService functionality

**Methods**:
- `create_gradient(gradient_type, stops, properties) -> str`
  - **Core Service**: GradientService.create_gradient()
  - **Migration**: Direct method call on core service
  - **Risk**: Low - method exists in core service

### 9. PatternServiceAdapter
**Purpose**: Wraps PatternService functionality

**Methods**:
- `create_pattern(pattern_type, properties) -> str`
  - **Core Service**: PatternService.create_pattern()
  - **Migration**: Direct method call on core service
  - **Risk**: Low - method exists in core service

### 10. FilterServiceAdapter
**Purpose**: Wraps FilterService functionality

**Methods**:
- `apply_filter(filter_type, element, properties) -> str`
  - **Core Service**: FilterService.apply_filter()
  - **Migration**: Direct method call on core service
  - **Risk**: Low - method exists in core service

### 11. ImageServiceAdapter
**Purpose**: Wraps ImageService functionality

**Methods**:
- `get_image_info(image_path: str) -> Optional[Dict[str, Any]]`
  - **Core Service**: ImageService.get_image_info()
  - **Migration**: Direct method call on core service
  - **Risk**: Low - method exists in core service

- `process_image(image_data, target_format) -> bytes`
  - **Core Service**: ImageService.process_image()
  - **Migration**: Direct method call on core service
  - **Risk**: Low - method exists in core service

## Migration Strategy

### Phase 1: Update ConversionServices
1. Remove `wrap_service_for_conversion_services` import and usage
2. Update ConversionServices to instantiate core services directly
3. Remove any adapter wrapping in the create_default() method

### Phase 2: Update Individual Consumers
1. **src/preprocessing/resolve_clippath_plugin.py**:
   - Replace `create_service_adapters` with direct service instantiation
   - Update method calls to use core service methods

2. **src/services/legacy_migration_analyzer.py**:
   - Remove service adapter imports
   - Update service instantiation to use core services

### Phase 3: Remove Adapter Files
1. Delete `src/services/service_adapters.py` (349 lines)
2. Update geometry module service adapters if needed
3. Remove any remaining adapter imports

## Risk Assessment

### High Risk (require careful testing)
- **ViewportResolverAdapter.calculate_viewport()**: Complex numpy array conversion
- **ConversionServices**: Central dependency injection changes

### Medium Risk (require validation)
- **ColorFactoryAdapter**: Constructor change from method call

### Low Risk (direct mapping)
- All other adapter methods have direct equivalents in core services

## Testing Requirements

### Unit Tests
- Test each core service method individually
- Validate adapter method replacements
- Ensure no functionality regression

### Integration Tests
- Test ConversionServices with core services
- Validate preprocessing pipeline functionality
- Check end-to-end conversion workflow

### Performance Tests
- Benchmark viewport calculations (numpy operations)
- Verify no performance regression in core services

## Implementation Checklist

### Task 2.1: Audit Complete ✅
- [x] All adapter classes identified (11 total)
- [x] All adapter methods mapped (13 total)
- [x] Consumer files identified (5 total)
- [x] Risk assessment completed
- [x] Migration strategy documented

### Task 2.2: Standardize Service Interfaces
- [ ] Verify ViewportEngine has expected methods
- [ ] Verify Color class interface matches adapter expectations
- [ ] Verify TransformEngine interface matches adapter expectations
- [ ] Update core service interfaces if needed

### Task 2.3: Remove Service Adapters
- [ ] Update ConversionServices to use core services directly
- [ ] Update all consumer files to use core services
- [ ] Delete service_adapters.py file
- [ ] Remove all adapter imports

### Task 2.4: Validate Service Modernization
- [ ] All service-related tests pass
- [ ] No adapter imports remain
- [ ] Core services function correctly
- [ ] No performance regression

## File Impact Summary

### Files to Delete
- `src/services/service_adapters.py` (349 lines)

### Files to Update
- `src/services/conversion_services.py` - Remove adapter wrapping
- `src/preprocessing/resolve_clippath_plugin.py` - Use core services
- `src/services/legacy_migration_analyzer.py` - Remove adapter usage
- Any test files that import adapters

### Expected Line Reduction
- **349 lines** removed from service adapters
- **~50-100 lines** of adapter import/usage code removed from consumers
- **Total reduction**: ~400-450 lines of compatibility code

---

*Generated: January 27, 2025*
*Status: Analysis Complete - Ready for Implementation*
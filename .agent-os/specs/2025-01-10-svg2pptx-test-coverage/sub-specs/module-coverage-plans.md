# Module Coverage Plans

This document provides detailed coverage implementation plans for each target module in the spec detailed in @.agent-os/specs/2025-01-10-svg2pptx-test-coverage/spec.md

> Created: 2025-01-10
> Version: 1.0.0

## Coverage Implementation Roadmap

### Phase 1: Zero-Coverage Modules (Weeks 1-2)

#### Module 1: converters/masking.py (0.0% → 95%+ coverage)

**Estimated Implementation Time**: 3-4 days

##### Code Analysis Requirements
```python
# Expected module structure analysis
class MaskConverter(BaseConverter):
    def process_mask_element(self, mask_element, slide):
        """Process SVG mask elements"""
        pass
    
    def apply_clipping_path(self, clip_path, shape):
        """Apply clipping path to PowerPoint shape"""
        pass
    
    def calculate_opacity_inheritance(self, element):
        """Calculate inherited opacity values"""
        pass
```

##### Test Implementation Plan
1. **Test File Creation**: `tests/test_masking.py`
2. **Required Fixtures**:
   ```python
   @pytest.fixture
   def mask_converter():
       return MaskConverter()
   
   @pytest.fixture
   def mock_slide():
       return Mock(spec=Slide)
   
   @pytest.fixture
   def sample_mask_elements():
       """Create comprehensive mask element samples"""
       return {
           'basic_mask': create_mask_element(id="mask1"),
           'complex_clip_path': create_clip_path_element(d="M10,10 L50,50"),
           'nested_opacity': create_nested_opacity_elements()
       }
   ```

3. **Test Categories** (targeting 95%+ coverage):
   - **Element Parsing Tests** (20% of coverage):
     - `test_parse_mask_element_success()`
     - `test_parse_mask_element_invalid_attributes()`
     - `test_parse_clip_path_element()`
     - `test_parse_nested_mask_elements()`
   
   - **Algorithm Tests** (40% of coverage):
     - `test_clipping_path_calculation_linear()`
     - `test_clipping_path_calculation_curved()`
     - `test_opacity_inheritance_single_level()`
     - `test_opacity_inheritance_multi_level()`
     - `test_mask_bounds_calculation()`
   
   - **PowerPoint Integration Tests** (25% of coverage):
     - `test_apply_mask_to_shape_success()`
     - `test_apply_clipping_to_shape()`
     - `test_mask_powerpoint_coordinate_conversion()`
   
   - **Error Handling Tests** (15% of coverage):
     - `test_invalid_mask_reference_handling()`
     - `test_missing_clip_path_handling()`
     - `test_malformed_path_data_handling()`

##### Success Metrics
- **Line Coverage**: 95%+ (targeting ~143/150 lines)
- **Branch Coverage**: 90%+ for conditional logic
- **Test Count**: 15-20 comprehensive tests
- **Execution Time**: <30 seconds

#### Module 2: converters/text_path.py (0.0% → 95%+ coverage)

**Estimated Implementation Time**: 4-5 days

##### Code Analysis Requirements
```python
# Expected module structure analysis
class TextPathConverter(BaseConverter):
    def process_text_path(self, text_path_element, slide):
        """Process textPath elements"""
        pass
    
    def calculate_text_position_along_path(self, text, path):
        """Calculate text positioning along curved paths"""
        pass
    
    def apply_text_orientation(self, text_shape, path_angle):
        """Apply text orientation based on path direction"""
        pass
```

##### Test Implementation Plan
1. **Test File Creation**: `tests/test_text_path.py`
2. **Required Fixtures**:
   ```python
   @pytest.fixture
   def text_path_converter():
       return TextPathConverter()
   
   @pytest.fixture
   def sample_paths():
       """Create various path types for testing"""
       return {
           'straight_line': "M0,0 L100,0",
           'curved_path': "M0,0 Q50,50 100,0", 
           'complex_path': "M0,0 C25,25 75,25 100,0 S150,-25 200,0"
       }
   
   @pytest.fixture
   def sample_text_elements():
       """Create text elements with various content"""
       return {
           'simple_text': "Hello World",
           'unicode_text': "こんにちは世界",
           'special_chars': "Text with special chars: @#$%"
       }
   ```

3. **Test Categories** (targeting 95%+ coverage):
   - **Path Processing Tests** (35% of coverage):
     - `test_parse_path_data_linear()`
     - `test_parse_path_data_curved()`
     - `test_parse_path_data_complex()`
     - `test_calculate_path_length()`
     - `test_get_point_at_distance()`
   
   - **Text Positioning Tests** (30% of coverage):
     - `test_position_text_along_straight_path()`
     - `test_position_text_along_curved_path()`
     - `test_text_spacing_calculation()`
     - `test_text_alignment_along_path()`
   
   - **Orientation Tests** (20% of coverage):
     - `test_calculate_text_angle_at_position()`
     - `test_apply_text_rotation()`
     - `test_text_orientation_smooth_curves()`
   
   - **Integration Tests** (15% of coverage):
     - `test_full_text_path_conversion()`
     - `test_text_path_powerpoint_output()`
     - `test_unicode_text_path_handling()`

##### Success Metrics
- **Line Coverage**: 95%+ (targeting ~190/200 lines)
- **Branch Coverage**: 90%+ for path processing logic
- **Test Count**: 18-22 comprehensive tests
- **Execution Time**: <45 seconds

### Phase 2: Low-Coverage Enhancement (Weeks 3-4)

#### Module 3: converters/gradients.py (11.5% → 95%+ coverage)

**Estimated Implementation Time**: 3-4 days

##### Current Coverage Analysis
```bash
# Identify existing test coverage
pytest --cov=converters.gradients --cov-report=term-missing tests/test_gradients.py

# Expected output shows current ~29/250 lines covered
# Gap analysis needed for:
# - Lines 45-87: Linear gradient angle calculations
# - Lines 120-165: Radial gradient processing
# - Lines 180-220: Color stop interpolation
# - Lines 235-250: Transformation matrix operations
```

##### Test Enhancement Plan
1. **Extend Existing Test File**: `tests/test_gradients.py`
2. **New Test Categories** (targeting 83.5% additional coverage):
   - **Linear Gradient Enhancement** (25% new coverage):
     - `test_linear_gradient_angle_calculation_0_to_360()`
     - `test_linear_gradient_direction_vector_calculation()`
     - `test_linear_gradient_coordinate_mapping()`
   
   - **Radial Gradient Enhancement** (25% new coverage):
     - `test_radial_gradient_center_point_calculation()`
     - `test_radial_gradient_radius_calculation()`
     - `test_radial_gradient_focal_point_handling()`
   
   - **Color Processing Enhancement** (20% new coverage):
     - `test_color_stop_position_parsing()`
     - `test_color_interpolation_algorithms()`
     - `test_gradient_opacity_handling()`
   
   - **Transformation Enhancement** (13.5% new coverage):
     - `test_gradient_transformation_matrix_application()`
     - `test_gradient_coordinate_system_conversion()`

##### Success Metrics
- **Line Coverage**: 95%+ (targeting ~238/250 lines)
- **Improvement**: +83.5% coverage increase
- **New Tests**: 12-15 additional tests
- **Regression**: 0% loss in existing coverage

#### Module 4: converters/styles.py (13.5% → 95%+ coverage)

**Estimated Implementation Time**: 4-5 days

##### Current Coverage Analysis
```bash
# Expected coverage gaps:
# - Lines 25-95: CSS parsing algorithms
# - Lines 110-180: Style inheritance logic
# - Lines 195-245: Style conflict resolution
# - Lines 260-300: Style caching mechanisms
```

##### Test Enhancement Plan
1. **Extend Existing Test File**: `tests/test_styles.py`
2. **New Test Categories** (targeting 81.5% additional coverage):
   - **CSS Parsing Enhancement** (30% new coverage):
     - `test_parse_complex_css_selectors()`
     - `test_parse_css_shorthand_properties()`
     - `test_parse_css_color_values_all_formats()`
     - `test_parse_css_units_and_measurements()`
   
   - **Inheritance Logic Enhancement** (25% new coverage):
     - `test_style_inheritance_cascade_rules()`
     - `test_style_specificity_calculation()`
     - `test_inherited_vs_computed_styles()`
   
   - **Conflict Resolution Enhancement** (15% new coverage):
     - `test_style_priority_resolution()`
     - `test_important_declaration_handling()`
     - `test_inline_vs_stylesheet_priority()`
   
   - **Performance Enhancement** (11.5% new coverage):
     - `test_style_caching_mechanisms()`
     - `test_style_optimization_paths()`

##### Success Metrics
- **Line Coverage**: 95%+ (targeting ~285/300 lines)
- **Improvement**: +81.5% coverage increase
- **New Tests**: 14-18 additional tests
- **Performance**: Maintain or improve style processing speed

### Phase 3: Moderate Coverage Optimization (Week 5)

#### Module 5: converters/filters.py (36.1% → 95%+ coverage)

**Estimated Implementation Time**: 3-4 days

##### Current Coverage Analysis
```bash
# Expected covered: ~144/400 lines
# Major gaps:
# - Lines 50-120: Complex filter effect algorithms
# - Lines 150-220: Filter chaining and composition
# - Lines 250-320: Filter coordinate transformations
# - Lines 350-400: Filter optimization and caching
```

##### Test Enhancement Plan
1. **Enhance Existing Test File**: `tests/test_filters.py`
2. **New Test Categories** (targeting 58.9% additional coverage):
   - **Filter Effects Enhancement** (20% new coverage):
     - `test_blur_filter_algorithm_implementation()`
     - `test_drop_shadow_filter_positioning()`
     - `test_color_matrix_filter_calculations()`
     - `test_composite_filter_blend_modes()`
   
   - **Filter Chain Enhancement** (20% new coverage):
     - `test_multi_filter_chain_processing()`
     - `test_filter_input_output_connections()`
     - `test_filter_chain_optimization()`
   
   - **Coordinate System Enhancement** (10% new coverage):
     - `test_filter_coordinate_space_transformations()`
     - `test_filter_units_and_scaling()`
   
   - **Performance Enhancement** (8.9% new coverage):
     - `test_filter_result_caching()`
     - `test_filter_performance_optimization_paths()`

##### Success Metrics
- **Line Coverage**: 95%+ (targeting ~380/400 lines)
- **Improvement**: +58.9% coverage increase
- **New Tests**: 12-16 additional tests
- **Performance**: Optimize filter processing pipeline

## Implementation Timeline and Milestones

### Week 1: Foundation (masking.py)
- **Day 1-2**: Code analysis and test structure setup
- **Day 3-4**: Core algorithm tests implementation
- **Day 5**: Integration tests and coverage validation

### Week 2: Algorithms (text_path.py)  
- **Day 1-2**: Path processing tests
- **Day 3-4**: Text positioning and orientation tests
- **Day 5**: Complex scenario and edge case tests

### Week 3: Enhancement Phase 1 (gradients.py)
- **Day 1-2**: Gap analysis and linear gradient tests
- **Day 3-4**: Radial gradient and color processing tests
- **Day 5**: Transformation and integration tests

### Week 4: Enhancement Phase 2 (styles.py)
- **Day 1-2**: CSS parsing enhancement tests
- **Day 3-4**: Inheritance and conflict resolution tests
- **Day 5**: Performance and caching tests

### Week 5: Optimization (filters.py)
- **Day 1-2**: Filter effects and algorithm tests
- **Day 3-4**: Filter chaining and coordinate system tests
- **Day 5**: Performance optimization and final validation

## Risk Mitigation and Contingency Plans

### High-Risk Areas
1. **Complex Algorithms**: text_path.py path following logic
   - **Mitigation**: Break into smaller, testable functions
   - **Contingency**: Use property-based testing with hypothesis

2. **Mock Complexity**: PowerPoint API interactions
   - **Mitigation**: Create reusable mock factories
   - **Contingency**: Use real PowerPoint objects in integration tests

3. **Performance Impact**: Comprehensive test execution time
   - **Mitigation**: Use pytest-xdist for parallel execution
   - **Contingency**: Mark slow tests for optional execution

### Success Validation Strategy
- **Daily Coverage Checks**: Monitor progress with coverage reports
- **Weekly Integration Testing**: Ensure no regression in existing functionality
- **Performance Benchmarking**: Track test execution time increases
- **Code Quality Metrics**: Maintain or improve complexity scores
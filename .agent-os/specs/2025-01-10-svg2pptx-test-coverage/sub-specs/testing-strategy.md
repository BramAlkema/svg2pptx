# Testing Strategy

This is the detailed testing strategy for the spec detailed in @.agent-os/specs/2025-01-10-svg2pptx-test-coverage/spec.md

> Created: 2025-01-10
> Version: 1.0.0

## Overall Testing Philosophy

### Proven Success Pattern (from animations.py & markers.py)
The testing strategy builds upon the proven success of animations.py (93.6% coverage) and markers.py (98.2% coverage) post-lxml migration. These modules demonstrate the effectiveness of:

1. **lxml-first approach**: All XML processing using lxml.etree
2. **Comprehensive mocking**: Isolate converter logic from PowerPoint API dependencies
3. **Parent-child XML relationships**: Proper element hierarchy using ET.SubElement()
4. **Abstract method implementation**: Make abstract converters testable through inheritance

### Testing Pyramid Implementation

#### Unit Tests (80% of coverage effort)
- **Scope**: Individual converter methods and functions
- **Focus**: Algorithm correctness, edge cases, error handling
- **Mocking**: Heavy use of mocks for PowerPoint API and dependencies
- **Pattern**: One test class per converter module

#### Integration Tests (15% of coverage effort)
- **Scope**: Converter interactions with base framework
- **Focus**: End-to-end conversion workflows
- **Mocking**: Minimal mocking, real XML parsing with mock PowerPoint output
- **Pattern**: Cross-module interaction testing

#### System Tests (5% of coverage effort)
- **Scope**: Full SVG to PowerPoint conversion scenarios
- **Focus**: Complex multi-element SVG documents
- **Mocking**: Mock only external file system and PowerPoint save operations
- **Pattern**: Full workflow validation

## Module-Specific Testing Strategies

### 1. masking.py (0.0% → 95%+ coverage)

#### Current State Analysis
- **Lines of Code**: ~150 lines (estimated)
- **Complexity**: High (path clipping algorithms, opacity calculations)
- **Dependencies**: Base converter, path processing, PowerPoint shape operations

#### Testing Approach: Complete Ground-Up Coverage
```python
class TestMaskConverter:
    """Comprehensive test suite for masking.py converter"""
    
    @pytest.fixture
    def mask_converter(self):
        return MaskConverter()
    
    @pytest.fixture
    def sample_mask_element(self):
        """Create sample SVG mask element with lxml"""
        mask = ET.Element("{http://www.w3.org/2000/svg}mask")
        mask.set("id", "mask1")
        mask.set("maskUnits", "objectBoundingBox")
        return mask
    
    def test_mask_parsing_success(self, mask_converter, sample_mask_element):
        """Test successful mask element parsing"""
        # Test core parsing functionality
        
    def test_clip_path_processing(self, mask_converter):
        """Test clipping path algorithm implementation"""
        # Test path-based clipping logic
        
    def test_opacity_calculations(self, mask_converter):
        """Test opacity inheritance and calculation"""
        # Test opacity handling edge cases
        
    def test_powerpoint_mask_application(self, mask_converter, mock_slide):
        """Test PowerPoint mask application with mocked slide"""
        # Mock PowerPoint shape operations
```

#### Coverage Targets:
- **Path Processing**: 100% coverage of clipping path algorithms
- **Opacity Handling**: All opacity calculation branches
- **Error Handling**: Invalid mask elements, missing attributes
- **Integration**: Interaction with base converter methods

### 2. text_path.py (0.0% → 95%+ coverage)

#### Current State Analysis
- **Lines of Code**: ~200 lines (estimated)
- **Complexity**: Very High (path following algorithms, text positioning)
- **Dependencies**: Path processing, text metrics, coordinate transformations

#### Testing Approach: Algorithm-Focused Coverage
```python
class TestTextPathConverter:
    """Comprehensive test suite for text_path.py converter"""
    
    @pytest.fixture
    def text_path_converter(self):
        return TextPathConverter()
    
    @pytest.fixture
    def sample_text_path(self):
        """Create sample textPath element with lxml"""
        text_path = ET.Element("{http://www.w3.org/2000/svg}textPath")
        text_path.set("href", "#path1")
        text_path.text = "Sample text along path"
        return text_path
    
    def test_path_following_algorithm(self, text_path_converter):
        """Test text positioning along curved paths"""
        # Test core path following logic
        
    def test_text_orientation_calculation(self, text_path_converter):
        """Test text rotation and orientation along paths"""
        # Test text angle calculations
        
    def test_unicode_text_handling(self, text_path_converter):
        """Test complex character support in path text"""
        # Test unicode and special character handling
```

#### Coverage Targets:
- **Path Following**: 100% coverage of positioning algorithms
- **Text Metrics**: All text measurement and spacing calculations
- **Coordinate Systems**: Path coordinate transformations
- **Edge Cases**: Empty paths, invalid path references

### 3. gradients.py (11.5% → 95%+ coverage)

#### Current State Analysis
- **Existing Tests**: Basic gradient creation tests (partial coverage)
- **Gaps**: Complex gradient algorithms, color interpolation, transformations
- **Lines of Code**: ~250 lines (estimated)

#### Testing Approach: Gap Analysis and Enhancement
```python
class TestGradientConverter:
    """Enhanced test suite for gradients.py converter"""
    
    # Extend existing test patterns
    def test_linear_gradient_angle_calculation(self, gradient_converter):
        """Test linear gradient angle processing - NEW"""
        # Cover angle calculation algorithms
        
    def test_radial_gradient_center_calculation(self, gradient_converter):
        """Test radial gradient center point processing - NEW"""
        # Cover center point and radius calculations
        
    def test_color_stop_interpolation(self, gradient_converter):
        """Test gradient color interpolation algorithms - NEW"""
        # Cover color blending and interpolation
        
    def test_gradient_transformation_matrix(self, gradient_converter):
        """Test gradient coordinate transformations - NEW"""
        # Cover transformation matrix applications
```

#### Coverage Targets:
- **Linear Gradients**: Angle calculations, direction vectors
- **Radial Gradients**: Center point, radius, and focal point processing
- **Color Stops**: Stop position parsing and color interpolation
- **Transformations**: Matrix-based coordinate transformations

### 4. styles.py (13.5% → 95%+ coverage)

#### Current State Analysis
- **Existing Tests**: Basic style parsing tests (minimal coverage)
- **Gaps**: CSS cascade logic, style inheritance, conflict resolution
- **Lines of Code**: ~300 lines (estimated)

#### Testing Approach: Systematic Path Coverage
```python
class TestStyleConverter:
    """Enhanced test suite for styles.py converter"""
    
    def test_css_style_parsing_complex(self, style_converter):
        """Test complex CSS style string parsing - NEW"""
        # Cover advanced CSS parsing scenarios
        
    def test_style_inheritance_cascade(self, style_converter):
        """Test style inheritance and cascade rules - NEW"""
        # Cover CSS cascade algorithm
        
    def test_style_conflict_resolution(self, style_converter):
        """Test style priority and override handling - NEW"""
        # Cover style conflict resolution logic
        
    def test_style_caching_optimization(self, style_converter):
        """Test style caching and performance optimization - NEW"""
        # Cover caching and optimization paths
```

#### Coverage Targets:
- **CSS Parsing**: Complex style string tokenization and parsing
- **Inheritance**: Style cascade and inheritance rule implementation
- **Performance**: Style caching and optimization mechanisms
- **Error Handling**: Malformed CSS, invalid properties

### 5. filters.py (36.1% → 95%+ coverage)

#### Current State Analysis
- **Existing Tests**: Basic filter tests (moderate coverage)
- **Gaps**: Complex filter effects, filter chaining, performance paths
- **Lines of Code**: ~400 lines (estimated)

#### Testing Approach: Enhancement and Optimization
```python
class TestFilterConverter:
    """Enhanced test suite for filters.py converter"""
    
    # Build upon existing tests
    def test_complex_filter_effects(self, filter_converter):
        """Test advanced filter effect implementations - ENHANCED"""
        # Cover complex filter algorithms
        
    def test_filter_chain_composition(self, filter_converter):
        """Test multi-filter chain processing - NEW"""
        # Cover filter chaining logic
        
    def test_filter_coordinate_systems(self, filter_converter):
        """Test filter coordinate space transformations - NEW"""
        # Cover coordinate system handling
        
    def test_filter_performance_optimization(self, filter_converter):
        """Test filter optimization and caching - NEW"""
        # Cover performance-critical paths
```

#### Coverage Targets:
- **Filter Primitives**: Individual filter effect implementations
- **Filter Chains**: Complex multi-filter composition logic
- **Coordinate Systems**: Filter coordinate space transformations
- **Performance**: Filter optimization and caching mechanisms

## Cross-Cutting Testing Concerns

### Error Handling Strategy
Every module must include comprehensive error handling tests:

```python
def test_invalid_svg_element_handling(self, converter):
    """Test graceful handling of invalid SVG elements"""
    invalid_element = ET.Element("invalid")
    with pytest.raises(ExpectedExceptionType):
        converter.convert_element(invalid_element, mock_slide)

def test_missing_required_attributes(self, converter):
    """Test handling of missing required attributes"""
    # Test each required attribute missing scenario

def test_malformed_attribute_values(self, converter):
    """Test handling of malformed attribute values"""
    # Test invalid attribute value scenarios
```

### Performance Testing Integration
For complex algorithms (gradients, filters, text paths):

```python
@pytest.mark.performance
def test_algorithm_performance_baseline(self, converter):
    """Establish performance baseline for complex algorithms"""
    # Use pytest-benchmark for performance regression detection
```

### Property-Based Testing (Optional Enhancement)
For modules with complex mathematical calculations:

```python
from hypothesis import given, strategies as st

@given(st.floats(min_value=0, max_value=360))
def test_gradient_angle_property(self, angle, gradient_converter):
    """Property-based test for gradient angle calculations"""
    # Test mathematical properties of gradient algorithms
```

## Test Execution and Coverage Validation

### Coverage Measurement Command
```bash
pytest --cov=converters --cov-report=html --cov-report=term-missing tests/
```

### Module-Specific Coverage Validation
```bash
# Test individual modules during development
pytest --cov=converters.masking --cov-report=term-missing tests/test_masking.py
pytest --cov=converters.text_path --cov-report=term-missing tests/test_text_path.py
pytest --cov=converters.gradients --cov-report=term-missing tests/test_gradients.py
pytest --cov=converters.styles --cov-report=term-missing tests/test_styles.py
pytest --cov=converters.filters --cov-report=term-missing tests/test_filters.py
```

### Success Criteria Validation
- Each module reaches 95%+ line coverage
- Branch coverage achieves 90%+ for conditional logic
- All tests pass in CI/CD environment
- No regression in existing module coverage
- Test execution time remains under 2 minutes total
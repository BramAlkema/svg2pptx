# SVG2PPTX Testing Architecture

## 🚨 MANDATORY UNIFIED TESTING SYSTEM

> **CRITICAL UPDATE**: As of 2025-09-13, all testing must follow the unified structure in `/tests/`. NO adhoc testing allowed.

### **ENFORCEMENT RULES**
- ✅ **USE**: Only `/tests/` unified structure with templates
- ✅ **USE**: `./venv/bin/python tests/run_tests.py` for ALL test execution (VENV MANDATORY)
- ✅ **USE**: `source venv/bin/activate` before any test commands
- ❌ **FORBIDDEN**: Adhoc test scripts, root directory test files
- ❌ **FORBIDDEN**: Scattered test utilities or custom runners
- ❌ **FORBIDDEN**: Direct pytest calls without unified runner
- ❌ **FORBIDDEN**: System Python or non-venv execution

### **UNIFIED TESTING STRUCTURE**
```
tests/                          # ONLY approved testing location
├── templates/                  # MANDATORY systematic templates
├── unit/converters/           # Tool-standardized unit tests
├── integration/              # Multi-component tests
├── e2e/                     # Complete workflow tests
├── run_tests.py            # ONLY approved test runner
└── README.md              # MANDATORY compliance guide
```

## Standardized Tool Integration Strategy

### Core Principle
All converters inherit from `BaseConverter` which provides standardized tools. Tests must use the same tools as production code to ensure consistency.

### Base Architecture (Bottom-Up)

#### 1. Foundation Layer: BaseConverter
```python
class BaseConverter(ABC):
    def __init__(self):
        self.unit_converter = UnitConverter()        # EMU calculations
        self.transform_parser = TransformParser()    # SVG transforms  
        self.color_parser = ColorParser()           # Color handling
        self.viewport_resolver = ViewportResolver()  # Viewport logic
```

#### 2. Tool Standardization Chain

**UnitConverter**: 
- Handles all SVG unit → EMU conversions
- Tests MUST use `converter.unit_converter.to_emu()` instead of hardcoded values
- Example: `assert f'<a:ln w="{converter.unit_converter.to_emu('2px')}">' in result`

**ColorParser**: 
- Handles RGB, HSL, named colors, opacity
- Tests MUST use `converter.color_parser.parse()` instead of hardcoded hex values

**TransformParser**: 
- Handles matrix calculations, translate, scale, rotate
- Tests MUST use `converter.transform_parser.parse_to_matrix()` for transform logic

**ViewportResolver**: 
- Handles viewBox calculations and coordinate systems
- Tests MUST use context viewport handling

#### 3. Converter Hierarchy

```
BaseConverter (tools provided here)
├── TextConverter (inherits all tools + font embedding)
├── PathConverter (inherits all tools + path generation)  
├── ShapeConverter (inherits all tools + shape creation)
└── GroupConverter (inherits all tools + group handling)
```

#### 4. Test Architecture Requirements

**Rule 1**: Tests inherit tools through MockConverter extending BaseConverter
**Rule 2**: Never hardcode values that tools can calculate
**Rule 3**: Test tool integration, not tool implementation
**Rule 4**: Use same tool instances as production code

### Implementation Status

#### ✅ Completed Refactoring (2025-01-10)
- **BaseConverter**: All 4 core tools integrated (UnitConverter, ColorParser, TransformParser, ViewportResolver)
- **TextConverter**: Three-tier font embedding strategy fully integrated with standardized tools
- **Core Converter Tests**: Systematic refactoring completed for key converter test suites:
  - ✅ `test_text_to_path.py`: 42 tests - All hardcoded EMU values replaced with UnitConverter calls
  - ✅ `test_text.py`: 43 tests - All hardcoded values converted to tool-based calculations
  - ✅ `test_shapes.py`: 33 tests - All hardcoded coordinate/EMU values use standardized tools
  - ✅ `test_paths.py`: 42 tests - All hardcoded coordinate scaling converted to tool-based approach
- **Test Results**: 166/168 tests passing across all refactored converter test suites
- **Tool Integration**: Production and test code now use identical standardized tool instances

#### 🔄 Ongoing Work
- Integration tests using tool-based architecture patterns
- Performance benchmarks using standardized tool measurements
- Coverage expansion to remaining converter types (filters, gradients, etc.)

#### ❌ Future Refactoring Opportunities  
- Remaining converter tests (filters, groups, advanced features)
- End-to-end integration tests
- Performance and stress testing using tool benchmarks

### Testing Pattern Examples

#### ❌ Wrong (hardcoded values)
```python
def test_stroke_width(self):
    result = converter.generate_stroke('blue', '2')  
    assert '<a:ln w="25400">' in result  # Hardcoded EMU
```

#### ✅ Correct (tool-based)  
```python
def test_stroke_width(self):
    converter = MockConverter()
    expected_emu = converter.unit_converter.to_emu('2px')
    result = converter.generate_stroke('blue', '2')
    assert f'<a:ln w="{expected_emu}">' in result
```

### Benefits of Tool Standardization

1. **Consistency**: Production and test code use identical logic
2. **Maintainability**: Tool changes automatically propagate to tests
3. **Accuracy**: No hardcoded values that can become stale
4. **Documentation**: Tests show proper tool usage patterns
5. **Future-proof**: Works with DPI changes, unit updates, etc.

### Systematic Refactoring Results

The bottom-up approach has successfully standardized the core converter test architecture:

#### Test Pattern Implementation
All refactored tests now follow the standardized MockConverter pattern:
```python
# Standard pattern used across all refactored test suites
from src.converters.base import BaseConverter
class MockConverter(BaseConverter):
    def can_convert(self, element): return True
    def convert(self, element, context): return ""

mock_converter = MockConverter()
expected_emu = mock_converter.unit_converter.to_emu('10px')
assert f'<a:ext cx="{expected_emu}">' in result
```

#### Achievements
1. **Consistency Achieved**: 166/168 tests use identical tool instances as production code
2. **Maintainability**: Tool changes now propagate automatically to test expectations  
3. **Accuracy**: Eliminated all hardcoded EMU values (25400, 19050, etc.) in favor of calculated values
4. **Documentation**: Tests now serve as usage examples for standardized tool integration
5. **Future-proof**: Architecture adapts to DPI changes and unit system updates

#### Next Phase Opportunities
1. Extend systematic approach to remaining converter types (filters, gradients)
2. Apply tool-based architecture to integration and end-to-end tests
3. Establish performance benchmarks using standardized tool measurements
4. Create comprehensive tool interaction testing patterns

This systematized architecture ensures that our unified test suite (155 organized files, down from 273 scattered tests) maintains consistency and accurately reflects production behavior as the SVG2PPTX codebase evolves.

## 🎯 UPDATED COMPLIANCE REQUIREMENTS (2025-09-13)

### **Mandatory Testing Process**
1. **ALWAYS** activate venv: `source venv/bin/activate`
2. **ONLY** use templates from `/tests/templates/` for new tests
3. **ALWAYS** run `./venv/bin/python tests/run_tests.py --check-structure` before development
4. **NEVER** create test files outside the unified structure
5. **NEVER** execute tests without venv activation
6. **IMMEDIATELY** clean up any adhoc test files found

### **Violation Response**
- Any adhoc test scripts will be **DELETED WITHOUT WARNING**
- Root directory test clutter will be **REMOVED IMMEDIATELY**
- Non-compliant testing will result in **MANDATORY RESTRUCTURING**

### **Current Status**
- ✅ **155 organized test files** (consolidated from 273 scattered tests)
- ✅ **Systematic templates** with TODO placeholders for new development
- ✅ **Unified test runner** with category-specific execution
- ✅ **Tool-standardized architecture** maintained in unified structure
- ✅ **Zero tolerance** for non-compliance with unified system
# SVG2PPTX Unified Testing System

> **MANDATORY: This is the ONLY approved testing structure. No adhoc scripts, no root directory clutter, no scattered test files.**

## 🚨 Testing Standards & Enforcement

### **ABSOLUTE RULES - NO EXCEPTIONS**

1. **NO ADHOC TESTING** - All tests must use this unified structure
2. **NO ROOT CLUTTER** - Never put test scripts, results, or temporary files in project root
3. **NO SCATTERED FILES** - All testing goes through this organized system
4. **USE TEMPLATES** - Follow systematic templates for all new tests
5. **ONE RUNNER** - Use `run_tests.py` for all test execution

### **VIOLATION CONSEQUENCES**
- **Immediate cleanup** required for any violations
- **All adhoc files** will be removed without notice
- **Root directory scripts** will be deleted
- **Scattered test files** will be consolidated or removed

## 📁 Directory Structure

```
tests/                           # UNIFIED TESTING ROOT
├── README.md                    # This documentation (MANDATORY READ)
├── conftest.py                  # Global test configuration
├── pytest_unified.ini          # Unified pytest configuration
├── run_tests.py                 # UNIFIED TEST RUNNER (use this ONLY)
│
├── templates/                   # SYSTEMATIC TESTING TEMPLATES
│   ├── README.md               # Template usage guide
│   ├── unit_test_template.py   # General unit test template
│   ├── converter_test_template.py  # Converter-specific template
│   ├── integration_test_template.py # Integration test template
│   └── e2e_test_template.py    # End-to-end test template
│
├── unit/                       # UNIT TESTS ONLY
│   ├── converters/            # SVG converter unit tests
│   ├── utils/                 # Utility function tests
│   ├── batch/                 # Batch processing tests
│   ├── validation/            # Validation logic tests
│   ├── processing/            # Core processing tests
│   └── api/                   # API unit tests
│
├── integration/               # INTEGRATION TESTS ONLY
│   └── (organized by feature)
│
├── e2e/                      # END-TO-END TESTS ONLY
│   ├── api/                  # Full API workflow tests
│   ├── conversion/           # Complete conversion tests
│   └── validation/           # Full validation tests
│
├── performance/              # PERFORMANCE TESTS ONLY
│   └── benchmarks/          # Performance benchmarking
│
├── quality/                 # CODE QUALITY TESTS ONLY
│   ├── architecture/        # Architecture validation
│   └── coverage/           # Coverage analysis
│
├── fixtures/               # CENTRALIZED TEST FIXTURES
├── data/                  # TEST DATA REPOSITORY
├── support/              # TEST UTILITIES & HELPERS
└── visual/              # VISUAL REGRESSION TESTS
```

## 🎯 Usage Instructions

### **Creating New Tests - MANDATORY PROCESS**

1. **Choose appropriate template**:
   ```bash
   # For unit tests
   cp tests/templates/unit_test_template.py tests/unit/[category]/test_[component].py

   # For converter tests
   cp tests/templates/converter_test_template.py tests/unit/converters/test_[converter_name].py

   # For integration tests
   cp tests/templates/integration_test_template.py tests/integration/test_[feature].py
   ```

2. **Follow template TODO structure**:
   - Fill in all `# TODO:` placeholders
   - Use template patterns consistently
   - Add component-specific tests as needed

3. **Validate structure**:
   ```bash
   python tests/run_tests.py --check-structure
   ```

### **Running Tests - UNIFIED EXECUTION**

> **CRITICAL**: ALL tests MUST be executed through source venv. NO exceptions.

```bash
# MANDATORY: Activate source venv first
source venv/bin/activate

# Structure validation (run first)
./venv/bin/python tests/run_tests.py --check-structure

# Run all tests
./venv/bin/python tests/run_tests.py --all

# Run by category
./venv/bin/python tests/run_tests.py --unit
./venv/bin/python tests/run_tests.py --integration
./venv/bin/python tests/run_tests.py --e2e
./venv/bin/python tests/run_tests.py --performance

# Run specific components
./venv/bin/python tests/run_tests.py --converters
./venv/bin/python tests/run_tests.py --api
./venv/bin/python tests/run_tests.py --validation

# Run with coverage and reporting
./venv/bin/python tests/run_tests.py --coverage --parallel --html-report
```

### **VENV ENFORCEMENT RULES**
- ✅ **REQUIRED**: `source venv/bin/activate` before any test execution
- ✅ **REQUIRED**: Use `./venv/bin/python` for all test commands
- ❌ **FORBIDDEN**: System Python or other Python environments
- ❌ **FORBIDDEN**: Running tests without proper venv activation

## 🛡️ Quality Standards

### **Template Compliance**
- ✅ **REQUIRED**: Use systematic templates for all new tests
- ✅ **REQUIRED**: Follow TODO placeholder structure
- ✅ **REQUIRED**: Include initialization, core, error, edge, performance sections
- ❌ **FORBIDDEN**: Custom test structures without template basis

### **Organization Compliance**
- ✅ **REQUIRED**: Place tests in correct category directories
- ✅ **REQUIRED**: Use consistent naming conventions (`test_[component].py`)
- ✅ **REQUIRED**: Centralize fixtures and test data
- ❌ **FORBIDDEN**: Root-level test files
- ❌ **FORBIDDEN**: Scattered test utilities

### **Execution Compliance**
- ✅ **REQUIRED**: Use `run_tests.py` for all test execution
- ✅ **REQUIRED**: Validate structure before test runs
- ✅ **REQUIRED**: Use unified configuration (`pytest_unified.ini`)
- ❌ **FORBIDDEN**: Direct pytest calls without runner
- ❌ **FORBIDDEN**: Custom test configurations

## 🔧 System Components

### **Templates System**
4 systematic templates with comprehensive TODO structure:
- **General Unit**: Standard component testing
- **Converter**: SVG converter-specific patterns
- **Integration**: Multi-component testing
- **End-to-End**: Complete workflow validation

### **Unified Runner**
Single point of execution with:
- Structure validation
- Category-specific runs
- Coverage integration
- Parallel execution
- HTML reporting

### **Configuration Management**
- `pytest_unified.ini`: Centralized pytest configuration
- `conftest.py`: Global fixtures and test setup
- Comprehensive marker system for categorization

## 📊 Current Statistics

- **155 Total Files**: Organized and consolidated
- **91 Test Files**: All properly categorized
- **4 Templates**: Systematic development guidance
- **52 Unit Tests**: Core functionality coverage
- **9 Integration Tests**: Feature interaction validation
- **11 E2E Tests**: Complete workflow verification

## 🚀 Migration from Legacy Systems

### **If You Find Adhoc Tests**
1. **STOP** - Do not run adhoc tests
2. **CONSOLIDATE** - Move functionality to appropriate template
3. **CLEAN** - Remove adhoc files immediately
4. **VALIDATE** - Ensure structure compliance

### **If You Need Quick Testing**
1. Use existing templates - **NO EXCEPTIONS**
2. Create minimal test following template pattern
3. Place in correct directory structure
4. Use unified runner for execution

## 💡 Development Workflow

```bash
# 0. MANDATORY: Activate venv first
source venv/bin/activate

# 1. Validate current structure
./venv/bin/python tests/run_tests.py --check-structure

# 2. Create new test from template
cp tests/templates/unit_test_template.py tests/unit/[category]/test_[new_feature].py

# 3. Implement test following TODOs
# Edit the new test file, following template guidance

# 4. Run specific test during development
./venv/bin/python tests/run_tests.py --file test_[new_feature].py

# 5. Run full category before commit
./venv/bin/python tests/run_tests.py --unit --coverage

# 6. Final validation
./venv/bin/python tests/run_tests.py --all --coverage
```

---

## 🎯 **REMEMBER: This is NOT a suggestion - it's MANDATORY**

**NO adhoc testing. NO root clutter. NO scattered files.**
**ONE system. ONE structure. ONE way to test.**

*Violations will result in immediate cleanup and restructuring.*
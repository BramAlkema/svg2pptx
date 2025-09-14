# Test Templates for SVG2PPTX

This directory contains standardized test templates for creating comprehensive, consistent tests across the SVG2PPTX codebase.

## Available Templates

### 1. `unit_test_template.py` - General Unit Test Template
- **Purpose**: Template for unit testing any component in the codebase
- **Usage**: Copy and customize for individual modules/classes
- **Includes**:
  - Component initialization tests
  - Core functionality tests
  - Error handling tests
  - Edge case tests
  - Configuration tests
  - Performance tests
  - Thread safety tests (if applicable)

### 2. `converter_test_template.py` - SVG Converter Test Template
- **Purpose**: Specialized template for testing SVG converter components
- **Usage**: Copy to `tests/unit/converters/` for new converter tests
- **Includes**:
  - SVG element handling tests
  - Coordinate transformation tests
  - Style processing tests
  - PowerPoint shape creation tests
  - Complex SVG structure tests
  - Converter-specific edge cases

### 3. `integration_test_template.py` - Integration Test Template
- **Purpose**: Template for testing multiple components working together
- **Usage**: Copy to `tests/integration/` for component integration tests
- **Includes**:
  - Multi-component workflow tests
  - Data consistency tests
  - Error propagation tests
  - Configuration integration tests
  - Resource management tests
  - Concurrent operation tests

### 4. `e2e_test_template.py` - End-to-End Test Template
- **Purpose**: Template for complete system workflow testing
- **Usage**: Copy to `tests/e2e/` for full system tests
- **Includes**:
  - Complete workflow tests
  - User scenario simulations
  - Performance validation
  - Output quality verification
  - Resource cleanup validation
  - API workflow tests (if applicable)

## How to Use Templates

### Step 1: Choose the Right Template
- **Unit tests**: Use `unit_test_template.py` for individual components
- **Converter tests**: Use `converter_test_template.py` for SVG converters
- **Integration tests**: Use `integration_test_template.py` for component interactions
- **E2E tests**: Use `e2e_test_template.py` for complete workflows

### Step 2: Copy and Customize
```bash
# Example: Creating a new converter test
cp tests/templates/converter_test_template.py tests/unit/converters/test_new_converter.py
```

### Step 3: Fill in TODO Placeholders
1. Search for all `TODO` comments in the copied file
2. Replace placeholder imports with actual module imports
3. Update class names and descriptions
4. Implement test fixtures with real data
5. Write actual test implementations
6. Add converter/component-specific test scenarios

### Step 4: Verify Template Completeness
- [ ] All TODO placeholders replaced
- [ ] Imports updated for target module
- [ ] Test fixtures provide realistic data
- [ ] Core functionality tests implemented
- [ ] Error handling tests added
- [ ] Edge cases covered
- [ ] Integration points tested
- [ ] Performance considerations addressed

## Template Guidelines

### Test Structure
Each template follows a consistent structure:
1. **Setup**: Imports, fixtures, test data
2. **Basic Tests**: Initialization, core functionality
3. **Edge Cases**: Boundary conditions, error scenarios
4. **Advanced Tests**: Performance, concurrency, integration
5. **Parametrized Tests**: Multiple scenario testing

### Naming Conventions
- Test files: `test_{component_name}.py`
- Test classes: `Test{ComponentName}`
- Test methods: `test_{functionality}_{scenario}`
- Fixtures: `{data_type}_fixture`

### Test Data
- Use realistic data that represents actual usage
- Include both simple and complex scenarios
- Cover edge cases and boundary conditions
- Provide both valid and invalid inputs

### Assertions
- Use descriptive assertion messages
- Test both positive and negative cases
- Verify expected behavior and side effects
- Check error conditions and exception handling

## Integration with Testing System

### pytest Configuration
Templates are designed to work with the project's pytest configuration:
- Automatic test discovery
- Fixture sharing via conftest.py
- Parameterized testing support
- Marker-based test categorization

### Test Categories
Templates support test categorization:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.performance` - Performance tests

### Coverage Integration
Templates are structured to support code coverage:
- Comprehensive test coverage of target modules
- Edge case coverage for robust testing
- Integration coverage for component interactions

## Best Practices

### Template Usage
1. **Don't skip TODOs**: Address all TODO placeholders
2. **Customize appropriately**: Adapt templates to specific needs
3. **Maintain consistency**: Follow template structure and patterns
4. **Add context**: Include component-specific test scenarios

### Test Implementation
1. **Start simple**: Implement basic tests first
2. **Build complexity**: Add complex scenarios incrementally
3. **Test realistically**: Use data that matches real usage
4. **Document assumptions**: Explain test setup and expectations

### Maintenance
1. **Keep templates updated**: Improve templates based on usage
2. **Share improvements**: Update templates when patterns emerge
3. **Maintain examples**: Keep placeholder examples current
4. **Document changes**: Update this README when templates change

## Examples

### Creating a Shape Converter Test
```bash
cp tests/templates/converter_test_template.py tests/unit/converters/test_shape_converter.py
```

Then customize:
- Replace `{ConverterName}` with `Shape`
- Import `from src.converters.shapes import ShapeConverter`
- Add SVG shape elements to test fixtures
- Implement shape-specific test scenarios

### Creating an API Integration Test
```bash
cp tests/templates/integration_test_template.py tests/integration/test_api_integration.py
```

Then customize:
- Replace `{IntegrationScenario}` with `APIIntegration`
- Import API components
- Add API-specific test scenarios
- Test API endpoint interactions

## Support

If you need help using these templates:
1. Check existing tests for examples
2. Review the template TODOs for guidance
3. Follow the patterns in similar existing tests
4. Ask for code review feedback on new tests

Remember: Good tests are the foundation of reliable software. Take time to implement comprehensive, maintainable tests using these templates.
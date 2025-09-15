# Dependency Injection Migration Guide

## Overview

The SVG2PPTX converter system has been refactored to use a centralized dependency injection pattern through the `ConversionServices` container. This guide explains how to migrate from the old manual instantiation pattern to the new dependency injection system.

## Key Benefits

- **Centralized service management** - All services created and configured in one place
- **Improved testability** - Easy to mock services for unit testing
- **Reduced coupling** - Converters no longer directly instantiate their dependencies
- **Consistent configuration** - Service configuration applied uniformly across all converters
- **Better maintainability** - Changes to service initialization only need to be made in one place

## Migration Overview

### Before (Old Pattern)
```python
# Manual instantiation in each converter
class RectangleConverter(BaseConverter):
    def __init__(self):
        super().__init__()
        self.unit_converter = UnitConverter()
        self.color_parser = ColorParser()
        self.transform_parser = TransformParser()
```

### After (New Pattern)
```python
# Dependency injection through services
class RectangleConverter(BaseConverter):
    def __init__(self, services: ConversionServices):
        super().__init__(services)
        # Services available through self.services or property accessors
```

## Quick Start

### 1. Basic Usage

```python
from src.services.conversion_services import ConversionServices
from src.converters.shapes import RectangleConverter

# Create services container
services = ConversionServices.create_default()

# Create converter with services
converter = RectangleConverter(services=services)

# Services are available through properties
unit_converter = converter.unit_converter
color_parser = converter.color_parser
```

### 2. Custom Configuration

```python
from src.services.conversion_services import ConversionServices, ConversionConfig

# Create custom configuration
config = ConversionConfig(
    default_dpi=150.0,
    viewport_width=1200.0,
    viewport_height=900.0,
    enable_caching=True
)

# Create services with custom config
services = ConversionServices.create_default(config)
```

### 3. Using Migration Helper

```python
from src.services.migration_utils import MigrationHelper
from src.converters.text import TextConverter

# Simplified converter creation
converter = MigrationHelper.create_converter_with_services(TextConverter)
```

## Detailed Migration Steps

### Step 1: Update Converter Constructors

**Old:**
```python
class MyConverter(BaseConverter):
    def __init__(self):
        super().__init__()
        self.unit_converter = UnitConverter()
        # ... other manual instantiations
```

**New:**
```python
class MyConverter(BaseConverter):
    def __init__(self, services: ConversionServices):
        super().__init__(services)
        # Services available through self.services or properties
```

### Step 2: Update Service Access

**Old:**
```python
# Direct access to manually created instances
length_emu = self.unit_converter.to_emu("10px")
color_info = self.color_parser.parse("#ff0000")
```

**New:**
```python
# Access through inherited properties (backward compatible)
length_emu = self.unit_converter.to_emu("10px")  # Still works!
color_info = self.color_parser.parse("#ff0000")  # Still works!

# Or access through services container
length_emu = self.services.unit_converter.to_emu("10px")
color_info = self.services.color_parser.parse("#ff0000")
```

### Step 3: Update Context Creation

**Old:**
```python
context = ConversionContext(svg_root)
```

**New:**
```python
services = ConversionServices.create_default()
context = ConversionContext(svg_root, services=services)
```

### Step 4: Update Entry Points

**Old:**
```python
converter = SVGToDrawingMLConverter()
result = converter.convert(svg_content)
```

**New:**
```python
# With explicit services (recommended)
services = ConversionServices.create_default()
converter = SVGToDrawingMLConverter(services=services)
result = converter.convert(svg_content)

# Or using migration compatibility (creates default services)
converter = SVGToDrawingMLConverter()  # Still works during migration
result = converter.convert(svg_content)
```

## API Reference

### ConversionServices

The main dependency injection container.

#### Constructor

```python
ConversionServices(
    unit_converter: UnitConverter,
    color_parser: ColorParser,
    transform_parser: TransformParser,
    viewport_resolver: ViewportResolver,
    config: ConversionConfig = None
)
```

#### Factory Methods

```python
# Create with default configuration
services = ConversionServices.create_default(config: Optional[ConversionConfig] = None)

# Create with custom service configurations
services = ConversionServices.create_custom(custom_config: Dict[str, Dict[str, Any]])

# Get singleton instance (creates if needed)
services = ConversionServices.get_default_instance()
```

#### Methods

```python
# Validate all services are functional
is_valid = services.validate_services()

# Clean up resources
services.cleanup()

# Reset singleton instance
ConversionServices.reset_default_instance()
```

### ConversionConfig

Configuration container for service parameters.

```python
config = ConversionConfig(
    default_dpi: float = 96.0,
    viewport_width: float = 800.0,
    viewport_height: float = 600.0,
    enable_caching: bool = True
)

# Load from dictionary
config = ConversionConfig.from_dict(config_dict)

# Load from JSON file
config = ConversionConfig.from_file("config.json")

# Convert to dictionary
config_dict = config.to_dict()
```

### BaseConverter

Updated base class for all converters.

```python
class MyConverter(BaseConverter):
    def __init__(self, services: ConversionServices):
        super().__init__(services)

    # Property accessors (backward compatible)
    @property
    def unit_converter(self) -> UnitConverter:
        return self.services.unit_converter

    @property
    def color_parser(self) -> ColorParser:
        return self.services.color_parser

    # Service validation
    def validate_services(self) -> bool:
        return self.services.validate_services()
```

### ConversionContext

Updated context class requiring services.

```python
# Required services parameter
context = ConversionContext(
    svg_root: Optional[ET.Element] = None,
    services: ConversionServices  # Required!
)

# Access services through context
unit_converter = context.unit_converter
viewport_handler = context.viewport_handler
```

## Testing with Dependency Injection

### Unit Testing

```python
import pytest
from unittest.mock import Mock
from src.services.conversion_services import ConversionServices

@pytest.fixture
def mock_services():
    services = Mock(spec=ConversionServices)
    services.unit_converter = Mock()
    services.color_parser = Mock()
    services.transform_parser = Mock()
    services.viewport_resolver = Mock()
    services.validate_services.return_value = True
    return services

def test_converter_with_mocked_services(mock_services):
    converter = RectangleConverter(services=mock_services)

    # Configure mock behavior
    mock_services.unit_converter.to_emu.return_value = 914400

    # Test converter behavior
    assert converter.unit_converter.to_emu("1in") == 914400
```

### Integration Testing

```python
def test_end_to_end_conversion():
    # Create real services for integration test
    services = ConversionServices.create_default()

    # Test full conversion pipeline
    converter = SVGToDrawingMLConverter(services=services)
    result = converter.convert(svg_content)

    # Verify services are functional
    assert services.validate_services()
```

## Best Practices

### 1. Always Use Factory Methods

**Good:**
```python
services = ConversionServices.create_default()
```

**Avoid:**
```python
services = ConversionServices(...)  # Manual construction
```

### 2. Validate Services

```python
services = ConversionServices.create_default()
if not services.validate_services():
    raise RuntimeError("Service validation failed")
```

### 3. Use Type Hints

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.conversion_services import ConversionServices

class MyConverter(BaseConverter):
    def __init__(self, services: 'ConversionServices'):
        super().__init__(services)
```

### 4. Configuration Examples

```python
# High DPI configuration
high_dpi_config = ConversionConfig(
    default_dpi=300.0,
    viewport_width=2400.0,
    viewport_height=1800.0
)

# Performance configuration
perf_config = ConversionConfig(
    default_dpi=96.0,
    enable_caching=True
)

# Custom service configuration
custom_config = {
    'unit_converter': {'default_dpi': 150.0},
    'color_parser': {'color_space': 'sRGB'},
    'viewport_resolver': {'strict_parsing': True}
}
services = ConversionServices.create_custom(custom_config)
```

## Common Migration Issues

### Issue 1: Missing Services Parameter

**Error:**
```
TypeError: ConversionContext requires ConversionServices instance
```

**Solution:**
```python
# Add services parameter
context = ConversionContext(svg_root, services=services)
```

### Issue 2: Converter Constructor Not Updated

**Error:**
```
TypeError: __init__() missing 1 required positional argument: 'services'
```

**Solution:**
```python
# Update converter constructor to accept services
converter = RectangleConverter(services=services)
```

### Issue 3: Service Access After Cleanup

**Error:**
```
AttributeError: 'NoneType' object has no attribute 'to_emu'
```

**Solution:**
```python
# Don't call cleanup() if services are still needed
# Or recreate services after cleanup
```

## Migration Checklist

- [ ] Update converter constructors to accept services parameter
- [ ] Replace manual service instantiation with dependency injection
- [ ] Update ConversionContext creation to pass services
- [ ] Update main entry points to use ConversionServices
- [ ] Add proper error handling for missing services
- [ ] Update tests to use service mocking
- [ ] Validate services before use
- [ ] Update documentation and examples

## Support

For questions or issues with the dependency injection migration:

1. Check integration tests in `tests/integration/test_dependency_injection_integration.py`
2. Review example usage in migration utilities
3. Validate services configuration and functionality
4. Check error messages for specific guidance

The dependency injection system is designed to be backward compatible during migration while encouraging adoption of the new patterns.
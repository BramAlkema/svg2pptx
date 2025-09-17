# ConversionServices API Reference

## Overview

The `ConversionServices` class provides centralized dependency injection for the SVG2PPTX converter system. It manages instances of `UnitConverter`, `ColorParser`, `TransformParser`, and `ViewportResolver` with consistent configuration.

## Module Location

```python
from src.services.conversion_services import ConversionServices, ConversionConfig
```

## Classes

### ConversionServices

Main dependency injection container that provides access to all conversion services.

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

**Parameters:**
- `unit_converter`: UnitConverter instance for length/coordinate conversion
- `color_parser`: ColorParser instance for color parsing and conversion
- `transform_parser`: TransformParser instance for SVG transform parsing
- `viewport_resolver`: ViewportResolver instance for viewport calculations
- `config`: Optional ConversionConfig with service parameters

**Raises:**
- `ServiceInitializationError`: If any service fails to initialize

#### Properties

```python
@property
def unit_converter(self) -> UnitConverter:
    """Access to unit conversion service."""

@property
def color_parser(self) -> ColorParser:
    """Access to color parsing service."""

@property
def transform_parser(self) -> TransformParser:
    """Access to transform parsing service."""

@property
def viewport_resolver(self) -> ViewportResolver:
    """Access to viewport resolution service."""

@property
def config(self) -> ConversionConfig:
    """Access to service configuration."""
```

#### Factory Methods

##### create_default(config=None)

Creates ConversionServices with default service configurations.

```python
@classmethod
def create_default(cls, config: Optional[ConversionConfig] = None) -> 'ConversionServices'
```

**Parameters:**
- `config`: Optional ConversionConfig for service parameters

**Returns:**
- ConversionServices instance with initialized services

**Raises:**
- `ServiceInitializationError`: If any service fails to initialize

**Example:**
```python
# Basic usage
services = ConversionServices.create_default()

# With custom configuration
config = ConversionConfig(default_dpi=150.0)
services = ConversionServices.create_default(config)
```

##### create_custom(custom_config)

Creates ConversionServices with custom service configurations.

```python
@classmethod
def create_custom(cls, custom_config: Dict[str, Dict[str, Any]]) -> 'ConversionServices'
```

**Parameters:**
- `custom_config`: Dictionary mapping service names to their config parameters

**Returns:**
- ConversionServices instance with custom-configured services

**Raises:**
- `ServiceInitializationError`: If any service fails to initialize

**Example:**
```python
custom_config = {
    'unit_converter': {'default_dpi': 300.0},
    'color_parser': {'color_space': 'sRGB'},
    'transform_parser': {'precision': 'high'},
    'viewport_resolver': {'strict_parsing': True}
}
services = ConversionServices.create_custom(custom_config)
```

##### get_default_instance()

Gets singleton default ConversionServices instance.

```python
@classmethod
def get_default_instance(cls) -> 'ConversionServices'
```

**Returns:**
- Singleton ConversionServices instance

**Note:** Creates the instance on first call using default configuration. Subsequent calls return the same instance.

**Example:**
```python
# Get singleton instance
services = ConversionServices.get_default_instance()

# Subsequent calls return same instance
same_services = ConversionServices.get_default_instance()
assert services is same_services
```

##### reset_default_instance()

Resets the singleton default instance.

```python
@classmethod
def reset_default_instance(cls) -> None
```

**Note:** Next call to `get_default_instance()` will create a new instance. Useful for testing and reconfiguration scenarios.

**Example:**
```python
# Reset singleton for testing
ConversionServices.reset_default_instance()
new_services = ConversionServices.get_default_instance()
```

#### Instance Methods

##### validate_services()

Validates that all services are properly initialized and functional.

```python
def validate_services(self) -> bool
```

**Returns:**
- `True` if all services are available and functional, `False` otherwise

**Example:**
```python
services = ConversionServices.create_default()
if not services.validate_services():
    raise RuntimeError("Service validation failed")
```

##### cleanup()

Cleans up service resources and resets references.

```python
def cleanup(self) -> None
```

**Note:** Sets all service references to None to enable garbage collection. Should be called when services are no longer needed.

**Example:**
```python
services = ConversionServices.create_default()
# ... use services ...
services.cleanup()  # Clean up when done
```

### ConversionConfig

Configuration container for ConversionServices parameters.

#### Constructor

```python
ConversionConfig(
    default_dpi: float = 96.0,
    viewport_width: float = 800.0,
    viewport_height: float = 600.0,
    enable_caching: bool = True
)
```

**Parameters:**
- `default_dpi`: Default DPI for unit conversion (default: 96.0)
- `viewport_width`: Default viewport width in pixels (default: 800.0)
- `viewport_height`: Default viewport height in pixels (default: 600.0)
- `enable_caching`: Whether to enable service caching (default: True)

#### Class Methods

##### from_dict(config_dict)

Creates ConversionConfig from dictionary with defaults for missing values.

```python
@classmethod
def from_dict(cls, config_dict: Dict[str, Any]) -> 'ConversionConfig'
```

**Parameters:**
- `config_dict`: Dictionary with configuration values

**Returns:**
- ConversionConfig instance with values from dictionary

**Example:**
```python
config_dict = {
    'default_dpi': 150.0,
    'viewport_width': 1200.0,
    'enable_caching': False
}
config = ConversionConfig.from_dict(config_dict)
```

##### from_file(file_path)

Loads ConversionConfig from JSON file, using defaults if file not found.

```python
@classmethod
def from_file(cls, file_path: str) -> 'ConversionConfig'
```

**Parameters:**
- `file_path`: Path to JSON configuration file

**Returns:**
- ConversionConfig instance loaded from file or with defaults

**Example:**
```python
# Load from file (falls back to defaults if file missing)
config = ConversionConfig.from_file("config.json")
```

**JSON file format:**
```json
{
    "default_dpi": 150.0,
    "viewport_width": 1200.0,
    "viewport_height": 900.0,
    "enable_caching": true
}
```

#### Instance Methods

##### to_dict()

Converts ConversionConfig to dictionary for serialization.

```python
def to_dict(self) -> Dict[str, Any]
```

**Returns:**
- Dictionary representation of configuration

**Example:**
```python
config = ConversionConfig(default_dpi=150.0)
config_dict = config.to_dict()
# {'default_dpi': 150.0, 'viewport_width': 800.0, ...}
```

### ServiceInitializationError

Exception raised when service initialization fails.

#### Constructor

```python
ServiceInitializationError(
    message: str,
    cause: Optional[Exception] = None
)
```

**Parameters:**
- `message`: Error message describing the failure
- `cause`: Optional underlying exception that caused the failure

**Example:**
```python
try:
    services = ConversionServices.create_default()
except ServiceInitializationError as e:
    print(f"Service initialization failed: {e}")
    if e.__cause__:
        print(f"Caused by: {e.__cause__}")
```

## Usage Patterns

### Basic Service Creation

```python
from src.services.conversion_services import ConversionServices

# Create with defaults
services = ConversionServices.create_default()

# Use services
length_emu = services.unit_converter.to_emu("10px")
color_info = services.color_parser.parse("#ff0000")
```

### Custom Configuration

```python
from src.services.conversion_services import ConversionServices, ConversionConfig

# Create custom config
config = ConversionConfig(
    default_dpi=300.0,
    viewport_width=2400.0,
    enable_caching=False
)

# Create services with config
services = ConversionServices.create_default(config)
```

### Converter Integration

```python
from src.converters.shapes import RectangleConverter

# Create converter with services
services = ConversionServices.create_default()
converter = RectangleConverter(services=services)

# Access services through converter
unit_converter = converter.unit_converter
color_parser = converter.color_parser
```

### Testing with Mocks

```python
from unittest.mock import Mock
from src.services.conversion_services import ConversionServices

# Create mock services for testing
services = Mock(spec=ConversionServices)
services.unit_converter = Mock()
services.color_parser = Mock()
services.validate_services.return_value = True

# Use in tests
converter = RectangleConverter(services=services)
```

### Singleton Pattern

```python
# Get singleton instance
services1 = ConversionServices.get_default_instance()
services2 = ConversionServices.get_default_instance()

# Same instance
assert services1 is services2

# Reset for testing
ConversionServices.reset_default_instance()
new_services = ConversionServices.get_default_instance()
assert new_services is not services1
```

### Error Handling

```python
from src.services.conversion_services import ServiceInitializationError

try:
    services = ConversionServices.create_default()

    if not services.validate_services():
        raise RuntimeError("Service validation failed")

except ServiceInitializationError as e:
    print(f"Failed to initialize services: {e}")
    # Handle initialization failure
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle other errors
```

## Configuration Examples

### High DPI Configuration

```python
high_dpi_config = ConversionConfig(
    default_dpi=300.0,
    viewport_width=2400.0,
    viewport_height=1800.0,
    enable_caching=True
)

services = ConversionServices.create_default(high_dpi_config)
```

### Performance Configuration

```python
perf_config = ConversionConfig(
    default_dpi=96.0,
    viewport_width=1920.0,
    viewport_height=1080.0,
    enable_caching=True
)

services = ConversionServices.create_default(perf_config)
```

### Custom Service Configuration

```python
custom_config = {
    'unit_converter': {
        'default_dpi': 150.0,
        'precision': 'high'
    },
    'color_parser': {
        'color_space': 'sRGB',
        'alpha_handling': 'preserve'
    },
    'transform_parser': {
        'matrix_precision': 6,
        'angle_units': 'degrees'
    },
    'viewport_resolver': {
        'strict_parsing': True,
        'fallback_dimensions': (800, 600)
    }
}

services = ConversionServices.create_custom(custom_config)
```

## Thread Safety

⚠️ **Important:** ConversionServices instances are not thread-safe. Each thread should have its own services instance or appropriate synchronization should be used.

```python
# Per-thread services (recommended)
import threading

thread_local = threading.local()

def get_thread_services():
    if not hasattr(thread_local, 'services'):
        thread_local.services = ConversionServices.create_default()
    return thread_local.services
```

## Performance Considerations

- **Service Creation**: Factory methods create new service instances each time. For high-frequency usage, consider reusing services instances.
- **Validation**: `validate_services()` performs functional tests on all services. Use sparingly in performance-critical code.
- **Cleanup**: Call `cleanup()` when services are no longer needed to free resources.
- **Singleton**: Use singleton pattern (`get_default_instance()`) for shared services across application.

## Migration from Legacy Pattern

### Before

```python
# Manual instantiation
unit_converter = UnitConverter()
color_parser = ColorParser()
transform_parser = TransformParser()
```

### After

```python
# Dependency injection
services = ConversionServices.create_default()
unit_converter = services.unit_converter
color_parser = services.color_parser
transform_parser = services.transform_parser
```

## See Also

- [Migration Guide](../dependency-injection-migration-guide.md)
- [Integration Tests](../../tests/integration/test_dependency_injection_integration.py)
- [Migration Utilities](../../src/services/migration_utils.py)
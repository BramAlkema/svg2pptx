# Dependency Injection Quick Reference

## TL;DR - Common Patterns

### Basic Usage

```python
from src.services.conversion_services import ConversionServices

# Create services
services = ConversionServices.create_default()

# Create converter with services
converter = MyConverter(services=services)

# Access services (backward compatible)
result = converter.unit_converter.to_emu("10px")
```

### Custom Configuration

```python
from src.services.conversion_services import ConversionConfig

config = ConversionConfig(default_dpi=150.0, viewport_width=1200.0)
services = ConversionServices.create_default(config)
```

### Testing

```python
from unittest.mock import Mock

services = Mock()
services.unit_converter = Mock()
services.validate_services.return_value = True
converter = MyConverter(services=services)
```

## Migration Patterns

| Old Pattern | New Pattern |
|-------------|-------------|
| `UnitConverter()` | `services.unit_converter` |
| `ColorParser()` | `services.color_parser` |
| `TransformParser()` | `services.transform_parser` |
| `ViewportResolver()` | `services.viewport_resolver` |
| `ConversionContext(svg)` | `ConversionContext(svg, services)` |

## Converter Constructor Updates

### Before
```python
class MyConverter(BaseConverter):
    def __init__(self):
        super().__init__()
        self.unit_converter = UnitConverter()
```

### After
```python
class MyConverter(BaseConverter):
    def __init__(self, services: ConversionServices):
        super().__init__(services)
        # Services available as self.unit_converter
```

## Entry Point Updates

### Before
```python
converter = SVGToDrawingMLConverter()
```

### After
```python
services = ConversionServices.create_default()
converter = SVGToDrawingMLConverter(services=services)
```

## Common Configurations

```python
# High DPI
config = ConversionConfig(default_dpi=300.0, viewport_width=2400.0)

# Performance optimized
config = ConversionConfig(default_dpi=96.0, enable_caching=True)

# Custom services
custom_config = {
    'unit_converter': {'default_dpi': 150.0},
    'color_parser': {'color_space': 'sRGB'}
}
services = ConversionServices.create_custom(custom_config)
```

## Error Handling

```python
try:
    services = ConversionServices.create_default()
    assert services.validate_services()
except ServiceInitializationError as e:
    # Handle service creation failure
    pass
```

## Testing Snippets

```python
@pytest.fixture
def mock_services():
    services = Mock(spec=ConversionServices)
    services.unit_converter = Mock()
    services.color_parser = Mock()
    services.transform_parser = Mock()
    services.viewport_resolver = Mock()
    services.validate_services.return_value = True
    return services
```

## Property Access (Backward Compatible)

All these still work after migration:

```python
converter.unit_converter.to_emu("10px")
converter.color_parser.parse("#ff0000")
converter.transform_parser.parse("scale(2)")
converter.viewport_resolver.parse_viewbox("0 0 100 100")
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| `TypeError: ConversionContext requires ConversionServices` | Add `services=services` parameter |
| `missing 1 required positional argument: 'services'` | Update converter constructor |
| `'NoneType' object has no attribute 'to_emu'` | Don't call `cleanup()` while services in use |

## Best Practices

✅ **Do:**
- Use factory methods (`create_default()`)
- Validate services (`validate_services()`)
- Use type hints (`services: ConversionServices`)
- Mock services for unit tests

❌ **Don't:**
- Manual service construction
- Skip service validation
- Call `cleanup()` while services in use
- Share services across threads without synchronization
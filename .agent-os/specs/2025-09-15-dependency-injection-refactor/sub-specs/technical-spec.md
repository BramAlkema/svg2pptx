# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-09-15-dependency-injection-refactor/spec.md

## Technical Requirements

- **ConversionServices Container**: Dataclass-based dependency injection container with factory methods for default and custom configurations
- **Service Lifecycle Management**: Singleton pattern for service instances with proper initialization order and circular dependency prevention
- **BaseConverter Integration**: Constructor injection pattern replacing manual service instantiation in 20+ converter classes
- **Configuration System**: File-based and programmatic configuration support for global service parameters (DPI, viewport dimensions, color profiles)
- **Backward Compatibility**: Property accessors maintaining existing converter APIs during migration period
- **Testing Infrastructure**: Pytest fixtures for service mocking and test isolation with 95%+ coverage requirement
- **Import Elimination**: Systematic removal of 102 manual import statements across src/converters/ modules
- **Error Handling**: Graceful service initialization failure handling with clear error messages and fallback mechanisms
- **Type Safety**: Full type hints for all service interfaces and dependency injection patterns
- **Documentation**: Comprehensive migration guide and developer documentation for new dependency injection patterns

## Architecture Components

### ConversionServices Container
```python
@dataclass
class ConversionServices:
    unit_converter: UnitConverter
    color_parser: ColorParser
    transform_parser: TransformParser
    viewport_resolver: ViewportResolver

    @classmethod
    def create_default(cls, config: Optional[ConversionConfig] = None) -> 'ConversionServices'
```

### Configuration System
```python
@dataclass
class ConversionConfig:
    default_dpi: float = 96.0
    viewport_width: float = 800.0
    viewport_height: float = 600.0
    enable_caching: bool = True
```

### Refactored BaseConverter
```python
class BaseConverter(ABC):
    def __init__(self, services: ConversionServices):
        self.services = services

    @property
    def unit_converter(self) -> UnitConverter:
        return self.services.unit_converter
```

## Implementation Strategy

### Phase 1: Foundation
- Create ConversionServices container and ConversionConfig classes
- Implement factory methods and service lifecycle management
- Establish testing patterns for service mocking

### Phase 2: BaseConverter Migration
- Modify BaseConverter to accept ConversionServices via constructor
- Add property accessors for backward compatibility
- Update ConverterRegistry to handle service injection

### Phase 3: Converter Refactoring
- Migrate all 20+ converter classes to dependency injection pattern
- Remove 102 manual service instantiations
- Update converter initialization throughout codebase

### Phase 4: Testing & Documentation
- Update test files with service injection patterns
- Create comprehensive test coverage with mocking
- Document migration guide and new patterns
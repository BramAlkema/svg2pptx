# Spec Tasks

## Tasks

- [x] 1. Create ConversionServices Container Foundation
  - [x] 1.1 Write tests for ConversionServices container and ConversionConfig classes
  - [x] 1.2 Implement ConversionServices dataclass with type hints and service properties
  - [x] 1.3 Implement ConversionConfig dataclass with default values and file loading
  - [x] 1.4 Create factory methods for default and custom service configurations
  - [x] 1.5 Implement service lifecycle management with proper initialization order
  - [x] 1.6 Add error handling for service initialization failures with fallback mechanisms
  - [x] 1.7 Create pytest fixtures for service mocking and test isolation patterns
  - [x] 1.8 Verify all ConversionServices foundation tests pass

- [x] 2. Refactor BaseConverter for Dependency Injection
  - [x] 2.1 Write tests for BaseConverter with dependency injection patterns
  - [x] 2.2 Modify BaseConverter constructor to accept ConversionServices parameter
  - [x] 2.3 Add property accessors for backward compatibility (unit_converter, color_parser, transform_parser)
  - [x] 2.4 Update ConverterRegistry to handle service injection during converter instantiation
  - [x] 2.5 Create migration utilities for gradual converter transition to new pattern
  - [x] 2.6 Add type hints and documentation for new BaseConverter interface
  - [x] 2.7 Test BaseConverter changes with existing converter classes for compatibility
  - [x] 2.8 Verify all BaseConverter refactoring tests pass

- [x] 3. Migrate Core Converter Classes
  - [x] 3.1 Write tests for migrated converter classes with service injection
  - [x] 3.2 Migrate ShapeConverter, TextConverter, and PathConverter to dependency injection
  - [x] 3.3 Migrate ImageConverter, GradientConverter, and StyleConverter classes
  - [x] 3.4 Migrate remaining converter classes (AnimationConverter, MarkerConverter, etc.)
  - [x] 3.5 Remove manual service instantiations from all migrated converter constructors
  - [x] 3.6 Update converter initialization calls throughout the codebase to use services
  - [x] 3.7 Test all migrated converters with mocked services for proper isolation
  - [x] 3.8 Verify all converter migration tests pass

- [ ] 4. Eliminate Manual Imports and Integration Testing
  - [ ] 4.1 Write comprehensive integration tests for end-to-end service injection
  - [ ] 4.2 Systematically remove remaining manual UnitConverter imports across src/
  - [ ] 4.3 Remove manual ColorParser and TransformParser instantiations
  - [ ] 4.4 Update main conversion entry points to use ConversionServices
  - [ ] 4.5 Create configuration examples and templates for different use cases
  - [ ] 4.6 Write migration guide and developer documentation for new patterns
  - [ ] 4.7 Perform comprehensive regression testing on conversion output quality
  - [ ] 4.8 Verify all 102 manual imports eliminated and integration tests pass
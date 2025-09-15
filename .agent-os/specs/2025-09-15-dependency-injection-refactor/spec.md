# Spec Requirements Document

> Spec: Dependency Injection System Refactoring
> Created: 2025-09-15

## Overview

Refactor the SVG2PPTX dependency injection system to eliminate 102 manual imports of UnitConverter, ColorParser, and TransformParser across converter classes. This will create a unified ConversionServices container enabling better testability, modularity, and maintainability while reducing tight coupling throughout the codebase.

## User Stories

### Centralized Service Management

As a developer, I want a centralized dependency injection system, so that I don't have to manually instantiate UnitConverter, ColorParser, and TransformParser in every converter class.

This eliminates the current pattern where each of the 20+ converter classes manually creates these service instances, leading to configuration inconsistencies and maintenance overhead.

### Improved Testing Infrastructure

As a developer, I want easier unit testing capabilities, so that I can mock dependencies without modifying constructor signatures in 20+ converter classes.

This enables isolated unit testing with proper service mocking, dramatically improving test reliability and development velocity.

### Configuration Consistency

As a developer, I want configuration-driven service initialization, so that I can adjust conversion parameters globally without hunting through scattered instantiation code.

This allows global DPI, viewport, and color profile changes to propagate automatically across all converters.

## Spec Scope

1. **ConversionServices Container** - Create centralized dependency injection container managing UnitConverter, ColorParser, TransformParser, and ViewportResolver instances
2. **BaseConverter Refactoring** - Modify BaseConverter to accept ConversionServices instead of manual dependency instantiation
3. **Import Elimination** - Remove 102 manual dependency instantiations across converter classes and replace with service injection
4. **Configuration System** - Implement global service configuration allowing parameter adjustment without code changes
5. **Testing Infrastructure** - Update test files to use dependency injection patterns with proper mocking capabilities

## Out of Scope

- Changing functional behavior of UnitConverter, ColorParser, or TransformParser classes
- Modifying external converter interfaces or user-facing APIs
- Performance optimization or benchmarking of the new system
- Adding new conversion services beyond the core three utilities

## Expected Deliverable

1. ConversionServices container with factory methods and configuration support
2. Refactored BaseConverter class accepting services via constructor injection
3. All 20+ converter classes migrated to use dependency injection pattern
4. Comprehensive test suite with 95%+ coverage demonstrating mocking capabilities
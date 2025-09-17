#!/usr/bin/env python3
"""
Dependency Injection Examples for SVG2PPTX

This file demonstrates various usage patterns for the new dependency injection
system in SVG2PPTX converter.
"""

from src.services.conversion_services import ConversionServices, ConversionConfig
from src.services.migration_utils import MigrationHelper
from src.converters.shapes import RectangleConverter
from src.converters.text import TextConverter
from src.converters.base import ConversionContext
from unittest.mock import Mock
import json


def example_basic_usage():
    """Basic dependency injection usage."""
    print("=== Basic Usage Example ===")

    # Create services with default configuration
    services = ConversionServices.create_default()

    # Create converter with services
    converter = RectangleConverter(services=services)

    # Access services through properties (backward compatible)
    length_emu = converter.unit_converter.to_emu("10px")
    print(f"10px = {length_emu} EMUs")

    # Validate services are working
    if converter.validate_services():
        print("✅ Services validation passed")
    else:
        print("❌ Services validation failed")


def example_custom_configuration():
    """Using custom configuration."""
    print("\n=== Custom Configuration Example ===")

    # Create custom configuration
    config = ConversionConfig(
        default_dpi=150.0,
        viewport_width=1200.0,
        viewport_height=900.0,
        enable_caching=True
    )

    # Create services with custom config
    services = ConversionServices.create_default(config)

    # Verify configuration is applied
    print(f"Default DPI: {services.config.default_dpi}")
    print(f"Viewport: {services.config.viewport_width}x{services.config.viewport_height}")

    # Use with converter
    converter = TextConverter(services=services)
    print("✅ TextConverter created with custom configuration")


def example_config_from_file():
    """Loading configuration from file."""
    print("\n=== Configuration from File Example ===")

    # Create example config file
    config_data = {
        "default_dpi": 300.0,
        "viewport_width": 2400.0,
        "viewport_height": 1800.0,
        "enable_caching": False
    }

    config_file = "example_config.json"
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)

    # Load configuration from file
    config = ConversionConfig.from_file(config_file)
    services = ConversionServices.create_default(config)

    print(f"Loaded DPI: {services.config.default_dpi}")
    print(f"Loaded viewport: {services.config.viewport_width}x{services.config.viewport_height}")
    print(f"Caching enabled: {services.config.enable_caching}")

    # Clean up
    import os
    os.unlink(config_file)


def example_custom_service_config():
    """Using custom service configurations."""
    print("\n=== Custom Service Configuration Example ===")

    # Define custom configurations for each service
    custom_config = {
        'unit_converter': {
            'default_dpi': 200.0
        },
        'color_parser': {
            # Custom color parser options would go here
        },
        'transform_parser': {
            # Custom transform parser options would go here
        },
        'viewport_resolver': {
            # Custom viewport resolver options would go here
        }
    }

    # Note: create_custom method would need to be implemented
    # For now, use default with custom config
    config = ConversionConfig(default_dpi=200.0)
    services = ConversionServices.create_default(config)

    # Verify custom configuration
    converter = RectangleConverter(services=services)
    print("✅ Services created with custom configurations")


def example_migration_helper():
    """Using migration helper utilities."""
    print("\n=== Migration Helper Example ===")

    # Easy converter creation with default services
    converter = MigrationHelper.create_converter_with_services(RectangleConverter)
    print("✅ Converter created via MigrationHelper")

    # With custom config
    config = ConversionConfig(default_dpi=150.0)
    converter_with_config = MigrationHelper.create_converter_with_services(
        TextConverter,
        config=config
    )
    print("✅ Converter created with custom config via MigrationHelper")

    # Validate migration status
    is_migrated = MigrationHelper.validate_converter_migration(converter)
    print(f"Converter migration status: {'✅ Migrated' if is_migrated else '❌ Not migrated'}")


def example_singleton_pattern():
    """Using singleton pattern for shared services."""
    print("\n=== Singleton Pattern Example ===")

    # Get singleton instance
    services1 = ConversionServices.get_default_instance()
    services2 = ConversionServices.get_default_instance()

    # Should be same instance
    print(f"Same instance: {services1 is services2}")

    # Reset singleton (useful for testing)
    ConversionServices.reset_default_instance()
    services3 = ConversionServices.get_default_instance()

    print(f"After reset, different instance: {services1 is not services3}")


def example_context_usage():
    """Using ConversionContext with services."""
    print("\n=== ConversionContext Example ===")

    # Create services
    services = ConversionServices.create_default()

    # Create context with services (required)
    context = ConversionContext(svg_root=None, services=services)

    # Access services through context
    length_emu = context.unit_converter.to_emu("5mm")
    print(f"5mm = {length_emu} EMUs")

    # Context provides direct access to services
    print(f"Services available in context: {context.services is not None}")


def example_testing_with_mocks():
    """Testing with mocked services."""
    print("\n=== Testing with Mocks Example ===")

    # Create mock services
    mock_services = Mock(spec=ConversionServices)
    mock_services.unit_converter = Mock()
    mock_services.color_parser = Mock()
    mock_services.transform_parser = Mock()
    mock_services.viewport_resolver = Mock()
    mock_services.validate_services.return_value = True

    # Configure mock behavior
    mock_services.unit_converter.to_emu.return_value = 914400  # 1 inch in EMUs

    # Create converter with mocked services
    converter = RectangleConverter(services=mock_services)

    # Test converter behavior
    result = converter.unit_converter.to_emu("1in")
    print(f"Mocked result: {result} EMUs")

    # Verify mock was called
    mock_services.unit_converter.to_emu.assert_called_with("1in")
    print("✅ Mock verification passed")


def example_error_handling():
    """Error handling examples."""
    print("\n=== Error Handling Example ===")

    try:
        # This will work
        services = ConversionServices.create_default()
        print("✅ Services created successfully")

        # Validate services
        if not services.validate_services():
            raise RuntimeError("Service validation failed")
        print("✅ Service validation passed")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Example of required services
    try:
        # This will fail - services required
        context = ConversionContext()
    except TypeError as e:
        print(f"✅ Expected error caught: {e}")


def example_service_lifecycle():
    """Service lifecycle management."""
    print("\n=== Service Lifecycle Example ===")

    # Create services
    services = ConversionServices.create_default()
    print("✅ Services created")

    # Use services
    converter = RectangleConverter(services=services)
    result = converter.unit_converter.to_emu("1cm")
    print(f"1cm = {result} EMUs")

    # Clean up when done (optional)
    services.cleanup()
    print("✅ Services cleaned up")

    # Note: converter.unit_converter will be None after cleanup


def example_multiple_converters():
    """Using services with multiple converters."""
    print("\n=== Multiple Converters Example ===")

    # Create shared services
    services = ConversionServices.create_default()

    # Create multiple converters sharing same services
    rect_converter = RectangleConverter(services=services)
    text_converter = TextConverter(services=services)

    # Verify they share the same service instances
    same_unit_converter = (
        rect_converter.unit_converter is text_converter.unit_converter
    )
    print(f"Converters share services: {same_unit_converter}")

    # All converters can validate services
    rect_valid = rect_converter.validate_services()
    text_valid = text_converter.validate_services()
    print(f"All converters valid: {rect_valid and text_valid}")


def main():
    """Run all examples."""
    print("SVG2PPTX Dependency Injection Examples")
    print("=" * 50)

    examples = [
        example_basic_usage,
        example_custom_configuration,
        example_config_from_file,
        example_custom_service_config,
        example_migration_helper,
        example_singleton_pattern,
        example_context_usage,
        example_testing_with_mocks,
        example_error_handling,
        example_service_lifecycle,
        example_multiple_converters,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"❌ Example failed: {e}")

    print("\n" + "=" * 50)
    print("Examples complete!")


if __name__ == "__main__":
    main()
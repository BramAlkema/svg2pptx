"""
Migration utilities for gradual converter transition to dependency injection.

This module provides utilities to help migrate from manual service instantiation
to the new ConversionServices dependency injection pattern.
"""

import warnings
from typing import Optional, Type

from .conversion_services import ConversionConfig, ConversionServices


class DeprecationWarning(UserWarning):
    """Warning for deprecated manual service instantiation patterns."""
    pass


def deprecated_manual_services(func):
    """
    Decorator to mark manual service instantiation as deprecated.

    Args:
        func: Function using manual service instantiation

    Returns:
        Wrapped function that emits deprecation warning
    """
    def wrapper(*args, **kwargs):
        warnings.warn(
            "Manual service instantiation is deprecated. "
            "Use ConversionServices dependency injection instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)
    return wrapper


class MigrationHelper:
    """Helper class for managing converter migration to dependency injection."""

    @staticmethod
    def create_converter_with_services(converter_class: type,
                                     services: ConversionServices | None = None,
                                     config: ConversionConfig | None = None):
        """
        Create converter instance with proper service injection.

        Args:
            converter_class: Converter class to instantiate
            services: ConversionServices instance (creates default if None)
            config: Configuration for default services

        Returns:
            Converter instance with injected services
        """
        if services is None:
            services = ConversionServices.create_default(config)

        return converter_class(services=services)

    @staticmethod
    def migrate_registry_to_services(registry, services: ConversionServices):
        """
        Migrate existing registry to use dependency injection.

        Args:
            registry: Existing ConverterRegistry instance
            services: ConversionServices to inject

        Note:
            This updates the registry in-place to use new services
        """
        registry.services = services

        # Re-register all converters with new services
        old_converters = registry.converters.copy()
        registry.converters.clear()
        registry.element_map.clear()

        for old_converter in old_converters:
            converter_class = old_converter.__class__
            new_converter = converter_class(services=services)
            registry.register(new_converter)

    @staticmethod
    @deprecated_manual_services
    def create_legacy_converter(converter_class: type):
        """
        Create converter using legacy manual service instantiation.

        Args:
            converter_class: Converter class to instantiate

        Returns:
            Converter instance with manual services

        Warning:
            This method is deprecated and should only be used during migration
        """
        return converter_class.create_with_default_services()

    @staticmethod
    def validate_converter_migration(converter) -> bool:
        """
        Validate that converter has been properly migrated to dependency injection.

        Args:
            converter: Converter instance to validate

        Returns:
            True if converter uses dependency injection, False if legacy
        """
        # Check if converter has services attribute
        if not hasattr(converter, 'services'):
            return False

        # Check if services is properly initialized
        if converter.services is None:
            return False

        # Validate services functionality
        return converter.validate_services()

    @staticmethod
    def get_migration_status(registry) -> dict:
        """
        Get migration status for all converters in registry.

        Args:
            registry: ConverterRegistry to analyze

        Returns:
            Dictionary with migration status information
        """
        total_converters = len(registry.converters)
        migrated_converters = 0
        legacy_converters = 0

        converter_status = {}

        for converter in registry.converters:
            converter_name = converter.__class__.__name__
            is_migrated = MigrationHelper.validate_converter_migration(converter)

            converter_status[converter_name] = {
                'migrated': is_migrated,
                'has_services': hasattr(converter, 'services'),
                'services_valid': converter.validate_services() if hasattr(converter, 'services') else False,
            }

            if is_migrated:
                migrated_converters += 1
            else:
                legacy_converters += 1

        return {
            'total_converters': total_converters,
            'migrated_converters': migrated_converters,
            'legacy_converters': legacy_converters,
            'migration_percentage': (migrated_converters / total_converters * 100) if total_converters > 0 else 0,
            'converter_details': converter_status,
        }

    @staticmethod
    def create_migration_plan(registry) -> list:
        """
        Create migration plan for converting legacy converters.

        Args:
            registry: ConverterRegistry to analyze

        Returns:
            List of migration steps
        """
        status = MigrationHelper.get_migration_status(registry)
        migration_steps = []

        if status['legacy_converters'] > 0:
            migration_steps.append({
                'step': 1,
                'description': 'Create ConversionServices instance',
                'action': 'services = ConversionServices.create_default()',
            })

            migration_steps.append({
                'step': 2,
                'description': 'Update registry with services',
                'action': 'registry.services = services',
            })

            for converter_name, details in status['converter_details'].items():
                if not details['migrated']:
                    migration_steps.append({
                        'step': len(migration_steps) + 1,
                        'description': f'Migrate {converter_name}',
                        'action': f'Update {converter_name} constructor to accept services parameter',
                    })

        return migration_steps


class ServiceCompatibilityChecker:
    """Checker for service compatibility during migration."""

    @staticmethod
    def check_converter_compatibility(converter_class: type) -> dict:
        """
        Check converter class compatibility with dependency injection.

        Args:
            converter_class: Converter class to check

        Returns:
            Dictionary with compatibility information
        """
        compatibility = {
            'supports_services': False,
            'has_migration_method': False,
            'constructor_signature': None,
            'issues': [],
        }

        # Check constructor signature
        try:
            import inspect
            sig = inspect.signature(converter_class.__init__)
            compatibility['constructor_signature'] = str(sig)

            # Check if services parameter exists
            if 'services' in sig.parameters:
                compatibility['supports_services'] = True
            else:
                compatibility['issues'].append('Constructor does not accept services parameter')

        except Exception as e:
            compatibility['issues'].append(f'Could not inspect constructor: {e}')

        # Check for migration method
        if hasattr(converter_class, 'create_with_default_services'):
            compatibility['has_migration_method'] = True
        else:
            compatibility['issues'].append('Missing create_with_default_services migration method')

        return compatibility

    @staticmethod
    def generate_compatibility_report(registry) -> str:
        """
        Generate human-readable compatibility report.

        Args:
            registry: ConverterRegistry to analyze

        Returns:
            Formatted compatibility report
        """
        report_lines = []
        report_lines.append("=== Converter Dependency Injection Compatibility Report ===\n")

        migration_status = MigrationHelper.get_migration_status(registry)

        report_lines.append(f"Total Converters: {migration_status['total_converters']}")
        report_lines.append(f"Migrated: {migration_status['migrated_converters']}")
        report_lines.append(f"Legacy: {migration_status['legacy_converters']}")
        report_lines.append(f"Migration Progress: {migration_status['migration_percentage']:.1f}%\n")

        for converter_name, details in migration_status['converter_details'].items():
            status = "✓ MIGRATED" if details['migrated'] else "✗ LEGACY"
            report_lines.append(f"{converter_name}: {status}")

            if not details['migrated']:
                if not details['has_services']:
                    report_lines.append("  - Missing services attribute")
                if not details['services_valid']:
                    report_lines.append("  - Services validation failed")

        return "\n".join(report_lines)
"""
ConversionServices dependency injection container.

This module provides the ConversionServices container that centralizes dependency
injection for UnitConverter, ColorParser, TransformParser, and ViewportResolver.
It eliminates 102 manual imports across converter classes.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, ClassVar
import json
import logging
from pathlib import Path

from src.units import UnitConverter
from src.colors import ColorParser
from src.transforms import TransformParser
from src.viewbox import ViewportResolver

logger = logging.getLogger(__name__)


class ServiceInitializationError(Exception):
    """Exception raised when service initialization fails."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        if cause is not None:
            self.__cause__ = cause


@dataclass
class ConversionConfig:
    """Configuration for ConversionServices container.

    Provides default values and file loading capabilities for global
    service parameters like DPI, viewport dimensions, and caching settings.
    """
    default_dpi: float = 96.0
    viewport_width: float = 800.0
    viewport_height: float = 600.0
    enable_caching: bool = True

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ConversionConfig':
        """Create ConversionConfig from dictionary with defaults for missing values."""
        # Only use keys that exist in the dataclass
        valid_keys = {field.name for field in cls.__dataclass_fields__.values()}
        filtered_config = {k: v for k, v in config_dict.items() if k in valid_keys}

        return cls(**filtered_config)

    @classmethod
    def from_file(cls, file_path: str) -> 'ConversionConfig':
        """Load ConversionConfig from JSON file, using defaults if file not found."""
        try:
            with open(file_path, 'r') as f:
                config_dict = json.load(f)
            return cls.from_dict(config_dict)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load config from {file_path}: {e}. Using defaults.")
            return cls()

    def to_dict(self) -> Dict[str, Any]:
        """Convert ConversionConfig to dictionary for serialization."""
        return {
            'default_dpi': self.default_dpi,
            'viewport_width': self.viewport_width,
            'viewport_height': self.viewport_height,
            'enable_caching': self.enable_caching
        }


@dataclass
class ConversionServices:
    """Dependency injection container for conversion services.

    Centralizes UnitConverter, ColorParser, TransformParser, and ViewportResolver
    instances to eliminate manual imports across converter classes.
    """
    unit_converter: UnitConverter
    color_parser: ColorParser
    transform_parser: TransformParser
    viewport_resolver: ViewportResolver
    config: ConversionConfig = None

    # Class-level singleton instance
    _default_instance: ClassVar[Optional['ConversionServices']] = None

    @classmethod
    def create_default(cls, config: Optional[ConversionConfig] = None) -> 'ConversionServices':
        """Create ConversionServices with default service configurations.

        Args:
            config: Optional configuration for service parameters

        Returns:
            ConversionServices instance with initialized services

        Raises:
            ServiceInitializationError: If any service fails to initialize
        """
        if config is None:
            config = ConversionConfig()

        try:
            # Initialize services with proper order and configuration
            from ..units import ConversionContext
            context = ConversionContext(dpi=config.default_dpi)
            unit_converter = UnitConverter(default_context=context)

            color_parser = ColorParser()

            transform_parser = TransformParser()

            viewport_resolver = ViewportResolver(unit_engine=unit_converter)

            return cls(
                unit_converter=unit_converter,
                color_parser=color_parser,
                transform_parser=transform_parser,
                viewport_resolver=viewport_resolver,
                config=config
            )

        except Exception as e:
            # Determine which service failed based on the error context
            service_name = "unknown"
            error_str = str(e)

            if "UnitConverter" in error_str or "default_dpi" in error_str:
                service_name = "UnitConverter"
            elif "ColorParser" in error_str:
                service_name = "ColorParser"
            elif "TransformParser" in error_str:
                service_name = "TransformParser"
            elif "ViewportResolver" in error_str:
                service_name = "ViewportResolver"

            raise ServiceInitializationError(
                f"Failed to initialize {service_name}: {e}", e
            )

    @classmethod
    def create_custom(cls, custom_config: Dict[str, Dict[str, Any]]) -> 'ConversionServices':
        """Create ConversionServices with custom service configurations.

        Args:
            custom_config: Dictionary mapping service names to their config parameters

        Returns:
            ConversionServices instance with custom-configured services

        Raises:
            ServiceInitializationError: If any service fails to initialize
        """
        try:
            # Extract service configurations with defaults
            unit_config = custom_config.get('unit_converter', {})
            color_config = custom_config.get('color_parser', {})
            transform_config = custom_config.get('transform_parser', {})
            viewport_config = custom_config.get('viewport_resolver', {})

            # Initialize services with custom configurations
            unit_converter = UnitConverter(**unit_config)
            color_parser = ColorParser(**color_config)
            transform_parser = TransformParser(**transform_config)
            viewport_resolver = ViewportResolver(unit_engine=unit_converter)

            return cls(
                unit_converter=unit_converter,
                color_parser=color_parser,
                transform_parser=transform_parser,
                viewport_resolver=viewport_resolver,
                config=config
            )

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to create custom services: {e}"
            ) from e

    @classmethod
    def get_default_instance(cls) -> 'ConversionServices':
        """Get singleton default ConversionServices instance.

        Creates the instance on first call using default configuration.
        Subsequent calls return the same instance.

        Returns:
            Singleton ConversionServices instance
        """
        if cls._default_instance is None:
            cls._default_instance = cls.create_default()

        return cls._default_instance

    @classmethod
    def reset_default_instance(cls) -> None:
        """Reset the singleton default instance.

        Next call to get_default_instance() will create a new instance.
        Useful for testing and reconfiguration scenarios.
        """
        if cls._default_instance is not None:
            cls._default_instance.cleanup()
        cls._default_instance = None

    def cleanup(self) -> None:
        """Clean up service resources and reset references.

        Sets all service references to None to enable garbage collection.
        Should be called when services are no longer needed.
        """
        self.unit_converter = None
        self.color_parser = None
        self.transform_parser = None
        self.viewport_resolver = None

    def validate_services(self) -> bool:
        """Validate that all services are properly initialized.

        Returns:
            True if all services are available and functional
        """
        try:
            # Check that all services exist and have basic functionality
            services = [
                self.unit_converter,
                self.color_parser,
                self.transform_parser,
                self.viewport_resolver
            ]

            # Verify all services are not None
            if any(service is None for service in services):
                return False

            # Test basic functionality of each service
            self.unit_converter.to_emu("10px")
            self.color_parser.parse("#000000")
            self.transform_parser.parse("translate(10,20)")
            self.viewport_resolver.parse_viewbox("0 0 100 100")

            return True

        except Exception as e:
            logger.error(f"Service validation failed: {e}")
            return False
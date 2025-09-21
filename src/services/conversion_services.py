"""
ConversionServices dependency injection container.

This module provides the ConversionServices container that centralizes dependency
injection for UnitConverter, ColorParser, TransformParser, and ViewportResolver.
It eliminates 102 manual imports across converter classes.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, ClassVar, Callable, Tuple, TYPE_CHECKING
import json
import logging
from pathlib import Path
import importlib.util

from src.colors import ColorParser

if TYPE_CHECKING:  # pragma: no cover - type hinting only
    from src.units import UnitConverter as UnitConverterType
else:  # pragma: no cover - runtime fallback for type annotations
    UnitConverterType = Any  # type: ignore

logger = logging.getLogger(__name__)

try:
    from src.transforms import TransformParser  # type: ignore
except ModuleNotFoundError as exc:
    if exc.name != 'numpy':
        raise
    logger.warning("NumPy not available - using simplified TransformParser fallback")

    class TransformParser:  # type: ignore
        """Minimal fallback transform parser when NumPy engine is unavailable."""

        def parse(self, transform_str: str) -> Any:
            return []

except ImportError as exc:
    if 'numpy' not in str(exc):
        raise
    logger.warning("TransformParser import failed due to NumPy - using simplified fallback")

    class TransformParser:  # type: ignore
        """Minimal fallback transform parser when NumPy engine is unavailable."""

        def parse(self, transform_str: str) -> Any:
            return []

try:
    from src.viewbox import ViewportResolver  # type: ignore
except ModuleNotFoundError as exc:
    if exc.name != 'numpy':
        raise
    logger.warning("NumPy not available - using simplified ViewportResolver fallback")

    class ViewportResolver:  # type: ignore
        """Minimal fallback viewport resolver when NumPy engine is unavailable."""

        def __init__(self, unit_engine: Any = None):
            self.unit_engine = unit_engine

        def parse_viewbox(self, viewbox: str) -> tuple:
            try:
                parts = [float(v) for v in viewbox.replace(',', ' ').split()]
                if len(parts) >= 4:
                    return tuple(parts[:4])
            except Exception:
                pass
            return (0.0, 0.0, 0.0, 0.0)

        def parse_viewbox_strings(self, viewbox_strings: Any) -> Any:
            parsed = [self.parse_viewbox(str(v)) for v in viewbox_strings]
            return parsed

except ImportError as exc:
    if 'numpy' not in str(exc):
        raise
    logger.warning("ViewportResolver import failed due to NumPy - using simplified fallback")

    class ViewportResolver:  # type: ignore
        """Minimal fallback viewport resolver when NumPy engine is unavailable."""

        def __init__(self, unit_engine: Any = None):
            self.unit_engine = unit_engine

        def parse_viewbox(self, viewbox: str) -> tuple:
            try:
                parts = [float(v) for v in viewbox.replace(',', ' ').split()]
                if len(parts) >= 4:
                    return tuple(parts[:4])
            except Exception:
                pass
            return (0.0, 0.0, 0.0, 0.0)

        def parse_viewbox_strings(self, viewbox_strings: Any) -> Any:
            parsed = [self.parse_viewbox(str(v)) for v in viewbox_strings]
            return parsed


class GradientService:
    """Simple registry for gradient definitions used during conversion."""

    def __init__(self) -> None:
        self._gradients: Dict[str, Any] = {}

    def register_gradient(self, gradient_id: str, gradient_element: Any) -> None:
        """Store a gradient element by its identifier."""

        if not gradient_id:
            return

        self._gradients[gradient_id] = gradient_element

    def get_gradient(self, gradient_id: str) -> Optional[Any]:
        """Retrieve a previously registered gradient element."""

        return self._gradients.get(gradient_id)

    def clear(self) -> None:
        """Remove all stored gradients."""

        self._gradients.clear()


class PatternService:
    """Registry for SVG pattern definitions used in conversions."""

    def __init__(self) -> None:
        self._patterns: Dict[str, Any] = {}

    def register_pattern(self, pattern_id: str, pattern_element: Any) -> None:
        """Store a pattern element by its identifier."""

        if not pattern_id:
            return

        self._patterns[pattern_id] = pattern_element

    def get_pattern(self, pattern_id: str) -> Optional[Any]:
        """Retrieve a registered pattern element."""

        return self._patterns.get(pattern_id)

    def clear(self) -> None:
        """Remove all stored pattern definitions."""

        self._patterns.clear()


class FilterService:
    """Registry for SVG filter definitions used by filter converters."""

    def __init__(self) -> None:
        self._filters: Dict[str, Any] = {}

    def register_filter(self, filter_id: str, filter_element: Any) -> None:
        """Store a filter element by its identifier."""

        if not filter_id:
            return

        self._filters[filter_id] = filter_element

    def get_filter(self, filter_id: str) -> Optional[Any]:
        """Retrieve a registered filter element."""

        return self._filters.get(filter_id)

    def clear(self) -> None:
        """Remove all stored filter definitions."""

        self._filters.clear()

class ServiceInitializationError(Exception):
    """Exception raised when service initialization fails."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        if cause is not None:
            self.__cause__ = cause


def _load_legacy_unit_converter():
    """Load the legacy UnitConverter implementation when NumPy engine is unavailable."""

    legacy_units_path = Path(__file__).resolve().parents[1] / 'units.py'
    spec = importlib.util.spec_from_file_location('svg2pptx._legacy_units', legacy_units_path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load legacy UnitConverter implementation")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.UnitConverter


def _get_unit_converter_class() -> Tuple[Any, bool]:
    """Return the UnitConverter class and whether it uses the NumPy engine."""

    try:
        from src.units import UnitConverter as modern_converter  # type: ignore
        return modern_converter, True
    except ModuleNotFoundError as exc:
        if exc.name != 'numpy':
            raise
        logger.warning("NumPy not available - falling back to legacy UnitConverter")
    except ImportError as exc:
        if 'numpy' not in str(exc):
            raise
        logger.warning("NumPy import failed - falling back to legacy UnitConverter")

    legacy_converter = _load_legacy_unit_converter()
    return legacy_converter, False


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


def _initialize_optional_service(
    config_value: Any,
    default_factory: Callable[[], Any]
) -> Any:
    """Initialize an optional service from config or return default instance."""

    if config_value is None:
        return default_factory()

    # Allow passing an already-initialized instance directly
    if not isinstance(config_value, dict):
        if callable(config_value):
            return config_value()
        return config_value

    if 'instance' in config_value and config_value['instance'] is not None:
        return config_value['instance']

    factory = config_value.get('factory')
    if callable(factory):
        return factory()

    return default_factory()


@dataclass
class ConversionServices:
    """Dependency injection container for conversion services.

    Centralizes UnitConverter, ColorParser, TransformParser, and ViewportResolver
    instances to eliminate manual imports across converter classes.
    """
    unit_converter: UnitConverterType
    color_parser: ColorParser
    transform_parser: TransformParser
    viewport_resolver: ViewportResolver
    gradient_service: Optional[GradientService] = None
    pattern_service: Optional[PatternService] = None
    filter_service: Optional[FilterService] = None
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
            unit_converter_cls, uses_numpy_engine = _get_unit_converter_class()

            if uses_numpy_engine:
                from src.units import ConversionContext  # type: ignore

                context = ConversionContext(dpi=config.default_dpi)
                unit_converter = unit_converter_cls(default_context=context)
            else:
                unit_converter = unit_converter_cls(
                    default_dpi=config.default_dpi,
                    viewport_width=config.viewport_width,
                    viewport_height=config.viewport_height
                )

            color_parser = ColorParser()

            transform_parser = TransformParser()

            viewport_resolver = ViewportResolver(unit_engine=unit_converter)

            gradient_service = GradientService()
            pattern_service = PatternService()
            filter_service = FilterService()

            return cls(
                unit_converter=unit_converter,
                color_parser=color_parser,
                transform_parser=transform_parser,
                viewport_resolver=viewport_resolver,
                gradient_service=gradient_service,
                pattern_service=pattern_service,
                filter_service=filter_service,
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
            unit_converter_cls, uses_numpy_engine = _get_unit_converter_class()

            if uses_numpy_engine:
                unit_converter = unit_converter_cls(**unit_config)
            else:
                sanitized_config = dict(unit_config)
                sanitized_config.pop('default_context', None)
                unit_converter = unit_converter_cls(**sanitized_config)
            color_parser = ColorParser(**color_config)
            transform_parser = TransformParser(**transform_config)
            viewport_resolver = ViewportResolver(unit_engine=unit_converter)

            gradient_service = _initialize_optional_service(
                custom_config.get('gradient_service'),
                GradientService
            )
            pattern_service = _initialize_optional_service(
                custom_config.get('pattern_service'),
                PatternService
            )
            filter_service = _initialize_optional_service(
                custom_config.get('filter_service'),
                FilterService
            )

            config_value = custom_config.get('config')
            if isinstance(config_value, ConversionConfig):
                config = config_value
            elif isinstance(config_value, dict):
                config = ConversionConfig.from_dict(config_value)
            else:
                config = ConversionConfig()

            return cls(
                unit_converter=unit_converter,
                color_parser=color_parser,
                transform_parser=transform_parser,
                viewport_resolver=viewport_resolver,
                gradient_service=gradient_service,
                pattern_service=pattern_service,
                filter_service=filter_service,
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
        if self.gradient_service is not None:
            self.gradient_service.clear()
        if self.pattern_service is not None:
            self.pattern_service.clear()
        if self.filter_service is not None:
            self.filter_service.clear()
        self.gradient_service = None
        self.pattern_service = None
        self.filter_service = None

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
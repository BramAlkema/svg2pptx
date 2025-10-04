"""
ConversionServices dependency injection container.

This module provides the ConversionServices container that centralizes dependency
injection for UnitConverter, ColorParser, TransformEngine, and ViewportEngine.
It eliminates 102 manual imports across converter classes.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, ClassVar
import json
import logging
from pathlib import Path

from ..units import UnitConverter, unit
from ..color import Color
from ..transforms import TransformEngine
from ..viewbox import ViewportEngine
from ..paths import PathSystem, create_path_system
from ..utils.style_parser import StyleParser
from ..utils.coordinate_transformer import CoordinateTransformer
from ..utils.font_processor import FontProcessor
from ..utils.path_processor import PathProcessor
from ..legacy.pptx_builder import PPTXBuilder
from .gradient_service import GradientService
from .pattern_service import PatternService
from .filter_service import FilterService
from .image_service import ImageService
from .style_service import StyleService
from .font_service import FontService

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

    Centralizes UnitConverter, ColorParser, TransformEngine, ViewportEngine,
    FontProcessor, FontService, GradientService, PatternService, ImageService,
    and enhanced StyleService instances to eliminate manual imports across converter classes.
    """
    unit_converter: UnitConverter
    color_factory: type  # Color class for creating color instances
    color_parser: Color  # Color class that can also parse colors for BaseConverter
    transform_parser: TransformEngine
    viewport_resolver: ViewportEngine
    path_system: PathSystem
    style_parser: StyleParser  # Legacy parser for backward compatibility
    style_service: StyleService  # Enhanced CSS engine with cascade/inheritance
    coordinate_transformer: CoordinateTransformer
    font_processor: FontProcessor
    font_service: FontService
    path_processor: PathProcessor
    pptx_builder: PPTXBuilder
    gradient_service: GradientService
    pattern_service: PatternService
    filter_service: FilterService
    image_service: ImageService
    config: ConversionConfig = None

    # Clean Slate Integration Services
    ir_scene_factory: Optional[Any] = None
    policy_engine: Optional[Any] = None
    mapper_registry: Optional[Any] = None
    drawingml_embedder: Optional[Any] = None

    # Class-level singleton instance
    _default_instance: ClassVar[Optional['ConversionServices']] = None

    @classmethod
    def create_default(cls, config: Optional[ConversionConfig] = None,
                       svg_root: Optional['ET.Element'] = None) -> 'ConversionServices':
        """Create ConversionServices with default service configurations.

        Args:
            config: Optional configuration for service parameters
            svg_root: Optional SVG root element for StyleService initialization

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
            unit_converter = UnitConverter(context=context)

            # Use core services directly (adapters removed)
            color_factory = Color
            color_parser = Color   # Same class for parsing colors

            transform_parser = TransformEngine()

            viewport_resolver = ViewportEngine(unit_engine=unit_converter)

            # PathSystem will be created when needed to avoid circular dependency
            path_system = None

            style_parser = StyleParser()

            # Initialize enhanced CSS StyleService
            style_service = StyleService(svg_root)

            coordinate_transformer = CoordinateTransformer()

            font_processor = FontProcessor()

            font_service = FontService()

            path_processor = PathProcessor()

            pptx_builder = PPTXBuilder(unit_converter)

            # Initialize policy engine once (shared between services)
            policy_engine = None
            try:
                from ..policy.engine import create_policy
                from ..policy.config import OutputTarget
                policy_engine = create_policy(OutputTarget.BALANCED)
            except ImportError:
                logger.debug("Policy engine not available, services will use legacy behavior")

            gradient_service = GradientService(policy_engine=policy_engine)

            pattern_service = PatternService()

            filter_service = FilterService(policy_engine=policy_engine)

            image_service = ImageService(enable_caching=config.enable_caching)

            return cls(
                unit_converter=unit_converter,
                color_factory=color_factory,
                color_parser=color_parser,
                transform_parser=transform_parser,
                viewport_resolver=viewport_resolver,
                path_system=path_system,
                style_parser=style_parser,
                style_service=style_service,
                coordinate_transformer=coordinate_transformer,
                font_processor=font_processor,
                font_service=font_service,
                path_processor=path_processor,
                pptx_builder=pptx_builder,
                gradient_service=gradient_service,
                pattern_service=pattern_service,
                filter_service=filter_service,
                image_service=image_service,
                config=config,
                policy_engine=policy_engine
            )

        except Exception as e:
            # Determine which service failed based on the error context
            service_name = "unknown"
            error_str = str(e)

            if "UnitConverter" in error_str or "default_dpi" in error_str:
                service_name = "UnitConverter"
            elif "Color" in error_str:
                service_name = "Color"
            elif "TransformEngine" in error_str:
                service_name = "TransformEngine"
            elif "ViewportEngine" in error_str:
                service_name = "ViewportEngine"

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
            color_config = custom_config.get('color_factory', {})
            transform_config = custom_config.get('transform_parser', {})
            viewport_config = custom_config.get('viewport_resolver', {})

            # Create config from custom_config or use default
            config_data = custom_config.get('config', {})
            config = ConversionConfig.from_dict(config_data)

            # Initialize services with custom configurations
            from ..units import ConversionContext
            context = ConversionContext(dpi=config.default_dpi)
            unit_converter = UnitConverter(context=context, **unit_config)
            color_factory = Color
            color_parser = Color
            transform_parser = TransformEngine(**transform_config)
            viewport_resolver = ViewportEngine(unit_engine=unit_converter, **viewport_config)

            # Initialize remaining services
            # PathSystem will be created per-conversion with viewport configuration
            from ..utils.style_parser import StyleParser
            from ..utils.coordinate_transformer import CoordinateTransformer
            from ..utils.font_processor import FontProcessor
            from ..utils.path_processor import PathProcessor
            from .gradient_service import GradientService
            from .pattern_service import PatternService
            from .filter_service import FilterService
            from .image_service import ImageService

            path_system = None  # Will be created per-conversion
            style_parser = StyleParser()

            # Initialize enhanced CSS StyleService
            style_service = StyleService(None)  # No SVG root in custom creation

            coordinate_transformer = CoordinateTransformer()
            font_processor = FontProcessor()
            font_service = FontService()
            path_processor = PathProcessor()
            pptx_builder = PPTXBuilder(unit_converter)
            gradient_service = GradientService()
            pattern_service = PatternService()
            filter_service = FilterService()
            image_service = ImageService(enable_caching=config.enable_caching)

            return cls(
                unit_converter=unit_converter,
                color_factory=color_factory,
                color_parser=color_parser,
                transform_parser=transform_parser,
                viewport_resolver=viewport_resolver,
                path_system=path_system,
                style_parser=style_parser,
                style_service=style_service,
                coordinate_transformer=coordinate_transformer,
                font_processor=font_processor,
                font_service=font_service,
                path_processor=path_processor,
                pptx_builder=pptx_builder,
                gradient_service=gradient_service,
                pattern_service=pattern_service,
                filter_service=filter_service,
                image_service=image_service,
                config=config
            )

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to create custom services: {e}"
            ) from e

    @classmethod
    def create_with_clean_slate(cls, config: Optional[ConversionConfig] = None,
                                svg_root: Optional['ET.Element'] = None) -> 'ConversionServices':
        """Create services with clean slate components enabled.

        Args:
            config: Optional configuration for service parameters
            svg_root: Optional SVG root element for StyleService initialization

        Returns:
            ConversionServices instance with clean slate services initialized

        Raises:
            ServiceInitializationError: If clean slate components fail to initialize
        """
        try:
            # Create base services first
            services = cls.create_default(config, svg_root)

            # Import clean slate components dynamically to avoid circular imports
            try:
                from core.ir import SceneFactory
                from core.policy import PolicyEngine
                from core.map import MapperRegistry
                from core.pptx import DrawingMLEmbedder
            except ImportError as e:
                logger.warning(f"Clean slate components not available: {e}")
                return services

            # Initialize clean slate services with existing services injected
            services.ir_scene_factory = SceneFactory(
                unit_converter=services.unit_converter,
                color_parser=services.color_parser,
                transform_engine=services.transform_parser
            )

            services.policy_engine = PolicyEngine(
                path_complexity_threshold=0.7,
                text_complexity_threshold=0.6,
                group_nesting_threshold=3,
                image_size_threshold=1024 * 1024
            )

            services.mapper_registry = MapperRegistry(
                path_system=services.path_system,
                style_service=services.style_service,
                gradient_service=services.gradient_service
            )

            services.drawingml_embedder = DrawingMLEmbedder(
                slide_width_emu=9144000,  # 10 inches
                slide_height_emu=6858000  # 7.5 inches
            )

            logger.info("Clean slate services initialized successfully")
            return services

        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize clean slate services: {e}", e
            )

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
        self.color_factory = None
        self.color_parser = None
        self.transform_parser = None
        self.viewport_resolver = None
        self.path_system = None
        self.style_parser = None
        self.style_service = None
        self.coordinate_transformer = None
        self.font_processor = None
        self.path_processor = None
        self.pptx_builder = None
        self.gradient_service = None
        self.pattern_service = None
        self.filter_service = None
        self.image_service = None

        # Clean up clean slate services
        self.ir_scene_factory = None
        self.policy_engine = None
        self.mapper_registry = None
        self.drawingml_embedder = None

    def validate_services(self) -> bool:
        """Validate that all services are properly initialized.

        Returns:
            True if all services are available and functional
        """
        try:
            # Check that all services exist and have basic functionality
            services = [
                self.unit_converter,
                self.color_factory,
                self.color_parser,
                self.transform_parser,
                self.viewport_resolver,
                self.path_system,  # Note: May be None initially
                self.style_parser,
                self.coordinate_transformer,
                self.font_processor,
                self.path_processor,
                self.pptx_builder,
                self.gradient_service,
                self.pattern_service,
                self.filter_service,
                self.image_service
            ]

            # Verify all services are not None (except path_system which is created per-conversion)
            required_services = [s for s in services if s is not self.path_system]
            if any(service is None for service in required_services):
                return False

            # Test basic functionality of each service
            unit("10px").to_emu()
            self.color_factory("#000000")  # Test color creation
            self.color_parser("#000000")  # Test color parser (Color class)
            self.transform_parser.parse_to_matrix("translate(10,20)")

            # Test viewport resolver with proper method
            self.viewport_resolver.parse_viewbox("0 0 100 100")
            self.viewport_resolver.calculate_viewport(800, 600)

            # Skip path_system testing since it's None initially
            self.style_parser.parse_style_string("color: red; font-size: 12px")  # Test style parsing
            self.style_parser.parse_style_attribute("color: red; font-size: 12px")  # Test new method
            self.coordinate_transformer.parse_coordinate_string("10,20 30,40")  # Test coordinate parsing

            # Test font processing with mock element
            from lxml import etree as ET
            mock_element = ET.Element('text')
            mock_element.set('font-family', 'Arial')
            self.font_processor.get_font_family(mock_element)  # Test font processing
            self.font_processor.process_font_attributes(mock_element)  # Test new method

            self.path_processor.parse_path_string("M 10 10 L 20 20")  # Test path processing
            self.path_processor.optimize_path("M 10 10 L 20 20")  # Test new method

            # Test PPTXBuilder methods
            presentation = self.pptx_builder.create_presentation()
            if presentation:
                self.pptx_builder.add_slide(presentation)

            # Test enhanced service functionality
            self.gradient_service.get_gradient_content("test_gradient_id")  # Should return None gracefully
            self.gradient_service.create_gradient("linear", [])  # Test new method
            self.pattern_service.get_pattern_content("test_pattern_id")  # Should return None gracefully
            self.pattern_service.create_pattern("dots", {})  # Test new method
            self.filter_service.get_filter_content("test_filter_id")  # Should return None gracefully
            self.filter_service.apply_filter("blur", mock_element, {})  # Test new method
            self.image_service.get_image_info("/nonexistent/path")  # Should return None gracefully

            return True

        except Exception as e:
            logger.error(f"Service validation failed: {e}")
            return False

    def get_path_system(self, viewport_width: float = None, viewport_height: float = None,
                       viewbox = None, enable_logging: bool = False) -> 'PathSystem':
        """
        Create PathSystem instance with services injection.

        This method avoids circular dependency by creating PathSystem on demand.
        """
        if self.path_system is None:
            # Create PathSystem with this services instance to avoid circular import
            from ..paths import create_path_system
            self.path_system = create_path_system(
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                viewbox=viewbox,
                enable_logging=enable_logging
            )
        return self.path_system
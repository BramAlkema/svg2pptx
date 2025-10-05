#!/usr/bin/env python3
"""
Pipeline Factory

Factory for creating configured clean slate conversion pipelines.
"""

import logging
from typing import Any

from ..io import DrawingMLEmbedder, SlideBuilder, create_embedder, create_package_writer
from ..map import (
    GroupMapper,
    create_group_mapper,
    create_image_mapper,
    create_path_mapper,
    create_text_mapper,
)
from ..policy import PolicyConfig, PolicyEngine
from .config import PipelineConfig
from .converter import CleanSlateConverter

logger = logging.getLogger(__name__)


class PipelineFactory:
    """
    Factory for creating configured conversion pipelines.

    Handles component initialization, dependency injection, and
    configuration-based setup for different use cases.
    """

    @staticmethod
    def create_converter(config: PipelineConfig = None) -> CleanSlateConverter:
        """
        Create configured CleanSlateConverter.

        Args:
            config: Pipeline configuration (uses defaults if None)

        Returns:
            Fully configured CleanSlateConverter

        Raises:
            RuntimeError: If pipeline creation fails
        """
        try:
            if config is None:
                config = PipelineConfig()

            # Create converter with configuration
            converter = CleanSlateConverter(config)

            logger.debug(f"Created converter with {config.quality_level.value} quality level")
            return converter

        except Exception as e:
            logger.error(f"Failed to create converter: {e}")
            raise RuntimeError(f"Pipeline creation failed: {e}") from e

    @staticmethod
    def create_policy_engine(config: PipelineConfig) -> PolicyEngine:
        """
        Create configured policy engine.

        Args:
            config: Pipeline configuration

        Returns:
            Configured PolicyEngine
        """
        # Create policy config from pipeline config
        policy_config = PolicyConfig()
        # Note: We use default policy config since custom thresholds
        # should be set on the PolicyConfig, not passed as individual parameters
        return PolicyEngine(policy_config)

    @staticmethod
    def create_services(config: PipelineConfig) -> Any | None:
        """
        Create services for enhanced processing (optional).

        Args:
            config: Pipeline configuration

        Returns:
            Services object if available, None otherwise
        """
        try:
            # Try to import and create conversion services if available
            from ..services.conversion_services import ConversionServices
            return ConversionServices.create_default()
        except ImportError:
            logger.debug("ConversionServices not available - using basic processing")
            return None
        except Exception as e:
            logger.warning(f"Failed to create services: {e}")
            return None

    @staticmethod
    def create_mappers(policy: PolicyEngine, config: PipelineConfig, services=None) -> dict[str, Any]:
        """
        Create configured mapper instances.

        Args:
            policy: Policy engine for decisions
            config: Pipeline configuration
            services: Optional services for enhanced processing

        Returns:
            Dictionary of configured mappers
        """
        # Create mappers with services integration for enhanced processing
        mappers = {
            'path': create_path_mapper(policy, services),
            'textframe': create_text_mapper(policy, services),
            'group': create_group_mapper(policy),  # Group mapper doesn't need services yet
            'image': create_image_mapper(policy, services),
        }

        # Configure group mapper with child mappers if needed
        if isinstance(mappers['group'], GroupMapper):
            mappers['group'].set_child_mappers({
                'path': mappers['path'],
                'text': mappers['textframe'],
                'image': mappers['image'],
            })

        return mappers

    @staticmethod
    def create_embedder(config: PipelineConfig) -> DrawingMLEmbedder:
        """
        Create configured embedder.

        Args:
            config: Pipeline configuration

        Returns:
            Configured DrawingMLEmbedder
        """
        return create_embedder(
            slide_width_emu=config.slide_config.width_emu,
            slide_height_emu=config.slide_config.height_emu,
        )

    @staticmethod
    def create_slide_builder(mappers: dict[str, Any], embedder: DrawingMLEmbedder,
                           policy: PolicyEngine, config: PipelineConfig) -> SlideBuilder:
        """
        Create configured slide builder.

        Args:
            mappers: Dictionary of mappers
            embedder: DrawingML embedder
            policy: Policy engine
            config: Pipeline configuration

        Returns:
            Configured SlideBuilder
        """
        from ..io.slide_builder import create_slide_builder
        return create_slide_builder(mappers, embedder, policy)

    @classmethod
    def create_complete_pipeline(cls, config: PipelineConfig = None) -> dict[str, Any]:
        """
        Create complete pipeline with all components.

        Args:
            config: Pipeline configuration (uses defaults if None)

        Returns:
            Dictionary containing all pipeline components

        Raises:
            RuntimeError: If component creation fails
        """
        try:
            if config is None:
                config = PipelineConfig()

            # Create core components with services integration
            services = cls.create_services(config)
            policy = cls.create_policy_engine(config)
            mappers = cls.create_mappers(policy, config, services)
            embedder = cls.create_embedder(config)
            slide_builder = cls.create_slide_builder(mappers, embedder, policy, config)
            package_writer = create_package_writer()
            converter = cls.create_converter(config)

            return {
                'config': config,
                'services': services,
                'policy': policy,
                'mappers': mappers,
                'embedder': embedder,
                'slide_builder': slide_builder,
                'package_writer': package_writer,
                'converter': converter,
            }

        except Exception as e:
            logger.error(f"Failed to create complete pipeline: {e}")
            raise RuntimeError(f"Complete pipeline creation failed: {e}") from e

    @staticmethod
    def create_preset_fast() -> CleanSlateConverter:
        """
        Create converter preset optimized for speed.

        Returns:
            Fast-configured CleanSlateConverter
        """
        config = PipelineConfig.create_fast()
        return PipelineFactory.create_converter(config)

    @staticmethod
    def create_preset_high_quality() -> CleanSlateConverter:
        """
        Create converter preset optimized for quality.

        Returns:
            High-quality-configured CleanSlateConverter
        """
        config = PipelineConfig.create_high_quality()
        return PipelineFactory.create_converter(config)

    @staticmethod
    def create_preset_debug() -> CleanSlateConverter:
        """
        Create converter preset for debugging.

        Returns:
            Debug-configured CleanSlateConverter
        """
        config = PipelineConfig.create_debug()
        return PipelineFactory.create_converter(config)

    @staticmethod
    def validate_pipeline(pipeline: dict[str, Any]) -> bool:
        """
        Validate pipeline components.

        Args:
            pipeline: Pipeline dictionary from create_complete_pipeline

        Returns:
            True if pipeline is valid

        Raises:
            ValueError: If pipeline is invalid
        """
        required_components = ['config', 'policy', 'mappers', 'embedder', 'converter']
        # Note: 'services' is optional for enhanced processing

        for component in required_components:
            if component not in pipeline:
                raise ValueError(f"Missing required component: {component}")

        # Validate mappers
        required_mappers = ['path', 'textframe', 'group', 'image']
        for mapper_type in required_mappers:
            if mapper_type not in pipeline['mappers']:
                raise ValueError(f"Missing required mapper: {mapper_type}")

        # Validate embedder dimensions
        embedder = pipeline['embedder']
        width, height = embedder.get_slide_dimensions()
        if width <= 0 or height <= 0:
            raise ValueError("Invalid slide dimensions")

        logger.debug("Pipeline validation successful")
        return True


def create_default_pipeline() -> CleanSlateConverter:
    """
    Create default conversion pipeline.

    Returns:
        CleanSlateConverter with balanced configuration
    """
    return PipelineFactory.create_converter()


def create_fast_pipeline() -> CleanSlateConverter:
    """
    Create fast conversion pipeline.

    Returns:
        CleanSlateConverter optimized for speed
    """
    return PipelineFactory.create_preset_fast()


def create_quality_pipeline() -> CleanSlateConverter:
    """
    Create high-quality conversion pipeline.

    Returns:
        CleanSlateConverter optimized for quality
    """
    return PipelineFactory.create_preset_high_quality()


def create_debug_pipeline() -> CleanSlateConverter:
    """
    Create debug conversion pipeline.

    Returns:
        CleanSlateConverter with debug output enabled
    """
    return PipelineFactory.create_preset_debug()
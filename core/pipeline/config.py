#!/usr/bin/env python3
"""
Pipeline Configuration

Configuration classes for the clean slate conversion pipeline.
Integrates with core.policy.PolicyConfig for unified policy decisions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

# Import comprehensive policy configuration
from ..policy.config import OutputTarget, PolicyConfig


class OutputFormat(Enum):
    """Output format options"""
    PPTX = "pptx"
    SLIDE_XML = "slide_xml"
    DEBUG_JSON = "debug_json"


class QualityLevel(Enum):
    """Quality vs performance trade-off levels"""
    FAST = "fast"          # Prioritize performance, accept lower quality
    BALANCED = "balanced"  # Balance quality and performance
    HIGH = "high"          # Prioritize quality, accept slower performance


@dataclass
class SlideConfig:
    """Slide configuration"""
    width_emu: int = 9144000   # 10 inches in EMU
    height_emu: int = 6858000  # 7.5 inches in EMU
    template: str = "blank"
    preserve_aspect_ratio: bool = True


@dataclass
class PerformanceConfig:
    """Performance optimization settings"""
    enable_caching: bool = True
    parallel_processing: bool = False
    max_workers: int = 4
    memory_limit_mb: int = 512


@dataclass
class PipelineConfig:
    """
    Complete pipeline configuration.

    Integrates with core.policy.PolicyConfig for unified policy decisions.
    """
    # Quality and output settings
    quality_level: QualityLevel = QualityLevel.BALANCED
    output_format: OutputFormat = OutputFormat.PPTX

    # Policy configuration (unified with core.policy)
    policy_config: PolicyConfig | None = None

    # Slide configuration
    slide_config: SlideConfig | None = None

    # Performance settings
    performance_config: PerformanceConfig | None = None

    # Debug and logging
    enable_debug: bool = False
    verbose_logging: bool = False

    # Feature flags
    enable_text_fixes: bool = True
    enable_group_flattening: bool = True
    enable_path_optimization: bool = True
    enable_image_conversion: bool = True

    def __post_init__(self):
        """Initialize default sub-configurations"""
        if self.policy_config is None:
            # Map QualityLevel to OutputTarget
            target_map = {
                QualityLevel.FAST: OutputTarget.SPEED,
                QualityLevel.BALANCED: OutputTarget.BALANCED,
                QualityLevel.HIGH: OutputTarget.QUALITY,
            }
            target = target_map.get(self.quality_level, OutputTarget.BALANCED)
            self.policy_config = PolicyConfig(target=target)

        if self.slide_config is None:
            self.slide_config = SlideConfig()

        if self.performance_config is None:
            self.performance_config = PerformanceConfig()

    @classmethod
    def create_fast(cls) -> 'PipelineConfig':
        """Create configuration optimized for speed"""
        return cls(
            quality_level=QualityLevel.FAST,
            policy_config=PolicyConfig(target=OutputTarget.SPEED),
            performance_config=PerformanceConfig(
                enable_caching=True,
                parallel_processing=True,
                max_workers=8,
                memory_limit_mb=256,
            ),
            enable_group_flattening=True,
            enable_path_optimization=True,
        )

    @classmethod
    def create_high_quality(cls) -> 'PipelineConfig':
        """Create configuration optimized for quality"""
        return cls(
            quality_level=QualityLevel.HIGH,
            policy_config=PolicyConfig(target=OutputTarget.QUALITY),
            performance_config=PerformanceConfig(
                enable_caching=True,
                parallel_processing=False,
                max_workers=2,
                memory_limit_mb=1024,
            ),
            enable_text_fixes=True,
            enable_group_flattening=False,  # Preserve structure
            enable_path_optimization=False,  # Preserve original paths
            enable_image_conversion=True,
        )

    @classmethod
    def create_debug(cls) -> 'PipelineConfig':
        """Create configuration for debugging and analysis"""
        return cls(
            quality_level=QualityLevel.BALANCED,
            output_format=OutputFormat.DEBUG_JSON,
            enable_debug=True,
            verbose_logging=True,
            performance_config=PerformanceConfig(
                enable_caching=False,
                parallel_processing=False,
                max_workers=1,
                memory_limit_mb=1024,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary"""
        result = {
            'quality_level': self.quality_level.value,
            'output_format': self.output_format.value,
            'slide_config': {
                'width_emu': self.slide_config.width_emu,
                'height_emu': self.slide_config.height_emu,
                'template': self.slide_config.template,
                'preserve_aspect_ratio': self.slide_config.preserve_aspect_ratio,
            },
            'performance_config': {
                'enable_caching': self.performance_config.enable_caching,
                'parallel_processing': self.performance_config.parallel_processing,
                'max_workers': self.performance_config.max_workers,
                'memory_limit_mb': self.performance_config.memory_limit_mb,
            },
            'enable_debug': self.enable_debug,
            'verbose_logging': self.verbose_logging,
            'enable_text_fixes': self.enable_text_fixes,
            'enable_group_flattening': self.enable_group_flattening,
            'enable_path_optimization': self.enable_path_optimization,
            'enable_image_conversion': self.enable_image_conversion,
        }

        # Add policy config if present
        if self.policy_config:
            result['policy_target'] = self.policy_config.target.value

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'PipelineConfig':
        """Create configuration from dictionary"""
        config = cls()

        if 'quality_level' in data:
            config.quality_level = QualityLevel(data['quality_level'])

        if 'output_format' in data:
            config.output_format = OutputFormat(data['output_format'])

        if 'policy_target' in data:
            target = OutputTarget(data['policy_target'])
            config.policy_config = PolicyConfig(target=target)

        if 'slide_config' in data:
            slide_data = data['slide_config']
            config.slide_config = SlideConfig(**slide_data)

        if 'performance_config' in data:
            perf_data = data['performance_config']
            config.performance_config = PerformanceConfig(**perf_data)

        # Copy simple boolean flags
        for flag in ['enable_debug', 'verbose_logging', 'enable_text_fixes',
                    'enable_group_flattening', 'enable_path_optimization',
                    'enable_image_conversion']:
            if flag in data:
                setattr(config, flag, data[flag])

        return config
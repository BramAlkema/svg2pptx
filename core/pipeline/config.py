#!/usr/bin/env python3
"""
Pipeline Configuration

Configuration classes for the clean slate conversion pipeline.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


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
class PolicyThresholds:
    """Thresholds for policy decisions"""
    path_complexity_threshold: float = 0.7
    text_complexity_threshold: float = 0.6
    group_nesting_threshold: int = 3
    image_size_threshold: int = 1024 * 1024  # 1MB

    # EMF fallback thresholds
    emf_path_segments: int = 50
    emf_text_runs: int = 20
    emf_group_children: int = 10


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
    """Complete pipeline configuration"""
    # Quality and output settings
    quality_level: QualityLevel = QualityLevel.BALANCED
    output_format: OutputFormat = OutputFormat.PPTX

    # Policy thresholds
    policy_thresholds: PolicyThresholds = None

    # Slide configuration
    slide_config: SlideConfig = None

    # Performance settings
    performance_config: PerformanceConfig = None

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
        if self.policy_thresholds is None:
            self.policy_thresholds = PolicyThresholds()

        if self.slide_config is None:
            self.slide_config = SlideConfig()

        if self.performance_config is None:
            self.performance_config = PerformanceConfig()

    @classmethod
    def create_fast(cls) -> 'PipelineConfig':
        """Create configuration optimized for speed"""
        return cls(
            quality_level=QualityLevel.FAST,
            policy_thresholds=PolicyThresholds(
                path_complexity_threshold=0.5,
                text_complexity_threshold=0.4,
                group_nesting_threshold=2,
                emf_path_segments=30,
                emf_text_runs=10,
                emf_group_children=5
            ),
            performance_config=PerformanceConfig(
                enable_caching=True,
                parallel_processing=True,
                max_workers=8,
                memory_limit_mb=256
            ),
            enable_group_flattening=True,
            enable_path_optimization=True
        )

    @classmethod
    def create_high_quality(cls) -> 'PipelineConfig':
        """Create configuration optimized for quality"""
        return cls(
            quality_level=QualityLevel.HIGH,
            policy_thresholds=PolicyThresholds(
                path_complexity_threshold=0.9,
                text_complexity_threshold=0.8,
                group_nesting_threshold=5,
                emf_path_segments=100,
                emf_text_runs=50,
                emf_group_children=20
            ),
            performance_config=PerformanceConfig(
                enable_caching=True,
                parallel_processing=False,
                max_workers=2,
                memory_limit_mb=1024
            ),
            enable_text_fixes=True,
            enable_group_flattening=False,  # Preserve structure
            enable_path_optimization=False,  # Preserve original paths
            enable_image_conversion=True
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
                memory_limit_mb=1024
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'quality_level': self.quality_level.value,
            'output_format': self.output_format.value,
            'policy_thresholds': {
                'path_complexity_threshold': self.policy_thresholds.path_complexity_threshold,
                'text_complexity_threshold': self.policy_thresholds.text_complexity_threshold,
                'group_nesting_threshold': self.policy_thresholds.group_nesting_threshold,
                'image_size_threshold': self.policy_thresholds.image_size_threshold,
                'emf_path_segments': self.policy_thresholds.emf_path_segments,
                'emf_text_runs': self.policy_thresholds.emf_text_runs,
                'emf_group_children': self.policy_thresholds.emf_group_children
            },
            'slide_config': {
                'width_emu': self.slide_config.width_emu,
                'height_emu': self.slide_config.height_emu,
                'template': self.slide_config.template,
                'preserve_aspect_ratio': self.slide_config.preserve_aspect_ratio
            },
            'performance_config': {
                'enable_caching': self.performance_config.enable_caching,
                'parallel_processing': self.performance_config.parallel_processing,
                'max_workers': self.performance_config.max_workers,
                'memory_limit_mb': self.performance_config.memory_limit_mb
            },
            'enable_debug': self.enable_debug,
            'verbose_logging': self.verbose_logging,
            'enable_text_fixes': self.enable_text_fixes,
            'enable_group_flattening': self.enable_group_flattening,
            'enable_path_optimization': self.enable_path_optimization,
            'enable_image_conversion': self.enable_image_conversion
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelineConfig':
        """Create configuration from dictionary"""
        config = cls()

        if 'quality_level' in data:
            config.quality_level = QualityLevel(data['quality_level'])

        if 'output_format' in data:
            config.output_format = OutputFormat(data['output_format'])

        if 'policy_thresholds' in data:
            thresholds_data = data['policy_thresholds']
            config.policy_thresholds = PolicyThresholds(**thresholds_data)

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
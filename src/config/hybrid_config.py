#!/usr/bin/env python3
"""
Hybrid Conversion Configuration

Configuration classes for hybrid conversion mode that combines
the existing mature system with the clean slate architecture.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ConversionMode(Enum):
    """Conversion mode options"""
    EXISTING_ONLY = "existing_only"     # Use only existing converter system
    CLEAN_SLATE_ONLY = "clean_slate_only"  # Use only clean slate architecture
    HYBRID = "hybrid"                   # Use hybrid bridge approach


@dataclass
class PolicyThresholds:
    """Policy thresholds for hybrid conversion decisions"""
    # Complexity thresholds for routing decisions
    path_complexity_threshold: float = 0.7
    text_complexity_threshold: float = 0.6
    group_nesting_threshold: int = 3
    image_size_threshold: int = 1024 * 1024  # 1MB

    # Element count thresholds for EMF fallback
    max_path_segments: int = 50
    max_text_runs: int = 20
    max_group_children: int = 10

    # Performance optimization thresholds
    prefer_native_for_simple: bool = True
    emf_fallback_for_filters: bool = True


@dataclass
class FeatureFlags:
    """Feature flags for selective clean slate functionality"""
    # Element type flags - which elements use clean slate path
    use_clean_slate_paths: bool = False
    use_clean_slate_text: bool = False
    use_clean_slate_groups: bool = False
    use_clean_slate_images: bool = False

    # Integration flags - which existing services to reuse
    use_existing_path_system: bool = True
    use_existing_color_system: bool = True
    use_existing_filter_system: bool = True
    use_existing_style_service: bool = True
    use_existing_viewport_engine: bool = True

    # Performance optimization flags
    enable_policy_caching: bool = True
    enable_mapper_caching: bool = True
    enable_parallel_mapping: bool = False


@dataclass
class PerformanceConfig:
    """Performance settings for hybrid mode"""
    # Caching settings
    enable_decision_cache: bool = True
    cache_size_limit: int = 1000
    cache_ttl_seconds: int = 300

    # Parallel processing
    max_parallel_mappers: int = 4
    parallel_threshold: int = 10  # Minimum elements for parallel processing

    # Memory management
    memory_limit_mb: int = 512
    gc_frequency: int = 100  # Run GC every N conversions


@dataclass
class HybridConversionConfig:
    """Configuration for hybrid conversion mode"""
    # Mode selection
    conversion_mode: ConversionMode = ConversionMode.EXISTING_ONLY
    clean_slate_elements: List[str] = field(default_factory=list)

    # Policy configuration
    policy_thresholds: PolicyThresholds = field(default_factory=PolicyThresholds)

    # Feature toggles
    feature_flags: FeatureFlags = field(default_factory=FeatureFlags)

    # Performance settings
    performance_config: PerformanceConfig = field(default_factory=PerformanceConfig)

    # Debugging and monitoring
    enable_debug_logging: bool = False
    enable_performance_monitoring: bool = False
    log_policy_decisions: bool = False

    @classmethod
    def create_existing_only(cls) -> 'HybridConversionConfig':
        """Create configuration using only existing system"""
        return cls(
            conversion_mode=ConversionMode.EXISTING_ONLY,
            feature_flags=FeatureFlags(
                # All clean slate features disabled
                use_clean_slate_paths=False,
                use_clean_slate_text=False,
                use_clean_slate_groups=False,
                use_clean_slate_images=False,
                # All existing systems enabled
                use_existing_path_system=True,
                use_existing_color_system=True,
                use_existing_filter_system=True,
                use_existing_style_service=True,
                use_existing_viewport_engine=True
            )
        )

    @classmethod
    def create_clean_slate_only(cls) -> 'HybridConversionConfig':
        """Create configuration using only clean slate architecture"""
        return cls(
            conversion_mode=ConversionMode.CLEAN_SLATE_ONLY,
            clean_slate_elements=['path', 'text', 'group', 'image'],
            feature_flags=FeatureFlags(
                # All clean slate features enabled
                use_clean_slate_paths=True,
                use_clean_slate_text=True,
                use_clean_slate_groups=True,
                use_clean_slate_images=True,
                # Selectively use existing systems for compatibility
                use_existing_path_system=False,
                use_existing_color_system=True,  # Keep for stability
                use_existing_filter_system=True,  # Keep for completeness
                use_existing_style_service=True,  # Keep for CSS parsing
                use_existing_viewport_engine=True  # Keep for viewport handling
            )
        )

    @classmethod
    def create_hybrid_paths_only(cls) -> 'HybridConversionConfig':
        """Create hybrid configuration with clean slate paths only"""
        return cls(
            conversion_mode=ConversionMode.HYBRID,
            clean_slate_elements=['path'],
            policy_thresholds=PolicyThresholds(
                path_complexity_threshold=0.6,  # Lower threshold for more clean slate usage
                prefer_native_for_simple=True
            ),
            feature_flags=FeatureFlags(
                use_clean_slate_paths=True,
                use_clean_slate_text=False,
                use_clean_slate_groups=False,
                use_clean_slate_images=False,
                use_existing_path_system=True,  # Inject into PathMapper
                use_existing_color_system=True,
                use_existing_filter_system=True,
                use_existing_style_service=True,
                use_existing_viewport_engine=True
            )
        )

    @classmethod
    def create_hybrid_text_and_paths(cls) -> 'HybridConversionConfig':
        """Create hybrid configuration with clean slate paths and text"""
        return cls(
            conversion_mode=ConversionMode.HYBRID,
            clean_slate_elements=['path', 'text'],
            policy_thresholds=PolicyThresholds(
                path_complexity_threshold=0.7,
                text_complexity_threshold=0.6,
                prefer_native_for_simple=True
            ),
            feature_flags=FeatureFlags(
                use_clean_slate_paths=True,
                use_clean_slate_text=True,
                use_clean_slate_groups=False,
                use_clean_slate_images=False,
                use_existing_path_system=True,
                use_existing_color_system=True,
                use_existing_filter_system=True,
                use_existing_style_service=True,
                use_existing_viewport_engine=True
            )
        )

    @classmethod
    def create_full_hybrid(cls) -> 'HybridConversionConfig':
        """Create full hybrid configuration with all elements"""
        return cls(
            conversion_mode=ConversionMode.HYBRID,
            clean_slate_elements=['path', 'text', 'group', 'image'],
            policy_thresholds=PolicyThresholds(
                path_complexity_threshold=0.7,
                text_complexity_threshold=0.6,
                group_nesting_threshold=3,
                image_size_threshold=1024 * 1024
            ),
            feature_flags=FeatureFlags(
                use_clean_slate_paths=True,
                use_clean_slate_text=True,
                use_clean_slate_groups=True,
                use_clean_slate_images=True,
                use_existing_path_system=True,
                use_existing_color_system=True,
                use_existing_filter_system=True,
                use_existing_style_service=True,
                use_existing_viewport_engine=True,
                enable_policy_caching=True,
                enable_mapper_caching=True
            ),
            performance_config=PerformanceConfig(
                enable_decision_cache=True,
                max_parallel_mappers=4,
                parallel_threshold=5
            )
        )

    def should_use_clean_slate_for_element(self, element_type: str) -> bool:
        """Check if clean slate should be used for a specific element type"""
        if self.conversion_mode == ConversionMode.EXISTING_ONLY:
            return False
        elif self.conversion_mode == ConversionMode.CLEAN_SLATE_ONLY:
            return True
        else:  # HYBRID mode
            return element_type in self.clean_slate_elements

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization"""
        return {
            'conversion_mode': self.conversion_mode.value,
            'clean_slate_elements': self.clean_slate_elements,
            'policy_thresholds': {
                'path_complexity_threshold': self.policy_thresholds.path_complexity_threshold,
                'text_complexity_threshold': self.policy_thresholds.text_complexity_threshold,
                'group_nesting_threshold': self.policy_thresholds.group_nesting_threshold,
                'image_size_threshold': self.policy_thresholds.image_size_threshold,
                'max_path_segments': self.policy_thresholds.max_path_segments,
                'max_text_runs': self.policy_thresholds.max_text_runs,
                'max_group_children': self.policy_thresholds.max_group_children,
                'prefer_native_for_simple': self.policy_thresholds.prefer_native_for_simple,
                'emf_fallback_for_filters': self.policy_thresholds.emf_fallback_for_filters
            },
            'feature_flags': {
                'use_clean_slate_paths': self.feature_flags.use_clean_slate_paths,
                'use_clean_slate_text': self.feature_flags.use_clean_slate_text,
                'use_clean_slate_groups': self.feature_flags.use_clean_slate_groups,
                'use_clean_slate_images': self.feature_flags.use_clean_slate_images,
                'use_existing_path_system': self.feature_flags.use_existing_path_system,
                'use_existing_color_system': self.feature_flags.use_existing_color_system,
                'use_existing_filter_system': self.feature_flags.use_existing_filter_system,
                'use_existing_style_service': self.feature_flags.use_existing_style_service,
                'use_existing_viewport_engine': self.feature_flags.use_existing_viewport_engine,
                'enable_policy_caching': self.feature_flags.enable_policy_caching,
                'enable_mapper_caching': self.feature_flags.enable_mapper_caching,
                'enable_parallel_mapping': self.feature_flags.enable_parallel_mapping
            },
            'performance_config': {
                'enable_decision_cache': self.performance_config.enable_decision_cache,
                'cache_size_limit': self.performance_config.cache_size_limit,
                'cache_ttl_seconds': self.performance_config.cache_ttl_seconds,
                'max_parallel_mappers': self.performance_config.max_parallel_mappers,
                'parallel_threshold': self.performance_config.parallel_threshold,
                'memory_limit_mb': self.performance_config.memory_limit_mb,
                'gc_frequency': self.performance_config.gc_frequency
            },
            'enable_debug_logging': self.enable_debug_logging,
            'enable_performance_monitoring': self.enable_performance_monitoring,
            'log_policy_decisions': self.log_policy_decisions
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HybridConversionConfig':
        """Create configuration from dictionary"""
        config = cls()

        if 'conversion_mode' in data:
            config.conversion_mode = ConversionMode(data['conversion_mode'])

        if 'clean_slate_elements' in data:
            config.clean_slate_elements = data['clean_slate_elements']

        if 'policy_thresholds' in data:
            threshold_data = data['policy_thresholds']
            config.policy_thresholds = PolicyThresholds(**threshold_data)

        if 'feature_flags' in data:
            flag_data = data['feature_flags']
            config.feature_flags = FeatureFlags(**flag_data)

        if 'performance_config' in data:
            perf_data = data['performance_config']
            config.performance_config = PerformanceConfig(**perf_data)

        # Copy simple boolean flags
        for flag in ['enable_debug_logging', 'enable_performance_monitoring', 'log_policy_decisions']:
            if flag in data:
                setattr(config, flag, data[flag])

        return config
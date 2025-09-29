#!/usr/bin/env python3
"""
Converter Pattern Templates for SVG Test Generation.

This module provides templates for generating SVG test cases specifically
designed to test converter modules in the svg2pptx system. Each template
corresponds to converter functionality and edge cases.
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ConverterType(Enum):
    """Types of converters available in the system."""
    SHAPES = "shapes"
    PATHS = "paths"
    TEXT = "text"
    GRADIENTS = "gradients"
    FILTERS = "filters"
    TRANSFORMS = "transforms"
    GROUPS = "groups"
    IMAGES = "images"
    MARKERS = "markers"
    MASKING = "masking"
    SYMBOLS = "symbols"
    ANIMATIONS = "animations"


@dataclass
class ConverterTestPattern:
    """Template pattern for converter testing."""
    name: str
    converter_type: ConverterType
    svg_elements: List[str]
    test_scenarios: List[str]
    edge_cases: List[str]
    performance_variants: List[str]
    expected_behaviors: Dict[str, Any]


class ConverterPatternLibrary:
    """Library of converter-specific test patterns."""

    def __init__(self):
        """Initialize pattern library with all converter patterns."""
        self.patterns = self._create_patterns()

    def _create_patterns(self) -> Dict[ConverterType, ConverterTestPattern]:
        """Create all converter test patterns."""
        return {
            ConverterType.SHAPES: self._create_shapes_pattern(),
            ConverterType.PATHS: self._create_paths_pattern(),
            ConverterType.TEXT: self._create_text_pattern(),
            ConverterType.GRADIENTS: self._create_gradients_pattern(),
            ConverterType.FILTERS: self._create_filters_pattern(),
            ConverterType.TRANSFORMS: self._create_transforms_pattern(),
            ConverterType.GROUPS: self._create_groups_pattern(),
            ConverterType.IMAGES: self._create_images_pattern(),
            ConverterType.MARKERS: self._create_markers_pattern(),
            ConverterType.MASKING: self._create_masking_pattern(),
            ConverterType.SYMBOLS: self._create_symbols_pattern(),
            ConverterType.ANIMATIONS: self._create_animations_pattern(),
        }

    def _create_shapes_pattern(self) -> ConverterTestPattern:
        """Create test pattern for shapes converter."""
        return ConverterTestPattern(
            name="Enhanced Shape Converter",
            converter_type=ConverterType.SHAPES,
            svg_elements=['rect', 'circle', 'ellipse', 'polygon', 'polyline', 'line'],
            test_scenarios=[
                'basic_shapes_individual',
                'basic_shapes_with_styling',
                'shapes_with_transforms',
                'shapes_with_gradients',
                'nested_shapes_in_groups',
                'shapes_with_filters',
                'batch_processing_multiple_shapes'
            ],
            edge_cases=[
                'zero_dimensions_shapes',
                'negative_coordinates',
                'extremely_large_shapes',
                'extremely_small_shapes',
                'invalid_shape_parameters',
                'missing_required_attributes',
                'malformed_point_data'
            ],
            performance_variants=[
                'single_shape_conversion',
                'batch_10_shapes',
                'batch_100_shapes',
                'batch_1000_shapes',
                'mixed_shape_types_batch',
                'complex_styling_batch',
                'deep_nesting_batch'
            ],
            expected_behaviors={
                'can_convert': 'should return True for supported elements',
                'convert': 'should return valid DrawingML XML',
                'batch_processing': 'should be 25-70x faster than individual',
                'error_handling': 'should gracefully handle invalid input',
                'coordinate_transformation': 'should use EMU coordinate system'
            }
        )

    def _create_paths_pattern(self) -> ConverterTestPattern:
        """Create test pattern for paths converter."""
        return ConverterTestPattern(
            name="Path Converter",
            converter_type=ConverterType.PATHS,
            svg_elements=['path'],
            test_scenarios=[
                'simple_line_paths',
                'bezier_curve_paths',
                'arc_segment_paths',
                'complex_mixed_commands',
                'closed_paths_with_z',
                'relative_coordinate_paths',
                'absolute_coordinate_paths',
                'path_with_styling'
            ],
            edge_cases=[
                'empty_path_data',
                'invalid_path_commands',
                'extremely_long_paths',
                'paths_with_floating_point_precision',
                'paths_with_scientific_notation',
                'malformed_command_sequences',
                'missing_coordinate_values'
            ],
            performance_variants=[
                'simple_path_conversion',
                'complex_path_with_many_commands',
                'batch_path_processing',
                'deeply_nested_curve_paths',
                'paths_with_high_precision_coordinates'
            ],
            expected_behaviors={
                'command_parsing': 'should parse all SVG path commands',
                'coordinate_precision': 'should maintain acceptable precision',
                'curve_conversion': 'should convert Bezier curves to DrawingML',
                'arc_handling': 'should convert arcs to appropriate curves',
                'optimization': 'should optimize path data for PowerPoint'
            }
        )

    def _create_text_pattern(self) -> ConverterTestPattern:
        """Create test pattern for text converter."""
        return ConverterTestPattern(
            name="Text Converter",
            converter_type=ConverterType.TEXT,
            svg_elements=['text', 'tspan', 'textPath'],
            test_scenarios=[
                'simple_text_elements',
                'text_with_font_styling',
                'text_with_positioning',
                'multiline_text_with_tspan',
                'text_along_path',
                'text_with_transforms',
                'text_with_colors_and_gradients',
                'text_with_special_characters'
            ],
            edge_cases=[
                'empty_text_content',
                'text_with_unicode_characters',
                'text_with_very_long_strings',
                'text_with_missing_font_family',
                'text_with_invalid_font_sizes',
                'text_with_extreme_positioning',
                'nested_tspan_elements'
            ],
            performance_variants=[
                'single_text_element',
                'multiple_text_elements',
                'complex_formatted_text',
                'text_with_font_embedding',
                'large_text_blocks'
            ],
            expected_behaviors={
                'font_handling': 'should handle font family fallbacks',
                'positioning': 'should position text correctly in EMU',
                'styling': 'should preserve text formatting',
                'encoding': 'should handle Unicode text properly',
                'path_text': 'should convert textPath to appropriate format'
            }
        )

    def _create_gradients_pattern(self) -> ConverterTestPattern:
        """Create test pattern for gradients converter."""
        return ConverterTestPattern(
            name="Gradients Converter",
            converter_type=ConverterType.GRADIENTS,
            svg_elements=['linearGradient', 'radialGradient', 'meshGradient'],
            test_scenarios=[
                'simple_linear_gradients',
                'simple_radial_gradients',
                'gradients_with_multiple_stops',
                'gradients_with_transforms',
                'gradients_with_opacity',
                'nested_gradient_references',
                'advanced_mesh_gradients',
                'gradient_units_objectBoundingBox'
            ],
            edge_cases=[
                'gradients_with_zero_stops',
                'gradients_with_single_stop',
                'gradients_with_invalid_colors',
                'gradients_with_missing_references',
                'circular_gradient_references',
                'gradients_with_extreme_coordinates',
                'malformed_gradient_definitions'
            ],
            performance_variants=[
                'simple_gradient_processing',
                'complex_multi_stop_gradients',
                'batch_gradient_processing',
                'gradients_with_high_resolution',
                'nested_gradient_inheritance'
            ],
            expected_behaviors={
                'color_interpolation': 'should interpolate colors correctly',
                'coordinate_mapping': 'should map gradient coordinates to EMU',
                'fallback_handling': 'should provide solid color fallbacks',
                'optimization': 'should optimize for PowerPoint limitations',
                'inheritance': 'should handle gradient inheritance properly'
            }
        )

    def _create_filters_pattern(self) -> ConverterTestPattern:
        """Create test pattern for filters converter."""
        return ConverterTestPattern(
            name="Filters Converter",
            converter_type=ConverterType.FILTERS,
            svg_elements=['filter', 'feGaussianBlur', 'feDropShadow', 'feColorMatrix'],
            test_scenarios=[
                'basic_gaussian_blur',
                'drop_shadow_effects',
                'color_matrix_transformations',
                'chained_filter_effects',
                'filters_with_animations',
                'filters_on_groups',
                'filters_with_masks',
                'complex_filter_compositions'
            ],
            edge_cases=[
                'filters_with_zero_radius',
                'filters_with_extreme_values',
                'filters_with_missing_primitives',
                'circular_filter_references',
                'filters_with_invalid_regions',
                'unsupported_filter_primitives',
                'filters_with_empty_definitions'
            ],
            performance_variants=[
                'simple_filter_application',
                'complex_filter_chains',
                'filters_on_large_elements',
                'batch_filter_processing',
                'high_complexity_filters'
            ],
            expected_behaviors={
                'effect_simulation': 'should simulate filters in PowerPoint',
                'fallback_strategies': 'should provide fallbacks for unsupported filters',
                'performance_optimization': 'should optimize filter processing',
                'quality_preservation': 'should maintain visual quality',
                'compatibility': 'should work across PowerPoint versions'
            }
        )

    def _create_transforms_pattern(self) -> ConverterTestPattern:
        """Create test pattern for transforms converter."""
        return ConverterTestPattern(
            name="Transforms Converter",
            converter_type=ConverterType.TRANSFORMS,
            svg_elements=['g'],  # transforms are attributes, not elements
            test_scenarios=[
                'simple_translate_transforms',
                'rotation_transforms',
                'scale_transforms',
                'skew_transforms',
                'matrix_transforms',
                'combined_transforms',
                'nested_transform_inheritance',
                'transforms_with_animation'
            ],
            edge_cases=[
                'identity_transforms',
                'zero_scale_transforms',
                'extreme_rotation_angles',
                'invalid_matrix_values',
                'transforms_with_infinity_values',
                'deeply_nested_transforms',
                'transforms_with_precision_issues'
            ],
            performance_variants=[
                'simple_transform_application',
                'complex_transform_chains',
                'batch_transform_processing',
                'high_precision_transforms',
                'deeply_nested_transforms'
            ],
            expected_behaviors={
                'matrix_calculation': 'should calculate transform matrices correctly',
                'coordinate_transformation': 'should transform coordinates to EMU',
                'inheritance': 'should handle transform inheritance properly',
                'optimization': 'should optimize transform chains',
                'precision': 'should maintain acceptable precision'
            }
        )

    def _create_groups_pattern(self) -> ConverterTestPattern:
        """Create test pattern for groups converter."""
        return ConverterTestPattern(
            name="Groups Converter",
            converter_type=ConverterType.GROUPS,
            svg_elements=['g'],
            test_scenarios=[
                'simple_element_grouping',
                'nested_group_hierarchies',
                'groups_with_transforms',
                'groups_with_styling',
                'groups_with_clipping',
                'groups_with_filters',
                'groups_with_opacity',
                'complex_nested_structures'
            ],
            edge_cases=[
                'empty_groups',
                'groups_with_only_metadata',
                'deeply_nested_groups',
                'groups_with_circular_references',
                'groups_with_invalid_children',
                'groups_with_extreme_nesting',
                'malformed_group_structures'
            ],
            performance_variants=[
                'simple_group_processing',
                'complex_nested_groups',
                'large_group_hierarchies',
                'groups_with_many_children',
                'deeply_nested_structures'
            ],
            expected_behaviors={
                'hierarchy_preservation': 'should preserve group hierarchy',
                'attribute_inheritance': 'should handle attribute inheritance',
                'transform_propagation': 'should propagate transforms correctly',
                'optimization': 'should optimize group structures',
                'clipping': 'should handle group-level clipping'
            }
        )

    def _create_images_pattern(self) -> ConverterTestPattern:
        """Create test pattern for images converter."""
        return ConverterTestPattern(
            name="Images Converter",
            converter_type=ConverterType.IMAGES,
            svg_elements=['image'],
            test_scenarios=[
                'external_image_references',
                'embedded_base64_images',
                'images_with_transforms',
                'images_with_clipping',
                'images_with_opacity',
                'images_with_filters',
                'scaled_and_positioned_images',
                'images_with_preserveAspectRatio'
            ],
            edge_cases=[
                'missing_image_references',
                'invalid_image_formats',
                'corrupted_base64_data',
                'images_with_zero_dimensions',
                'images_with_extreme_scaling',
                'images_with_invalid_urls',
                'malformed_image_elements'
            ],
            performance_variants=[
                'single_image_processing',
                'multiple_image_processing',
                'large_image_handling',
                'base64_image_processing',
                'complex_image_transformations'
            ],
            expected_behaviors={
                'image_embedding': 'should embed images in PowerPoint',
                'format_conversion': 'should handle different image formats',
                'scaling': 'should scale images appropriately',
                'aspect_ratio': 'should preserve aspect ratios when needed',
                'error_handling': 'should handle missing images gracefully'
            }
        )

    def _create_markers_pattern(self) -> ConverterTestPattern:
        """Create test pattern for markers converter."""
        return ConverterTestPattern(
            name="Markers Converter",
            converter_type=ConverterType.MARKERS,
            svg_elements=['marker'],
            test_scenarios=[
                'simple_arrow_markers',
                'custom_marker_shapes',
                'markers_on_paths',
                'markers_on_lines',
                'markers_with_transforms',
                'markers_with_styling',
                'start_mid_end_markers',
                'markers_with_scaling'
            ],
            edge_cases=[
                'markers_with_zero_dimensions',
                'markers_with_missing_definitions',
                'circular_marker_references',
                'markers_with_invalid_viewbox',
                'markers_with_extreme_scaling',
                'malformed_marker_elements',
                'markers_with_complex_content'
            ],
            performance_variants=[
                'simple_marker_application',
                'complex_marker_shapes',
                'multiple_markers_on_paths',
                'batch_marker_processing',
                'markers_with_animations'
            ],
            expected_behaviors={
                'marker_placement': 'should place markers correctly on paths',
                'orientation': 'should orient markers properly',
                'scaling': 'should scale markers appropriately',
                'styling': 'should apply marker styling correctly',
                'inheritance': 'should handle marker inheritance'
            }
        )

    def _create_masking_pattern(self) -> ConverterTestPattern:
        """Create test pattern for masking converter."""
        return ConverterTestPattern(
            name="Masking Converter",
            converter_type=ConverterType.MASKING,
            svg_elements=['mask', 'clipPath'],
            test_scenarios=[
                'simple_rectangular_masks',
                'complex_path_masks',
                'nested_masking_operations',
                'masks_with_gradients',
                'masks_with_transforms',
                'clipPath_operations',
                'masks_with_opacity',
                'combined_masks_and_clips'
            ],
            edge_cases=[
                'empty_mask_definitions',
                'masks_with_no_content',
                'circular_mask_references',
                'masks_with_invalid_units',
                'extremely_complex_masks',
                'masks_with_missing_references',
                'malformed_mask_elements'
            ],
            performance_variants=[
                'simple_mask_application',
                'complex_mask_shapes',
                'nested_mask_operations',
                'batch_mask_processing',
                'high_resolution_masks'
            ],
            expected_behaviors={
                'mask_application': 'should apply masks correctly',
                'clipping': 'should handle clipPath operations',
                'transparency': 'should handle mask transparency',
                'optimization': 'should optimize mask operations',
                'fallback': 'should provide fallbacks for unsupported masks'
            }
        )

    def _create_symbols_pattern(self) -> ConverterTestPattern:
        """Create test pattern for symbols converter."""
        return ConverterTestPattern(
            name="Symbols Converter",
            converter_type=ConverterType.SYMBOLS,
            svg_elements=['symbol', 'use'],
            test_scenarios=[
                'simple_symbol_definitions',
                'symbol_reuse_with_use',
                'symbols_with_transforms',
                'symbols_with_styling',
                'nested_symbol_structures',
                'symbols_with_viewbox',
                'symbols_with_clipping',
                'cross_referenced_symbols'
            ],
            edge_cases=[
                'undefined_symbol_references',
                'circular_symbol_references',
                'symbols_with_missing_content',
                'symbols_with_invalid_viewbox',
                'deeply_nested_symbols',
                'symbols_with_extreme_scaling',
                'malformed_symbol_elements'
            ],
            performance_variants=[
                'simple_symbol_instantiation',
                'complex_symbol_reuse',
                'multiple_symbol_instances',
                'deeply_nested_symbols',
                'batch_symbol_processing'
            ],
            expected_behaviors={
                'symbol_instantiation': 'should instantiate symbols correctly',
                'reuse_optimization': 'should optimize symbol reuse',
                'transform_application': 'should apply transforms to instances',
                'inheritance': 'should handle symbol inheritance',
                'reference_resolution': 'should resolve symbol references'
            }
        )

    def _create_animations_pattern(self) -> ConverterTestPattern:
        """Create test pattern for animations converter."""
        return ConverterTestPattern(
            name="Animations Converter",
            converter_type=ConverterType.ANIMATIONS,
            svg_elements=['animate', 'animateTransform', 'animateMotion'],
            test_scenarios=[
                'simple_property_animations',
                'transform_animations',
                'motion_path_animations',
                'color_animations',
                'opacity_animations',
                'complex_animation_sequences',
                'synchronized_animations',
                'animations_with_timing'
            ],
            edge_cases=[
                'animations_with_zero_duration',
                'animations_with_invalid_values',
                'circular_animation_references',
                'animations_with_missing_targets',
                'animations_with_extreme_values',
                'malformed_animation_elements',
                'animations_with_complex_timing'
            ],
            performance_variants=[
                'simple_animation_processing',
                'complex_animation_sequences',
                'multiple_simultaneous_animations',
                'long_duration_animations',
                'high_frequency_animations'
            ],
            expected_behaviors={
                'animation_conversion': 'should convert to PowerPoint animations',
                'timing_preservation': 'should preserve animation timing',
                'interpolation': 'should handle value interpolation',
                'synchronization': 'should sync multiple animations',
                'fallback': 'should provide static fallbacks'
            }
        )

    def get_pattern(self, converter_type: ConverterType) -> Optional[ConverterTestPattern]:
        """Get test pattern for specific converter type."""
        return self.patterns.get(converter_type)

    def get_all_patterns(self) -> Dict[ConverterType, ConverterTestPattern]:
        """Get all converter test patterns."""
        return self.patterns

    def get_elements_for_converter(self, converter_type: ConverterType) -> List[str]:
        """Get SVG elements handled by specific converter."""
        pattern = self.get_pattern(converter_type)
        return pattern.svg_elements if pattern else []

    def get_test_scenarios_for_converter(self, converter_type: ConverterType) -> List[str]:
        """Get test scenarios for specific converter."""
        pattern = self.get_pattern(converter_type)
        return pattern.test_scenarios if pattern else []

    def get_edge_cases_for_converter(self, converter_type: ConverterType) -> List[str]:
        """Get edge cases for specific converter."""
        pattern = self.get_pattern(converter_type)
        return pattern.edge_cases if pattern else []

    def get_performance_variants_for_converter(self, converter_type: ConverterType) -> List[str]:
        """Get performance test variants for specific converter."""
        pattern = self.get_pattern(converter_type)
        return pattern.performance_variants if pattern else []


# Convenience function for easy access
def get_converter_patterns() -> ConverterPatternLibrary:
    """Get initialized converter pattern library."""
    return ConverterPatternLibrary()
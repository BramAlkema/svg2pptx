#!/usr/bin/env python3
"""
Core SVG Filter Processing System

This module provides the foundation for SVG filter processing in the clean slate
architecture, combining policy-driven decision making with template-based XML
generation for high-fidelity PowerPoint conversion.
"""

from .base import (
    FilterProcessor,
    FilterContext,
    FilterResult,
    FilterStrategy,
    FilterException,
    FilterValidationError,
    create_filter_context
)
from .factory import (
    FilterFactory,
    FilterRegistrationError,
    FilterNotFoundError,
    create_filter_factory
)
from .offset import (
    OffsetProcessor,
    OffsetParameters,
    OffsetFilterException,
    create_offset_processor
)
from .flood import (
    FloodProcessor,
    FloodParameters,
    FloodFilterException,
    create_flood_processor
)
from .blend import (
    BlendProcessor,
    BlendParameters,
    BlendMode,
    BlendFilterException,
    create_blend_processor
)
from .color_matrix import (
    ColorMatrixProcessor,
    ColorMatrixParameters,
    ColorMatrixType,
    ColorMatrixFilterException,
    create_color_matrix_processor
)
from .composite import (
    CompositeProcessor,
    CompositeParameters,
    CompositeOperator,
    CompositeFilterException,
    create_composite_processor
)
from .morphology import (
    MorphologyProcessor,
    MorphologyParameters,
    MorphologyOperator,
    MorphologyFilterException,
    create_morphology_processor
)
from .component_transfer import (
    ComponentTransferProcessor,
    ComponentTransferParameters,
    ComponentTransferException,
    TransferFunctionType,
    create_component_transfer_processor
)
from .convolve_matrix import (
    ConvolveMatrixProcessor,
    ConvolveMatrixParameters,
    ConvolveMatrixException,
    ConvolveMatrixValidationError,
    EdgeMode,
    create_convolve_matrix_processor
)
from .displacement_map import (
    DisplacementMapProcessor,
    DisplacementMapParameters,
    DisplacementMapException,
    DisplacementMapValidationError,
    create_displacement_map_processor
)
from .blur import (
    GaussianBlurProcessor,
    BlurParameters,
    BlurFilterException,
    BlurValidationError,
    create_gaussian_blur_processor
)
from .drop_shadow import (
    DropShadowProcessor,
    DropShadowParameters,
    DropShadowException,
    DropShadowValidationError,
    create_drop_shadow_processor
)
from .diffuse_lighting import (
    DiffuseLightingProcessor,
    DiffuseLightingParameters,
    DiffuseLightingException,
    DiffuseLightingValidationError,
    create_diffuse_lighting_processor
)
from .specular_lighting import (
    SpecularLightingProcessor,
    SpecularLightingParameters,
    SpecularLightingException,
    SpecularLightingValidationError,
    create_specular_lighting_processor
)
from .tile import (
    TileProcessor,
    TileParameters,
    TileFilterException,
    TileValidationError,
    create_tile_processor
)
from .turbulence import (
    TurbulenceProcessor,
    TurbulenceParameters,
    TurbulenceFilterException,
    TurbulenceValidationError,
    create_turbulence_processor
)
from .image import (
    ImageProcessor,
    ImageParameters,
    ImageFilterException,
    ImageValidationError,
    create_image_processor
)

__all__ = [
    "FilterProcessor",
    "FilterContext",
    "FilterResult",
    "FilterStrategy",
    "FilterException",
    "FilterValidationError",
    "create_filter_context",
    "FilterFactory",
    "FilterRegistrationError",
    "FilterNotFoundError",
    "create_filter_factory",
    "OffsetProcessor",
    "OffsetParameters",
    "OffsetFilterException",
    "create_offset_processor",
    "FloodProcessor",
    "FloodParameters",
    "FloodFilterException",
    "create_flood_processor",
    "BlendProcessor",
    "BlendParameters",
    "BlendMode",
    "BlendFilterException",
    "create_blend_processor",
    "ColorMatrixProcessor",
    "ColorMatrixParameters",
    "ColorMatrixType",
    "ColorMatrixFilterException",
    "create_color_matrix_processor",
    "CompositeProcessor",
    "CompositeParameters",
    "CompositeOperator",
    "CompositeFilterException",
    "create_composite_processor",
    "MorphologyProcessor",
    "MorphologyParameters",
    "MorphologyOperator",
    "MorphologyFilterException",
    "create_morphology_processor",
    "ComponentTransferProcessor",
    "ComponentTransferParameters",
    "ComponentTransferException",
    "TransferFunctionType",
    "create_component_transfer_processor",
    "ConvolveMatrixProcessor",
    "ConvolveMatrixParameters",
    "ConvolveMatrixException",
    "ConvolveMatrixValidationError",
    "EdgeMode",
    "create_convolve_matrix_processor",
    "DisplacementMapProcessor",
    "DisplacementMapParameters",
    "DisplacementMapException",
    "DisplacementMapValidationError",
    "create_displacement_map_processor",
    "GaussianBlurProcessor",
    "BlurParameters",
    "BlurFilterException",
    "BlurValidationError",
    "create_gaussian_blur_processor",
    "DropShadowProcessor",
    "DropShadowParameters",
    "DropShadowException",
    "DropShadowValidationError",
    "create_drop_shadow_processor",
    "DiffuseLightingProcessor",
    "DiffuseLightingParameters",
    "DiffuseLightingException",
    "DiffuseLightingValidationError",
    "create_diffuse_lighting_processor",
    "SpecularLightingProcessor",
    "SpecularLightingParameters",
    "SpecularLightingException",
    "SpecularLightingValidationError",
    "create_specular_lighting_processor",
    "TileProcessor",
    "TileParameters",
    "TileFilterException",
    "TileValidationError",
    "create_tile_processor",
    "TurbulenceProcessor",
    "TurbulenceParameters",
    "TurbulenceFilterException",
    "TurbulenceValidationError",
    "create_turbulence_processor",
    "ImageProcessor",
    "ImageParameters",
    "ImageFilterException",
    "ImageValidationError",
    "create_image_processor"
]
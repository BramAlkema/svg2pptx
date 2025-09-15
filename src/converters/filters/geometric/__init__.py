"""
Geometric transformation filters.

This module contains filter implementations for geometric transformations:
- transforms: Offset operations, turbulence generation, geometric math
- composite: Merge operations, blend modes, multi-layer processing
- morphology: Vector-first dilate/erode operations (Task 2.1)
- diffuse_lighting: Vector-first diffuse lighting with 3D effects (Task 2.2)
- specular_lighting: Vector-first specular lighting with highlights (Task 2.3)
- component_transfer: Vector-first component transfer with color effects (Task 2.4)
- displacement_map: Vector-first displacement mapping with path subdivision (Task 2.5)
- tile: EMF-based pattern system for feTile filter effects (Task 2.7)
"""

from .transforms import (
    OffsetFilter,
    TurbulenceFilter,
    OffsetFilterException,
    TurbulenceFilterException
)
from .composite import (
    CompositeFilter,
    MergeFilter,
    BlendFilter,
    CompositeFilterException,
    MergeFilterException,
    BlendFilterException
)
from .morphology import (
    MorphologyFilter,
    MorphologyParameters
)
from .diffuse_lighting import (
    DiffuseLightingFilter,
    DiffuseLightingParameters
)
from .specular_lighting import (
    SpecularLightingFilter,
    SpecularLightingParameters
)
from .component_transfer import (
    ComponentTransferFilter,
    ComponentTransferParameters
)
from .displacement_map import (
    DisplacementMapFilter,
    DisplacementMapParameters
)
from .tile import (
    TileFilter,
    TileParameters,
    TileResult
)

__all__ = [
    "OffsetFilter",
    "TurbulenceFilter",
    "OffsetFilterException",
    "TurbulenceFilterException",
    "CompositeFilter",
    "MergeFilter",
    "BlendFilter",
    "CompositeFilterException",
    "MergeFilterException",
    "BlendFilterException",
    "MorphologyFilter",
    "MorphologyParameters",
    "DiffuseLightingFilter",
    "DiffuseLightingParameters",
    "SpecularLightingFilter",
    "SpecularLightingParameters",
    "ComponentTransferFilter",
    "ComponentTransferParameters",
    "DisplacementMapFilter",
    "DisplacementMapParameters",
    "TileFilter",
    "TileParameters",
    "TileResult",
]
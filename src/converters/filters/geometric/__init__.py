"""
Geometric transformation filters.

This module contains filter implementations for geometric transformations:
- transforms: Offset operations, turbulence generation, geometric math
- composite: Merge operations, blend modes, multi-layer processing
- morphology: Vector-first dilate/erode operations (Task 2.1)
- diffuse_lighting: Vector-first diffuse lighting with 3D effects (Task 2.2)
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
]
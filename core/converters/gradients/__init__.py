"""
Gradient converters for SVG2PPTX.

Provides specialized engines for converting different gradient types:
- MeshGradientEngine: SVG 2.0 mesh gradients
"""

from .mesh_engine import MeshGradientEngine, convert_mesh_gradient, create_mesh_gradient_engine

__all__ = [
    'MeshGradientEngine',
    'convert_mesh_gradient',
    'create_mesh_gradient_engine',
]

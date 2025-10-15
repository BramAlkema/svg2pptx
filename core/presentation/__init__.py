"""
Presentation-level orchestration helpers.

These abstractions sit on top of DrawingMLEmbedder and PackageWriter to give
high-level builders a common entry point when composing PPTX output.
"""

from .composer import AssetEmbedder, PackageAssembler, PresentationComposer, SlideAssembler

__all__ = [
    "AssetEmbedder",
    "PresentationComposer",
    "PackageAssembler",
    "SlideAssembler",
]

"""Base definitions for shape generator helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import XMLBuilderBase

if TYPE_CHECKING:  # pragma: no cover
    from lxml.etree import Element


class BaseShapeGenerator:
    """Common utilities shared by shape generator implementations."""

    def __init__(self, builder: XMLBuilderBase) -> None:
        self.builder = builder

    # The methods below intentionally raise to ensure subclasses implement them.
    def generate_group_shape(self, *args, **kwargs) -> "Element":  # pragma: no cover
        raise NotImplementedError

    def generate_group_picture(self, *args, **kwargs) -> "Element":  # pragma: no cover
        raise NotImplementedError

    def generate_path_shape(self, *args, **kwargs) -> "Element":  # pragma: no cover
        raise NotImplementedError

    def generate_path_emf_picture(self, *args, **kwargs) -> "Element":  # pragma: no cover
        raise NotImplementedError

    def generate_path_emf_placeholder(self, *args, **kwargs) -> "Element":  # pragma: no cover
        raise NotImplementedError

    def generate_text_shape(self, *args, **kwargs) -> "Element":  # pragma: no cover
        raise NotImplementedError

    def generate_text_emf_picture(self, *args, **kwargs) -> "Element":  # pragma: no cover
        raise NotImplementedError

    def generate_text_paragraph(self, *args, **kwargs) -> "Element":  # pragma: no cover
        raise NotImplementedError

    def generate_text_run(self, *args, **kwargs) -> "Element":  # pragma: no cover
        raise NotImplementedError

    def generate_image_raster_picture(self, *args, **kwargs) -> "Element":  # pragma: no cover
        raise NotImplementedError

    def generate_image_vector_picture(self, *args, **kwargs) -> "Element":  # pragma: no cover
        raise NotImplementedError

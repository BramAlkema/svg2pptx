"""
Font subsetting helper built on top of fontTools.

Encapsulates subset option construction and execution so the embedding engine
can delegate the heavy lifting.
"""

from __future__ import annotations

import os
import tempfile

from fontTools import subset
from fontTools.ttLib import TTFont

from ..data.embedded_font import FontSubsetRequest


class FontSubsetter:
    """Perform font subsetting with configurable defaults."""

    def __init__(self, preserve_kerning_tables: bool = False):
        self._preserve_kerning_tables = preserve_kerning_tables

    def create_subset(self, font: TTFont, subset_request: FontSubsetRequest) -> bytes | None:
        """
        Execute subsetting for the supplied font.

        Returns the subset font bytes or None if subsetting failed.
        """
        try:
            options = self.build_subset_options(subset_request)

            subsetter = subset.Subsetter(options=options)
            subsetter.populate(text=options.text)
            subsetter.subset(font)

            with tempfile.NamedTemporaryFile(suffix='.ttf', delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                font.save(temp_path)
                with open(temp_path, 'rb') as handle:
                    return handle.read()
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        except Exception:
            return None

    def build_subset_options(self, subset_request: FontSubsetRequest) -> subset.Options:
        """Create configured subset options for the request."""
        options = subset.Options()

        optimization_level = subset_request.optimization_level.lower()
        if optimization_level == "aggressive":
            options.desubroutinize = True
            options.hinting = False
            options.layout_features = []
        elif optimization_level == "basic":
            options.desubroutinize = False
            options.hinting = subset_request.preserve_hinting
            if not subset_request.preserve_layout_tables:
                options.layout_features = []
        else:
            options.desubroutinize = False
            options.hinting = True

        preserve_kerning = (
            subset_request.preserve_kerning
            if subset_request.preserve_kerning is not None
            else self._preserve_kerning_tables
        )

        if not preserve_kerning:
            drop_tables = getattr(options, "drop_tables", set())
            try:
                drop_tables.add("kern")
            except AttributeError:
                drop_tables = set(drop_tables)
                drop_tables.add("kern")
            options.drop_tables = drop_tables

        options.text = ''.join(subset_request.characters)
        return options


__all__ = ["FontSubsetter"]

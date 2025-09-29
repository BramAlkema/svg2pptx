#!/usr/bin/env python3
"""
Mappers Module

Policy-driven IR to DrawingML/EMF converters.
Mappers take canonical IR elements and produce PowerPoint-compatible output.

Key principles:
- Policy-driven decisions (native vs EMF)
- Leverage battle-tested adapters
- Clean separation between IR and output format
- Measurable quality and performance metrics
"""

from .base import *
from .path_mapper import *
from .text_mapper import *
from .group_mapper import *
from .image_mapper import *

__all__ = [
    # Base mapper interface
    "Mapper", "MapperResult", "OutputFormat",

    # Specific mappers
    "PathMapper", "TextMapper", "GroupMapper", "ImageMapper",

    # Factory functions
    "create_path_mapper", "create_text_mapper",
    "create_group_mapper", "create_image_mapper",

    # Results and utilities
    "MappingError", "validate_mapper_result",
]
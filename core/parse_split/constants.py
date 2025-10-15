"""
Parser-related constants extracted for the module slicing effort.
"""

# CSS font-weight threshold for bold
FONT_WEIGHT_BOLD_THRESHOLD = 700

# Path coordinate thresholds
MIN_PATH_COORDS_FOR_LINE = 2
MIN_PATH_COORDS_FOR_CURVE = 3
MIN_PATH_COORDS_FOR_CUBIC = 6
MIN_PATH_COORDS_FOR_ARC = 4

# Segment complexity limits
MAX_SIMPLE_PATH_SEGMENTS = 10

__all__ = [
    "FONT_WEIGHT_BOLD_THRESHOLD",
    "MIN_PATH_COORDS_FOR_LINE",
    "MIN_PATH_COORDS_FOR_CURVE",
    "MIN_PATH_COORDS_FOR_CUBIC",
    "MIN_PATH_COORDS_FOR_ARC",
    "MAX_SIMPLE_PATH_SEGMENTS",
]

#!/usr/bin/env python3
"""
Fractional EMU Constants

Core constants for fractional EMU coordinate system.
"""

# EMU (English Metric Units) conversion constants
EMU_PER_INCH = 914400
EMU_PER_POINT = 12700
EMU_PER_MM = 36000
EMU_PER_CM = 360000

# DPI constants
DEFAULT_DPI = 96
POINTS_PER_INCH = 72

# PowerPoint slide dimensions (EMU)
SLIDE_WIDTH_EMU = 9144000   # 10 inches
SLIDE_HEIGHT_EMU = 6858000  # 7.5 inches

# Precision limits
MAX_FRACTIONAL_PRECISION = 10000  # Maximum precision multiplier
MIN_EMU_VALUE = -27273042329600   # PowerPoint minimum coordinate
MAX_EMU_VALUE = 27273042316900    # PowerPoint maximum coordinate

# Coordinate space limits
DRAWINGML_COORD_SPACE = 21600  # DrawingML coordinate space units

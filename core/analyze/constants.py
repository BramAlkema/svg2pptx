"""
Shared constants for SVG analysis system.

This module centralizes all magic numbers, thresholds, and mappings used
throughout the analysis and validation system.
"""

# ==============================================================================
# XML Namespaces
# ==============================================================================

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
"""Standard SVG namespace URI."""


# ==============================================================================
# Complexity Analysis Thresholds
# ==============================================================================

COMPLEXITY_THRESHOLD_SIMPLE = 0.3
"""
Complexity score threshold for 'simple' SVG classification.

SVGs scoring below 0.3 are considered simple and suitable for 'speed' policy.
Typical characteristics: <50 elements, basic shapes, no complex features.
"""

COMPLEXITY_THRESHOLD_MODERATE = 0.6
"""
Complexity score threshold for 'moderate' SVG classification.

SVGs scoring between 0.3-0.6 are moderately complex and best suited for
'balanced' policy. Typical characteristics: 50-200 elements, some gradients/filters.
"""

# Note: Scores >= 0.6 are considered complex and require 'quality' policy


# ==============================================================================
# Performance Estimation Constants
# ==============================================================================

BASE_PPTX_SIZE_KB = 30
"""
Base size of an empty PPTX file in kilobytes.

Includes: content types, relationships, presentation.xml, slide layout.
"""

AVG_ELEMENT_SIZE_KB = 2
"""
Average size overhead per SVG element in KB.

Based on empirical data from DrawingML serialization. Includes element
XML, attributes, and relationship overhead.
"""

FILTER_SIZE_OVERHEAD_KB = 10
"""
Additional size overhead per filter in KB.

Filters add significant size due to EMF fallback or complex DrawingML
with glow/shadow/reflection effects.
"""

IMAGE_SIZE_OVERHEAD_KB = 20
"""
Additional size overhead per embedded image in KB.

Covers base64 encoding overhead and relationship management. Does not
include actual image data (varies by image size).
"""

BASE_MEMORY_MB = 50
"""
Base memory usage for conversion process in MB.

Includes: Python runtime, lxml parser, pptx library, and base overhead.
Measured on Python 3.9+ with typical dependency versions.
"""

ELEMENT_MEMORY_BYTES = 1024
"""
Memory overhead per SVG element in bytes.

Covers in-memory DOM representation, intermediate IR objects, and
DrawingML element generation.
"""


# ==============================================================================
# Validation Thresholds
# ==============================================================================

MAX_RECOMMENDED_GRADIENT_STOPS = 10
"""
Maximum recommended gradient stops for optimal compatibility.

PowerPoint supports gradients with many stops, but >10 stops may cause
compatibility issues with Google Slides and older PowerPoint versions.
"""

COMPLEX_FILTER_THRESHOLD = 5
"""
Number of filter primitives that defines a 'complex' filter.

Filters with >5 primitives are more likely to require EMF fallback and
benefit from 'quality' policy for better rendering.
"""


# ==============================================================================
# Filter Name Mapping
# ==============================================================================

FILTER_NAME_MAP = {
    'feBlend': 'blend',
    'feColorMatrix': 'colormatrix',
    'feComponentTransfer': 'componenttransfer',
    'feComposite': 'composite',
    'feConvolveMatrix': 'convolvematrix',
    'feDiffuseLighting': 'diffuselighting',
    'feDisplacementMap': 'displacementmap',
    'feDropShadow': 'dropshadow',
    'feFlood': 'flood',
    'feGaussianBlur': 'blur',
    'feImage': 'image',
    'feMerge': 'merge',
    'feMorphology': 'morphology',
    'feOffset': 'offset',
    'feSpecularLighting': 'specularlighting',
    'feTile': 'tile',
    'feTurbulence': 'turbulence',
}
"""
Mapping of SVG filter element names to simplified names.

Maps full SVG filter primitive names (e.g., 'feGaussianBlur') to simplified
names used in API responses (e.g., 'blur').
"""


# ==============================================================================
# SVG Named Colors (Complete SVG 1.1 Specification)
# ==============================================================================

SVG_NAMED_COLORS = frozenset([
    # A
    'aliceblue', 'antiquewhite', 'aqua', 'aquamarine', 'azure',

    # B
    'beige', 'bisque', 'black', 'blanchedalmond', 'blue', 'blueviolet',
    'brown', 'burlywood',

    # C
    'cadetblue', 'chartreuse', 'chocolate', 'coral', 'cornflowerblue',
    'cornsilk', 'crimson', 'cyan',

    # D
    'darkblue', 'darkcyan', 'darkgoldenrod', 'darkgray', 'darkgrey',
    'darkgreen', 'darkkhaki', 'darkmagenta', 'darkolivegreen', 'darkorange',
    'darkorchid', 'darkred', 'darksalmon', 'darkseagreen', 'darkslateblue',
    'darkslategray', 'darkslategrey', 'darkturquoise', 'darkviolet',
    'deeppink', 'deepskyblue', 'dimgray', 'dimgrey', 'dodgerblue',

    # F
    'firebrick', 'floralwhite', 'forestgreen', 'fuchsia',

    # G
    'gainsboro', 'ghostwhite', 'gold', 'goldenrod', 'gray', 'grey',
    'green', 'greenyellow',

    # H
    'honeydew', 'hotpink',

    # I
    'indianred', 'indigo', 'ivory',

    # K
    'khaki',

    # L
    'lavender', 'lavenderblush', 'lawngreen', 'lemonchiffon', 'lightblue',
    'lightcoral', 'lightcyan', 'lightgoldenrodyellow', 'lightgray',
    'lightgrey', 'lightgreen', 'lightpink', 'lightsalmon', 'lightseagreen',
    'lightskyblue', 'lightslategray', 'lightslategrey', 'lightsteelblue',
    'lightyellow', 'lime', 'limegreen', 'linen',

    # M
    'magenta', 'maroon', 'mediumaquamarine', 'mediumblue', 'mediumorchid',
    'mediumpurple', 'mediumseagreen', 'mediumslateblue', 'mediumspringgreen',
    'mediumturquoise', 'mediumvioletred', 'midnightblue', 'mintcream',
    'mistyrose', 'moccasin',

    # N
    'navajowhite', 'navy',

    # O
    'oldlace', 'olive', 'olivedrab', 'orange', 'orangered', 'orchid',

    # P
    'palegoldenrod', 'palegreen', 'paleturquoise', 'palevioletred',
    'papayawhip', 'peachpuff', 'peru', 'pink', 'plum', 'powderblue',
    'purple',

    # R
    'red', 'rosybrown', 'royalblue',

    # S
    'saddlebrown', 'salmon', 'sandybrown', 'seagreen', 'seashell',
    'sienna', 'silver', 'skyblue', 'slateblue', 'slategray', 'slategrey',
    'snow', 'springgreen', 'steelblue',

    # T
    'tan', 'teal', 'thistle', 'tomato', 'transparent', 'turquoise',

    # V
    'violet',

    # W
    'wheat', 'white', 'whitesmoke',

    # Y
    'yellow', 'yellowgreen',
])
"""
Complete set of SVG 1.1 named colors (147 total).

From SVG 1.1 specification: https://www.w3.org/TR/SVG11/types.html#ColorKeywords
Includes all CSS2 named colors plus 'transparent'.
"""


# ==============================================================================
# Policy Confidence Levels
# ==============================================================================

POLICY_CONFIDENCE_HIGH = 0.95
"""High confidence in policy recommendation (complex SVGs)."""

POLICY_CONFIDENCE_MEDIUM = 0.85
"""Medium confidence in policy recommendation (moderate SVGs)."""

POLICY_CONFIDENCE_LOW = 0.9
"""Lower confidence for simple SVGs (could use speed or balanced)."""

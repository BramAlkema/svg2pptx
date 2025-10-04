#!/usr/bin/env python3
"""
Text Layout Engine
==================

Convert baseline-anchored SVG text to top-left PPT textboxes.
"""

# EMU constants
EMU_PER_INCH = 914400
EMU_PER_PT = EMU_PER_INCH // 72  # 12700

# Font metrics fallbacks
DEFAULT_ASCENT = 0.80   # safe fallback for sans fonts
DEFAULT_DESCENT = 0.20

def svg_text_to_ppt_box(svg_x, svg_y, anchor, text, font_family, font_size_pt, services, tspans=None):
    """
    Convert SVG baseline-anchored text to PPT top-left textbox.

    Args:
        svg_x, svg_y: SVG coordinates (baseline position)
        anchor: text-anchor value ('start'|'middle'|'end')
        text: Text content
        font_family: Font family name
        font_size_pt: Font size in points
        services: ConversionServices with viewport mapping
        tspans: Optional tspan elements (future enhancement)

    Returns:
        tuple: (x_left_emu, y_top_emu, width_emu, height_emu)
    """
    # Get viewport mapping from services
    viewport_mapping = services.get_viewport_mapping()

    # Transform SVG coordinates to EMU
    x_emu = int(svg_x * viewport_mapping['scale_x'] + viewport_mapping['translate_x'])
    y_emu = int(svg_y * viewport_mapping['scale_y'] + viewport_mapping['translate_y'])

    # Get font metrics (prefer real, else fallback)
    if hasattr(services, 'font_service') and services.font_service:
        metrics = getattr(services.font_service, 'metrics', lambda x: None)(font_family)
        ascent, descent = metrics or (DEFAULT_ASCENT, DEFAULT_DESCENT)
    else:
        ascent, descent = DEFAULT_ASCENT, DEFAULT_DESCENT

    # Measure text width in EMU (prefer real, else crude fallback)
    if hasattr(services, 'font_service') and services.font_service:
        measure_fn = getattr(services.font_service, 'measure', None)
        width_pt = measure_fn(text, font_family, font_size_pt) if measure_fn else None
    else:
        width_pt = None

    if width_pt is None:
        # ~0.5em average per Latin glyph, scale by font size (em=font_size)
        width_pt = 0.5 * font_size_pt * max(1, len(text))

    width_emu = int(round(width_pt * EMU_PER_PT))
    line_h_pt = font_size_pt * 1.2
    height_emu = int(round(line_h_pt * EMU_PER_PT))

    # Convert baseline to top-left (subtract ascent)
    y_top = y_emu - int(round(font_size_pt * ascent * EMU_PER_PT))

    # Apply anchor correction
    if anchor == 'middle':
        x_left = x_emu - (width_emu // 2)
    elif anchor == 'end':
        x_left = x_emu - width_emu
    else:  # start or None
        x_left = x_emu

    return x_left, y_top, width_emu, height_emu


def parse_tspans(text_el):
    """
    Parse tspan elements for multi-run text.

    Args:
        text_el: SVG text element

    Returns:
        List of run dictionaries with text, dx, dy, font properties
    """
    runs = []

    # Simple implementation - just get the main text for now
    main_text = text_el.text or ""
    if main_text.strip():
        runs.append({
            'text': main_text,
            'dx': None,
            'dy': None,
            'font_family': text_el.get('font-family'),
            'font_size': text_el.get('font-size'),
            'font_weight': text_el.get('font-weight')
        })

    # Process tspan children
    for tspan in text_el.findall('.//tspan'):
        tspan_text = tspan.text or ""
        if tspan_text.strip():
            run = {
                'text': tspan_text,
                'dx': float(tspan.get('dx', 0)) if tspan.get('dx') else None,
                'dy': float(tspan.get('dy', 0)) if tspan.get('dy') else None,
                'font_family': tspan.get('font-family'),
                'font_size': tspan.get('font-size'),
                'font_weight': tspan.get('font-weight')
            }
            runs.append(run)

    return runs


class FontMetrics:
    """Basic font metrics with fallback tables."""

    # Font metrics table: family -> (ascent_ratio, descent_ratio)
    FONT_METRICS = {
        "Arial": (0.82, 0.18),
        "Helvetica": (0.82, 0.18),
        "Times New Roman": (0.83, 0.17),
        "Courier New": (0.80, 0.20),
        "Verdana": (0.82, 0.18),
        "Georgia": (0.83, 0.17),
        "Tahoma": (0.82, 0.18),
        "Comic Sans MS": (0.81, 0.19),
        "Impact": (0.85, 0.15),
        "Trebuchet MS": (0.82, 0.18)
    }

    # Character width table (as fraction of em)
    CHAR_WIDTHS = {
        'A': 0.72, 'B': 0.67, 'C': 0.72, 'D': 0.72, 'E': 0.67, 'F': 0.61, 'G': 0.78, 'H': 0.72, 'I': 0.28, 'J': 0.50,
        'K': 0.67, 'L': 0.56, 'M': 0.83, 'N': 0.72, 'O': 0.78, 'P': 0.67, 'Q': 0.78, 'R': 0.72, 'S': 0.67, 'T': 0.61,
        'U': 0.72, 'V': 0.67, 'W': 0.94, 'X': 0.67, 'Y': 0.67, 'Z': 0.61,
        'a': 0.56, 'b': 0.56, 'c': 0.50, 'd': 0.56, 'e': 0.56, 'f': 0.28, 'g': 0.56, 'h': 0.56, 'i': 0.22, 'j': 0.22,
        'k': 0.50, 'l': 0.22, 'm': 0.83, 'n': 0.56, 'o': 0.56, 'p': 0.56, 'q': 0.56, 'r': 0.33, 's': 0.50, 't': 0.28,
        'u': 0.56, 'v': 0.50, 'w': 0.72, 'x': 0.50, 'y': 0.50, 'z': 0.50,
        '0': 0.56, '1': 0.56, '2': 0.56, '3': 0.56, '4': 0.56, '5': 0.56, '6': 0.56, '7': 0.56, '8': 0.56, '9': 0.56,
        ' ': 0.28, '.': 0.28, ',': 0.28, ':': 0.28, ';': 0.28, '!': 0.33, '?': 0.56, '-': 0.33, '_': 0.56,
        '(': 0.33, ')': 0.33, '[': 0.28, ']': 0.28, '{': 0.33, '}': 0.33, '/': 0.28, '\\': 0.28, '|': 0.26,
        '@': 1.0, '#': 0.56, '$': 0.56, '%': 0.89, '^': 0.47, '&': 0.67, '*': 0.39, '+': 0.58, '=': 0.58,
        '<': 0.58, '>': 0.58, '"': 0.35, "'": 0.19, '`': 0.33, '~': 0.58
    }

    @classmethod
    def get_metrics(cls, font_family):
        """Get ascent/descent ratios for font family."""
        return cls.FONT_METRICS.get(font_family, (DEFAULT_ASCENT, DEFAULT_DESCENT))

    @classmethod
    def measure_text_width(cls, text, font_family, font_size_pt):
        """Estimate text width using character width table."""
        total_width = 0.0

        for char in text:
            char_width = cls.CHAR_WIDTHS.get(char, 0.56)  # Default to 'o' width
            total_width += char_width

        # Convert em units to points
        width_pt = total_width * font_size_pt
        return width_pt


class BasicFontService:
    """Basic font service with fallback metrics."""

    def metrics(self, font_family):
        """Get font metrics (ascent, descent) as ratios."""
        return FontMetrics.get_metrics(font_family)

    def measure(self, text, font_family, font_size_pt):
        """Measure text width in points."""
        return FontMetrics.measure_text_width(text, font_family, font_size_pt)

    def pick_typeface(self, svg_font_family):
        """Map SVG font-family to PPT typeface."""
        if not svg_font_family:
            return "Arial"

        # Clean up font family string
        cleaned = svg_font_family.strip().strip('\'"').split(',')[0].strip()

        # Map common aliases
        font_map = {
            "Arial": "Arial",
            "Helvetica": "Arial",  # Fallback to Arial on Windows
            "Times": "Times New Roman",
            "Times New Roman": "Times New Roman",
            "Courier": "Courier New",
            "Courier New": "Courier New",
            "Verdana": "Verdana",
            "Georgia": "Georgia",
            "Tahoma": "Tahoma",
            "Comic Sans MS": "Comic Sans MS",
            "Impact": "Impact",
            "Trebuchet MS": "Trebuchet MS",
            "sans-serif": "Arial",
            "serif": "Times New Roman",
            "monospace": "Courier New"
        }

        return font_map.get(cleaned, cleaned)  # Return original if not in map
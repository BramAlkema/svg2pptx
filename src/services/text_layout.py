"""SVG to PowerPoint text layout conversion."""
from typing import Tuple
from src.units import EMU_PER_POINT


def svg_text_to_ppt_box(svg_x: float, svg_y: float, anchor: str, text: str,
                       font_family: str, font_size_pt: float,
                       services: 'ConversionServices') -> Tuple[int, int, int, int]:
    """
    Convert SVG baseline-anchored text to PowerPoint top-left textbox.

    Args:
        svg_x, svg_y: SVG baseline coordinates
        anchor: text-anchor value ('start'|'middle'|'end')
        text: Text content
        font_family: Font family name
        font_size_pt: Font size in points
        services: ConversionServices with font and viewport services

    Returns:
        Tuple[x_emu, y_emu, width_emu, height_emu]: PowerPoint textbox coordinates
    """
    # Transform SVG coordinates to EMU using unit_converter
    if hasattr(services, 'unit_converter'):
        # Convert SVG coordinates (assumed to be in pixels) to EMU
        # Pass the value as string with unit suffix
        baseline_x_emu = services.unit_converter.to_emu(f"{svg_x}px")
        baseline_y_emu = services.unit_converter.to_emu(f"{svg_y}px")
    else:
        # Fallback if unit converter not available (72 DPI assumption)
        PX_TO_EMU = 9525  # 1px = 9525 EMU at 96 DPI
        baseline_x_emu = int(svg_x * PX_TO_EMU)
        baseline_y_emu = int(svg_y * PX_TO_EMU)

    # Get font metrics (use font_processor if available, else default)
    if hasattr(services, 'font_processor') and hasattr(services.font_processor, 'get_metrics'):
        metrics = services.font_processor.get_metrics(font_family)
    else:
        # Use default metrics if font processor not available
        from dataclasses import dataclass
        @dataclass
        class DefaultMetrics:
            ascent: float = 0.8
            descent: float = 0.2
        metrics = DefaultMetrics()

    # Calculate text dimensions (use font_processor if available)
    if hasattr(services, 'font_processor') and hasattr(services.font_processor, 'measure_text_width'):
        width_pt = services.font_processor.measure_text_width(text, font_family, font_size_pt)
    else:
        # Estimate width based on text length and font size
        width_pt = len(text) * font_size_pt * 0.6  # Rough estimate
    width_emu = int(width_pt * EMU_PER_POINT)

    # Line height (1.2x font size)
    line_height_pt = font_size_pt * 1.2
    height_emu = int(line_height_pt * EMU_PER_POINT)

    # Convert baseline to top-left (subtract ascent)
    ascent_emu = int(font_size_pt * metrics.ascent * EMU_PER_POINT)
    y_top_emu = baseline_y_emu - ascent_emu

    # Apply text-anchor adjustment
    if anchor == 'middle':
        x_left_emu = baseline_x_emu - (width_emu // 2)
    elif anchor == 'end':
        x_left_emu = baseline_x_emu - width_emu
    else:  # 'start' or None
        x_left_emu = baseline_x_emu

    return x_left_emu, y_top_emu, width_emu, height_emu
#!/usr/bin/env python3
"""
Legacy Text Adapter

Wraps the existing text conversion logic with your documented fixes applied.
Provides clean interface for the new architecture while preserving proven functionality.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from lxml import etree as ET

from core.ir import TextFrame, Run, TextAnchor, Point, Rect
from core.policy import TextDecision


class TextStyleResolver:
    """
    Resolves text styling with your documented fixes.

    Implements:
    - Raw anchor handling (no double mapping)
    - Per-tspan styling inheritance
    - Conservative baseline calculation
    - ConversionContext coordinate pipeline
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def resolve_text_runs(self, text_element: ET.Element) -> List[Run]:
        """
        Extract styled runs using per-tspan logic.

        Implements your documented fix for per-tspan run styling.

        Args:
            text_element: SVG <text> element

        Returns:
            List of Run objects with resolved styling
        """
        base_style = self._read_text_style(text_element)
        runs = []

        # Direct text node before children
        if text_element.text and text_element.text.strip():
            runs.append(self._create_run(text_element.text.strip(), base_style))

        # Process tspan children
        for child in text_element:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            if tag == "tspan":
                # Check for positioned tspan (creates line break)
                if child.get('x') is not None or child.get('y') is not None:
                    # Add newline run to signal line break
                    if runs and not runs[-1].text.endswith('\n'):
                        last_run = runs[-1]
                        runs[-1] = Run(
                            text=last_run.text + '\n',
                            font_family=last_run.font_family,
                            font_size_pt=last_run.font_size_pt,
                            bold=last_run.bold,
                            italic=last_run.italic,
                            underline=last_run.underline,
                            strike=last_run.strike,
                            rgb=last_run.rgb
                        )

                # Merge child style with parent
                child_style = self._merge_style(base_style, self._read_text_style(child, parent=base_style))

                if child.text and child.text.strip():
                    runs.append(self._create_run(child.text.strip(), child_style))

            # Handle tail text with parent style
            if child.tail and child.tail.strip():
                runs.append(self._create_run(child.tail.strip(), base_style))

        # Ensure at least one run
        if not runs:
            runs.append(self._create_run("", base_style))

        return runs

    def get_raw_text_anchor(self, element: ET.Element) -> TextAnchor:
        """
        Get raw SVG text-anchor value (no double mapping).

        Implements your documented fix for anchor handling.

        Args:
            element: SVG text element

        Returns:
            Raw TextAnchor enum value
        """
        anchor_str = element.get('text-anchor', 'start')

        anchor_map = {
            'start': TextAnchor.START,
            'middle': TextAnchor.MIDDLE,
            'end': TextAnchor.END
        }

        return anchor_map.get(anchor_str, TextAnchor.START)

    def _read_text_style(self, el: ET.Element, parent: Dict[str, Any] = None) -> Dict[str, Any]:
        """Read style from element (attributes + CSS) and normalize."""
        # Start from parent or defaults
        style = dict(parent or {
            "font_family": self._extract_font_family(el),
            "font_size_pt": self._extract_font_size(el),
            "bold": False,
            "italic": False,
            "underline": False,
            "strike": False,
            "rgb": "000000",  # Default black (not red!)
        })

        # Font family
        ff = el.get('font-family')
        if not ff and 'style' in el.attrib:
            ff = self._extract_css_property(el.get('style', ''), 'font-family')
        if ff:
            ff = ff.split(',')[0].strip().strip('\'"')
            style["font_family"] = ff

        # Font size
        fs_attr = el.get('font-size')
        if fs_attr:
            try:
                # Simple pt conversion (would integrate with units API)
                if fs_attr.endswith('pt'):
                    style["font_size_pt"] = float(fs_attr[:-2])
                elif fs_attr.endswith('px'):
                    style["font_size_pt"] = float(fs_attr[:-2]) * 0.75  # px to pt
                else:
                    style["font_size_pt"] = float(fs_attr)
            except ValueError:
                pass

        # Weight and style
        fw = el.get('font-weight') or self._extract_css_property(el.get('style', ''), 'font-weight')
        fs = el.get('font-style') or self._extract_css_property(el.get('style', ''), 'font-style')

        style["bold"] = fw in ('bold', 'bolder', '600', '700', '800', '900') or style.get("bold", False)
        style["italic"] = fs in ('italic', 'oblique') or style.get("italic", False)

        # Text decoration
        td = el.get('text-decoration') or self._extract_css_property(el.get('style', ''), 'text-decoration')
        if td:
            style["underline"] = 'underline' in td or style.get("underline", False)
            style["strike"] = ('line-through' in td or 'strikethrough' in td) or style.get("strike", False)

        # Fill color
        fill = el.get('fill') or self._extract_css_property(el.get('style', ''), 'fill')
        if fill and fill != 'none':
            rgb = self._parse_color_to_rgb(fill)
            if rgb:
                style["rgb"] = rgb

        return style

    def _merge_style(self, base: Dict[str, Any], child: Dict[str, Any]) -> Dict[str, Any]:
        """Merge child style with base style."""
        result = dict(base)
        result.update(child or {})
        return result

    def _create_run(self, text: str, style: Dict[str, Any]) -> Run:
        """Create Run from text and style."""
        return Run(
            text=text,
            font_family=style.get("font_family", "Arial"),
            font_size_pt=style.get("font_size_pt", 12.0),
            bold=style.get("bold", False),
            italic=style.get("italic", False),
            underline=style.get("underline", False),
            strike=style.get("strike", False),
            rgb=style.get("rgb", "000000")
        )

    def _extract_font_family(self, el: ET.Element) -> str:
        """Extract font family with fallback."""
        family = el.get('font-family')
        if not family:
            style = el.get('style', '')
            family = self._extract_css_property(style, 'font-family')
        return family.split(',')[0].strip().strip('\'"') if family else "Arial"

    def _extract_font_size(self, el: ET.Element) -> float:
        """Extract font size with fallback."""
        size = el.get('font-size')
        if not size:
            style = el.get('style', '')
            size = self._extract_css_property(style, 'font-size')

        if size:
            try:
                if size.endswith('pt'):
                    return float(size[:-2])
                elif size.endswith('px'):
                    return float(size[:-2]) * 0.75
                else:
                    return float(size)
            except ValueError:
                pass

        return 12.0

    def _extract_css_property(self, css: str, prop: str) -> Optional[str]:
        """Extract CSS property value."""
        if not css or not prop:
            return None

        # Simple CSS parsing
        for rule in css.split(';'):
            if ':' in rule:
                key, value = rule.split(':', 1)
                if key.strip() == prop:
                    return value.strip()
        return None

    def _parse_color_to_rgb(self, color: str) -> Optional[str]:
        """Parse color to RRGGBB format (simplified)."""
        color = color.strip().lower()

        if color.startswith('#'):
            hex_color = color[1:]
            if len(hex_color) == 3:
                # Expand shorthand #RGB to #RRGGBB
                hex_color = ''.join([c*2 for c in hex_color])
            if len(hex_color) == 6:
                return hex_color.upper()

        # Named colors (simplified)
        color_map = {
            'black': '000000',
            'white': 'FFFFFF',
            'red': 'FF0000',
            'green': '008000',
            'blue': '0000FF',
            'yellow': 'FFFF00',
            'cyan': '00FFFF',
            'magenta': 'FF00FF',
        }

        return color_map.get(color)


class FontMetricsAdapter:
    """
    Adapter for font metrics calculations.

    Provides conservative baseline adjustment per your documented fixes.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def calculate_conservative_baseline_offset(self, font_family: str, font_size_pt: float) -> float:
        """
        Calculate conservative baseline offset.

        Implements your documented fix: ~5% of ascender to avoid visible drift.

        Args:
            font_family: Font family name
            font_size_pt: Font size in points

        Returns:
            Baseline offset in EMU
        """
        try:
            # Conservative: ~5% of font size for baseline adjustment
            baseline_ratio = 0.05
            offset_pt = font_size_pt * baseline_ratio
            offset_emu = offset_pt * 9525  # pt to EMU conversion
            return offset_emu
        except Exception:
            return 0.0  # Trust PPTX text box positioning

    def estimate_text_dimensions(self, text: str, font_family: str, font_size_pt: float) -> Tuple[float, float]:
        """
        Estimate text dimensions (simplified).

        Args:
            text: Text content
            font_family: Font family
            font_size_pt: Font size in points

        Returns:
            Tuple of (width_pixels, height_pixels)
        """
        # Simplified dimension estimation
        # In production, would integrate with proven text measurement
        avg_char_width = font_size_pt * 0.6  # Rough estimate
        line_height = font_size_pt * 1.2

        lines = text.split('\n')
        max_line_length = max(len(line) for line in lines) if lines else 0

        width = max_line_length * avg_char_width
        height = len(lines) * line_height

        return width, height


class LegacyTextAdapter:
    """
    Main adapter for legacy text conversion functionality.

    Applies your documented text fixes while wrapping existing proven logic.
    """

    def __init__(self):
        self.style_resolver = TextStyleResolver()
        self.font_metrics = FontMetricsAdapter()
        self.logger = logging.getLogger(__name__)

    def convert_text_element_to_ir(self, text_element: ET.Element, context=None) -> TextFrame:
        """
        Convert SVG text element to IR TextFrame.

        Applies all your documented fixes:
        - Raw anchor handling
        - ConversionContext coordinate pipeline
        - Per-tspan styling
        - Conservative baseline handling

        Args:
            text_element: SVG <text> element
            context: Conversion context (optional)

        Returns:
            TextFrame IR element
        """
        # 1. Parse coordinates using context (your fix: use ConversionContext)
        x_val = text_element.get('x', '0')
        y_val = text_element.get('y', '0')

        try:
            x = float(x_val) if x_val else 0.0
            y = float(y_val) if y_val else 0.0
        except ValueError:
            x, y = 0.0, 0.0

        # 2. Transform coordinates (your fix: use context.transform_point)
        if context and hasattr(context, 'transform_point'):
            try:
                x_emu, y_emu = context.transform_point(x, y)
                origin = Point(x_emu, y_emu)
            except Exception:
                # Fallback coordinate conversion
                origin = Point(x * 9525, y * 9525)
        else:
            # Simple EMU conversion
            origin = Point(x * 9525, y * 9525)

        # 3. Get raw anchor (your fix: no double mapping)
        anchor = self.style_resolver.get_raw_text_anchor(text_element)

        # 4. Extract styled runs (your fix: per-tspan styling)
        runs = self.style_resolver.resolve_text_runs(text_element)

        # 5. Calculate text dimensions
        text_content = ''.join(run.text for run in runs)
        primary_font = runs[0].font_family if runs else "Arial"
        primary_size = runs[0].font_size_pt if runs else 12.0

        width_px, height_px = self.font_metrics.estimate_text_dimensions(
            text_content, primary_font, primary_size
        )

        # 6. Convert to EMU and create bounding box
        width_emu = width_px * 9525 / 96  # px to EMU
        height_emu = height_px * 9525 / 96

        bbox = Rect(origin.x, origin.y, width_emu, height_emu)

        # 7. Calculate conservative baseline shift (your fix)
        baseline_shift = self.font_metrics.calculate_conservative_baseline_offset(
            primary_font, primary_size
        )

        return TextFrame(
            origin=origin,
            runs=runs,
            anchor=anchor,
            bbox=bbox,
            baseline_shift=baseline_shift
        )

    def generate_drawingml_from_ir(self, text_frame: TextFrame, decision: TextDecision) -> str:
        """
        Generate DrawingML XML from IR TextFrame.

        Implements your documented fixes for paragraph alignment.

        Args:
            text_frame: TextFrame IR element
            decision: Policy decision for this text

        Returns:
            DrawingML XML string
        """
        if not decision.use_native:
            # Fallback to EMF - would integrate with EMF adapter
            return self._generate_emf_fallback(text_frame)

        # Generate native DrawingML with fixes
        return self._generate_native_drawingml(text_frame)

    def _generate_native_drawingml(self, text_frame: TextFrame) -> str:
        """
        Generate native DrawingML with your fixes applied.

        Implements:
        - Proper paragraph alignment separation
        - Multiple paragraphs for line breaks
        - Per-run styling
        """
        # Convert anchor to DrawingML alignment (your fix: map once)
        align_map = {
            TextAnchor.START: 'l',
            TextAnchor.MIDDLE: 'ctr',
            TextAnchor.END: 'r'
        }
        align = align_map.get(text_frame.anchor, 'l')

        # Split runs into lines
        lines = text_frame.lines()

        # Build DrawingML structure
        xml_parts = []
        xml_parts.append('<p:sp>')
        xml_parts.append('<p:txBody>')

        # Body properties (your fix: vertical anchor separate from horizontal)
        xml_parts.append(
            '<a:bodyPr vertOverflow="ellipsis" wrap="square" rtlCol="0" '
            'anchor="t" anchorCtr="0"/>'  # Vertical: top by default
        )

        xml_parts.append('<a:lstStyle/>')

        # Generate paragraphs (one per line)
        for line_runs in lines:
            xml_parts.append('<a:p>')

            # Paragraph properties (your fix: horizontal alignment here)
            if align in ("ctr", "r", "l", "just"):
                xml_parts.append(f'<a:pPr algn="{align}"/>')

            # Generate runs
            for run in line_runs:
                if not run.text:
                    continue

                xml_parts.append('<a:r>')

                # Run properties
                size_hundredths = int(run.font_size_pt * 100)
                xml_parts.append(
                    f'<a:rPr lang="en-US" sz="{size_hundredths}" '
                    f'b="{"1" if run.bold else "0"}" '
                    f'i="{"1" if run.italic else "0"}" '
                    f'dirty="0"'
                )

                if run.underline:
                    xml_parts.append(' u="sng"')
                if run.strike:
                    xml_parts.append(' strike="sngStrike"')

                xml_parts.append('>')

                # Color
                xml_parts.append('<a:solidFill>')
                xml_parts.append(f'<a:srgbClr val="{run.rgb}"/>')
                xml_parts.append('</a:solidFill>')

                # Font
                xml_parts.append(f'<a:latin typeface="{run.font_family}"/>')
                xml_parts.append('</a:rPr>')

                # Text content
                xml_parts.append(f'<a:t>{self._escape_xml(run.text)}</a:t>')
                xml_parts.append('</a:r>')

            xml_parts.append('<a:endParaRPr/>')
            xml_parts.append('</a:p>')

        xml_parts.append('</a:txBody>')
        xml_parts.append('</p:sp>')

        return ''.join(xml_parts)

    def _generate_emf_fallback(self, text_frame: TextFrame) -> str:
        """Generate EMF fallback for complex text."""
        # Placeholder - would integrate with EMF adapter
        return f'<!-- EMF fallback for text: {text_frame.text_content[:50]}... -->'

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&apos;'))
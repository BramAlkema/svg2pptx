#!/usr/bin/env python3
"""
Tests for WordArt Color Mapping Service

Validates SVG color/gradient mapping to PowerPoint DrawingML format.
"""

import pytest
from lxml import etree as ET

from core.services.wordart_color_service import (
    WordArtColorMappingService,
    LinearGradientInfo,
    RadialGradientInfo,
    GradientStop,
    create_wordart_color_service
)
from src.converters.wordart_gradient_mapper import (
    WordArtGradientMapper,
    create_wordart_gradient_mapper
)


class TestWordArtColorMappingService:
    """Test color mapping service functionality."""

    def setup_method(self):
        """Set up test service."""
        self.service = WordArtColorMappingService()

    def test_map_solid_fill_basic(self):
        """Test basic solid fill mapping."""
        fill = self.service.map_solid_fill("#FF0000")

        # Define namespace
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Check structure
        assert fill.tag == f"{a_ns}solidFill"
        srgb_clr = fill.find(f"{a_ns}srgbClr")
        assert srgb_clr is not None
        assert srgb_clr.get("val") == "FF0000"

        # Should not have alpha for fully opaque
        alpha = srgb_clr.find(f"{a_ns}alpha")
        assert alpha is None

    def test_map_solid_fill_with_opacity(self):
        """Test solid fill with opacity."""
        fill = self.service.map_solid_fill("#00FF00", opacity=0.5)

        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        srgb_clr = fill.find(f"{a_ns}srgbClr")
        assert srgb_clr.get("val") == "00FF00"

        # Check alpha value
        alpha = srgb_clr.find(f"{a_ns}alpha")
        assert alpha is not None
        assert alpha.get("val") == "50000"  # 50% = 50000

    def test_map_solid_fill_invalid_color(self):
        """Test solid fill with invalid color falls back to black."""
        fill = self.service.map_solid_fill("invalid-color")

        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        srgb_clr = fill.find(f"{a_ns}srgbClr")
        assert srgb_clr.get("val") == "000000"  # Black fallback

    def test_map_linear_gradient_basic(self):
        """Test basic linear gradient mapping."""
        stops = [
            GradientStop(0.0, "#FF0000", 1.0),
            GradientStop(1.0, "#0000FF", 1.0)
        ]
        gradient = LinearGradientInfo(x1=0, y1=0, x2=1, y2=0, stops=stops)

        fill = self.service.map_linear_gradient(gradient)

        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Check structure
        assert fill.tag == f"{a_ns}gradFill"
        assert fill.get("flip") == "none"
        assert fill.get("rotWithShape") == "1"

        # Check stops
        gs_lst = fill.find(f"{a_ns}gsLst")
        assert gs_lst is not None

        stops_found = gs_lst.findall(f"{a_ns}gs")
        assert len(stops_found) == 2

        # Check first stop
        first_stop = stops_found[0]
        assert first_stop.get("pos") == "0"
        first_color = first_stop.find(f"{a_ns}srgbClr")
        assert first_color.get("val") == "FF0000"

        # Check last stop
        last_stop = stops_found[1]
        assert last_stop.get("pos") == "100000"
        last_color = last_stop.find(f"{a_ns}srgbClr")
        assert last_color.get("val") == "0000FF"

        # Check linear direction
        lin = fill.find(f"{a_ns}lin")
        assert lin is not None
        assert lin.get("ang") == "0"  # 0 degrees for horizontal
        assert lin.get("scaled") == "0"

    def test_map_linear_gradient_angled(self):
        """Test angled linear gradient."""
        stops = [
            GradientStop(0.0, "#FF0000", 1.0),
            GradientStop(1.0, "#0000FF", 1.0)
        ]
        # 45-degree diagonal
        gradient = LinearGradientInfo(x1=0, y1=0, x2=1, y2=1, stops=stops)

        fill = self.service.map_linear_gradient(gradient)

        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        lin = fill.find(f"{a_ns}lin")
        angle = int(lin.get("ang"))
        # Should be close to 45 degrees (45 * 60000 = 2700000)
        assert abs(angle - 2700000) < 60000  # 1 degree tolerance

    def test_map_radial_gradient_basic(self):
        """Test basic radial gradient mapping."""
        stops = [
            GradientStop(0.0, "#FFFFFF", 1.0),
            GradientStop(1.0, "#000000", 1.0)
        ]
        gradient = RadialGradientInfo(cx=0.5, cy=0.5, r=0.5, stops=stops)

        fill = self.service.map_radial_gradient(gradient)

        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Check structure
        assert fill.tag == f"{a_ns}gradFill"

        # Check stops (should be reversed for radial)
        gs_lst = fill.find(f"{a_ns}gsLst")
        stops_found = gs_lst.findall(f"{a_ns}gs")
        assert len(stops_found) == 2

        # First stop should be the original last stop (reversed)
        first_stop = stops_found[0]
        first_color = first_stop.find(f"{a_ns}srgbClr")
        assert first_color.get("val") == "000000"

        # Check path type
        path = fill.find(f"{a_ns}path")
        assert path is not None
        assert path.get("path") == "circle"

        # Check fill rect
        fill_to_rect = path.find(f"{a_ns}fillToRect")
        assert fill_to_rect is not None

    def test_gradient_stop_simplification(self):
        """Test gradient stop simplification for large gradients."""
        # Create gradient with too many stops
        stops = []
        for i in range(15):  # More than MAX_GRADIENT_STOPS (8)
            position = i / 14
            color = f"#{i*17:02X}{i*17:02X}{i*17:02X}"  # Gradient from black to white
            stops.append(GradientStop(position, color, 1.0))

        simplified = self.service._simplify_gradient_stops(stops)

        # Should be reduced to 8 stops
        assert len(simplified) <= self.service.MAX_GRADIENT_STOPS

        # First and last should be preserved
        assert simplified[0].position == 0.0
        assert simplified[-1].position == 1.0

        # Stops should be in position order
        positions = [stop.position for stop in simplified]
        assert positions == sorted(positions)

    def test_angle_snapping(self):
        """Test gradient angle snapping to common angles."""
        # Test snapping to 45 degrees
        snapped = self.service._snap_angle(47.0)  # Close to 45
        assert snapped == 45.0

        # Test snapping to 90 degrees
        snapped = self.service._snap_angle(88.0)  # Close to 90
        assert snapped == 90.0

        # Test no snapping for distant angles
        snapped = self.service._snap_angle(30.0)  # Not close to any snap angle
        assert snapped == 30.0

    def test_color_distance_calculation(self):
        """Test color distance calculation."""
        from core.color import Color

        red = Color("#FF0000")
        blue = Color("#0000FF")
        green = Color("#00FF00")

        # Distance between different colors should be > 0
        dist_red_blue = self.service._color_distance(red, blue)
        assert dist_red_blue > 0

        # Distance should be symmetric
        dist_blue_red = self.service._color_distance(blue, red)
        assert abs(dist_red_blue - dist_blue_red) < 0.001

        # Distance to self should be 0
        dist_red_red = self.service._color_distance(red, red)
        assert dist_red_red == 0

    def test_parse_svg_linear_gradient(self):
        """Test parsing SVG linearGradient element."""
        svg_gradient = ET.fromstring('''
            <linearGradient xmlns="http://www.w3.org/2000/svg"
                          id="grad1" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#FF0000"/>
                <stop offset="100%" stop-color="#0000FF"/>
            </linearGradient>
        ''')

        gradient_info = self.service.parse_svg_gradient(svg_gradient)

        assert isinstance(gradient_info, LinearGradientInfo)
        assert gradient_info.x1 == 0
        assert gradient_info.y1 == 0
        assert gradient_info.x2 == 1
        assert gradient_info.y2 == 1
        assert len(gradient_info.stops) == 2
        assert gradient_info.stops[0].color == "#FF0000"
        assert gradient_info.stops[1].color == "#0000FF"

    def test_parse_svg_radial_gradient(self):
        """Test parsing SVG radialGradient element."""
        svg_gradient = ET.fromstring('''
            <radialGradient xmlns="http://www.w3.org/2000/svg"
                          id="grad1" cx="0.5" cy="0.5" r="0.5">
                <stop offset="0%" stop-color="#FFFFFF"/>
                <stop offset="100%" stop-color="#000000"/>
            </radialGradient>
        ''')

        gradient_info = self.service.parse_svg_gradient(svg_gradient)

        assert isinstance(gradient_info, RadialGradientInfo)
        assert gradient_info.cx == 0.5
        assert gradient_info.cy == 0.5
        assert gradient_info.r == 0.5
        assert len(gradient_info.stops) == 2

    def test_parse_gradient_stops_with_style(self):
        """Test parsing gradient stops with style attributes."""
        svg_gradient = ET.fromstring('''
            <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1">
                <stop offset="0%" style="stop-color:#FF0000;stop-opacity:0.8"/>
                <stop offset="100%" style="stop-color:#0000FF;stop-opacity:0.6"/>
            </linearGradient>
        ''')

        gradient_info = self.service.parse_svg_gradient(svg_gradient)
        stops = gradient_info.stops

        assert len(stops) == 2
        assert stops[0].color == "#FF0000"
        assert stops[0].opacity == 0.8
        assert stops[1].color == "#0000FF"
        assert stops[1].opacity == 0.6

    def test_factory_function(self):
        """Test factory function."""
        service = create_wordart_color_service()
        assert isinstance(service, WordArtColorMappingService)


class TestWordArtGradientMapper:
    """Test gradient mapper functionality."""

    def setup_method(self):
        """Set up test mapper."""
        self.mapper = WordArtGradientMapper()

    def test_extract_gradient_id(self):
        """Test gradient ID extraction from URL."""
        # Valid URL
        gradient_id = self.mapper._extract_gradient_id("url(#gradient1)")
        assert gradient_id == "gradient1"

        # Invalid URL
        gradient_id = self.mapper._extract_gradient_id("none")
        assert gradient_id is None

        # Empty URL
        gradient_id = self.mapper._extract_gradient_id("url(#)")
        assert gradient_id == ""

    def test_map_gradient_reference(self):
        """Test mapping gradient reference to DrawingML."""
        # Create SVG defs with gradient
        svg_defs = ET.fromstring('''
            <defs xmlns="http://www.w3.org/2000/svg">
                <linearGradient id="grad1" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stop-color="#FF0000"/>
                    <stop offset="100%" stop-color="#0000FF"/>
                </linearGradient>
            </defs>
        ''')

        # Create element with gradient reference
        element = ET.Element("text")
        element.set("fill", "url(#grad1)")

        # Map gradient
        fill = self.mapper.map_gradient_reference(element, "url(#grad1)", svg_defs)

        assert fill is not None
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        assert fill.tag == f"{a_ns}gradFill"

    def test_approximate_mesh_gradient(self):
        """Test mesh gradient approximation."""
        # Create mock mesh gradient
        mesh = ET.fromstring('''
            <meshGradient xmlns="http://www.w3.org/2000/svg">
                <meshRow>
                    <meshPatch>
                        <stop stop-color="#FF0000"/>
                        <stop stop-color="#00FF00"/>
                        <stop stop-color="#0000FF"/>
                        <stop stop-color="#FFFF00"/>
                    </meshPatch>
                </meshRow>
            </meshGradient>
        ''')

        fill = self.mapper.approximate_mesh_gradient(mesh)

        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        # Should create gradient fill if enough colors, otherwise solid fill
        assert fill.tag in [f"{a_ns}gradFill", f"{a_ns}solidFill"]

        # If it's a gradient fill, should be radial
        if fill.tag == f"{a_ns}gradFill":
            path = fill.find(f"{a_ns}path")
            assert path is not None
            assert path.get("path") == "circle"

    def test_approximate_pattern_fill(self):
        """Test pattern fill approximation."""
        # Create mock pattern
        pattern = ET.fromstring('''
            <pattern xmlns="http://www.w3.org/2000/svg" id="pattern1">
                <rect fill="#FF0000" width="10" height="10"/>
                <circle fill="#0000FF" cx="5" cy="5" r="2"/>
            </pattern>
        ''')

        fill = self.mapper.approximate_pattern_fill(pattern)

        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        # Should return either solidFill or gradFill
        assert fill.tag in [f"{a_ns}solidFill", f"{a_ns}gradFill"]

    def test_resolve_gradient_chain(self):
        """Test gradient inheritance resolution."""
        # Create parent and child gradients
        svg_defs = ET.fromstring('''
            <defs xmlns="http://www.w3.org/2000/svg"
                  xmlns:xlink="http://www.w3.org/1999/xlink">
                <linearGradient id="parent" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stop-color="#FF0000"/>
                    <stop offset="100%" stop-color="#0000FF"/>
                </linearGradient>
                <linearGradient id="child" xlink:href="#parent" x1="0" y1="0" x2="0" y2="1"/>
            </defs>
        ''')

        child_gradient = svg_defs.find(".//*[@id='child']")
        resolved = self.mapper._resolve_gradient_chain(child_gradient, svg_defs)

        # Should inherit stops from parent but override direction
        assert resolved.get('x2') == "0"  # Child's x2
        assert resolved.get('y2') == "1"  # Child's y2

        # Should have stops from parent
        stops = resolved.findall('.//{http://www.w3.org/2000/svg}stop')
        assert len(stops) == 2

    def test_factory_function(self):
        """Test factory function."""
        mapper = create_wordart_gradient_mapper()
        assert isinstance(mapper, WordArtGradientMapper)


class TestGradientIntegration:
    """Test integration between color service and gradient mapper."""

    def setup_method(self):
        """Set up test components."""
        self.color_service = WordArtColorMappingService()
        self.gradient_mapper = WordArtGradientMapper()

    def test_complex_gradient_mapping(self):
        """Test end-to-end gradient mapping."""
        # Create complex SVG structure
        svg_doc = ET.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink">
                <defs>
                    <linearGradient id="complexGrad" x1="0" y1="0" x2="1" y2="1"
                                  gradientTransform="rotate(30)">
                        <stop offset="0%" stop-color="#FF0000" stop-opacity="0.8"/>
                        <stop offset="25%" stop-color="#FF8000"/>
                        <stop offset="50%" stop-color="#FFFF00"/>
                        <stop offset="75%" stop-color="#80FF00"/>
                        <stop offset="100%" stop-color="#00FF00" stop-opacity="0.6"/>
                    </linearGradient>
                </defs>
                <text fill="url(#complexGrad)">Test Text</text>
            </svg>
        ''')

        defs = svg_doc.find('.//{http://www.w3.org/2000/svg}defs')
        text_element = svg_doc.find('.//{http://www.w3.org/2000/svg}text')

        # Map gradient
        fill = self.gradient_mapper.map_gradient_reference(
            text_element, "url(#complexGrad)", defs
        )

        assert fill is not None
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Should be gradient fill
        assert fill.tag == f"{a_ns}gradFill"

        # Check that opacity is preserved in stops
        gs_lst = fill.find(f"{a_ns}gsLst")
        stops = gs_lst.findall(f"{a_ns}gs")

        # Should have some stops with alpha
        has_alpha = False
        for stop in stops:
            srgb_clr = stop.find(f"{a_ns}srgbClr")
            alpha = srgb_clr.find(f"{a_ns}alpha")
            if alpha is not None:
                has_alpha = True
                break

        assert has_alpha

    def test_gradient_fallback_handling(self):
        """Test graceful fallback for unsupported gradients."""
        # Create invalid gradient reference
        svg_defs = ET.fromstring('<defs xmlns="http://www.w3.org/2000/svg"/>')
        element = ET.Element("text")

        # Should return None for missing gradient
        fill = self.gradient_mapper.map_gradient_reference(
            element, "url(#missing)", svg_defs
        )
        assert fill is None

    def test_gradient_stop_edge_cases(self):
        """Test edge cases in gradient stop handling."""
        # Single stop gradient
        single_stop_gradient = ET.fromstring('''
            <linearGradient xmlns="http://www.w3.org/2000/svg" id="single">
                <stop offset="0%" stop-color="#FF0000"/>
            </linearGradient>
        ''')

        gradient_info = self.color_service.parse_svg_gradient(single_stop_gradient)
        # Should have 2 stops (duplicate added)
        assert len(gradient_info.stops) == 2

        # No stops gradient (should get defaults)
        no_stop_gradient = ET.fromstring('''
            <linearGradient xmlns="http://www.w3.org/2000/svg" id="empty"/>
        ''')

        gradient_info = self.color_service.parse_svg_gradient(no_stop_gradient)
        # Should have default black to white
        assert len(gradient_info.stops) == 2
        assert gradient_info.stops[0].color == "#000000"
        assert gradient_info.stops[1].color == "#FFFFFF"
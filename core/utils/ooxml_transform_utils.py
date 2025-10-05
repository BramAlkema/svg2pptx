#!/usr/bin/env python3
"""
OOXML Transform Utilities

Provides utilities for converting SVG transforms to PowerPoint DrawingML format.
Handles unit conversions, angle calculations, and XML generation for <a:xfrm> elements.
"""

from dataclasses import dataclass
from typing import Any, Dict

from lxml import etree as ET

from .xml_builder import XMLBuilder


@dataclass
class OOXMLTransform:
    """Represents a PowerPoint DrawingML transform."""

    # Position (EMU units)
    x: int = 0
    y: int = 0

    # Dimensions (EMU units)
    width: int = 0
    height: int = 0

    # Rotation (1/60000 degrees)
    rotation: int = 0

    # Flip flags
    flip_h: bool = False
    flip_v: bool = False


class OOXMLTransformUtils:
    """Utilities for converting transforms to PowerPoint DrawingML format."""

    # PowerPoint angle units: 1 degree = 60,000 angle units
    ANGLE_UNITS_PER_DEGREE = 60000

    # EMU conversion constants
    EMU_PER_INCH = 914400
    EMU_PER_POINT = 12700  # 1 point = 1/72 inch
    PIXELS_PER_INCH = 96   # Standard web DPI
    EMU_PER_PIXEL = EMU_PER_INCH // PIXELS_PER_INCH  # 9525 EMU per pixel

    def __init__(self):
        """Initialize transform utilities."""
        self.xml_builder = XMLBuilder()

    def degrees_to_angle_units(self, degrees: float) -> int:
        """
        Convert degrees to PowerPoint angle units (1/60000 degrees).

        Args:
            degrees: Angle in degrees

        Returns:
            Angle in PowerPoint units (integer)
        """
        # Round to nearest integer for PowerPoint compatibility
        return round(degrees * self.ANGLE_UNITS_PER_DEGREE)

    def angle_units_to_degrees(self, angle_units: int) -> float:
        """
        Convert PowerPoint angle units back to degrees.

        Args:
            angle_units: Angle in PowerPoint units

        Returns:
            Angle in degrees
        """
        return angle_units / self.ANGLE_UNITS_PER_DEGREE

    def pixels_to_emu(self, pixels: float) -> int:
        """
        Convert pixels to EMU (English Metric Units).

        Args:
            pixels: Size in pixels

        Returns:
            Size in EMU (integer)
        """
        return round(pixels * self.EMU_PER_PIXEL)

    def emu_to_pixels(self, emu: int) -> float:
        """
        Convert EMU back to pixels.

        Args:
            emu: Size in EMU

        Returns:
            Size in pixels
        """
        return emu / self.EMU_PER_PIXEL

    def points_to_emu(self, points: float) -> int:
        """
        Convert points to EMU.

        Args:
            points: Size in points (1/72 inch)

        Returns:
            Size in EMU (integer)
        """
        return round(points * self.EMU_PER_POINT)

    def create_ooxml_transform(
        self,
        translate_x: float = 0.0,
        translate_y: float = 0.0,
        width: float = 100.0,
        height: float = 100.0,
        rotation_deg: float = 0.0,
        flip_h: bool = False,
        flip_v: bool = False,
        input_unit: str = "px",
    ) -> OOXMLTransform:
        """
        Create OOXML transform from SVG transform components.

        Args:
            translate_x: X translation
            translate_y: Y translation
            width: Shape width
            height: Shape height
            rotation_deg: Rotation in degrees
            flip_h: Horizontal flip
            flip_v: Vertical flip
            input_unit: Input unit ("px", "pt", "emu")

        Returns:
            OOXMLTransform object
        """
        # Convert coordinates based on input unit
        if input_unit == "px":
            x_emu = self.pixels_to_emu(translate_x)
            y_emu = self.pixels_to_emu(translate_y)
            w_emu = self.pixels_to_emu(width)
            h_emu = self.pixels_to_emu(height)
        elif input_unit == "pt":
            x_emu = self.points_to_emu(translate_x)
            y_emu = self.points_to_emu(translate_y)
            w_emu = self.points_to_emu(width)
            h_emu = self.points_to_emu(height)
        elif input_unit == "emu":
            x_emu = round(translate_x)
            y_emu = round(translate_y)
            w_emu = round(width)
            h_emu = round(height)
        else:
            raise ValueError(f"Unsupported input unit: {input_unit}")

        # Convert rotation to angle units
        rotation_units = self.degrees_to_angle_units(rotation_deg)

        return OOXMLTransform(
            x=x_emu,
            y=y_emu,
            width=w_emu,
            height=h_emu,
            rotation=rotation_units,
            flip_h=flip_h,
            flip_v=flip_v,
        )

    def generate_xfrm_xml(self, transform: OOXMLTransform) -> ET.Element:
        """
        Generate <a:xfrm> XML element from transform.

        Args:
            transform: OOXML transform object

        Returns:
            XML element for <a:xfrm>
        """
        # Create root xfrm element with namespace
        xfrm = ET.Element("{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm")

        # Add flip attributes if needed
        if transform.flip_h:
            xfrm.set("flipH", "1")
        if transform.flip_v:
            xfrm.set("flipV", "1")

        # Add rotation if non-zero
        if transform.rotation != 0:
            xfrm.set("rot", str(transform.rotation))

        # Add offset (position)
        off = ET.SubElement(xfrm, "{http://schemas.openxmlformats.org/drawingml/2006/main}off")
        off.set("x", str(transform.x))
        off.set("y", str(transform.y))

        # Add extent (dimensions)
        ext = ET.SubElement(xfrm, "{http://schemas.openxmlformats.org/drawingml/2006/main}ext")
        ext.set("cx", str(transform.width))
        ext.set("cy", str(transform.height))

        return xfrm

    def generate_xfrm_xml_string(self, transform: OOXMLTransform) -> str:
        """
        Generate <a:xfrm> XML as string.

        Args:
            transform: OOXML transform object

        Returns:
            XML string
        """
        element = self.generate_xfrm_xml(transform)
        return ET.tostring(element, encoding='unicode', pretty_print=True)

    def validate_transform_limits(self, transform: OOXMLTransform) -> dict[str, Any]:
        """
        Validate transform against PowerPoint limits.

        Args:
            transform: OOXML transform to validate

        Returns:
            Validation result with warnings and errors
        """
        result = {
            'valid': True,
            'warnings': [],
            'errors': [],
        }

        # Check coordinate limits (PowerPoint has practical limits)
        max_coord = 2**31 - 1  # 32-bit signed integer limit

        if abs(transform.x) > max_coord:
            result['errors'].append(f"X coordinate {transform.x} exceeds limits")
            result['valid'] = False

        if abs(transform.y) > max_coord:
            result['errors'].append(f"Y coordinate {transform.y} exceeds limits")
            result['valid'] = False

        if transform.width <= 0:
            result['errors'].append(f"Width {transform.width} must be positive")
            result['valid'] = False

        if transform.height <= 0:
            result['errors'].append(f"Height {transform.height} must be positive")
            result['valid'] = False

        # Check for very large dimensions (performance warning)
        max_practical_size = 100 * self.EMU_PER_INCH  # 100 inches

        if transform.width > max_practical_size:
            result['warnings'].append(f"Width {transform.width} EMU is very large")

        if transform.height > max_practical_size:
            result['warnings'].append(f"Height {transform.height} EMU is very large")

        # Check rotation range (PowerPoint handles full 360° range)
        if abs(transform.rotation) > 360 * self.ANGLE_UNITS_PER_DEGREE:
            result['warnings'].append(f"Rotation {transform.rotation} exceeds 360°")

        return result

    def optimize_transform(self, transform: OOXMLTransform) -> OOXMLTransform:
        """
        Optimize transform for PowerPoint compatibility.

        Args:
            transform: Original transform

        Returns:
            Optimized transform
        """
        # Normalize rotation to 0-360° range
        normalized_rotation = transform.rotation % (360 * self.ANGLE_UNITS_PER_DEGREE)

        # For common angles, snap to exact values for better compatibility
        common_angles = {
            0: 0,
            90 * self.ANGLE_UNITS_PER_DEGREE: 90 * self.ANGLE_UNITS_PER_DEGREE,
            180 * self.ANGLE_UNITS_PER_DEGREE: 180 * self.ANGLE_UNITS_PER_DEGREE,
            270 * self.ANGLE_UNITS_PER_DEGREE: 270 * self.ANGLE_UNITS_PER_DEGREE,
        }

        # Snap to common angles if within 1° tolerance
        tolerance = self.ANGLE_UNITS_PER_DEGREE  # 1 degree
        for exact_angle, snap_value in common_angles.items():
            if abs(normalized_rotation - exact_angle) <= tolerance:
                normalized_rotation = snap_value
                break

        return OOXMLTransform(
            x=transform.x,
            y=transform.y,
            width=transform.width,
            height=transform.height,
            rotation=normalized_rotation,
            flip_h=transform.flip_h,
            flip_v=transform.flip_v,
        )


def create_ooxml_transform_utils() -> OOXMLTransformUtils:
    """
    Factory function to create OOXML transform utilities.

    Returns:
        OOXMLTransformUtils instance
    """
    return OOXMLTransformUtils()
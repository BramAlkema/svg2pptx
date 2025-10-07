#!/usr/bin/env python3
"""
DrawingML Effect IR

Represents PowerPoint native visual effects (blur, shadow, glow, etc.)
that can be applied to shapes.

All measurements are stored in points (pt) and converted to EMU (English Metric Units)
for DrawingML output using the core.units system.
"""

from dataclasses import dataclass
from ..units import unit


@dataclass(frozen=True)
class Effect:
    """Base class for DrawingML effects"""
    pass


@dataclass(frozen=True)
class BlurEffect(Effect):
    """Gaussian blur effect

    Maps to <a:blur rad="..."/>

    Attributes:
        radius: Blur radius in points (converted to EMU)
    """
    radius: float  # points

    def to_emu(self) -> int:
        """Convert radius to EMU using unit system"""
        return unit(f"{self.radius}pt").to_emu()


@dataclass(frozen=True)
class ShadowEffect(Effect):
    """Drop shadow effect

    Maps to <a:outerShdw blurRad="..." dist="..." dir="..."/>

    Attributes:
        blur_radius: Shadow blur in points
        distance: Shadow offset distance in points
        angle: Shadow direction in degrees (0° = right, 90° = down)
        color: Shadow color (RRGGBB hex)
        alpha: Shadow opacity (0.0 to 1.0)
    """
    blur_radius: float  # points
    distance: float     # points
    angle: float        # degrees
    color: str = "000000"  # black
    alpha: float = 0.5     # 50% opacity

    def to_emu(self) -> tuple[int, int]:
        """Convert blur and distance to EMU using unit system"""
        return (
            unit(f"{self.blur_radius}pt").to_emu(),
            unit(f"{self.distance}pt").to_emu()
        )

    def to_direction_emu(self) -> int:
        """Convert angle to DrawingML direction (60000 per degree)"""
        return int(self.angle * 60000) % 21600000

    def to_alpha_val(self) -> int:
        """Convert alpha to DrawingML value (0-100000)"""
        return int(self.alpha * 100000)


@dataclass(frozen=True)
class GlowEffect(Effect):
    """Glow effect

    Maps to <a:glow rad="..."><a:srgbClr val="..."/></a:glow>

    Attributes:
        radius: Glow radius in points
        color: Glow color (RRGGBB hex)
    """
    radius: float
    color: str = "FFFFFF"  # white

    def to_emu(self) -> int:
        """Convert radius to EMU using unit system"""
        return unit(f"{self.radius}pt").to_emu()


@dataclass(frozen=True)
class SoftEdgeEffect(Effect):
    """Soft edge effect (feathered edges)

    Maps to <a:softEdge rad="..."/>

    Attributes:
        radius: Feather radius in points
    """
    radius: float

    def to_emu(self) -> int:
        """Convert radius to EMU using unit system"""
        return unit(f"{self.radius}pt").to_emu()


@dataclass(frozen=True)
class ReflectionEffect(Effect):
    """Reflection effect

    Maps to <a:reflection blurRad="..." stA="..." endA="..." dist="..."/>

    Attributes:
        blur_radius: Reflection blur in points
        start_alpha: Starting opacity (0.0 to 1.0)
        end_alpha: Ending opacity (0.0 to 1.0)
        distance: Reflection distance in points
    """
    blur_radius: float = 3.0
    start_alpha: float = 0.5
    end_alpha: float = 0.0
    distance: float = 0.0

    def to_emu(self) -> tuple[int, int]:
        """Convert blur and distance to EMU using unit system"""
        return (
            unit(f"{self.blur_radius}pt").to_emu(),
            unit(f"{self.distance}pt").to_emu()
        )

    def to_alpha_vals(self) -> tuple[int, int]:
        """Convert alpha values to DrawingML (0-100000)"""
        return (
            int(self.start_alpha * 100000),
            int(self.end_alpha * 100000)
        )

"""
EMF tile starter pack generator.

This module provides pre-configured EMF pattern tiles for common use cases,
optimized for PowerPoint compatibility and visual quality.
"""

from typing import Dict, List, Tuple, Optional
from .emf_blob import EMFBlob, create_pattern_tile, get_starter_pack


class EMFTileLibrary:
    """EMF tile library with pre-configured patterns."""

    def __init__(self):
        """Initialize the tile library."""
        self._tiles_cache: Dict[str, EMFBlob] = {}
        self._generate_starter_pack()

    def _generate_starter_pack(self) -> None:
        """Generate the starter pack of EMF tiles."""
        # Basic line patterns
        self._tiles_cache['hatch_horizontal'] = create_pattern_tile(
            'hatch',
            direction='horizontal',
            width=50, height=50,
            color=0x000000,
            background=0xFFFFFF
        )

        self._tiles_cache['hatch_vertical'] = create_pattern_tile(
            'hatch',
            direction='vertical',
            width=50, height=50,
            color=0x000000,
            background=0xFFFFFF
        )

        self._tiles_cache['hatch_diagonal_forward'] = create_pattern_tile(
            'hatch',
            direction='diagonal',
            width=50, height=50,
            color=0x000000,
            background=0xFFFFFF
        )

        self._tiles_cache['hatch_diagonal_back'] = create_pattern_tile(
            'hatch',
            direction='diagonal',  # Will need to be enhanced for backward diagonal
            width=50, height=50,
            color=0x000000,
            background=0xFFFFFF
        )

        # Cross patterns
        self._tiles_cache['crosshatch'] = create_pattern_tile(
            'crosshatch',
            spacing=10,
            width=50, height=50,
            color=0x000000,
            background=0xFFFFFF
        )

        self._tiles_cache['crosshatch_fine'] = create_pattern_tile(
            'crosshatch',
            spacing=5,
            width=25, height=25,
            color=0x000000,
            background=0xFFFFFF
        )

        self._tiles_cache['crosshatch_coarse'] = create_pattern_tile(
            'crosshatch',
            spacing=20,
            width=100, height=100,
            color=0x000000,
            background=0xFFFFFF
        )

        # Grid patterns
        self._tiles_cache['grid_fine'] = create_pattern_tile(
            'grid',
            cell_width=10, cell_height=10,
            line_width=1,
            width=50, height=50,
            color=0x808080,
            background=0xFFFFFF
        )

        self._tiles_cache['grid_medium'] = create_pattern_tile(
            'grid',
            cell_width=20, cell_height=20,
            line_width=1,
            width=100, height=100,
            color=0x606060,
            background=0xFFFFFF
        )

        self._tiles_cache['grid_coarse'] = create_pattern_tile(
            'grid',
            cell_width=40, cell_height=40,
            line_width=2,
            width=200, height=200,
            color=0x404040,
            background=0xFFFFFF
        )

        # Dot patterns
        self._tiles_cache['dots_small'] = create_pattern_tile(
            'dots',
            radius=2, spacing=8,
            width=25, height=25,
            color=0x000000,
            background=0xFFFFFF
        )

        self._tiles_cache['dots_medium'] = create_pattern_tile(
            'dots',
            radius=4, spacing=15,
            width=50, height=50,
            color=0x000000,
            background=0xFFFFFF
        )

        self._tiles_cache['dots_large'] = create_pattern_tile(
            'dots',
            radius=8, spacing=25,
            width=100, height=100,
            color=0x000000,
            background=0xFFFFFF
        )

        # Brick patterns
        self._tiles_cache['brick_standard'] = create_pattern_tile(
            'brick',
            brick_width=30, brick_height=15,
            mortar_width=2,
            width=120, height=60,
            color=0x8B4513,  # Saddle brown
            mortar_color=0xD3D3D3  # Light gray
        )

        self._tiles_cache['brick_running_bond'] = create_pattern_tile(
            'brick',
            brick_width=40, brick_height=20,
            mortar_width=3,
            width=160, height=80,
            color=0xB22222,  # Fire brick
            mortar_color=0xF5F5DC  # Beige
        )

        # Specialized patterns
        self._add_specialized_patterns()

    def _add_specialized_patterns(self) -> None:
        """Add specialized pattern tiles."""
        # Diagonal grid (45-degree rotated grid)
        self._tiles_cache['grid_diagonal'] = create_pattern_tile(
            'crosshatch',  # Using crosshatch as approximation
            spacing=15,
            width=75, height=75,
            color=0x606060,
            background=0xFFFFFF
        )

        # Hex dots pattern (approximated with regular dots)
        self._tiles_cache['hex_dots'] = create_pattern_tile(
            'dots',
            radius=6, spacing=18,
            width=60, height=60,
            color=0x4169E1,  # Royal blue
            background=0xFFFFFF
        )

        # Dense crosshatch for shading
        self._tiles_cache['crosshatch_dense'] = create_pattern_tile(
            'crosshatch',
            spacing=3,
            width=15, height=15,
            color=0x696969,  # Dim gray
            background=0xFFFFFF
        )

    def get_tile(self, pattern_name: str) -> Optional[EMFBlob]:
        """Get an EMF tile by name.

        Args:
            pattern_name: Name of the pattern tile

        Returns:
            EMFBlob instance or None if not found
        """
        return self._tiles_cache.get(pattern_name)

    def list_tiles(self) -> List[str]:
        """List all available tile names.

        Returns:
            List of pattern tile names
        """
        return sorted(self._tiles_cache.keys())

    def get_tiles_by_category(self, category: str) -> Dict[str, EMFBlob]:
        """Get tiles by category.

        Args:
            category: Category name ('hatch', 'crosshatch', 'grid', 'dots', 'brick')

        Returns:
            Dictionary of pattern tiles in the category
        """
        return {
            name: tile for name, tile in self._tiles_cache.items()
            if name.startswith(category)
        }

    def create_custom_tile(self, pattern_type: str, name: str, **kwargs) -> EMFBlob:
        """Create a custom tile and add it to the library.

        Args:
            pattern_type: Type of pattern ('hatch', 'crosshatch', 'grid', 'dots', 'brick')
            name: Custom name for the tile
            **kwargs: Pattern-specific parameters

        Returns:
            Created EMFBlob instance
        """
        tile = create_pattern_tile(pattern_type, **kwargs)
        self._tiles_cache[name] = tile
        return tile

    def get_tile_info(self, pattern_name: str) -> Optional[Dict[str, any]]:
        """Get information about a tile.

        Args:
            pattern_name: Name of the pattern tile

        Returns:
            Dictionary with tile information or None if not found
        """
        if pattern_name not in self._tiles_cache:
            return None

        tile = self._tiles_cache[pattern_name]
        return {
            'name': pattern_name,
            'width': tile.width,
            'height': tile.height,
            'category': self._get_category_from_name(pattern_name),
            'handles': len(tile.object_handles),
            'records': len(tile.records)
        }

    def _get_category_from_name(self, name: str) -> str:
        """Determine category from tile name."""
        if name.startswith('hatch'):
            return 'hatch'
        elif name.startswith('crosshatch'):
            return 'crosshatch'
        elif name.startswith('grid'):
            return 'grid'
        elif name.startswith('dots'):
            return 'dots'
        elif name.startswith('brick'):
            return 'brick'
        else:
            return 'custom'

    def export_tile_library_info(self) -> Dict[str, Dict[str, any]]:
        """Export complete tile library information.

        Returns:
            Dictionary with all tile information
        """
        return {
            name: self.get_tile_info(name)
            for name in self.list_tiles()
        }


# Global tile library instance
_tile_library: Optional[EMFTileLibrary] = None


def get_tile_library() -> EMFTileLibrary:
    """Get the global tile library instance.

    Returns:
        EMFTileLibrary singleton instance
    """
    global _tile_library
    if _tile_library is None:
        _tile_library = EMFTileLibrary()
    return _tile_library


def get_pattern_tile(pattern_name: str) -> Optional[EMFBlob]:
    """Get a pattern tile by name.

    Args:
        pattern_name: Name of the pattern tile

    Returns:
        EMFBlob instance or None if not found
    """
    return get_tile_library().get_tile(pattern_name)


def list_available_patterns() -> List[str]:
    """List all available pattern names.

    Returns:
        List of pattern tile names
    """
    return get_tile_library().list_tiles()


def get_patterns_by_category(category: str) -> Dict[str, EMFBlob]:
    """Get pattern tiles by category.

    Args:
        category: Category name ('hatch', 'crosshatch', 'grid', 'dots', 'brick')

    Returns:
        Dictionary of pattern tiles in the category
    """
    return get_tile_library().get_tiles_by_category(category)


def create_powerpoint_xml_for_pattern(pattern_name: str, tile_mode: str = 'tile') -> Optional[str]:
    """Create PowerPoint XML for a pattern tile.

    Args:
        pattern_name: Name of the pattern tile
        tile_mode: 'tile' or 'stretch' mode

    Returns:
        PowerPoint DrawingML XML string or None if pattern not found
    """
    tile = get_pattern_tile(pattern_name)
    if tile is None:
        return None

    # Generate a dummy handle for the pattern
    handle = hash(pattern_name) % 1000

    if tile_mode == 'stretch':
        return tile.xml_stretch_fill(handle)
    else:
        return tile.xml_tile_fill(handle)


# Pre-configured color schemes for patterns
PATTERN_COLOR_SCHEMES = {
    'grayscale': {
        'foreground': 0x000000,  # Black
        'background': 0xFFFFFF,  # White
        'accent': 0x808080       # Gray
    },
    'blueprint': {
        'foreground': 0xFFFFFF,  # White
        'background': 0x003366,  # Dark blue
        'accent': 0x6699CC       # Light blue
    },
    'warm': {
        'foreground': 0x8B4513,  # Saddle brown
        'background': 0xFFF8DC,  # Cornsilk
        'accent': 0xDEB887       # Burlywood
    },
    'cool': {
        'foreground': 0x2F4F4F,  # Dark slate gray
        'background': 0xF0F8FF,  # Alice blue
        'accent': 0x4682B4       # Steel blue
    },
    'high_contrast': {
        'foreground': 0x000000,  # Black
        'background': 0xFFFF00,  # Yellow
        'accent': 0xFF0000       # Red
    }
}


def create_colored_pattern(base_pattern: str, color_scheme: str,
                          custom_name: str = None) -> Optional[EMFBlob]:
    """Create a colored version of a pattern.

    Args:
        base_pattern: Base pattern name
        color_scheme: Color scheme name from PATTERN_COLOR_SCHEMES
        custom_name: Custom name for the new pattern

    Returns:
        New EMFBlob with applied colors or None if base pattern not found
    """
    if color_scheme not in PATTERN_COLOR_SCHEMES:
        raise ValueError(f"Unknown color scheme: {color_scheme}")

    colors = PATTERN_COLOR_SCHEMES[color_scheme]
    lib = get_tile_library()
    base_tile = lib.get_tile(base_pattern)

    if base_tile is None:
        return None

    # Determine pattern type from base pattern name
    pattern_type = lib._get_category_from_name(base_pattern)

    # Create new colored pattern
    if custom_name is None:
        custom_name = f"{base_pattern}_{color_scheme}"

    return lib.create_custom_tile(
        pattern_type,
        custom_name,
        width=base_tile.width,
        height=base_tile.height,
        color=colors['foreground'],
        background=colors['background']
    )
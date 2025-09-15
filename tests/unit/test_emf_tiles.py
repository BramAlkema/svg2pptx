"""
Test suite for EMF tiles starter pack.
Tests tile library, pattern generation, and PowerPoint XML generation.
"""

import pytest
from unittest.mock import patch, Mock

from src.emf_tiles import (
    EMFTileLibrary, get_tile_library, get_pattern_tile,
    list_available_patterns, get_patterns_by_category,
    create_powerpoint_xml_for_pattern, create_colored_pattern,
    PATTERN_COLOR_SCHEMES
)
from src.emf_blob import EMFBlob


class TestEMFTileLibrary:
    """Test suite for EMF tile library functionality."""

    @pytest.fixture
    def tile_library(self):
        """Create a fresh EMFTileLibrary instance."""
        return EMFTileLibrary()

    def test_initialization(self, tile_library):
        """Test tile library initialization."""
        assert isinstance(tile_library, EMFTileLibrary)
        assert len(tile_library._tiles_cache) > 0

    def test_starter_pack_generation(self, tile_library):
        """Test that starter pack contains expected patterns."""
        expected_patterns = [
            'hatch_horizontal', 'hatch_vertical', 'hatch_diagonal_forward',
            'crosshatch', 'crosshatch_fine', 'crosshatch_coarse',
            'grid_fine', 'grid_medium', 'grid_coarse',
            'dots_small', 'dots_medium', 'dots_large',
            'brick_standard', 'brick_running_bond'
        ]

        available_patterns = tile_library.list_tiles()

        for pattern in expected_patterns:
            assert pattern in available_patterns, f"Missing pattern: {pattern}"

    def test_get_tile_existing(self, tile_library):
        """Test getting an existing tile."""
        tile = tile_library.get_tile('crosshatch')

        assert tile is not None
        assert isinstance(tile, EMFBlob)
        assert tile.width > 0
        assert tile.height > 0

    def test_get_tile_nonexistent(self, tile_library):
        """Test getting a nonexistent tile."""
        tile = tile_library.get_tile('nonexistent_pattern')

        assert tile is None

    def test_list_tiles(self, tile_library):
        """Test listing all available tiles."""
        tiles = tile_library.list_tiles()

        assert isinstance(tiles, list)
        assert len(tiles) > 0
        assert all(isinstance(name, str) for name in tiles)
        # Should be sorted
        assert tiles == sorted(tiles)

    def test_get_tiles_by_category_hatch(self, tile_library):
        """Test getting tiles by hatch category."""
        hatch_tiles = tile_library.get_tiles_by_category('hatch')

        assert isinstance(hatch_tiles, dict)
        assert len(hatch_tiles) >= 3  # At least horizontal, vertical, diagonal
        assert all(name.startswith('hatch') for name in hatch_tiles.keys())
        assert all(isinstance(tile, EMFBlob) for tile in hatch_tiles.values())

    def test_get_tiles_by_category_crosshatch(self, tile_library):
        """Test getting tiles by crosshatch category."""
        crosshatch_tiles = tile_library.get_tiles_by_category('crosshatch')

        assert isinstance(crosshatch_tiles, dict)
        assert len(crosshatch_tiles) >= 3  # At least standard, fine, coarse
        assert all(name.startswith('crosshatch') for name in crosshatch_tiles.keys())

    def test_get_tiles_by_category_grid(self, tile_library):
        """Test getting tiles by grid category."""
        grid_tiles = tile_library.get_tiles_by_category('grid')

        assert isinstance(grid_tiles, dict)
        assert len(grid_tiles) >= 3  # At least fine, medium, coarse
        assert all(name.startswith('grid') for name in grid_tiles.keys())

    def test_get_tiles_by_category_dots(self, tile_library):
        """Test getting tiles by dots category."""
        dots_tiles = tile_library.get_tiles_by_category('dots')

        assert isinstance(dots_tiles, dict)
        assert len(dots_tiles) >= 3  # At least small, medium, large
        assert all(name.startswith('dots') for name in dots_tiles.keys())

    def test_get_tiles_by_category_brick(self, tile_library):
        """Test getting tiles by brick category."""
        brick_tiles = tile_library.get_tiles_by_category('brick')

        assert isinstance(brick_tiles, dict)
        assert len(brick_tiles) >= 2  # At least standard, running bond
        assert all(name.startswith('brick') for name in brick_tiles.keys())

    def test_create_custom_tile(self, tile_library):
        """Test creating a custom tile."""
        custom_tile = tile_library.create_custom_tile(
            'hatch',
            'my_custom_hatch',
            direction='horizontal',
            width=75, height=75,
            color=0xFF0000
        )

        assert isinstance(custom_tile, EMFBlob)
        assert custom_tile.width == 75
        assert custom_tile.height == 75

        # Should be added to library
        retrieved_tile = tile_library.get_tile('my_custom_hatch')
        assert retrieved_tile is custom_tile

    def test_get_tile_info_existing(self, tile_library):
        """Test getting info for existing tile."""
        info = tile_library.get_tile_info('crosshatch')

        assert info is not None
        assert info['name'] == 'crosshatch'
        assert info['width'] > 0
        assert info['height'] > 0
        assert info['category'] == 'crosshatch'
        assert isinstance(info['handles'], int)
        assert isinstance(info['records'], int)

    def test_get_tile_info_nonexistent(self, tile_library):
        """Test getting info for nonexistent tile."""
        info = tile_library.get_tile_info('nonexistent')

        assert info is None

    def test_category_determination(self, tile_library):
        """Test category determination from tile names."""
        assert tile_library._get_category_from_name('hatch_horizontal') == 'hatch'
        assert tile_library._get_category_from_name('crosshatch_fine') == 'crosshatch'
        assert tile_library._get_category_from_name('grid_medium') == 'grid'
        assert tile_library._get_category_from_name('dots_large') == 'dots'
        assert tile_library._get_category_from_name('brick_standard') == 'brick'
        assert tile_library._get_category_from_name('unknown_pattern') == 'custom'

    def test_export_tile_library_info(self, tile_library):
        """Test exporting complete tile library information."""
        info = tile_library.export_tile_library_info()

        assert isinstance(info, dict)
        assert len(info) > 0

        # Check structure of exported info
        for name, tile_info in info.items():
            assert isinstance(name, str)
            assert isinstance(tile_info, dict)
            assert 'name' in tile_info
            assert 'width' in tile_info
            assert 'height' in tile_info
            assert 'category' in tile_info

    def test_specialized_patterns(self, tile_library):
        """Test that specialized patterns are included."""
        specialized_patterns = ['grid_diagonal', 'hex_dots', 'crosshatch_dense']

        available_patterns = tile_library.list_tiles()

        for pattern in specialized_patterns:
            assert pattern in available_patterns, f"Missing specialized pattern: {pattern}"


class TestGlobalTileLibrary:
    """Test suite for global tile library functions."""

    def test_get_tile_library_singleton(self):
        """Test that get_tile_library returns singleton instance."""
        lib1 = get_tile_library()
        lib2 = get_tile_library()

        assert lib1 is lib2
        assert isinstance(lib1, EMFTileLibrary)

    def test_get_pattern_tile(self):
        """Test getting pattern tile through global function."""
        tile = get_pattern_tile('crosshatch')

        assert tile is not None
        assert isinstance(tile, EMFBlob)

    def test_get_pattern_tile_nonexistent(self):
        """Test getting nonexistent pattern tile."""
        tile = get_pattern_tile('nonexistent_pattern')

        assert tile is None

    def test_list_available_patterns(self):
        """Test listing available patterns through global function."""
        patterns = list_available_patterns()

        assert isinstance(patterns, list)
        assert len(patterns) > 0
        assert 'crosshatch' in patterns

    def test_get_patterns_by_category(self):
        """Test getting patterns by category through global function."""
        hatch_patterns = get_patterns_by_category('hatch')

        assert isinstance(hatch_patterns, dict)
        assert len(hatch_patterns) > 0
        assert all(name.startswith('hatch') for name in hatch_patterns.keys())


class TestPowerPointXMLGeneration:
    """Test suite for PowerPoint XML generation."""

    def test_create_powerpoint_xml_tile_mode(self):
        """Test creating PowerPoint XML in tile mode."""
        xml = create_powerpoint_xml_for_pattern('crosshatch', 'tile')

        assert xml is not None
        assert '<a:blipFill>' in xml
        assert '<a:tile' in xml
        assert 'r:embed=' in xml
        assert 'algn="tl"' in xml

    def test_create_powerpoint_xml_stretch_mode(self):
        """Test creating PowerPoint XML in stretch mode."""
        xml = create_powerpoint_xml_for_pattern('grid_fine', 'stretch')

        assert xml is not None
        assert '<a:blipFill>' in xml
        assert '<a:stretch>' in xml
        assert 'r:embed=' in xml
        assert '<a:fillRect/>' in xml

    def test_create_powerpoint_xml_nonexistent_pattern(self):
        """Test creating XML for nonexistent pattern."""
        xml = create_powerpoint_xml_for_pattern('nonexistent_pattern')

        assert xml is None

    def test_create_powerpoint_xml_default_mode(self):
        """Test that default mode is 'tile'."""
        xml = create_powerpoint_xml_for_pattern('dots_medium')

        assert xml is not None
        assert '<a:tile' in xml
        assert '<a:stretch>' not in xml


class TestColorSchemes:
    """Test suite for pattern color schemes."""

    def test_pattern_color_schemes_exist(self):
        """Test that predefined color schemes exist."""
        expected_schemes = ['grayscale', 'blueprint', 'warm', 'cool', 'high_contrast']

        for scheme in expected_schemes:
            assert scheme in PATTERN_COLOR_SCHEMES
            colors = PATTERN_COLOR_SCHEMES[scheme]
            assert 'foreground' in colors
            assert 'background' in colors
            assert 'accent' in colors

    def test_color_scheme_values(self):
        """Test color scheme values are valid RGB integers."""
        for scheme_name, colors in PATTERN_COLOR_SCHEMES.items():
            for color_name, color_value in colors.items():
                assert isinstance(color_value, int)
                assert 0 <= color_value <= 0xFFFFFF

    def test_create_colored_pattern_valid_scheme(self):
        """Test creating colored pattern with valid scheme."""
        colored_pattern = create_colored_pattern('crosshatch', 'blueprint')

        assert colored_pattern is not None
        assert isinstance(colored_pattern, EMFBlob)

    def test_create_colored_pattern_invalid_scheme(self):
        """Test creating colored pattern with invalid scheme."""
        with pytest.raises(ValueError, match="Unknown color scheme"):
            create_colored_pattern('crosshatch', 'invalid_scheme')

    def test_create_colored_pattern_nonexistent_base(self):
        """Test creating colored pattern with nonexistent base pattern."""
        colored_pattern = create_colored_pattern('nonexistent_pattern', 'grayscale')

        assert colored_pattern is None

    def test_create_colored_pattern_custom_name(self):
        """Test creating colored pattern with custom name."""
        lib = get_tile_library()
        colored_pattern = create_colored_pattern(
            'grid_fine', 'warm', 'my_warm_grid'
        )

        assert colored_pattern is not None
        # Should be added to library with custom name
        retrieved = lib.get_tile('my_warm_grid')
        assert retrieved is colored_pattern

    def test_create_colored_pattern_default_name(self):
        """Test creating colored pattern with default name generation."""
        lib = get_tile_library()
        colored_pattern = create_colored_pattern('dots_small', 'cool')

        assert colored_pattern is not None
        # Should be added with default name
        retrieved = lib.get_tile('dots_small_cool')
        assert retrieved is colored_pattern


class TestPatternQuality:
    """Test suite for pattern quality and consistency."""

    def test_all_patterns_have_valid_dimensions(self):
        """Test that all patterns have valid dimensions."""
        lib = get_tile_library()

        for pattern_name in lib.list_tiles():
            tile = lib.get_tile(pattern_name)
            assert tile.width > 0, f"Pattern {pattern_name} has invalid width"
            assert tile.height > 0, f"Pattern {pattern_name} has invalid height"

    def test_all_patterns_can_be_finalized(self):
        """Test that all patterns can be finalized to EMF blobs."""
        lib = get_tile_library()

        for pattern_name in lib.list_tiles():
            tile = lib.get_tile(pattern_name)
            try:
                blob = tile.finalize()
                assert isinstance(blob, bytes)
                assert len(blob) > 0
            except Exception as e:
                pytest.fail(f"Pattern {pattern_name} failed to finalize: {e}")

    def test_pattern_name_consistency(self):
        """Test that pattern names follow consistent conventions."""
        lib = get_tile_library()

        for pattern_name in lib.list_tiles():
            # Should be lowercase with underscores
            assert pattern_name.islower(), f"Pattern {pattern_name} not lowercase"
            assert ' ' not in pattern_name, f"Pattern {pattern_name} contains spaces"
            # Should have category prefix
            category = lib._get_category_from_name(pattern_name)
            if category != 'custom':
                assert pattern_name.startswith(category), f"Pattern {pattern_name} doesn't start with category {category}"

    def test_pattern_categories_coverage(self):
        """Test that all expected categories have patterns."""
        lib = get_tile_library()
        expected_categories = ['hatch', 'crosshatch', 'grid', 'dots', 'brick']

        for category in expected_categories:
            patterns = lib.get_tiles_by_category(category)
            assert len(patterns) > 0, f"No patterns found for category {category}"

    def test_pattern_size_distribution(self):
        """Test that patterns have reasonable size distribution."""
        lib = get_tile_library()
        sizes = []

        for pattern_name in lib.list_tiles():
            tile = lib.get_tile(pattern_name)
            sizes.append((tile.width, tile.height))

        # Should have variety in sizes
        unique_sizes = set(sizes)
        assert len(unique_sizes) > 5, "Not enough size variety in patterns"

        # All sizes should be reasonable (between 15 and 200)
        for width, height in sizes:
            assert 15 <= width <= 200, f"Width {width} outside reasonable range"
            assert 15 <= height <= 200, f"Height {height} outside reasonable range"


class TestIntegrationWithEMFBlob:
    """Test suite for integration with EMFBlob functionality."""

    def test_tile_generation_matches_emf_blob(self):
        """Test that tile generation produces valid EMF blobs."""
        lib = get_tile_library()
        tile = lib.get_tile('crosshatch')

        # Should have EMF blob characteristics
        assert hasattr(tile, 'records')
        assert hasattr(tile, 'object_handles')
        assert hasattr(tile, 'finalize')
        assert hasattr(tile, 'xml_tile_fill')
        assert hasattr(tile, 'xml_stretch_fill')

    def test_xml_generation_integration(self):
        """Test XML generation integration."""
        lib = get_tile_library()
        tile = lib.get_tile('grid_medium')

        # Test both XML generation methods
        tile_xml = tile.xml_tile_fill(1)
        stretch_xml = tile.xml_stretch_fill(1)

        assert tile_xml != stretch_xml
        assert '<a:tile' in tile_xml
        assert '<a:stretch>' in stretch_xml

    def test_custom_tile_integration(self):
        """Test that custom tiles integrate properly."""
        lib = get_tile_library()
        custom_tile = lib.create_custom_tile(
            'hatch', 'integration_test',
            direction='vertical',
            width=60, height=60
        )

        # Should work with all EMF blob methods
        blob = custom_tile.finalize()
        xml = custom_tile.xml_tile_fill(999)

        assert isinstance(blob, bytes)
        assert len(blob) > 0
        assert 'r:embed="emf_999"' in xml
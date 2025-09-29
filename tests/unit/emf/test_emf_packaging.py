"""
Test suite for EMF packaging and PowerPoint integration.
Tests relationship management, PPTX integration, and shape generation.
"""

import pytest
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from src.emf_packaging import (
    EMFRelationshipManager, PPTXEMFIntegrator, EMFShapeGenerator,
    EMFPackagingError, create_emf_integrator, create_shape_generator,
    create_pattern_rectangle_xml, validate_emf_packaging
)
from src.emf_blob import EMFBlob, create_pattern_tile


class TestEMFRelationshipManager:
    """Test suite for EMF relationship management."""

    @pytest.fixture
    def relationship_manager(self):
        """Create EMF relationship manager."""
        return EMFRelationshipManager()

    @pytest.fixture
    def sample_emf_data(self):
        """Create sample EMF data."""
        return b'\x01\x00\x00\x00\x6c\x00\x00\x00' + b'\x00' * 100

    def test_initialization(self, relationship_manager):
        """Test relationship manager initialization."""
        assert len(relationship_manager._emf_blobs) == 0
        assert len(relationship_manager._relationships) == 0
        assert relationship_manager._next_id == 1

    def test_add_emf_blob_with_name(self, relationship_manager, sample_emf_data):
        """Test adding EMF blob with explicit name."""
        rel_id = relationship_manager.add_emf_blob(sample_emf_data, "test_pattern.emf")

        assert rel_id == "rId1"
        assert "test_pattern.emf" in relationship_manager._emf_blobs
        assert relationship_manager._relationships["rId1"] == "test_pattern.emf"
        assert relationship_manager._next_id == 2

    def test_add_emf_blob_without_name(self, relationship_manager, sample_emf_data):
        """Test adding EMF blob without explicit name (auto-generated)."""
        rel_id = relationship_manager.add_emf_blob(sample_emf_data)

        assert rel_id == "rId1"
        assert len(relationship_manager._emf_blobs) == 1
        assert len(relationship_manager._relationships) == 1

        # Check auto-generated name format
        filename = relationship_manager._relationships[rel_id]
        assert filename.startswith("emf_")
        assert filename.endswith(".emf")

    def test_add_multiple_emf_blobs(self, relationship_manager, sample_emf_data):
        """Test adding multiple EMF blobs."""
        rel_id1 = relationship_manager.add_emf_blob(sample_emf_data, "pattern1.emf")
        rel_id2 = relationship_manager.add_emf_blob(sample_emf_data + b'\x01', "pattern2.emf")

        assert rel_id1 == "rId1"
        assert rel_id2 == "rId2"
        assert len(relationship_manager._emf_blobs) == 2
        assert relationship_manager._next_id == 3

    def test_get_emf_data_existing(self, relationship_manager, sample_emf_data):
        """Test getting EMF data for existing relationship."""
        rel_id = relationship_manager.add_emf_blob(sample_emf_data, "test.emf")
        retrieved_data = relationship_manager.get_emf_data(rel_id)

        assert retrieved_data == sample_emf_data

    def test_get_emf_data_nonexistent(self, relationship_manager):
        """Test getting EMF data for nonexistent relationship."""
        data = relationship_manager.get_emf_data("rId999")

        assert data is None

    def test_get_emf_filename(self, relationship_manager, sample_emf_data):
        """Test getting EMF filename by relationship ID."""
        rel_id = relationship_manager.add_emf_blob(sample_emf_data, "test.emf")
        filename = relationship_manager.get_emf_filename(rel_id)

        assert filename == "test.emf"

    def test_get_emf_filename_nonexistent(self, relationship_manager):
        """Test getting filename for nonexistent relationship."""
        filename = relationship_manager.get_emf_filename("rId999")

        assert filename is None

    def test_list_relationships(self, relationship_manager, sample_emf_data):
        """Test listing all relationships."""
        rel_id1 = relationship_manager.add_emf_blob(sample_emf_data, "pattern1.emf")
        rel_id2 = relationship_manager.add_emf_blob(sample_emf_data, "pattern2.emf")

        relationships = relationship_manager.list_relationships()

        assert len(relationships) == 2
        assert (rel_id1, "pattern1.emf") in relationships
        assert (rel_id2, "pattern2.emf") in relationships

    def test_generate_relationship_xml_empty(self, relationship_manager):
        """Test generating relationship XML with no relationships."""
        xml = relationship_manager.generate_relationship_xml()

        assert xml == ""

    def test_generate_relationship_xml_single(self, relationship_manager, sample_emf_data):
        """Test generating relationship XML with single relationship."""
        rel_id = relationship_manager.add_emf_blob(sample_emf_data, "test.emf")
        xml = relationship_manager.generate_relationship_xml()

        assert '<?xml version="1.0"' in xml
        assert '<Relationships' in xml
        assert f'Id="{rel_id}"' in xml
        assert 'Target="../media/test.emf"' in xml
        assert 'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"' in xml

    def test_generate_relationship_xml_multiple(self, relationship_manager, sample_emf_data):
        """Test generating relationship XML with multiple relationships."""
        rel_id1 = relationship_manager.add_emf_blob(sample_emf_data, "pattern1.emf")
        rel_id2 = relationship_manager.add_emf_blob(sample_emf_data, "pattern2.emf")

        xml = relationship_manager.generate_relationship_xml()

        assert f'Id="{rel_id1}"' in xml
        assert f'Id="{rel_id2}"' in xml
        assert 'Target="../media/pattern1.emf"' in xml
        assert 'Target="../media/pattern2.emf"' in xml


class TestPPTXEMFIntegrator:
    """Test suite for PPTX EMF integration."""

    @pytest.fixture
    def integrator(self):
        """Create PPTX EMF integrator."""
        return PPTXEMFIntegrator()

    @pytest.fixture
    def mock_tile_library(self):
        """Mock tile library with test pattern."""
        mock_tile = Mock(spec=EMFBlob)
        mock_tile.finalize.return_value = b'\x01\x00\x00\x00\x6c\x00\x00\x00' + b'\x00' * 100

        with patch('src.emf_packaging.get_pattern_tile') as mock_get_tile:
            mock_get_tile.return_value = mock_tile
            yield mock_get_tile

    def test_initialization(self, integrator):
        """Test integrator initialization."""
        assert hasattr(integrator, 'relationship_manager')
        assert isinstance(integrator.relationship_manager, EMFRelationshipManager)

    def test_add_pattern_fill_valid_pattern(self, integrator, mock_tile_library):
        """Test adding valid pattern fill."""
        xml = integrator.add_pattern_fill('crosshatch', 'tile')

        assert '<a:blipFill>' in xml
        assert '<a:tile' in xml
        assert 'r:embed="rId1"' in xml
        mock_tile_library.assert_called_once_with('crosshatch')

    def test_add_pattern_fill_nonexistent_pattern(self, integrator):
        """Test adding nonexistent pattern fill."""
        with patch('src.emf_packaging.get_pattern_tile', return_value=None):
            with pytest.raises(EMFPackagingError, match="Pattern 'nonexistent' not found"):
                integrator.add_pattern_fill('nonexistent')

    def test_add_pattern_fill_stretch_mode(self, integrator, mock_tile_library):
        """Test adding pattern fill in stretch mode."""
        xml = integrator.add_pattern_fill('grid_fine', 'stretch')

        assert '<a:blipFill>' in xml
        assert '<a:stretch>' in xml
        assert '<a:fillRect/>' in xml
        assert 'r:embed="rId1"' in xml

    def test_add_custom_emf_valid(self, integrator):
        """Test adding custom EMF blob."""
        mock_emf = Mock(spec=EMFBlob)
        mock_emf.finalize.return_value = b'\x01\x00\x00\x00\x6c\x00\x00\x00' + b'\x00' * 100

        xml = integrator.add_custom_emf(mock_emf, 'custom_pattern', 'tile')

        assert '<a:blipFill>' in xml
        assert '<a:tile' in xml
        assert 'r:embed="rId1"' in xml
        mock_emf.finalize.assert_called_once()

    def test_add_custom_emf_finalize_error(self, integrator):
        """Test adding custom EMF with finalization error."""
        mock_emf = Mock(spec=EMFBlob)
        mock_emf.finalize.side_effect = Exception("Finalization failed")

        with pytest.raises(EMFPackagingError, match="Failed to package custom EMF"):
            integrator.add_custom_emf(mock_emf, 'custom_pattern')

    def test_generate_tile_fill_xml(self, integrator):
        """Test generating tile fill XML."""
        xml = integrator._generate_tile_fill_xml("rId123")

        assert '<a:blipFill>' in xml
        assert '<a:tile' in xml
        assert 'r:embed="rId123"' in xml
        assert 'algn="tl"' in xml
        assert 'sx="100000" sy="100000"' in xml

    def test_generate_stretch_fill_xml(self, integrator):
        """Test generating stretch fill XML."""
        xml = integrator._generate_stretch_fill_xml("rId456")

        assert '<a:blipFill>' in xml
        assert '<a:stretch>' in xml
        assert 'r:embed="rId456"' in xml
        assert '<a:fillRect/>' in xml

    def test_export_to_pptx_media(self, integrator, mock_tile_library):
        """Test exporting EMF blobs to PPTX media directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            media_dir = Path(temp_dir) / "media"

            # Add a pattern fill first
            integrator.add_pattern_fill('crosshatch')

            exported = integrator.export_to_pptx_media(media_dir)

            assert len(exported) == 1
            assert "rId1" in exported
            assert exported["rId1"].endswith(".emf")

            # Check file was created
            emf_file = media_dir / exported["rId1"]
            assert emf_file.exists()
            assert emf_file.stat().st_size > 0

    def test_get_relationship_xml(self, integrator, mock_tile_library):
        """Test getting relationship XML."""
        integrator.add_pattern_fill('crosshatch')
        xml = integrator.get_relationship_xml()

        assert '<?xml version="1.0"' in xml
        assert '<Relationships' in xml
        assert 'rId1' in xml

    def test_update_content_types_new_emf(self, integrator):
        """Test updating content types XML with new EMF extension."""
        original_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="png" ContentType="image/png"/>
</Types>'''

        updated_xml = integrator.update_content_types(original_xml)

        assert 'Extension="emf"' in updated_xml
        assert 'ContentType="image/x-emf"' in updated_xml
        assert 'Extension="png"' in updated_xml  # Original should remain

    def test_update_content_types_existing_emf(self, integrator):
        """Test updating content types XML with existing EMF extension."""
        original_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="emf" ContentType="image/x-emf"/>
    <Default Extension="png" ContentType="image/png"/>
</Types>'''

        updated_xml = integrator.update_content_types(original_xml)

        # Should not duplicate EMF extension
        emf_count = updated_xml.count('Extension="emf"')
        assert emf_count == 1


class TestEMFShapeGenerator:
    """Test suite for EMF shape generation."""

    @pytest.fixture
    def integrator(self):
        """Create PPTX EMF integrator."""
        return PPTXEMFIntegrator()

    @pytest.fixture
    def shape_generator(self, integrator):
        """Create EMF shape generator."""
        return EMFShapeGenerator(integrator)

    @pytest.fixture
    def mock_tile_library(self):
        """Mock tile library."""
        mock_tile = Mock(spec=EMFBlob)
        mock_tile.finalize.return_value = b'\x01\x00\x00\x00\x6c\x00\x00\x00' + b'\x00' * 100

        with patch('src.emf_packaging.get_pattern_tile') as mock_get_tile:
            mock_get_tile.return_value = mock_tile
            yield mock_get_tile

    def test_initialization(self, shape_generator, integrator):
        """Test shape generator initialization."""
        assert shape_generator.integrator is integrator
        assert shape_generator.shape_id == 1

    def test_create_rectangle_with_pattern(self, shape_generator, mock_tile_library):
        """Test creating rectangle with pattern fill."""
        xml = shape_generator.create_rectangle_with_pattern(
            x=100, y=200, width=300, height=400,
            pattern_name='crosshatch', tile_mode='tile'
        )

        assert '<p:sp>' in xml
        assert '<p:cNvPr id="1" name="Rectangle 1"/>' in xml
        assert '<a:off x="100" y="200"/>' in xml
        assert '<a:ext cx="300" cy="400"/>' in xml
        assert '<a:prstGeom prst="rect">' in xml
        assert '<a:blipFill>' in xml

    def test_create_ellipse_with_pattern(self, shape_generator, mock_tile_library):
        """Test creating ellipse with pattern fill."""
        xml = shape_generator.create_ellipse_with_pattern(
            x=50, y=75, width=150, height=200,
            pattern_name='grid_fine', tile_mode='stretch'
        )

        assert '<p:sp>' in xml
        assert '<p:cNvPr id="1" name="Ellipse 1"/>' in xml
        assert '<a:off x="50" y="75"/>' in xml
        assert '<a:ext cx="150" cy="200"/>' in xml
        assert '<a:prstGeom prst="ellipse">' in xml
        assert '<a:blipFill>' in xml
        assert '<a:stretch>' in xml

    def test_shape_id_increment(self, shape_generator, mock_tile_library):
        """Test that shape IDs increment properly."""
        xml1 = shape_generator.create_rectangle_with_pattern(
            0, 0, 100, 100, 'crosshatch'
        )
        xml2 = shape_generator.create_ellipse_with_pattern(
            0, 0, 100, 100, 'grid_fine'
        )

        assert 'id="1"' in xml1
        assert 'id="2"' in xml2

    def test_create_rectangle_invalid_pattern(self, shape_generator):
        """Test creating rectangle with invalid pattern."""
        with patch('src.emf_packaging.get_pattern_tile', return_value=None):
            with pytest.raises(EMFPackagingError):
                shape_generator.create_rectangle_with_pattern(
                    0, 0, 100, 100, 'invalid_pattern'
                )


class TestFactoryFunctions:
    """Test suite for factory functions."""

    def test_create_emf_integrator(self):
        """Test creating EMF integrator via factory."""
        integrator = create_emf_integrator()

        assert isinstance(integrator, PPTXEMFIntegrator)
        assert hasattr(integrator, 'relationship_manager')

    def test_create_shape_generator_with_integrator(self):
        """Test creating shape generator with provided integrator."""
        integrator = PPTXEMFIntegrator()
        generator = create_shape_generator(integrator)

        assert isinstance(generator, EMFShapeGenerator)
        assert generator.integrator is integrator

    def test_create_shape_generator_without_integrator(self):
        """Test creating shape generator without provided integrator."""
        generator = create_shape_generator()

        assert isinstance(generator, EMFShapeGenerator)
        assert isinstance(generator.integrator, PPTXEMFIntegrator)

    def test_create_pattern_rectangle_xml(self):
        """Test creating pattern rectangle XML via utility function."""
        with patch('src.emf_packaging.get_pattern_tile') as mock_get_tile:
            mock_tile = Mock(spec=EMFBlob)
            mock_tile.finalize.return_value = b'\x01\x00\x00\x00\x6c\x00\x00\x00' + b'\x00' * 100
            mock_get_tile.return_value = mock_tile

            xml, integrator = create_pattern_rectangle_xml(
                x=100, y=200, width=300, height=400,
                pattern_name='crosshatch'
            )

            assert '<p:sp>' in xml
            assert '<a:off x="100" y="200"/>' in xml
            assert '<a:ext cx="300" cy="400"/>' in xml
            assert isinstance(integrator, PPTXEMFIntegrator)


class TestValidationFunctions:
    """Test suite for validation functions."""

    def test_validate_emf_packaging_empty(self):
        """Test validation with empty integrator."""
        integrator = PPTXEMFIntegrator()
        warnings = validate_emf_packaging(integrator)

        assert len(warnings) == 1
        assert "No EMF blobs registered" in warnings[0]

    def test_validate_emf_packaging_valid(self):
        """Test validation with valid integrator."""
        integrator = PPTXEMFIntegrator()

        with patch('src.emf_packaging.get_pattern_tile') as mock_get_tile:
            mock_tile = Mock(spec=EMFBlob)
            mock_tile.finalize.return_value = b'\x01\x00\x00\x00\x6c\x00\x00\x00' + b'\x00' * 100
            mock_get_tile.return_value = mock_tile

            integrator.add_pattern_fill('crosshatch')

        warnings = validate_emf_packaging(integrator)

        assert len(warnings) == 0

    def test_validate_emf_packaging_duplicate_data(self):
        """Test validation with duplicate EMF data."""
        integrator = PPTXEMFIntegrator()

        with patch('src.emf_packaging.get_pattern_tile') as mock_get_tile:
            mock_tile = Mock(spec=EMFBlob)
            # Same data for both patterns
            mock_tile.finalize.return_value = b'\x01\x00\x00\x00\x6c\x00\x00\x00' + b'\x00' * 100
            mock_get_tile.return_value = mock_tile

            integrator.add_pattern_fill('pattern1')
            integrator.add_pattern_fill('pattern2')

        warnings = validate_emf_packaging(integrator)

        assert len(warnings) == 1
        assert "Duplicate EMF data detected" in warnings[0]

    def test_validate_emf_packaging_invalid_header(self):
        """Test validation with invalid EMF header."""
        integrator = PPTXEMFIntegrator()

        with patch('src.emf_packaging.get_pattern_tile') as mock_get_tile:
            mock_tile = Mock(spec=EMFBlob)
            # Invalid EMF header (should start with \x01\x00\x00\x00)
            mock_tile.finalize.return_value = b'\xFF\xFF\xFF\xFF' + b'\x00' * 100
            mock_get_tile.return_value = mock_tile

            integrator.add_pattern_fill('invalid_pattern')

        warnings = validate_emf_packaging(integrator)

        assert len(warnings) == 1
        assert "Invalid EMF header" in warnings[0]


class TestIntegrationScenarios:
    """Test suite for integration scenarios."""

    def test_complete_pattern_workflow(self):
        """Test complete workflow from pattern to PowerPoint XML."""
        with patch('src.emf_packaging.get_pattern_tile') as mock_get_tile:
            mock_tile = Mock(spec=EMFBlob)
            mock_tile.finalize.return_value = b'\x01\x00\x00\x00\x6c\x00\x00\x00' + b'\x00' * 100
            mock_get_tile.return_value = mock_tile

            # Create integrator and add pattern
            integrator = create_emf_integrator()
            fill_xml = integrator.add_pattern_fill('crosshatch')

            # Create shape with pattern
            generator = create_shape_generator(integrator)
            shape_xml = generator.create_rectangle_with_pattern(
                914400, 914400, 1828800, 1828800, 'grid_fine'
            )

            # Export to media directory
            with tempfile.TemporaryDirectory() as temp_dir:
                media_dir = Path(temp_dir) / "media"
                exported = integrator.export_to_pptx_media(media_dir)

                # Get relationship XML
                rel_xml = integrator.get_relationship_xml()

                # Validate all components
                assert '<a:blipFill>' in fill_xml
                assert '<p:sp>' in shape_xml
                assert len(exported) >= 1
                assert '<?xml version="1.0"' in rel_xml

    def test_multiple_patterns_in_presentation(self):
        """Test using multiple different patterns in one presentation."""
        with patch('src.emf_packaging.get_pattern_tile') as mock_get_tile:
            # Different EMF data for each pattern
            def mock_finalize_side_effect():
                import random
                base = b'\x01\x00\x00\x00\x6c\x00\x00\x00'
                suffix = bytes([random.randint(0, 255) for _ in range(100)])
                return base + suffix

            mock_tile = Mock(spec=EMFBlob)
            mock_tile.finalize.side_effect = mock_finalize_side_effect
            mock_get_tile.return_value = mock_tile

            integrator = create_emf_integrator()
            generator = create_shape_generator(integrator)

            # Add multiple patterns
            patterns = ['crosshatch', 'grid_fine', 'dots_small', 'brick_standard']
            shapes = []

            for i, pattern in enumerate(patterns):
                shape_xml = generator.create_rectangle_with_pattern(
                    i * 914400, 0, 914400, 914400, pattern
                )
                shapes.append(shape_xml)

            # Check that each shape has correct coordinates and different embed IDs
            assert len(shapes) == 4
            for i, shape in enumerate(shapes):
                assert f'<a:off x="{i * 914400}" y="0"/>' in shape
                assert f'r:embed="rId{i+1}"' in shape

            # Check relationship count
            relationships = integrator.relationship_manager.list_relationships()
            assert len(relationships) == 4

    def test_error_handling_workflow(self):
        """Test error handling in complete workflow."""
        integrator = create_emf_integrator()

        # Test with nonexistent pattern
        with pytest.raises(EMFPackagingError):
            integrator.add_pattern_fill('nonexistent_pattern')

        # Test with EMF finalization error
        mock_emf = Mock(spec=EMFBlob)
        mock_emf.finalize.side_effect = RuntimeError("EMF error")

        with pytest.raises(EMFPackagingError):
            integrator.add_custom_emf(mock_emf, 'error_pattern')

        # Integrator should still be in clean state
        assert len(integrator.relationship_manager._relationships) == 0
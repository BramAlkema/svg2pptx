"""
EMF blob packaging for PowerPoint integration.

This module handles embedding EMF blobs into PowerPoint presentations,
managing relationships, and generating proper OOXML markup.
"""

import io
import hashlib
import base64
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import zipfile
from lxml import etree as ET
from xml.dom import minidom

from .emf_blob import EMFBlob
from .emf_tiles import get_pattern_tile


class EMFPackagingError(Exception):
    """Exception raised for EMF packaging errors."""
    pass


class EMFRelationshipManager:
    """Manages EMF blob relationships in PowerPoint packages."""

    def __init__(self):
        """Initialize relationship manager."""
        self._emf_blobs: Dict[str, bytes] = {}
        self._relationships: Dict[str, str] = {}
        self._next_id = 1

    def add_emf_blob(self, emf_data: bytes, name: Optional[str] = None) -> str:
        """Add an EMF blob and return its relationship ID.

        Args:
            emf_data: EMF blob bytes
            name: Optional name for the EMF (auto-generated if None)

        Returns:
            Relationship ID (e.g., "rId123")
        """
        if name is None:
            # Generate name from content hash
            hash_obj = hashlib.md5(emf_data, usedforsecurity=False)
            name = f"emf_{hash_obj.hexdigest()[:8]}.emf"

        # Generate relationship ID
        rel_id = f"rId{self._next_id}"
        self._next_id += 1

        # Store blob and relationship
        self._emf_blobs[name] = emf_data
        self._relationships[rel_id] = name

        return rel_id

    def get_emf_data(self, rel_id: str) -> Optional[bytes]:
        """Get EMF data by relationship ID.

        Args:
            rel_id: Relationship ID

        Returns:
            EMF blob bytes or None if not found
        """
        name = self._relationships.get(rel_id)
        if name is None:
            return None
        return self._emf_blobs.get(name)

    def get_emf_filename(self, rel_id: str) -> Optional[str]:
        """Get EMF filename by relationship ID.

        Args:
            rel_id: Relationship ID

        Returns:
            Filename or None if not found
        """
        return self._relationships.get(rel_id)

    def list_relationships(self) -> List[Tuple[str, str]]:
        """List all EMF relationships.

        Returns:
            List of (relationship_id, filename) tuples
        """
        return list(self._relationships.items())

    def generate_relationship_xml(self) -> str:
        """Generate relationship XML for EMF blobs.

        Returns:
            XML string for relationships
        """
        # TODO: DUPLICATE - Consolidate with src/utils/xml_builder.py
        # WARNING: This duplicates XML relationship generation functionality
        # MIGRATE: Replace with self.services.xml_builder.create_relationships()
        # PRIORITY: MEDIUM - Phase 2 XML generation consolidation
        # EFFORT: 2h - Relationships XML template standardization
        from ..utils.migration_tracker import DuplicateWarning
        DuplicateWarning.warn_duplicate('src/utils/xml_builder.py', 'XMLBuilder.create_relationships()', 'xml_generation', 'MEDIUM')

        relationships = []

        for rel_id, filename in self._relationships.items():
            relationships.append(
                f'<Relationship Id="{rel_id}" '
                f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                f'Target="../media/{filename}"/>'
            )

        if not relationships:
            return ""

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    {chr(10).join(relationships)}
</Relationships>'''


class PPTXEMFIntegrator:
    """Integrates EMF blobs into PowerPoint presentations."""

    def __init__(self):
        """Initialize PPTX EMF integrator."""
        self.relationship_manager = EMFRelationshipManager()

    def add_pattern_fill(self, pattern_name: str, tile_mode: str = 'tile') -> str:
        """Add a pattern fill EMF and return PowerPoint XML.

        Args:
            pattern_name: Name of the pattern from the tile library
            tile_mode: 'tile' or 'stretch' mode

        Returns:
            PowerPoint DrawingML XML for the pattern fill

        Raises:
            EMFPackagingError: If pattern not found or packaging fails
        """
        # Get pattern tile
        tile = get_pattern_tile(pattern_name)
        if tile is None:
            raise EMFPackagingError(f"Pattern '{pattern_name}' not found in tile library")

        try:
            # Generate EMF blob
            emf_data = tile.finalize()

            # Add to relationship manager
            rel_id = self.relationship_manager.add_emf_blob(emf_data, f"{pattern_name}.emf")

            # Generate XML
            if tile_mode == 'stretch':
                return self._generate_stretch_fill_xml(rel_id)
            else:
                return self._generate_tile_fill_xml(rel_id)

        except Exception as e:
            raise EMFPackagingError(f"Failed to package pattern '{pattern_name}': {e}")

    def add_custom_emf(self, emf_blob: EMFBlob, name: str, tile_mode: str = 'tile') -> str:
        """Add a custom EMF blob and return PowerPoint XML.

        Args:
            emf_blob: EMF blob instance
            name: Name for the EMF
            tile_mode: 'tile' or 'stretch' mode

        Returns:
            PowerPoint DrawingML XML for the EMF fill

        Raises:
            EMFPackagingError: If packaging fails
        """
        try:
            # Generate EMF blob
            emf_data = emf_blob.finalize()

            # Add to relationship manager
            rel_id = self.relationship_manager.add_emf_blob(emf_data, f"{name}.emf")

            # Generate XML
            if tile_mode == 'stretch':
                return self._generate_stretch_fill_xml(rel_id)
            else:
                return self._generate_tile_fill_xml(rel_id)

        except Exception as e:
            raise EMFPackagingError(f"Failed to package custom EMF '{name}': {e}")

    def _generate_tile_fill_xml(self, rel_id: str) -> str:
        """Generate tiled fill XML.

        Args:
            rel_id: Relationship ID for the EMF

        Returns:
            PowerPoint DrawingML XML
        """
        # TODO: DUPLICATE - Consolidate with src/utils/xml_builder.py
        # WARNING: This duplicates DrawingML XML generation functionality
        # MIGRATE: Replace with self.services.xml_builder.create_blip_fill()
        # PRIORITY: MEDIUM - Phase 2 XML generation consolidation
        # EFFORT: 3h - XML template consolidation and PowerPoint validation
        from ..utils.migration_tracker import DuplicateWarning
        DuplicateWarning.warn_duplicate('src/utils/xml_builder.py', 'XMLBuilder.create_blip_fill()', 'xml_generation', 'MEDIUM')

        return f'''
        <a:blipFill>
            <a:blip r:embed="{rel_id}">
                <a:extLst>
                    <a:ext uri="{{28A0092B-C50C-407E-A947-70E740481C1C}}">
                        <a14:useLocalDpi xmlns:a14="http://schemas.microsoft.com/office/drawing/2010/main" val="0"/>
                    </a:ext>
                </a:extLst>
            </a:blip>
            <a:tile tx="0" ty="0" sx="100000" sy="100000" algn="tl" flip="none"/>
        </a:blipFill>'''

    def _generate_stretch_fill_xml(self, rel_id: str) -> str:
        """Generate stretched fill XML.

        Args:
            rel_id: Relationship ID for the EMF

        Returns:
            PowerPoint DrawingML XML
        """
        # TODO: DUPLICATE - Consolidate with src/utils/xml_builder.py
        # WARNING: This duplicates DrawingML XML generation functionality
        # MIGRATE: Replace with self.services.xml_builder.create_blip_fill()
        # PRIORITY: MEDIUM - Phase 2 XML generation consolidation
        # EFFORT: 3h - XML template consolidation with stretch mode support
        from ..utils.migration_tracker import DuplicateWarning
        DuplicateWarning.warn_duplicate('src/utils/xml_builder.py', 'XMLBuilder.create_blip_fill()', 'xml_generation', 'MEDIUM')

        return f'''
        <a:blipFill>
            <a:blip r:embed="{rel_id}">
                <a:extLst>
                    <a:ext uri="{{28A0092B-C50C-407E-A947-70E740481C1C}}">
                        <a14:useLocalDpi xmlns:a14="http://schemas.microsoft.com/office/drawing/2010/main" val="0"/>
                    </a:ext>
                </a:extLst>
            </a:blip>
            <a:stretch>
                <a:fillRect/>
            </a:stretch>
        </a:blipFill>'''

    def export_to_pptx_media(self, media_dir: Path) -> Dict[str, str]:
        """Export all EMF blobs to a PPTX media directory.

        Args:
            media_dir: Path to the media directory in PPTX

        Returns:
            Dictionary mapping relationship IDs to filenames

        Raises:
            EMFPackagingError: If export fails
        """
        try:
            media_dir.mkdir(parents=True, exist_ok=True)
            exported = {}

            for rel_id, filename in self.relationship_manager.list_relationships():
                emf_data = self.relationship_manager.get_emf_data(rel_id)
                if emf_data is None:
                    continue

                file_path = media_dir / filename
                file_path.write_bytes(emf_data)
                exported[rel_id] = filename

            return exported

        except Exception as e:
            raise EMFPackagingError(f"Failed to export EMF blobs to media directory: {e}")

    def get_relationship_xml(self) -> str:
        """Get relationship XML for all EMF blobs.

        Returns:
            XML string for relationships
        """
        return self.relationship_manager.generate_relationship_xml()

    def update_content_types(self, content_types_xml: str) -> str:
        """Update content types XML to include EMF extensions.

        Args:
            content_types_xml: Existing content types XML

        Returns:
            Updated content types XML
        """
        try:
            # Parse existing XML
            root = ET.fromstring(content_types_xml)

            # Check if EMF extension already exists
            emf_exists = False
            for default in root.findall('.//{http://schemas.openxmlformats.org/package/2006/content-types}Default'):
                if default.get('Extension') == 'emf':
                    emf_exists = True
                    break

            # Add EMF content type if not exists
            if not emf_exists:
                emf_default = ET.Element('Default')
                emf_default.set('Extension', 'emf')
                emf_default.set('ContentType', 'image/x-emf')
                root.append(emf_default)

            # Convert back to string with proper formatting
            rough_string = ET.tostring(root, encoding='unicode')
            reparsed = minidom.parseString(rough_string)
            return reparsed.toprettyxml(indent='  ').split('\n', 1)[1]  # Remove XML declaration

        except Exception as e:
            raise EMFPackagingError(f"Failed to update content types: {e}")


class EMFShapeGenerator:
    """Generates PowerPoint shapes with EMF fills."""

    def __init__(self, integrator: PPTXEMFIntegrator):
        """Initialize shape generator.

        Args:
            integrator: PPTX EMF integrator instance
        """
        self.integrator = integrator
        self.shape_id = 1

    def create_rectangle_with_pattern(self, x: int, y: int, width: int, height: int,
                                    pattern_name: str, tile_mode: str = 'tile') -> str:
        """Create a rectangle shape with pattern fill.

        Args:
            x: X coordinate in EMUs
            y: Y coordinate in EMUs
            width: Width in EMUs
            height: Height in EMUs
            pattern_name: Pattern name from tile library
            tile_mode: 'tile' or 'stretch' mode

        Returns:
            PowerPoint shape XML

        Raises:
            EMFPackagingError: If shape creation fails
        """
        try:
            fill_xml = self.integrator.add_pattern_fill(pattern_name, tile_mode)
            shape_id = self._get_next_shape_id()

            return f'''
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="{shape_id}" name="Rectangle {shape_id}"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="{x}" y="{y}"/>
                        <a:ext cx="{width}" cy="{height}"/>
                    </a:xfrm>
                    <a:prstGeom prst="rect">
                        <a:avLst/>
                    </a:prstGeom>
                    {fill_xml}
                </p:spPr>
            </p:sp>'''

        except Exception as e:
            raise EMFPackagingError(f"Failed to create rectangle with pattern '{pattern_name}': {e}")

    def create_ellipse_with_pattern(self, x: int, y: int, width: int, height: int,
                                  pattern_name: str, tile_mode: str = 'tile') -> str:
        """Create an ellipse shape with pattern fill.

        Args:
            x: X coordinate in EMUs
            y: Y coordinate in EMUs
            width: Width in EMUs
            height: Height in EMUs
            pattern_name: Pattern name from tile library
            tile_mode: 'tile' or 'stretch' mode

        Returns:
            PowerPoint shape XML

        Raises:
            EMFPackagingError: If shape creation fails
        """
        try:
            fill_xml = self.integrator.add_pattern_fill(pattern_name, tile_mode)
            shape_id = self._get_next_shape_id()

            return f'''
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="{shape_id}" name="Ellipse {shape_id}"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="{x}" y="{y}"/>
                        <a:ext cx="{width}" cy="{height}"/>
                    </a:xfrm>
                    <a:prstGeom prst="ellipse">
                        <a:avLst/>
                    </a:prstGeom>
                    {fill_xml}
                </p:spPr>
            </p:sp>'''

        except Exception as e:
            raise EMFPackagingError(f"Failed to create ellipse with pattern '{pattern_name}': {e}")

    def _get_next_shape_id(self) -> int:
        """Get next shape ID."""
        current_id = self.shape_id
        self.shape_id += 1
        return current_id


def create_emf_integrator() -> PPTXEMFIntegrator:
    """Factory function to create a new PPTX EMF integrator.

    Returns:
        PPTXEMFIntegrator instance
    """
    return PPTXEMFIntegrator()


def create_shape_generator(integrator: PPTXEMFIntegrator = None) -> EMFShapeGenerator:
    """Factory function to create a new EMF shape generator.

    Args:
        integrator: Optional EMF integrator (creates new one if None)

    Returns:
        EMFShapeGenerator instance
    """
    if integrator is None:
        integrator = create_emf_integrator()
    return EMFShapeGenerator(integrator)


# Utility functions for common operations

def create_pattern_rectangle_xml(x: int, y: int, width: int, height: int,
                                pattern_name: str, tile_mode: str = 'tile') -> Tuple[str, PPTXEMFIntegrator]:
    """Create XML for a rectangle with pattern fill.

    Args:
        x: X coordinate in EMUs
        y: Y coordinate in EMUs
        width: Width in EMUs
        height: Height in EMUs
        pattern_name: Pattern name from tile library
        tile_mode: 'tile' or 'stretch' mode

    Returns:
        Tuple of (shape XML, integrator instance)
    """
    integrator = create_emf_integrator()
    generator = create_shape_generator(integrator)

    shape_xml = generator.create_rectangle_with_pattern(
        x, y, width, height, pattern_name, tile_mode
    )

    return shape_xml, integrator


def extract_emf_blobs_from_pptx(pptx_path: Path) -> Dict[str, bytes]:
    """Extract all EMF blobs from an existing PPTX file.

    Args:
        pptx_path: Path to PPTX file

    Returns:
        Dictionary mapping filenames to EMF blob bytes

    Raises:
        EMFPackagingError: If extraction fails
    """
    try:
        emf_blobs = {}

        with zipfile.ZipFile(pptx_path, 'r') as pptx_zip:
            # Look for EMF files in media directory
            for file_info in pptx_zip.infolist():
                if file_info.filename.startswith('ppt/media/') and file_info.filename.endswith('.emf'):
                    filename = Path(file_info.filename).name
                    emf_data = pptx_zip.read(file_info.filename)
                    emf_blobs[filename] = emf_data

        return emf_blobs

    except Exception as e:
        raise EMFPackagingError(f"Failed to extract EMF blobs from PPTX: {e}")


def validate_emf_packaging(integrator: PPTXEMFIntegrator) -> List[str]:
    """Validate EMF packaging for common issues.

    Args:
        integrator: EMF integrator to validate

    Returns:
        List of validation warnings (empty if no issues)
    """
    warnings = []

    # Check for empty relationship manager
    relationships = integrator.relationship_manager.list_relationships()
    if not relationships:
        warnings.append("No EMF blobs registered in relationship manager")

    # Check for duplicate EMF data
    emf_hashes = {}
    for rel_id, filename in relationships:
        emf_data = integrator.relationship_manager.get_emf_data(rel_id)
        if emf_data is not None:
            data_hash = hashlib.md5(emf_data, usedforsecurity=False).hexdigest()
            if data_hash in emf_hashes:
                warnings.append(f"Duplicate EMF data detected: {filename} and {emf_hashes[data_hash]}")
            else:
                emf_hashes[data_hash] = filename

    # Check for valid EMF headers
    for rel_id, filename in relationships:
        emf_data = integrator.relationship_manager.get_emf_data(rel_id)
        if emf_data is not None and len(emf_data) >= 4:
            # Check for EMF signature
            if emf_data[:4] != b'\x01\x00\x00\x00':  # EMR_HEADER record type
                warnings.append(f"Invalid EMF header in {filename}")

    return warnings
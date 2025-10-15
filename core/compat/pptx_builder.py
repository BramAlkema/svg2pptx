#!/usr/bin/env python3
"""
PPTXBuilder - Direct PPTX File Creation

Creates PPTX files by manually building the ZIP structure
and injecting DrawingML shapes directly into slide XML.
"""

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..units import UnitConverter
else:
    try:
        from ..units import UnitConverter
    except ImportError:
        UnitConverter = None

from .pptx_manifest import PPTXManifestBuilder
from .pptx_media import MediaManager
from .pptx_slide import SlideBuilder, SlideDimensions


class PPTXBuilder:
    """Build PPTX files from scratch with direct XML manipulation."""

    def __init__(self, unit_converter: Optional['UnitConverter'] = None):
        self.unit_converter = unit_converter

        if self.unit_converter:
            width = self.unit_converter.to_emu('10in')
            height = self.unit_converter.to_emu('7.5in')
        else:
            width = 9_144_000  # 10 inches in EMUs
            height = 6_858_000  # 7.5 inches in EMUs

        self.slide_dimensions = SlideDimensions(width=width, height=height)
        self.slide_builder = SlideBuilder(self.slide_dimensions)
        self.media_manager = MediaManager()

        self._next_shape_id = 1000

    def create_minimal_pptx(self, drawingml_shapes: str, output_path: str):
        """Create a minimal PPTX file with DrawingML shapes."""

        # Create temporary directory for PPTX structure
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            self.media_manager.copy_to_package(temp_path)
            self._ensure_base_directories(temp_path)

            manifest = PPTXManifestBuilder(image_extensions=self.media_manager.image_extensions())
            manifest.write_doc_props(temp_path)
            manifest.write_manifest(temp_path)
            manifest.write_theme(temp_path)
            manifest.write_layout_and_master(temp_path)

            slide_path = temp_path / 'ppt' / 'slides' / 'slide1.xml'
            slide_path.write_text(self.slide_builder.render(drawingml_shapes), encoding='utf-8')

            self._write_slide_relationships(temp_path)

            self._zip_pptx_structure(temp_path, output_path)

    def _ensure_base_directories(self, base_path: Path) -> None:
        (base_path / 'ppt' / 'slides').mkdir(parents=True, exist_ok=True)
        (base_path / 'ppt' / '_rels').mkdir(parents=True, exist_ok=True)
        (base_path / 'ppt' / 'slides' / '_rels').mkdir(parents=True, exist_ok=True)

    def _write_slide_relationships(self, base_path: Path) -> None:
        rels_xml = self._create_slide_relationships()
        rels_path = base_path / 'ppt' / 'slides' / '_rels' / 'slide1.xml.rels'
        rels_path.write_text(rels_xml, encoding='utf-8')


    def add_image(self, image_path: str) -> str:
        """Add image to PPTX and return embed ID."""
        return self.media_manager.register_image(image_path)

    def _create_slide_relationships(self) -> str:
        """Create slide relationships XML including image relationships."""
        relationships = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
                        '    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>']

        # Add image relationships
        relationships.extend(self.media_manager.get_image_relationships())

        relationships.append('</Relationships>')
        return '\n'.join(relationships)

    def _next_id(self) -> int:
        """Generate next unique shape ID."""
        self._next_shape_id += 1
        return self._next_shape_id

    def add_picture(self, embed_id: str, x: str, y: str, width: str, height: str,
                    name: str = "Picture") -> str:
        """
        Return a <p:pic> DrawingML block that references an image relationship (embed_id).
        Coordinates and size support unit strings (e.g., '1in', '2.5cm', '100px').

        Args:
            embed_id: Relationship ID from add_image()
            x: X position with units (e.g., '1in', '2.54cm')
            y: Y position with units (e.g., '1in', '2.54cm')
            width: Width with units (e.g., '3in', '7.62cm')
            height: Height with units (e.g., '2in', '5.08cm')
            name: Display name for the picture

        Returns:
            DrawingML XML for the picture shape

        NOTE: You must have called add_image(path) beforehand to allocate the embed_id
        and to inject the slide relationship in slide1.xml.rels.
        """
        # Convert units to EMUs
        if self.unit_converter:
            x_emu = int(self.unit_converter.to_emu(x))
            y_emu = int(self.unit_converter.to_emu(y))
            w_emu = int(self.unit_converter.to_emu(width))
            h_emu = int(self.unit_converter.to_emu(height))
        else:
            # Fallback: assume values are already in EMUs if no converter
            try:
                x_emu = int(float(x))
                y_emu = int(float(y))
                w_emu = int(float(width))
                h_emu = int(float(height))
            except ValueError:
                raise ValueError(
                    f"No unit converter available and values are not numeric: "
                    f"x='{x}', y='{y}', width='{width}', height='{height}'. "
                    f"Either provide a UnitConverter or use numeric EMU values.",
                )

        # PowerPoint wants a unique shape id per picture
        shape_id = self._next_id()

        return f'''<p:pic xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                         xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                         xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:nvPicPr>
    <p:cNvPr id="{shape_id}" name="{name} {shape_id}"/>
    <p:cNvPicPr>
      <a:picLocks noChangeAspect="1"/>
    </p:cNvPicPr>
    <p:nvPr/>
  </p:nvPicPr>
  <p:blipFill>
    <a:blip r:embed="{embed_id}"/>
    <a:stretch><a:fillRect/></a:stretch>
  </a:blipFill>
  <p:spPr>
    <a:xfrm>
      <a:off x="{x_emu}" y="{y_emu}"/>
      <a:ext cx="{w_emu}" cy="{h_emu}"/>
    </a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
</p:pic>'''

    def _zip_pptx_structure(self, temp_path: Path, output_path: str):
        """Create ZIP archive from PPTX directory structure."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(temp_path))
                    zipf.write(file_path, arcname)


# Smoke test and usage examples
if __name__ == "__main__":
    # Test 1: Rectangle only (no repair dialogs, visible shape)
    rect = """
    <p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
          xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
      <p:nvSpPr>
        <p:cNvPr id="1001" name="Rect 1001"/>
        <p:cNvSpPr/>
        <p:nvPr/>
      </p:nvSpPr>
      <p:spPr>
        <a:xfrm>
          <a:off x="1143000" y="1143000"/>
          <a:ext cx="2286000" cy="1143000"/>
        </a:xfrm>
        <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        <a:solidFill><a:srgbClr val="24394B"/></a:solidFill>
        <a:ln><a:noFill/></a:ln>
      </p:spPr>
      <p:txBody>
        <a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p>
      </p:txBody>
    </p:sp>
    """.strip()

    out = "minimal_demo.pptx"
    PPTXBuilder().create_minimal_pptx(rect, out)
    print(f"wrote {out} - rectangle at ~1.25\" from top-left")

    # Test 2: Picture example with units system (requires an image file)
    # Uncomment if you have an image to test:
    """
    from .services.conversion_services import ConversionServices

    # Create services with unit converter
    services = ConversionServices.create_default()
    builder = services.pptx_builder

    # 1) Register an image file → get rId (also wires slide1.xml.rels)
    # rid = builder.add_image("logo.png")  # Replace with actual image path

    # 2) Create picture shape XML (position 1" x 1", size 3" x 2") - now with unit strings!
    # pic = builder.add_picture(rid, "1in", "1in", "3in", "2in")

    # 3) Build PPTX with this shape
    # builder.create_minimal_pptx(pic, "picture_demo.pptx")
    # print("wrote picture_demo.pptx - image at 1\" x 1\" position using units!")
    """

#!/usr/bin/env python3
"""
Package Writer

Handles final PPTX package assembly from slide XML and relationships.
"""

import io
import logging
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional

from .embedder import EmbedderResult

logger = logging.getLogger(__name__)


class PackageError(Exception):
    """Exception raised when package writing fails"""
    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message)
        self.cause = cause


@dataclass
class PackageManifest:
    """Manifest of PPTX package contents"""
    slides: list[str]
    relationships: list[dict[str, Any]]
    media_files: list[dict[str, Any]]
    content_types: list[dict[str, str]]

    # Package metadata
    title: str | None = None
    author: str | None = None
    created_date: str | None = None


class PackageWriter:
    """
    Writes complete PPTX packages from embedded slide content.

    Handles ZIP assembly, content types, relationships, and media files
    to create valid PowerPoint presentations.

    Args:
        enable_debug: Enable debug data collection for tracing (default: False)

    Example with tracing:
        >>> writer = PackageWriter(enable_debug=True)
        >>> result = writer.write_package(embedder_results, "output.pptx")
        >>> print(result['debug_data']['package_creation_ms'])
        5.2
    """

    def __init__(self, enable_debug: bool = False):
        """
        Initialize package writer.

        Args:
            enable_debug: Enable debug data collection for E2E tracing
        """
        self.logger = logging.getLogger(__name__)
        self.enable_debug = enable_debug
        self._debug_data = {} if enable_debug else None

        # Standard PPTX content types
        self._content_types = {
            'rels': 'application/vnd.openxmlformats-package.relationships+xml',
            'xml': 'application/xml',
            'slide': 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml',
            'presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml',
            'layout': 'application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml',
            'master': 'application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml',
            'theme': 'application/vnd.openxmlformats-officedocument.theme+xml',
            'image_png': 'image/png',
            'image_jpeg': 'image/jpeg',
            'image_emf': 'application/emf',
        }

    def write_package(self, embedder_results: list[EmbedderResult],
                     output_path: str, manifest: PackageManifest = None) -> dict[str, Any]:
        """
        Write complete PPTX package from embedder results.

        Args:
            embedder_results: List of embedded slide results
            output_path: Path to write PPTX file
            manifest: Optional package manifest

        Returns:
            Dictionary with package statistics and metadata.
            When enable_debug=True, includes 'debug_data' with:
                - package_creation_ms: Time to create ZIP in memory
                - file_write_ms: Time to write file to disk
                - package_size_bytes: Final package size
                - compression_ratio: Compression ratio achieved
                - zip_structure: Counts of ZIP components

        Raises:
            PackageError: If package writing fails
        """
        start_time = time.perf_counter()

        try:
            # Apply default manifest
            if manifest is None:
                manifest = self._create_default_manifest(embedder_results)

            # Track package creation timing
            if self.enable_debug:
                self._debug_data['packaging_start'] = time.perf_counter()

            # Create package in memory first
            package_data = self._create_package_data(embedder_results, manifest)

            if self.enable_debug:
                package_creation_time = (time.perf_counter() - self._debug_data['packaging_start']) * 1000
                self._debug_data['package_creation_ms'] = package_creation_time
                self._debug_data['package_size_bytes'] = len(package_data)

                # Track ZIP structure
                self._debug_data['zip_structure'] = {
                    'slides': len(embedder_results),
                    'relationships': len(manifest.relationships),
                    'media_files': len(manifest.media_files),
                    'content_types': len(manifest.content_types),
                }

            # Track file write timing
            if self.enable_debug:
                file_write_start = time.perf_counter()

            # Write to output file
            self._write_package_file(package_data, output_path)

            if self.enable_debug:
                file_write_time = (time.perf_counter() - file_write_start) * 1000
                self._debug_data['file_write_ms'] = file_write_time

            # Calculate statistics
            processing_time = (time.perf_counter() - start_time) * 1000
            package_size = len(package_data)
            compression_ratio = self._estimate_compression_ratio(embedder_results, package_size)

            if self.enable_debug:
                self._debug_data['compression_ratio'] = compression_ratio
                self._debug_data['total_time_ms'] = processing_time

            result = {
                'output_path': output_path,
                'package_size_bytes': package_size,
                'slide_count': len(embedder_results),
                'processing_time_ms': processing_time,
                'media_files': len(manifest.media_files),
                'relationships': len(manifest.relationships),
                'compression_ratio': compression_ratio,
            }

            # Include debug data when enabled
            if self.enable_debug:
                result['debug_data'] = self._debug_data.copy()

            return result

        except Exception as e:
            raise PackageError(f"Failed to write PPTX package: {e}", cause=e)

    def write_package_stream(self, embedder_results: list[EmbedderResult],
                           stream: BinaryIO, manifest: PackageManifest = None) -> dict[str, Any]:
        """
        Write PPTX package to stream.

        Args:
            embedder_results: List of embedded slide results
            stream: Binary stream to write to
            manifest: Optional package manifest

        Returns:
            Dictionary with package statistics
        """
        try:
            # Apply default manifest
            if manifest is None:
                manifest = self._create_default_manifest(embedder_results)

            # Create package data
            package_data = self._create_package_data(embedder_results, manifest)

            # Write to stream
            stream.write(package_data)

            return {
                'package_size_bytes': len(package_data),
                'slide_count': len(embedder_results),
                'media_files': len(manifest.media_files),
                'relationships': len(manifest.relationships),
            }

        except Exception as e:
            raise PackageError(f"Failed to write PPTX to stream: {e}", cause=e)

    def _create_package_data(self, embedder_results: list[EmbedderResult],
                           manifest: PackageManifest) -> bytes:
        """Create complete PPTX package data in memory"""
        try:
            # Use BytesIO to build package in memory
            package_buffer = io.BytesIO()

            with zipfile.ZipFile(package_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Write core structure files
                self._write_core_structure(zip_file)

                # Write presentation.xml
                presentation_xml = self._generate_presentation_xml(len(embedder_results))
                zip_file.writestr('ppt/presentation.xml', presentation_xml)

                # Write slides
                for i, result in enumerate(embedder_results, 1):
                    zip_file.writestr(f'ppt/slides/slide{i}.xml', result.slide_xml)

                    # Write slide relationships
                    slide_rels = self._generate_slide_relationships(result.relationship_data)
                    zip_file.writestr(f'ppt/slides/_rels/slide{i}.xml.rels', slide_rels)

                # Write media files
                self._write_media_files(zip_file, manifest.media_files)

                # Write content types
                content_types_xml = self._generate_content_types(manifest)
                zip_file.writestr('[Content_Types].xml', content_types_xml)

                # Write main relationships
                main_rels = self._generate_main_relationships()
                zip_file.writestr('_rels/.rels', main_rels)

                # Write presentation relationships
                pres_rels = self._generate_presentation_relationships(len(embedder_results))
                zip_file.writestr('ppt/_rels/presentation.xml.rels', pres_rels)

            return package_buffer.getvalue()

        except Exception as e:
            raise PackageError(f"Failed to create package data: {e}", cause=e)

    def _write_package_file(self, package_data: bytes, output_path: str) -> None:
        """Write package data to file"""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'wb') as f:
                f.write(package_data)

        except Exception as e:
            raise PackageError(f"Failed to write package file: {e}", cause=e)

    def _create_default_manifest(self, embedder_results: list[EmbedderResult]) -> PackageManifest:
        """Create default package manifest from embedder results"""
        all_relationships = []
        all_media_files = []

        for result in embedder_results:
            all_relationships.extend(result.relationship_data)
            all_media_files.extend(result.media_files)

        return PackageManifest(
            slides=[f'slide{i+1}.xml' for i in range(len(embedder_results))],
            relationships=all_relationships,
            media_files=all_media_files,
            content_types=self._generate_content_type_list(embedder_results),
            title="SVG2PPTX Generated Presentation",
            author="SVG2PPTX Clean Slate Architecture",
        )

    def _write_core_structure(self, zip_file: zipfile.ZipFile) -> None:
        """Write core PPTX structure files"""
        # Create directory structure
        zip_file.writestr('ppt/', '')
        zip_file.writestr('ppt/slides/', '')
        zip_file.writestr('ppt/slides/_rels/', '')
        zip_file.writestr('ppt/_rels/', '')
        zip_file.writestr('ppt/slideLayouts/', '')
        zip_file.writestr('ppt/slideMasters/', '')
        zip_file.writestr('ppt/theme/', '')
        zip_file.writestr('ppt/media/', '')
        zip_file.writestr('_rels/', '')

        # Copy theme, master, and layouts from presentationml templates
        from pathlib import Path
        template_dir = Path(__file__).parent.parent.parent / 'archive' / 'presentationml'

        # Copy theme
        theme_file = template_dir / 'theme.xml'
        if theme_file.exists():
            zip_file.writestr('ppt/theme/theme1.xml', theme_file.read_text())
        else:
            theme_xml = self._generate_theme_xml()
            zip_file.writestr('ppt/theme/theme1.xml', theme_xml)

        # Copy slide master
        master_file = template_dir / 'slideMaster.xml'
        if master_file.exists():
            zip_file.writestr('ppt/slideMasters/slideMaster1.xml', master_file.read_text())
        else:
            master_xml = self._generate_slide_master_xml()
            zip_file.writestr('ppt/slideMasters/slideMaster1.xml', master_xml)

        # Copy all slide layouts
        layouts_dir = template_dir / 'slideLayouts'
        if layouts_dir.exists():
            for layout_file in sorted(layouts_dir.glob('slideLayout*.xml')):
                zip_file.writestr(f'ppt/slideLayouts/{layout_file.name}', layout_file.read_text())
        else:
            layout_xml = self._generate_slide_layout_xml()
            zip_file.writestr('ppt/slideLayouts/slideLayout1.xml', layout_xml)

    def _generate_presentation_xml(self, slide_count: int) -> str:
        """Generate presentation.xml"""
        slide_ids = []
        for i in range(1, slide_count + 1):
            slide_ids.append(f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>')

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:sldMasterIdLst>
        <p:sldMasterId id="2147483648" r:id="rId1"/>
    </p:sldMasterIdLst>
    <p:sldIdLst>
        {chr(10).join(slide_ids)}
    </p:sldIdLst>
    <p:sldSz cx="9144000" cy="6858000"/>
    <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''

    def _generate_slide_relationships(self, relationship_data: list[dict[str, Any]]) -> str:
        """Generate slide relationship XML"""
        if not relationship_data:
            return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>'''

        relationships = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>']

        for i, rel in enumerate(relationship_data, 2):
            relationships.append(f'<Relationship Id="rId{i}" Type="{rel["type"]}" Target="{rel["target"]}"/>')

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    {chr(10).join(relationships)}
</Relationships>'''

    def _write_media_files(self, zip_file: zipfile.ZipFile, media_files: list[dict[str, Any]]) -> None:
        """Write media files to package"""
        for media in media_files:
            filename = media['filename']
            data = media.get('data', b'')

            if data or not media.get('requires_rendering', False):
                zip_file.writestr(f'ppt/media/{filename}', data)

    def _generate_content_types(self, manifest: PackageManifest) -> str:
        """Generate [Content_Types].xml"""
        defaults = [
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
            '<Default Extension="xml" ContentType="application/xml"/>',
            '<Default Extension="png" ContentType="image/png"/>',
            '<Default Extension="jpeg" ContentType="image/jpeg"/>',
            '<Default Extension="emf" ContentType="application/emf"/>',
        ]

        overrides = [
            '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
            '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
            '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
            '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
        ]

        # Add slide overrides
        for i, slide in enumerate(manifest.slides, 1):
            overrides.append(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    {chr(10).join(defaults)}
    {chr(10).join(overrides)}
</Types>'''

    def _generate_main_relationships(self) -> str:
        """Generate main _rels/.rels"""
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>'''

    def _generate_presentation_relationships(self, slide_count: int) -> str:
        """Generate presentation relationships with correct rId mapping"""
        relationships = [
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>',
        ]

        # Add slides starting at rId2 (presentation.xml expects rId2 for first slide)
        for i in range(1, slide_count + 1):
            relationships.append(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>')

        # Theme comes after slides
        relationships.append('<Relationship Id="rId' + str(slide_count + 2) + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>')

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    {chr(10).join(relationships)}
</Relationships>'''

    def _generate_theme_xml(self) -> str:
        """Generate minimal theme XML"""
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">
    <a:themeElements>
        <a:clrScheme name="Office">
            <a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
            <a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
            <a:dk2><a:srgbClr val="1F497D"/></a:dk2>
            <a:lt2><a:srgbClr val="EEECE1"/></a:lt2>
            <a:accent1><a:srgbClr val="4F81BD"/></a:accent1>
            <a:accent2><a:srgbClr val="F79646"/></a:accent2>
            <a:accent3><a:srgbClr val="9BBB59"/></a:accent3>
            <a:accent4><a:srgbClr val="8064A2"/></a:accent4>
            <a:accent5><a:srgbClr val="4BACC6"/></a:accent5>
            <a:accent6><a:srgbClr val="F366CC"/></a:accent6>
            <a:hlink><a:srgbClr val="0000FF"/></a:hlink>
            <a:folHlink><a:srgbClr val="800080"/></a:folHlink>
        </a:clrScheme>
        <a:fontScheme name="Office">
            <a:majorFont>
                <a:latin typeface="Calibri Light"/>
            </a:majorFont>
            <a:minorFont>
                <a:latin typeface="Calibri"/>
            </a:minorFont>
        </a:fontScheme>
        <a:fmtScheme name="Office">
            <a:fillStyleLst>
                <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
            </a:fillStyleLst>
            <a:lnStyleLst>
                <a:ln w="9525" cap="flat" cmpd="sng" algn="ctr">
                    <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                </a:ln>
            </a:lnStyleLst>
            <a:effectStyleLst>
                <a:effectStyle><a:effectLst/></a:effectStyle>
            </a:effectStyleLst>
            <a:bgFillStyleLst>
                <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
            </a:bgFillStyleLst>
        </a:fmtScheme>
    </a:themeElements>
</a:theme>'''

    def _generate_slide_master_xml(self) -> str:
        """Generate minimal slide master XML"""
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr/>
        </p:spTree>
    </p:cSld>
    <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2"
             accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6"
             hlink="hlink" folHlink="folHlink"/>
    <p:sldLayoutIdLst>
        <p:sldLayoutId id="2147483649" r:id="rId1"/>
    </p:sldLayoutIdLst>
</p:sldMaster>'''

    def _generate_slide_layout_xml(self) -> str:
        """Generate minimal slide layout XML"""
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
             type="blank" preserve="1">
    <p:cSld name="Blank">
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr/>
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sldLayout>'''

    def _generate_content_type_list(self, embedder_results: list[EmbedderResult]) -> list[dict[str, str]]:
        """Generate content type list from embedder results"""
        content_types = []

        for result in embedder_results:
            for media in result.media_files:
                content_type = media.get('content_type', 'application/octet-stream')
                filename = media['filename']
                extension = Path(filename).suffix.lstrip('.')

                content_types.append({
                    'extension': extension,
                    'content_type': content_type,
                })

        return content_types

    def _estimate_compression_ratio(self, embedder_results: list[EmbedderResult],
                                  package_size: int) -> float:
        """Estimate compression ratio"""
        try:
            uncompressed_size = sum(result.total_size_bytes for result in embedder_results)
            if uncompressed_size == 0:
                return 1.0

            return package_size / uncompressed_size
        except (ZeroDivisionError, TypeError):
            return 1.0


def create_package_writer(enable_debug: bool = False) -> PackageWriter:
    """
    Create PackageWriter instance.

    Args:
        enable_debug: Enable debug data collection for E2E tracing

    Returns:
        Configured PackageWriter
    """
    return PackageWriter(enable_debug=enable_debug)
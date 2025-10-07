#!/usr/bin/env python3
"""
Coordinate Extraction Script
=============================

Extracts coordinate metadata from baseline PPTX files for regression comparison.

This script unzips PPTX files and extracts DrawingML coordinates from slide XML
to create a comparable metadata snapshot.

Usage:
    python tests/baseline/extract_coordinates.py --phase phase0

Output:
    - tests/baseline/outputs/{phase}/metadata/coordinates.json
"""

import os
import sys
import json
import zipfile
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from lxml import etree as ET


# DrawingML namespaces
NAMESPACES = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
}


def extract_shape_coordinates(shape_elem: ET.Element) -> Dict:
    """
    Extract coordinate data from a shape element.

    Returns dict with position, size, and transform data.
    """
    coordinates = {}

    # Extract position and size (xfrm element)
    xfrm = shape_elem.find('.//a:xfrm', NAMESPACES)
    if xfrm is not None:
        # Offset (position)
        off = xfrm.find('a:off', NAMESPACES)
        if off is not None:
            coordinates['x'] = int(off.get('x', 0))
            coordinates['y'] = int(off.get('y', 0))

        # Extents (size)
        ext = xfrm.find('a:ext', NAMESPACES)
        if ext is not None:
            coordinates['cx'] = int(ext.get('cx', 0))
            coordinates['cy'] = int(ext.get('cy', 0))

        # Rotation
        rot = xfrm.get('rot')
        if rot is not None:
            coordinates['rot'] = int(rot)

        # Flip
        flipH = xfrm.get('flipH')
        if flipH:
            coordinates['flipH'] = flipH == 'true' or flipH == '1'

        flipV = xfrm.get('flipV')
        if flipV:
            coordinates['flipV'] = flipV == 'true' or flipV == '1'

    return coordinates


def extract_path_coordinates(path_elem: ET.Element) -> List[Dict]:
    """
    Extract coordinate data from path commands.

    Returns list of path command dicts.
    """
    commands = []

    # Find all path commands
    for child in path_elem:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        command = {'type': tag}

        # Extract coordinate attributes
        for attr, value in child.attrib.items():
            # Convert coordinate values to int
            if attr in ('x', 'y', 'w', 'h', 'hR', 'wR', 'stAng', 'swAng'):
                try:
                    command[attr] = int(value)
                except ValueError:
                    command[attr] = value
            else:
                command[attr] = value

        commands.append(command)

    return commands


def extract_slide_metadata(slide_xml: str) -> Dict:
    """
    Extract all coordinate metadata from a slide XML file.

    Args:
        slide_xml: Raw XML content of slide

    Returns:
        Dict with shapes and their coordinate data
    """
    root = ET.fromstring(slide_xml.encode('utf-8'))

    metadata = {
        'shapes': [],
        'total_shapes': 0,
    }

    # Find all shapes
    shapes = root.findall('.//p:sp', NAMESPACES)

    for i, shape in enumerate(shapes):
        shape_data = {
            'index': i,
            'type': 'shape',
            'coordinates': extract_shape_coordinates(shape),
        }

        # Check for path geometry
        custGeom = shape.find('.//a:custGeom', NAMESPACES)
        if custGeom is not None:
            path_list = custGeom.find('.//a:pathLst', NAMESPACES)
            if path_list is not None:
                paths = []
                for path in path_list.findall('a:path', NAMESPACES):
                    path_data = {
                        'w': int(path.get('w', 0)),
                        'h': int(path.get('h', 0)),
                        'commands': extract_path_coordinates(path),
                    }
                    paths.append(path_data)

                shape_data['paths'] = paths

        metadata['shapes'].append(shape_data)

    metadata['total_shapes'] = len(shapes)

    return metadata


def extract_pptx_coordinates(pptx_path: Path) -> Dict:
    """
    Extract coordinate metadata from a PPTX file.

    Args:
        pptx_path: Path to PPTX file

    Returns:
        Dict with slides and coordinate metadata
    """
    metadata = {
        'pptx_path': str(pptx_path.relative_to(project_root)),
        'slides': [],
        'total_slides': 0,
    }

    try:
        with zipfile.ZipFile(pptx_path, 'r') as pptx_zip:
            # Find all slide XML files
            slide_files = [
                name for name in pptx_zip.namelist()
                if name.startswith('ppt/slides/slide') and name.endswith('.xml')
            ]

            slide_files.sort()  # Ensure consistent ordering

            for slide_file in slide_files:
                slide_xml = pptx_zip.read(slide_file).decode('utf-8')
                slide_metadata = extract_slide_metadata(slide_xml)

                slide_metadata['slide_file'] = slide_file

                metadata['slides'].append(slide_metadata)

            metadata['total_slides'] = len(slide_files)

    except Exception as e:
        metadata['error'] = str(e)

    return metadata


def extract_all_coordinates(phase: str = "phase0") -> Dict:
    """
    Extract coordinates from all baseline PPTX files.

    Args:
        phase: Phase identifier (e.g., "phase0", "phase1")

    Returns:
        Complete coordinates metadata dict
    """
    print(f"\n{'='*60}")
    print(f"Extracting Baseline Coordinates - {phase.upper()}")
    print(f"{'='*60}\n")

    base_dir = project_root / "tests" / "baseline" / "outputs" / phase

    if not base_dir.exists():
        print(f"❌ Phase directory not found: {base_dir}")
        return {}

    # Load manifest to get list of PPTX files
    manifest_path = base_dir / "metadata" / "manifest.json"

    if not manifest_path.exists():
        print(f"⚠️  Manifest not found, scanning for PPTX files...")
        # Scan for PPTX files manually
        pptx_files = list(base_dir.rglob("*.pptx"))
    else:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        # Get PPTX files from manifest
        pptx_files = []
        for category, items in manifest.get('categories', {}).items():
            for item in items:
                if item.get('success'):
                    pptx_path = project_root / item['pptx_path']
                    if pptx_path.exists():
                        pptx_files.append(pptx_path)

    print(f"Found {len(pptx_files)} PPTX files\n")

    # Extract coordinates from each PPTX
    coordinates_data = {
        'phase': phase,
        'timestamp': datetime.now().isoformat(),
        'files': [],
        'summary': {
            'total_files': len(pptx_files),
            'total_slides': 0,
            'total_shapes': 0,
        }
    }

    for pptx_path in pptx_files:
        print(f"Extracting: {pptx_path.name}... ", end='')

        metadata = extract_pptx_coordinates(pptx_path)

        if 'error' in metadata:
            print(f"❌ {metadata['error']}")
        else:
            total_shapes = sum(slide['total_shapes'] for slide in metadata['slides'])
            print(f"✅ {metadata['total_slides']} slides, {total_shapes} shapes")

            coordinates_data['summary']['total_slides'] += metadata['total_slides']
            coordinates_data['summary']['total_shapes'] += total_shapes

        coordinates_data['files'].append(metadata)

    # Save coordinates metadata
    output_path = base_dir / "metadata" / "coordinates.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(coordinates_data, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Coordinate Extraction Complete")
    print(f"{'='*60}")
    print(f"Total Files:  {coordinates_data['summary']['total_files']}")
    print(f"Total Slides: {coordinates_data['summary']['total_slides']}")
    print(f"Total Shapes: {coordinates_data['summary']['total_shapes']}")
    print(f"\nCoordinates saved: {output_path}")
    print(f"{'='*60}\n")

    return coordinates_data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract coordinates from baseline PPTX files"
    )
    parser.add_argument(
        "--phase",
        default="phase0",
        help="Phase identifier (default: phase0)"
    )

    args = parser.parse_args()

    try:
        coordinates = extract_all_coordinates(phase=args.phase)

        if not coordinates:
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

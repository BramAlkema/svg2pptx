#!/usr/bin/env python3
"""
Baseline Generation Script
==========================

Generates baseline PPTX files from test SVGs for regression testing during
fractional EMU + baked transform implementation.

Usage:
    python tests/baseline/generate_baseline.py

Output:
    - tests/baseline/outputs/phase0/{category}/*.pptx - Baseline PPTX files
    - tests/baseline/outputs/phase0/metadata/manifest.json - Test manifest
"""

import os
import sys
from pathlib import Path
from typing import Dict, List
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.pipeline.converter import CleanSlateConverter
from core.pipeline.config import PipelineConfig


# Baseline test suite (24 SVGs across 7 categories)
BASELINE_TESTS = {
    "shapes": [
        "tests/data/real_world_svgs/basic_rectangle.svg",
        "tests/data/real_world_svgs/basic_circle.svg",
        "tests/data/real_world_svgs/basic_ellipse.svg",
        "tests/data/real_world_svgs/polygon_simple.svg",
        "tests/data/real_world_svgs/polyline_simple.svg",
        "tests/data/real_world_svgs/line_simple.svg",
    ],
    "paths": [
        "tests/data/real_world_svgs/bezier_curves.svg",
        "tests/data/real_world_svgs/arc_segments.svg",
        "tests/data/real_world_svgs/path_mixed_commands.svg",
        "tests/data/real_world_svgs/multiple_paths.svg",
    ],
    "transforms": [
        "tests/data/real_world_svgs/complex_transforms.svg",
        "tests/data/real_world_svgs/nested_groups.svg",
        "tests/data/real_world_svgs/transform_various.svg",
    ],
    "text": [
        "tests/data/real_world_svgs/text_simple.svg",
        "tests/data/real_world_svgs/text_styled.svg",
    ],
    "gradients": [
        "tests/data/real_world_svgs/linear_gradient.svg",
        "tests/data/real_world_svgs/radial_gradient.svg",
    ],
    "filters": [
        "tests/data/real_world_svgs/filter_blur.svg",
        "tests/data/real_world_svgs/filter_drop_shadow.svg",
    ],
    "edge_cases": [
        "tests/data/real_world_svgs/extreme_coordinates.svg",
        "tests/data/real_world_svgs/zero_dimensions.svg",
        "tests/data/real_world_svgs/many_elements.svg",
        "tests/data/real_world_svgs/tiny_values.svg",
        "tests/data/real_world_svgs/huge_values.svg",
    ],
}


def ensure_output_dirs(phase: str = "phase0") -> Dict[str, Path]:
    """Create output directory structure."""
    base_dir = project_root / "tests" / "baseline" / "outputs" / phase

    dirs = {
        "base": base_dir,
        "metadata": base_dir / "metadata",
    }

    # Add category directories
    for category in BASELINE_TESTS.keys():
        dirs[category] = base_dir / category

    # Create all directories
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    return dirs


def find_existing_svgs() -> Dict[str, List[str]]:
    """
    Find which baseline SVGs actually exist in the codebase.

    Returns categorized dict with only existing files.
    """
    existing = {}

    for category, svg_list in BASELINE_TESTS.items():
        found_svgs = []
        for svg_path in svg_list:
            full_path = project_root / svg_path
            if full_path.exists():
                found_svgs.append(svg_path)
            else:
                print(f"⚠️  Missing: {svg_path}")

        if found_svgs:
            existing[category] = found_svgs

    return existing


def generate_baseline_pptx(svg_path: str, output_path: Path) -> Dict:
    """
    Convert SVG to PPTX and return metadata.

    Args:
        svg_path: Relative path to SVG file
        output_path: Where to save PPTX

    Returns:
        Metadata dict with conversion info
    """
    full_svg_path = project_root / svg_path

    try:
        # Create converter
        converter = CleanSlateConverter(PipelineConfig())

        # Convert SVG file to PPTX
        result = converter.convert_file(str(full_svg_path), str(output_path))

        # Read SVG for size
        with open(full_svg_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()

        # Extract metadata
        metadata = {
            "svg_path": svg_path,
            "pptx_path": str(output_path.relative_to(project_root)),
            "svg_size_bytes": len(svg_content),
            "pptx_size_bytes": len(result.output_data),
            "conversion_time_ms": result.total_time_ms,
            "element_count": result.elements_processed,
            "success": True,
            "timestamp": datetime.now().isoformat(),
        }

        print(f"✅ Generated: {output_path.name}")
        return metadata

    except Exception as e:
        print(f"❌ Failed: {svg_path} - {str(e)}")
        return {
            "svg_path": svg_path,
            "pptx_path": str(output_path.relative_to(project_root)),
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def generate_all_baselines(phase: str = "phase0") -> Dict:
    """
    Generate baseline PPTX files for all existing test SVGs.

    Returns:
        Manifest dict with all metadata
    """
    print(f"\n{'='*60}")
    print(f"Generating Baseline Test Suite - {phase.upper()}")
    print(f"{'='*60}\n")

    # Setup output directories
    dirs = ensure_output_dirs(phase)
    print(f"Output directory: {dirs['base']}\n")

    # Find existing SVGs
    existing_svgs = find_existing_svgs()

    if not existing_svgs:
        print("❌ No test SVGs found!")
        return {}

    # Generate baselines
    manifest = {
        "phase": phase,
        "timestamp": datetime.now().isoformat(),
        "categories": {},
        "summary": {
            "total_svgs": 0,
            "successful": 0,
            "failed": 0,
        }
    }

    for category, svg_list in existing_svgs.items():
        print(f"\n--- Category: {category} ({len(svg_list)} SVGs) ---")

        category_metadata = []

        for svg_path in svg_list:
            # Generate output filename
            svg_name = Path(svg_path).stem
            output_path = dirs[category] / f"{svg_name}.pptx"

            # Convert and collect metadata
            metadata = generate_baseline_pptx(svg_path, output_path)
            category_metadata.append(metadata)

            # Update summary
            manifest["summary"]["total_svgs"] += 1
            if metadata.get("success"):
                manifest["summary"]["successful"] += 1
            else:
                manifest["summary"]["failed"] += 1

        manifest["categories"][category] = category_metadata

    # Save manifest
    manifest_path = dirs["metadata"] / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Baseline Generation Complete")
    print(f"{'='*60}")
    print(f"Total SVGs:   {manifest['summary']['total_svgs']}")
    print(f"Successful:   {manifest['summary']['successful']}")
    print(f"Failed:       {manifest['summary']['failed']}")
    print(f"\nManifest saved: {manifest_path}")
    print(f"{'='*60}\n")

    return manifest


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate baseline PPTX files for regression testing"
    )
    parser.add_argument(
        "--phase",
        default="phase0",
        help="Phase identifier (default: phase0)"
    )

    args = parser.parse_args()

    try:
        manifest = generate_all_baselines(phase=args.phase)

        if manifest["summary"]["failed"] > 0:
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

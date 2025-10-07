#!/usr/bin/env python3
"""
Baseline Comparison Script
===========================

Compares coordinates from different phases against baseline to detect changes.

This script performs phase-specific comparisons:
- Phase 1: Should match Phase 0 exactly (infrastructure only)
- Phase 2: Transform tests expected to differ (baked transforms)
- Phase 3: Minor precision differences expected (<0.01 EMU)
- Phase 4: Should match Phase 3 (integration complete)

Usage:
    python tests/baseline/compare_with_baseline.py --baseline phase0 --compare phase1

Output:
    - Comparison report to console
    - tests/baseline/outputs/comparisons/phase0_vs_phase1.json
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class CoordinateDiff:
    """Represents a coordinate difference between phases."""
    file_name: str
    slide_index: int
    shape_index: int
    coordinate: str
    baseline_value: Any
    compare_value: Any
    delta: float = 0.0
    delta_percent: float = 0.0

    def __str__(self):
        if self.delta != 0:
            return (
                f"{self.file_name} | Slide {self.slide_index} | Shape {self.shape_index} | "
                f"{self.coordinate}: {self.baseline_value} → {self.compare_value} "
                f"(Δ {self.delta:+.2f}, {self.delta_percent:+.4f}%)"
            )
        else:
            return (
                f"{self.file_name} | Slide {self.slide_index} | Shape {self.shape_index} | "
                f"{self.coordinate}: {self.baseline_value} → {self.compare_value}"
            )


class BaselineComparator:
    """Compares coordinate metadata between phases."""

    # Tolerance levels (in EMU)
    TOLERANCE_EXACT = 0  # Phase 1 vs Phase 0
    TOLERANCE_PRECISION = 1  # Phase 3 vs Phase 0 (sub-EMU rounding)
    TOLERANCE_INTEGRATION = 1  # Phase 4 vs Phase 3

    # Categories where transform differences are expected in Phase 2
    TRANSFORM_CATEGORIES = {'transforms', 'paths', 'shapes'}

    def __init__(self, baseline_phase: str, compare_phase: str):
        self.baseline_phase = baseline_phase
        self.compare_phase = compare_phase
        self.differences: List[CoordinateDiff] = []

    def load_coordinates(self, phase: str) -> Dict:
        """Load coordinates metadata for a phase."""
        coords_path = (
            project_root / "tests" / "baseline" / "outputs" / phase /
            "metadata" / "coordinates.json"
        )

        if not coords_path.exists():
            raise FileNotFoundError(f"Coordinates not found: {coords_path}")

        with open(coords_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def compare_coordinates(
        self,
        baseline_coord: Dict,
        compare_coord: Dict,
        tolerance: float = 0
    ) -> List[CoordinateDiff]:
        """
        Compare two coordinate dicts and return differences.

        Args:
            baseline_coord: Baseline coordinate dict
            compare_coord: Comparison coordinate dict
            tolerance: Tolerance in EMU for floating point comparison

        Returns:
            List of CoordinateDiff objects
        """
        diffs = []

        # Compare each coordinate field
        for key in ['x', 'y', 'cx', 'cy', 'rot']:
            baseline_val = baseline_coord.get(key)
            compare_val = compare_coord.get(key)

            if baseline_val is None and compare_val is None:
                continue

            if baseline_val is None or compare_val is None:
                # One value missing
                diff = CoordinateDiff(
                    file_name='',
                    slide_index=0,
                    shape_index=0,
                    coordinate=key,
                    baseline_value=baseline_val,
                    compare_value=compare_val,
                )
                diffs.append(diff)
                continue

            # Calculate delta
            delta = abs(compare_val - baseline_val)

            if delta > tolerance:
                delta_percent = (delta / abs(baseline_val) * 100) if baseline_val != 0 else 0

                diff = CoordinateDiff(
                    file_name='',
                    slide_index=0,
                    shape_index=0,
                    coordinate=key,
                    baseline_value=baseline_val,
                    compare_value=compare_val,
                    delta=delta,
                    delta_percent=delta_percent,
                )
                diffs.append(diff)

        return diffs

    def compare_shapes(
        self,
        baseline_shapes: List[Dict],
        compare_shapes: List[Dict],
        tolerance: float = 0
    ) -> List[CoordinateDiff]:
        """Compare shapes between baseline and comparison."""
        diffs = []

        # Compare shape counts
        if len(baseline_shapes) != len(compare_shapes):
            print(f"⚠️  Shape count mismatch: {len(baseline_shapes)} vs {len(compare_shapes)}")

        # Compare each shape
        for i in range(min(len(baseline_shapes), len(compare_shapes))):
            baseline_shape = baseline_shapes[i]
            compare_shape = compare_shapes[i]

            # Compare coordinates
            baseline_coord = baseline_shape.get('coordinates', {})
            compare_coord = compare_shape.get('coordinates', {})

            coord_diffs = self.compare_coordinates(baseline_coord, compare_coord, tolerance)

            for diff in coord_diffs:
                diff.shape_index = i
                diffs.append(diff)

        return diffs

    def compare_files(
        self,
        baseline_file: Dict,
        compare_file: Dict,
        tolerance: float = 0
    ) -> List[CoordinateDiff]:
        """Compare all slides in a file."""
        diffs = []

        baseline_slides = baseline_file.get('slides', [])
        compare_slides = compare_file.get('slides', [])

        if len(baseline_slides) != len(compare_slides):
            print(f"⚠️  Slide count mismatch: {len(baseline_slides)} vs {len(compare_slides)}")

        # Compare each slide
        for i in range(min(len(baseline_slides), len(compare_slides))):
            baseline_slide = baseline_slides[i]
            compare_slide = compare_slides[i]

            baseline_shapes = baseline_slide.get('shapes', [])
            compare_shapes = compare_slide.get('shapes', [])

            slide_diffs = self.compare_shapes(baseline_shapes, compare_shapes, tolerance)

            for diff in slide_diffs:
                diff.slide_index = i
                diffs.append(diff)

        return diffs

    def determine_tolerance(self, file_name: str) -> float:
        """
        Determine expected tolerance based on phase and file category.

        Returns tolerance in EMU.
        """
        # Phase 1 vs Phase 0: Exact match expected
        if self.compare_phase == "phase1" and self.baseline_phase == "phase0":
            return self.TOLERANCE_EXACT

        # Phase 2 vs Phase 0: Transform tests will differ significantly
        if self.compare_phase == "phase2" and self.baseline_phase == "phase0":
            # Check if file is in transform-affected category
            for category in self.TRANSFORM_CATEGORIES:
                if category in file_name.lower():
                    # Transform files expected to differ - use large tolerance
                    return float('inf')  # Don't flag as errors
            # Non-transform files should match exactly
            return self.TOLERANCE_EXACT

        # Phase 3 vs Phase 0/2: Minor precision differences allowed
        if self.compare_phase == "phase3":
            return self.TOLERANCE_PRECISION

        # Phase 4 vs Phase 3: Should match
        if self.compare_phase == "phase4" and self.baseline_phase == "phase3":
            return self.TOLERANCE_INTEGRATION

        # Default: exact match
        return self.TOLERANCE_EXACT

    def compare(self) -> Dict:
        """
        Perform full comparison between baseline and compare phases.

        Returns:
            Comparison report dict
        """
        print(f"\n{'='*60}")
        print(f"Comparing: {self.baseline_phase.upper()} vs {self.compare_phase.upper()}")
        print(f"{'='*60}\n")

        # Load both coordinate sets
        baseline_data = self.load_coordinates(self.baseline_phase)
        compare_data = self.load_coordinates(self.compare_phase)

        print(f"Baseline: {len(baseline_data.get('files', []))} files")
        print(f"Compare:  {len(compare_data.get('files', []))} files\n")

        # Build file lookup by filename (not full path, since phase differs)
        baseline_files = {Path(f['pptx_path']).name: f for f in baseline_data.get('files', [])}
        compare_files = {Path(f['pptx_path']).name: f for f in compare_data.get('files', [])}

        report = {
            'baseline_phase': self.baseline_phase,
            'compare_phase': self.compare_phase,
            'timestamp': datetime.now().isoformat(),
            'files_compared': 0,
            'total_differences': 0,
            'differences_by_file': {},
            'summary': {
                'exact_matches': 0,
                'minor_differences': 0,
                'major_differences': 0,
                'missing_files': [],
            }
        }

        # Compare each file
        for file_name, baseline_file in baseline_files.items():
            if file_name not in compare_files:
                report['summary']['missing_files'].append(file_name)
                print(f"⚠️  Missing in compare: {file_name}")
                continue

            compare_file = compare_files[file_name]

            # Determine tolerance for this file
            tolerance = self.determine_tolerance(file_name)

            print(f"Comparing: {file_name} (tolerance: {tolerance} EMU)... ", end='')

            # Compare files
            file_diffs = self.compare_files(baseline_file, compare_file, tolerance)

            # Update differences with file name
            for diff in file_diffs:
                diff.file_name = file_name

            report['files_compared'] += 1

            if len(file_diffs) == 0:
                print("✅ Exact match")
                report['summary']['exact_matches'] += 1
            elif tolerance == float('inf'):
                print(f"⚠️  {len(file_diffs)} differences (expected)")
                report['summary']['minor_differences'] += 1
            else:
                print(f"❌ {len(file_diffs)} differences")
                report['summary']['major_differences'] += 1

            report['differences_by_file'][file_name] = [
                {
                    'slide': d.slide_index,
                    'shape': d.shape_index,
                    'coordinate': d.coordinate,
                    'baseline': d.baseline_value,
                    'compare': d.compare_value,
                    'delta': d.delta,
                    'delta_percent': d.delta_percent,
                }
                for d in file_diffs
            ]

            report['total_differences'] += len(file_diffs)
            self.differences.extend(file_diffs)

        # Print summary
        print(f"\n{'='*60}")
        print(f"Comparison Summary")
        print(f"{'='*60}")
        print(f"Files compared:       {report['files_compared']}")
        print(f"Exact matches:        {report['summary']['exact_matches']}")
        print(f"Minor differences:    {report['summary']['minor_differences']}")
        print(f"Major differences:    {report['summary']['major_differences']}")
        print(f"Total differences:    {report['total_differences']}")
        print(f"{'='*60}\n")

        return report

    def save_report(self, report: Dict):
        """Save comparison report to JSON."""
        output_dir = project_root / "tests" / "baseline" / "outputs" / "comparisons"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{self.baseline_phase}_vs_{self.compare_phase}.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        print(f"Report saved: {output_path}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Compare baseline coordinates between phases"
    )
    parser.add_argument(
        "--baseline",
        required=True,
        help="Baseline phase (e.g., phase0)"
    )
    parser.add_argument(
        "--compare",
        required=True,
        help="Comparison phase (e.g., phase1)"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save comparison report to JSON"
    )

    args = parser.parse_args()

    try:
        comparator = BaselineComparator(args.baseline, args.compare)
        report = comparator.compare()

        if args.save:
            comparator.save_report(report)

        # Exit with error if major differences found
        if report['summary']['major_differences'] > 0:
            print("❌ Major differences detected!")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
Comprehensive SMIL Animation Test Runner for SVG2PPTX

This script runs a complete battery of tests against our SMIL animation
parser and converter, providing detailed analysis of conversion capabilities.

Usage:
    source venv/bin/activate && PYTHONPATH=. python tests/scripts/run_animation_tests.py
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from lxml import etree

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.converters.animations import AnimationConverter, AnimationType
from core.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext


@dataclass
class AnimationTestResult:
    """Results from testing a single animation element."""
    file_name: str
    element_index: int
    animation_type: str
    target_attribute: str
    can_convert: bool
    conversion_successful: bool
    values: str
    duration: str
    begin_time: str
    advanced_features: List[str]
    error_message: str = ""


class AnimationTestRunner:
    """Comprehensive animation testing and analysis."""

    def __init__(self):
        self.services = ConversionServices.create_default()
        self.converter = AnimationConverter(self.services)
        self.test_files = [
            "tests/data/multislide/svg_samples/animation_sequences/pure_smil_fade_sequence.svg",
            "tests/data/multislide/svg_samples/animation_sequences/rotating_shapes.svg",
            "tests/data/multislide/svg_samples/animation_sequences/motion_path_complex.svg",
            "tests/data/multislide/svg_samples/animation_sequences/comprehensive_smil_suite.svg",
            "tests/data/multislide/svg_samples/animation_sequences/advanced_timing_controls.svg"
        ]
        self.results: List[AnimationTestResult] = []

    def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive animation tests."""
        print("=" * 60)
        print("SVG2PPTX SMIL Animation Test Suite")
        print("=" * 60)

        total_animations = 0
        successful_conversions = 0

        for file_path in self.test_files:
            if not os.path.exists(file_path):
                print(f"⚠️  Skipping missing file: {file_path}")
                continue

            file_results = self._test_file(file_path)
            self.results.extend(file_results)

            file_animations = len(file_results)
            file_successful = sum(1 for r in file_results if r.conversion_successful)

            total_animations += file_animations
            successful_conversions += file_successful

            print(f"📁 {Path(file_path).name}")
            print(f"   Animations: {file_animations}, Successful: {file_successful}")

        # Generate summary report
        summary = self._generate_summary()
        self._print_detailed_report(summary)

        return summary

    def _test_file(self, file_path: str) -> List[AnimationTestResult]:
        """Test all animations in a single SVG file."""
        results = []

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            root = etree.fromstring(content.encode('utf-8'))
            animate_elements = root.xpath('//*[local-name()="animate" or local-name()="animateTransform" or local-name()="animateMotion"]')

            for i, elem in enumerate(animate_elements):
                result = self._test_element(file_path, i, elem, root)
                results.append(result)

        except Exception as e:
            # Create error result for file
            results.append(AnimationTestResult(
                file_name=Path(file_path).name,
                element_index=0,
                animation_type="ERROR",
                target_attribute="",
                can_convert=False,
                conversion_successful=False,
                values="",
                duration="",
                begin_time="",
                advanced_features=[],
                error_message=str(e)
            ))

        return results

    def _test_element(self, file_path: str, index: int, element: etree.Element, root: etree.Element) -> AnimationTestResult:
        """Test a single animation element."""
        tag_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag

        # Extract basic properties
        target_attr = element.get('attributeName', 'motion')
        values = element.get('values', '')
        duration = element.get('dur', '')
        begin_time = element.get('begin', '0s')

        # Detect advanced features
        advanced_features = []
        if element.get('keySplines'):
            advanced_features.append('keySplines')
        if element.get('accumulate'):
            advanced_features.append('accumulate')
        if element.get('additive'):
            advanced_features.append('additive')
        if element.get('calcMode') in ['spline', 'discrete']:
            advanced_features.append(f'calcMode={element.get("calcMode")}')
        if begin_time and ('.' in begin_time or begin_time.startswith('-')):
            advanced_features.append('complex_timing')

        # Test conversion
        can_convert = False
        conversion_successful = False
        error_message = ""

        try:
            can_convert = self.converter.can_convert(element)

            if can_convert:
                context = ConversionContext(services=self.services, svg_root=root)
                result = self.converter.convert(element, context)
                conversion_successful = True

        except Exception as e:
            error_message = str(e)

        return AnimationTestResult(
            file_name=Path(file_path).name,
            element_index=index,
            animation_type=tag_name,
            target_attribute=target_attr,
            can_convert=can_convert,
            conversion_successful=conversion_successful,
            values=values[:50] + "..." if len(values) > 50 else values,
            duration=duration,
            begin_time=begin_time,
            advanced_features=advanced_features,
            error_message=error_message
        )

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary statistics."""
        total = len(self.results)
        successful = sum(1 for r in self.results if r.conversion_successful)
        can_convert = sum(1 for r in self.results if r.can_convert)

        # Group by animation type
        by_type = {}
        for result in self.results:
            key = f"{result.animation_type}[{result.target_attribute}]"
            if key not in by_type:
                by_type[key] = {"total": 0, "successful": 0}
            by_type[key]["total"] += 1
            if result.conversion_successful:
                by_type[key]["successful"] += 1

        # Advanced features usage
        advanced_usage = {}
        for result in self.results:
            for feature in result.advanced_features:
                advanced_usage[feature] = advanced_usage.get(feature, 0) + 1

        return {
            "total_animations": total,
            "can_convert": can_convert,
            "successful_conversions": successful,
            "conversion_rate": (successful / total * 100) if total > 0 else 0,
            "recognition_rate": (can_convert / total * 100) if total > 0 else 0,
            "by_animation_type": by_type,
            "advanced_features": advanced_usage,
            "errors": [r for r in self.results if r.error_message]
        }

    def _print_detailed_report(self, summary: Dict[str, Any]):
        """Print detailed test report."""
        print("\n" + "=" * 60)
        print("DETAILED TEST RESULTS")
        print("=" * 60)

        print(f"📊 Overall Statistics:")
        print(f"   Total Animations: {summary['total_animations']}")
        print(f"   Recognition Rate: {summary['recognition_rate']:.1f}%")
        print(f"   Conversion Rate: {summary['conversion_rate']:.1f}%")

        print(f"\n🎯 Animation Type Breakdown:")
        for anim_type, stats in summary['by_animation_type'].items():
            rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"   {anim_type}: {stats['successful']}/{stats['total']} ({rate:.0f}%)")

        if summary['advanced_features']:
            print(f"\n⚡ Advanced Features Detected:")
            for feature, count in summary['advanced_features'].items():
                print(f"   {feature}: {count} instances")

        if summary['errors']:
            print(f"\n⚠️  Errors ({len(summary['errors'])}):")
            for error in summary['errors'][:5]:  # Show first 5 errors
                print(f"   {error.file_name}[{error.element_index}]: {error.error_message}")

        print(f"\n✅ Test Suite Complete!")
        print(f"   Animation parser is {'READY' if summary['recognition_rate'] > 95 else 'NEEDS WORK'}")
        print(f"   Converter is {'FUNCTIONAL' if summary['conversion_rate'] > 80 else 'NEEDS ENHANCEMENT'}")


def main():
    """Run the animation test suite."""
    runner = AnimationTestRunner()
    runner.run_all_tests()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Unit Converter Bottleneck Analysis for Task 1.2

Analyzes the current unit conversion system to identify performance bottlenecks
and areas for NumPy optimization.
"""

import sys
import time
import gc
import re
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
# Import directly from the units.py file
import importlib.util
units_path = project_root / "src" / "units.py"
spec = importlib.util.spec_from_file_location("units_module", units_path)
units_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(units_module)

UnitConverter = units_module.UnitConverter
UnitType = units_module.UnitType
ViewportContext = units_module.ViewportContext


class UnitConverterBottleneckAnalysis:
    """Analyzes unit converter performance bottlenecks."""

    def __init__(self):
        self.converter = UnitConverter()
        self.context = ViewportContext(width=800, height=600, font_size=16, dpi=96)

    def test_current_performance(self):
        """Test current unit converter performance."""
        print("🔍 Current Unit Converter Performance Analysis")
        print("=" * 60)

        # Test different scenarios
        scenarios = [
            ("Mixed units (small)", self._generate_mixed_units(1000)),
            ("Mixed units (medium)", self._generate_mixed_units(10000)),
            ("Mixed units (large)", self._generate_mixed_units(50000)),
            ("Pixel values only", [f"{i}px" for i in range(10000)]),
            ("Point values only", [f"{i}pt" for i in range(10000)]),
            ("Percentage values", [f"{i}%" for i in range(10000)]),
            ("Complex mixed", self._generate_complex_mixed(10000))
        ]

        results = []

        for scenario_name, values in scenarios:
            print(f"\n--- {scenario_name} ({len(values):,} values) ---")

            # Test individual conversion
            gc.collect()
            start_time = time.perf_counter()

            individual_results = []
            for value in values[:1000]:  # Subset for individual test
                try:
                    emu = self.converter.to_emu(value, self.context)
                    individual_results.append(emu)
                except:
                    individual_results.append(0)

            individual_time = time.perf_counter() - start_time
            individual_throughput = 1000 / individual_time

            # Test batch conversion
            gc.collect()
            start_time = time.perf_counter()

            batch_dict = {f"value_{i}": value for i, value in enumerate(values[:1000])}
            batch_results = self.converter.batch_convert(batch_dict, self.context)

            batch_time = time.perf_counter() - start_time
            batch_throughput = 1000 / batch_time

            print(f"  Individual: {individual_time:.6f}s ({individual_throughput:.0f} conv/sec)")
            print(f"  Batch: {batch_time:.6f}s ({batch_throughput:.0f} conv/sec)")
            print(f"  Batch speedup: {individual_time/batch_time:.1f}x")

            results.append({
                'scenario': scenario_name,
                'size': len(values),
                'individual_time': individual_time,
                'batch_time': batch_time,
                'individual_throughput': individual_throughput,
                'batch_throughput': batch_throughput,
                'speedup': individual_time / batch_time
            })

        return results

    def _generate_mixed_units(self, count: int) -> List[str]:
        """Generate mixed unit values."""
        units = ['px', 'pt', 'mm', 'cm', 'in', 'em', '%']
        return [f"{i * 0.5:.1f}{units[i % len(units)]}" for i in range(count)]

    def _generate_complex_mixed(self, count: int) -> List[str]:
        """Generate complex mixed values with decimals."""
        units = ['px', 'pt', 'mm', 'cm', 'in', 'em', 'ex', '%', 'vw', 'vh']
        return [f"{(i * 0.123 + 0.456):.3f}{units[i % len(units)]}" for i in range(count)]

    def analyze_parsing_bottlenecks(self):
        """Analyze string parsing bottlenecks."""
        print("\n🔍 String Parsing Bottleneck Analysis")
        print("=" * 40)

        test_values = [
            "100px", "2.5em", "50%", "1.5in", "10mm", "12pt",
            "0.5vh", "25vw", "1.2ex", "0px", "-10px", "1.23456789px"
        ] * 1000

        # Current regex parsing
        gc.collect()
        start_time = time.perf_counter()

        regex_results = []
        for value in test_values:
            result = self.converter.parse_length(value, self.context)
            regex_results.append(result)

        regex_time = time.perf_counter() - start_time

        print(f"Current regex parsing: {regex_time:.6f}s ({len(test_values)/regex_time:.0f} parse/sec)")

        # Analyze regex overhead
        pattern = re.compile(r'([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(.*)$')

        gc.collect()
        start_time = time.perf_counter()

        compiled_results = []
        for value in test_values:
            match = pattern.match(value.strip())
            if match:
                numeric = float(match.group(1))
                unit = match.group(2).lower().strip()
                compiled_results.append((numeric, unit))
            else:
                compiled_results.append((0.0, ''))

        compiled_time = time.perf_counter() - start_time

        print(f"Compiled regex parsing: {compiled_time:.6f}s ({len(test_values)/compiled_time:.0f} parse/sec)")
        print(f"Regex optimization: {regex_time/compiled_time:.1f}x speedup")

        return {
            'regex_time': regex_time,
            'compiled_time': compiled_time,
            'regex_speedup': regex_time / compiled_time
        }

    def identify_conversion_bottlenecks(self):
        """Identify unit conversion bottlenecks."""
        print("\n🔍 Unit Conversion Bottleneck Analysis")
        print("=" * 40)

        # Test different unit types
        unit_tests = [
            ("pixels", [f"{i}px" for i in range(1000, 2000)]),
            ("points", [f"{i}pt" for i in range(1000, 2000)]),
            ("millimeters", [f"{i}mm" for i in range(1000, 2000)]),
            ("inches", [f"{i}in" for i in range(100, 200)]),
            ("ems", [f"{i}em" for i in range(1, 100)]),
            ("percentages", [f"{i}%" for i in range(1, 100)])
        ]

        conversion_results = {}

        for unit_name, values in unit_tests:
            gc.collect()
            start_time = time.perf_counter()

            converted = []
            for value in values:
                emu = self.converter.to_emu(value, self.context)
                converted.append(emu)

            conversion_time = time.perf_counter() - start_time
            throughput = len(values) / conversion_time

            print(f"{unit_name:12}: {conversion_time:.6f}s ({throughput:.0f} conv/sec)")
            conversion_results[unit_name] = {
                'time': conversion_time,
                'throughput': throughput
            }

        return conversion_results

    def run_comprehensive_analysis(self):
        """Run comprehensive bottleneck analysis."""
        print("🚀 Unit Converter Bottleneck Analysis - Task 1.2")
        print("=" * 70)

        # Run all analyses
        performance_results = self.test_current_performance()
        parsing_results = self.analyze_parsing_bottlenecks()
        conversion_results = self.identify_conversion_bottlenecks()

        # Identify bottlenecks
        return self.identify_optimization_opportunities(
            performance_results, parsing_results, conversion_results
        )

    def identify_optimization_opportunities(self, performance_results, parsing_results, conversion_results):
        """Identify specific optimization opportunities."""
        print("\n" + "=" * 70)
        print("📊 BOTTLENECK ANALYSIS SUMMARY")
        print("=" * 70)

        bottlenecks = []

        # Analyze performance results
        avg_individual_throughput = sum(r['individual_throughput'] for r in performance_results) / len(performance_results)
        avg_batch_throughput = sum(r['batch_throughput'] for r in performance_results) / len(performance_results)

        print(f"\n🎯 CURRENT PERFORMANCE:")
        print(f"  Average individual throughput: {avg_individual_throughput:.0f} conversions/sec")
        print(f"  Average batch throughput: {avg_batch_throughput:.0f} conversions/sec")
        print(f"  Current batch speedup: {avg_batch_throughput/avg_individual_throughput:.1f}x")

        # Identify bottlenecks
        if avg_individual_throughput < 50000:
            bottlenecks.append("Individual conversion throughput too low (<50K/sec)")

        if avg_batch_throughput < 200000:
            bottlenecks.append("Batch conversion throughput too low (<200K/sec)")

        # Parsing bottlenecks
        if parsing_results['regex_speedup'] > 2:
            bottlenecks.append("Regex parsing can be optimized further")

        # Conversion bottlenecks
        slowest_conversion = min(conversion_results.values(), key=lambda x: x['throughput'])
        fastest_conversion = max(conversion_results.values(), key=lambda x: x['throughput'])

        if fastest_conversion['throughput'] / slowest_conversion['throughput'] > 5:
            bottlenecks.append("Large performance variation between unit types")

        print(f"\n🔍 IDENTIFIED BOTTLENECKS:")
        for i, bottleneck in enumerate(bottlenecks, 1):
            print(f"  {i}. {bottleneck}")

        print(f"\n💡 NUMPY OPTIMIZATION OPPORTUNITIES:")
        print(f"  1. Vectorized string parsing with NumPy char arrays")
        print(f"  2. Pre-computed conversion factor matrices")
        print(f"  3. Broadcasting for batch operations")
        print(f"  4. Vectorized regex operations")
        print(f"  5. Memory-efficient structured arrays")
        print(f"  6. Compiled critical paths with Numba")

        print(f"\n🎯 TARGET IMPROVEMENTS (Task 1.2):")
        print(f"  - Individual throughput: {avg_individual_throughput:.0f} → {avg_individual_throughput * 15:.0f} conv/sec (15x)")
        print(f"  - Batch throughput: {avg_batch_throughput:.0f} → {avg_batch_throughput * 30:.0f} conv/sec (30x)")
        print(f"  - Overall speedup target: 10-30x")

        return {
            'bottlenecks': bottlenecks,
            'current_performance': {
                'individual_throughput': avg_individual_throughput,
                'batch_throughput': avg_batch_throughput
            },
            'target_performance': {
                'individual_throughput': avg_individual_throughput * 15,
                'batch_throughput': avg_batch_throughput * 30
            }
        }


def main():
    """Run the unit converter bottleneck analysis."""
    try:
        analyzer = UnitConverterBottleneckAnalysis()
        results = analyzer.run_comprehensive_analysis()

        print("\n🎯 ANALYSIS COMPLETE - Ready for Task 1.2 Implementation")
        return 0

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
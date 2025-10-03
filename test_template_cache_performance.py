#!/usr/bin/env python3
"""
Test Template Cache Performance

Tests the performance impact of template caching and deep copy optimization.
"""

import time
import statistics
from typing import List
from lxml import etree as ET
from lxml.etree import Element
import copy

def create_test_template() -> Element:
    """Create a test template similar to our text templates."""
    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:nvSpPr>
    <p:cNvPr id="1" name="TextFrame"/>
    <p:cNvSpPr txBox="1"/>
    <p:nvPr/>
  </p:nvSpPr>
  <p:spPr>
    <a:xfrm>
      <a:off x="0" y="0"/>
      <a:ext cx="1" cy="1"/>
    </a:xfrm>
    <a:prstGeom prst="rect">
      <a:avLst/>
    </a:prstGeom>
    <a:noFill/>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="none" rtlCol="0">
      <a:spAutoFit/>
    </a:bodyPr>
    <a:lstStyle/>
    <a:p>
      <a:r>
        <a:rPr lang="en-US" sz="1200" b="0" i="0">
          <a:solidFill>
            <a:srgbClr val="000000"/>
          </a:solidFill>
          <a:latin typeface="Arial"/>
        </a:rPr>
        <a:t>Sample Text</a:t>
      </a:r>
    </a:p>
  </p:txBody>
</p:sp>"""
    return ET.fromstring(xml_content)

def benchmark_current_deep_copy(template: Element, iterations: int = 1000) -> List[float]:
    """Benchmark current deep copy method (serialize + parse)."""
    times = []

    for _ in range(iterations):
        start_time = time.perf_counter()

        # Current method: serialize to string then parse back
        copy_element = ET.fromstring(ET.tostring(template))

        end_time = time.perf_counter()
        times.append(end_time - start_time)

    return times

def benchmark_optimized_deep_copy(template: Element, iterations: int = 1000) -> List[float]:
    """Benchmark optimized deep copy method using copy.deepcopy."""
    times = []

    for _ in range(iterations):
        start_time = time.perf_counter()

        # Optimized method: use copy.deepcopy
        copy_element = copy.deepcopy(template)

        end_time = time.perf_counter()
        times.append(end_time - start_time)

    return times

def benchmark_no_copy(template: Element, iterations: int = 1000) -> List[float]:
    """Benchmark no copy (reference only) for comparison."""
    times = []

    for _ in range(iterations):
        start_time = time.perf_counter()

        # No copy method: just reference (unsafe but fastest)
        copy_element = template

        end_time = time.perf_counter()
        times.append(end_time - start_time)

    return times

def analyze_results(name: str, times: List[float]):
    """Analyze and print performance results."""
    mean_time = statistics.mean(times)
    ops_per_sec = len(times) / sum(times)

    print(f"✓ {name}:")
    print(f"  Mean time: {mean_time:.6f}s")
    print(f"  Operations/sec: {ops_per_sec:.1f}")
    print(f"  Total time: {sum(times):.4f}s")

    return {
        'mean': mean_time,
        'ops_per_sec': ops_per_sec,
        'total': sum(times)
    }

def main():
    """Run template cache performance tests."""
    print("🔄 Template Cache Deep Copy Performance Test")
    print("=" * 50)

    # Create test template
    template = create_test_template()
    iterations = 1000
    print(f"Running {iterations} deep copy operations...\n")

    # Test current method (serialize + parse)
    print("📊 Testing CURRENT method (serialize + parse)...")
    current_times = benchmark_current_deep_copy(template, iterations)
    current_stats = analyze_results("Current Deep Copy", current_times)

    # Test optimized method (copy.deepcopy)
    print(f"\n📊 Testing OPTIMIZED method (copy.deepcopy)...")
    optimized_times = benchmark_optimized_deep_copy(template, iterations)
    optimized_stats = analyze_results("Optimized Deep Copy", optimized_times)

    # Test no copy (reference only)
    print(f"\n📊 Testing REFERENCE ONLY (no copy)...")
    no_copy_times = benchmark_no_copy(template, iterations)
    no_copy_stats = analyze_results("No Copy Reference", no_copy_times)

    # Performance comparison
    print(f"\n🏁 PERFORMANCE COMPARISON:")
    print("=" * 30)

    speedup = optimized_stats['ops_per_sec'] / current_stats['ops_per_sec']
    time_reduction = (current_stats['mean'] - optimized_stats['mean']) / current_stats['mean'] * 100

    print(f"Current:   {current_stats['ops_per_sec']:.1f} ops/sec")
    print(f"Optimized: {optimized_stats['ops_per_sec']:.1f} ops/sec")
    print(f"Reference: {no_copy_stats['ops_per_sec']:.1f} ops/sec")

    print(f"\nSpeedup: {speedup:.2f}x")
    print(f"Time reduction: {time_reduction:.1f}%")

    if speedup > 1.0:
        print(f"🚀 Optimized deep copy is {speedup:.2f}x FASTER!")
    else:
        print(f"⚠️  Optimized deep copy is {1/speedup:.2f}x slower")

    return {
        'current': current_stats,
        'optimized': optimized_stats,
        'no_copy': no_copy_stats,
        'speedup': speedup
    }

if __name__ == "__main__":
    results = main()
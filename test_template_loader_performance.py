#!/usr/bin/env python3
"""
Test TemplateLoader Performance

Tests the direct performance of template loading with optimized deep copy.
"""

import time
import statistics
import sys
from typing import List, Dict

# Add project root to path
sys.path.append('/Users/ynse/projects/svg2pptx')

def benchmark_template_loader_performance():
    """Test the optimized TemplateLoader performance."""
    try:
        from core.io.template_loader import TemplateLoader
        loader = TemplateLoader()

        # Test template loading operations
        templates_to_test = [
            "text_shape.xml",
            "text_emf_picture.xml",
            "text_paragraph.xml",
            "text_run.xml",
            "path_shape.xml",
            "path_emf_picture.xml",
            "group_shape.xml",
            "group_picture.xml"
        ]

        print("🔄 Testing TemplateLoader Performance")
        print("=" * 40)

        total_ops = 0
        iterations = 1000

        for template_name in templates_to_test:
            try:
                times = []

                for _ in range(iterations):
                    start_time = time.perf_counter()
                    element = loader.load_template(template_name)
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)

                if times:
                    ops_per_sec = len(times) / sum(times)
                    total_ops += ops_per_sec
                    print(f"  {template_name:20}: {ops_per_sec:8.1f} ops/sec")

            except Exception as e:
                print(f"  {template_name:20}: Failed - {e}")

        print("=" * 40)
        print(f"  {'TOTAL THROUGHPUT':20}: {total_ops:8.1f} ops/sec")

        # Test cache hit performance vs cache miss
        print(f"\n🎯 Cache Performance Analysis:")
        print("-" * 30)

        # Clear cache and measure first load (cache miss)
        loader.clear_cache()

        miss_times = []
        for _ in range(100):
            loader.clear_cache()  # Force cache miss
            start_time = time.perf_counter()
            loader.load_template("text_shape.xml")
            end_time = time.perf_counter()
            miss_times.append(end_time - start_time)

        # Measure subsequent loads (cache hits)
        hit_times = []
        for _ in range(100):
            start_time = time.perf_counter()
            loader.load_template("text_shape.xml")  # Cache hit
            end_time = time.perf_counter()
            hit_times.append(end_time - start_time)

        miss_ops_per_sec = len(miss_times) / sum(miss_times)
        hit_ops_per_sec = len(hit_times) / sum(hit_times)
        cache_speedup = hit_ops_per_sec / miss_ops_per_sec

        print(f"  Cache Miss:   {miss_ops_per_sec:8.1f} ops/sec")
        print(f"  Cache Hit:    {hit_ops_per_sec:8.1f} ops/sec")
        print(f"  Cache Speedup: {cache_speedup:6.2f}x")

        return {
            'total_throughput': total_ops,
            'cache_miss_performance': miss_ops_per_sec,
            'cache_hit_performance': hit_ops_per_sec,
            'cache_speedup': cache_speedup
        }

    except Exception as e:
        print(f"❌ TemplateLoader test failed: {e}")
        return {}

if __name__ == "__main__":
    results = benchmark_template_loader_performance()
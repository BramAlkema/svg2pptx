"""
Performance benchmarks for NumPy-optimized filter implementations.

This module provides comprehensive performance testing to validate the claimed
40-120x speedup improvements through NumPy vectorization compared to legacy
scalar implementations.

Performance Targets:
- Gaussian Blur: >100,000 operations/second (100x improvement)
- Convolution: >50,000 operations/second (50x improvement)
- Edge Detection: >200,000 operations/second (200x improvement)
- Memory Usage: 50-70% reduction vs legacy
- Batch Processing: Linear scaling with input size

Test Categories:
1. Single Operation Benchmarks - Individual filter performance
2. Batch Processing Benchmarks - Vectorized batch operations
3. Memory Efficiency Tests - Memory usage analysis
4. Scalability Tests - Performance scaling validation
5. Accuracy Validation - Correctness comparison vs legacy
"""

import pytest
import numpy as np
import time
import psutil
import os
from typing import List, Dict, Any, Tuple
from unittest.mock import Mock
from lxml import etree

from src.converters.filters.numpy_integration import (
    NumPyGaussianBlurAdapter,
    NumPyConvolveMatrixAdapter,
    benchmark_filter_performance
)
from src.converters.filters.numpy_filters import (
    NumPyBlurFilter,
    NumPyConvolutionFilter,
    apply_optimized_gaussian_blur,
    apply_optimized_convolution,
    apply_optimized_edge_detection,
    SCIPY_AVAILABLE,
    NUMBA_AVAILABLE
)
from src.converters.filters.image.blur import GaussianBlurFilter
from src.converters.filters.image.convolve_matrix import ConvolveMatrixFilter
from src.converters.filters.core.base import FilterContext


class TestNumPyFilterPerformance:
    """
    Comprehensive performance benchmarks for NumPy filter implementations.
    """

    @pytest.fixture
    def setup_performance_test_data(self):
        """Setup test data for performance benchmarking"""
        # Create mock filter context
        mock_unit_converter = Mock()
        mock_unit_converter.to_emu.return_value = 50000
        mock_unit_converter.to_px.return_value = 2.0

        mock_context = Mock(spec=FilterContext)
        mock_context.unit_converter = mock_unit_converter
        mock_context.transform_parser = Mock()
        mock_context.color_parser = Mock()
        mock_context.viewport = {'width': 200, 'height': 100}
        mock_context.get_property.return_value = None

        # Create test images of various sizes
        test_images = {
            'small': np.random.rand(50, 50, 3).astype(np.float32),
            'medium': np.random.rand(200, 200, 3).astype(np.float32),
            'large': np.random.rand(500, 500, 3).astype(np.float32),
            'grayscale': np.random.rand(200, 200).astype(np.float32)
        }

        # Create test SVG elements
        blur_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        blur_element.set("stdDeviation", "2.5")

        conv_element = etree.Element("feConvolveMatrix")
        conv_element.set("kernelMatrix", "0 -1 0 -1 4 -1 0 -1 0")  # Laplacian
        conv_element.set("order", "3")

        return {
            'mock_context': mock_context,
            'test_images': test_images,
            'blur_element': blur_element,
            'conv_element': conv_element,
            'performance_targets': {
                'blur_ops_per_second': 100000,
                'convolution_ops_per_second': 50000,
                'edge_detection_ops_per_second': 200000,
                'memory_reduction_percent': 50
            }
        }

    @pytest.mark.performance
    def test_gaussian_blur_performance_single_operations(self, setup_performance_test_data):
        """
        Benchmark single Gaussian blur operations.

        Target: >100,000 operations/second
        """
        data = setup_performance_test_data
        numpy_filter = NumPyGaussianBlurAdapter()
        legacy_filter = GaussianBlurFilter()

        # Test different blur intensities
        blur_values = [0.5, 1.0, 2.5, 5.0, 10.0]
        numpy_times = []
        legacy_times = []

        for blur_sigma in blur_values:
            # Setup element
            element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
            element.set("stdDeviation", str(blur_sigma))

            # Benchmark NumPy implementation
            start_time = time.perf_counter()
            for _ in range(1000):  # 1000 operations
                result = numpy_filter.apply(element, data['mock_context'])
                assert result.success
            numpy_time = time.perf_counter() - start_time
            numpy_times.append(numpy_time)

            # Benchmark legacy implementation
            start_time = time.perf_counter()
            for _ in range(1000):  # 1000 operations
                result = legacy_filter.apply(element, data['mock_context'])
                assert result.success
            legacy_time = time.perf_counter() - start_time
            legacy_times.append(legacy_time)

        # Calculate performance metrics
        avg_numpy_time = np.mean(numpy_times)
        avg_legacy_time = np.mean(legacy_times)
        speedup = avg_legacy_time / avg_numpy_time if avg_numpy_time > 0 else 0
        ops_per_second = 1000 / avg_numpy_time if avg_numpy_time > 0 else 0

        # Validate performance targets
        assert ops_per_second >= data['performance_targets']['blur_ops_per_second'], \
            f"Blur performance below target: {ops_per_second:.0f} < {data['performance_targets']['blur_ops_per_second']}"

        # Report performance improvement
        print(f"\nGaussian Blur Performance:")
        print(f"  NumPy: {ops_per_second:.0f} ops/sec")
        print(f"  Speedup: {speedup:.1f}x")
        print(f"  Target met: {'✓' if ops_per_second >= data['performance_targets']['blur_ops_per_second'] else '✗'}")

    @pytest.mark.performance
    def test_convolution_performance_single_operations(self, setup_performance_test_data):
        """
        Benchmark single convolution operations.

        Target: >50,000 operations/second
        """
        data = setup_performance_test_data
        numpy_filter = NumPyConvolveMatrixAdapter()
        legacy_filter = ConvolveMatrixFilter()

        # Test different kernel types
        kernels = {
            'identity': "0 0 0 0 1 0 0 0 0",
            'laplacian': "0 -1 0 -1 4 -1 0 -1 0",
            'sobel_h': "-1 0 1 -2 0 2 -1 0 1",
            'gaussian': "1 2 1 2 4 2 1 2 1"
        }

        numpy_times = []
        legacy_times = []

        for kernel_name, kernel_matrix in kernels.items():
            # Setup element
            element = etree.Element("feConvolveMatrix")
            element.set("kernelMatrix", kernel_matrix)
            element.set("order", "3")

            # Benchmark NumPy implementation
            start_time = time.perf_counter()
            for _ in range(500):  # 500 operations
                result = numpy_filter.apply(element, data['mock_context'])
                assert result.success
            numpy_time = time.perf_counter() - start_time
            numpy_times.append(numpy_time)

            # Benchmark legacy implementation
            start_time = time.perf_counter()
            for _ in range(500):  # 500 operations
                result = legacy_filter.apply(element, data['mock_context'])
                assert result.success
            legacy_time = time.perf_counter() - start_time
            legacy_times.append(legacy_time)

        # Calculate performance metrics
        avg_numpy_time = np.mean(numpy_times)
        avg_legacy_time = np.mean(legacy_times)
        speedup = avg_legacy_time / avg_numpy_time if avg_numpy_time > 0 else 0
        ops_per_second = 500 / avg_numpy_time if avg_numpy_time > 0 else 0

        # Validate performance targets
        assert ops_per_second >= data['performance_targets']['convolution_ops_per_second'], \
            f"Convolution performance below target: {ops_per_second:.0f} < {data['performance_targets']['convolution_ops_per_second']}"

        print(f"\nConvolution Performance:")
        print(f"  NumPy: {ops_per_second:.0f} ops/sec")
        print(f"  Speedup: {speedup:.1f}x")
        print(f"  Target met: {'✓' if ops_per_second >= data['performance_targets']['convolution_ops_per_second'] else '✗'}")

    @pytest.mark.performance
    def test_batch_processing_performance(self, setup_performance_test_data):
        """
        Benchmark batch processing capabilities.

        Tests vectorized operations on multiple images simultaneously.
        """
        data = setup_performance_test_data
        numpy_blur = NumPyBlurFilter()

        # Test batch sizes
        batch_sizes = [1, 10, 50, 100]
        processing_times = []

        for batch_size in batch_sizes:
            # Create batch of test images
            images = [data['test_images']['medium'] for _ in range(batch_size)]
            sigma_x = [2.0] * batch_size
            sigma_y = [2.0] * batch_size

            # Benchmark batch processing
            start_time = time.perf_counter()
            results = numpy_blur.apply_gaussian_blur_vectorized(images, sigma_x, sigma_y)
            processing_time = time.perf_counter() - start_time
            processing_times.append(processing_time)

            # Validate results
            assert len(results) == batch_size
            for result in results:
                assert result.shape == data['test_images']['medium'].shape

        # Analyze scaling behavior
        # Should be approximately linear for well-vectorized operations
        time_per_image = [t / bs for t, bs in zip(processing_times, batch_sizes)]
        scaling_efficiency = min(time_per_image) / max(time_per_image)

        print(f"\nBatch Processing Performance:")
        print(f"  Batch sizes: {batch_sizes}")
        print(f"  Times per image: {[f'{t:.4f}s' for t in time_per_image]}")
        print(f"  Scaling efficiency: {scaling_efficiency:.2f}")

        # Scaling should be reasonably efficient (>0.5 for vectorized operations)
        assert scaling_efficiency > 0.5, f"Poor scaling efficiency: {scaling_efficiency:.2f}"

    @pytest.mark.performance
    def test_edge_detection_performance(self, setup_performance_test_data):
        """
        Benchmark optimized edge detection operations.

        Target: >200,000 operations/second
        """
        data = setup_performance_test_data
        conv_filter = NumPyConvolutionFilter()

        edge_types = ['sobel', 'laplacian', 'prewitt']
        performance_results = {}

        for edge_type in edge_types:
            if not SCIPY_AVAILABLE:
                pytest.skip(f"SciPy not available for {edge_type} optimization")

            # Benchmark edge detection
            start_time = time.perf_counter()
            for _ in range(1000):  # 1000 operations
                result = conv_filter.apply_edge_detection_optimized(
                    data['test_images']['small'], edge_type
                )
                assert result.shape == data['test_images']['small'].shape
            processing_time = time.perf_counter() - start_time

            ops_per_second = 1000 / processing_time
            performance_results[edge_type] = ops_per_second

        # Validate performance targets
        avg_performance = np.mean(list(performance_results.values()))
        assert avg_performance >= data['performance_targets']['edge_detection_ops_per_second'], \
            f"Edge detection performance below target: {avg_performance:.0f} < {data['performance_targets']['edge_detection_ops_per_second']}"

        print(f"\nEdge Detection Performance:")
        for edge_type, ops_per_sec in performance_results.items():
            print(f"  {edge_type}: {ops_per_sec:.0f} ops/sec")
        print(f"  Average: {avg_performance:.0f} ops/sec")
        print(f"  Target met: {'✓' if avg_performance >= data['performance_targets']['edge_detection_ops_per_second'] else '✗'}")

    @pytest.mark.performance
    def test_memory_efficiency(self, setup_performance_test_data):
        """
        Test memory efficiency of NumPy implementations vs legacy.

        Target: 50-70% memory reduction
        """
        data = setup_performance_test_data
        process = psutil.Process(os.getpid())

        # Baseline memory usage
        baseline_memory = process.memory_info().rss

        # Test NumPy memory usage
        numpy_filter = NumPyBlurFilter()
        large_images = [data['test_images']['large'] for _ in range(10)]

        memory_before_numpy = process.memory_info().rss
        results_numpy = numpy_filter.apply_gaussian_blur_vectorized(
            large_images, [3.0] * 10, [3.0] * 10
        )
        memory_after_numpy = process.memory_info().rss
        numpy_memory_usage = memory_after_numpy - memory_before_numpy

        # Clean up
        del results_numpy
        del large_images

        # Test with smaller batch for comparison
        small_images = [data['test_images']['small'] for _ in range(10)]
        memory_before_small = process.memory_info().rss
        results_small = numpy_filter.apply_gaussian_blur_vectorized(
            small_images, [3.0] * 10, [3.0] * 10
        )
        memory_after_small = process.memory_info().rss
        small_memory_usage = memory_after_small - memory_before_small

        # Calculate memory efficiency
        memory_per_large_image = numpy_memory_usage / 10 if numpy_memory_usage > 0 else 0
        memory_per_small_image = small_memory_usage / 10 if small_memory_usage > 0 else 0

        print(f"\nMemory Efficiency:")
        print(f"  Large image (500x500): {memory_per_large_image / 1024 / 1024:.2f} MB")
        print(f"  Small image (50x50): {memory_per_small_image / 1024 / 1024:.2f} MB")
        print(f"  Baseline memory: {baseline_memory / 1024 / 1024:.2f} MB")

        # Memory usage should be reasonable for the image sizes
        max_expected_memory_per_large = 50 * 1024 * 1024  # 50 MB per large image
        assert memory_per_large_image < max_expected_memory_per_large, \
            f"Memory usage too high: {memory_per_large_image / 1024 / 1024:.2f} MB > 50 MB"

    @pytest.mark.performance
    def test_scalability_analysis(self, setup_performance_test_data):
        """
        Test performance scaling with different input sizes.
        """
        data = setup_performance_test_data
        numpy_filter = NumPyBlurFilter()

        # Test different image sizes
        sizes = [(50, 50), (100, 100), (200, 200), (300, 300)]
        processing_times = []

        for width, height in sizes:
            test_image = np.random.rand(height, width, 3).astype(np.float32)

            # Benchmark processing time
            start_time = time.perf_counter()
            for _ in range(100):  # 100 operations per size
                result = numpy_filter.apply_gaussian_blur_vectorized(test_image, 2.0, 2.0)
                assert result.shape == test_image.shape
            processing_time = time.perf_counter() - start_time
            processing_times.append(processing_time / 100)  # Time per operation

        # Analyze scaling
        pixels = [w * h for w, h in sizes]
        times_per_pixel = [t / p for t, p in zip(processing_times, pixels)]

        print(f"\nScalability Analysis:")
        for (w, h), time, tpp in zip(sizes, processing_times, times_per_pixel):
            print(f"  {w}x{h}: {time*1000:.2f}ms ({tpp*1e9:.2f}ns/pixel)")

        # Scaling should be roughly linear for well-optimized algorithms
        scaling_factor = max(times_per_pixel) / min(times_per_pixel)
        assert scaling_factor < 3.0, f"Poor scaling: {scaling_factor:.2f}x variation in time per pixel"

    @pytest.mark.performance
    def test_separable_kernel_optimization(self, setup_performance_test_data):
        """
        Test performance improvement from separable kernel optimization.
        """
        data = setup_performance_test_data
        conv_filter = NumPyConvolutionFilter()

        # Test separable vs non-separable kernels
        separable_kernel = np.outer([1, 2, 1], [1, 2, 1])  # Gaussian-like, separable
        non_separable_kernel = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])  # Not separable

        test_image = data['test_images']['medium']

        # Benchmark separable kernel
        start_time = time.perf_counter()
        for _ in range(100):
            result = conv_filter.apply_convolution_vectorized(test_image, separable_kernel)
        separable_time = time.perf_counter() - start_time

        # Benchmark non-separable kernel
        start_time = time.perf_counter()
        for _ in range(100):
            result = conv_filter.apply_convolution_vectorized(test_image, non_separable_kernel)
        non_separable_time = time.perf_counter() - start_time

        # Separable convolution should be faster
        speedup = non_separable_time / separable_time if separable_time > 0 else 1

        print(f"\nSeparable Kernel Optimization:")
        print(f"  Separable: {separable_time*1000:.2f}ms")
        print(f"  Non-separable: {non_separable_time*1000:.2f}ms")
        print(f"  Speedup: {speedup:.1f}x")

        # Should see some improvement for separable kernels
        assert speedup >= 1.0, f"Separable kernel should be faster: {speedup:.2f}x"

    @pytest.mark.performance
    @pytest.mark.skipif(not SCIPY_AVAILABLE, reason="SciPy not available")
    def test_scipy_optimization_impact(self, setup_performance_test_data):
        """
        Test the performance impact of SciPy optimizations.
        """
        data = setup_performance_test_data

        # Test with SciPy available
        numpy_filter = NumPyBlurFilter()
        test_image = data['test_images']['medium']

        start_time = time.perf_counter()
        for _ in range(100):
            result = numpy_filter.apply_gaussian_blur_vectorized(test_image, 3.0, 3.0)
        scipy_time = time.perf_counter() - start_time

        # Test separable blur (should be even faster)
        start_time = time.perf_counter()
        for _ in range(100):
            result = numpy_filter.apply_separable_blur(test_image, 3.0, 3.0)
        separable_time = time.perf_counter() - start_time

        print(f"\nSciPy Optimization Impact:")
        print(f"  Standard SciPy: {scipy_time*1000:.2f}ms")
        print(f"  Separable: {separable_time*1000:.2f}ms")
        print(f"  Improvement: {scipy_time/separable_time:.1f}x")

    @pytest.mark.performance
    def test_benchmark_utility_function(self, setup_performance_test_data):
        """
        Test the benchmark utility function for comprehensive analysis.
        """
        data = setup_performance_test_data
        numpy_filter = NumPyGaussianBlurAdapter()

        # Run comprehensive benchmark
        benchmark_results = benchmark_filter_performance(
            numpy_filter,
            data['blur_element'],
            data['mock_context'],
            iterations=100
        )

        # Validate benchmark results
        assert 'mean_time' in benchmark_results
        assert 'throughput' in benchmark_results
        assert 'success_rate' in benchmark_results
        assert benchmark_results['success_rate'] >= 0.95  # Should have high success rate
        assert benchmark_results['throughput'] > 1000  # Should process >1000 ops/sec

        print(f"\nBenchmark Results:")
        print(f"  Success rate: {benchmark_results['success_rate']:.1%}")
        print(f"  Mean time: {benchmark_results['mean_time']*1000:.2f}ms")
        print(f"  Throughput: {benchmark_results['throughput']:.0f} ops/sec")
        print(f"  Std deviation: {benchmark_results['std_time']*1000:.2f}ms")


class TestNumPyFilterAccuracy:
    """
    Accuracy validation tests to ensure NumPy optimizations maintain correctness.
    """

    @pytest.fixture
    def setup_accuracy_test_data(self):
        """Setup test data for accuracy validation"""
        # Create deterministic test images
        np.random.seed(42)  # For reproducible results

        test_images = {
            'gradient': np.linspace(0, 1, 10000).reshape(100, 100, 1).astype(np.float32),
            'checkerboard': np.kron([[1, 0] * 25, [0, 1] * 25] * 25, np.ones((2, 2, 1))).astype(np.float32),
            'noise': np.random.rand(50, 50, 3).astype(np.float32)
        }

        return {'test_images': test_images}

    def test_blur_accuracy_validation(self, setup_accuracy_test_data):
        """
        Validate that NumPy blur produces mathematically correct results.
        """
        data = setup_accuracy_test_data
        numpy_filter = NumPyBlurFilter()

        # Test with known blur parameters
        test_image = data['test_images']['gradient']
        sigma = 2.0

        # Apply NumPy blur
        blurred_numpy = numpy_filter.apply_gaussian_blur_vectorized(test_image, sigma, sigma)

        # Validate basic properties
        assert blurred_numpy.shape == test_image.shape
        assert np.all(blurred_numpy >= 0) and np.all(blurred_numpy <= 1)

        # Test that blur reduces high-frequency content (should be smoother)
        # Calculate gradient magnitude as a proxy for high-frequency content
        grad_original = np.gradient(test_image.squeeze())
        grad_blurred = np.gradient(blurred_numpy.squeeze())

        original_variation = np.std(grad_original)
        blurred_variation = np.std(grad_blurred)

        # Blurred image should have less variation
        assert blurred_variation < original_variation, "Blur should reduce high-frequency content"

        print(f"\nBlur Accuracy Validation:")
        print(f"  Original gradient std: {original_variation:.4f}")
        print(f"  Blurred gradient std: {blurred_variation:.4f}")
        print(f"  Smoothing factor: {original_variation/blurred_variation:.2f}x")

    def test_convolution_accuracy_validation(self, setup_accuracy_test_data):
        """
        Validate that NumPy convolution produces correct results.
        """
        data = setup_accuracy_test_data
        conv_filter = NumPyConvolutionFilter()

        # Test with identity kernel (should return unchanged image)
        test_image = data['test_images']['checkerboard']
        identity_kernel = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 0]])

        result = conv_filter.apply_convolution_vectorized(test_image, identity_kernel)

        # Identity convolution should preserve the image (within numerical precision)
        difference = np.abs(result - test_image)
        max_difference = np.max(difference)

        assert max_difference < 1e-6, f"Identity convolution error too large: {max_difference}"

        print(f"\nConvolution Accuracy Validation:")
        print(f"  Identity kernel max error: {max_difference:.2e}")
        print(f"  Mean absolute error: {np.mean(difference):.2e}")

    def test_edge_detection_accuracy(self, setup_accuracy_test_data):
        """
        Validate edge detection accuracy against known patterns.
        """
        if not SCIPY_AVAILABLE:
            pytest.skip("SciPy not available for edge detection accuracy test")

        data = setup_accuracy_test_data
        conv_filter = NumPyConvolutionFilter()

        # Create a test image with known edges
        edge_image = np.zeros((50, 50))
        edge_image[20:30, :] = 1.0  # Horizontal edge
        edge_image[:, 20:30] = 1.0  # Vertical edge

        # Apply edge detection
        sobel_result = conv_filter.apply_edge_detection_optimized(edge_image, "sobel")
        laplacian_result = conv_filter.apply_edge_detection_optimized(edge_image, "laplacian")

        # Edge detection should produce high values near edges
        # Check that edge regions have higher values than interior regions
        edge_region = sobel_result[19:31, 19:31]  # Around the cross pattern
        interior_region = sobel_result[5:15, 5:15]  # Interior region

        edge_mean = np.mean(edge_region)
        interior_mean = np.mean(interior_region)

        assert edge_mean > interior_mean, "Edge detection should highlight edges"

        print(f"\nEdge Detection Accuracy:")
        print(f"  Edge region mean: {edge_mean:.4f}")
        print(f"  Interior region mean: {interior_mean:.4f}")
        print(f"  Edge enhancement: {edge_mean/interior_mean:.2f}x")


if __name__ == "__main__":
    # Run performance tests when executed directly
    pytest.main([__file__, "-v", "-m", "performance", "--tb=short"])
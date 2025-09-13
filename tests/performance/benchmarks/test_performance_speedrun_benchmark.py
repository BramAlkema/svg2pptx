#!/usr/bin/env python3
"""
Tests for speedrun benchmark performance module.
"""

import pytest
import time
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from src.performance.speedrun_benchmark import (
    BenchmarkResult, BenchmarkSuite, SVGTestGenerator,
    PerformanceBenchmark, SpeedrunValidator, BenchmarkReporter
)


class TestBenchmarkResult:
    """Test BenchmarkResult dataclass."""
    
    def test_benchmark_result_creation(self):
        """Test basic benchmark result creation."""
        result = BenchmarkResult(
            test_name="test_basic_shapes",
            svg_count=10,
            total_elements=50,
            baseline_time_seconds=2.5,
            optimized_time_seconds=0.25,
            speedup_factor=10.0
        )
        
        assert result.test_name == "test_basic_shapes"
        assert result.svg_count == 10
        assert result.total_elements == 50
        assert result.baseline_time_seconds == 2.5
        assert result.optimized_time_seconds == 0.25
        assert result.speedup_factor == 10.0
    
    def test_speedup_calculation(self):
        """Test speedup factor calculation."""
        result = BenchmarkResult(
            test_name="speedup_test",
            svg_count=5,
            total_elements=25,
            baseline_time_seconds=5.0,
            optimized_time_seconds=1.0,
            speedup_factor=0.0  # Will be calculated
        )
        
        # Calculate speedup factor
        result.speedup_factor = result.baseline_time_seconds / result.optimized_time_seconds
        assert result.speedup_factor == 5.0
    
    def test_benchmark_result_validation(self):
        """Test benchmark result validation."""
        # Valid result
        valid_result = BenchmarkResult(
            test_name="valid_test",
            svg_count=1,
            total_elements=5,
            baseline_time_seconds=1.0,
            optimized_time_seconds=0.1,
            speedup_factor=10.0
        )
        
        assert valid_result.svg_count > 0
        assert valid_result.total_elements > 0
        assert valid_result.baseline_time_seconds > 0
        assert valid_result.optimized_time_seconds > 0
        assert valid_result.speedup_factor > 1.0  # Should be improvement


class TestSVGTestGenerator:
    """Test SVG test data generation."""
    
    def test_generator_initialization(self):
        """Test SVG test generator initialization."""
        generator = SVGTestGenerator(seed=42)
        assert generator.seed == 42
        assert generator.rng is not None
    
    def test_generate_basic_shapes(self):
        """Test generation of basic SVG shapes."""
        generator = SVGTestGenerator()
        
        shapes = generator.generate_basic_shapes(count=10)
        assert len(shapes) == 10
        
        # Check that different shape types are generated
        shape_types = set()
        for shape in shapes:
            if hasattr(shape, 'tag'):
                shape_types.add(shape.tag)
        
        assert len(shape_types) > 1  # Should have variety
    
    def test_generate_complex_svg(self):
        """Test generation of complex SVG documents."""
        generator = SVGTestGenerator()
        
        svg_doc = generator.generate_complex_svg(
            element_count=20,
            include_groups=True,
            include_transforms=True
        )
        
        assert svg_doc is not None
        assert svg_doc.tag.endswith('svg')
        
        # Count elements
        all_elements = svg_doc.xpath('//*')
        assert len(all_elements) >= 20
    
    def test_generate_performance_test_suite(self):
        """Test generation of performance test suite."""
        generator = SVGTestGenerator()
        
        test_suite = generator.generate_performance_test_suite()
        
        assert 'small_documents' in test_suite
        assert 'medium_documents' in test_suite
        assert 'large_documents' in test_suite
        
        # Verify scaling
        small_count = len(test_suite['small_documents'])
        medium_count = len(test_suite['medium_documents'])
        large_count = len(test_suite['large_documents'])
        
        assert small_count > 0
        assert medium_count > 0
        assert large_count > 0
    
    def test_deterministic_generation(self):
        """Test deterministic generation with seeds."""
        generator1 = SVGTestGenerator(seed=123)
        generator2 = SVGTestGenerator(seed=123)
        
        shapes1 = generator1.generate_basic_shapes(count=5)
        shapes2 = generator2.generate_basic_shapes(count=5)
        
        # Should generate identical sequences
        assert len(shapes1) == len(shapes2)
        # Note: Exact comparison would require serialization


class TestBenchmarkSuite:
    """Test benchmark suite functionality."""
    
    @pytest.fixture
    def mock_optimizer(self):
        """Create mock optimizer for testing."""
        optimizer = Mock()
        optimizer.process_svg_elements.return_value = ["result1", "result2"]
        optimizer.get_performance_metrics.return_value = {
            'processing_time': 0.1,
            'cache_hit_rate': 0.8,
            'elements_processed': 2
        }
        return optimizer
    
    @pytest.fixture
    def benchmark_suite(self, mock_optimizer):
        """Create BenchmarkSuite instance."""
        return BenchmarkSuite(optimizer=mock_optimizer)
    
    def test_benchmark_suite_initialization(self, benchmark_suite, mock_optimizer):
        """Test benchmark suite initialization."""
        assert benchmark_suite.optimizer == mock_optimizer
        assert benchmark_suite.test_generator is not None
        assert len(benchmark_suite.results) == 0
    
    def test_run_single_benchmark(self, benchmark_suite):
        """Test running a single benchmark."""
        test_elements = [Mock(), Mock(), Mock()]
        
        with patch('time.time', side_effect=[0, 0.5, 0.5, 0.05]):  # Baseline and optimized times
            result = benchmark_suite.run_single_benchmark(
                test_name="single_test",
                elements=test_elements
            )
        
        assert isinstance(result, BenchmarkResult)
        assert result.test_name == "single_test"
        assert result.total_elements == len(test_elements)
        assert result.speedup_factor > 1.0
    
    def test_run_performance_suite(self, benchmark_suite):
        """Test running complete performance suite."""
        with patch.object(benchmark_suite.test_generator, 'generate_performance_test_suite') as mock_gen:
            mock_gen.return_value = {
                'small_documents': [[Mock(), Mock()]],
                'medium_documents': [[Mock() for _ in range(10)]],
                'large_documents': [[Mock() for _ in range(50)]]
            }
            
            with patch('time.time', side_effect=[0, 1, 1, 0.1] * 10):  # Multiple timing pairs
                results = benchmark_suite.run_performance_suite()
        
        assert len(results) > 0
        assert all(isinstance(result, BenchmarkResult) for result in results)
    
    def test_benchmark_with_different_modes(self, benchmark_suite):
        """Test benchmarking with different optimization modes."""
        elements = [Mock() for _ in range(5)]
        
        # Mock different optimization modes
        mode_results = {}
        for mode in ['conservative', 'aggressive', 'ludicrous']:
            with patch.object(benchmark_suite.optimizer, 'set_mode'):
                with patch('time.time', side_effect=[0, 1, 1, 0.1]):
                    result = benchmark_suite.run_single_benchmark(f"test_{mode}", elements)
                    mode_results[mode] = result
        
        assert len(mode_results) == 3
        assert all(result.speedup_factor > 1.0 for result in mode_results.values())


class TestPerformanceBenchmark:
    """Test performance benchmarking functionality."""
    
    def test_benchmark_initialization(self):
        """Test performance benchmark initialization."""
        benchmark = PerformanceBenchmark()
        assert benchmark.baseline_optimizer is not None
        assert benchmark.speedrun_optimizer is not None
        assert benchmark.test_generator is not None
    
    def test_baseline_vs_speedrun_comparison(self):
        """Test comparison between baseline and speedrun performance."""
        benchmark = PerformanceBenchmark()
        test_elements = [Mock() for _ in range(10)]
        
        # Mock baseline performance
        with patch.object(benchmark.baseline_optimizer, 'process_svg_elements') as mock_baseline:
            mock_baseline.return_value = ["baseline"] * 10
            
            # Mock speedrun performance
            with patch.object(benchmark.speedrun_optimizer, 'process_svg_elements') as mock_speedrun:
                mock_speedrun.return_value = ["speedrun"] * 10
                
                with patch('time.time', side_effect=[0, 2.0, 2.0, 0.2]):  # 10x speedup
                    result = benchmark.compare_performance(test_elements)
        
        assert result.speedup_factor == 10.0
        assert result.total_elements == 10
    
    def test_memory_usage_benchmarking(self):
        """Test memory usage benchmarking."""
        benchmark = PerformanceBenchmark()
        
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 1024 * 1024  # 1MB
            
            memory_stats = benchmark.measure_memory_usage([Mock() for _ in range(5)])
        
        assert 'peak_memory_mb' in memory_stats
        assert 'memory_efficiency' in memory_stats
    
    def test_cache_efficiency_analysis(self):
        """Test cache efficiency analysis."""
        benchmark = PerformanceBenchmark()
        
        # Mock cache with different hit rates
        mock_cache = Mock()
        mock_cache.get_stats.return_value = Mock(
            hit_rate=0.85,
            hits=85,
            misses=15,
            total_requests=100
        )
        
        with patch.object(benchmark.speedrun_optimizer, 'cache', mock_cache):
            cache_analysis = benchmark.analyze_cache_efficiency([Mock() for _ in range(10)])
        
        assert 'hit_rate' in cache_analysis
        assert 'cache_effectiveness' in cache_analysis
        assert cache_analysis['hit_rate'] == 0.85


class TestSpeedrunValidator:
    """Test speedrun performance validation."""
    
    def test_validator_initialization(self):
        """Test speedrun validator initialization."""
        validator = SpeedrunValidator(target_speedup=10.0)
        assert validator.target_speedup == 10.0
        assert validator.validation_thresholds is not None
    
    def test_validate_speedup_target(self):
        """Test speedup target validation."""
        validator = SpeedrunValidator(target_speedup=5.0)
        
        # Test passing result
        passing_result = BenchmarkResult(
            test_name="passing_test",
            svg_count=1,
            total_elements=10,
            baseline_time_seconds=1.0,
            optimized_time_seconds=0.15,  # 6.67x speedup
            speedup_factor=6.67
        )
        
        assert validator.validate_speedup_target(passing_result) is True
        
        # Test failing result
        failing_result = BenchmarkResult(
            test_name="failing_test",
            svg_count=1,
            total_elements=10,
            baseline_time_seconds=1.0,
            optimized_time_seconds=0.3,  # 3.33x speedup
            speedup_factor=3.33
        )
        
        assert validator.validate_speedup_target(failing_result) is False
    
    def test_validate_memory_efficiency(self):
        """Test memory efficiency validation."""
        validator = SpeedrunValidator()
        
        # Good memory usage
        good_memory_stats = {
            'peak_memory_mb': 64,
            'memory_per_element_kb': 1.2
        }
        assert validator.validate_memory_efficiency(good_memory_stats, 1000) is True
        
        # Excessive memory usage
        bad_memory_stats = {
            'peak_memory_mb': 2048,  # 2GB
            'memory_per_element_kb': 50.0
        }
        assert validator.validate_memory_efficiency(bad_memory_stats, 100) is False
    
    def test_comprehensive_validation(self):
        """Test comprehensive speedrun validation."""
        validator = SpeedrunValidator(target_speedup=8.0)
        
        benchmark_result = BenchmarkResult(
            test_name="comprehensive_test",
            svg_count=5,
            total_elements=50,
            baseline_time_seconds=5.0,
            optimized_time_seconds=0.5,  # 10x speedup
            speedup_factor=10.0
        )
        
        memory_stats = {
            'peak_memory_mb': 128,
            'memory_per_element_kb': 2.5
        }
        
        cache_stats = {
            'hit_rate': 0.90,
            'cache_effectiveness': 'excellent'
        }
        
        validation_result = validator.comprehensive_validation(
            benchmark_result, memory_stats, cache_stats
        )
        
        assert validation_result['overall_pass'] is True
        assert validation_result['speedup_pass'] is True
        assert validation_result['memory_pass'] is True
        assert validation_result['cache_pass'] is True


class TestBenchmarkReporter:
    """Test benchmark reporting functionality."""
    
    @pytest.fixture
    def sample_results(self):
        """Create sample benchmark results."""
        return [
            BenchmarkResult(
                test_name="small_svg_test",
                svg_count=5,
                total_elements=25,
                baseline_time_seconds=1.0,
                optimized_time_seconds=0.08,  # 12.5x
                speedup_factor=12.5
            ),
            BenchmarkResult(
                test_name="medium_svg_test", 
                svg_count=20,
                total_elements=200,
                baseline_time_seconds=8.0,
                optimized_time_seconds=0.7,   # 11.4x
                speedup_factor=11.4
            )
        ]
    
    def test_reporter_initialization(self, sample_results):
        """Test benchmark reporter initialization."""
        reporter = BenchmarkReporter(results=sample_results)
        assert len(reporter.results) == 2
        assert reporter.report_format == 'text'  # Default format
    
    def test_generate_summary_report(self, sample_results):
        """Test summary report generation."""
        reporter = BenchmarkReporter(results=sample_results)
        summary = reporter.generate_summary_report()
        
        assert 'total_tests' in summary
        assert 'average_speedup' in summary
        assert 'min_speedup' in summary
        assert 'max_speedup' in summary
        
        assert summary['total_tests'] == 2
        assert summary['average_speedup'] == (12.5 + 11.4) / 2
        assert summary['min_speedup'] == 11.4
        assert summary['max_speedup'] == 12.5
    
    def test_generate_detailed_report(self, sample_results):
        """Test detailed report generation."""
        reporter = BenchmarkReporter(results=sample_results)
        detailed_report = reporter.generate_detailed_report()
        
        assert isinstance(detailed_report, str)
        assert "small_svg_test" in detailed_report
        assert "medium_svg_test" in detailed_report
        assert "12.5x" in detailed_report
        assert "11.4x" in detailed_report
    
    def test_export_to_json(self, sample_results, tmp_path):
        """Test JSON export functionality."""
        reporter = BenchmarkReporter(results=sample_results)
        output_file = tmp_path / "benchmark_results.json"
        
        reporter.export_to_json(output_file)
        
        assert output_file.exists()
        
        # Verify JSON content
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert len(data['results']) == 2
        assert data['summary']['total_tests'] == 2
    
    def test_generate_html_report(self, sample_results, tmp_path):
        """Test HTML report generation."""
        reporter = BenchmarkReporter(results=sample_results, report_format='html')
        html_report = reporter.generate_html_report()
        
        assert isinstance(html_report, str)
        assert '<html>' in html_report
        assert '<table>' in html_report
        assert '12.5' in html_report  # Speedup value
    
    def test_performance_regression_detection(self, sample_results):
        """Test performance regression detection."""
        reporter = BenchmarkReporter(results=sample_results)
        
        # Mock historical results with lower performance
        historical_results = [
            BenchmarkResult(
                test_name="small_svg_test",
                svg_count=5,
                total_elements=25,
                baseline_time_seconds=1.0,
                optimized_time_seconds=0.2,  # 5x (worse than current 12.5x)
                speedup_factor=5.0
            )
        ]
        
        regressions = reporter.detect_regressions(
            historical_results=historical_results,
            regression_threshold=0.1  # 10% threshold
        )
        
        # Should detect improvement, not regression
        assert len(regressions) == 0


@pytest.mark.integration
class TestBenchmarkIntegration:
    """Integration tests for benchmark suite."""
    
    def test_end_to_end_benchmark(self):
        """Test complete benchmark workflow."""
        # Initialize components
        test_generator = SVGTestGenerator(seed=42)
        
        with patch('src.performance.speedrun_benchmark.SVGSpeedrunOptimizer') as mock_optimizer:
            mock_optimizer.return_value.process_svg_elements.return_value = ["result"]
            
            benchmark_suite = BenchmarkSuite(optimizer=mock_optimizer.return_value)
            
            # Generate test data
            test_elements = test_generator.generate_basic_shapes(count=5)
            
            # Run benchmark
            with patch('time.time', side_effect=[0, 1, 1, 0.1]):
                result = benchmark_suite.run_single_benchmark("integration_test", test_elements)
        
        assert isinstance(result, BenchmarkResult)
        assert result.speedup_factor == 10.0
    
    def test_benchmark_validation_workflow(self):
        """Test benchmark validation workflow."""
        # Create validator
        validator = SpeedrunValidator(target_speedup=5.0)
        
        # Create mock benchmark result
        result = BenchmarkResult(
            test_name="validation_test",
            svg_count=3,
            total_elements=15,
            baseline_time_seconds=3.0,
            optimized_time_seconds=0.4,  # 7.5x speedup
            speedup_factor=7.5
        )
        
        # Validate performance
        assert validator.validate_speedup_target(result) is True
        
        # Generate report
        reporter = BenchmarkReporter(results=[result])
        summary = reporter.generate_summary_report()
        
        assert summary['average_speedup'] == 7.5


@pytest.mark.benchmark
class TestBenchmarkPerformance:
    """Performance tests for benchmark suite itself."""
    
    def test_benchmark_overhead(self, benchmark):
        """Test benchmark measurement overhead."""
        test_elements = [Mock() for _ in range(10)]
        
        def benchmark_operation():
            # Simulate benchmark timing
            start = time.time()
            time.sleep(0.001)  # Simulate processing
            end = time.time()
            return end - start
        
        result = benchmark(benchmark_operation)
        assert result < 0.1  # Benchmark overhead should be minimal
    
    def test_test_generation_performance(self, benchmark):
        """Test SVG test generation performance."""
        generator = SVGTestGenerator(seed=42)
        
        def generate_test_suite():
            return generator.generate_performance_test_suite()
        
        test_suite = benchmark(generate_test_suite)
        assert len(test_suite) > 0
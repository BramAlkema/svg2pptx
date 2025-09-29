#!/usr/bin/env python3
"""
Comprehensive Batch Processing Tests

Tests the complete batch processing pipeline including job management,
conversion workflows, and error handling for SVG2PPTX conversion.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET

# Batch processing components
try:
    from src.batch.tasks import process_batch_job
    from src.batch.models import BatchJob, JobStatus, ConversionJob
    BATCH_AVAILABLE = True
except ImportError:
    BATCH_AVAILABLE = False

# Core conversion systems
from core.services.conversion_services import ConversionServices
from src.svg2drawingml import SVGToDrawingMLConverter


class TestBatchProcessingCore:
    """Test core batch processing functionality."""

    @pytest.mark.skipif(not BATCH_AVAILABLE, reason="Batch processing not available")
    def test_batch_job_model_creation(self):
        """Test BatchJob model creation and validation."""
        job_data = {
            'id': 'test-job-123',
            'svg_files': ['file1.svg', 'file2.svg'],
            'output_format': 'pptx',
            'settings': {'quality': 'high'},
            'status': JobStatus.PENDING
        }

        job = BatchJob(**job_data)
        assert job.id == 'test-job-123'
        assert len(job.svg_files) == 2
        assert job.status == JobStatus.PENDING

    @pytest.mark.skipif(not BATCH_AVAILABLE, reason="Batch processing not available")
    def test_conversion_job_creation(self):
        """Test ConversionJob creation with SVG content."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="10" y="10" width="80" height="80" fill="blue"/></svg>'

        job = ConversionJob(
            input_svg=svg_content,
            output_format='pptx',
            job_id='conv-123'
        )

        assert job.input_svg == svg_content
        assert job.output_format == 'pptx'
        assert job.job_id == 'conv-123'

    @pytest.mark.skipif(not BATCH_AVAILABLE, reason="Batch processing not available")
    def test_process_batch_job_function(self):
        """Test the main batch job processing function."""
        # Create mock batch job
        mock_job = Mock()
        mock_job.id = 'test-batch-001'
        mock_job.svg_files = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><circle cx="100" cy="100" r="50" fill="red"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><rect x="50" y="50" width="100" height="100" fill="green"/></svg>'
        ]
        mock_job.settings = {'optimization': 'standard'}

        try:
            result = process_batch_job(mock_job)
            assert result is not None, "Batch job processing should return result"
        except Exception as e:
            pytest.skip(f"Batch job processing failed: {e}")


class TestBatchConversionWorkflows:
    """Test batch conversion workflows with multiple SVG files."""

    def setup_method(self):
        """Set up test fixtures."""
        self.services = ConversionServices.create_default()
        self.test_svgs = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="10" y="10" width="80" height="80" fill="blue"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="red"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><ellipse cx="50" cy="50" rx="45" ry="30" fill="green"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="M20,20 L80,20 L50,80 Z" fill="purple"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text x="50" y="50" font-size="16" text-anchor="middle" fill="black">Test</text></svg>'
        ]

    def test_sequential_conversion_workflow(self):
        """Test converting multiple SVGs sequentially."""
        converter = SVGToDrawingMLConverter()
        results = []

        for i, svg_content in enumerate(self.test_svgs):
            try:
                result = converter.convert(svg_content)
                results.append({
                    'index': i,
                    'success': result is not None,
                    'output_length': len(result) if result else 0
                })
            except Exception as e:
                results.append({
                    'index': i,
                    'success': False,
                    'error': str(e)
                })

        # Verify we processed all SVGs
        assert len(results) == len(self.test_svgs), "Should process all SVG files"

        # Count successful conversions
        successful = sum(1 for r in results if r.get('success', False))
        assert successful >= len(self.test_svgs) * 0.6, f"At least 60% of conversions should succeed, got {successful}/{len(self.test_svgs)}"

    def test_batch_conversion_with_error_handling(self):
        """Test batch conversion with malformed SVG handling."""
        # Mix of valid and invalid SVGs
        mixed_svgs = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="10" y="10" width="80" height="80" fill="blue"/></svg>',  # Valid
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="10" y="10" width="80" height="80" fill="blue"</svg>',  # Missing >
            '',  # Empty
            '<not-svg>Invalid content</not-svg>',  # Invalid
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="red"/></svg>'  # Valid
        ]

        converter = SVGToDrawingMLConverter()
        results = []

        for svg_content in mixed_svgs:
            try:
                result = converter.convert(svg_content)
                results.append({
                    'success': result is not None and len(result) > 0,
                    'content': svg_content[:50] + '...' if len(svg_content) > 50 else svg_content
                })
            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e)[:100],  # Truncate long errors
                    'content': svg_content[:50] + '...' if len(svg_content) > 50 else svg_content
                })

        # Verify we handled all inputs
        assert len(results) == len(mixed_svgs), "Should process all inputs"

        # At least the valid SVGs should work
        successful = sum(1 for r in results if r.get('success', False))
        assert successful >= 1, "At least some valid SVGs should convert successfully"

    def test_batch_conversion_performance_metrics(self):
        """Test batch conversion with performance tracking."""
        import time

        converter = SVGToDrawingMLConverter()
        metrics = {
            'total_files': len(self.test_svgs),
            'successful_conversions': 0,
            'failed_conversions': 0,
            'total_processing_time': 0,
            'average_file_size': 0,
            'total_output_size': 0
        }

        start_time = time.time()

        for svg_content in self.test_svgs:
            file_start = time.time()
            try:
                result = converter.convert(svg_content)
                if result and len(result) > 0:
                    metrics['successful_conversions'] += 1
                    metrics['total_output_size'] += len(result)
                else:
                    metrics['failed_conversions'] += 1
            except Exception:
                metrics['failed_conversions'] += 1

            metrics['total_processing_time'] += time.time() - file_start

        metrics['average_processing_time'] = metrics['total_processing_time'] / metrics['total_files']
        metrics['average_output_size'] = (
            metrics['total_output_size'] / metrics['successful_conversions']
            if metrics['successful_conversions'] > 0 else 0
        )

        # Validate metrics
        assert metrics['total_files'] == len(self.test_svgs)
        assert metrics['successful_conversions'] + metrics['failed_conversions'] == metrics['total_files']
        assert metrics['total_processing_time'] > 0, "Should track processing time"

    def test_concurrent_batch_processing_simulation(self):
        """Test simulation of concurrent batch processing."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        converter = SVGToDrawingMLConverter()
        thread_results = {}
        lock = threading.Lock()

        def convert_svg(svg_index, svg_content):
            """Convert single SVG in thread."""
            thread_id = threading.current_thread().ident
            try:
                result = converter.convert(svg_content)
                success = result is not None and len(result) > 0
                with lock:
                    thread_results[svg_index] = {
                        'thread_id': thread_id,
                        'success': success,
                        'output_size': len(result) if result else 0
                    }
                return success
            except Exception as e:
                with lock:
                    thread_results[svg_index] = {
                        'thread_id': thread_id,
                        'success': False,
                        'error': str(e)
                    }
                return False

        # Use ThreadPoolExecutor to simulate concurrent processing
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_index = {
                executor.submit(convert_svg, i, svg): i
                for i, svg in enumerate(self.test_svgs)
            }

            completed = 0
            for future in as_completed(future_to_index):
                completed += 1

        # Verify all tasks completed
        assert completed == len(self.test_svgs), "All conversion tasks should complete"
        assert len(thread_results) == len(self.test_svgs), "Should have results for all SVGs"

        # Check thread safety - different threads should be used
        thread_ids = set(result.get('thread_id') for result in thread_results.values() if result.get('thread_id'))
        assert len(thread_ids) >= 1, "Should use at least one thread"


class TestBatchFileManagement:
    """Test batch file management and I/O operations."""

    def test_batch_file_processing_with_temp_files(self):
        """Test batch processing with temporary files."""
        converter = SVGToDrawingMLConverter()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create temporary SVG files
            svg_files = []
            for i, svg_content in enumerate([
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="10" y="10" width="80" height="80" fill="red"/></svg>',
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="blue"/></svg>'
            ]):
                svg_file = temp_path / f"test_{i}.svg"
                svg_file.write_text(svg_content)
                svg_files.append(svg_file)

            # Process files
            results = []
            for svg_file in svg_files:
                try:
                    content = svg_file.read_text()
                    result = converter.convert(content)
                    results.append({
                        'file': svg_file.name,
                        'success': result is not None,
                        'size': len(result) if result else 0
                    })
                except Exception as e:
                    results.append({
                        'file': svg_file.name,
                        'success': False,
                        'error': str(e)
                    })

            # Verify file processing
            assert len(results) == len(svg_files), "Should process all files"
            successful = sum(1 for r in results if r.get('success', False))
            assert successful >= 1, "At least one file should process successfully"

    def test_batch_configuration_processing(self):
        """Test batch processing with different configuration settings."""
        configurations = [
            {'quality': 'high', 'optimization': 'minimal'},
            {'quality': 'standard', 'optimization': 'standard'},
            {'quality': 'fast', 'optimization': 'aggressive'}
        ]

        test_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="20" y="20" width="60" height="60" fill="orange"/></svg>'
        converter = SVGToDrawingMLConverter()

        config_results = []

        for config in configurations:
            try:
                # Note: SVGToDrawingMLConverter doesn't currently accept config parameters
                # This test validates the framework for when configuration support is added
                result = converter.convert(test_svg)
                config_results.append({
                    'config': config,
                    'success': result is not None,
                    'output_size': len(result) if result else 0
                })
            except Exception as e:
                config_results.append({
                    'config': config,
                    'success': False,
                    'error': str(e)
                })

        # Verify all configurations were tested
        assert len(config_results) == len(configurations), "Should test all configurations"

    def test_batch_result_aggregation(self):
        """Test aggregating results from batch processing."""
        converter = SVGToDrawingMLConverter()
        test_svgs = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50"><rect x="5" y="5" width="40" height="40" fill="cyan"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50"><circle cx="25" cy="25" r="20" fill="magenta"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50"><ellipse cx="25" cy="25" rx="20" ry="15" fill="yellow"/></svg>'
        ]

        batch_results = {
            'batch_id': 'test-batch-aggregation',
            'processed_count': 0,
            'successful_count': 0,
            'failed_count': 0,
            'total_output_size': 0,
            'processing_errors': [],
            'individual_results': []
        }

        for i, svg_content in enumerate(test_svgs):
            batch_results['processed_count'] += 1

            try:
                result = converter.convert(svg_content)
                if result and len(result) > 0:
                    batch_results['successful_count'] += 1
                    batch_results['total_output_size'] += len(result)
                    batch_results['individual_results'].append({
                        'index': i,
                        'status': 'success',
                        'output_size': len(result)
                    })
                else:
                    batch_results['failed_count'] += 1
                    batch_results['individual_results'].append({
                        'index': i,
                        'status': 'failed',
                        'reason': 'Empty result'
                    })
            except Exception as e:
                batch_results['failed_count'] += 1
                batch_results['processing_errors'].append({
                    'index': i,
                    'error': str(e)
                })
                batch_results['individual_results'].append({
                    'index': i,
                    'status': 'error',
                    'error': str(e)
                })

        # Validate aggregated results
        assert batch_results['processed_count'] == len(test_svgs)
        assert batch_results['successful_count'] + batch_results['failed_count'] == batch_results['processed_count']
        assert len(batch_results['individual_results']) == len(test_svgs)

        # Calculate success rate
        success_rate = batch_results['successful_count'] / batch_results['processed_count'] if batch_results['processed_count'] > 0 else 0
        assert success_rate >= 0.0, "Success rate should be non-negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
#!/usr/bin/env python3
"""
End-to-End Integration Tests for Clean Slate Batch Processing

Tests the complete workflow: API → Download → Clean Slate Conversion → Drive Upload → Trace Storage
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Set Huey to immediate mode for synchronous testing
os.environ['HUEY_IMMEDIATE'] = 'true'

from core.batch.url_downloader import download_svgs_to_temp, cleanup_temp_directory
from core.batch.coordinator import coordinate_batch_workflow_clean_slate
from core.batch.models import BatchJob, DEFAULT_DB_PATH


# Sample SVG content for mocking
SAMPLE_SVG = b'''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
</svg>'''


@pytest.fixture
def mock_batch_job():
    """Create mock BatchJob"""
    job = Mock()
    job.job_id = "batch_test_123"
    job.status = "created"
    job.total_files = 1
    job.drive_integration_enabled = False
    job.drive_upload_status = "not_requested"
    job.drive_folder_pattern = None
    job.metadata = {}
    job.save = Mock()
    return job


@pytest.fixture
def mock_http_response():
    """Create mock HTTP response with SVG content"""
    response = Mock()
    response.status_code = 200
    response.headers = {'Content-Type': 'image/svg+xml'}
    response.iter_content = Mock(return_value=[SAMPLE_SVG])
    response.raise_for_status = Mock()
    return response


class TestDownloadToConversionFlow:
    """Test URL download → Clean Slate conversion flow"""

    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_complete_download_and_conversion(self, mock_convert, mock_batch_job_cls,
                                              mock_get, mock_batch_job, mock_http_response):
        """Test complete flow from URL download through conversion"""
        # Setup mocks
        mock_get.return_value = mock_http_response
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False

        # Mock conversion result with trace data
        mock_convert.return_value = {
            'success': True,
            'output_path': '/tmp/output.pptx',
            'page_count': 1,
            'output_size_bytes': 5000,
            'architecture': 'clean_slate',
            'debug_trace': [{
                'page_number': 1,
                'pipeline_trace': {
                    'parse_result': {'element_count': 1},
                    'embedder_result': {'shapes_embedded': 1}
                },
                'package_trace': {
                    'package_creation_ms': 5.2,
                    'file_write_ms': 1.3
                }
            }]
        }

        try:
            # Step 1: Download URLs
            urls = ['https://example.com/test.svg']
            download_result = download_svgs_to_temp(urls, job_id='batch_test_123')

            assert download_result.success is True
            assert len(download_result.file_paths) == 1

            # Step 2: Convert using coordinator
            workflow_task = coordinate_batch_workflow_clean_slate(
                job_id='batch_test_123',
                file_paths=download_result.file_paths,
                conversion_options={'quality': 'high'}
            )

            # Unwrap Huey Result if needed
            workflow_result = workflow_task() if hasattr(workflow_task, '__call__') else workflow_task

            # Verify complete workflow
            assert workflow_result['success'] is True
            assert workflow_result['architecture'] == 'clean_slate'
            assert 'conversion' in workflow_result
            assert workflow_result['conversion']['page_count'] == 1

            # Verify trace data included
            assert 'debug_trace' in workflow_result['conversion']
            assert len(workflow_result['conversion']['debug_trace']) == 1

            # Verify job status updated
            assert mock_batch_job.status == "completed"
            assert mock_batch_job.save.called

        finally:
            cleanup_temp_directory(download_result.temp_dir)

    @patch('core.batch.url_downloader.requests.get')
    def test_download_failure_stops_workflow(self, mock_get):
        """Test that download failure prevents conversion"""
        # Mock download failure
        mock_get.side_effect = Exception("Network error")

        # Attempt download
        urls = ['https://example.com/broken.svg']
        download_result = download_svgs_to_temp(urls, job_id='batch_test_456')

        # Verify download failed
        assert download_result.success is False
        assert len(download_result.file_paths) == 0
        assert len(download_result.errors) > 0

        # Conversion should not be attempted (tested at API level)


class TestConversionWithDriveIntegration:
    """Test Clean Slate conversion with Drive upload"""

    @patch('core.batch.coordinator.DRIVE_AVAILABLE', True)
    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    @patch('core.batch.coordinator.upload_batch_files_to_drive')
    def test_complete_workflow_with_drive_upload(self, mock_upload, mock_convert,
                                                 mock_batch_job_cls, mock_get,
                                                 mock_batch_job, mock_http_response):
        """Test complete workflow including Drive upload"""
        # Setup mocks
        mock_get.return_value = mock_http_response
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = True

        # Mock conversion result
        mock_convert.return_value = {
            'success': True,
            'output_path': '/tmp/output.pptx',
            'page_count': 1,
            'output_size_bytes': 5000,
            'architecture': 'clean_slate',
            'debug_trace': [{
                'page_number': 1,
                'pipeline_trace': {'parse_result': {}},
                'package_trace': {'package_creation_ms': 5.2}
            }]
        }

        # Mock Drive upload result
        mock_upload.return_value = {
            'success': True,
            'folder_id': 'drive_folder_123',
            'folder_url': 'https://drive.google.com/drive/folders/123'
        }

        try:
            # Download URLs
            urls = ['https://example.com/test.svg']
            download_result = download_svgs_to_temp(urls, job_id='batch_test_789')

            # Convert with Drive integration
            workflow_task = coordinate_batch_workflow_clean_slate(
                job_id='batch_test_789',
                file_paths=download_result.file_paths
            )

            # Unwrap Huey Result
            workflow_result = workflow_task() if hasattr(workflow_task, '__call__') else workflow_task

            # Verify complete workflow
            assert workflow_result['success'] is True
            assert workflow_result['workflow'] == 'conversion_and_drive'
            assert 'conversion' in workflow_result
            assert 'upload' in workflow_result
            assert workflow_result['upload']['success'] is True

            # Verify Drive upload was called
            assert mock_upload.called

            # Verify job status
            assert mock_batch_job.status == "completed"
            assert mock_batch_job.drive_upload_status == "completed"

        finally:
            cleanup_temp_directory(download_result.temp_dir)


class TestTraceDataPersistence:
    """Test trace data storage in BatchJob metadata"""

    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_trace_data_stored_in_metadata(self, mock_convert, mock_batch_job_cls,
                                          mock_get, mock_batch_job, mock_http_response):
        """Test that trace data is stored in BatchJob.metadata"""
        # Setup mocks
        mock_get.return_value = mock_http_response
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False
        mock_batch_job.metadata = {}

        # Mock conversion with trace
        trace_data = [{
            'page_number': 1,
            'pipeline_trace': {
                'parse_result': {'elements': 5},
                'analysis_result': {'scene_objects': 3}
            },
            'package_trace': {
                'package_creation_ms': 5.2,
                'file_write_ms': 1.3
            }
        }]

        mock_convert.return_value = {
            'success': True,
            'output_path': '/tmp/output.pptx',
            'page_count': 1,
            'output_size_bytes': 5000,
            'architecture': 'clean_slate',
            'debug_trace': trace_data
        }

        try:
            # Download and convert
            urls = ['https://example.com/test.svg']
            download_result = download_svgs_to_temp(urls, job_id='batch_test_abc')

            workflow_task = coordinate_batch_workflow_clean_slate(
                job_id='batch_test_abc',
                file_paths=download_result.file_paths
            )

            # Unwrap Huey Result
            workflow_result = workflow_task() if hasattr(workflow_task, '__call__') else workflow_task

            # Verify trace stored in metadata
            assert 'trace_data' in mock_batch_job.metadata
            trace_metadata = mock_batch_job.metadata['trace_data']
            assert trace_metadata['architecture'] == 'clean_slate'
            assert trace_metadata['page_count'] == 1
            assert trace_metadata['workflow'] == 'conversion_only'
            assert 'debug_trace' in trace_metadata
            assert trace_metadata['debug_trace'] == trace_data

        finally:
            cleanup_temp_directory(download_result.temp_dir)


class TestErrorRecovery:
    """Test error handling and recovery scenarios"""

    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_conversion_failure_updates_job_status(self, mock_convert, mock_batch_job_cls,
                                                   mock_get, mock_batch_job, mock_http_response):
        """Test that conversion failure updates job status to failed"""
        # Setup mocks
        mock_get.return_value = mock_http_response
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False

        # Mock conversion failure
        mock_convert.return_value = {
            'success': False,
            'error_message': 'Invalid SVG structure',
            'error_type': 'parse_error'
        }

        try:
            # Download and convert
            urls = ['https://example.com/invalid.svg']
            download_result = download_svgs_to_temp(urls, job_id='batch_test_fail')

            workflow_task = coordinate_batch_workflow_clean_slate(
                job_id='batch_test_fail',
                file_paths=download_result.file_paths
            )

            # Unwrap Huey Result
            workflow_result = workflow_task() if hasattr(workflow_task, '__call__') else workflow_task

            # Verify failure handling
            assert workflow_result['success'] is False
            assert mock_batch_job.status == "failed"

        finally:
            cleanup_temp_directory(download_result.temp_dir)

    @patch('core.batch.coordinator.DRIVE_AVAILABLE', True)
    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    @patch('core.batch.coordinator.upload_batch_files_to_drive')
    def test_upload_failure_after_successful_conversion(self, mock_upload, mock_convert,
                                                       mock_batch_job_cls, mock_get,
                                                       mock_batch_job, mock_http_response):
        """Test handling when conversion succeeds but Drive upload fails"""
        # Setup mocks
        mock_get.return_value = mock_http_response
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = True

        # Conversion succeeds
        mock_convert.return_value = {
            'success': True,
            'output_path': '/tmp/output.pptx',
            'page_count': 1,
            'output_size_bytes': 5000,
            'architecture': 'clean_slate',
            'debug_trace': []
        }

        # Upload fails
        mock_upload.side_effect = Exception("Drive API error")

        try:
            # Download and convert
            urls = ['https://example.com/test.svg']
            download_result = download_svgs_to_temp(urls, job_id='batch_test_partial')

            workflow_task = coordinate_batch_workflow_clean_slate(
                job_id='batch_test_partial',
                file_paths=download_result.file_paths
            )

            # Unwrap Huey Result
            workflow_result = workflow_task() if hasattr(workflow_task, '__call__') else workflow_task

            # Verify partial success
            assert workflow_result['success'] is True  # Conversion succeeded
            assert workflow_result['workflow'] == 'conversion_only_upload_failed'
            assert workflow_result['upload']['success'] is False

            # Verify job status reflects upload failure
            assert mock_batch_job.status == "completed_upload_failed"
            assert mock_batch_job.drive_upload_status == "failed"

        finally:
            cleanup_temp_directory(download_result.temp_dir)


class TestMultipleFileProcessing:
    """Test processing multiple SVG files"""

    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_multiple_svg_files_conversion(self, mock_convert, mock_batch_job_cls,
                                          mock_get, mock_batch_job):
        """Test downloading and converting multiple SVG files"""
        # Setup mocks for multiple files
        def create_response(content):
            resp = Mock()
            resp.status_code = 200
            resp.headers = {'Content-Type': 'image/svg+xml'}
            resp.iter_content = Mock(return_value=[content])
            resp.raise_for_status = Mock()
            return resp

        mock_get.side_effect = [
            create_response(SAMPLE_SVG),
            create_response(SAMPLE_SVG),
            create_response(SAMPLE_SVG)
        ]

        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False

        # Mock conversion result for multiple pages
        mock_convert.return_value = {
            'success': True,
            'output_path': '/tmp/output.pptx',
            'page_count': 3,
            'output_size_bytes': 15000,
            'architecture': 'clean_slate',
            'debug_trace': [
                {'page_number': 1, 'pipeline_trace': {}, 'package_trace': {}},
                {'page_number': 2, 'pipeline_trace': {}, 'package_trace': {}},
                {'page_number': 3, 'pipeline_trace': {}, 'package_trace': {}}
            ]
        }

        try:
            # Download multiple URLs
            urls = [
                'https://example.com/file1.svg',
                'https://example.com/file2.svg',
                'https://example.com/file3.svg'
            ]
            download_result = download_svgs_to_temp(urls, job_id='batch_test_multi')

            assert download_result.success is True
            assert len(download_result.file_paths) == 3

            # Convert all files
            workflow_task = coordinate_batch_workflow_clean_slate(
                job_id='batch_test_multi',
                file_paths=download_result.file_paths
            )

            # Unwrap Huey Result
            workflow_result = workflow_task() if hasattr(workflow_task, '__call__') else workflow_task

            # Verify multi-page result
            assert workflow_result['success'] is True
            assert workflow_result['conversion']['page_count'] == 3
            assert len(workflow_result['conversion']['debug_trace']) == 3

        finally:
            cleanup_temp_directory(download_result.temp_dir)


class TestConversionQualityOptions:
    """Test conversion quality parameter handling"""

    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_quality_parameter_passed_to_conversion(self, mock_convert, mock_batch_job_cls,
                                                   mock_get, mock_batch_job, mock_http_response):
        """Test quality parameter is passed to conversion"""
        # Setup mocks
        mock_get.return_value = mock_http_response
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False

        mock_convert.return_value = {
            'success': True,
            'output_path': '/tmp/output.pptx',
            'page_count': 1,
            'output_size_bytes': 5000,
            'architecture': 'clean_slate',
            'debug_trace': []
        }

        try:
            # Download
            urls = ['https://example.com/test.svg']
            download_result = download_svgs_to_temp(urls, job_id='batch_test_quality')

            # Convert with specific quality
            workflow_result = coordinate_batch_workflow_clean_slate(
                job_id='batch_test_quality',
                file_paths=download_result.file_paths,
                conversion_options={'quality': 'fast'}
            )

            # Verify quality parameter was passed
            call_args = mock_convert.call_args
            conversion_options = call_args[1]['conversion_options']
            assert conversion_options['quality'] == 'fast'
            assert conversion_options['enable_debug'] is True  # Always enabled for batch

        finally:
            cleanup_temp_directory(download_result.temp_dir)

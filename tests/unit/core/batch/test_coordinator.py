#!/usr/bin/env python3
"""
Unit Tests for Batch Coordinator

Tests the Clean Slate batch coordinator that orchestrates
conversion + Drive upload workflows.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Set Huey to immediate mode for testing
os.environ['HUEY_IMMEDIATE'] = 'true'

from core.batch.coordinator import (
    coordinate_batch_workflow_clean_slate,
    get_coordinator_info,
    CoordinatorError
)


@pytest.fixture
def mock_batch_job():
    """Create mock BatchJob"""
    job = Mock()
    job.job_id = "test_job_123"
    job.status = "created"
    job.total_files = 3
    job.drive_integration_enabled = False
    job.drive_upload_status = "not_requested"
    job.drive_folder_pattern = None
    job.metadata = {}  # Must be dict, not Mock
    job.save = Mock()
    return job


@pytest.fixture
def mock_conversion_result():
    """Create mock conversion result"""
    return {
        'success': True,
        'output_path': '/tmp/test.pptx',
        'page_count': 3,
        'output_size_bytes': 6432,
        'architecture': 'clean_slate',
        'debug_trace': [
            {
                'page_number': 1,
                'pipeline_trace': {
                    'parse_result': {},
                    'embedder_result': {}
                }
            }
        ]
    }


@pytest.fixture
def mock_upload_result():
    """Create mock upload result"""
    return {
        'success': True,
        'folder_id': 'drive_folder_123',
        'folder_url': 'https://drive.google.com/drive/folders/123',
        'uploaded_files': [{
            'name': 'test_job_123.pptx',
            'id': 'file_id_123'
        }]
    }


class TestCoordinatorInfo:
    """Test coordinator information"""

    def test_get_coordinator_info(self):
        """Test coordinator info returns correct structure"""
        info = get_coordinator_info()

        assert info['coordinator'] == 'clean_slate_batch'
        assert info['architecture'] == 'clean_slate'
        assert 'capabilities' in info
        assert 'workflow_stages' in info
        assert 'trace_data_available' in info

    def test_coordinator_capabilities(self):
        """Test coordinator capabilities are correct"""
        info = get_coordinator_info()
        caps = info['capabilities']

        assert caps['multi_svg_conversion'] is True
        assert caps['e2e_tracing'] is True
        assert caps['status_tracking'] is True
        assert caps['error_recovery'] is True


class TestCoordinatorConversionOnly:
    """Test coordinator with conversion only (no Drive)"""

    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_successful_conversion_no_drive(self, mock_convert, mock_batch_job_cls,
                                           mock_batch_job, mock_conversion_result):
        """Test successful conversion without Drive upload"""
        # Setup mocks
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False
        mock_convert.return_value = mock_conversion_result

        # Execute
        task = coordinate_batch_workflow_clean_slate(
            job_id="test_job_123",
            file_paths=['/tmp/test1.svg', '/tmp/test2.svg'],
            conversion_options={'quality': 'high'}
        )
        # Unwrap Huey Result
        result = task() if hasattr(task, '__call__') else task

        # Verify
        assert result['success'] is True
        assert result['job_id'] == "test_job_123"
        assert result['architecture'] == 'clean_slate'
        assert result['workflow'] == 'conversion_only'
        assert 'conversion' in result
        assert 'upload' not in result

        # Verify job status updated
        assert mock_batch_job.status == "completed"
        assert mock_batch_job.save.called

    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_job_status_progression(self, mock_convert, mock_batch_job_cls,
                                   mock_batch_job, mock_conversion_result):
        """Test job status updates through workflow"""
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False
        mock_convert.return_value = mock_conversion_result

        coordinate_batch_workflow_clean_slate(
            job_id="test_job_123",
            file_paths=['/tmp/test.svg']
        )

        # Verify status progression
        assert mock_batch_job.save.call_count >= 2
        # First call: status = "processing"
        # Second call: status = "completed"


class TestCoordinatorWithDrive:
    """Test coordinator with Drive integration"""

    @patch('core.batch.coordinator.DRIVE_AVAILABLE', True)
    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    @patch('core.batch.coordinator.upload_batch_files_to_drive')
    def test_successful_conversion_and_drive_upload(self, mock_upload, mock_convert,
                                                   mock_batch_job_cls, mock_batch_job,
                                                   mock_conversion_result, mock_upload_result):
        """Test successful conversion with Drive upload"""
        # Setup mocks
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = True
        mock_convert.return_value = mock_conversion_result
        mock_upload.return_value = mock_upload_result

        # Execute
        task = coordinate_batch_workflow_clean_slate(
            job_id="test_job_123",
            file_paths=['/tmp/test.svg'],
            conversion_options={'generate_previews': True}
        )
        # Unwrap Huey Result
        result = task() if hasattr(task, '__call__') else task

        # Verify
        assert result['success'] is True
        assert result['workflow'] == 'conversion_and_drive'
        assert 'conversion' in result
        assert 'upload' in result
        assert result['upload']['success'] is True

        # Verify upload was called
        assert mock_upload.called
        # Verify job status
        assert mock_batch_job.status == "completed"
        assert mock_batch_job.drive_upload_status == "completed"

    @patch('core.batch.coordinator.DRIVE_AVAILABLE', True)
    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    @patch('core.batch.coordinator.upload_batch_files_to_drive')
    def test_conversion_success_upload_failure(self, mock_upload, mock_convert,
                                              mock_batch_job_cls, mock_batch_job,
                                              mock_conversion_result):
        """Test conversion succeeds but upload fails"""
        # Setup mocks
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = True
        mock_convert.return_value = mock_conversion_result
        mock_upload.side_effect = Exception("Drive API error")

        # Execute
        task = coordinate_batch_workflow_clean_slate(
            job_id="test_job_123",
            file_paths=['/tmp/test.svg']
        )
        # Unwrap Huey Result
        result = task() if hasattr(task, '__call__') else task

        # Verify - conversion succeeded
        assert result['success'] is True  # Overall success because conversion worked
        assert result['workflow'] == 'conversion_only_upload_failed'
        assert result['upload']['success'] is False

        # Verify job status reflects upload failure
        assert mock_batch_job.status == "completed_upload_failed"
        assert mock_batch_job.drive_upload_status == "failed"


class TestCoordinatorErrorHandling:
    """Test coordinator error handling"""

    @patch('core.batch.coordinator.BatchJob')
    def test_job_not_found(self, mock_batch_job_cls):
        """Test handling of non-existent job"""
        mock_batch_job_cls.get_by_id.return_value = None

        task = coordinate_batch_workflow_clean_slate(
            job_id="nonexistent_job",
            file_paths=['/tmp/test.svg']
        )
        # Unwrap Huey Result
        result = task() if hasattr(task, '__call__') else task

        assert result['success'] is False
        assert result['error_type'] == 'job_not_found'
        assert 'not found' in result['error_message']

    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_conversion_failure(self, mock_convert, mock_batch_job_cls, mock_batch_job):
        """Test handling of conversion failure"""
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False

        # Mock conversion failure
        mock_convert.return_value = {
            'success': False,
            'error_message': 'Invalid SVG content',
            'error_type': 'parse_error'
        }

        task = coordinate_batch_workflow_clean_slate(
            job_id="test_job_123",
            file_paths=['/tmp/invalid.svg']
        )
        # Unwrap Huey Result
        result = task() if hasattr(task, '__call__') else task

        assert result['success'] is False
        assert mock_batch_job.status == "failed"

    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_unexpected_exception_handling(self, mock_convert, mock_batch_job_cls,
                                          mock_batch_job):
        """Test handling of unexpected exceptions"""
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_convert.side_effect = Exception("Unexpected error")

        task = coordinate_batch_workflow_clean_slate(
            job_id="test_job_123",
            file_paths=['/tmp/test.svg']
        )
        # Unwrap Huey Result
        result = task() if hasattr(task, '__call__') else task

        assert result['success'] is False
        assert 'error_message' in result
        assert mock_batch_job.status == "failed"


class TestCoordinatorTracing:
    """Test coordinator trace aggregation"""

    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_trace_data_included(self, mock_convert, mock_batch_job_cls,
                                mock_batch_job, mock_conversion_result):
        """Test that trace data is included in result"""
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False
        mock_convert.return_value = mock_conversion_result

        task = coordinate_batch_workflow_clean_slate(
            job_id="test_job_123",
            file_paths=['/tmp/test.svg']
        )
        # Unwrap Huey Result
        result = task() if hasattr(task, '__call__') else task

        # Verify trace data passed through
        assert 'conversion' in result
        assert 'debug_trace' in result['conversion']

    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_debug_always_enabled_for_batch(self, mock_convert, mock_batch_job_cls,
                                           mock_batch_job, mock_conversion_result):
        """Test that debug is always enabled for batch jobs"""
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False
        mock_convert.return_value = mock_conversion_result

        coordinate_batch_workflow_clean_slate(
            job_id="test_job_123",
            file_paths=['/tmp/test.svg'],
            conversion_options={'enable_debug': False}  # Try to disable
        )

        # Verify conversion was called with debug=True regardless
        call_args = mock_convert.call_args
        conversion_options = call_args[1]['conversion_options']
        assert conversion_options['enable_debug'] is True


class TestCoordinatorFileHandling:
    """Test coordinator file path handling"""

    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_output_path_creation(self, mock_convert, mock_batch_job_cls,
                                 mock_batch_job, mock_conversion_result):
        """Test that output path is created correctly"""
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False
        mock_convert.return_value = mock_conversion_result

        coordinate_batch_workflow_clean_slate(
            job_id="test_job_456",
            file_paths=['/tmp/test.svg']
        )

        # Verify output path includes job_id
        call_args = mock_convert.call_args
        output_path = call_args[1]['output_path']
        assert 'test_job_456' in output_path
        assert output_path.endswith('.pptx')


class TestCoordinatorConversionOptions:
    """Test coordinator conversion options handling"""

    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_quality_option_propagation(self, mock_convert, mock_batch_job_cls,
                                       mock_batch_job, mock_conversion_result):
        """Test quality option is passed to conversion"""
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False
        mock_convert.return_value = mock_conversion_result

        coordinate_batch_workflow_clean_slate(
            job_id="test_job_123",
            file_paths=['/tmp/test.svg'],
            conversion_options={'quality': 'fast'}
        )

        call_args = mock_convert.call_args
        conversion_options = call_args[1]['conversion_options']
        assert conversion_options['quality'] == 'fast'

    @patch('core.batch.coordinator.BatchJob')
    @patch('core.batch.coordinator.convert_multiple_svgs_clean_slate')
    def test_default_quality_option(self, mock_convert, mock_batch_job_cls,
                                   mock_batch_job, mock_conversion_result):
        """Test default quality is 'high'"""
        mock_batch_job_cls.get_by_id.return_value = mock_batch_job
        mock_batch_job.drive_integration_enabled = False
        mock_convert.return_value = mock_conversion_result

        coordinate_batch_workflow_clean_slate(
            job_id="test_job_123",
            file_paths=['/tmp/test.svg']
        )

        call_args = mock_convert.call_args
        conversion_options = call_args[1]['conversion_options']
        assert conversion_options['quality'] == 'high'

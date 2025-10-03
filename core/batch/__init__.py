#!/usr/bin/env python3
"""
Clean Slate Batch Processing

Huey-based batch conversion tasks using Clean Slate architecture.
Provides E2E tracing and modern IR → Policy → Map → Embed pipeline.
"""

from .tasks import (
    convert_multiple_svgs_clean_slate,
    convert_multipage_svg_clean_slate,
    process_directory_to_pptx,
    process_zip_to_pptx,
    CleanSlateConversionError
)

from .coordinator import (
    coordinate_batch_workflow_clean_slate,
    get_coordinator_info,
    CoordinatorError
)

from .url_downloader import (
    download_svgs_to_temp,
    cleanup_temp_directory,
    get_downloader_info,
    DownloadError,
    DownloadResult
)

from .models import (
    CleanSlateBatchJob
)

__all__ = [
    # Conversion tasks
    'convert_multiple_svgs_clean_slate',
    'convert_multipage_svg_clean_slate',
    'process_directory_to_pptx',
    'process_zip_to_pptx',
    'CleanSlateConversionError',

    # Coordinator
    'coordinate_batch_workflow_clean_slate',
    'get_coordinator_info',
    'CoordinatorError',

    # URL Downloader
    'download_svgs_to_temp',
    'cleanup_temp_directory',
    'get_downloader_info',
    'DownloadError',
    'DownloadResult',

    # Models (Clean Slate only - no legacy, in-memory)
    'CleanSlateBatchJob'
]

#!/usr/bin/env python3
"""
Clean Slate Batch Tasks

Huey tasks for batch SVG conversion using Clean Slate architecture.
Provides E2E tracing and modern IR → Policy → Map → Embed pipeline.
"""

import logging
import tempfile
import zipfile
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

# Import Huey instance directly
from huey import SqliteHuey
import os

# Create Huey instance (same config as legacy)
DATA_DIR = Path(os.getenv('HUEY_DATA_DIR', './data'))
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / 'svg2pptx_jobs.db'

huey = SqliteHuey(
    name='svg2pptx_clean_slate',
    filename=str(DB_PATH),
    immediate=os.getenv('HUEY_IMMEDIATE', 'false').lower() == 'true',
    results=True,
    store_none=False,
    utc=True
)

# Clean Slate imports
from ..multipage.converter import CleanSlateMultiPageConverter, PageSource
from ..pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


class CleanSlateConversionError(Exception):
    """Custom exception for Clean Slate conversion errors."""
    pass


@huey.task(retries=3, retry_delay=60)
def convert_multiple_svgs_clean_slate(
    file_paths: List[str],
    output_path: str,
    conversion_options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Convert multiple SVG files to multi-slide PPTX using Clean Slate.

    Args:
        file_paths: List of SVG file paths
        output_path: Output PPTX path
        conversion_options: Optional conversion parameters including:
            - enable_debug: bool (default True) - Enable E2E tracing
            - quality: str - Quality preset (default 'high')
            - slide_width: float - Slide width in inches (default 10.0)
            - slide_height: float - Slide height in inches (default 7.5)

    Returns:
        Dictionary with conversion result and E2E trace data
    """
    try:
        options = conversion_options or {}
        enable_debug = options.get('enable_debug', True)

        logger.info(f"Clean Slate: Converting {len(file_paths)} SVG files to {output_path}")

        # Validate inputs
        if not file_paths:
            raise CleanSlateConversionError("No SVG files provided")

        for file_path in file_paths:
            if not Path(file_path).exists():
                raise CleanSlateConversionError(f"File not found: {file_path}")

        # Configure Clean Slate pipeline
        from ..pipeline.config import QualityLevel

        quality_map = {
            'fast': QualityLevel.FAST,
            'balanced': QualityLevel.BALANCED,
            'high': QualityLevel.HIGH
        }

        pipeline_config = PipelineConfig(
            enable_debug=enable_debug,  # ✅ E2E TRACING
            quality_level=quality_map.get(options.get('quality', 'high'), QualityLevel.HIGH)
        )

        # Initialize Clean Slate multipage converter
        converter = CleanSlateMultiPageConverter(config=pipeline_config)

        start_time = time.time()

        # Convert multiple SVGs → multi-slide PPTX
        result = converter.convert_files(
            svg_files=file_paths,
            output_path=output_path
        )

        processing_time = time.time() - start_time

        # Extract E2E trace data from page results
        trace_data = []
        if enable_debug and hasattr(result, 'page_results'):
            for i, page_result in enumerate(result.page_results):
                if hasattr(page_result, 'debug_data') and page_result.debug_data:
                    trace_data.append({
                        'page_number': i + 1,
                        'svg_file': file_paths[i] if i < len(file_paths) else 'unknown',
                        'pipeline_trace': page_result.debug_data
                    })

        # Build response
        return {
            'success': True,
            'output_path': output_path,
            'output_size_bytes': result.package_size_bytes,
            'page_count': result.page_count,
            'processing_time_seconds': processing_time,
            'total_elements': result.total_elements,
            'native_elements': result.total_native_elements,
            'emf_elements': result.total_emf_elements,
            'avg_quality': result.avg_quality,
            'avg_performance': result.avg_performance,
            'compression_ratio': result.compression_ratio,
            'architecture': 'clean_slate',
            'debug_trace': trace_data if enable_debug else None,
            'completed_at': datetime.utcnow().isoformat()
        }

    except CleanSlateConversionError as e:
        logger.error(f"Clean Slate conversion error: {e}")
        return {
            'success': False,
            'error_message': str(e),
            'error_type': 'clean_slate_conversion_error',
            'architecture': 'clean_slate',
            'failed_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Unexpected error in Clean Slate conversion: {e}")
        return {
            'success': False,
            'error_message': str(e),
            'error_type': 'unexpected_error',
            'architecture': 'clean_slate',
            'failed_at': datetime.utcnow().isoformat()
        }


@huey.task(retries=3, retry_delay=60)
def convert_multipage_svg_clean_slate(
    svg_content: str,
    output_path: str,
    conversion_options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Convert SVG 2.0 multipage SVG to multi-slide PPTX using Clean Slate.

    Args:
        svg_content: SVG 2.0 content with multiple <page> elements
        output_path: Output PPTX path
        conversion_options: Optional conversion parameters

    Returns:
        Dictionary with conversion result and E2E trace data
    """
    try:
        options = conversion_options or {}
        enable_debug = options.get('enable_debug', True)

        logger.info(f"Clean Slate: Converting SVG 2.0 multipage to {output_path}")

        # Detect pages in SVG 2.0 content
        from ..multipage.detection import detect_pages_in_svg

        page_elements = detect_pages_in_svg(svg_content)

        if not page_elements:
            raise CleanSlateConversionError("No pages detected in SVG content")

        # Build PageSource objects
        pages = []
        for i, (page_element, title) in enumerate(page_elements):
            pages.append(PageSource(
                content=page_element,
                title=title or f"Page {i+1}",
                metadata={'page_number': i+1}
            ))

        # Configure Clean Slate pipeline
        from ..pipeline.config import QualityLevel

        quality_map = {
            'fast': QualityLevel.FAST,
            'balanced': QualityLevel.BALANCED,
            'high': QualityLevel.HIGH
        }

        pipeline_config = PipelineConfig(
            enable_debug=enable_debug,
            quality_level=quality_map.get(options.get('quality', 'high'), QualityLevel.HIGH)
        )

        # Initialize Clean Slate multipage converter
        converter = CleanSlateMultiPageConverter(config=pipeline_config)

        start_time = time.time()

        # Convert multipage SVG → multi-slide PPTX
        result = converter.convert_pages(
            pages=pages,
            output_path=output_path
        )

        processing_time = time.time() - start_time

        # Extract E2E trace data
        trace_data = []
        if enable_debug and hasattr(result, 'page_results'):
            for i, page_result in enumerate(result.page_results):
                if hasattr(page_result, 'debug_data') and page_result.debug_data:
                    trace_data.append({
                        'page_number': i + 1,
                        'page_title': pages[i].title if i < len(pages) else 'unknown',
                        'pipeline_trace': page_result.debug_data
                    })

        return {
            'success': True,
            'output_path': output_path,
            'output_size_bytes': result.package_size_bytes,
            'page_count': result.page_count,
            'processing_time_seconds': processing_time,
            'total_elements': result.total_elements,
            'native_elements': result.total_native_elements,
            'emf_elements': result.total_emf_elements,
            'avg_quality': result.avg_quality,
            'avg_performance': result.avg_performance,
            'compression_ratio': result.compression_ratio,
            'architecture': 'clean_slate',
            'svg_type': 'multipage_svg_2.0',
            'debug_trace': trace_data if enable_debug else None,
            'completed_at': datetime.utcnow().isoformat()
        }

    except CleanSlateConversionError as e:
        logger.error(f"Clean Slate multipage conversion error: {e}")
        return {
            'success': False,
            'error_message': str(e),
            'error_type': 'multipage_conversion_error',
            'architecture': 'clean_slate',
            'failed_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Unexpected error in multipage conversion: {e}")
        return {
            'success': False,
            'error_message': str(e),
            'error_type': 'unexpected_error',
            'architecture': 'clean_slate',
            'failed_at': datetime.utcnow().isoformat()
        }


@huey.task()
def process_directory_to_pptx(
    directory_path: str,
    output_path: str,
    conversion_options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Process all SVG files in a directory to multi-slide PPTX.

    Args:
        directory_path: Directory containing SVG files
        output_path: Output PPTX path
        conversion_options: Optional conversion parameters

    Returns:
        Dictionary with conversion result
    """
    try:
        dir_path = Path(directory_path)

        if not dir_path.exists() or not dir_path.is_dir():
            raise CleanSlateConversionError(f"Directory not found: {directory_path}")

        # Find all SVG files
        svg_files = sorted(dir_path.glob('*.svg'))

        if not svg_files:
            raise CleanSlateConversionError(f"No SVG files found in {directory_path}")

        logger.info(f"Processing {len(svg_files)} SVG files from {directory_path}")

        # Convert directly (don't call huey task from huey task)
        from ..multipage.converter import CleanSlateMultiPageConverter
        from ..pipeline.config import PipelineConfig, QualityLevel

        options = conversion_options or {}
        enable_debug = options.get('enable_debug', True)

        quality_map = {
            'fast': QualityLevel.FAST,
            'balanced': QualityLevel.BALANCED,
            'high': QualityLevel.HIGH
        }

        pipeline_config = PipelineConfig(
            enable_debug=enable_debug,
            quality_level=quality_map.get(options.get('quality', 'high'), QualityLevel.HIGH)
        )

        converter = CleanSlateMultiPageConverter(config=pipeline_config)
        start_time = time.time()

        result = converter.convert_files(
            svg_files=[str(f) for f in svg_files],
            output_path=output_path
        )

        processing_time = time.time() - start_time

        # Extract E2E trace
        trace_data = []
        if enable_debug and hasattr(result, 'page_results'):
            for i, page_result in enumerate(result.page_results):
                if hasattr(page_result, 'debug_data') and page_result.debug_data:
                    trace_data.append({
                        'page_number': i + 1,
                        'svg_file': str(svg_files[i]) if i < len(svg_files) else 'unknown',
                        'pipeline_trace': page_result.debug_data
                    })

        return {
            'success': True,
            'output_path': output_path,
            'output_size_bytes': result.package_size_bytes,
            'page_count': result.page_count,
            'processing_time_seconds': processing_time,
            'total_elements': result.total_elements,
            'native_elements': result.total_native_elements,
            'emf_elements': result.total_emf_elements,
            'avg_quality': result.avg_quality,
            'avg_performance': result.avg_performance,
            'compression_ratio': result.compression_ratio,
            'architecture': 'clean_slate',
            'debug_trace': trace_data if enable_debug else None,
            'completed_at': datetime.utcnow().isoformat()
        }

    except CleanSlateConversionError:
        raise
    except Exception as e:
        logger.error(f"Error processing directory {directory_path}: {e}")
        return {
            'success': False,
            'error_message': str(e),
            'error_type': 'directory_processing_error',
            'failed_at': datetime.utcnow().isoformat()
        }


@huey.task()
def process_zip_to_pptx(
    zip_content: bytes,
    output_path: str,
    conversion_options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Extract SVG files from ZIP and convert to multi-slide PPTX.

    Args:
        zip_content: ZIP file content as bytes
        output_path: Output PPTX path
        conversion_options: Optional conversion parameters

    Returns:
        Dictionary with conversion result
    """
    try:
        logger.info(f"Processing ZIP archive ({len(zip_content)} bytes)")

        temp_dir = Path(tempfile.mkdtemp(prefix='svg2pptx_zip_'))
        svg_files = []

        try:
            # Extract ZIP
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                temp_zip.write(zip_content)
                temp_zip.flush()

                with zipfile.ZipFile(temp_zip.name, 'r') as zip_file:
                    # Extract all SVG files
                    all_files = zip_file.namelist()
                    svg_names = [
                        f for f in all_files
                        if f.lower().endswith('.svg') and not f.startswith('__MACOSX/')
                    ]

                    if not svg_names:
                        raise CleanSlateConversionError("No SVG files found in ZIP")

                    if len(svg_names) > 50:
                        raise CleanSlateConversionError(f"Too many SVG files: {len(svg_names)} (max 50)")

                    # Extract SVG files to temp directory
                    for svg_name in svg_names:
                        zip_file.extract(svg_name, temp_dir)
                        extracted_path = temp_dir / svg_name
                        if extracted_path.exists():
                            svg_files.append(str(extracted_path))

                # Clean up temp zip
                Path(temp_zip.name).unlink(missing_ok=True)

            if not svg_files:
                raise CleanSlateConversionError("No valid SVG files extracted from ZIP")

            logger.info(f"Extracted {len(svg_files)} SVG files from ZIP")

            # Convert directly (don't call huey task from huey task)
            from ..multipage.converter import CleanSlateMultiPageConverter
            from ..pipeline.config import PipelineConfig, QualityLevel

            options = conversion_options or {}
            enable_debug = options.get('enable_debug', True)

            quality_map = {
                'fast': QualityLevel.FAST,
                'balanced': QualityLevel.BALANCED,
                'high': QualityLevel.HIGH
            }

            pipeline_config = PipelineConfig(
                enable_debug=enable_debug,
                quality_level=quality_map.get(options.get('quality', 'high'), QualityLevel.HIGH)
            )

            converter = CleanSlateMultiPageConverter(config=pipeline_config)
            start_time = time.time()

            result = converter.convert_files(
                svg_files=svg_files,
                output_path=output_path
            )

            processing_time = time.time() - start_time

            # Extract E2E trace
            trace_data = []
            if enable_debug and hasattr(result, 'page_results'):
                for i, page_result in enumerate(result.page_results):
                    if hasattr(page_result, 'debug_data') and page_result.debug_data:
                        trace_data.append({
                            'page_number': i + 1,
                            'svg_file': svg_files[i] if i < len(svg_files) else 'unknown',
                            'pipeline_trace': page_result.debug_data
                        })

            return {
                'success': True,
                'output_path': output_path,
                'output_size_bytes': result.package_size_bytes,
                'page_count': result.page_count,
                'processing_time_seconds': processing_time,
                'total_elements': result.total_elements,
                'native_elements': result.total_native_elements,
                'emf_elements': result.total_emf_elements,
                'avg_quality': result.avg_quality,
                'avg_performance': result.avg_performance,
                'compression_ratio': result.compression_ratio,
                'architecture': 'clean_slate',
                'debug_trace': trace_data if enable_debug else None,
                'completed_at': datetime.utcnow().isoformat()
            }

        finally:
            # Cleanup temp directory
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    except CleanSlateConversionError:
        raise
    except zipfile.BadZipFile:
        return {
            'success': False,
            'error_message': 'Invalid ZIP file format',
            'error_type': 'invalid_zip',
            'failed_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error processing ZIP: {e}")
        return {
            'success': False,
            'error_message': str(e),
            'error_type': 'zip_processing_error',
            'failed_at': datetime.utcnow().isoformat()
        }

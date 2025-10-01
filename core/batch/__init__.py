#!/usr/bin/env python3
"""
Dual-mode batch processing for SVG to PowerPoint conversion.

This module provides both:
- Batch mode: Huey-based background processing with SQLite backend
- Simple mode: Synchronous processing without external dependencies
"""

# Always available - simple mode
from .simple_api import create_simple_router

# Try to import Huey-based components (may not be available)
try:
    from .huey_app import huey
    from .tasks import (
        convert_single_svg,
        merge_presentations, 
        cleanup_temp_files,
        process_svg_batch,
        extract_and_process_zip,
        periodic_cleanup
    )
    from .api import create_batch_router
    
    HUEY_AVAILABLE = True
    
    __all__ = [
        'huey',
        'convert_single_svg',
        'merge_presentations',
        'cleanup_temp_files', 
        'process_svg_batch',
        'extract_and_process_zip',
        'periodic_cleanup',
        'create_batch_router',
        'create_simple_router',
        'HUEY_AVAILABLE'
    ]
    
except ImportError:
    # Huey not available - only simple mode
    HUEY_AVAILABLE = False
    
    __all__ = [
        'create_simple_router',
        'HUEY_AVAILABLE'
    ]
#!/usr/bin/env python3
"""
Huey application configuration for SVG to PowerPoint batch processing.

Default: MemoryHuey (no background threads, immediate execution)
Production: Set HUEY_USE_SQLITE=true for persistent queue with background workers
"""

import os
from huey import MemoryHuey, SqliteHuey
from pathlib import Path

# Check if production mode with SQLite backend is needed
USE_SQLITE = os.getenv('HUEY_USE_SQLITE', 'false').lower() == 'true'

if USE_SQLITE:
    # Production: SQLite backend with background workers
    data_dir = Path(os.getenv('HUEY_DATA_DIR', './data'))
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / 'svg2pptx_jobs.db'

    huey = SqliteHuey(
        name='svg2pptx',
        filename=str(db_path),
        immediate=False,  # Async mode with background threads
        results=True,
        store_none=False,
        utc=True
    )
else:
    # Default: Memory backend - no threads, immediate execution
    huey = MemoryHuey(
        name='svg2pptx',
        immediate=True,  # Synchronous execution, no background threads
        results=True,
        store_none=False,
        utc=True
    )

# Export for use in tasks
__all__ = ['huey']

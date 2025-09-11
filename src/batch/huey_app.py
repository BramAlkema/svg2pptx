#!/usr/bin/env python3
"""
Huey application configuration for SVG to PowerPoint batch processing.

Uses SQLite as the backend - completely pure Python, no external dependencies.
"""

import os
from huey import SqliteHuey
from pathlib import Path

# Create data directory for Huey database
DATA_DIR = Path(os.getenv('HUEY_DATA_DIR', './data'))
DATA_DIR.mkdir(exist_ok=True)

# Database path
DB_PATH = DATA_DIR / 'svg2pptx_jobs.db'

# Create Huey instance with SQLite backend
huey = SqliteHuey(
    name='svg2pptx',
    filename=str(DB_PATH),
    # Configuration
    immediate=os.getenv('HUEY_IMMEDIATE', 'false').lower() == 'true',  # Sync mode for testing
    results=True,  # Store task results
    store_none=False,  # Don't store None results
    utc=True,  # Use UTC timestamps
    # Consumer settings
    consumer={
        'workers': int(os.getenv('HUEY_WORKERS', '4')),
        'worker_type': 'thread',  # Use threads for I/O bound tasks
        'initial_delay': 0.1,
        'backoff': 1.15,
        'max_delay': 10.0,
        'check_worker_health': True,
        'health_check_interval': 1,
    }
)

# Export for use in tasks
__all__ = ['huey']
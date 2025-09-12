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
    utc=True  # Use UTC timestamps
)

# Export for use in tasks
__all__ = ['huey']
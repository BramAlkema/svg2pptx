#!/usr/bin/env python3
"""
Huey worker startup script for SVG to PowerPoint batch processing.

Usage:
    python -m src.batch.worker
    
Or directly:
    python src/batch/worker.py
    
Or using Huey's consumer:
    huey_consumer src.batch.huey_app.huey
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.batch.huey_app import huey

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("Starting Huey consumer for SVG to PowerPoint batch processing...")
    logger.info(f"Database path: {huey.storage.filename}")
    logger.info(f"Consumer config: {huey.consumer}")
    
    # Start the consumer
    from huey.consumer import Consumer
    consumer = Consumer(huey)
    consumer.run()
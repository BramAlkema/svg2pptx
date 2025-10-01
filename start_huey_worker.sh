#!/bin/bash
# Start Huey worker for SVG2PPTX batch processing

echo "🚀 Starting Huey worker..."
echo "================================"
echo "Database: data/svg2pptx_jobs.db"
echo "Workers: 4"
echo "Press Ctrl+C to stop"
echo "================================"
echo ""

source venv/bin/activate
PYTHONPATH=. huey_consumer core.batch.huey_app.huey --workers 4 --logfile huey.log

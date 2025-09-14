# SVG2PPTX Batch Processing with Dual Mode Support

This module provides efficient SVG to PowerPoint conversion with two processing modes:

- **Batch Mode**: Background processing using Huey with SQLite backend (pure Python)
- **Simple Mode**: Synchronous processing without external dependencies for testing

## Features

### Batch Mode
- ✅ **Pure Python** - SQLite backend, no Redis/RabbitMQ needed
- ✅ **Simple deployment** - Single database file
- ✅ **Background processing** - Async task execution
- ✅ **Progress tracking** - Real-time status monitoring
- ✅ **Automatic retries** - Built-in error handling
- ✅ **Periodic cleanup** - Automatic file cleanup

### Simple Mode  
- ✅ **No dependencies** - Works without Huey installation
- ✅ **Immediate results** - Synchronous processing
- ✅ **Testing friendly** - Perfect for development and testing
- ✅ **Same API** - Compatible endpoints with batch mode

### Both Modes
- ✅ **FastAPI integration** - REST API endpoints
- ✅ **File validation** - SVG and ZIP archive support
- ✅ **Multiple formats** - Single PPTX or ZIP archive output

## Quick Start

### Simple Mode (No Dependencies)

```bash
# 1. Use the API directly (no worker needed)
from fastapi import FastAPI
from src.batch.api import create_batch_router

app = FastAPI()
app.include_router(create_batch_router())

# 2. Start the API server
uvicorn main:app --host 0.0.0.0 --port 8000

# 3. Use simple endpoints
curl -X POST "http://localhost:8000/batch/simple/convert-files" \
  -F "files=@test.svg"
```

### Batch Mode (With Background Processing)

```bash
# 1. Install dependencies
pip install -r requirements-batch.txt

# 2. Start the Huey worker
python -m src.batch.worker
# OR: huey_consumer src.batch.huey_app.huey

# 3. Start the API server (in another terminal)
uvicorn main:app --host 0.0.0.0 --port 8000

# 4. Use batch endpoints
curl -X POST "http://localhost:8000/batch/convert-files" \
  -F "files=@test.svg"
```

## API Endpoints

### Batch Mode (Background Processing)

#### Convert Multiple Files
```bash
curl -X POST "http://localhost:8000/batch/convert-files" \
  -F "files=@file1.svg" \
  -F "files=@file2.svg" \
  -F "slide_width=10.0" \
  -F "slide_height=7.5" \
  -F "output_format=single_pptx"
```

#### Check Status
```bash
curl "http://localhost:8000/batch/status/{batch_id}"
```

#### Download Result
```bash
curl "http://localhost:8000/batch/download/{batch_id}" -o result.pptx
```

#### Cancel Job
```bash
curl -X DELETE "http://localhost:8000/batch/cancel/{batch_id}"
```

### Simple Mode (Immediate Processing)

#### Convert Multiple Files (Synchronous)
```bash
curl -X POST "http://localhost:8000/batch/simple/convert-files" \
  -F "files=@file1.svg" \
  -F "files=@file2.svg" \
  -F "slide_width=10.0" \
  -F "slide_height=7.5" \
  -F "output_format=single_pptx"
# Returns result immediately with job_id
```

#### Download Result (Simple)
```bash
curl "http://localhost:8000/batch/simple/download/{job_id}" -o result.pptx
```

### Both Modes

#### Health Check
```bash
curl "http://localhost:8000/batch/health"
```

#### Worker Status
```bash
curl "http://localhost:8000/batch/worker-status"
```

## Configuration

### Environment Variables

```bash
# Huey configuration
HUEY_DATA_DIR=./data              # Database directory
HUEY_WORKERS=4                    # Number of worker threads
HUEY_IMMEDIATE=false              # Sync mode (for testing)

# Processing limits
MAX_BATCH_SIZE=50                 # Max files per batch
MAX_FILE_SIZE_MB=10               # Max file size
```

### Custom Configuration

```python
from src.batch.huey_app import huey

# Configure Huey programmatically
huey.consumer.workers = 8
huey.consumer.worker_type = 'thread'
```

## Usage Examples

### Direct Task Usage

```python
from src.batch.tasks import process_svg_batch

# Process files directly
file_list = [
    {'filename': 'test.svg', 'content': svg_content}
]
result = process_svg_batch(file_list, {'output_format': 'single_pptx'})
```

### With FastAPI Background Tasks

```python
from fastapi import BackgroundTasks
from src.batch.tasks import process_svg_batch

@app.post("/process")
async def process_files(background_tasks: BackgroundTasks):
    task = process_svg_batch(file_list, options)
    return {"task_id": task.id}
```

## Database Management

### View Tasks
```python
import sqlite3
conn = sqlite3.connect('data/svg2pptx_jobs.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM task")
print(cursor.fetchall())
```

### Cleanup Database
```bash
# Remove all completed tasks
sqlite3 data/svg2pptx_jobs.db "DELETE FROM task WHERE executed_time IS NOT NULL"
```

## Development

### Running Tests

```bash
# Set immediate mode for testing
export HUEY_IMMEDIATE=true
pytest tests/unit/batch/ -v
```

### Adding New Tasks

```python
from src.batch.huey_app import huey

@huey.task(retries=3, retry_delay=60)
def my_custom_task(data):
    # Your task logic here
    return result

@huey.periodic_task(cron_str='0 */6 * * *')  # Every 6 hours
def scheduled_task():
    # Periodic task logic
    pass
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │───▶│   Huey Tasks    │───▶│  SQLite Queue   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Huey Consumer  │◀───│  Task Execution │───▶│  File Storage   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Mode Comparison

| Feature | Simple Mode | Batch Mode (Huey) | Celery |
|---------|-------------|-------------------|--------|
| **Setup** | None | Single SQLite file | Redis/RabbitMQ required |
| **Dependencies** | None | Pure Python | Redis client required |
| **Processing** | Synchronous | Background tasks | Background tasks |
| **Deployment** | Immediate | Copy database file | Complex broker setup |
| **Monitoring** | Not needed | SQLite queries | Flower dashboard |
| **Scaling** | Request limited | Single machine | Multi-machine clusters |
| **Best for** | Testing/development | Small-medium production | Large distributed systems |
| **Max files** | 20 files, 50MB | 50 files, 100MB | Unlimited |

## Troubleshooting

### Worker Not Processing Tasks
```bash
# Check if worker is running
ps aux | grep huey

# Check database
sqlite3 data/svg2pptx_jobs.db ".schema"
```

### Tasks Failing
```bash
# Check logs
tail -f worker.log

# Check task status in database
sqlite3 data/svg2pptx_jobs.db "SELECT * FROM task WHERE executed_time IS NULL"
```

### Storage Issues
```bash
# Check disk space
df -h /tmp/svg2pptx_output

# Clean up old files
find /tmp/svg2pptx_output -mtime +1 -delete
```
"""
Clean Slate Batch Job Models

Pure in-memory batch processing models with no database dependencies.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


# In-memory job store
_job_store: Dict[str, 'CleanSlateBatchJob'] = {}


@dataclass
class CleanSlateBatchJob:
    """
    Clean Slate batch job model.

    Stores job metadata, status, and complete E2E trace data in memory.
    """
    job_id: str
    status: str  # 'created', 'processing', 'completed', 'failed', 'completed_upload_failed'
    total_files: int
    completed_files: int = 0
    failed_files: int = 0

    # Drive integration
    drive_integration_enabled: bool = False
    drive_upload_status: str = "not_requested"  # 'not_requested', 'pending', 'completed', 'failed'
    drive_folder_id: Optional[str] = None
    drive_folder_url: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Trace data (stored directly as dict)
    trace_data: Optional[Dict[str, Any]] = None

    # Error information
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    def __post_init__(self):
        """Initialize timestamps."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CleanSlateBatchJob':
        """Create from dictionary."""
        # Parse timestamps
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        return cls(**data)

    def save(self) -> None:
        """Save job to in-memory store."""
        self.updated_at = datetime.utcnow()
        _job_store[self.job_id] = self

    @classmethod
    def get_by_id(cls, job_id: str) -> Optional['CleanSlateBatchJob']:
        """Retrieve job by ID from in-memory store."""
        return _job_store.get(job_id)

    @classmethod
    def delete(cls, job_id: str) -> None:
        """Delete job from in-memory store."""
        _job_store.pop(job_id, None)

    @classmethod
    def get_all(cls) -> Dict[str, 'CleanSlateBatchJob']:
        """Get all jobs from in-memory store."""
        return _job_store.copy()

    @classmethod
    def clear_all(cls) -> None:
        """Clear all jobs from in-memory store (for testing)."""
        _job_store.clear()

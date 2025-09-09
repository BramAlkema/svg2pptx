#!/usr/bin/env python3
"""
Pydantic schemas for API request/response models.
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ConvertRequest(BaseModel):
    """Request model for SVG conversion."""
    url: HttpUrl = Field(..., description="URL of the SVG file to convert")
    fileId: Optional[str] = Field(None, description="Optional Google Drive file ID to update")


class ConvertResponse(BaseModel):
    """Response model for successful conversion."""
    success: bool = Field(True, description="Indicates successful conversion")
    fileId: str = Field(..., description="Google Drive file ID")
    shareableLink: str = Field(..., description="Public shareable link to the file")
    fileName: str = Field(..., description="Name of the created/updated file")
    fileSize: int = Field(..., description="File size in bytes")
    processingTime: float = Field(..., description="Processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Conversion timestamp")


class ErrorResponse(BaseModel):
    """Response model for errors."""
    success: bool = Field(False, description="Indicates failed operation")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
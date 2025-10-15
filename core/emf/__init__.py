#!/usr/bin/env python3
"""
EMF System for Clean Slate Architecture

EMF blob generation and packaging migrated from legacy src/ for self-contained operation.
"""

from .emf_blob import EMFBlob, EMFBrushStyle, EMFRecordType

__all__ = [
    'EMFBlob',
    'EMFRecordType',
    'EMFBrushStyle',
]
"""Shared namespace constants for the XML builder package."""

from __future__ import annotations

# OpenXML namespaces
P_URI = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_URI = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_URI = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CONTENT_TYPES_URI = "http://schemas.openxmlformats.org/package/2006/content-types"
RELATIONSHIPS_URI = "http://schemas.openxmlformats.org/package/2006/relationships"

# Namespace maps commonly used with lxml
NSMAP = {
    "p": P_URI,
    "a": A_URI,
    "r": R_URI,
}

CONTENT_NSMAP = {
    None: CONTENT_TYPES_URI,
}

RELATIONSHIPS_NSMAP = {
    None: RELATIONSHIPS_URI,
}


__all__ = [
    "A_URI",
    "CONTENT_NSMAP",
    "CONTENT_TYPES_URI",
    "NSMAP",
    "P_URI",
    "R_URI",
    "RELATIONSHIPS_NSMAP",
    "RELATIONSHIPS_URI",
]

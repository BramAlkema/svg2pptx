# Technical Stack

> Last Updated: 2025-09-13
> Version: 1.1.0

## Application Framework

- **Framework:** Python-based conversion engine
- **Version:** Python 3.8+

## Database

- **Primary Database:** File-based processing (no persistent database required)

## JavaScript

- **Framework:** Google Apps Script for Google Workspace integration

## CSS Framework

- **Framework:** N/A (SVG processing and PowerPoint generation)

## Core Technologies

### Python Engine
- **python-pptx**: PowerPoint file generation and manipulation
- **lxml**: XML and SVG parsing (REQUIRED - see XML Parsing Standards below)
- **DrawML conversion engine**: Map SVG elements to PowerPoint's Drawing Markup Language
- **LibreOffice reference**: Leverage open-source SVG-to-DrawML conversion algorithms
- **FastAPI/Flask**: For API endpoints (cloud deployment)

### Google Apps Script Integration
- **Google Apps Script**: Client-side integration for Google Workspace
- **Google Drive API**: File handling and storage integration
- **Google Slides API**: Direct presentation creation capabilities

## XML Parsing Standards

### REQUIRED Library
- **lxml**: The ONLY approved XML parsing library for this project
  - Use `from lxml import etree` for XML/SVG parsing
  - Provides robust namespace handling required for SVG processing
  - Superior performance and memory management for large XML files
  - Full XPath support for complex SVG element queries

### PROHIBITED Libraries
- **xml.etree.ElementTree**: NEVER use this library
  - Inadequate namespace handling for SVG files
  - Poor performance with complex XML structures
  - Limited XPath support
  - Security vulnerabilities with untrusted XML

### Code Standards
```python
# CORRECT - Use lxml
from lxml import etree

# Parse SVG content
parser = etree.XMLParser(ns_clean=True, recover=True)
root = etree.fromstring(svg_content, parser)

# INCORRECT - Never use ElementTree
# from xml.etree import ElementTree  # FORBIDDEN
```

## Deployment Options

### Cloud API
- **Platform:** Docker containers
- **API Framework:** FastAPI for high-performance endpoints
- **File Processing:** Temporary file handling with cleanup

### Google Apps Script
- **Platform:** Google Apps Script runtime
- **Integration:** Direct Google Workspace integration
- **Distribution:** Google Workspace Marketplace

## Development Tools
- **Version Control:** Git
- **Package Management:** pip (Python), clasp (Google Apps Script)
- **Testing:** pytest for Python components
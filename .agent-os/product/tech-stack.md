# Technical Stack

> Last Updated: 2025-09-09
> Version: 1.0.0

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
- **SVG parsing libraries**: For vector graphics processing
- **DrawML conversion engine**: Map SVG elements to PowerPoint's Drawing Markup Language
- **LibreOffice reference**: Leverage open-source SVG-to-DrawML conversion algorithms
- **FastAPI/Flask**: For API endpoints (cloud deployment)

### Google Apps Script Integration
- **Google Apps Script**: Client-side integration for Google Workspace
- **Google Drive API**: File handling and storage integration
- **Google Slides API**: Direct presentation creation capabilities

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
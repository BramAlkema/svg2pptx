# Spec Requirements Document

> Spec: SVG to Google Drive API
> Created: 2025-09-09

## Overview

Create a simple web API that accepts SVG URLs, converts them to PowerPoint format using the existing conversion engine, and uploads the result to Google Drive. This API will enable Google Apps users to import complex vector graphics that Google Slides cannot handle natively.

## User Stories

### API Client Integration

As a Google Apps developer, I want to POST an SVG URL to an API endpoint, so that I can programmatically convert and import vector graphics into Google Drive presentations.

The client sends a POST request with an SVG URL and optionally a Google Drive file ID. The API fetches the SVG, processes it through the existing conversion engine, and either creates a new PPTX file in Google Drive or updates an existing file. The response includes the Drive file ID and shareable link for immediate use.

### Existing File Updates

As an API user, I want to update an existing Google Drive presentation with new SVG content, so that I can refresh slides without creating duplicate files.

When a fileId parameter is provided, the API updates the existing Google Drive file instead of creating a new one, maintaining sharing permissions and folder location while replacing the slide content.

## Spec Scope

1. **HTTP API Endpoint** - Single POST endpoint accepting SVG URL and optional fileId parameters
2. **SVG Processing** - Integration with existing SVG to PPTX conversion engine
3. **Google Drive Upload** - Service account-based file creation and updates in Google Drive
4. **Authentication** - Simple API key-based request authentication
5. **Error Handling** - Comprehensive error responses for common failure scenarios

## Out of Scope

- User OAuth authentication (service account only)
- Complex Drive folder management
- Real-time conversion progress tracking
- SVG content validation beyond basic format checking
- Batch processing of multiple SVGs
- Custom slide dimensions or templates

## Expected Deliverable

1. Working API endpoint that accepts SVG URLs and returns Google Drive file information
2. Integration with existing SVG conversion engine producing valid PPTX files
3. Google Drive service account setup with proper file creation and update capabilities
#!/usr/bin/env python3
"""
Main conversion service that integrates SVG processing with Google Drive.
"""

import logging
import time
from typing import Dict, Optional, Any
from pathlib import Path

from .google_drive import GoogleDriveService, GoogleDriveError
from .google_slides import GoogleSlidesService, GoogleSlidesError
from .file_processor import UploadManager, FileProcessor
from ..config import get_settings

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Custom exception for conversion operations."""
    pass


class ConversionService:
    """
    Main service for SVG to PPTX conversion and Google Drive upload.
    
    Integrates all the components: SVG fetching, conversion, and Drive upload.
    """
    
    def __init__(self):
        """Initialize conversion service."""
        self.settings = get_settings()
        self.drive_service = None
        self.slides_service = None
        self.upload_manager = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize Google Drive, Slides, and upload services."""
        try:
            self.drive_service = GoogleDriveService()
            self.slides_service = GoogleSlidesService()
            self.upload_manager = UploadManager(self.drive_service)
            logger.info("Conversion service initialized successfully")
        except GoogleDriveError as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            raise ConversionError(f"Google Drive initialization failed: {e}")
        except GoogleSlidesError as e:
            logger.error(f"Failed to initialize Google Slides service: {e}")
            raise ConversionError(f"Google Slides initialization failed: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize conversion service: {e}")
            raise ConversionError(f"Service initialization failed: {e}")
    
    def convert_and_upload(self, svg_url: str, file_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert SVG from URL to PPTX and upload to Google Drive.
        
        Args:
            svg_url: URL of the SVG file to convert
            file_id: Optional Google Drive file ID to update
            
        Returns:
            Dictionary with conversion and upload results
        """
        start_time = time.time()
        
        try:
            # Step 1: Fetch SVG content (placeholder for now)
            logger.info(f"Processing SVG from URL: {svg_url}")
            svg_content = self._fetch_svg_content(svg_url)
            
            # Step 2: Convert SVG to PPTX (placeholder for now)
            logger.info("Converting SVG to PPTX")
            pptx_content = self._convert_svg_to_pptx(svg_content, svg_url)
            
            # Step 3: Generate filename
            filename = self._generate_filename(svg_url)
            
            # Step 4: Upload or update in Google Drive
            if file_id:
                logger.info(f"Updating existing file: {file_id}")
                result = self.upload_manager.update_file_content(
                    file_id=file_id,
                    content=pptx_content,
                    filename=filename
                )
            else:
                logger.info(f"Uploading new file: {filename}")
                result = self.upload_manager.upload_content_as_file(
                    content=pptx_content,
                    filename=filename,
                    folder_id=self.settings.google_drive_folder_id
                )
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Enhance result with processing info
            result.update({
                'processingTime': round(processing_time, 2),
                'sourceUrl': svg_url,
                'conversionMethod': 'svg2pptx-api'
            })
            
            # Generate preview information if possible
            try:
                logger.info("Generating presentation previews")
                presentation_id = self._extract_presentation_id_from_drive_file(result['fileId'])
                if presentation_id:
                    preview_info = self.slides_service.generate_preview_summary(presentation_id)
                    result['previews'] = preview_info['previews']
                    result['presentationUrl'] = preview_info['urls']['presentation']
                    logger.info(f"Generated preview info: {preview_info['previews']['available']} thumbnails")
                else:
                    logger.warning("Could not extract presentation ID for previews")
            except Exception as e:
                logger.warning(f"Could not generate previews: {e}")
                result['previews'] = {'available': 0, 'total': 0, 'error': str(e)}
            
            logger.info(f"Conversion completed successfully in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Conversion failed after {processing_time:.2f}s: {e}")
            raise ConversionError(f"Conversion failed: {e}")
        finally:
            # Clean up any temporary files
            if self.upload_manager:
                self.upload_manager.cleanup_all()
    
    def _fetch_svg_content(self, svg_url: str) -> bytes:
        """
        Fetch SVG content from URL.
        
        Args:
            svg_url: URL to fetch SVG from
            
        Returns:
            SVG content as bytes
        """
        try:
            import httpx
            import urllib.parse
            
            # Validate URL format
            parsed_url = urllib.parse.urlparse(svg_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ConversionError(f"Invalid URL format: {svg_url}")
            
            # Only allow HTTP/HTTPS schemes for security
            if parsed_url.scheme.lower() not in ['http', 'https']:
                raise ConversionError(f"Unsupported URL scheme: {parsed_url.scheme}")
            
            logger.info(f"Fetching SVG content from: {svg_url}")
            
            # Fetch content with timeout and size limits
            timeout = httpx.Timeout(30.0)  # 30 second timeout
            with httpx.Client(timeout=timeout) as client:
                response = client.get(
                    svg_url,
                    headers={
                        'User-Agent': 'SVG2PPTX-API/1.0',
                        'Accept': 'image/svg+xml,application/xml,text/xml,*/*'
                    },
                    follow_redirects=True
                )
                
                # Check response status
                response.raise_for_status()
                
                # Validate content type
                content_type = response.headers.get('content-type', '').lower()
                if not any(ct in content_type for ct in ['svg', 'xml']):
                    logger.warning(f"Unexpected content type: {content_type}")
                
                # Check content size (limit to 10MB)
                content_length = len(response.content)
                max_size = 10 * 1024 * 1024  # 10MB
                if content_length > max_size:
                    raise ConversionError(f"SVG file too large: {content_length} bytes (max: {max_size})")
                
                # Validate that content looks like SVG
                content_str = response.content.decode('utf-8', errors='replace')
                if '<svg' not in content_str.lower():
                    raise ConversionError("Downloaded content does not appear to be valid SVG")
                
                logger.info(f"Successfully fetched SVG content: {content_length} bytes")
                return response.content
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching SVG: {e.response.status_code} - {e.response.text}")
            raise ConversionError(f"Failed to fetch SVG: HTTP {e.response.status_code}")
        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching SVG from {svg_url}: {e}")
            raise ConversionError(f"Timeout fetching SVG from URL (30s timeout exceeded)")
        except httpx.RequestError as e:
            logger.error(f"Request error fetching SVG from {svg_url}: {e}")
            raise ConversionError(f"Network error fetching SVG: {e}")
        except UnicodeDecodeError as e:
            logger.error(f"Unicode decode error in SVG content: {e}")
            raise ConversionError("Downloaded SVG content contains invalid UTF-8 encoding")
        except Exception as e:
            logger.error(f"Unexpected error fetching SVG from {svg_url}: {e}")
            raise ConversionError(f"Failed to fetch SVG content: {e}")
    
    def _convert_svg_to_pptx(self, svg_content: bytes, source_url: str) -> bytes:
        """
        Convert SVG content to PPTX format using preprocessing and modular converters.
        
        Args:
            svg_content: SVG content as bytes
            source_url: Original SVG URL for reference
            
        Returns:
            PPTX content as bytes
        """
        temp_svg_path = None
        temp_pptx_path = None
        
        try:
            from src.preprocessing import create_optimizer
            from src.converters import ConverterRegistry, CoordinateSystem, ConversionContext
            from src.core.pptx_builder import PPTXBuilder
            import tempfile
            import os
            from lxml import etree as ET
            
            logger.info(f"Starting SVG to PPTX conversion for content from {source_url}")
            
            # Step 1: Preprocess SVG content for better conversion quality
            svg_text = svg_content.decode('utf-8', errors='replace')
            
            if self.settings.svg_preprocessing_enabled:
                logger.info(f"Preprocessing SVG with {self.settings.svg_preprocessing_preset} preset")
                
                optimizer = create_optimizer(
                    preset=self.settings.svg_preprocessing_preset,
                    precision=self.settings.svg_preprocessing_precision,
                    multipass=self.settings.svg_preprocessing_multipass
                )
                optimized_svg = optimizer.optimize(svg_text)
                logger.info("SVG preprocessing completed")
            else:
                logger.info("SVG preprocessing disabled, using original content")
                optimized_svg = svg_text
            
            # Step 2: Parse optimized SVG
            root = ET.fromstring(optimized_svg)
            logger.info("Parsed optimized SVG structure")
            
            # Step 3: Initialize modular conversion system with services
            from src.services.conversion_services import ConversionServices

            # Create default services for conversion
            services = ConversionServices.create_default()
            registry = ConverterRegistry(services=services)
            registry.register_default_converters()

            # Extract viewBox or use default coordinates
            viewbox = root.get('viewBox')
            if viewbox:
                coords = [float(x) for x in viewbox.split()]
                coord_system = CoordinateSystem(tuple(coords))
            else:
                width = float(root.get('width', '800').replace('px', ''))
                height = float(root.get('height', '600').replace('px', ''))
                coord_system = CoordinateSystem((0, 0, width, height))

            # Step 4: Convert SVG using modular converters
            # ConversionContext now requires services parameter
            context = ConversionContext(services=services, svg_root=root)
            context.coordinate_system = coord_system
            context.converter_registry = registry

            logger.info("Converting SVG using modular converter system")
            drawingml_elements = []

            for element in root:
                # get_converter expects ET.Element, not element tag
                converter = registry.get_converter(element)
                if converter:
                    try:
                        result = converter.convert(element, context)
                        if result:
                            drawingml_elements.append(result)
                    except Exception as e:
                        logger.warning(f"Failed to convert element {element.tag}: {e}")
            
            # Combine all DrawingML elements
            drawingml = '\n'.join(drawingml_elements)
            logger.info(f"Generated DrawingML with {len(drawingml_elements)} elements ({len(drawingml)} characters)")
            
            # Fallback to legacy converter if no elements were converted
            if not drawingml_elements:
                logger.warning("No elements converted with modular system, falling back to legacy converter")
                from src.svg2drawingml import SVGToDrawingMLConverter
                from src.services.conversion_services import ConversionServices

                # Save optimized SVG to temporary file for legacy converter
                with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False, encoding='utf-8') as f:
                    f.write(optimized_svg)
                    temp_svg_path = f.name

                # Create converter with default services
                services = ConversionServices.create_default()
                converter = SVGToDrawingMLConverter(services=services)
                drawingml = converter.convert_file(temp_svg_path)
                logger.info(f"Fallback conversion completed ({len(drawingml)} characters)")
            
            # Step 5: Create PPTX file using the builder
            builder = PPTXBuilder()
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
                temp_pptx_path = f.name
            
            logger.info(f"Creating PPTX file: {temp_pptx_path}")
            builder.create_minimal_pptx(drawingml, temp_pptx_path)
            
            # Read the generated PPTX content
            with open(temp_pptx_path, 'rb') as f:
                pptx_content = f.read()
            
            logger.info(f"Successfully converted SVG to PPTX ({len(pptx_content)} bytes)")
            
            # Verify the PPTX content is valid
            if len(pptx_content) < 1000:  # PPTX files should be at least 1KB
                raise ConversionError("Generated PPTX file appears to be too small to be valid")
            
            # Check for ZIP signature (PPTX files are ZIP archives)
            if not pptx_content.startswith(b'PK'):
                raise ConversionError("Generated file does not have valid ZIP/PPTX signature")
            
            return pptx_content
            
        except ImportError as e:
            logger.error(f"Import error in conversion engine: {e}")
            raise ConversionError(f"Conversion engine not available: {e}")
        except Exception as e:
            logger.error(f"SVG to PPTX conversion failed: {e}")
            # Try to create error PPTX as fallback
            try:
                return self._create_error_pptx(source_url, str(e))
            except Exception as fallback_error:
                logger.error(f"Fallback error PPTX creation also failed: {fallback_error}")
                raise ConversionError(f"Conversion failed and unable to create error document: {e}")
        finally:
            # Clean up temporary files
            if temp_svg_path and os.path.exists(temp_svg_path):
                try:
                    os.unlink(temp_svg_path)
                    logger.debug(f"Cleaned up temporary SVG file: {temp_svg_path}")
                except OSError as e:
                    logger.warning(f"Could not clean up temp SVG file {temp_svg_path}: {e}")
            
            if temp_pptx_path and os.path.exists(temp_pptx_path):
                try:
                    os.unlink(temp_pptx_path)
                    logger.debug(f"Cleaned up temporary PPTX file: {temp_pptx_path}")
                except OSError as e:
                    logger.warning(f"Could not clean up temp PPTX file {temp_pptx_path}: {e}")
    
    def _create_error_pptx(self, source_url: str, error_message: str) -> bytes:
        """Create a minimal PPTX file indicating conversion error."""
        try:
            from src.core.pptx_builder import PPTXBuilder
            import tempfile
            import os
            
            # Create error message as DrawingML
            error_drawingml = f'''
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="1" name="Error Message"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="914400" y="1143000"/>
                        <a:ext cx="7315200" cy="1143000"/>
                    </a:xfrm>
                    <a:prstGeom prst="rect">
                        <a:avLst/>
                    </a:prstGeom>
                    <a:solidFill>
                        <a:srgbClr val="FFE6E6"/>
                    </a:solidFill>
                </p:spPr>
                <p:txBody>
                    <a:bodyPr/>
                    <a:lstStyle/>
                    <a:p>
                        <a:r>
                            <a:rPr lang="en-US"/>
                            <a:t>Conversion Error: {error_message}</a:t>
                        </a:r>
                    </a:p>
                    <a:p>
                        <a:r>
                            <a:rPr lang="en-US"/>
                            <a:t>Source: {source_url}</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>'''
            
            builder = PPTXBuilder()
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
                temp_path = f.name
            
            builder.create_minimal_pptx(error_drawingml, temp_path)
            
            with open(temp_path, 'rb') as f:
                content = f.read()
            
            os.unlink(temp_path)
            return content
            
        except Exception as e:
            logger.error(f"Failed to create error PPTX: {e}")
            # Return minimal binary content as last resort
            return b"Conversion failed"
    
    def _generate_filename(self, svg_url: str) -> str:
        """
        Generate appropriate filename for converted PPTX.
        
        Args:
            svg_url: Source SVG URL
            
        Returns:
            Generated filename
        """
        try:
            # Extract filename from URL
            url_path = Path(svg_url)
            base_name = url_path.stem or "converted_svg"
            
            # Clean filename
            safe_name = "".join(c for c in base_name if c.isalnum() or c in "._-")[:50]
            
            return f"{safe_name}.pptx"
            
        except Exception:
            # Fallback filename
            return "svg_conversion.pptx"
    
    def _extract_presentation_id_from_drive_file(self, drive_file_id: str) -> Optional[str]:
        """
        Extract presentation ID from Google Drive file.
        
        For PPTX files uploaded to Google Drive, the file ID is often the same as the
        presentation ID when opened in Google Slides.
        
        Args:
            drive_file_id: Google Drive file ID
            
        Returns:
            Presentation ID if extractable, None otherwise
        """
        try:
            # For PPTX files, the Drive file ID is typically the same as presentation ID
            # when the file is opened in Google Slides
            return drive_file_id
        except Exception as e:
            logger.warning(f"Could not extract presentation ID: {e}")
            return None
    
    async def get_presentation_previews(self, drive_file_id: str) -> Dict[str, Any]:
        """
        Get PNG previews for a converted presentation.
        
        Args:
            drive_file_id: Google Drive file ID
            
        Returns:
            Dictionary with preview information and download results
        """
        try:
            presentation_id = self._extract_presentation_id_from_drive_file(drive_file_id)
            if not presentation_id:
                return {
                    'success': False,
                    'error': 'Could not determine presentation ID',
                    'fileId': drive_file_id
                }
            
            logger.info(f"Generating previews for presentation: {presentation_id}")
            
            # Get preview summary
            summary = self.slides_service.generate_preview_summary(presentation_id)
            
            # Download preview images
            preview_downloads = await self.slides_service.download_slide_previews(presentation_id)
            
            return {
                'success': True,
                'fileId': drive_file_id,
                'presentationId': presentation_id,
                'presentation': summary['presentation'],
                'previews': {
                    'summary': summary['previews'],
                    'downloads': preview_downloads,
                    'successful': sum(1 for p in preview_downloads if p.get('success')),
                    'total': len(preview_downloads)
                },
                'urls': summary['urls']
            }
            
        except Exception as e:
            logger.error(f"Failed to get presentation previews: {e}")
            return {
                'success': False,
                'error': str(e),
                'fileId': drive_file_id
            }
    
    def test_service(self) -> Dict[str, Any]:
        """
        Test the conversion service with a simple example.
        
        Returns:
            Test result dictionary
        """
        try:
            logger.info("Testing conversion service...")
            
            # Test with a simple SVG URL
            test_url = "https://example.com/test.svg"
            result = self.convert_and_upload(svg_url=test_url)
            
            logger.info("Conversion service test completed successfully")
            return {
                'success': True,
                'message': 'Conversion service test passed',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Conversion service test failed: {e}")
            return {
                'success': False,
                'message': 'Conversion service test failed',
                'error': str(e)
            }


if __name__ == "__main__":
    # Test the conversion service
    try:
        service = ConversionService()
        result = service.test_service()
        print(f"Test result: {result}")
    except Exception as e:
        print(f"Service test failed: {e}")
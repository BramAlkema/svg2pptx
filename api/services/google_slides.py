#!/usr/bin/env python3
"""
Google Slides service for generating PNG previews from presentations.
"""

import logging
import httpx
from typing import Dict, List, Optional, Any
from pathlib import Path
import base64
import asyncio

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .google_oauth import GoogleOAuthService, GoogleOAuthError
from ..config import get_settings

logger = logging.getLogger(__name__)


class GoogleSlidesError(Exception):
    """Custom exception for Google Slides operations."""
    
    def __init__(self, message: str, error_code: Optional[int] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class GoogleSlidesService:
    """
    Google Slides API service for presentation operations.
    
    Handles slide preview generation, thumbnail creation, and presentation metadata.
    """
    
    def __init__(self, oauth_service: Optional[GoogleOAuthService] = None):
        """
        Initialize Google Slides service.
        
        Args:
            oauth_service: Optional GoogleOAuthService instance
        """
        self.settings = get_settings()
        self.oauth_service = oauth_service or GoogleOAuthService()
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Slides API service."""
        try:
            credentials = self.oauth_service.get_credentials()
            self.service = build('slides', 'v1', credentials=credentials)
            logger.info("Google Slides service initialized successfully")
        except GoogleOAuthError as e:
            raise GoogleSlidesError(f"OAuth authentication failed: {e.message}")
        except Exception as e:
            raise GoogleSlidesError(f"Failed to initialize Google Slides service: {e}")
    
    def get_presentation_info(self, presentation_id: str) -> Dict[str, Any]:
        """
        Get basic information about a presentation.
        
        Args:
            presentation_id: Google Slides presentation ID
            
        Returns:
            Dictionary with presentation information
        """
        try:
            presentation = self.service.presentations().get(
                presentationId=presentation_id,
                fields="presentationId,title,slides.objectId,pageSize"
            ).execute()
            
            slide_ids = [slide['objectId'] for slide in presentation.get('slides', [])]
            page_size = presentation.get('pageSize', {})
            
            return {
                'presentationId': presentation['presentationId'],
                'title': presentation.get('title', 'Untitled Presentation'),
                'slideCount': len(slide_ids),
                'slideIds': slide_ids,
                'pageSize': {
                    'width': page_size.get('width', {}).get('magnitude', 10),
                    'height': page_size.get('height', {}).get('magnitude', 7.5),
                    'unit': page_size.get('width', {}).get('unit', 'INCH')
                }
            }
            
        except HttpError as e:
            error_msg = self._extract_error_message(e)
            logger.error(f"Failed to get presentation info: {error_msg}")
            raise GoogleSlidesError(f"Could not get presentation info: {error_msg}", e.resp.status)
        except Exception as e:
            logger.error(f"Unexpected error getting presentation info: {e}")
            raise GoogleSlidesError(f"Presentation info failed: {e}")
    
    def get_slide_thumbnails(self, presentation_id: str, 
                           thumbnail_size: str = "LARGE") -> List[Dict[str, Any]]:
        """
        Get thumbnail URLs for all slides in a presentation.
        
        Args:
            presentation_id: Google Slides presentation ID
            thumbnail_size: Size of thumbnails (SMALL, MEDIUM, LARGE)
            
        Returns:
            List of dictionaries with slide info and thumbnail URLs
        """
        try:
            # Get presentation info first
            presentation_info = self.get_presentation_info(presentation_id)
            slide_ids = presentation_info['slideIds']
            
            thumbnails = []
            
            for i, slide_id in enumerate(slide_ids):
                try:
                    # Get thumbnail for this slide
                    thumbnail_response = self.service.presentations().pages().getThumbnail(
                        presentationId=presentation_id,
                        pageObjectId=slide_id,
                        thumbnailProperties_thumbnailSize=thumbnail_size
                    ).execute()
                    
                    thumbnails.append({
                        'slideNumber': i + 1,
                        'slideId': slide_id,
                        'thumbnailUrl': thumbnail_response.get('contentUrl'),
                        'width': thumbnail_response.get('width'),
                        'height': thumbnail_response.get('height')
                    })
                    
                except HttpError as e:
                    logger.warning(f"Failed to get thumbnail for slide {slide_id}: {e}")
                    thumbnails.append({
                        'slideNumber': i + 1,
                        'slideId': slide_id,
                        'thumbnailUrl': None,
                        'error': str(e)
                    })
            
            logger.info(f"Generated {len(thumbnails)} slide thumbnails")
            return thumbnails
            
        except GoogleSlidesError:
            raise
        except Exception as e:
            logger.error(f"Failed to get slide thumbnails: {e}")
            raise GoogleSlidesError(f"Thumbnail generation failed: {e}")
    
    async def download_slide_previews(self, presentation_id: str, 
                                    output_dir: Optional[str] = None,
                                    thumbnail_size: str = "LARGE") -> List[Dict[str, Any]]:
        """
        Download PNG previews for all slides in a presentation.
        
        Args:
            presentation_id: Google Slides presentation ID
            output_dir: Directory to save PNG files (optional)
            thumbnail_size: Size of thumbnails (SMALL, MEDIUM, LARGE)
            
        Returns:
            List of dictionaries with slide info and downloaded file paths
        """
        try:
            # Get thumbnail URLs
            thumbnails = self.get_slide_thumbnails(presentation_id, thumbnail_size)
            
            previews = []
            
            async with httpx.AsyncClient() as client:
                for thumbnail in thumbnails:
                    slide_number = thumbnail['slideNumber']
                    thumbnail_url = thumbnail.get('thumbnailUrl')
                    
                    if not thumbnail_url:
                        previews.append({
                            'slideNumber': slide_number,
                            'slideId': thumbnail['slideId'],
                            'success': False,
                            'error': 'No thumbnail URL available'
                        })
                        continue
                    
                    try:
                        # Download the image
                        response = await client.get(thumbnail_url)
                        response.raise_for_status()
                        
                        image_data = response.content
                        
                        result = {
                            'slideNumber': slide_number,
                            'slideId': thumbnail['slideId'],
                            'success': True,
                            'imageData': image_data,
                            'imageSize': len(image_data),
                            'width': thumbnail.get('width'),
                            'height': thumbnail.get('height')
                        }
                        
                        # Save to file if output directory specified
                        if output_dir:
                            Path(output_dir).mkdir(parents=True, exist_ok=True)
                            filename = f"slide_{slide_number:02d}.png"
                            file_path = Path(output_dir) / filename
                            
                            with open(file_path, 'wb') as f:
                                f.write(image_data)
                            
                            result['filePath'] = str(file_path)
                            result['filename'] = filename
                        
                        previews.append(result)
                        logger.info(f"Downloaded preview for slide {slide_number}")
                        
                    except Exception as e:
                        logger.error(f"Failed to download slide {slide_number}: {e}")
                        previews.append({
                            'slideNumber': slide_number,
                            'slideId': thumbnail['slideId'],
                            'success': False,
                            'error': str(e)
                        })
            
            successful = sum(1 for p in previews if p.get('success'))
            logger.info(f"Downloaded {successful}/{len(previews)} slide previews")
            
            return previews
            
        except Exception as e:
            logger.error(f"Failed to download slide previews: {e}")
            raise GoogleSlidesError(f"Preview download failed: {e}")
    
    def generate_preview_summary(self, presentation_id: str) -> Dict[str, Any]:
        """
        Generate a summary with presentation info and preview thumbnails.
        
        Args:
            presentation_id: Google Slides presentation ID
            
        Returns:
            Dictionary with presentation summary and preview info
        """
        try:
            # Get presentation info
            presentation_info = self.get_presentation_info(presentation_id)
            
            # Get thumbnail URLs (but don't download the images)
            thumbnails = self.get_slide_thumbnails(presentation_id, "MEDIUM")
            
            # Create summary
            summary = {
                'presentation': {
                    'id': presentation_id,
                    'title': presentation_info['title'],
                    'slideCount': presentation_info['slideCount'],
                    'pageSize': presentation_info['pageSize']
                },
                'previews': {
                    'available': len([t for t in thumbnails if t.get('thumbnailUrl')]),
                    'total': len(thumbnails),
                    'thumbnails': thumbnails
                },
                'urls': {
                    'presentation': f"https://docs.google.com/presentation/d/{presentation_id}/edit",
                    'view': f"https://docs.google.com/presentation/d/{presentation_id}/present"
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate preview summary: {e}")
            raise GoogleSlidesError(f"Preview summary failed: {e}")
    
    def _extract_error_message(self, error: HttpError) -> str:
        """Extract readable error message from HttpError."""
        try:
            if hasattr(error, 'content'):
                import json
                error_content = json.loads(error.content.decode('utf-8'))
                return error_content.get('error', {}).get('message', str(error))
        except:
            pass
        
        return str(error)


# Utility functions for easier access

def get_presentation_previews(presentation_id: str) -> Dict[str, Any]:
    """
    Get presentation info with preview thumbnails.
    
    Args:
        presentation_id: Google Slides presentation ID
        
    Returns:
        Dictionary with presentation and preview information
    """
    try:
        slides_service = GoogleSlidesService()
        return slides_service.generate_preview_summary(presentation_id)
    except Exception as e:
        return {
            'error': str(e),
            'presentation': {'id': presentation_id},
            'previews': {'available': 0, 'total': 0}
        }


async def download_presentation_previews(presentation_id: str, 
                                       output_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Download all slide previews for a presentation.
    
    Args:
        presentation_id: Google Slides presentation ID
        output_dir: Directory to save PNG files
        
    Returns:
        List of download results
    """
    try:
        slides_service = GoogleSlidesService()
        return await slides_service.download_slide_previews(presentation_id, output_dir)
    except Exception as e:
        logger.error(f"Failed to download previews: {e}")
        return [{'error': str(e), 'success': False}]


if __name__ == "__main__":
    # Test the Google Slides service
    import sys
    
    if len(sys.argv) > 1:
        presentation_id = sys.argv[1]
        print(f"Testing with presentation ID: {presentation_id}")
        
        try:
            summary = get_presentation_previews(presentation_id)
            print(f"Presentation: {summary['presentation']['title']}")
            print(f"Slides: {summary['previews']['available']}/{summary['previews']['total']}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python api/services/google_slides.py <presentation_id>")
        print("This will test getting preview info for a Google Slides presentation.")
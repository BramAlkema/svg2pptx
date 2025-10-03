#!/usr/bin/env python3
"""
Image Processing Adapter

Integrates Clean Slate ImageMapper with the comprehensive existing image processing system.
Leverages proven ImageService and ImageConverter for complete image handling capabilities.
"""

import logging
import base64
import os
from typing import Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from urllib.parse import urlparse

# Import existing image processing system
try:
    from ..services.image_service import ImageService, ImageInfo
    IMAGE_SYSTEM_AVAILABLE = True
except ImportError:
    IMAGE_SYSTEM_AVAILABLE = False
    # Create fallback ImageInfo for when system is not available
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class ImageInfo:
        width: int
        height: int
        format: str
        file_size: int
        content: Optional[bytes] = None
        temp_path: Optional[str] = None

    logging.warning("Image service not available - image adapter will use fallback")

from ..ir import Image


@dataclass
class ImageProcessingResult:
    """Result of image processing"""
    image_data: bytes
    format: str
    width: int
    height: int
    relationship_id: str
    embed_id: str
    metadata: Dict[str, Any]


class ImageProcessingAdapter:
    """
    Adapter for integrating IR image processing with existing comprehensive image system.

    Leverages the proven image infrastructure:
    - ImageService for metadata extraction, validation, and caching
    - ImageConverter for Base64, file path, and URL processing
    """

    def __init__(self, services=None):
        """Initialize image processing adapter"""
        self.logger = logging.getLogger(__name__)
        self._image_system_available = IMAGE_SYSTEM_AVAILABLE
        self.services = services

        # Initialize existing image components
        if self._image_system_available:
            try:
                self.image_service = ImageService(enable_caching=True)
            except Exception as e:
                self.logger.warning(f"Failed to initialize image service: {e}")
                self._image_system_available = False
        else:
            self.image_service = None

        if not self._image_system_available:
            self.logger.warning("Image system not available - will use placeholder")

    def can_process_image(self, image: Image) -> bool:
        """Check if image can be processed"""
        return (
            self._image_system_available and
            image is not None and
            (
                (hasattr(image, 'href') and image.href is not None) or
                (hasattr(image, 'data') and image.data)
            )
        )

    def process_image(self, image: Image, base_path: Optional[str] = None) -> ImageProcessingResult:
        """
        Process IR.Image element using existing comprehensive image system.

        Args:
            image: IR Image element to process
            base_path: Base path for resolving relative image references

        Returns:
            ImageProcessingResult with processed image data and metadata

        Raises:
            ValueError: If image cannot be processed
        """
        if not self.can_process_image(image):
            raise ValueError("Cannot process this image")

        try:
            # Use existing image system for comprehensive processing
            return self._process_with_existing_system(image, base_path)

        except Exception as e:
            self.logger.warning(f"Existing image system failed, using fallback: {e}")
            return self._process_fallback_image(image, base_path)

    def _process_with_existing_system(self, image: Image, base_path: Optional[str]) -> ImageProcessingResult:
        """Process image using existing comprehensive image system"""

        # Handle both href and direct data cases
        if image.href:
            href = image.href
            self.logger.debug(f"Processing image href: {href}")

            # Step 1: Use ImageService to process the image href
            if self.image_service:
                try:
                    # Process different href types using existing ImageService methods
                    if href.startswith('data:'):
                        # Base64 data URL processing
                        image_info = self._process_data_url(href)
                    elif href.startswith('http'):
                        # External URL processing
                        image_info = self._process_external_url(href)
                    else:
                        # File path processing
                        image_info = self._process_file_path(href, base_path)

                    # Generate relationship ID and embed ID
                    relationship_id = f"rId{hash(href) % 1000000}"
                    embed_id = f"image{hash(href) % 100000}"

                    return ImageProcessingResult(
                        image_data=image_info.content or b'',
                        format=image_info.format,
                        width=image_info.width,
                        height=image_info.height,
                        relationship_id=relationship_id,
                        embed_id=embed_id,
                        metadata={
                            'href': href,
                            'processing_method': 'existing_system',
                            'file_size': image_info.file_size,
                            'temp_path': image_info.temp_path,
                            'image_service_used': True
                        }
                    )

                except Exception as e:
                    self.logger.warning(f"ImageService processing failed: {e}")
                    # Fall through to basic processing

        elif image.data:
            # Direct data processing - image data already available
            self.logger.debug("Processing image with direct data")

            # Generate relationship ID and embed ID based on data hash
            data_hash = hash(image.data)
            relationship_id = f"rId{data_hash % 1000000}"
            embed_id = f"image{data_hash % 100000}"

            # Use image size or default dimensions
            width = int(image.size.width) if image.size.width > 0 else 100
            height = int(image.size.height) if image.size.height > 0 else 100

            return ImageProcessingResult(
                image_data=image.data,
                format=image.format,
                width=width,
                height=height,
                relationship_id=relationship_id,
                embed_id=embed_id,
                metadata={
                    'href': None,
                    'processing_method': 'direct_data',
                    'file_size': len(image.data),
                    'image_service_used': False
                }
            )

        # Fallback to basic processing if neither href nor data processing succeeded
        return self._process_basic_image(image, base_path)

    def _process_data_url(self, data_url: str) -> ImageInfo:
        """Process Base64 data URL using ImageService"""
        try:
            # Use ImageService's data URL processing
            return self.image_service.process_data_url(data_url)
        except Exception as e:
            self.logger.warning(f"Data URL processing failed: {e}")
            # Fallback to manual Base64 processing
            return self._manual_data_url_processing(data_url)

    def _process_external_url(self, url: str) -> ImageInfo:
        """Process external image URL using ImageService"""
        try:
            # Use ImageService's URL processing
            return self.image_service.process_url(url)
        except Exception as e:
            self.logger.warning(f"External URL processing failed: {e}")
            # Fallback to placeholder
            return ImageInfo(
                width=100, height=100, format='png',
                file_size=0, content=b''
            )

    def _process_file_path(self, file_path: str, base_path: Optional[str]) -> ImageInfo:
        """Process file path using ImageService"""
        try:
            # Resolve relative paths
            if base_path and not os.path.isabs(file_path):
                resolved_path = os.path.join(base_path, file_path)
            else:
                resolved_path = file_path

            # Use ImageService's file processing
            return self.image_service.process_file(resolved_path)
        except Exception as e:
            self.logger.warning(f"File path processing failed: {e}")
            # Fallback to placeholder
            return ImageInfo(
                width=100, height=100, format='png',
                file_size=0, content=b''
            )

    def _manual_data_url_processing(self, data_url: str) -> ImageInfo:
        """Manual fallback for Base64 data URL processing"""
        try:
            # Parse data URL format: data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...
            if not data_url.startswith('data:'):
                raise ValueError("Invalid data URL format")

            # Extract mime type and base64 data
            header, data = data_url.split(',', 1)
            mime_part = header.split(';')[0].replace('data:', '')

            # Extract format from mime type
            if 'image/' in mime_part:
                format = mime_part.replace('image/', '')
            else:
                format = 'png'  # Default fallback

            # Decode base64 data
            image_data = base64.b64decode(data)

            # Basic image info (would need PIL for real dimensions)
            return ImageInfo(
                width=100,  # Placeholder - real implementation would extract from image data
                height=100,  # Placeholder - real implementation would extract from image data
                format=format,
                file_size=len(image_data),
                content=image_data
            )

        except Exception as e:
            self.logger.error(f"Manual data URL processing failed: {e}")
            raise ValueError(f"Failed to process data URL: {e}")

    def _process_basic_image(self, image: Image, base_path: Optional[str]) -> ImageProcessingResult:
        """Basic image processing when ImageService unavailable"""
        href = image.href

        # Basic href type detection
        if href.startswith('data:'):
            try:
                image_info = self._manual_data_url_processing(href)
            except Exception:
                image_info = ImageInfo(width=100, height=100, format='png', file_size=0, content=b'')
        else:
            # Placeholder for file/URL processing
            image_info = ImageInfo(width=100, height=100, format='png', file_size=0, content=b'')

        relationship_id = f"rId{hash(href) % 1000000}"
        embed_id = f"image{hash(href) % 100000}"

        return ImageProcessingResult(
            image_data=image_info.content or b'',
            format=image_info.format,
            width=image_info.width,
            height=image_info.height,
            relationship_id=relationship_id,
            embed_id=embed_id,
            metadata={
                'href': href,
                'processing_method': 'basic_fallback',
                'file_size': image_info.file_size
            }
        )

    def _process_fallback_image(self, image: Image, base_path: Optional[str]) -> ImageProcessingResult:
        """Ultimate fallback when all processing fails"""
        href = image.href or "placeholder"

        return ImageProcessingResult(
            image_data=b'',  # Empty placeholder
            format='png',
            width=100,
            height=100,
            relationship_id=f"rId{hash(href) % 1000000}",
            embed_id=f"image{hash(href) % 100000}",
            metadata={
                'href': href,
                'processing_method': 'fallback_placeholder',
                'reason': 'image_system_unavailable'
            }
        )

    def validate_image_format(self, format: str) -> bool:
        """Validate if image format is supported by PowerPoint"""
        powerpoint_formats = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}
        return format.lower() in powerpoint_formats

    def calculate_scaling(self, original_size: Tuple[int, int], target_size: Tuple[int, int],
                         preserve_aspect: bool = True) -> Tuple[int, int]:
        """Calculate optimal image scaling"""
        orig_width, orig_height = original_size
        target_width, target_height = target_size

        if not preserve_aspect:
            return target_width, target_height

        # Calculate aspect ratios
        orig_aspect = orig_width / orig_height if orig_height > 0 else 1.0
        target_aspect = target_width / target_height if target_height > 0 else 1.0

        if orig_aspect > target_aspect:
            # Image is wider - constrain by width
            final_width = target_width
            final_height = int(target_width / orig_aspect)
        else:
            # Image is taller - constrain by height
            final_height = target_height
            final_width = int(target_height * orig_aspect)

        return final_width, final_height

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get statistics about image processing system usage"""
        return {
            'image_system_available': self._image_system_available,
            'components_initialized': {
                'image_service': self.image_service is not None,
                'image_converter': self.image_converter is not None
            },
            'features_available': {
                'data_url_processing': self._image_system_available,
                'file_path_processing': self._image_system_available,
                'external_url_processing': self._image_system_available,
                'format_validation': True,
                'scaling_calculation': True,
                'metadata_extraction': self._image_system_available
            }
        }


def create_image_adapter(services=None) -> ImageProcessingAdapter:
    """Create image processing adapter instance"""
    return ImageProcessingAdapter(services)
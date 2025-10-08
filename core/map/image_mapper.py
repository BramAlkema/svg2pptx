#!/usr/bin/env python3
"""
Image Mapper

Maps IR.Image elements to DrawingML with optimized format conversion
and embedding strategies.
"""

import logging
import time
from typing import Any, Dict

from ..ir import ClipRef, Image, IRElement
from ..policy import ImageDecision, Policy
from .base import Mapper, MapperResult, MappingError, OutputFormat

logger = logging.getLogger(__name__)


class ImageMapper(Mapper):
    """
    Maps IR.Image elements to DrawingML output.

    Handles format conversion, embedding optimization, and relationship
    management for raster and vector images.
    """

    def __init__(self, policy: Policy, services=None):
        """
        Initialize image mapper.

        Args:
            policy: Policy engine for decision making
            services: Optional services for image processing integration
        """
        super().__init__(policy)
        self.logger = logging.getLogger(__name__)
        self.services = services

        # Initialize image processing adapter
        try:
            from .image_adapter import create_image_adapter
            self.image_adapter = create_image_adapter(services)
            self._has_image_adapter = True
        except ImportError:
            self.image_adapter = None
            self._has_image_adapter = False
            self.logger.warning("Image adapter not available - using fallback processing")

        # Image format compatibility
        self._powerpoint_formats = {'png', 'jpg', 'gif', 'bmp', 'tiff'}
        self._vector_formats = {'svg'}

        # Relationship counter for unique IDs
        self._rel_id_counter = 1

    def can_map(self, element: IRElement) -> bool:
        """Check if element is an Image"""
        return isinstance(element, Image)

    def map(self, image: Image) -> MapperResult:
        """
        Map Image element to appropriate output format.

        Args:
            image: Image IR element

        Returns:
            MapperResult with DrawingML content

        Raises:
            MappingError: If mapping fails
        """
        start_time = time.perf_counter()

        try:
            # Get policy decision (images typically go to EMF for best fidelity)
            decision = self.policy.decide_image(image)

            # Always map images as embedded pictures for best compatibility
            result = self._map_to_picture(image, decision)

            # Record timing
            result.processing_time_ms = (time.perf_counter() - start_time) * 1000

            # Record statistics
            self._record_mapping(result)

            return result

        except Exception as e:
            self._record_error(e)
            raise MappingError(f"Failed to map image: {e}", element=image, cause=e)

    def _map_to_picture(self, image: Image, decision: ImageDecision) -> MapperResult:
        """Map image to PowerPoint picture shape"""
        try:
            # Process image using image adapter if available
            if self._has_image_adapter and self.image_adapter.can_process_image(image):
                try:
                    processing_result = self.image_adapter.process_image(image)

                    # Use processed image data and metadata
                    processed_data = processing_result.image_data
                    processed_format = processing_result.format
                    processed_width = processing_result.width
                    processed_height = processing_result.height
                    rel_id = processing_result.relationship_id

                    # Calculate positioning - use processed dimensions if available
                    if processed_width > 0 and processed_height > 0:
                        # Apply scaling calculation if needed
                        target_size = (int(image.size.width), int(image.size.height))
                        if target_size != (processed_width, processed_height):
                            scaled_width, scaled_height = self.image_adapter.calculate_scaling(
                                (processed_width, processed_height), target_size, preserve_aspect=True,
                            )
                        else:
                            scaled_width, scaled_height = processed_width, processed_height
                    else:
                        scaled_width, scaled_height = int(image.size.width), int(image.size.height)

                    x_emu = int(image.origin.x * 12700)  # Convert to EMU
                    y_emu = int(image.origin.y * 12700)
                    width_emu = int(scaled_width * 12700)
                    height_emu = int(scaled_height * 12700)

                    image_adapter_used = True
                    processing_metadata = processing_result.metadata

                except Exception as e:
                    self.logger.warning(f"Image adapter processing failed: {e}")
                    # Fall back to basic processing
                    processed_data = image.data
                    processed_format = image.format
                    rel_id = f"rId{self._rel_id_counter}"
                    self._rel_id_counter += 1

                    x_emu = int(image.origin.x * 12700)
                    y_emu = int(image.origin.y * 12700)
                    width_emu = int(image.size.width * 12700)
                    height_emu = int(image.size.height * 12700)

                    image_adapter_used = False
                    processing_metadata = {'processing_method': 'fallback'}
            else:
                # Basic processing without image adapter
                processed_data = image.data
                processed_format = image.format
                rel_id = f"rId{self._rel_id_counter}"
                self._rel_id_counter += 1

                x_emu = int(image.origin.x * 12700)
                y_emu = int(image.origin.y * 12700)
                width_emu = int(image.size.width * 12700)
                height_emu = int(image.size.height * 12700)

                image_adapter_used = False
                processing_metadata = {'processing_method': 'basic'}

            # Generate clipping XML if needed
            clip_xml = ""
            clip_meta = None
            clip_media_files = None
            if image.clip:
                clip_xml, clip_meta = self._generate_image_clip_xml(image.clip, image)
                if clip_meta and 'media_files' in clip_meta:
                    clip_media_files = clip_meta.pop('media_files')

            # Generate opacity if needed
            opacity_xml = ""
            if image.opacity < 1.0:
                opacity_val = int(image.opacity * 100000)
                opacity_xml = f'<a:effectLst><a:alpha val="{opacity_val}"/></a:effectLst>'

            # Handle different image formats
            if processed_format in self._vector_formats:
                # Vector images (SVG) - typically need conversion or EMF
                xml_content = self._generate_vector_image_xml(
                    image, rel_id, x_emu, y_emu, width_emu, height_emu,
                    clip_xml, opacity_xml,
                )
                output_format = OutputFormat.EMF_VECTOR
            else:
                # Raster images - direct embedding
                xml_content = self._generate_raster_image_xml(
                    image, rel_id, x_emu, y_emu, width_emu, height_emu,
                    clip_xml, opacity_xml,
                )
                output_format = OutputFormat.EMF_RASTER

            # Prepare media files for embedding
            media_files = [{
                'relationship_id': rel_id,
                'data': processed_data,
                'format': processed_format,
                'content_type': self._get_content_type(processed_format),
            }] if processed_data else None

            if clip_media_files:
                if media_files:
                    media_files.extend(clip_media_files)
                else:
                    media_files = clip_media_files

            return MapperResult(
                element=image,
                output_format=output_format,
                xml_content=xml_content,
                policy_decision=decision,
                media_files=media_files,
                metadata={
                    'format': processed_format,
                    'size_bytes': len(processed_data) if processed_data else 0,
                    'dimensions': (image.size.width, image.size.height),
                    'has_transparency': processed_format in ['png', 'gif'],
                    'relationship_id': rel_id,
                    'requires_conversion': processed_format in self._vector_formats,
                    'has_clipping': image.clip is not None,
                    'clip_strategy': clip_meta.get('strategy') if clip_meta else None,
                    'clip_complexity': clip_meta.get('complexity') if clip_meta else None,
                    'clip_bridge': clip_meta.get('bridge') if clip_meta else None,
                    'clip_structured_strategy': clip_meta.get('structured_strategy') if clip_meta else None,
                    'clip_structured_kind': clip_meta.get('structured_kind') if clip_meta else None,
                    'clip_structured_used_bbox': clip_meta.get('structured_used_bbox') if clip_meta else None,
                    'clip_media_meta': clip_meta.get('media_meta') if clip_meta else None,
                    'clip_media_files': clip_media_files,
                    'has_opacity': image.opacity < 1.0,
                    'image_adapter_used': image_adapter_used,
                    'processing_metadata': processing_metadata,
                },
                estimated_quality=decision.estimated_quality or 0.98,
                estimated_performance=decision.estimated_performance or 0.9,
                output_size_bytes=len(xml_content.encode('utf-8')),
            )

        except Exception as e:
            raise MappingError(f"Failed to generate picture for image: {e}", image, e)

    def _generate_raster_image_xml(self, image: Image, rel_id: str,
                                 x_emu: int, y_emu: int, width_emu: int, height_emu: int,
                                 clip_xml: str, opacity_xml: str) -> str:
        """Generate XML for raster image (PNG, JPG, etc.)"""

        effects_xml = opacity_xml

        xml_content = f"""<p:pic>
    <p:nvPicPr>
        <p:cNvPr id="1" name="Image"/>
        <p:cNvPicPr>
            <a:picLocks noChangeAspect="1"/>
        </p:cNvPicPr>
        <p:nvPr/>
    </p:nvPicPr>
    <p:blipFill>
        <a:blip r:embed="{rel_id}">
            <a:extLst>
                <a:ext uri="{{28A0092B-C50C-407E-A947-70E740481C1C}}">
                    <a14:useLocalDpi xmlns:a14="http://schemas.microsoft.com/office/drawing/2010/main" val="0"/>
                </a:ext>
            </a:extLst>
        </a:blip>
        <a:stretch>
            <a:fillRect/>
        </a:stretch>
    </p:blipFill>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{width_emu}" cy="{height_emu}"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
        {clip_xml}
        {effects_xml}
    </p:spPr>
</p:pic>"""

        return xml_content

    def _generate_vector_image_xml(self, image: Image, rel_id: str,
                                 x_emu: int, y_emu: int, width_emu: int, height_emu: int,
                                 clip_xml: str, opacity_xml: str) -> str:
        """Generate XML for vector image (SVG) - typically requires EMF conversion"""

        effects_xml = opacity_xml

        # Vector images are rendered as EMF for best fidelity
        xml_content = f"""<p:pic>
    <p:nvPicPr>
        <p:cNvPr id="1" name="VectorImage"/>
        <p:cNvPicPr>
            <a:picLocks noChangeAspect="1"/>
        </p:cNvPicPr>
        <p:nvPr/>
    </p:nvPicPr>
    <p:blipFill>
        <a:blip r:embed="{rel_id}">
            <a:extLst>
                <a:ext uri="{{A7D7AC89-857B-4B46-9C2E-2B86D7B4E2B4}}">
                    <emf:emfBlip xmlns:emf="http://schemas.microsoft.com/office/drawing/2010/emf"/>
                </a:ext>
            </a:extLst>
        </a:blip>
        <a:stretch>
            <a:fillRect/>
        </a:stretch>
    </p:blipFill>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{width_emu}" cy="{height_emu}"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
        {clip_xml}
        {effects_xml}
    </p:spPr>
</p:pic>"""

        return xml_content

    def _generate_image_clip_xml(self, clip_ref: Any, image: Image | None = None) -> tuple[str, dict | None]:
        """Generate image clipping XML"""
        if not clip_ref:
            return "", None

        if isinstance(clip_ref, ClipRef) and clip_ref.path_segments:
            try:
                from .clipping_adapter import create_clipping_adapter
                adapter = create_clipping_adapter(self.services)
                context = {'bounding_box': getattr(image, 'bbox', None)}
                effect_stack = getattr(image, 'effects', None)
                if effect_stack is None:
                    effect_stack = getattr(image, 'effect_stack', None)
                if effect_stack is not None:
                    context['effect_stack'] = effect_stack
                result = adapter.generate_clip_xml(clip_ref, context)

                clip_meta = {
                    'strategy': result.strategy,
                    'complexity': result.complexity,
                }
                metadata = result.metadata or {}
                if 'bridge' in metadata:
                    clip_meta['bridge'] = metadata['bridge']
                if 'structured_strategy' in metadata:
                    clip_meta['structured_strategy'] = metadata['structured_strategy']
                structured_result = metadata.get('structured_result')
                if structured_result is not None:
                    clip_meta['structured_kind'] = getattr(getattr(structured_result, 'strategy', None), 'value', None)
                    clip_meta['structured_used_bbox'] = getattr(structured_result, 'used_bbox_rect', None)
                media_files = metadata.get('media_files')
                if media_files:
                    clip_meta['media_files'] = media_files
                if 'media_meta' in metadata:
                    clip_meta['media_meta'] = metadata['media_meta']

                return result.xml_content, clip_meta
            except Exception as exc:
                self.logger.debug(f"Image clipping adapter fallback: {exc}")

        clip_id = getattr(clip_ref, 'clip_id', None)
        if isinstance(clip_id, str) and clip_id.startswith("bbox:"):
            try:
                _, _x, _y, width, height = clip_id.split(':')
                width_emu = int(float(width) * 12700)
                height_emu = int(float(height) * 12700)
                return f"""<a:clipPath>
            <a:path>
                <a:moveTo><a:pt x="0" y="0"/></a:moveTo>
                <a:lnTo><a:pt x="{width_emu}" y="0"/></a:lnTo>
                <a:lnTo><a:pt x="{width_emu}" y="{height_emu}"/></a:lnTo>
                <a:lnTo><a:pt x="0" y="{height_emu}"/></a:lnTo>
                <a:close/>
            </a:path>
        </a:clipPath>""", {'strategy': 'bbox'}
            except ValueError:
                self.logger.debug(f"Unable to parse bbox clip id: {clip_id}")

        return f'<!-- Image clipping: {clip_id or clip_ref} -->', {'strategy': 'fallback'}

    def _get_content_type(self, format: str) -> str:
        """Get MIME content type for image format"""
        content_type_map = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'tiff': 'image/tiff',
            'svg': 'application/emf',  # SVG converted to EMF
        }
        return content_type_map.get(format.lower(), 'application/octet-stream')

    def get_relationship_data(self, image: Image) -> dict[str, Any]:
        """
        Get relationship data for embedding image in PPTX.

        Args:
            image: Image IR element

        Returns:
            Relationship data for PPTX package
        """
        # Determine content type
        content_type_map = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'tiff': 'image/tiff',
            'svg': 'application/emf',  # SVG converted to EMF
        }

        content_type = content_type_map.get(image.format, 'application/octet-stream')

        return {
            'target': f"../media/image{self._rel_id_counter}.{image.format}",
            'type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image',
            'content_type': content_type,
            'data': image.data,
            'format': image.format,
        }

    def supports_format(self, format: str) -> bool:
        """Check if image format is supported"""
        return format.lower() in (self._powerpoint_formats | self._vector_formats)

    def get_format_statistics(self) -> dict[str, int]:
        """Get image format processing statistics"""
        # This would be enhanced to track format-specific stats
        stats = self.get_statistics()
        return {
            'total_images': stats['total_mapped'],
            'raster_images': stats.get('raster_count', 0),
            'vector_images': stats.get('vector_count', 0),
            'conversion_required': stats.get('conversion_count', 0),
        }


def create_image_mapper(policy: Policy, services=None) -> ImageMapper:
    """
    Create ImageMapper with policy engine.

    Args:
        policy: Policy engine for decisions
        services: Optional services for image processing integration

    Returns:
        Configured ImageMapper
    """
    return ImageMapper(policy, services)

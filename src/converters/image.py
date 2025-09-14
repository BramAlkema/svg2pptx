"""
ImageConverter for handling SVG <image> elements.
Converts SVG images to PowerPoint image shapes with proper positioning and scaling.
"""

from lxml import etree as ET
import base64
import os
from typing import Optional, Tuple
from urllib.parse import urlparse
import tempfile

from .base import BaseConverter, ConversionContext
from ..units import UnitConverter
from ..transforms import TransformParser
from ..viewbox import ViewportResolver


class ImageConverter(BaseConverter):
    """Converter for SVG image elements."""
    
    supported_elements = ['image']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        tag = self.get_element_tag(element)
        return tag == 'image'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG image to DrawingML."""
        # Extract image attributes using UnitConverter
        x_str = element.get('x', '0')
        y_str = element.get('y', '0')
        width_str = element.get('width', '0')
        height_str = element.get('height', '0')
        
        # Use inherited parse_length method from BaseConverter
        x = self.parse_length(x_str)
        y = self.parse_length(y_str)
        width = self.parse_length(width_str)
        height = self.parse_length(height_str)
        
        # Get image source
        href = element.get('href') or element.get('{http://www.w3.org/1999/xlink}href', '')
        if not href:
            return '<!-- Image element missing href attribute -->'
        
        # Convert position using ViewportResolver if available
        emu_x, emu_y = self._convert_svg_to_drawingml_coords(x, y, context)
        
        # Convert dimensions
        emu_width = context.coordinate_system.svg_length_to_emu(width, 'x')
        emu_height = context.coordinate_system.svg_length_to_emu(height, 'y')
        
        # Process image source and get embed ID
        image_embed_id = self._process_image_source(href, context)
        if not image_embed_id:
            return '<!-- Unable to process image source -->'
        
        # Get style attributes
        opacity = self.get_attribute_with_style(element, 'opacity', '1')
        
        # Handle transforms
        transform = element.get('transform')
        transform_xml = self._generate_transform(transform, context) if transform else ''
        
        # Get shape ID
        shape_id = context.get_next_shape_id()
        
        # Generate alpha (transparency) value
        alpha_value = int(float(opacity) * 100000)
        alpha_xml = f'<a:alpha val="{alpha_value}"/>' if float(opacity) < 1.0 else ''
        
        return f'''
        <p:pic>
            <p:nvPicPr>
                <p:cNvPr id="{shape_id}" name="Image {shape_id}"/>
                <p:cNvPicPr>
                    <a:picLocks noChangeAspect="1"/>
                </p:cNvPicPr>
                <p:nvPr/>
            </p:nvPicPr>
            <p:blipFill>
                <a:blip r:embed="{image_embed_id}">
                    {alpha_xml}
                </a:blip>
                <a:stretch>
                    <a:fillRect/>
                </a:stretch>
            </p:blipFill>
            <p:spPr>
                {transform_xml}
                <a:xfrm>
                    <a:off x="{emu_x}" y="{emu_y}"/>
                    <a:ext cx="{emu_width}" cy="{emu_height}"/>
                </a:xfrm>
            </p:spPr>
        </p:pic>'''
    
    def _convert_svg_to_drawingml_coords(self, x: float, y: float, context: ConversionContext) -> Tuple[int, int]:
        """Convert SVG coordinates to DrawingML EMUs using ViewportResolver if available."""
        # Use ViewportResolver if available in context
        if hasattr(context, 'viewport_mapping') and context.viewport_mapping is not None:
            return context.viewport_mapping.svg_to_emu(x, y)
        
        # Fallback to standard coordinate system conversion
        return context.coordinate_system.svg_to_emu(x, y)
    
    def _generate_transform(self, transform: str, context: ConversionContext) -> str:
        """Generate DrawingML transform from SVG transform."""
        # This is a placeholder - full implementation would use TransformParser
        return ''
    
    def _process_image_source(self, href: str, context: ConversionContext) -> Optional[str]:
        """Process image source and return embed ID for PowerPoint."""
        try:
            if href.startswith('data:'):
                # Handle data URLs (base64 encoded images)
                return self._process_data_url(href, context)
            elif href.startswith('http://') or href.startswith('https://'):
                # Handle web URLs
                return self._process_web_url(href, context)
            else:
                # Handle relative file paths
                return self._process_file_path(href, context)
        except Exception as e:
            # Log error and return None for graceful degradation
            if hasattr(context, 'logger'):
                context.logger.warning(f"Failed to process image source '{href}': {e}")
            return None
    
    def _process_data_url(self, data_url: str, context: ConversionContext) -> Optional[str]:
        """Process data URL and extract image data."""
        try:
            # Parse data URL: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...
            if ';base64,' not in data_url:
                return None
            
            header, data = data_url.split(';base64,', 1)
            mime_type = header.split(':', 1)[1]
            
            # Decode base64 data
            image_data = base64.b64decode(data)
            
            # Determine file extension from MIME type
            extension_map = {
                'image/png': '.png',
                'image/jpeg': '.jpg',
                'image/jpg': '.jpg',
                'image/gif': '.gif',
                'image/bmp': '.bmp',
                'image/webp': '.webp'
            }
            extension = extension_map.get(mime_type, '.png')
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
                temp_file.write(image_data)
                temp_path = temp_file.name
            
            # Add to PowerPoint as embedded image
            embed_id = self._add_image_to_pptx(temp_path, context)
            
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
            
            return embed_id
            
        except Exception:
            return None
    
    def _process_web_url(self, url: str, context: ConversionContext) -> Optional[str]:
        """Process web URL image source."""
        # For web URLs, we would need to download the image
        # This is a placeholder implementation
        if hasattr(context, 'download_web_image'):
            return context.download_web_image(url)
        return None
    
    def _process_file_path(self, file_path: str, context: ConversionContext) -> Optional[str]:
        """Process local file path image source."""
        try:
            # Resolve relative paths
            if hasattr(context, 'base_path'):
                full_path = os.path.join(context.base_path, file_path)
            else:
                full_path = file_path
            
            if os.path.exists(full_path):
                return self._add_image_to_pptx(full_path, context)
            
            return None
        except Exception:
            return None
    
    def _add_image_to_pptx(self, image_path: str, context: ConversionContext) -> Optional[str]:
        """Add image to PowerPoint and return embed ID."""
        # This would integrate with the PowerPoint generation system
        # For now, return a placeholder embed ID
        if hasattr(context, 'add_image'):
            return context.add_image(image_path)
        
        # Generate a placeholder embed ID based on image path
        import hashlib
        hash_obj = hashlib.md5(image_path.encode())
        return f"rId{hash_obj.hexdigest()[:8]}"
    
    def _get_image_dimensions(self, image_path: str) -> Tuple[int, int]:
        """Get image dimensions in pixels."""
        try:
            # This would use PIL or similar to get actual image dimensions
            # For now, return default dimensions
            return (800, 600)
        except Exception:
            return (800, 600)
    
    def _preserve_aspect_ratio(self, original_width: int, original_height: int, 
                             target_width: float, target_height: float) -> Tuple[float, float]:
        """Preserve aspect ratio when scaling image."""
        if original_width == 0 or original_height == 0:
            return target_width, target_height
        
        aspect_ratio = original_width / original_height
        
        # Scale to fit within target dimensions while preserving aspect ratio
        if target_width / target_height > aspect_ratio:
            # Target is wider than image, scale by height
            new_height = target_height
            new_width = new_height * aspect_ratio
        else:
            # Target is taller than image, scale by width
            new_width = target_width
            new_height = new_width / aspect_ratio
        
        return new_width, new_height
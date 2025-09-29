"""
Test suite for ImageConverter.
Tests image handling, data URLs, file paths, and ViewportEngine integration.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from lxml import etree as ET
import base64
import tempfile
import os

from src.converters.image import ImageConverter
from src.converters.base import ConversionContext


class TestImageConverter:
    """Test suite for ImageConverter functionality."""
    
    @pytest.fixture
    def converter(self):
        """Create an ImageConverter instance."""
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        # Configure image_service mock
        mock_services.image_service = Mock()

        # Create mock image info object with width/height attributes
        mock_image_info = Mock()
        mock_image_info.width = 100
        mock_image_info.height = 80
        mock_image_info.path = 'test.png'
        mock_image_info.format = 'PNG'

        mock_services.image_service.process_image_source = Mock(return_value=mock_image_info)
        mock_services.image_service.generate_embed_id = Mock(return_value='rId123')

        return ImageConverter(services=mock_services)
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock ConversionContext with necessary attributes."""
        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu = Mock(return_value=(914400, 914400))
        context.coordinate_system.svg_length_to_emu = Mock(return_value=914400)
        context.get_next_shape_id = Mock(return_value=1)
        context.add_image = Mock(return_value="rId123")
        return context
    
    def test_can_convert_image_element(self, converter):
        """Test that converter can handle image elements."""
        element = ET.fromstring('<image href="test.png"/>')
        assert converter.can_convert(element) is True
        
        non_image = ET.fromstring('<rect/>')
        assert converter.can_convert(non_image) is False
    
    def test_basic_image_conversion(self, converter, mock_context):
        """Test basic image conversion with file path."""
        element = ET.fromstring('<image x="10" y="20" width="100" height="80" href="test.png"/>')
        
        with patch('os.path.exists', return_value=True):
            result = converter.convert(element, mock_context)
        
        assert '<p:pic>' in result
        assert '<p:cNvPr id="1" name="Image 1"/>' in result
        assert '<a:off x="914400" y="914400"/>' in result
        assert '<a:ext cx="914400" cy="914400"/>' in result
        assert 'r:embed="rId123"' in result
    
    def test_viewport_resolver_integration(self, converter, mock_context):
        """Test ViewportEngine integration for coordinate mapping."""
        element = ET.fromstring('<image x="50" y="100" width="200" height="150" href="test.jpg"/>')
        
        # Mock ViewportEngine integration through context
        viewport_mapping = Mock()
        viewport_mapping.svg_to_emu = Mock(return_value=(1828800, 3657600))
        mock_context.viewport_mapping = viewport_mapping
        
        with patch('os.path.exists', return_value=True):
            result = converter.convert(element, mock_context)
        
        # Verify ViewportEngine was used for coordinate conversion
        viewport_mapping.svg_to_emu.assert_called_once_with(50.0, 100.0)
        assert '<a:off x="1828800" y="3657600"/>' in result
    
    def test_viewport_resolver_fallback(self, converter, mock_context):
        """Test fallback to standard coordinate system when ViewportEngine not available."""
        element = ET.fromstring('<image x="10" y="20" width="100" height="80" href="test.png"/>')
        
        # No ViewportEngine in context
        mock_context.viewport_mapping = None
        
        with patch('os.path.exists', return_value=True):
            result = converter.convert(element, mock_context)
        
        # Should use standard coordinate system
        mock_context.coordinate_system.svg_to_emu.assert_called_once_with(10.0, 20.0)
        assert '<p:pic>' in result
    
    def test_data_url_processing(self, converter, mock_context):
        """Test processing of base64 data URLs."""
        # Create a simple base64 encoded image (1x1 pixel PNG)
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        b64_data = base64.b64encode(png_data).decode('utf-8')
        data_url = f'data:image/png;base64,{b64_data}'
        
        element = ET.fromstring(f'<image x="0" y="0" width="100" height="100" href="{data_url}"/>')
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test_image.png'
            mock_temp.return_value.__enter__.return_value.write = Mock()
            
            with patch('os.unlink'):
                result = converter.convert(element, mock_context)
        
        assert '<p:pic>' in result
        assert 'r:embed=' in result
    
    def test_missing_href_attribute(self, converter, mock_context):
        """Test handling of image element without href attribute."""
        element = ET.fromstring('<image x="0" y="0" width="100" height="100"/>')
        
        result = converter.convert(element, mock_context)
        
        assert '<!-- Image element missing href attribute -->' in result
    
    def test_xlink_href_attribute(self, converter, mock_context):
        """Test handling of xlink:href attribute (SVG 1.1)."""
        element = ET.fromstring('<image x="0" y="0" width="100" height="100" xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="test.png"/>')
        
        with patch('os.path.exists', return_value=True):
            result = converter.convert(element, mock_context)
        
        assert '<p:pic>' in result
        assert 'r:embed="rId123"' in result
    
    def test_opacity_handling(self, converter, mock_context):
        """Test opacity attribute handling."""
        element = ET.fromstring('<image x="0" y="0" width="100" height="100" href="test.png" opacity="0.5"/>')
        
        with patch('os.path.exists', return_value=True):
            result = converter.convert(element, mock_context)
        
        # Should include alpha value (50% = 50000)
        assert '<a:alpha val="50000"/>' in result
    
    def test_full_opacity_no_alpha(self, converter, mock_context):
        """Test that full opacity doesn't add alpha element."""
        element = ET.fromstring('<image x="0" y="0" width="100" height="100" href="test.png" opacity="1.0"/>')
        
        result = converter.convert(element, mock_context)
        
        # Should not include alpha element for full opacity
        assert '<a:alpha' not in result
    
    def test_transform_handling(self, converter, mock_context):
        """Test transform attribute handling."""
        element = ET.fromstring('<image x="0" y="0" width="100" height="100" href="test.png" transform="rotate(45)"/>')
        
        # Mock transform generation
        converter._generate_transform = Mock(return_value='<a:xfrm rot="2700000"/>')
        
        with patch('os.path.exists', return_value=True):
            result = converter.convert(element, mock_context)
        
        # Verify transform was processed
        converter._generate_transform.assert_called_once_with('rotate(45)', mock_context)
        assert '<a:xfrm' in result
    
    def test_web_url_processing(self, converter, mock_context):
        """Test processing of web URLs."""
        element = ET.fromstring('<image x="0" y="0" width="100" height="100" href="https://example.com/image.jpg"/>')

        # Configure image service to handle web URLs and return different embed ID
        mock_image_info = Mock()
        mock_image_info.width = 100
        mock_image_info.height = 80
        mock_image_info.path = 'https://example.com/image.jpg'
        mock_image_info.format = 'JPEG'

        converter.services.image_service.process_image_source.return_value = mock_image_info
        converter.services.image_service.generate_embed_id.return_value = 'rId456'

        result = converter.convert(element, mock_context)

        assert 'r:embed="rId456"' in result
    
    def test_web_url_without_downloader(self, converter, mock_context):
        """Test web URL handling when downloader not available."""
        element = ET.fromstring('<image x="0" y="0" width="100" height="100" href="https://example.com/image.jpg"/>')

        # Configure image service to return None for failed web URL download
        converter.services.image_service.process_image_source.return_value = None

        result = converter.convert(element, mock_context)

        assert '<!-- Unable to process image source -->' in result
    
    def test_relative_file_path_with_base_path(self, converter, mock_context):
        """Test relative file path resolution with base path."""
        element = ET.fromstring('<image x="0" y="0" width="100" height="100" href="images/test.png"/>')

        mock_context.base_path = '/path/to/svg'

        with patch('os.path.exists', return_value=True):
            result = converter.convert(element, mock_context)

        # Verify the image service was called with the resolved path
        converter.services.image_service.process_image_source.assert_called_once_with('images/test.png', '/path/to/svg')
        assert '<p:pic>' in result
    
    def test_nonexistent_file_path(self, converter, mock_context):
        """Test handling of nonexistent file paths."""
        element = ET.fromstring('<image x="0" y="0" width="100" height="100" href="nonexistent.png"/>')

        # Configure image service to return None for nonexistent file
        converter.services.image_service.process_image_source.return_value = None

        with patch('os.path.exists', return_value=False):
            result = converter.convert(element, mock_context)

        assert '<!-- Unable to process image source -->' in result
    
    def test_edge_case_zero_dimensions(self, converter, mock_context):
        """Test handling of image with zero dimensions."""
        element = ET.fromstring('<image x="0" y="0" width="0" height="0" href="test.png"/>')
        
        mock_context.coordinate_system.svg_length_to_emu = Mock(return_value=0)
        
        with patch('os.path.exists', return_value=True):
            result = converter.convert(element, mock_context)
        
        assert '<a:ext cx="0" cy="0"/>' in result
        assert '<p:pic>' in result
    
    def test_edge_case_missing_dimensions(self, converter, mock_context):
        """Test handling of image with missing width/height."""
        element = ET.fromstring('<image href="test.png"/>')
        
        with patch('os.path.exists', return_value=True):
            result = converter.convert(element, mock_context)
        
        # Should use default values (0)
        mock_context.coordinate_system.svg_to_emu.assert_called_once_with(0.0, 0.0)
        assert '<p:pic>' in result
    
    def test_invalid_data_url(self, converter, mock_context):
        """Test handling of invalid data URLs."""
        element = ET.fromstring('<image x="0" y="0" width="100" height="100" href="data:invalid"/>')

        # Configure image service to return None for invalid data URL
        converter.services.image_service.process_image_source.return_value = None

        result = converter.convert(element, mock_context)

        assert '<!-- Unable to process image source -->' in result
    
    def test_aspect_ratio_preservation(self, converter):
        """Test aspect ratio preservation utility method."""
        # Test landscape image (2:1 ratio)
        new_width, new_height = converter._preserve_aspect_ratio(200, 100, 150, 150)
        assert new_width == 150
        assert new_height == 75
        
        # Test portrait image (1:2 ratio)
        new_width, new_height = converter._preserve_aspect_ratio(100, 200, 150, 150)
        assert new_width == 75
        assert new_height == 150
        
        # Test square image
        new_width, new_height = converter._preserve_aspect_ratio(100, 100, 150, 150)
        assert new_width == 150
        assert new_height == 150
    
    def test_aspect_ratio_zero_dimensions(self, converter):
        """Test aspect ratio handling with zero original dimensions."""
        new_width, new_height = converter._preserve_aspect_ratio(0, 100, 150, 150)
        assert new_width == 150
        assert new_height == 150
        
        new_width, new_height = converter._preserve_aspect_ratio(100, 0, 150, 150)
        assert new_width == 150
        assert new_height == 150
    
    def test_shape_id_generation(self, converter, mock_context):
        """Test proper shape ID generation for images."""
        element = ET.fromstring('<image x="0" y="0" width="100" height="100" href="test.png"/>')
        
        # Test with different shape IDs
        for shape_id in [1, 42, 999]:
            mock_context.get_next_shape_id = Mock(return_value=shape_id)
            with patch('os.path.exists', return_value=True):
                result = converter.convert(element, mock_context)
            assert f'<p:cNvPr id="{shape_id}" name="Image {shape_id}"/>' in result
#!/usr/bin/env python3
"""
End-to-End Edge Case Tests for Image Pipeline

Tests the complete SVG → IR → Mapper → Embedder → PPTX pipeline
with strange but valid edge cases to ensure robustness.
"""

import pytest
import base64
from io import BytesIO
from unittest.mock import Mock
from lxml import etree as ET

from core.parse.parser import SVGParser
from core.map.image_mapper import ImageMapper
from core.io.embedder import DrawingMLEmbedder
from core.policy.engine import PolicyEngine
from core.policy.config import PolicyConfig


class MockPackageWriter:
    """Mock package writer for testing"""
    def __init__(self):
        self.files = {}

    def write_file(self, path, data):
        self.files[path] = data


# Test image data (1x1 pixel PNG)
TINY_PNG = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

# 1x1 transparent PNG
TRANSPARENT_PNG = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAEklEQVR42mNgYGD4z8DAwAAACQoCAf4b2vEAAAAASUVORK5CYII="
)


class TestImageEdgeCasesPipeline:
    """Test complete pipeline with edge cases"""

    def test_data_url_with_whitespace(self):
        """Test data URL with whitespace (should be trimmed)"""
        data_url = f"data:image/png;base64,{base64.b64encode(TINY_PNG).decode()}"

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
            <image x="  10  " y="  20  " width="50" height="50" href="  {data_url}  "/>
        </svg>'''

        # Parse to IR
        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)

        assert scene is not None
        assert len(scene) > 0

        # Find image
        image = None
        for child in scene:
            if hasattr(child, 'href'):
                image = child
                break

        assert image is not None
        assert image.source_type == "data_url"
        assert image.image_data is not None
        print(f"✅ Whitespace handling: image parsed with {len(image.image_data)} bytes")

    def test_multiple_images_same_data(self):
        """Test multiple images with identical data (deduplication)"""
        data_url = f"data:image/png;base64,{base64.b64encode(TINY_PNG).decode()}"

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
            <image x="0" y="0" width="50" height="50" href="{data_url}"/>
            <image x="60" y="0" width="50" height="50" href="{data_url}"/>
            <image x="120" y="0" width="50" height="50" href="{data_url}"/>
        </svg>'''

        # Parse to IR
        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)

        # Count images
        images = [c for c in scene if hasattr(c, 'href')]
        assert len(images) == 3

        # Map with policy
        config = PolicyConfig()
        policy = PolicyEngine(config)
        mapper = ImageMapper(policy)

        results = []
        for img in images:
            result = mapper.map(img)
            results.append(result)

        # Check deduplication tracking
        assert len(mapper._embedded_sha256) == 1, "Should track one unique SHA-256"

        # All should have media requests
        for result in results:
            assert len(result.media_requests) == 1

        print(f"✅ Deduplication: 3 images tracked as 1 unique SHA-256")

    def test_tiny_image_1x1(self):
        """Test 1x1 pixel image (minimum size)"""
        data_url = f"data:image/png;base64,{base64.b64encode(TINY_PNG).decode()}"

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg">
            <image x="0" y="0" width="1" height="1" href="{data_url}"/>
        </svg>'''

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)
        
        

        image = scene[0]
        assert image.width == 1
        assert image.height == 1
        assert image.image_data is not None

        config = PolicyConfig()
        policy = PolicyEngine(config)
        mapper = ImageMapper(policy)
        result = mapper.map(image)

        assert result.xml_content is not None
        assert "<p:pic" in result.xml_content
        print(f"✅ 1x1 pixel image: mapped successfully")

    def test_huge_coordinates(self):
        """Test image with very large coordinates"""
        data_url = f"data:image/png;base64,{base64.b64encode(TINY_PNG).decode()}"

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg">
            <image x="99999" y="88888" width="100" height="100" href="{data_url}"/>
        </svg>'''

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)
        
        

        image = scene[0]
        assert image.x == 99999
        assert image.y == 88888

        config = PolicyConfig()
        policy = PolicyEngine(config)
        mapper = ImageMapper(policy)
        result = mapper.map(image)

        # Check EMU conversion (9525 multiplier)
        parsed_xml = ET.fromstring(result.xml_content)
        off = parsed_xml.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}off")

        expected_x = str(int(99999 * 9525))
        expected_y = str(int(88888 * 9525))
        assert off.get("x") == expected_x
        assert off.get("y") == expected_y
        print(f"✅ Huge coordinates: {image.x},{image.y} → EMU {expected_x},{expected_y}")

    def test_fractional_dimensions(self):
        """Test image with fractional pixel dimensions"""
        data_url = f"data:image/png;base64,{base64.b64encode(TINY_PNG).decode()}"

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg">
            <image x="10.5" y="20.75" width="99.999" height="88.123" href="{data_url}"/>
        </svg>'''

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)
        
        

        image = scene[0]
        assert image.x == 10.5
        assert image.y == 20.75
        assert image.width == 99.999
        assert image.height == 88.123

        config = PolicyConfig()
        policy = PolicyEngine(config)
        mapper = ImageMapper(policy)
        result = mapper.map(image)

        assert result.xml_content is not None
        print(f"✅ Fractional dimensions: {image.width}x{image.height} handled")

    def test_xlink_href_legacy(self):
        """Test legacy xlink:href attribute (SVG 1.1)"""
        data_url = f"data:image/png;base64,{base64.b64encode(TINY_PNG).decode()}"

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
            <image x="0" y="0" width="50" height="50" xlink:href="{data_url}"/>
        </svg>'''

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)
        
        

        image = scene[0]
        assert image.href == data_url
        assert image.source_type == "data_url"
        assert image.image_data is not None
        print(f"✅ xlink:href (SVG 1.1): {len(image.image_data)} bytes loaded")

    def test_image_with_opacity(self):
        """Test image with opacity attribute"""
        data_url = f"data:image/png;base64,{base64.b64encode(TRANSPARENT_PNG).decode()}"

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg">
            <image x="0" y="0" width="50" height="50" opacity="0.5" href="{data_url}"/>
        </svg>'''

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)
        
        

        image = scene[0]
        assert image.opacity == 0.5
        assert image.image_data is not None

        config = PolicyConfig()
        policy = PolicyEngine(config)
        mapper = ImageMapper(policy)
        result = mapper.map(image)

        assert result.xml_content is not None
        print(f"✅ Opacity {image.opacity}: image mapped")

    def test_different_mime_types(self):
        """Test parsing different MIME types from data URLs"""
        test_cases = [
            ("image/jpeg", "jpg"),
            ("image/gif", "gif"),
            ("image/bmp", "bmp"),
            ("image/webp", "webp"),
        ]

        for mime_type, expected_ext in test_cases:
            data_url = f"data:{mime_type};base64,{base64.b64encode(TINY_PNG).decode()}"

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg">
                <image x="0" y="0" width="50" height="50" href="{data_url}"/>
            </svg>'''

            parser = SVGParser()
            scene, parse_result = parser.parse_to_ir(svg)
            
            

            image = scene[0]
            assert image.mime_type == mime_type
            assert image.format_ext == expected_ext

        print(f"✅ MIME types: tested {len(test_cases)} formats")

    def test_file_path_image(self):
        """Test file:// URL parsing"""
        svg = '''<svg xmlns="http://www.w3.org/2000/svg">
            <image x="0" y="0" width="50" height="50" href="file:///path/to/image.png"/>
        </svg>'''

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)
        
        

        image = scene[0]
        assert image.source_type == "file"
        assert image.href == "file:///path/to/image.png"
        assert image.format_ext == "png"
        assert image.mime_type == "image/png"
        print(f"✅ File path: source_type={image.source_type}, format={image.format_ext}")

    def test_http_url_image(self):
        """Test HTTP URL parsing"""
        svg = '''<svg xmlns="http://www.w3.org/2000/svg">
            <image x="0" y="0" width="50" height="50" href="http://example.com/image.jpg"/>
        </svg>'''

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)
        
        

        image = scene[0]
        assert image.source_type == "http"
        assert image.format_ext == "jpg"
        assert image.mime_type == "image/jpeg"
        print(f"✅ HTTP URL: source_type={image.source_type}")

    def test_https_url_image(self):
        """Test HTTPS URL parsing"""
        svg = '''<svg xmlns="http://www.w3.org/2000/svg">
            <image x="0" y="0" width="50" height="50" href="https://cdn.example.com/images/photo.webp"/>
        </svg>'''

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)
        
        

        image = scene[0]
        assert image.source_type == "https"
        assert image.format_ext == "webp"
        assert image.mime_type == "image/webp"
        print(f"✅ HTTPS URL: source_type={image.source_type}")

    def test_zero_position_image(self):
        """Test image at origin (0,0)"""
        data_url = f"data:image/png;base64,{base64.b64encode(TINY_PNG).decode()}"

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg">
            <image x="0" y="0" width="100" height="100" href="{data_url}"/>
        </svg>'''

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)
        
        

        image = scene[0]
        assert image.x == 0
        assert image.y == 0

        config = PolicyConfig()
        policy = PolicyEngine(config)
        mapper = ImageMapper(policy)
        result = mapper.map(image)

        parsed_xml = ET.fromstring(result.xml_content)
        off = parsed_xml.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}off")
        assert off.get("x") == "0"
        assert off.get("y") == "0"
        print(f"✅ Origin (0,0): positioned correctly")

    def test_complete_pipeline_with_embedder(self):
        """Test complete pipeline through embedder"""
        data_url = f"data:image/png;base64,{base64.b64encode(TINY_PNG).decode()}"

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
            <image x="10" y="20" width="100" height="150" href="{data_url}"/>
        </svg>'''

        # Parse
        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)

        # Analyze
        
        

        # Map
        config = PolicyConfig()
        policy = PolicyEngine(config)
        mapper = ImageMapper(policy)

        mapper_results = []
        for child in scene:
            if hasattr(child, 'href'):
                result = mapper.map(child)
                mapper_results.append(result)

        # Embed
        embedder = DrawingMLEmbedder()
        embed_result = embedder.embed_scene(scene, mapper_results)

        # Validate
        assert embed_result.slide_xml is not None
        assert embed_result.relationships_xml is not None
        assert len(embed_result.media_files) == 1  # One media file
        assert embed_result.media_files[0]['filename'] == 'image1.png'
        assert embed_result.media_files[0]['data'] == TINY_PNG
        assert "r:embed=" in embed_result.slide_xml

        print(f"✅ Complete pipeline: Parse → Analyze → Map → Embed successful")
        print(f"   Media files: {[m['filename'] for m in embed_result.media_files]}")
        print(f"   Slide XML: {len(embed_result.slide_xml)} bytes")
        print(f"   Relationships XML: {len(embed_result.relationships_xml)} bytes")


class TestImageInvalidCases:
    """Test handling of invalid/malformed cases"""

    def test_missing_dimensions(self):
        """Test image with missing width/height (should be rejected)"""
        data_url = f"data:image/png;base64,{base64.b64encode(TINY_PNG).decode()}"

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg">
            <image x="0" y="0" href="{data_url}"/>
        </svg>'''

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)
        
        

        # Should have no children (image rejected due to missing dimensions)
        images = [c for c in scene if hasattr(c, 'href')]
        assert len(images) == 0
        print(f"✅ Missing dimensions: correctly rejected")

    def test_zero_dimensions(self):
        """Test image with zero width/height (should be rejected)"""
        data_url = f"data:image/png;base64,{base64.b64encode(TINY_PNG).decode()}"

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg">
            <image x="0" y="0" width="0" height="100" href="{data_url}"/>
        </svg>'''

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)
        
        

        images = [c for c in scene if hasattr(c, 'href')]
        assert len(images) == 0
        print(f"✅ Zero dimensions: correctly rejected")

    def test_missing_href(self):
        """Test image without href (should be rejected)"""
        svg = '''<svg xmlns="http://www.w3.org/2000/svg">
            <image x="0" y="0" width="100" height="100"/>
        </svg>'''

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(svg)
        
        

        images = [c for c in scene if hasattr(c, 'href')]
        assert len(images) == 0
        print(f"✅ Missing href: correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

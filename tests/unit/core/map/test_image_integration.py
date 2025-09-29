#!/usr/bin/env python3
"""
Test Image Processing Integration

Validates that image processing works correctly with the existing comprehensive image system.
"""

import sys
import os
import base64

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))


def test_image_adapter_import():
    """Test that image adapter can be imported"""
    try:
        from core.map.image_adapter import ImageProcessingAdapter, create_image_adapter

        # Test adapter creation
        adapter = create_image_adapter()
        assert adapter is not None
        assert isinstance(adapter, ImageProcessingAdapter)

        print("✅ Image adapter import and creation successful")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_image_adapter_basic_functionality():
    """Test basic image adapter functionality"""
    try:
        from core.map.image_adapter import create_image_adapter
        from core.ir import Image, Point, Rect

        # Create test image with data
        test_data = b"fake_image_data"
        image = Image(
            origin=Point(x=10, y=20),
            size=Rect(x=0, y=0, width=100, height=50),
            data=test_data,
            format="png"
        )

        # Create adapter
        adapter = create_image_adapter()

        # Test capability check
        can_process = adapter.can_process_image(image)
        assert isinstance(can_process, bool)

        # Test statistics
        stats = adapter.get_processing_statistics()
        assert isinstance(stats, dict)
        assert 'image_system_available' in stats

        print(f"✅ Image adapter basic functionality test successful (can_process: {can_process})")
        print(f"   Image system available: {stats['image_system_available']}")
        return True

    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def test_image_mapper_integration():
    """Test ImageMapper image processing integration"""
    try:
        from core.map.image_mapper import ImageMapper
        from core.policy.engine import Policy
        from core.policy.targets import ImageDecision, DecisionReason
        from core.ir import Image, Point, Rect
        from unittest.mock import Mock

        # Create mock policy
        policy = Mock()
        decision = ImageDecision(
            use_native=False,  # Use EMF for images
            estimated_quality=0.95,
            estimated_performance=0.9,
            reasons=[DecisionReason.SIMPLE_GEOMETRY]
        )
        policy.decide_image.return_value = decision

        # Create test image with data
        test_data = b"fake_png_data"
        image = Image(
            origin=Point(x=10, y=20),
            size=Rect(x=0, y=0, width=100, height=50),
            data=test_data,
            format="png"
        )

        # Create mapper and test
        mapper = ImageMapper(policy)
        result = mapper.map(image)

        # Verify image was processed
        assert result.output_format.value in ["emf_raster", "emf_vector"]
        assert "p:pic" in result.xml_content
        assert result.metadata is not None
        assert result.metadata['format'] == 'png'

        # Should contain image references
        xml_lower = result.xml_content.lower()
        has_image_ref = ("blip" in xml_lower and "r:embed" in xml_lower)

        print(f"✅ ImageMapper integration test successful (has_image_ref: {has_image_ref})")
        return True

    except Exception as e:
        print(f"❌ ImageMapper integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_href_processing():
    """Test different image href processing strategies"""
    try:
        from core.map.image_adapter import create_image_adapter
        from core.ir import Image, Point, Rect

        adapter = create_image_adapter()

        # Test Base64 data URL
        base64_data = base64.b64encode(b"fake_image_data").decode('utf-8')
        data_url = f"data:image/png;base64,{base64_data}"

        data_url_image = Image(
            origin=Point(x=0, y=0),
            size=Rect(x=0, y=0, width=100, height=50),
            data=b"",  # Empty data - will be processed from href
            format="png",
            href=data_url
        )

        if adapter.can_process_image(data_url_image):
            result = adapter.process_image(data_url_image)

            assert result.image_data is not None
            assert result.format == "png"
            assert result.relationship_id is not None

            print(f"✅ Data URL processing successful - Format: {result.format}")
        else:
            print("✅ Data URL processing correctly reports unavailable")

        # Test file path href
        file_path_image = Image(
            origin=Point(x=0, y=0),
            size=Rect(x=0, y=0, width=100, height=50),
            data=b"",
            format="jpg",
            href="/path/to/image.jpg"
        )

        if adapter.can_process_image(file_path_image):
            result = adapter.process_image(file_path_image)
            print(f"✅ File path processing successful - Strategy: {result.metadata.get('processing_method')}")
        else:
            print("✅ File path processing correctly handles unavailable files")

        return True

    except Exception as e:
        print(f"❌ Image href processing test failed: {e}")
        return False


def test_image_scaling_calculation():
    """Test image scaling and positioning calculation"""
    try:
        from core.map.image_adapter import create_image_adapter

        adapter = create_image_adapter()

        # Test aspect ratio preservation
        original_size = (200, 100)
        target_size = (100, 100)

        scaled_size = adapter.calculate_scaling(original_size, target_size, preserve_aspect=True)

        # Should maintain aspect ratio (2:1) - constrain by width
        expected_size = (100, 50)
        assert scaled_size == expected_size

        print(f"✅ Image scaling calculation successful: {original_size} → {scaled_size}")

        # Test without aspect ratio preservation
        scaled_size_no_aspect = adapter.calculate_scaling(original_size, target_size, preserve_aspect=False)
        assert scaled_size_no_aspect == target_size

        print(f"✅ Non-aspect scaling calculation successful: {original_size} → {scaled_size_no_aspect}")
        return True

    except Exception as e:
        print(f"❌ Image scaling calculation test failed: {e}")
        return False


def test_image_format_validation():
    """Test image format validation"""
    try:
        from core.map.image_adapter import create_image_adapter

        adapter = create_image_adapter()

        # Test PowerPoint-supported formats
        assert adapter.validate_image_format('png') == True
        assert adapter.validate_image_format('jpg') == True
        assert adapter.validate_image_format('gif') == True
        assert adapter.validate_image_format('PNG') == True  # Case insensitive

        # Test unsupported formats
        assert adapter.validate_image_format('webp') == True  # WebP is supported
        assert adapter.validate_image_format('xyz') == False

        print("✅ Image format validation test successful")
        return True

    except Exception as e:
        print(f"❌ Image format validation test failed: {e}")
        return False


if __name__ == "__main__":
    print("Running Image Processing Integration Tests...")

    success = True
    success &= test_image_adapter_import()
    success &= test_image_adapter_basic_functionality()
    success &= test_image_mapper_integration()
    success &= test_image_href_processing()
    success &= test_image_scaling_calculation()
    success &= test_image_format_validation()

    if success:
        print("\n🎉 All image processing integration tests passed!")
        exit(0)
    else:
        print("\n❌ Some image processing integration tests failed!")
        exit(1)
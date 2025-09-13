#!/usr/bin/env python3
"""
Comprehensive tests for SVG masking and clipping path converter.

This test suite covers:
- Mask definition processing and applications
- ClipPath definition processing and applications  
- Data classes and enums
- PowerPoint conversion output
- Complex masking and clipping scenarios
- Edge cases and error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET
from typing import Dict, List, Optional, Tuple

from src.converters.masking import (
    MaskingConverter,
    MaskDefinition, ClipPathDefinition, MaskApplication, ClipApplication,
    MaskType, ClippingType
)
from src.converters.base import ConversionContext


class TestMaskType:
    """Test MaskType enum."""
    
    def test_mask_type_values(self):
        """Test MaskType enum values."""
        assert MaskType.LUMINANCE.value == "luminance"
        assert MaskType.ALPHA.value == "alpha"


class TestClippingType:
    """Test ClippingType enum."""
    
    def test_clipping_type_values(self):
        """Test ClippingType enum values."""
        assert ClippingType.PATH_BASED.value == "path"
        assert ClippingType.SHAPE_BASED.value == "shape"
        assert ClippingType.COMPLEX.value == "complex"


class TestMaskDefinition:
    """Test MaskDefinition dataclass."""
    
    def test_mask_definition_creation(self):
        """Test MaskDefinition creation with required fields."""
        content_elements = [ET.Element("rect")]
        mask_def = MaskDefinition(
            id="mask1",
            mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox",
            mask_units="userSpaceOnUse",
            x=0.0, y=0.0, width=1.0, height=1.0,
            content_elements=content_elements
        )
        
        assert mask_def.id == "mask1"
        assert mask_def.mask_type == MaskType.LUMINANCE
        assert mask_def.units == "objectBoundingBox"
        assert mask_def.mask_units == "userSpaceOnUse"
        assert mask_def.x == 0.0
        assert mask_def.y == 0.0
        assert mask_def.width == 1.0
        assert mask_def.height == 1.0
        assert mask_def.content_elements == content_elements
        assert mask_def.opacity == 1.0  # default
        assert mask_def.transform is None  # default
    
    def test_mask_definition_with_optional_fields(self):
        """Test MaskDefinition with optional fields."""
        content_elements = [ET.Element("circle")]
        mask_def = MaskDefinition(
            id="mask2",
            mask_type=MaskType.ALPHA,
            units="userSpaceOnUse",
            mask_units="objectBoundingBox",
            x=10.0, y=20.0, width=50.0, height=60.0,
            content_elements=content_elements,
            opacity=0.8,
            transform="translate(10,20)"
        )
        
        assert mask_def.opacity == 0.8
        assert mask_def.transform == "translate(10,20)"


class TestClipPathDefinition:
    """Test ClipPathDefinition dataclass."""
    
    def test_clippath_definition_creation(self):
        """Test ClipPathDefinition creation with required fields."""
        clip_def = ClipPathDefinition(
            id="clip1",
            units="userSpaceOnUse",
            clip_rule="nonzero"
        )
        
        assert clip_def.id == "clip1"
        assert clip_def.units == "userSpaceOnUse"
        assert clip_def.clip_rule == "nonzero"
        assert clip_def.path_data is None  # default
        assert clip_def.shapes is None  # default
        assert clip_def.clipping_type == ClippingType.PATH_BASED  # default
        assert clip_def.transform is None  # default
    
    def test_clippath_definition_with_optional_fields(self):
        """Test ClipPathDefinition with optional fields."""
        shapes = [ET.Element("path"), ET.Element("rect")]
        clip_def = ClipPathDefinition(
            id="clip2",
            units="objectBoundingBox",
            clip_rule="evenodd",
            path_data="M 0 0 L 100 0 L 100 100 L 0 100 Z",
            shapes=shapes,
            clipping_type=ClippingType.COMPLEX,
            transform="scale(2)"
        )
        
        assert clip_def.path_data == "M 0 0 L 100 0 L 100 100 L 0 100 Z"
        assert clip_def.shapes == shapes
        assert clip_def.clipping_type == ClippingType.COMPLEX
        assert clip_def.transform == "scale(2)"


class TestMaskApplication:
    """Test MaskApplication dataclass."""
    
    def test_mask_application_creation(self):
        """Test MaskApplication creation."""
        element = ET.Element("rect")
        mask_def = MaskDefinition(
            id="mask1", mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox", mask_units="userSpaceOnUse",
            x=0, y=0, width=1, height=1, content_elements=[]
        )
        bounds = (10.0, 20.0, 100.0, 50.0)
        
        mask_app = MaskApplication(
            target_element=element,
            mask_definition=mask_def,
            resolved_bounds=bounds
        )
        
        assert mask_app.target_element == element
        assert mask_app.mask_definition == mask_def
        assert mask_app.resolved_bounds == bounds
        assert mask_app.requires_rasterization is False  # default


class TestClipApplication:
    """Test ClipApplication dataclass."""
    
    def test_clip_application_creation(self):
        """Test ClipApplication creation."""
        element = ET.Element("circle")
        clip_def = ClipPathDefinition(
            id="clip1", units="userSpaceOnUse", clip_rule="nonzero"
        )
        
        clip_app = ClipApplication(
            target_element=element,
            clip_definition=clip_def
        )
        
        assert clip_app.target_element == element
        assert clip_app.clip_definition == clip_def
        assert clip_app.resolved_path is None  # default
        assert clip_app.powerpoint_compatible is True  # default


class TestMaskingConverter(MaskingConverter):
    """Testable version of MaskingConverter with mocked dependencies."""
    
    def __init__(self):
        super().__init__()
        # Mock dependencies to avoid initialization issues
        self.unit_converter = Mock()
        self.color_parser = Mock()
        self.transform_parser = Mock()
        self.viewport_resolver = Mock()
        
        # Setup common mock returns
        self.unit_converter.convert_to_user_units.return_value = 10.0
        self.unit_converter.convert_to_emu.return_value = 914400  # 10 points in EMU
        self.transform_parser.parse_transform.return_value = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        self.transform_parser.apply_matrix_to_path.return_value = "M 0 0 L 100 100"


class TestMaskingConverter:
    """Test MaskingConverter functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = TestMaskingConverter()
        self.context = Mock()
        self.context.get_next_shape_id.return_value = 123
    
    def test_initialization(self):
        """Test converter initialization."""
        assert self.converter.__class__.supported_elements == ['mask', 'clipPath', 'defs']
        assert isinstance(self.converter.mask_definitions, dict)
        assert isinstance(self.converter.clippath_definitions, dict)
        assert isinstance(self.converter.masked_elements, list)
        assert isinstance(self.converter.clipped_elements, list)
        assert len(self.converter.mask_definitions) == 0
        assert len(self.converter.clippath_definitions) == 0
    
    def test_can_convert_mask_element(self):
        """Test can_convert with mask element."""
        mask_element = ET.Element("mask")
        result = self.converter.can_convert(mask_element, self.context)
        assert result is True
    
    def test_can_convert_clippath_element(self):
        """Test can_convert with clipPath element."""
        clippath_element = ET.Element("clipPath")
        result = self.converter.can_convert(clippath_element, self.context)
        assert result is True
    
    def test_can_convert_element_with_mask_reference(self):
        """Test can_convert with element that has mask reference."""
        rect_element = ET.Element("rect")
        rect_element.set("mask", "url(#mask1)")
        result = self.converter.can_convert(rect_element, self.context)
        assert result is True
    
    def test_can_convert_element_with_clip_reference(self):
        """Test can_convert with element that has clip-path reference."""
        circle_element = ET.Element("circle")
        circle_element.set("clip-path", "url(#clip1)")
        result = self.converter.can_convert(circle_element, self.context)
        assert result is True
    
    def test_can_convert_unsupported_element(self):
        """Test can_convert with unsupported element."""
        line_element = ET.Element("line")
        result = self.converter.can_convert(line_element, self.context)
        assert result is False
    
    def test_convert_mask_element(self):
        """Test convert with mask element."""
        mask_element = ET.Element("mask")
        mask_element.set("id", "testMask")
        mask_element.set("mask-type", "alpha")
        
        # Add content to mask
        rect_child = ET.SubElement(mask_element, "rect")
        rect_child.set("width", "100")
        rect_child.set("height", "50")
        
        with patch.object(self.converter, '_process_mask_definition') as mock_process:
            mock_process.return_value = ""
            result = self.converter.convert(mask_element, self.context)
            mock_process.assert_called_once_with(mask_element, self.context)
    
    def test_convert_clippath_element(self):
        """Test convert with clipPath element."""
        clippath_element = ET.Element("clipPath")
        clippath_element.set("id", "testClip")
        
        with patch.object(self.converter, '_process_clippath_definition') as mock_process:
            mock_process.return_value = ""
            result = self.converter.convert(clippath_element, self.context)
            mock_process.assert_called_once_with(clippath_element, self.context)
    
    def test_convert_element_with_masking(self):
        """Test convert with element that needs masking applied."""
        rect_element = ET.Element("rect")
        rect_element.set("mask", "url(#mask1)")
        rect_element.set("clip-path", "url(#clip1)")
        
        with patch.object(self.converter, '_apply_masking_clipping') as mock_apply:
            mock_apply.return_value = "masking output"
            result = self.converter.convert(rect_element, self.context)
            mock_apply.assert_called_once_with(rect_element, self.context)
            assert result == "masking output"


class TestMaskDefinitionProcessing:
    """Test mask definition processing."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = TestMaskingConverter()
        self.context = Mock()
    
    def test_process_mask_definition_basic(self):
        """Test processing basic mask definition."""
        mask_element = ET.Element("mask")
        mask_element.set("id", "mask1")
        mask_element.set("mask-type", "luminance")
        mask_element.set("maskUnits", "objectBoundingBox")
        
        # Add content element
        rect_child = ET.SubElement(mask_element, "rect")
        rect_child.set("fill", "white")
        
        result = self.converter._process_mask_definition(mask_element, self.context)
        
        assert result == ""  # Definitions don't generate output
        assert "mask1" in self.converter.mask_definitions
        
        mask_def = self.converter.mask_definitions["mask1"]
        assert mask_def.id == "mask1"
        assert mask_def.mask_type == MaskType.LUMINANCE
        assert mask_def.units == "objectBoundingBox"
        assert mask_def.mask_units == "userSpaceOnUse"  # default
        assert len(mask_def.content_elements) == 1
        assert mask_def.content_elements[0] == rect_child
    
    def test_process_mask_definition_with_all_attributes(self):
        """Test processing mask definition with all attributes."""
        mask_element = ET.Element("mask")
        mask_element.set("id", "mask2")
        mask_element.set("mask-type", "alpha")
        mask_element.set("maskUnits", "userSpaceOnUse")
        mask_element.set("maskContentUnits", "objectBoundingBox")
        mask_element.set("x", "10")
        mask_element.set("y", "20")
        mask_element.set("width", "100")
        mask_element.set("height", "50")
        mask_element.set("opacity", "0.8")
        mask_element.set("transform", "rotate(45)")
        
        result = self.converter._process_mask_definition(mask_element, self.context)
        
        assert result == ""
        mask_def = self.converter.mask_definitions["mask2"]
        assert mask_def.mask_type == MaskType.ALPHA
        assert mask_def.units == "userSpaceOnUse"
        assert mask_def.mask_units == "objectBoundingBox"
        assert mask_def.opacity == 0.8
        assert mask_def.transform == "rotate(45)"
    
    def test_process_mask_definition_without_id(self):
        """Test processing mask definition without id attribute."""
        mask_element = ET.Element("mask")
        
        with patch('src.converters.masking.logger') as mock_logger:
            result = self.converter._process_mask_definition(mask_element, self.context)
            assert result == ""
            mock_logger.warning.assert_called_once_with("Mask element without id attribute")
        
        assert len(self.converter.mask_definitions) == 0
    
    def test_process_mask_definition_percentage_coordinates(self):
        """Test processing mask with percentage coordinates."""
        mask_element = ET.Element("mask")
        mask_element.set("id", "mask3")
        mask_element.set("maskUnits", "objectBoundingBox")
        mask_element.set("x", "-10%")
        mask_element.set("y", "-10%")
        mask_element.set("width", "120%")
        mask_element.set("height", "120%")
        
        result = self.converter._process_mask_definition(mask_element, self.context)
        
        mask_def = self.converter.mask_definitions["mask3"]
        # Percentage values should be converted to decimals for objectBoundingBox
        assert mask_def.x == -0.1
        assert mask_def.y == -0.1
        assert mask_def.width == 1.2
        assert mask_def.height == 1.2


class TestClipPathDefinitionProcessing:
    """Test clipPath definition processing."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = TestMaskingConverter()
        self.context = Mock()
    
    def test_process_clippath_definition_basic(self):
        """Test processing basic clipPath definition."""
        clippath_element = ET.Element("clipPath")
        clippath_element.set("id", "clip1")
        
        # Add a rect child
        rect_child = ET.SubElement(clippath_element, "rect")
        rect_child.set("x", "10")
        rect_child.set("y", "10")
        rect_child.set("width", "80")
        rect_child.set("height", "60")
        
        result = self.converter._process_clippath_definition(clippath_element, self.context)
        
        assert result == ""  # Definitions don't generate output
        assert "clip1" in self.converter.clippath_definitions
        
        clip_def = self.converter.clippath_definitions["clip1"]
        assert clip_def.id == "clip1"
        assert clip_def.units == "userSpaceOnUse"  # default
        assert clip_def.clip_rule == "nonzero"  # default
        assert clip_def.clipping_type == ClippingType.SHAPE_BASED
        assert len(clip_def.shapes) == 1
        assert clip_def.shapes[0] == rect_child
    
    def test_process_clippath_definition_single_path(self):
        """Test processing clipPath with single path element."""
        clippath_element = ET.Element("clipPath")
        clippath_element.set("id", "clip2")
        clippath_element.set("clipPathUnits", "objectBoundingBox")
        
        # Add a path child
        path_child = ET.SubElement(clippath_element, "path")
        path_child.set("d", "M 0 0 L 100 0 L 100 100 L 0 100 Z")
        
        result = self.converter._process_clippath_definition(clippath_element, self.context)
        
        clip_def = self.converter.clippath_definitions["clip2"]
        assert clip_def.units == "objectBoundingBox"
        assert clip_def.clipping_type == ClippingType.PATH_BASED
        assert clip_def.path_data == "M 0 0 L 100 0 L 100 100 L 0 100 Z"
        assert len(clip_def.shapes) == 1
    
    def test_process_clippath_definition_complex(self):
        """Test processing clipPath with multiple elements (complex)."""
        clippath_element = ET.Element("clipPath")
        clippath_element.set("id", "clip3")
        clippath_element.set("clip-rule", "evenodd")
        clippath_element.set("transform", "translate(10,20)")
        
        # Add multiple children
        rect_child = ET.SubElement(clippath_element, "rect")
        circle_child = ET.SubElement(clippath_element, "circle")
        
        result = self.converter._process_clippath_definition(clippath_element, self.context)
        
        clip_def = self.converter.clippath_definitions["clip3"]
        assert clip_def.clip_rule == "evenodd"
        assert clip_def.clipping_type == ClippingType.COMPLEX
        assert clip_def.transform == "translate(10,20)"
        assert len(clip_def.shapes) == 2
    
    def test_process_clippath_definition_without_id(self):
        """Test processing clipPath definition without id attribute."""
        clippath_element = ET.Element("clipPath")
        
        with patch('src.converters.masking.logger') as mock_logger:
            result = self.converter._process_clippath_definition(clippath_element, self.context)
            assert result == ""
            mock_logger.warning.assert_called_once_with("ClipPath element without id attribute")
        
        assert len(self.converter.clippath_definitions) == 0


class TestMaskApplication:
    """Test mask application functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = TestMaskingConverter()
        self.context = Mock()
        self.context.get_next_shape_id.return_value = 456
        
        # Setup mock for element bounds
        self.converter._get_element_bounds = Mock(return_value=(0.0, 0.0, 100.0, 100.0))
        
        # Create a mask definition
        mask_def = MaskDefinition(
            id="testMask",
            mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox",
            mask_units="userSpaceOnUse",
            x=-0.1, y=-0.1, width=1.2, height=1.2,
            content_elements=[ET.Element("rect")]
        )
        self.converter.mask_definitions["testMask"] = mask_def
    
    def test_apply_mask_basic(self):
        """Test basic mask application."""
        element = ET.Element("rect")
        mask_ref = "url(#testMask)"
        
        with patch.object(self.converter, '_mask_requires_rasterization') as mock_raster:
            mock_raster.return_value = False
            with patch.object(self.converter, '_generate_powerpoint_mask_output') as mock_output:
                mock_output.return_value = "powerpoint mask output"
                
                result = self.converter._apply_mask(element, mask_ref, self.context)
                
                assert result == "powerpoint mask output"
                mock_raster.assert_called_once()
                mock_output.assert_called_once()
        
        # Check that mask application was stored
        assert len(self.converter.masked_elements) == 1
        mask_app = self.converter.masked_elements[0]
        assert mask_app.target_element == element
        assert mask_app.mask_definition.id == "testMask"
    
    def test_apply_mask_requires_rasterization(self):
        """Test mask application that requires rasterization."""
        element = ET.Element("circle")
        mask_ref = "url(#testMask)"
        
        with patch.object(self.converter, '_mask_requires_rasterization') as mock_raster:
            mock_raster.return_value = True
            with patch.object(self.converter, '_generate_rasterized_mask_output') as mock_output:
                mock_output.return_value = "rasterized mask output"
                
                result = self.converter._apply_mask(element, mask_ref, self.context)
                
                assert result == "rasterized mask output"
                mock_output.assert_called_once()
    
    def test_apply_mask_invalid_reference(self):
        """Test mask application with invalid reference."""
        element = ET.Element("rect")
        mask_ref = "url(#nonexistentMask)"
        
        with patch('src.converters.masking.logger') as mock_logger:
            result = self.converter._apply_mask(element, mask_ref, self.context)
            assert result == ""
            mock_logger.warning.assert_called_once()
    
    def test_apply_mask_object_bounding_box_units(self):
        """Test mask application with objectBoundingBox units."""
        element = ET.Element("rect")
        mask_ref = "url(#testMask)"
        
        # Mock element bounds
        self.converter._get_element_bounds.return_value = (50.0, 60.0, 200.0, 150.0)
        
        with patch.object(self.converter, '_mask_requires_rasterization', return_value=False):
            with patch.object(self.converter, '_generate_powerpoint_mask_output', return_value=""):
                result = self.converter._apply_mask(element, mask_ref, self.context)
        
        # Check resolved bounds calculation
        mask_app = self.converter.masked_elements[0]
        expected_x = 50.0 + (-0.1 * 200.0)  # 30.0
        expected_y = 60.0 + (-0.1 * 150.0)  # 45.0
        expected_width = 1.2 * 200.0  # 240.0
        expected_height = 1.2 * 150.0  # 180.0
        
        assert mask_app.resolved_bounds == (expected_x, expected_y, expected_width, expected_height)
    
    def test_apply_mask_user_space_units(self):
        """Test mask application with userSpaceOnUse units."""
        # Create mask with userSpaceOnUse units
        mask_def = MaskDefinition(
            id="userSpaceMask",
            mask_type=MaskType.ALPHA,
            units="userSpaceOnUse",
            mask_units="userSpaceOnUse",
            x=10.0, y=15.0, width=100.0, height=80.0,
            content_elements=[ET.Element("circle")]
        )
        self.converter.mask_definitions["userSpaceMask"] = mask_def
        
        element = ET.Element("path")
        mask_ref = "url(#userSpaceMask)"
        
        with patch.object(self.converter, '_mask_requires_rasterization', return_value=False):
            with patch.object(self.converter, '_generate_powerpoint_mask_output', return_value=""):
                result = self.converter._apply_mask(element, mask_ref, self.context)
        
        # Check that bounds are used directly for userSpaceOnUse
        mask_app = self.converter.masked_elements[0]
        assert mask_app.resolved_bounds == (10.0, 15.0, 100.0, 80.0)


class TestClipPathApplication:
    """Test clipPath application functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = TestMaskingConverter()
        self.context = Mock()
        self.context.get_next_shape_id.return_value = 789
        
        # Setup mock for element bounds
        self.converter._get_element_bounds = Mock(return_value=(0.0, 0.0, 100.0, 100.0))
        
        # Create clipPath definitions
        path_clip = ClipPathDefinition(
            id="pathClip",
            units="userSpaceOnUse",
            clip_rule="nonzero",
            path_data="M 0 0 L 100 0 L 100 100 L 0 100 Z",
            shapes=[ET.Element("path")],
            clipping_type=ClippingType.PATH_BASED
        )
        self.converter.clippath_definitions["pathClip"] = path_clip
        
        shape_clip = ClipPathDefinition(
            id="shapeClip",
            units="userSpaceOnUse",
            clip_rule="nonzero",
            shapes=[ET.Element("rect")],
            clipping_type=ClippingType.SHAPE_BASED
        )
        self.converter.clippath_definitions["shapeClip"] = shape_clip
    
    def test_apply_clipping_path_based(self):
        """Test clipPath application with path-based clipping."""
        element = ET.Element("rect")
        clip_ref = "url(#pathClip)"
        
        with patch.object(self.converter, '_generate_powerpoint_clip_output') as mock_output:
            mock_output.return_value = "powerpoint clip output"
            
            result = self.converter._apply_clipping(element, clip_ref, self.context)
            
            assert result == "powerpoint clip output"
            mock_output.assert_called_once()
        
        # Check that clip application was stored
        assert len(self.converter.clipped_elements) == 1
        clip_app = self.converter.clipped_elements[0]
        assert clip_app.target_element == element
        assert clip_app.clip_definition.id == "pathClip"
        assert clip_app.resolved_path == "M 0 0 L 100 0 L 100 100 L 0 100 Z"
        assert clip_app.powerpoint_compatible is True
    
    def test_apply_clipping_shape_based(self):
        """Test clipPath application with shape-based clipping."""
        element = ET.Element("circle")
        clip_ref = "url(#shapeClip)"
        
        with patch.object(self.converter, '_convert_shape_to_path') as mock_convert:
            mock_convert.return_value = "M 10 10 L 90 10 L 90 90 L 10 90 Z"
            with patch.object(self.converter, '_generate_powerpoint_clip_output') as mock_output:
                mock_output.return_value = "shape clip output"
                
                result = self.converter._apply_clipping(element, clip_ref, self.context)
                
                assert result == "shape clip output"
                mock_convert.assert_called_once()
        
        clip_app = self.converter.clipped_elements[0]
        assert clip_app.resolved_path == "M 10 10 L 90 10 L 90 90 L 10 90 Z"
    
    def test_apply_clipping_complex(self):
        """Test clipPath application with complex clipping."""
        # Create complex clipPath definition
        complex_clip = ClipPathDefinition(
            id="complexClip",
            units="userSpaceOnUse",
            clip_rule="evenodd",
            shapes=[ET.Element("rect"), ET.Element("circle")],
            clipping_type=ClippingType.COMPLEX
        )
        self.converter.clippath_definitions["complexClip"] = complex_clip
        
        element = ET.Element("path")
        clip_ref = "url(#complexClip)"
        
        with patch.object(self.converter, '_merge_complex_clip_paths') as mock_merge:
            mock_merge.return_value = "complex path data"
            with patch.object(self.converter, '_generate_rasterized_clip_output') as mock_output:
                mock_output.return_value = "rasterized clip output"
                
                result = self.converter._apply_clipping(element, clip_ref, self.context)
                
                assert result == "rasterized clip output"
        
        clip_app = self.converter.clipped_elements[0]
        assert clip_app.powerpoint_compatible is False
    
    def test_apply_clipping_invalid_reference(self):
        """Test clipPath application with invalid reference."""
        element = ET.Element("rect")
        clip_ref = "url(#nonexistentClip)"
        
        with patch('src.converters.masking.logger') as mock_logger:
            result = self.converter._apply_clipping(element, clip_ref, self.context)
            assert result == ""
            mock_logger.warning.assert_called_once()
    
    def test_apply_clipping_with_transform(self):
        """Test clipPath application with transform."""
        # Add transform to clipPath
        self.converter.clippath_definitions["pathClip"].transform = "scale(2)"
        
        element = ET.Element("rect")
        clip_ref = "url(#pathClip)"
        
        with patch.object(self.converter, '_generate_powerpoint_clip_output', return_value=""):
            result = self.converter._apply_clipping(element, clip_ref, self.context)
        
        # Verify transform was applied
        self.converter.transform_parser.parse_transform.assert_called_once_with("scale(2)")
        self.converter.transform_parser.apply_matrix_to_path.assert_called_once()


class TestRasterizationLogic:
    """Test mask rasterization requirement logic."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = TestMaskingConverter()
    
    def test_mask_requires_rasterization_simple(self):
        """Test simple mask that doesn't require rasterization."""
        mask_def = MaskDefinition(
            id="simple",
            mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox",
            mask_units="userSpaceOnUse",
            x=0, y=0, width=1, height=1,
            content_elements=[ET.Element("rect")]
        )
        
        result = self.converter._mask_requires_rasterization(mask_def)
        assert result is False
    
    def test_mask_requires_rasterization_alpha(self):
        """Test alpha mask requires rasterization."""
        mask_def = MaskDefinition(
            id="alpha",
            mask_type=MaskType.ALPHA,
            units="objectBoundingBox",
            mask_units="userSpaceOnUse",
            x=0, y=0, width=1, height=1,
            content_elements=[ET.Element("rect")]
        )
        
        result = self.converter._mask_requires_rasterization(mask_def)
        assert result is True
    
    def test_mask_requires_rasterization_image_content(self):
        """Test mask with image content requires rasterization."""
        image_element = ET.Element("image")
        mask_def = MaskDefinition(
            id="image",
            mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox",
            mask_units="userSpaceOnUse",
            x=0, y=0, width=1, height=1,
            content_elements=[image_element]
        )
        
        result = self.converter._mask_requires_rasterization(mask_def)
        assert result is True
    
    def test_mask_requires_rasterization_text_content(self):
        """Test mask with text content requires rasterization."""
        text_element = ET.Element("text")
        tspan_element = ET.Element("tspan")
        textpath_element = ET.Element("textPath")
        
        for element in [text_element, tspan_element, textpath_element]:
            mask_def = MaskDefinition(
                id="text",
                mask_type=MaskType.LUMINANCE,
                units="objectBoundingBox",
                mask_units="userSpaceOnUse",
                x=0, y=0, width=1, height=1,
                content_elements=[element]
            )
            
            result = self.converter._mask_requires_rasterization(mask_def)
            assert result is True
    
    def test_mask_requires_rasterization_use_element(self):
        """Test mask with use element requires rasterization."""
        use_element = ET.Element("use")
        mask_def = MaskDefinition(
            id="use",
            mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox",
            mask_units="userSpaceOnUse",
            x=0, y=0, width=1, height=1,
            content_elements=[use_element]
        )
        
        result = self.converter._mask_requires_rasterization(mask_def)
        assert result is True
    
    def test_mask_requires_rasterization_filter(self):
        """Test mask with filter requires rasterization."""
        filter_element = ET.Element("rect")
        filter_element.set("filter", "url(#blur)")
        mask_def = MaskDefinition(
            id="filter",
            mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox",
            mask_units="userSpaceOnUse",
            x=0, y=0, width=1, height=1,
            content_elements=[filter_element]
        )
        
        result = self.converter._mask_requires_rasterization(mask_def)
        assert result is True
    
    def test_mask_requires_rasterization_complex_gradient(self):
        """Test mask with complex gradient requires rasterization."""
        gradient_element = ET.Element("rect")
        gradient_element.set("fill", "url(#complexGradient)")
        
        mask_def = MaskDefinition(
            id="gradient",
            mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox",
            mask_units="userSpaceOnUse",
            x=0, y=0, width=1, height=1,
            content_elements=[gradient_element]
        )
        
        with patch.object(self.converter, '_has_complex_gradient') as mock_complex:
            mock_complex.return_value = True
            result = self.converter._mask_requires_rasterization(mask_def)
            assert result is True
    
    def test_has_complex_gradient(self):
        """Test complex gradient detection."""
        # Test element with gradient fill
        element = ET.Element("rect")
        element.set("fill", "url(#gradient1)")
        result = self.converter._has_complex_gradient(element)
        assert result is True
        
        # Test element with gradient stroke
        element2 = ET.Element("circle")
        element2.set("stroke", "url(#gradient2)")
        result2 = self.converter._has_complex_gradient(element2)
        assert result2 is True
        
        # Test element without gradient
        element3 = ET.Element("path")
        element3.set("fill", "red")
        result3 = self.converter._has_complex_gradient(element3)
        assert result3 is False


class TestUtilityFunctions:
    """Test utility and helper functions."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = TestMaskingConverter()
        self.context = Mock()
    
    def test_parse_coordinate_percentage_object_bounding_box(self):
        """Test coordinate parsing with percentage for objectBoundingBox."""
        result = self.converter._parse_coordinate("50%", True)
        assert result == 0.5
        
        result = self.converter._parse_coordinate("-10%", True)
        assert result == -0.1
        
        result = self.converter._parse_coordinate("120%", True)
        assert result == 1.2
    
    def test_parse_coordinate_percentage_user_space(self):
        """Test coordinate parsing with percentage for userSpaceOnUse."""
        result = self.converter._parse_coordinate("50%", False)
        assert result == 50.0  # Raw percentage value
    
    def test_parse_coordinate_unit_value(self):
        """Test coordinate parsing with unit values."""
        result = self.converter._parse_coordinate("25px", True)
        assert result == 10.0  # Mock returns 10.0
        self.converter.unit_converter.convert_to_user_units.assert_called_with("25px")
        
        result = self.converter._parse_coordinate("2em", False)
        assert result == 10.0
    
    def test_extract_reference_id_url_format(self):
        """Test reference ID extraction from url() format."""
        result = self.converter._extract_reference_id("url(#myMask)")
        assert result == "myMask"
        
        result = self.converter._extract_reference_id("url(#clip-path-1)")
        assert result == "clip-path-1"
    
    def test_extract_reference_id_hash_format(self):
        """Test reference ID extraction from # format."""
        result = self.converter._extract_reference_id("#simpleMask")
        assert result == "simpleMask"
    
    def test_extract_reference_id_invalid(self):
        """Test reference ID extraction with invalid format."""
        result = self.converter._extract_reference_id("invalidRef")
        assert result is None
        
        result = self.converter._extract_reference_id("")
        assert result is None
    
    def test_get_element_bounds(self):
        """Test element bounds calculation."""
        element = ET.Element("rect")
        result = self.converter._get_element_bounds(element, self.context)
        assert result == (0.0, 0.0, 100.0, 100.0)  # Default mock return
    
    def test_convert_shape_to_path_rect(self):
        """Test rectangle to path conversion."""
        rect = ET.Element("rect")
        rect.set("x", "10")
        rect.set("y", "20")
        rect.set("width", "50")
        rect.set("height", "30")
        
        result = self.converter._convert_shape_to_path(rect, self.context)
        expected = "M 10.0 20.0 L 60.0 20.0 L 60.0 50.0 L 10.0 50.0 Z"
        assert result == expected
    
    def test_convert_shape_to_path_circle(self):
        """Test circle to path conversion."""
        circle = ET.Element("circle")
        circle.set("cx", "50")
        circle.set("cy", "40")
        circle.set("r", "25")
        
        result = self.converter._convert_shape_to_path(circle, self.context)
        expected = "M 25.0 40.0 A 25.0 25.0 0 1 0 75.0 40.0 A 25.0 25.0 0 1 0 25.0 40.0 Z"
        assert result == expected
    
    def test_convert_shape_to_path_ellipse(self):
        """Test ellipse to path conversion."""
        ellipse = ET.Element("ellipse")
        ellipse.set("cx", "60")
        ellipse.set("cy", "30")
        ellipse.set("rx", "40")
        ellipse.set("ry", "20")
        
        result = self.converter._convert_shape_to_path(ellipse, self.context)
        expected = "M 20.0 30.0 A 40.0 20.0 0 1 0 100.0 30.0 A 40.0 20.0 0 1 0 20.0 30.0 Z"
        assert result == expected
    
    def test_convert_shape_to_path_unsupported(self):
        """Test conversion of unsupported shape."""
        line = ET.Element("line")
        result = self.converter._convert_shape_to_path(line, self.context)
        assert result == ""
    
    def test_merge_complex_clip_paths(self):
        """Test merging multiple shapes into complex clipping path."""
        path1 = ET.Element("path")
        path1.set("d", "M 0 0 L 100 0 L 100 100 Z")
        
        rect = ET.Element("rect")
        rect.set("x", "10")
        rect.set("y", "10")
        rect.set("width", "80")
        rect.set("height", "80")
        
        shapes = [path1, rect]
        result = self.converter._merge_complex_clip_paths(shapes, self.context)
        
        # Should combine both path data
        assert "M 0 0 L 100 0 L 100 100 Z" in result
        assert "M 10.0 10.0 L 90.0 10.0 L 90.0 90.0 L 10.0 90.0 Z" in result
    
    def test_transform_path_to_object_bounds(self):
        """Test path coordinate transformation to object bounds."""
        path = "M 0 0 L 1 1"
        bounds = (10.0, 20.0, 100.0, 50.0)
        
        # Current implementation returns path as-is (placeholder)
        result = self.converter._transform_path_to_object_bounds(path, bounds)
        assert result == path
    
    def test_convert_svg_path_to_pptx(self):
        """Test SVG path to PowerPoint path conversion."""
        svg_path = "M 0 0 L 100 100 Z"
        
        # Current implementation returns placeholder
        result = self.converter._convert_svg_path_to_pptx(svg_path)
        assert "moveTo" in result
        assert "lnTo" in result


class TestOutputGeneration:
    """Test PowerPoint output generation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = TestMaskingConverter()
        self.context = Mock()
        self.context.get_next_shape_id.return_value = 999
    
    def test_generate_powerpoint_mask_output(self):
        """Test PowerPoint mask output generation."""
        element = ET.Element("rect")
        mask_def = MaskDefinition(
            id="testMask", mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox", mask_units="userSpaceOnUse",
            x=0, y=0, width=1, height=1, content_elements=[]
        )
        mask_app = MaskApplication(
            target_element=element,
            mask_definition=mask_def,
            resolved_bounds=(10.0, 20.0, 100.0, 80.0)
        )
        
        result = self.converter._generate_powerpoint_mask_output(mask_app, self.context)
        
        assert "PowerPoint Mask Application" in result
        assert "p:sp" in result
        assert "cNvPr id=\"999\"" in result
        assert "MaskedShape" in result
        # Check EMU conversion was called
        assert self.converter.unit_converter.convert_to_emu.call_count >= 4
    
    def test_generate_rasterized_mask_output(self):
        """Test rasterized mask output generation."""
        element = ET.Element("circle")
        mask_def = MaskDefinition(
            id="complexMask", mask_type=MaskType.ALPHA,
            units="userSpaceOnUse", mask_units="userSpaceOnUse",
            x=0, y=0, width=100, height=100, content_elements=[]
        )
        mask_app = MaskApplication(
            target_element=element,
            mask_definition=mask_def,
            resolved_bounds=(0.0, 0.0, 100.0, 100.0),
            requires_rasterization=True
        )
        
        result = self.converter._generate_rasterized_mask_output(mask_app, self.context)
        
        assert "Rasterized Mask Output" in result
        assert "Complex mask requires image rasterization" in result
        assert "complexMask" in result
        assert "circle" in result
        assert "RasterizedMask" in result
    
    def test_generate_powerpoint_clip_output(self):
        """Test PowerPoint clipping output generation."""
        element = ET.Element("path")
        clip_def = ClipPathDefinition(
            id="testClip", units="userSpaceOnUse", clip_rule="nonzero"
        )
        clip_app = ClipApplication(
            target_element=element,
            clip_definition=clip_def,
            resolved_path="M 0 0 L 100 0 L 100 100 L 0 100 Z"
        )
        
        with patch.object(self.converter, '_convert_svg_path_to_pptx') as mock_convert:
            mock_convert.return_value = '<a:moveTo><a:pt x="0" y="0"/></a:moveTo>'
            
            result = self.converter._generate_powerpoint_clip_output(clip_app, self.context)
            
            assert "PowerPoint Clipping Path" in result
            assert "custGeom" in result
            assert "ClippingShape" in result
            assert mock_convert.return_value in result
            mock_convert.assert_called_once_with("M 0 0 L 100 0 L 100 100 L 0 100 Z")
    
    def test_generate_powerpoint_clip_output_no_path(self):
        """Test PowerPoint clipping output with no resolved path."""
        element = ET.Element("rect")
        clip_def = ClipPathDefinition(
            id="emptyClip", units="userSpaceOnUse", clip_rule="nonzero"
        )
        clip_app = ClipApplication(
            target_element=element,
            clip_definition=clip_def,
            resolved_path=None
        )
        
        result = self.converter._generate_powerpoint_clip_output(clip_app, self.context)
        assert result == ""
    
    def test_generate_rasterized_clip_output(self):
        """Test rasterized clipping output generation."""
        element = ET.Element("g")
        clip_def = ClipPathDefinition(
            id="complexClip", units="userSpaceOnUse", clip_rule="evenodd",
            clipping_type=ClippingType.COMPLEX
        )
        clip_app = ClipApplication(
            target_element=element,
            clip_definition=clip_def,
            powerpoint_compatible=False
        )
        
        result = self.converter._generate_rasterized_clip_output(clip_app, self.context)
        
        assert "Rasterized Clipping Output" in result
        assert "Complex clipping requires rasterization" in result
        assert "complexClip" in result
        assert "ComplexClip" in result


class TestStateManagement:
    """Test converter state management."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = TestMaskingConverter()
    
    def test_get_mask_definitions(self):
        """Test getting mask definitions copy."""
        mask_def = MaskDefinition(
            id="test", mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox", mask_units="userSpaceOnUse",
            x=0, y=0, width=1, height=1, content_elements=[]
        )
        self.converter.mask_definitions["test"] = mask_def
        
        result = self.converter.get_mask_definitions()
        assert result == self.converter.mask_definitions
        assert result is not self.converter.mask_definitions  # Should be copy
    
    def test_get_clippath_definitions(self):
        """Test getting clipPath definitions copy."""
        clip_def = ClipPathDefinition(
            id="test", units="userSpaceOnUse", clip_rule="nonzero"
        )
        self.converter.clippath_definitions["test"] = clip_def
        
        result = self.converter.get_clippath_definitions()
        assert result == self.converter.clippath_definitions
        assert result is not self.converter.clippath_definitions  # Should be copy
    
    def test_get_masked_elements(self):
        """Test getting masked elements copy."""
        element = ET.Element("rect")
        mask_def = MaskDefinition(
            id="test", mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox", mask_units="userSpaceOnUse",
            x=0, y=0, width=1, height=1, content_elements=[]
        )
        mask_app = MaskApplication(
            target_element=element,
            mask_definition=mask_def,
            resolved_bounds=(0, 0, 100, 100)
        )
        self.converter.masked_elements.append(mask_app)
        
        result = self.converter.get_masked_elements()
        assert result == self.converter.masked_elements
        assert result is not self.converter.masked_elements  # Should be copy
    
    def test_get_clipped_elements(self):
        """Test getting clipped elements copy."""
        element = ET.Element("circle")
        clip_def = ClipPathDefinition(
            id="test", units="userSpaceOnUse", clip_rule="nonzero"
        )
        clip_app = ClipApplication(
            target_element=element,
            clip_definition=clip_def
        )
        self.converter.clipped_elements.append(clip_app)
        
        result = self.converter.get_clipped_elements()
        assert result == self.converter.clipped_elements
        assert result is not self.converter.clipped_elements  # Should be copy
    
    def test_reset(self):
        """Test converter state reset."""
        # Add some data
        mask_def = MaskDefinition(
            id="test", mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox", mask_units="userSpaceOnUse",
            x=0, y=0, width=1, height=1, content_elements=[]
        )
        self.converter.mask_definitions["test"] = mask_def
        
        clip_def = ClipPathDefinition(
            id="test", units="userSpaceOnUse", clip_rule="nonzero"
        )
        self.converter.clippath_definitions["test"] = clip_def
        
        self.converter.masked_elements.append(Mock())
        self.converter.clipped_elements.append(Mock())
        
        # Reset should clear everything
        self.converter.reset()
        
        assert len(self.converter.mask_definitions) == 0
        assert len(self.converter.clippath_definitions) == 0
        assert len(self.converter.masked_elements) == 0
        assert len(self.converter.clipped_elements) == 0


class TestIntegrationScenarios:
    """Test complex integration scenarios."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = TestMaskingConverter()
        self.context = Mock()
        self.context.get_next_shape_id.side_effect = range(1000, 2000)  # Sequential IDs
    
    def test_complete_mask_workflow(self):
        """Test complete mask processing workflow."""
        # Step 1: Process mask definition
        mask_element = ET.Element("mask")
        mask_element.set("id", "complexMask")
        mask_element.set("mask-type", "luminance")
        mask_element.set("maskUnits", "objectBoundingBox")
        
        rect_content = ET.SubElement(mask_element, "rect")
        rect_content.set("fill", "white")
        rect_content.set("width", "100%")
        rect_content.set("height", "100%")
        
        result1 = self.converter._process_mask_definition(mask_element, self.context)
        assert result1 == ""
        assert "complexMask" in self.converter.mask_definitions
        
        # Step 2: Apply mask to element
        target_element = ET.Element("circle")
        target_element.set("mask", "url(#complexMask)")
        
        with patch.object(self.converter, '_mask_requires_rasterization', return_value=False):
            with patch.object(self.converter, '_generate_powerpoint_mask_output') as mock_output:
                mock_output.return_value = "mask applied"
                result2 = self.converter._apply_mask(target_element, "url(#complexMask)", self.context)
        
        assert result2 == "mask applied"
        assert len(self.converter.masked_elements) == 1
    
    def test_complete_clippath_workflow(self):
        """Test complete clipPath processing workflow."""
        # Step 1: Process clipPath definition
        clippath_element = ET.Element("clipPath")
        clippath_element.set("id", "rectClip")
        clippath_element.set("clipPathUnits", "userSpaceOnUse")
        
        rect_shape = ET.SubElement(clippath_element, "rect")
        rect_shape.set("x", "10")
        rect_shape.set("y", "10")
        rect_shape.set("width", "80")
        rect_shape.set("height", "60")
        
        result1 = self.converter._process_clippath_definition(clippath_element, self.context)
        assert result1 == ""
        assert "rectClip" in self.converter.clippath_definitions
        
        # Step 2: Apply clipping to element
        target_element = ET.Element("path")
        target_element.set("clip-path", "url(#rectClip)")
        
        with patch.object(self.converter, '_generate_powerpoint_clip_output') as mock_output:
            mock_output.return_value = "clip applied"
            result2 = self.converter._apply_clipping(target_element, "url(#rectClip)", self.context)
        
        assert result2 == "clip applied"
        assert len(self.converter.clipped_elements) == 1
    
    def test_element_with_both_mask_and_clip(self):
        """Test element with both mask and clipPath applied."""
        # Setup mask definition
        mask_def = MaskDefinition(
            id="testMask", mask_type=MaskType.LUMINANCE,
            units="objectBoundingBox", mask_units="userSpaceOnUse",
            x=0, y=0, width=1, height=1, content_elements=[]
        )
        self.converter.mask_definitions["testMask"] = mask_def
        
        # Setup clipPath definition
        clip_def = ClipPathDefinition(
            id="testClip", units="userSpaceOnUse", clip_rule="nonzero",
            path_data="M 0 0 L 100 100 Z", clipping_type=ClippingType.PATH_BASED
        )
        self.converter.clippath_definitions["testClip"] = clip_def
        
        # Element with both mask and clip-path
        element = ET.Element("rect")
        element.set("mask", "url(#testMask)")
        element.set("clip-path", "url(#testClip)")
        
        with patch.object(self.converter, '_apply_mask') as mock_mask:
            mock_mask.return_value = "mask output"
            with patch.object(self.converter, '_apply_clipping') as mock_clip:
                mock_clip.return_value = "clip output"
                
                result = self.converter._apply_masking_clipping(element, self.context)
                
                assert result == "mask output\nclip output"
                mock_mask.assert_called_once_with(element, "url(#testMask)", self.context)
                mock_clip.assert_called_once_with(element, "url(#testClip)", self.context)
    
    def test_nested_defs_processing(self):
        """Test processing masks and clipPaths within defs element."""
        # Create defs element containing both mask and clipPath
        defs_element = ET.Element("defs")
        
        # Mask in defs
        mask_element = ET.SubElement(defs_element, "mask")
        mask_element.set("id", "defsMask")
        
        # ClipPath in defs
        clippath_element = ET.SubElement(defs_element, "clipPath")
        clippath_element.set("id", "defsClip")
        
        # Process individual elements (converter handles elements one by one)
        result1 = self.converter.convert(mask_element, self.context)
        result2 = self.converter.convert(clippath_element, self.context)
        
        assert result1 == ""  # Definitions don't produce output
        assert result2 == ""
        assert "defsMask" in self.converter.mask_definitions
        assert "defsClip" in self.converter.clippath_definitions
    
    def test_multiple_masks_same_element(self):
        """Test edge case with multiple mask applications."""
        # Setup multiple mask definitions
        for i in range(3):
            mask_def = MaskDefinition(
                id=f"mask{i}", mask_type=MaskType.LUMINANCE,
                units="objectBoundingBox", mask_units="userSpaceOnUse",
                x=0, y=0, width=1, height=1, content_elements=[]
            )
            self.converter.mask_definitions[f"mask{i}"] = mask_def
        
        element = ET.Element("rect")
        
        # Apply multiple masks (simulate sequential processing)
        for i in range(3):
            with patch.object(self.converter, '_mask_requires_rasterization', return_value=False):
                with patch.object(self.converter, '_generate_powerpoint_mask_output', return_value=""):
                    self.converter._apply_mask(element, f"url(#mask{i})", self.context)
        
        # Should have 3 mask applications
        assert len(self.converter.masked_elements) == 3
        assert all(app.target_element == element for app in self.converter.masked_elements)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
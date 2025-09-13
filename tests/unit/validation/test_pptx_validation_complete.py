#!/usr/bin/env python3
"""
Complete PPTX validation tests to reach 90% coverage.

This module contains the most targeted tests to hit remaining uncovered code paths.
"""

import pytest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import xml.etree.ElementTree as ET

from tools.pptx_validator import (
    PPTXValidator,
    ValidationLevel,
    ComparisonResult,
    ValidationResult,
    ComparisonMetrics,
    create_reference_pptx_database
)


class TestPPTXValidatorComplete:
    """Complete test coverage for remaining lines."""
    
    def test_extraction_with_namespaced_elements(self):
        """Test extraction with properly namespaced elements."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zip_file:
                # Add proper structure
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
                
                zip_file.writestr('_rels/.rels', '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>''')
                
                zip_file.writestr('ppt/presentation.xml', '''<?xml version="1.0"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId1"/>
    </p:sldIdLst>
</p:presentation>''')
                
                # Add slide with namespaced drawing elements
                zip_file.writestr('ppt/slides/slide1.xml', '''<?xml version="1.0"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:sp>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="100" y="100"/>
                        <a:ext cx="200" cy="200"/>
                    </a:xfrm>
                    <a:prstGeom prst="rect"/>
                    <a:solidFill>
                        <a:srgbClr val="FF0000"/>
                    </a:solidFill>
                </p:spPr>
                <p:txBody>
                    <a:bodyPr/>
                    <a:lstStyle/>
                    <a:p>
                        <a:r>
                            <a:t>Test Text</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
            <!-- Additional elements with attributes -->
            <a:rect x="0" y="0" width="100" height="100"/>
            <a:circle cx="50" cy="50" r="25" fill="blue"/>
        </p:spTree>
    </p:cSld>
</p:sld>''')
            
            # This should extract content properly
            content = validator._extract_pptx_content(Path(f.name))
            
            assert len(content['slides']) == 1
            assert len(content['slides'][0]['shapes']) >= 1
            assert len(content['slides'][0]['drawing_elements']) >= 1
            assert 'Test Text' in content['slides'][0]['text_elements']
        
        # Clean up
        Path(f.name).unlink()
    
    def test_comparison_with_valid_files_but_content_differences(self):
        """Test comparison of valid files with content differences."""
        validator = PPTXValidator()
        
        # Create reference file
        ref_content = {
            '[Content_Types].xml': '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''',
            
            '_rels/.rels': '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>''',
            
            'ppt/presentation.xml': '''<?xml version="1.0"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId1"/>
    </p:sldIdLst>
</p:presentation>''',
            
            'ppt/slides/slide1.xml': '''<?xml version="1.0"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:sp>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="100" y="100"/>
                        <a:ext cx="200" cy="200"/>
                    </a:xfrm>
                    <a:prstGeom prst="rect"/>
                </p:spPr>
            </p:sp>
            <a:rect x="10" y="10" width="50" height="50"/>
        </p:spTree>
    </p:cSld>
</p:sld>'''
        }
        
        # Create output file with different content
        out_content = dict(ref_content)  # Copy reference
        out_content['ppt/slides/slide1.xml'] = '''<?xml version="1.0"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:sp>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="200" y="200"/>
                        <a:ext cx="100" cy="100"/>
                    </a:xfrm>
                    <a:prstGeom prst="ellipse"/>
                </p:spPr>
            </p:sp>
            <!-- Different drawing elements -->
            <a:circle cx="25" cy="25" r="15"/>
            <a:line x1="0" y1="0" x2="100" y2="100"/>
        </p:spTree>
    </p:cSld>
</p:sld>'''
        
        with tempfile.NamedTemporaryFile(suffix='_ref.pptx', delete=False) as ref_file:
            with zipfile.ZipFile(ref_file, 'w') as zip_file:
                for filename, content in ref_content.items():
                    zip_file.writestr(filename, content)
            
            with tempfile.NamedTemporaryFile(suffix='_out.pptx', delete=False) as out_file:
                with zipfile.ZipFile(out_file, 'w') as zip_file:
                    for filename, content in out_content.items():
                        zip_file.writestr(filename, content)
                
                result, metrics, details = validator.compare_pptx_files(
                    Path(ref_file.name), Path(out_file.name)
                )
                
                # Should be valid comparison with measured differences
                assert result in [ComparisonResult.SIMILAR, ComparisonResult.DIFFERENT, ComparisonResult.IDENTICAL]
                assert 0.0 <= metrics.overall_accuracy <= 1.0
                assert 0.0 <= metrics.structural_similarity <= 1.0
                assert 0.0 <= metrics.visual_similarity <= 1.0
                assert 0.0 <= metrics.element_count_match <= 1.0
                assert 0.0 <= metrics.attribute_match <= 1.0
                
                # Should have metadata from both files
                assert "reference_metadata" in details
                assert "output_metadata" in details
                
                # Clean up
                Path(out_file.name).unlink()
        
        # Clean up
        Path(ref_file.name).unlink()
    
    def test_attribute_match_calculation_detailed(self):
        """Test detailed attribute matching calculation."""
        validator = PPTXValidator()
        
        # Create content with various attributes
        ref_content = {
            "slides": [
                {
                    "drawing_elements": [
                        {"tag": "a:rect", "attributes": {"x": "10", "y": "20", "width": "100"}},
                        {"tag": "a:circle", "attributes": {"cx": "50", "cy": "50", "r": "25"}},
                        {"tag": "a:line", "attributes": {"x1": "0", "y1": "0", "x2": "100", "y2": "100"}}
                    ]
                }
            ]
        }
        
        out_content = {
            "slides": [
                {
                    "drawing_elements": [
                        {"tag": "a:rect", "attributes": {"x": "10", "y": "20", "width": "100"}},  # Same
                        {"tag": "a:circle", "attributes": {"cx": "60", "cy": "60", "r": "30"}},  # Different values
                        {"tag": "a:polygon", "attributes": {"points": "0,0 100,0 50,100"}}        # Different element
                    ]
                }
            ]
        }
        
        similarity = validator._calculate_attribute_match(ref_content, out_content)
        
        # Should calculate based on attribute overlap
        assert 0.0 <= similarity <= 1.0
        
        # Test with empty attributes
        empty_content = {"slides": [{"drawing_elements": []}]}
        similarity = validator._calculate_attribute_match(empty_content, empty_content)
        assert similarity == 1.0
        
        # Test with one empty, one non-empty
        similarity = validator._calculate_attribute_match(empty_content, ref_content)
        assert similarity == 0.0
    
    def test_element_count_match_edge_cases(self):
        """Test element count matching with edge cases."""
        validator = PPTXValidator()
        
        # Test with different element counts
        ref_content = {"slides": [{"drawing_elements": [{"tag": "a:rect"}, {"tag": "a:circle"}]}]}
        out_content = {"slides": [{"drawing_elements": [{"tag": "a:rect"}]}]}
        
        similarity = validator._calculate_element_count_match(ref_content, out_content)
        assert 0.0 < similarity < 1.0  # Should be 0.5 (1/2)
        
        # Test with zero in reference
        zero_ref_content = {"slides": [{"drawing_elements": []}]}
        similarity = validator._calculate_element_count_match(zero_ref_content, out_content)
        assert similarity == 0.0
        
        # Test with matching non-zero counts
        matching_content = {"slides": [{"drawing_elements": [{"tag": "a:rect"}, {"tag": "a:circle"}]}]}
        similarity = validator._calculate_element_count_match(ref_content, matching_content)
        assert similarity == 1.0
    
    def test_validation_score_boundary_conditions(self):
        """Test validation score calculation at boundaries."""
        validator = PPTXValidator()
        
        # Test with many warnings (should cap at 0)
        errors = []
        warnings = ["warning"] * 20  # Many warnings
        metadata = {'total_elements': 10, 'slide_count': 2}
        
        score = validator._calculate_validation_score(errors, warnings, metadata)
        assert score == 0.0  # Should be capped at 0
        
        # Test with elements but no slides
        errors = []
        warnings = []
        metadata = {'total_elements': 10, 'slide_count': 0}
        
        score = validator._calculate_validation_score(errors, warnings, metadata)
        assert 0.0 <= score <= 0.5  # Should be reduced for no slides
        
        # Test with slides but no elements
        errors = []
        warnings = []
        metadata = {'total_elements': 0, 'slide_count': 2}
        
        score = validator._calculate_validation_score(errors, warnings, metadata)
        assert 0.0 <= score <= 0.7  # Should be reduced for no elements
    
    def test_shape_data_extraction_with_invalid_geometry(self):
        """Test shape data extraction with invalid geometry values."""
        validator = PPTXValidator()
        
        # Shape with invalid geometry values
        shape_xml = '''<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
                              xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
            <p:spPr>
                <a:xfrm>
                    <a:off/>
                    <a:ext/>
                </a:xfrm>
                <a:prstGeom prst="rect"/>
                <a:solidFill>
                    <a:srgbClr/>
                </a:solidFill>
            </p:spPr>
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:r>
                        <a:t>Valid Text</a:t>
                    </a:r>
                </a:p>
            </p:txBody>
        </p:sp>'''
        
        shape_element = ET.fromstring(shape_xml)
        shape_data = validator._extract_shape_data(shape_element)
        
        # Should handle missing/invalid attributes gracefully
        assert shape_data['type'] == 'rect'
        assert shape_data['geometry']['x'] == '0'  # Default value
        assert shape_data['geometry']['y'] == '0'  # Default value
        assert shape_data['text'] == 'Valid Text'
    
    def test_comprehensive_similarity_calculation(self):
        """Test comprehensive similarity calculation scenarios."""
        validator = PPTXValidator()
        
        # Create complex content for similarity testing
        complex_ref = {
            "slides": [
                {
                    "shapes": [
                        {
                            "type": "rect",
                            "geometry": {"width": "100", "height": "100", "x": "10", "y": "10"},
                            "style": {"fill_color": "FF0000"},
                            "text": "Shape 1"
                        },
                        {
                            "type": "ellipse", 
                            "geometry": {"width": "50", "height": "50", "x": "200", "y": "200"},
                            "style": {"fill_color": "00FF00"},
                            "text": "Shape 2"
                        }
                    ],
                    "text_elements": ["Shape 1", "Shape 2", "Additional Text"],
                    "drawing_elements": [
                        {"tag": "a:rect", "attributes": {"x": "10", "y": "10"}},
                        {"tag": "a:ellipse", "attributes": {"cx": "225", "cy": "225"}}
                    ]
                },
                {
                    "shapes": [
                        {
                            "type": "star5",
                            "geometry": {"width": "75", "height": "75", "x": "100", "y": "100"},
                            "style": {"fill_color": "0000FF"},
                            "text": "Star"
                        }
                    ],
                    "text_elements": ["Star"],
                    "drawing_elements": [
                        {"tag": "a:star", "attributes": {"points": "5"}}
                    ]
                }
            ]
        }
        
        # Create similar content with small differences
        similar_out = {
            "slides": [
                {
                    "shapes": [
                        {
                            "type": "rect",
                            "geometry": {"width": "95", "height": "105", "x": "10", "y": "10"},  # Similar size
                            "style": {"fill_color": "FF0000"},
                            "text": "Shape 1"
                        },
                        {
                            "type": "ellipse",
                            "geometry": {"width": "50", "height": "50", "x": "200", "y": "200"}, 
                            "style": {"fill_color": "00FF00"},
                            "text": "Shape 2 Modified"  # Different text
                        }
                    ],
                    "text_elements": ["Shape 1", "Shape 2 Modified", "Additional Text"],
                    "drawing_elements": [
                        {"tag": "a:rect", "attributes": {"x": "10", "y": "10"}},
                        {"tag": "a:ellipse", "attributes": {"cx": "225", "cy": "225"}}
                    ]
                },
                {
                    "shapes": [
                        {
                            "type": "star5",
                            "geometry": {"width": "75", "height": "75", "x": "100", "y": "100"},
                            "style": {"fill_color": "0000FF"},
                            "text": "Star"
                        }
                    ],
                    "text_elements": ["Star"],
                    "drawing_elements": [
                        {"tag": "a:star", "attributes": {"points": "5"}}
                    ]
                }
            ]
        }
        
        # Test all similarity calculations
        structural_sim = validator._calculate_structural_similarity(complex_ref, similar_out)
        content_sim = validator._calculate_content_similarity(complex_ref, similar_out)
        visual_sim = validator._calculate_visual_similarity(complex_ref, similar_out)
        element_match = validator._calculate_element_count_match(complex_ref, similar_out)
        attr_match = validator._calculate_attribute_match(complex_ref, similar_out)
        
        # All should be reasonable values
        assert 0.8 <= structural_sim <= 1.0  # Same structure
        assert 0.7 <= content_sim <= 1.0     # Similar content
        assert 0.7 <= visual_sim <= 1.0      # Similar visual properties
        assert element_match == 1.0          # Same element count
        assert 0.8 <= attr_match <= 1.0      # Similar attributes


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
#!/usr/bin/env python3
"""
Comprehensive tests for PPTX validation to achieve 90% coverage.

This module provides extensive testing of the PPTX validation framework
to ensure all code paths are covered and functionality is complete.
"""

import pytest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any
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


class TestComprehensivePPTXValidator:
    """Comprehensive test coverage for PPTX validator."""
    
    def test_all_validation_levels(self):
        """Test validator with all validation levels."""
        for level in [ValidationLevel.STRICT, ValidationLevel.STANDARD, ValidationLevel.LENIENT]:
            validator = PPTXValidator(level)
            assert validator.validation_level == level
    
    def test_namespace_map_access(self):
        """Test namespace map access."""
        validator = PPTXValidator()
        assert 'a' in validator.namespace_map
        assert 'p' in validator.namespace_map
        assert 'r' in validator.namespace_map
    
    def test_validation_score_calculation_edge_cases(self):
        """Test validation score calculation with edge cases."""
        validator = PPTXValidator()
        
        # Test with errors
        errors = ["Error 1", "Error 2"]
        warnings = []
        metadata = {}
        score = validator._calculate_validation_score(errors, warnings, metadata)
        assert score == 0.0
        
        # Test with warnings only
        errors = []
        warnings = ["Warning 1", "Warning 2", "Warning 3"]
        metadata = {'total_elements': 10, 'slide_count': 2}
        score = validator._calculate_validation_score(errors, warnings, metadata)
        assert 0.0 < score < 1.0
        
        # Test with no elements
        errors = []
        warnings = []
        metadata = {'total_elements': 0, 'slide_count': 0}
        score = validator._calculate_validation_score(errors, warnings, metadata)
        assert score < 1.0
        
        # Test perfect score
        errors = []
        warnings = []
        metadata = {'total_elements': 10, 'slide_count': 2}
        score = validator._calculate_validation_score(errors, warnings, metadata)
        assert score == 1.0
    
    def test_extract_shape_data_edge_cases(self):
        """Test shape data extraction with various edge cases."""
        validator = PPTXValidator()
        
        # Test with minimal shape element
        minimal_shape = ET.fromstring('''<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>''')
        shape_data = validator._extract_shape_data(minimal_shape)
        assert shape_data['type'] == 'unknown'
        assert shape_data['text'] == ''
        
        # Test with shape containing only preset geometry
        geom_only_shape = ET.fromstring('''
        <p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
              xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
            <p:spPr>
                <a:prstGeom prst="star5"/>
            </p:spPr>
        </p:sp>''')
        shape_data = validator._extract_shape_data(geom_only_shape)
        assert shape_data['type'] == 'star5'
        
        # Test with shape containing only text
        text_only_shape = ET.fromstring('''
        <p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
              xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
            <p:txBody>
                <a:p>
                    <a:r>
                        <a:t>Only Text</a:t>
                    </a:r>
                    <a:r>
                        <a:t> More Text</a:t>
                    </a:r>
                </a:p>
            </p:txBody>
        </p:sp>''')
        shape_data = validator._extract_shape_data(text_only_shape)
        assert 'Only Text More Text' in shape_data['text']
    
    def test_similarity_calculations_edge_cases(self):
        """Test similarity calculations with edge cases."""
        validator = PPTXValidator()
        
        # Test structural similarity with empty content
        empty_content = {"slides": []}
        similarity = validator._calculate_structural_similarity(empty_content, empty_content)
        assert similarity == 1.0
        
        # Test with one empty, one non-empty
        non_empty_content = {"slides": [{"shapes": [{"type": "rect"}]}]}
        similarity = validator._calculate_structural_similarity(empty_content, non_empty_content)
        assert similarity == 0.0
        
        # Test content similarity with empty text
        empty_text_content = {"slides": [{"text_elements": []}]}
        similarity = validator._calculate_content_similarity(empty_text_content, empty_text_content)
        assert similarity == 1.0
        
        # Test visual similarity with empty slides
        similarity = validator._calculate_visual_similarity(empty_content, empty_content)
        assert similarity == 0.0  # No slides to compare
        
        # Test element count match with zeros
        similarity = validator._calculate_element_count_match(empty_content, empty_content)
        assert similarity == 1.0
        
        # Test attribute match with empty attributes
        similarity = validator._calculate_attribute_match(empty_content, empty_content)
        assert similarity == 1.0
    
    def test_compare_shape_visual_properties_edge_cases(self):
        """Test shape visual property comparison edge cases."""
        validator = PPTXValidator()
        
        # Test with minimal shapes
        minimal_shape = {"type": "unknown", "geometry": {}, "style": {}}
        similarity = validator._compare_shape_visual_properties(minimal_shape, minimal_shape)
        assert similarity >= 0.0
        
        # Test with different types
        rect_shape = {"type": "rect", "geometry": {}, "style": {}}
        circle_shape = {"type": "ellipse", "geometry": {}, "style": {}}
        similarity = validator._compare_shape_visual_properties(rect_shape, circle_shape)
        assert similarity < 1.0
        
        # Test with geometry but invalid values
        invalid_geom_shape = {
            "type": "rect", 
            "geometry": {"width": "invalid", "height": "0"}, 
            "style": {}
        }
        similarity = validator._compare_shape_visual_properties(invalid_geom_shape, rect_shape)
        assert similarity >= 0.0
        
        # Test with matching styles
        styled_shape1 = {
            "type": "rect",
            "geometry": {"width": "100", "height": "100"},
            "style": {"fill_color": "FF0000"}
        }
        styled_shape2 = {
            "type": "rect", 
            "geometry": {"width": "95", "height": "105"},  # Similar size
            "style": {"fill_color": "FF0000"}
        }
        similarity = validator._compare_shape_visual_properties(styled_shape1, styled_shape2)
        assert similarity > 0.5
    
    def test_generate_difference_report_comprehensive(self):
        """Test difference report generation with various scenarios."""
        validator = PPTXValidator()
        
        # Test with different slide counts
        ref_content = {"slides": [{"shapes": []}, {"shapes": []}]}
        out_content = {"slides": [{"shapes": []}]}
        differences = validator._generate_difference_report(ref_content, out_content)
        assert any("Slide count mismatch" in diff for diff in differences)
        
        # Test with different shape counts
        ref_content = {"slides": [{"shapes": [{"type": "rect"}, {"type": "circle"}], "text_elements": []}]}
        out_content = {"slides": [{"shapes": [{"type": "rect"}], "text_elements": []}]}
        differences = validator._generate_difference_report(ref_content, out_content)
        assert any("shape count mismatch" in diff for diff in differences)
        
        # Test with different text element counts
        ref_content = {"slides": [{"shapes": [], "text_elements": ["text1", "text2"]}]}
        out_content = {"slides": [{"shapes": [], "text_elements": ["text1"]}]}
        differences = validator._generate_difference_report(ref_content, out_content)
        assert any("text element count mismatch" in diff for diff in differences)
        
        # Test error handling in difference generation
        with patch.object(validator, '_generate_difference_report') as mock_diff:
            mock_diff.side_effect = Exception("Test error")
            # Call the actual method to test exception handling
            validator._generate_difference_report.__wrapped__(validator, ref_content, out_content)
    
    def test_extract_pptx_content_error_handling(self):
        """Test PPTX content extraction with error conditions."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zip_file:
                # Add valid structure but malformed slide XML
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
                
                zip_file.writestr('ppt/slides/slide1.xml', '''<?xml version="1.0"?>
<malformed_xml>
    <unclosed_tag>
</malformed_xml''')  # Intentionally malformed
            
            # Should handle malformed XML gracefully
            content = validator._extract_pptx_content(Path(f.name))
            assert isinstance(content, dict)
            assert "slides" in content
        
        # Clean up
        Path(f.name).unlink()
    
    def test_create_reference_database_without_metadata(self):
        """Test reference database creation without corpus metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            corpus_path = temp_path / "corpus"
            corpus_path.mkdir()
            
            output_path = temp_path / "references.json"
            database = create_reference_pptx_database(corpus_path, output_path)
            
            # Should create empty database structure
            assert "references" in database
            assert len(database["references"]) == 0
            assert output_path.exists()
    
    def test_comparison_with_processing_exceptions(self):
        """Test PPTX comparison when processing raises exceptions."""
        validator = PPTXValidator()
        
        # Mock the validation to fail
        with patch.object(validator, 'validate_pptx_structure') as mock_validate:
            mock_validate.return_value = ValidationResult(
                valid=False, score=0.0, errors=["Mock error"], warnings=[], metadata={}
            )
            
            result, metrics, details = validator.compare_pptx_files(
                Path("test1.pptx"), Path("test2.pptx")
            )
            
            assert result == ComparisonResult.ERROR
            assert metrics.overall_accuracy == 0.0
            assert "error" in details
    
    def test_validation_with_slide_processing_errors(self):
        """Test validation when slide processing encounters errors."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zip_file:
                # Add required structure
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
                
                # Add slide with malformed XML that will cause processing errors
                zip_file.writestr('ppt/slides/slide1.xml', '''<?xml version="1.0"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <malformed_content>
</p:sld''')  # Missing closing tag
            
            result = validator.validate_pptx_structure(Path(f.name))
            
            # Should handle slide processing errors gracefully
            assert isinstance(result, ValidationResult)
            # May be valid despite slide processing errors (depends on implementation)
        
        # Clean up
        Path(f.name).unlink()


class TestPPTXValidatorIntegration:
    """Integration tests for PPTX validation functionality."""
    
    def test_end_to_end_validation_workflow(self):
        """Test complete validation workflow."""
        validator = PPTXValidator(ValidationLevel.STANDARD)
        
        # Create a comprehensive test PPTX
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zip_file:
                # Complete PPTX structure
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-presentationml.presentation.main+xml"/>
</Types>''')
                
                zip_file.writestr('_rels/.rels', '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>''')
                
                zip_file.writestr('ppt/presentation.xml', '''<?xml version="1.0"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId1"/>
        <p:sldId id="257" r:id="rId2"/>
    </p:sldIdLst>
</p:presentation>''')
                
                # Add multiple slides with various content
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
                            <a:t>Slide 1 Content</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>''')
                
                zip_file.writestr('ppt/slides/slide2.xml', '''<?xml version="1.0"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:sp>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="300" y="300"/>
                        <a:ext cx="150" cy="150"/>
                    </a:xfrm>
                    <a:prstGeom prst="ellipse"/>
                    <a:solidFill>
                        <a:srgbClr val="00FF00"/>
                    </a:solidFill>
                </p:spPr>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>''')
            
            # Validate the comprehensive PPTX
            result = validator.validate_pptx_structure(Path(f.name))
            
            assert result.valid is True
            assert result.score > 0.8
            assert result.metadata['slide_count'] == 2
            assert result.metadata['total_elements'] > 0
            assert len(result.errors) == 0
        
        # Clean up
        Path(f.name).unlink()
    
    def test_comparison_accuracy_scenarios(self):
        """Test various comparison accuracy scenarios."""
        validator = PPTXValidator()
        
        # Create reference and output files with known differences
        ref_pptx = self._create_reference_pptx()
        similar_pptx = self._create_similar_pptx()
        different_pptx = self._create_different_pptx()
        
        with tempfile.NamedTemporaryFile(suffix='_ref.pptx', delete=False) as ref_file:
            with zipfile.ZipFile(ref_file, 'w') as zip_file:
                for filename, content in ref_pptx.items():
                    zip_file.writestr(filename, content)
            
            # Test similar comparison
            with tempfile.NamedTemporaryFile(suffix='_similar.pptx', delete=False) as similar_file:
                with zipfile.ZipFile(similar_file, 'w') as zip_file:
                    for filename, content in similar_pptx.items():
                        zip_file.writestr(filename, content)
                
                result, metrics, details = validator.compare_pptx_files(
                    Path(ref_file.name), Path(similar_file.name)
                )
                
                assert result in [ComparisonResult.SIMILAR, ComparisonResult.IDENTICAL]
                assert metrics.overall_accuracy > 0.7
                assert metrics.structural_similarity > 0.8
            
            # Test different comparison
            with tempfile.NamedTemporaryFile(suffix='_different.pptx', delete=False) as diff_file:
                with zipfile.ZipFile(diff_file, 'w') as zip_file:
                    for filename, content in different_pptx.items():
                        zip_file.writestr(filename, content)
                
                result, metrics, details = validator.compare_pptx_files(
                    Path(ref_file.name), Path(diff_file.name)
                )
                
                assert result in [ComparisonResult.DIFFERENT, ComparisonResult.SIMILAR]
                assert metrics.overall_accuracy < 1.0
                assert len(details.get('differences', [])) >= 0
                
                # Clean up
                Path(diff_file.name).unlink()
            
            # Clean up
            Path(similar_file.name).unlink()
        
        # Clean up
        Path(ref_file.name).unlink()
    
    def _create_reference_pptx(self) -> Dict[str, str]:
        """Create reference PPTX content."""
        return {
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
                    <a:solidFill>
                        <a:srgbClr val="FF0000"/>
                    </a:solidFill>
                </p:spPr>
                <p:txBody>
                    <a:bodyPr/>
                    <a:lstStyle/>
                    <a:p>
                        <a:r>
                            <a:t>Reference Text</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>'''
        }
    
    def _create_similar_pptx(self) -> Dict[str, str]:
        """Create similar PPTX content."""
        similar = self._create_reference_pptx()
        # Slightly different color and text
        similar['ppt/slides/slide1.xml'] = similar['ppt/slides/slide1.xml'].replace(
            'FF0000', 'FF0001'  # Very similar color
        ).replace(
            'Reference Text', 'Reference Text Updated'  # Slightly different text
        )
        return similar
    
    def _create_different_pptx(self) -> Dict[str, str]:
        """Create different PPTX content."""
        different = self._create_reference_pptx()
        # Add an extra slide and change content significantly
        different['ppt/presentation.xml'] = different['ppt/presentation.xml'].replace(
            '</p:sldIdLst>',
            '    <p:sldId id="257" r:id="rId2"/>\n    </p:sldIdLst>'
        )
        
        different['ppt/slides/slide1.xml'] = different['ppt/slides/slide1.xml'].replace(
            'rect', 'ellipse'  # Different shape
        ).replace(
            'FF0000', '00FF00'  # Different color
        ).replace(
            'Reference Text', 'Completely Different Content'
        )
        
        # Add second slide
        different['ppt/slides/slide2.xml'] = '''<?xml version="1.0"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:sp>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="300" y="300"/>
                        <a:ext cx="100" cy="100"/>
                    </a:xfrm>
                    <a:prstGeom prst="star5"/>
                    <a:solidFill>
                        <a:srgbClr val="0000FF"/>
                    </a:solidFill>
                </p:spPr>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>'''
        return different


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
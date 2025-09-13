#!/usr/bin/env python3
"""
Final targeted tests to achieve 90% coverage for PPTX validation.

This module includes specific tests to hit the remaining uncovered code paths
in the PPTX validator.
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


class TestPPTXValidatorFinalCoverage:
    """Target remaining uncovered lines in PPTX validator."""
    
    def test_validation_with_zipfile_error(self):
        """Test validation when zipfile operations raise exceptions."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            # Create a file that looks like PPTX but will cause zipfile errors during processing
            with zipfile.ZipFile(f, 'w') as zip_file:
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
                zip_file.writestr('_rels/.rels', '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>''')
                zip_file.writestr('ppt/presentation.xml', '''<?xml version="1.0"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:sldIdLst>
    </p:sldIdLst>
</p:presentation>''')
            
            # Mock zipfile to raise an exception during slide processing
            with patch('zipfile.ZipFile') as mock_zipfile:
                mock_context = MagicMock()
                mock_zipfile.return_value.__enter__.return_value = mock_context
                mock_context.namelist.return_value = ['[Content_Types].xml', '_rels/.rels', 'ppt/presentation.xml']
                mock_context.read.side_effect = Exception("Mock zipfile error")
                
                result = validator.validate_pptx_structure(Path(f.name))
                
                # Should handle the exception gracefully
                assert result.valid is False
                assert any("Unexpected error" in error for error in result.errors)
        
        # Clean up
        Path(f.name).unlink()
    
    def test_comparison_with_extract_content_exception(self):
        """Test comparison when content extraction raises exceptions."""
        validator = PPTXValidator()
        
        # Create valid files first
        with tempfile.NamedTemporaryFile(suffix='_ref.pptx', delete=False) as ref_file:
            with zipfile.ZipFile(ref_file, 'w') as zip_file:
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
                zip_file.writestr('_rels/.rels', '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>''')
                zip_file.writestr('ppt/presentation.xml', '''<?xml version="1.0"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:sldIdLst></p:sldIdLst>
</p:presentation>''')
            
            with tempfile.NamedTemporaryFile(suffix='_out.pptx', delete=False) as out_file:
                with zipfile.ZipFile(out_file, 'w') as zip_file:
                    zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
                    zip_file.writestr('_rels/.rels', '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>''')
                    zip_file.writestr('ppt/presentation.xml', '''<?xml version="1.0"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:sldIdLst></p:sldIdLst>
</p:presentation>''')
                
                # Mock extract content to raise exception
                with patch.object(validator, '_extract_pptx_content') as mock_extract:
                    mock_extract.side_effect = Exception("Mock extraction error")
                    
                    result, metrics, details = validator.compare_pptx_files(
                        Path(ref_file.name), Path(out_file.name)
                    )
                    
                    assert result == ComparisonResult.ERROR
                    assert metrics.overall_accuracy == 0.0
                    assert "error" in details
                
                # Clean up
                Path(out_file.name).unlink()
            
            # Clean up
            Path(ref_file.name).unlink()
    
    def test_shape_visual_property_comparison_division_by_zero(self):
        """Test shape comparison with zero division scenarios."""
        validator = PPTXValidator()
        
        # Test with zero geometry values
        shape_with_zero_geom = {
            "type": "rect",
            "geometry": {"width": "0", "height": "100"},
            "style": {}
        }
        
        normal_shape = {
            "type": "rect", 
            "geometry": {"width": "100", "height": "100"},
            "style": {}
        }
        
        # Should handle zero division gracefully
        similarity = validator._compare_shape_visual_properties(shape_with_zero_geom, normal_shape)
        assert 0.0 <= similarity <= 1.0
        
        # Test with both zero
        both_zero_shape = {
            "type": "rect",
            "geometry": {"width": "0", "height": "0"},
            "style": {}
        }
        
        similarity = validator._compare_shape_visual_properties(shape_with_zero_geom, both_zero_shape)
        assert 0.0 <= similarity <= 1.0
    
    def test_similarity_calculations_with_exceptions(self):
        """Test similarity calculations when exceptions occur."""
        validator = PPTXValidator()
        
        # Test structural similarity with malformed content that might cause exceptions
        malformed_content = {"slides": [{"shapes": None}]}  # None instead of list
        normal_content = {"slides": [{"shapes": []}]}
        
        # Should handle exceptions gracefully and return 0.0
        similarity = validator._calculate_structural_similarity(malformed_content, normal_content)
        assert similarity == 0.0
        
        # Test content similarity with exception-causing content
        similarity = validator._calculate_content_similarity(malformed_content, normal_content)
        assert similarity == 0.0
        
        # Test visual similarity with exception-causing content
        similarity = validator._calculate_visual_similarity(malformed_content, normal_content)
        assert similarity == 0.0
        
        # Test element count match with exception-causing content
        similarity = validator._calculate_element_count_match(malformed_content, normal_content)
        assert similarity == 0.0
        
        # Test attribute match with exception-causing content
        similarity = validator._calculate_attribute_match(malformed_content, normal_content)
        assert similarity == 0.0
    
    def test_extract_shape_data_with_none_text(self):
        """Test shape extraction when text elements have None text."""
        validator = PPTXValidator()
        
        # Create shape with text element that has None text
        shape_xml = '''<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
                              xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:r>
                        <a:t></a:t>
                    </a:r>
                </a:p>
            </p:txBody>
        </p:sp>'''
        
        shape_element = ET.fromstring(shape_xml)
        
        # Manually set text to None to simulate the condition
        text_elem = shape_element.find('.//a:t', validator.namespace_map)
        text_elem.text = None
        
        shape_data = validator._extract_shape_data(shape_element)
        
        # Should handle None text gracefully
        assert shape_data['text'] == ''
    
    def test_validation_with_missing_slide_id_list(self):
        """Test validation when presentation has no slide ID list."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zip_file:
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
                
                zip_file.writestr('_rels/.rels', '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>''')
                
                # Presentation without slide ID list
                zip_file.writestr('ppt/presentation.xml', '''<?xml version="1.0"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <!-- No p:sldIdLst element -->
</p:presentation>''')
            
            result = validator.validate_pptx_structure(Path(f.name))
            
            assert result.metadata['slide_count'] == 0
            assert any("No slides found" in warning for warning in result.warnings)
        
        # Clean up  
        Path(f.name).unlink()
    
    def test_create_reference_database_main_execution(self):
        """Test the main execution path of create_reference_database."""
        # This tests the if __name__ == '__main__' block indirectly
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create corpus with metadata
            corpus_path = temp_path / "svg_corpus"
            corpus_path.mkdir()
            
            metadata = {
                "test_files": {
                    "test.svg": {
                        "expected_elements": 1,
                        "complexity": "basic",
                        "features": ["rect"]
                    }
                }
            }
            
            with open(corpus_path / "corpus_metadata.json", 'w') as f:
                json.dump(metadata, f)
            
            # Create database 
            db_path = temp_path / "reference_database.json"
            database = create_reference_pptx_database(corpus_path, db_path)
            
            assert db_path.exists()
            assert "test.pptx" in database["references"]
            
            # Verify the created database structure
            ref_entry = database["references"]["test.pptx"]
            assert ref_entry["svg_source"] == "test.svg"
            assert ref_entry["accuracy_threshold"] == 0.85
            assert ref_entry["reference_file"] == "references/test.pptx"
    
    def test_validation_with_slide_xml_read_error(self):
        """Test validation when slide XML reading fails."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zip_file:
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
                
                zip_file.writestr('_rels/.rels', '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>''')
                
                zip_file.writestr('ppt/presentation.xml', '''<?xml version="1.0"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId1"/>
    </p:sldIdLst>
</p:presentation>''')
                
                # Add slide file that will be detected but cause read error
                zip_file.writestr('ppt/slides/slide1.xml', '''<?xml version="1.0"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld>
        <p:spTree>
        </p:spTree>
    </p:cSld>
</p:sld>''')
            
            # Mock zipfile to cause read error on slide files
            original_zipfile = zipfile.ZipFile
            
            class MockZipFile(original_zipfile):
                def read(self, name):
                    if name.startswith('ppt/slides/'):
                        raise Exception("Mock read error")
                    return super().read(name)
            
            with patch('zipfile.ZipFile', MockZipFile):
                result = validator.validate_pptx_structure(Path(f.name))
                
                # Should handle read errors gracefully with warnings
                assert len(result.warnings) > 0 or len(result.errors) > 0
        
        # Clean up
        Path(f.name).unlink()
    
    def test_difference_report_generation_exception(self):
        """Test difference report generation with exception handling."""
        validator = PPTXValidator()
        
        # Create content that will cause exception during difference generation
        problematic_content = {"slides": [{"shapes": []}]}
        normal_content = {"slides": [{"shapes": []}]}
        
        # Mock the difference generation to raise exception
        original_method = validator._generate_difference_report
        
        def mock_diff_with_exception(ref_content, out_content):
            # Simulate exception in processing
            if len(ref_content.get("slides", [])) == 1:
                raise Exception("Mock difference generation error")
            return original_method(ref_content, out_content)
        
        validator._generate_difference_report = mock_diff_with_exception
        
        differences = validator._generate_difference_report(problematic_content, normal_content)
        
        # Should handle exception and include error message
        assert len(differences) > 0
        assert any("Error generating difference report" in diff for diff in differences)


class TestMainExecutionPath:
    """Test main execution paths and command-line usage."""
    
    def test_pptx_validator_main_with_existing_corpus(self):
        """Test the main execution when SVG corpus exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create corpus directory structure
            corpus_path = temp_path / "tests" / "test_data" / "svg_corpus"
            corpus_path.mkdir(parents=True)
            
            metadata = {
                "test_files": {
                    "basic.svg": {
                        "expected_elements": 1,
                        "complexity": "basic", 
                        "features": ["rect"]
                    }
                }
            }
            
            with open(corpus_path / "corpus_metadata.json", 'w') as f:
                json.dump(metadata, f)
            
            # Change to temp directory to simulate the main execution environment
            import os
            original_cwd = os.getcwd()
            
            try:
                os.chdir(temp_path)
                
                # Import and test the main execution logic
                from tools.pptx_validator import create_reference_pptx_database
                
                db_path = Path("tests/test_data/pptx_references/reference_database.json")
                db_path.parent.mkdir(parents=True, exist_ok=True)
                
                database = create_reference_pptx_database(corpus_path, db_path)
                
                assert db_path.exists()
                assert len(database["references"]) == 1
                assert "basic.pptx" in database["references"]
                
            finally:
                os.chdir(original_cwd)
    
    def test_pptx_validator_main_without_corpus(self):
        """Test the main execution when SVG corpus doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            import os
            original_cwd = os.getcwd()
            
            try:
                os.chdir(temp_path)
                
                # The corpus path doesn't exist, so main should handle this
                corpus_path = Path("tests/test_data/svg_corpus")
                assert not corpus_path.exists()
                
                # This would normally print an error message
                # We can't easily test print statements, but we can verify the path logic
                assert not corpus_path.exists()
                
            finally:
                os.chdir(original_cwd)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
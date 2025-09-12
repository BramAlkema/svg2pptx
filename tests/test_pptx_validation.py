#!/usr/bin/env python3
"""
Tests for PPTX validation and comparison systems.

This module tests the PPTX validation framework including structure validation,
content comparison, and accuracy measurement against reference files.
"""

import pytest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any
import json
from lxml import etree as ET

from tools.pptx_validator import (
    PPTXValidator,
    ValidationLevel,
    ComparisonResult,
    ValidationResult,
    ComparisonMetrics,
    create_reference_pptx_database
)


class TestPPTXValidator:
    """Test PPTX validator functionality."""
    
    def test_validator_initialization(self):
        """Test validator can be initialized with different levels."""
        validator_standard = PPTXValidator(ValidationLevel.STANDARD)
        assert validator_standard.validation_level == ValidationLevel.STANDARD
        
        validator_comprehensive = PPTXValidator(ValidationLevel.COMPREHENSIVE)
        assert validator_comprehensive.validation_level == ValidationLevel.COMPREHENSIVE
        
        validator_minimal = PPTXValidator(ValidationLevel.MINIMAL)
        assert validator_minimal.validation_level == ValidationLevel.MINIMAL
    
    def test_validate_nonexistent_file(self):
        """Test validation of non-existent PPTX file."""
        validator = PPTXValidator()
        result = validator.validate_pptx_structure(Path("nonexistent.pptx"))
        
        assert result.valid is False
        assert result.score == 0.0
        assert len(result.errors) > 0
        assert "File not found" in result.errors[0]
    
    def test_validate_invalid_zip_file(self):
        """Test validation of invalid ZIP file."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            f.write(b"Not a valid ZIP file")
            f.flush()
            
            result = validator.validate_pptx_structure(Path(f.name))
            
        assert result.valid is False
        assert result.score == 0.0
        assert any("not a valid ZIP archive" in error for error in result.errors)
        
        # Clean up
        Path(f.name).unlink()
    
    def test_validate_minimal_valid_pptx(self):
        """Test validation of minimal valid PPTX structure."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            # Create minimal PPTX structure
            with zipfile.ZipFile(f, 'w') as zip_file:
                # Content Types
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
</Types>''')
                
                # Main relationships
                zip_file.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>''')
                
                # Presentation
                zip_file.writestr('ppt/presentation.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId1"/>
    </p:sldIdLst>
</p:presentation>''')
            
            result = validator.validate_pptx_structure(Path(f.name))
        
        assert result.valid is True
        assert result.score > 0.0
        assert len(result.errors) == 0
        assert 'slide_count' in result.metadata
        
        # Clean up
        Path(f.name).unlink()
    
    def test_validate_pptx_with_slides(self):
        """Test validation of PPTX with actual slide content."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zip_file:
                # Add required files
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
                
                # Add slide with shapes
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
        </p:spTree>
    </p:cSld>
</p:sld>''')
            
            result = validator.validate_pptx_structure(Path(f.name))
        
        assert result.valid is True
        assert result.score > 0.0
        assert result.metadata['slide_count'] == 1
        assert result.metadata['total_elements'] > 0
        
        # Clean up
        Path(f.name).unlink()


class TestPPTXComparison:
    """Test PPTX comparison functionality."""
    
    def test_compare_identical_files(self):
        """Test comparison of identical PPTX files."""
        validator = PPTXValidator()
        
        # Create two identical files
        pptx_content = self._create_test_pptx_content()
        
        with tempfile.NamedTemporaryFile(suffix='_ref.pptx', delete=False) as ref_file:
            with zipfile.ZipFile(ref_file, 'w') as zip_file:
                for filename, content in pptx_content.items():
                    zip_file.writestr(filename, content)
            
            with tempfile.NamedTemporaryFile(suffix='_out.pptx', delete=False) as out_file:
                with zipfile.ZipFile(out_file, 'w') as zip_file:
                    for filename, content in pptx_content.items():
                        zip_file.writestr(filename, content)
                
                result, metrics, details = validator.compare_pptx_files(
                    Path(ref_file.name), Path(out_file.name)
                )
        
        assert result == ComparisonResult.IDENTICAL
        assert metrics.overall_accuracy >= 0.95
        assert metrics.structural_similarity > 0.9
        
        # Clean up
        Path(ref_file.name).unlink()
        Path(out_file.name).unlink()
    
    def test_compare_different_files(self):
        """Test comparison of different PPTX files."""
        validator = PPTXValidator()
        
        ref_content = self._create_test_pptx_content()
        out_content = self._create_test_pptx_content()
        
        # Modify output content to be different
        out_content['ppt/slides/slide1.xml'] = out_content['ppt/slides/slide1.xml'].replace(
            'Test Text', 'Different Text'
        ).replace('FF0000', '00FF00')  # Change color
        
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
        
        assert result in [ComparisonResult.SIMILAR, ComparisonResult.DIFFERENT]
        assert metrics.overall_accuracy < 1.0
        assert len(details.get('differences', [])) >= 0
        
        # Clean up
        Path(ref_file.name).unlink()
        Path(out_file.name).unlink()
    
    def test_compare_invalid_files(self):
        """Test comparison of invalid PPTX files."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as invalid_file:
            invalid_file.write(b"Invalid content")
            invalid_file.flush()
            
            result, metrics, details = validator.compare_pptx_files(
                Path(invalid_file.name), Path(invalid_file.name)
            )
        
        assert result == ComparisonResult.ERROR
        assert metrics.overall_accuracy == 0.0
        assert 'error' in details
        
        # Clean up
        Path(invalid_file.name).unlink()
    
    def _create_test_pptx_content(self) -> Dict[str, str]:
        """Create test PPTX file content."""
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
                            <a:t>Test Text</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>'''
        }


class TestContentExtraction:
    """Test PPTX content extraction functionality."""
    
    def test_extract_shape_data(self):
        """Test extraction of shape data from XML elements."""
        validator = PPTXValidator()
        
        # Create test shape XML
        shape_xml = '''<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
                              xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
            <p:spPr>
                <a:xfrm>
                    <a:off x="100" y="200"/>
                    <a:ext cx="300" cy="400"/>
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
                        <a:t>Shape Text</a:t>
                    </a:r>
                </a:p>
            </p:txBody>
        </p:sp>'''
        
        shape_element = ET.fromstring(shape_xml)
        shape_data = validator._extract_shape_data(shape_element)
        
        assert shape_data['type'] == 'rect'
        assert shape_data['geometry']['x'] == '100'
        assert shape_data['geometry']['y'] == '200'
        assert shape_data['geometry']['width'] == '300'
        assert shape_data['geometry']['height'] == '400'
        assert shape_data['style']['fill_color'] == 'FF0000'
        assert shape_data['text'] == 'Shape Text'
    
    def test_extract_pptx_content_structure(self):
        """Test extraction of complete PPTX content structure."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            pptx_content = self._create_complex_pptx_content()
            
            with zipfile.ZipFile(f, 'w') as zip_file:
                for filename, content in pptx_content.items():
                    zip_file.writestr(filename, content)
            
            content = validator._extract_pptx_content(Path(f.name))
        
        assert len(content['slides']) > 0
        assert 'shapes' in content['slides'][0]
        assert 'text_elements' in content['slides'][0]
        assert 'drawing_elements' in content['slides'][0]
        
        # Check that shapes were extracted
        shapes = content['slides'][0]['shapes']
        assert len(shapes) > 0
        assert shapes[0]['type'] == 'rect'
        
        # Check that text elements were extracted
        text_elements = content['slides'][0]['text_elements']
        assert len(text_elements) > 0
        assert 'Complex Shape Text' in text_elements
        
        # Clean up
        Path(f.name).unlink()
    
    def _create_complex_pptx_content(self) -> Dict[str, str]:
        """Create complex PPTX content for testing."""
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
                        <a:ext cx="300" cy="200"/>
                    </a:xfrm>
                    <a:prstGeom prst="rect"/>
                    <a:solidFill>
                        <a:srgbClr val="0080FF"/>
                    </a:solidFill>
                </p:spPr>
                <p:txBody>
                    <a:bodyPr/>
                    <a:lstStyle/>
                    <a:p>
                        <a:r>
                            <a:t>Complex Shape Text</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
            <p:sp>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="500" y="300"/>
                        <a:ext cx="150" cy="150"/>
                    </a:xfrm>
                    <a:prstGeom prst="ellipse"/>
                    <a:solidFill>
                        <a:srgbClr val="FF8000"/>
                    </a:solidFill>
                </p:spPr>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>'''
        }


class TestReferenceDatabaseCreation:
    """Test reference database creation functionality."""
    
    def test_create_reference_database(self):
        """Test creation of reference PPTX database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock corpus metadata
            corpus_path = temp_path / "corpus"
            corpus_path.mkdir()
            
            metadata = {
                "corpus_info": {"total_files": 2},
                "test_files": {
                    "basic_shapes/rectangle.svg": {
                        "expected_elements": 1,
                        "complexity": "basic",
                        "features": ["rectangle", "fill"]
                    },
                    "text/simple_text.svg": {
                        "expected_elements": 1, 
                        "complexity": "intermediate",
                        "features": ["text", "font"]
                    }
                }
            }
            
            with open(corpus_path / "corpus_metadata.json", 'w') as f:
                json.dump(metadata, f)
            
            # Create reference database
            output_path = temp_path / "references.json"
            database = create_reference_pptx_database(corpus_path, output_path)
            
            assert output_path.exists()
            assert len(database["references"]) == 2
            assert "basic_shapes/rectangle.pptx" in database["references"]
            assert "text/simple_text.pptx" in database["references"]
            
            # Verify database structure
            ref_entry = database["references"]["basic_shapes/rectangle.pptx"]
            assert ref_entry["svg_source"] == "basic_shapes/rectangle.svg"
            assert ref_entry["expected_elements"] == 1
            assert ref_entry["complexity"] == "basic"
            assert ref_entry["accuracy_threshold"] == 0.85


class TestSimilarityCalculations:
    """Test similarity calculation algorithms."""
    
    def test_structural_similarity_identical(self):
        """Test structural similarity calculation for identical content."""
        validator = PPTXValidator()
        
        content = {
            "slides": [
                {
                    "shapes": [{"type": "rect"}, {"type": "circle"}],
                    "text_elements": ["text1"],
                    "drawing_elements": [{"tag": "a:rect"}]
                }
            ]
        }
        
        similarity = validator._calculate_structural_similarity(content, content)
        assert similarity == 1.0
    
    def test_structural_similarity_different(self):
        """Test structural similarity calculation for different content."""
        validator = PPTXValidator()
        
        ref_content = {
            "slides": [
                {"shapes": [{"type": "rect"}]},
                {"shapes": [{"type": "circle"}]}
            ]
        }
        
        out_content = {
            "slides": [
                {"shapes": [{"type": "rect"}]}
            ]
        }
        
        similarity = validator._calculate_structural_similarity(ref_content, out_content)
        assert 0.0 < similarity < 1.0
    
    def test_content_similarity_calculation(self):
        """Test content similarity calculation."""
        validator = PPTXValidator()
        
        ref_content = {
            "slides": [
                {"text_elements": ["Hello World", "Test Text"]}
            ]
        }
        
        out_content = {
            "slides": [
                {"text_elements": ["Hello World", "Test Text"]}
            ]
        }
        
        similarity = validator._calculate_content_similarity(ref_content, out_content)
        assert similarity == 1.0
    
    def test_visual_similarity_calculation(self):
        """Test visual similarity calculation."""
        validator = PPTXValidator()
        
        ref_content = {
            "slides": [
                {
                    "shapes": [{
                        "type": "rect",
                        "geometry": {"width": "100", "height": "100"},
                        "style": {"fill_color": "FF0000"}
                    }]
                }
            ]
        }
        
        out_content = {
            "slides": [
                {
                    "shapes": [{
                        "type": "rect",
                        "geometry": {"width": "100", "height": "100"},
                        "style": {"fill_color": "FF0000"}
                    }]
                }
            ]
        }
        
        similarity = validator._calculate_visual_similarity(ref_content, out_content)
        assert similarity == 1.0


class TestErrorHandling:
    """Test error handling in PPTX validation."""
    
    def test_corrupted_xml_handling(self):
        """Test handling of corrupted XML in PPTX files."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zip_file:
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
                
                zip_file.writestr('_rels/.rels', '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>''')
                
                # Corrupted presentation.xml
                zip_file.writestr('ppt/presentation.xml', '''<?xml version="1.0"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId1"/>
    </unclosed_tag>''')  # Intentionally corrupted
            
            result = validator.validate_pptx_structure(Path(f.name))
        
        assert result.valid is False
        assert any("XML parse error" in error for error in result.errors)
        
        # Clean up
        Path(f.name).unlink()
    
    def test_missing_required_files(self):
        """Test handling of missing required PPTX files."""
        validator = PPTXValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zip_file:
                # Only add content types, missing other required files
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
            
            result = validator.validate_pptx_structure(Path(f.name))
        
        assert result.valid is False
        assert any("Missing required file" in error for error in result.errors)
        
        # Clean up
        Path(f.name).unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
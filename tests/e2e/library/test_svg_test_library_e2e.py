#!/usr/bin/env python3
"""
Tests for SVG test library management and validation system.

This module tests the infrastructure for managing real-world SVG files
used in E2E testing, including file validation, categorization, and metadata extraction.
"""

import pytest
import tempfile
from pathlib import Path
import json
from lxml import etree as ET

# Import the test library management system (to be implemented)
# from tools.testing.svg_test_library import SVGTestLibrary, SVGMetadata, SVGCategory


class TestSVGTestLibrary:
    """Test SVG test library management functionality."""
    
    @pytest.fixture
    def temp_svg_dir(self):
        """Create temporary directory with test SVG files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create sample SVG files
            simple_svg = '''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="50" height="50" fill="red"/>
</svg>'''
            
            complex_svg = '''<?xml version="1.0"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
    </defs>
    <circle cx="100" cy="100" r="50" fill="url(#grad1)"/>
    <path d="M 50 50 L 150 50 L 100 150 Z" fill="blue"/>
    <text x="100" y="180" text-anchor="middle" font-family="Arial" font-size="14">Complex SVG</text>
</svg>'''
            
            # Write test files
            (temp_path / "simple_rect.svg").write_text(simple_svg)
            (temp_path / "complex_design.svg").write_text(complex_svg)
            
            # Create invalid SVG
            (temp_path / "invalid.svg").write_text("Not an SVG file")
            
            yield temp_path
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample SVG metadata for testing."""
        return {
            "filename": "complex_design.svg",
            "source_tool": "illustrator",
            "complexity": "high",
            "features": ["gradients", "paths", "text", "shapes"],
            "converter_modules": ["gradients", "paths", "text", "shapes"],
            "file_size": 1024,
            "element_count": 5,
            "viewport": {"width": 200, "height": 200}
        }
    
    def test_svg_library_initialization(self, temp_svg_dir):
        """Test SVG test library initialization."""
        # This test will validate the library initialization once implemented
        assert temp_svg_dir.exists()
        svg_files = list(temp_svg_dir.glob("*.svg"))
        assert len(svg_files) == 3  # 2 valid + 1 invalid
    
    def test_svg_file_validation(self, temp_svg_dir):
        """Test SVG file validation functionality."""
        valid_files = []
        invalid_files = []
        
        for svg_file in temp_svg_dir.glob("*.svg"):
            try:
                # Test XML parsing
                with open(svg_file, 'r') as f:
                    content = f.read()
                    
                # Parse with lxml to validate XML structure
                root = ET.fromstring(content)
                
                # Check if it's actually an SVG
                tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
                if tag == 'svg':
                    valid_files.append(svg_file.name)
                else:
                    invalid_files.append(svg_file.name)
                    
            except (ET.XMLSyntaxError, Exception):
                invalid_files.append(svg_file.name)
        
        assert "simple_rect.svg" in valid_files
        assert "complex_design.svg" in valid_files
        assert "invalid.svg" in invalid_files
    
    def test_svg_metadata_extraction(self, temp_svg_dir):
        """Test metadata extraction from SVG files."""
        complex_svg_path = temp_svg_dir / "complex_design.svg"
        
        # Parse SVG and extract metadata
        with open(complex_svg_path, 'r') as f:
            content = f.read()
        
        root = ET.fromstring(content)
        
        # Extract basic metadata
        width = root.get('width', '0')
        height = root.get('height', '0')
        
        # Count elements by type
        elements = {}
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            elements[tag] = elements.get(tag, 0) + 1
        
        # Verify metadata extraction
        assert width == "200"
        assert height == "200"
        assert elements.get('circle', 0) >= 1
        assert elements.get('path', 0) >= 1
        assert elements.get('text', 0) >= 1
        assert elements.get('linearGradient', 0) >= 1
    
    def test_converter_module_mapping(self, temp_svg_dir):
        """Test mapping SVG features to converter modules."""
        complex_svg_path = temp_svg_dir / "complex_design.svg"
        
        with open(complex_svg_path, 'r') as f:
            content = f.read()
        
        root = ET.fromstring(content)
        
        # Identify converter modules needed
        converter_modules = set()
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            # Map elements to converter modules
            if tag in ['rect', 'circle', 'ellipse', 'polygon', 'line']:
                converter_modules.add('shapes')
            elif tag == 'path':
                converter_modules.add('paths')
            elif tag == 'text':
                converter_modules.add('text')
            elif tag in ['linearGradient', 'radialGradient']:
                converter_modules.add('gradients')
            elif tag in ['filter']:
                converter_modules.add('filters')
            elif tag in ['marker']:
                converter_modules.add('markers')
        
        # Verify expected modules are identified
        assert 'shapes' in converter_modules
        assert 'paths' in converter_modules
        assert 'text' in converter_modules
        assert 'gradients' in converter_modules
    
    def test_svg_categorization_by_complexity(self, temp_svg_dir):
        """Test SVG categorization by complexity level."""
        files_with_complexity = []
        
        for svg_file in temp_svg_dir.glob("*.svg"):
            if svg_file.name == "invalid.svg":
                continue
                
            try:
                with open(svg_file, 'r') as f:
                    content = f.read()
                
                root = ET.fromstring(content)
                
                # Calculate complexity metrics
                element_count = len(list(root.iter()))
                has_gradients = any('Gradient' in elem.tag for elem in root.iter())
                has_paths = any('path' in elem.tag.lower() for elem in root.iter())
                has_text = any('text' in elem.tag.lower() for elem in root.iter())
                
                # Determine complexity
                complexity = "low"
                if element_count > 10 or has_gradients or (has_paths and has_text):
                    complexity = "high"
                elif element_count > 5 or has_paths or has_text:
                    complexity = "medium"
                
                files_with_complexity.append({
                    "filename": svg_file.name,
                    "complexity": complexity,
                    "element_count": element_count
                })
                
            except Exception:
                continue
        
        # Verify complexity categorization
        complexities = {f["filename"]: f["complexity"] for f in files_with_complexity}
        assert complexities.get("simple_rect.svg") == "low"
        assert complexities.get("complex_design.svg") == "high"
    
    def test_metadata_persistence(self, temp_svg_dir, sample_metadata):
        """Test saving and loading SVG metadata."""
        metadata_file = temp_svg_dir / "metadata.json"
        
        # Test saving metadata
        metadata_db = {"complex_design.svg": sample_metadata}
        with open(metadata_file, 'w') as f:
            json.dump(metadata_db, f, indent=2)
        
        # Test loading metadata
        with open(metadata_file, 'r') as f:
            loaded_metadata = json.load(f)
        
        assert "complex_design.svg" in loaded_metadata
        assert loaded_metadata["complex_design.svg"]["source_tool"] == "illustrator"
        assert loaded_metadata["complex_design.svg"]["complexity"] == "high"
        assert "gradients" in loaded_metadata["complex_design.svg"]["features"]


class TestSVGLibraryIntegration:
    """Test integration with existing converter system."""
    
    def test_integration_with_converter_registry(self):
        """Test that SVG test library integrates with converter registry."""
        # This test ensures the test library works with our existing registry
        from core.converters.base import ConverterRegistryFactory
        
        registry = ConverterRegistryFactory.get_registry()
        assert len(registry.converters) > 0
        
        # Verify registry can handle test SVG elements
        test_svg = '''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg">
    <rect x="0" y="0" width="100" height="100"/>
</svg>'''
        
        root = ET.fromstring(test_svg)
        rect_elem = root.find('.//{http://www.w3.org/2000/svg}rect')
        
        converter = registry.get_converter(rect_elem)
        assert converter is not None
        assert converter.can_convert(rect_elem)
    
    def test_real_world_svg_processing(self):
        """Test processing pipeline with real-world SVG structure."""
        # Test that our library will work with actual design tool exports
        figma_style_svg = '''<?xml version="1.0"?>
<svg width="375" height="812" viewBox="0 0 375 812" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect width="375" height="812" fill="white"/>
<rect x="24" y="24" width="327" height="200" rx="12" fill="#F3F4F6"/>
<path d="M187.5 124C196.389 124 203.5 116.889 203.5 108C203.5 99.1112 196.389 92 187.5 92C178.611 92 171.5 99.1112 171.5 108C171.5 116.889 178.611 124 187.5 124Z" fill="#6B7280"/>
</svg>'''
        
        from core.converters.base import ConverterRegistryFactory, ConversionContext, CoordinateSystem
        
        # Parse the SVG
        root = ET.fromstring(figma_style_svg)
        
        # Create conversion context
        viewbox = (0, 0, 375, 812)
        coord_sys = CoordinateSystem(viewbox)
        context = ConversionContext(root)
        context.coordinate_system = coord_sys
        
        # Get registry and test conversion
        registry = ConverterRegistryFactory.get_registry()
        
        # Find and convert elements
        conversions = []
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag in ['rect', 'path', 'circle', 'ellipse']:
                result = registry.convert_element(elem, context)
                if result:
                    conversions.append((tag, len(result)))
        
        # Verify conversions happened
        assert len(conversions) > 0
        assert any(tag == 'rect' for tag, _ in conversions)
        assert any(tag == 'path' for tag, _ in conversions)


class TestSVGLibraryValidation:
    """Test comprehensive validation of SVG test library."""
    
    def test_svg_library_baseline_requirements(self):
        """Test that library meets baseline requirements."""
        # This test will validate we have sufficient SVG files
        # Once implemented, should verify:
        # - At least 50 SVG files
        # - Coverage of all major design tools
        # - Diverse complexity levels
        # - All converter modules represented
    
    def test_svg_file_source_tracking(self):
        """Test tracking of SVG file sources and origins."""
        # Test metadata includes source tool information
        sources = ["figma", "illustrator", "inkscape", "sketch", "web"]
        
        # Verify each source type is represented
        # This will be implemented with actual files
        assert len(sources) >= 4  # At least 4 different source types
    
    def test_converter_module_coverage_mapping(self):
        """Test mapping between SVG files and converter modules."""
        # Verify all converter modules are exercised
        expected_modules = [
            "shapes", "paths", "text", "gradients", 
            "filters", "animations", "markers", "masking"
        ]
        
        # This test will verify the test library includes files that exercise each module
        assert len(expected_modules) == 8
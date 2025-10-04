#!/usr/bin/env python3
"""
Visual regression tests using golden standard comparisons.

This module provides comprehensive visual validation by comparing SVG-to-PPTX
conversion results against pre-validated "golden" reference files.
"""

import pytest
import os
import tempfile
from pathlib import Path
from typing import List
from lxml import etree as ET
from zipfile import ZipFile

# Test data paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "golden_standards"

class GoldenTestResult:
    """Result of a golden standard test comparison."""
    
    def __init__(self, test_name: str, passed: bool, differences: List[str] = None):
        self.test_name = test_name
        self.passed = passed
        self.differences = differences or []
        
    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"{self.test_name}: {status}"


class PPTXValidator:
    """Validates PPTX files against golden standards."""
    
    def __init__(self):
        self.tolerance = 0.001  # Coordinate tolerance for floating point comparisons
    
    def compare_pptx_files(self, actual_path: Path, expected_path: Path) -> GoldenTestResult:
        """Compare two PPTX files for structural and content equivalence."""
        test_name = actual_path.stem
        differences = []
        
        try:
            # Extract and compare XML content
            actual_content = self._extract_pptx_content(actual_path)
            expected_content = self._extract_pptx_content(expected_path)
            
            # Compare slide content
            slide_diffs = self._compare_slides(actual_content, expected_content)
            if slide_diffs:
                differences.extend(slide_diffs)
            
            # Compare relationships and structure
            structure_diffs = self._compare_structure(actual_content, expected_content)
            if structure_diffs:
                differences.extend(structure_diffs)
            
        except Exception as e:
            differences.append(f"Comparison failed: {str(e)}")
        
        return GoldenTestResult(test_name, len(differences) == 0, differences)
    
    def _extract_pptx_content(self, pptx_path: Path) -> dict:
        """Extract relevant XML content from PPTX file."""
        content = {
            'slides': [],
            'rels': None,
            'presentation': None
        }
        
        with ZipFile(pptx_path, 'r') as zf:
            # Extract slide XML files
            for file_info in zf.filelist:
                if file_info.filename.startswith('ppt/slides/slide') and file_info.filename.endswith('.xml'):
                    content['slides'].append(zf.read(file_info.filename).decode('utf-8'))
                elif file_info.filename == 'ppt/presentation.xml':
                    content['presentation'] = zf.read(file_info.filename).decode('utf-8')
                elif file_info.filename == 'ppt/_rels/presentation.xml.rels':
                    content['rels'] = zf.read(file_info.filename).decode('utf-8')
        
        return content
    
    def _compare_slides(self, actual: dict, expected: dict) -> List[str]:
        """Compare slide content between actual and expected PPTX files."""
        differences = []
        
        if len(actual['slides']) != len(expected['slides']):
            differences.append(f"Slide count mismatch: {len(actual['slides'])} vs {len(expected['slides'])}")
            return differences
        
        for i, (actual_slide, expected_slide) in enumerate(zip(actual['slides'], expected['slides'])):
            slide_diffs = self._compare_slide_xml(actual_slide, expected_slide, i + 1)
            differences.extend(slide_diffs)
        
        return differences
    
    def _compare_slide_xml(self, actual_xml: str, expected_xml: str, slide_num: int) -> List[str]:
        """Compare individual slide XML content."""
        differences = []
        
        try:
            actual_root = ET.fromstring(actual_xml)
            expected_root = ET.fromstring(expected_xml)
            
            # Compare shape count
            actual_shapes = self._count_shapes(actual_root)
            expected_shapes = self._count_shapes(expected_root)
            
            if actual_shapes != expected_shapes:
                differences.append(f"Slide {slide_num}: Shape count mismatch ({actual_shapes} vs {expected_shapes})")
            
            # Compare coordinate values (with tolerance)
            coord_diffs = self._compare_coordinates(actual_root, expected_root, slide_num)
            differences.extend(coord_diffs)
            
            # Compare color values
            color_diffs = self._compare_colors(actual_root, expected_root, slide_num)
            differences.extend(color_diffs)
            
        except ET.ParseError as e:
            differences.append(f"Slide {slide_num}: XML parse error - {str(e)}")
        
        return differences
    
    def _count_shapes(self, root: ET.Element) -> int:
        """Count shapes in slide XML."""
        shape_count = 0
        for elem in root.iter():
            if elem.tag.endswith('}sp') or elem.tag.endswith('}grpSp'):
                shape_count += 1
        return shape_count
    
    def _compare_coordinates(self, actual: ET.Element, expected: ET.Element, slide_num: int) -> List[str]:
        """Compare coordinate values with tolerance."""
        differences = []
        
        # Extract coordinate attributes
        coord_attrs = ['x', 'y', 'cx', 'cy', 'w', 'h']
        
        for attr in coord_attrs:
            actual_coords = [elem.get(attr) for elem in actual.iter() if elem.get(attr)]
            expected_coords = [elem.get(attr) for elem in expected.iter() if elem.get(attr)]
            
            if len(actual_coords) != len(expected_coords):
                differences.append(f"Slide {slide_num}: {attr} coordinate count mismatch")
                continue
            
            for i, (actual_val, expected_val) in enumerate(zip(actual_coords, expected_coords)):
                try:
                    actual_float = float(actual_val)
                    expected_float = float(expected_val)
                    
                    if abs(actual_float - expected_float) > self.tolerance:
                        differences.append(
                            f"Slide {slide_num}: {attr}[{i}] coordinate mismatch "
                            f"({actual_float} vs {expected_float})"
                        )
                except (ValueError, TypeError):
                    if actual_val != expected_val:
                        differences.append(
                            f"Slide {slide_num}: {attr}[{i}] value mismatch "
                            f"('{actual_val}' vs '{expected_val}')"
                        )
        
        return differences
    
    def _compare_colors(self, actual: ET.Element, expected: ET.Element, slide_num: int) -> List[str]:
        """Compare color values in slide content."""
        differences = []
        
        # Extract color attributes (simplified - could be more comprehensive)
        color_attrs = ['val', 'color']
        
        for attr in color_attrs:
            actual_colors = [elem.get(attr) for elem in actual.iter() if elem.get(attr) and 'color' in elem.tag.lower()]
            expected_colors = [elem.get(attr) for elem in expected.iter() if elem.get(attr) and 'color' in elem.tag.lower()]
            
            if actual_colors != expected_colors:
                differences.append(f"Slide {slide_num}: Color values mismatch")
        
        return differences
    
    def _compare_structure(self, actual: dict, expected: dict) -> List[str]:
        """Compare PPTX structural elements."""
        differences = []
        
        # Compare presentation structure
        if actual.get('presentation') != expected.get('presentation'):
            differences.append("Presentation structure mismatch")
        
        return differences


@pytest.fixture
def pptx_validator():
    """Fixture providing PPTX validator instance."""
    return PPTXValidator()


@pytest.fixture
def golden_test_data():
    """Fixture providing golden test data paths."""
    if not GOLDEN_DIR.exists():
        pytest.skip(f"Golden test data directory not found: {GOLDEN_DIR}")
    
    test_cases = []
    for svg_file in GOLDEN_DIR.glob("*.svg"):
        pptx_file = svg_file.with_suffix(".pptx")
        if pptx_file.exists():
            test_cases.append((svg_file, pptx_file))
    
    return test_cases


class TestGoldenStandards:
    """Golden standard visual regression tests."""
    
    def test_basic_shapes_golden(self, pptx_validator, golden_test_data):
        """Test basic shapes against golden standards."""
        from core.svg2pptx import convert_svg_to_pptx
        
        for svg_file, expected_pptx in golden_test_data:
            if "basic_shapes" not in svg_file.name:
                continue
            
            # Convert SVG to PPTX
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
                try:
                    convert_svg_to_pptx(str(svg_file), tmp.name)
                    
                    # Compare against golden standard
                    result = pptx_validator.compare_pptx_files(Path(tmp.name), expected_pptx)
                    
                    # Assert no differences
                    if not result.passed:
                        pytest.fail(f"Golden test failed for {svg_file.name}: {result.differences}")
                
                finally:
                    os.unlink(tmp.name)
    
    def test_complex_paths_golden(self, pptx_validator, golden_test_data):
        """Test complex paths against golden standards."""
        from core.svg2pptx import convert_svg_to_pptx
        
        for svg_file, expected_pptx in golden_test_data:
            if "complex_paths" not in svg_file.name:
                continue
            
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
                try:
                    convert_svg_to_pptx(str(svg_file), tmp.name)
                    result = pptx_validator.compare_pptx_files(Path(tmp.name), expected_pptx)
                    
                    if not result.passed:
                        pytest.fail(f"Golden test failed for {svg_file.name}: {result.differences}")
                
                finally:
                    os.unlink(tmp.name)
    
    def test_text_rendering_golden(self, pptx_validator, golden_test_data):
        """Test text rendering against golden standards."""
        from core.svg2pptx import convert_svg_to_pptx
        
        for svg_file, expected_pptx in golden_test_data:
            if "text_rendering" not in svg_file.name:
                continue
            
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
                try:
                    convert_svg_to_pptx(str(svg_file), tmp.name)
                    result = pptx_validator.compare_pptx_files(Path(tmp.name), expected_pptx)
                    
                    if not result.passed:
                        pytest.fail(f"Golden test failed for {svg_file.name}: {result.differences}")
                
                finally:
                    os.unlink(tmp.name)
    
    def test_transforms_golden(self, pptx_validator, golden_test_data):
        """Test transforms against golden standards."""
        from core.svg2pptx import convert_svg_to_pptx
        
        for svg_file, expected_pptx in golden_test_data:
            if "transforms" not in svg_file.name:
                continue
            
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
                try:
                    convert_svg_to_pptx(str(svg_file), tmp.name)
                    result = pptx_validator.compare_pptx_files(Path(tmp.name), expected_pptx)
                    
                    if not result.passed:
                        pytest.fail(f"Golden test failed for {svg_file.name}: {result.differences}")
                
                finally:
                    os.unlink(tmp.name)
    
    @pytest.mark.slow
    def test_comprehensive_golden_suite(self, pptx_validator, golden_test_data):
        """Run comprehensive golden test suite."""
        from core.svg2pptx import convert_svg_to_pptx
        
        results = []
        
        for svg_file, expected_pptx in golden_test_data:
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
                try:
                    convert_svg_to_pptx(str(svg_file), tmp.name)
                    result = pptx_validator.compare_pptx_files(Path(tmp.name), expected_pptx)
                    results.append(result)
                    
                except Exception as e:
                    results.append(GoldenTestResult(svg_file.name, False, [f"Conversion failed: {str(e)}"]))
                
                finally:
                    os.unlink(tmp.name)
        
        # Report summary
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        
        print(f"\nGolden Test Suite Results: {passed}/{total} passed")
        
        for result in results:
            if not result.passed:
                print(f"FAILED: {result}")
                for diff in result.differences:
                    print(f"  - {diff}")
        
        # Fail if any tests failed
        failed_tests = [r for r in results if not r.passed]
        if failed_tests:
            pytest.fail(f"{len(failed_tests)} golden tests failed")


if __name__ == "__main__":
    # CLI for running golden tests independently
    import sys
    
    validator = PPTXValidator()
    
    if len(sys.argv) != 3:
        print("Usage: python test_golden_standards.py <actual.pptx> <expected.pptx>")
        sys.exit(1)
    
    actual_path = Path(sys.argv[1])
    expected_path = Path(sys.argv[2])
    
    result = validator.compare_pptx_files(actual_path, expected_path)
    print(result)
    
    if not result.passed:
        for diff in result.differences:
            print(f"  - {diff}")
        sys.exit(1)
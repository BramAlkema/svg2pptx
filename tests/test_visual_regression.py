#!/usr/bin/env python3
"""
Tests for visual regression testing system.

This module tests the visual regression testing framework including
LibreOffice integration, image comparison algorithms, and test execution.
"""

import pytest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import subprocess
import shutil

from tools.visual_regression_tester import (
    VisualRegressionTester,
    LibreOfficeRenderer,
    ImageComparator,
    ComparisonMethod,
    VisualComparisonResult,
    RegressionTestResult,
    PILLOW_AVAILABLE
)


class TestLibreOfficeRenderer:
    """Test LibreOffice rendering functionality."""
    
    def test_renderer_initialization(self):
        """Test LibreOffice renderer initialization."""
        renderer = LibreOfficeRenderer()
        assert renderer.libreoffice_path is not None
        assert len(renderer.libreoffice_path) > 0
    
    def test_find_libreoffice_paths(self):
        """Test LibreOffice path detection."""
        renderer = LibreOfficeRenderer()
        
        # Test that we can find a path
        found_path = renderer._find_libreoffice()
        assert found_path is not None
        
        # Test with custom path that doesn't exist - should raise RuntimeError
        with pytest.raises(RuntimeError, match="LibreOffice not found"):
            LibreOfficeRenderer("/nonexistent/libreoffice")
        
        # Test with working path (the one we found)
        working_renderer = LibreOfficeRenderer(found_path)
        assert working_renderer.libreoffice_path == found_path
    
    def test_libreoffice_verification(self):
        """Test LibreOffice verification process."""
        renderer = LibreOfficeRenderer()
        
        # Should not raise exception if LibreOffice is working
        try:
            renderer._verify_libreoffice()
        except RuntimeError as e:
            # If verification fails, it should be due to LibreOffice issues
            assert "LibreOffice" in str(e)
    
    def test_convert_pptx_missing_file(self):
        """Test conversion with missing PPTX file."""
        renderer = LibreOfficeRenderer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            missing_pptx = temp_path / "missing.pptx"
            output_dir = temp_path / "output"
            
            with pytest.raises(FileNotFoundError):
                renderer.convert_pptx_to_images(missing_pptx, output_dir)
    
    def test_convert_pptx_to_images_mock(self):
        """Test PPTX to image conversion with mocked LibreOffice."""
        renderer = LibreOfficeRenderer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock PPTX file
            pptx_file = temp_path / "test.pptx"
            with zipfile.ZipFile(pptx_file, 'w') as zip_file:
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
            
            output_dir = temp_path / "output"
            
            # Mock subprocess to simulate successful conversion
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stderr="", stdout="")
                
                # Create expected output files
                output_dir.mkdir(parents=True, exist_ok=True)
                expected_image = output_dir / "test.png"
                expected_image.touch()  # Create empty file
                
                images = renderer.convert_pptx_to_images(pptx_file, output_dir)
                
                assert len(images) >= 1
                assert expected_image in images
                
                # Verify LibreOffice was called correctly
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert renderer.libreoffice_path in call_args
                assert '--headless' in call_args
                assert '--convert-to' in call_args


class TestImageComparator:
    """Test image comparison functionality."""
    
    def test_comparator_initialization(self):
        """Test image comparator initialization."""
        comparator = ImageComparator()
        
        if PILLOW_AVAILABLE:
            assert not comparator.mock_mode
        else:
            assert comparator.mock_mode
    
    def test_compare_images_mock_mode(self):
        """Test image comparison in mock mode."""
        # Force mock mode for testing
        comparator = ImageComparator()
        comparator.mock_mode = True
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create dummy image files
            ref_image = temp_path / "reference.png"
            out_image = temp_path / "output.png"
            ref_image.touch()
            out_image.touch()
            
            result = comparator.compare_images(ref_image, out_image)
            
            assert isinstance(result, VisualComparisonResult)
            assert result.similarity_score == 0.95  # Mock value
            assert result.metadata["mock"] is True
    
    def test_compare_images_missing_files(self):
        """Test image comparison with missing files."""
        comparator = ImageComparator()
        
        # Only test if not in mock mode
        if not getattr(comparator, 'mock_mode', False):
            missing_ref = Path("/nonexistent/reference.png")
            missing_out = Path("/nonexistent/output.png")
            
            with pytest.raises(FileNotFoundError):
                comparator.compare_images(missing_ref, missing_out)
    
    @pytest.mark.skipif(not PILLOW_AVAILABLE, reason="Pillow not available")
    def test_comparison_methods(self):
        """Test different comparison methods with Pillow available."""
        comparator = ImageComparator()
        
        # Test that the comparison methods exist
        expected_methods = [
            '_pixel_perfect_comparison',
            '_structural_similarity_comparison', 
            '_perceptual_hash_comparison',
            '_histogram_comparison',
            '_edge_detection_comparison'
        ]
        
        for method_name in expected_methods:
            assert hasattr(comparator, method_name), f"Method {method_name} not found"
            assert callable(getattr(comparator, method_name)), f"Method {method_name} is not callable"
    
    def test_mock_comparison_result(self):
        """Test mock comparison result generation."""
        comparator = ImageComparator()
        
        for method in ComparisonMethod:
            result = comparator._mock_comparison_result(method)
            
            assert isinstance(result, VisualComparisonResult)
            assert 0.0 <= result.similarity_score <= 1.0
            assert result.comparison_method == method.value
            assert result.metadata["mock"] is True


class TestVisualRegressionTester:
    """Test main visual regression testing functionality."""
    
    def test_tester_initialization(self):
        """Test visual regression tester initialization."""
        tester = VisualRegressionTester()
        
        assert isinstance(tester.renderer, LibreOfficeRenderer)
        assert isinstance(tester.comparator, ImageComparator)
        assert isinstance(tester.temp_dirs, list)
    
    def test_run_regression_test_mock(self):
        """Test regression test execution with mocked components."""
        tester = VisualRegressionTester()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock PPTX files
            ref_pptx = temp_path / "reference.pptx"
            out_pptx = temp_path / "output.pptx"
            
            # Create minimal PPTX structure
            for pptx_file in [ref_pptx, out_pptx]:
                with zipfile.ZipFile(pptx_file, 'w') as zip_file:
                    zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
            
            # Mock the renderer and comparator
            with patch.object(tester.renderer, 'convert_pptx_to_images') as mock_convert:
                with patch.object(tester.comparator, 'compare_images') as mock_compare:
                    # Setup mocks
                    mock_image1 = temp_path / "ref_slide1.png"
                    mock_image2 = temp_path / "out_slide1.png"
                    mock_image1.touch()
                    mock_image2.touch()
                    
                    mock_convert.side_effect = [
                        [mock_image1],  # Reference images
                        [mock_image2]   # Output images
                    ]
                    
                    mock_compare.return_value = VisualComparisonResult(
                        similarity_score=0.92,
                        pixel_difference_count=800,
                        total_pixels=10000,
                        comparison_method="structural_similarity"
                    )
                    
                    # Run test
                    result = tester.run_regression_test(
                        ref_pptx, out_pptx, "test_mock", similarity_threshold=0.90
                    )
                    
                    assert isinstance(result, RegressionTestResult)
                    assert result.test_name == "test_mock"
                    assert result.passed is True  # 0.92 >= 0.90
                    assert result.similarity_threshold == 0.90
                    assert result.actual_similarity == 0.92
                    assert result.execution_time > 0
    
    def test_run_regression_test_failure(self):
        """Test regression test with conversion failure."""
        tester = VisualRegressionTester()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock PPTX files
            ref_pptx = temp_path / "reference.pptx"
            out_pptx = temp_path / "output.pptx"
            ref_pptx.touch()
            out_pptx.touch()
            
            # Mock renderer to raise exception
            with patch.object(tester.renderer, 'convert_pptx_to_images') as mock_convert:
                mock_convert.side_effect = RuntimeError("Conversion failed")
                
                result = tester.run_regression_test(ref_pptx, out_pptx, "test_failure")
                
                assert isinstance(result, RegressionTestResult)
                assert result.passed is False
                assert result.error_message is not None
                assert "Conversion failed" in result.error_message
    
    def test_run_test_suite(self):
        """Test running a suite of visual regression tests."""
        tester = VisualRegressionTester()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            ref_pptx = temp_path / "reference.pptx"
            out_pptx = temp_path / "output.pptx"
            
            with zipfile.ZipFile(ref_pptx, 'w') as zip_file:
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
            
            with zipfile.ZipFile(out_pptx, 'w') as zip_file:
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
            
            # Test configuration
            test_configs = [
                {
                    "name": "suite_test_1",
                    "reference": str(ref_pptx),
                    "output": str(out_pptx),
                    "similarity_threshold": 0.95,
                    "comparison_methods": ["structural_similarity"]
                }
            ]
            
            output_dir = temp_path / "results"
            
            # Mock the individual test execution
            with patch.object(tester, 'run_regression_test') as mock_run_test:
                mock_result = RegressionTestResult(
                    test_name="suite_test_1",
                    passed=True,
                    similarity_threshold=0.95,
                    actual_similarity=0.98,
                    comparison_results={},
                    execution_time=1.5
                )
                mock_run_test.return_value = mock_result
                
                results = tester.run_test_suite(test_configs, output_dir)
                
                assert len(results) == 1
                assert "suite_test_1" in results
                assert results["suite_test_1"].passed is True
                
                # Verify files were created
                assert output_dir.exists()
                assert (output_dir / "suite_test_1_result.json").exists()
                assert (output_dir / "visual_regression_summary.json").exists()
    
    def test_cleanup(self):
        """Test cleanup functionality."""
        tester = VisualRegressionTester()
        
        # Add some mock temp directories
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_temp = temp_path / "mock_temp"
            mock_temp.mkdir()
            
            tester.temp_dirs.append(mock_temp)
            
            # Cleanup should handle this gracefully
            tester.cleanup()
            
            assert len(tester.temp_dirs) == 0


class TestDataStructures:
    """Test data structures and serialization."""
    
    def test_visual_comparison_result_serialization(self):
        """Test VisualComparisonResult serialization."""
        result = VisualComparisonResult(
            similarity_score=0.85,
            pixel_difference_count=1500,
            total_pixels=10000,
            comparison_method="pixel_perfect",
            differences_image_path="/path/to/diff.png",
            metadata={"test": "data"}
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["similarity_score"] == 0.85
        assert result_dict["pixel_difference_count"] == 1500
        assert result_dict["total_pixels"] == 10000
        assert result_dict["comparison_method"] == "pixel_perfect"
        assert result_dict["differences_image_path"] == "/path/to/diff.png"
        assert result_dict["metadata"]["test"] == "data"
    
    def test_regression_test_result_serialization(self):
        """Test RegressionTestResult serialization."""
        comparison_results = {
            "method1": VisualComparisonResult(
                similarity_score=0.90,
                pixel_difference_count=100,
                total_pixels=1000,
                comparison_method="method1"
            )
        }
        
        result = RegressionTestResult(
            test_name="serialization_test",
            passed=True,
            similarity_threshold=0.85,
            actual_similarity=0.90,
            comparison_results=comparison_results,
            execution_time=2.5,
            error_message=None
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["test_name"] == "serialization_test"
        assert result_dict["passed"] is True
        assert result_dict["similarity_threshold"] == 0.85
        assert result_dict["actual_similarity"] == 0.90
        assert result_dict["execution_time"] == 2.5
        assert result_dict["error_message"] is None
        
        # Check nested comparison results
        assert "method1" in result_dict["comparison_results"]
        assert result_dict["comparison_results"]["method1"]["similarity_score"] == 0.90
    
    def test_comparison_methods_enum(self):
        """Test ComparisonMethod enum values."""
        methods = [
            ComparisonMethod.PIXEL_PERFECT,
            ComparisonMethod.STRUCTURAL_SIMILARITY,
            ComparisonMethod.PERCEPTUAL_HASH,
            ComparisonMethod.HISTOGRAM_COMPARISON,
            ComparisonMethod.EDGE_DETECTION,
            ComparisonMethod.TEMPLATE_MATCHING
        ]
        
        for method in methods:
            assert isinstance(method.value, str)
            assert len(method.value) > 0


class TestIntegration:
    """Integration tests for visual regression testing."""
    
    def test_end_to_end_mock_workflow(self):
        """Test end-to-end workflow with mocked components."""
        tester = VisualRegressionTester()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test PPTX files
            ref_pptx = temp_path / "reference.pptx"
            out_pptx = temp_path / "output.pptx"
            
            # Create basic PPTX structure
            for pptx_file in [ref_pptx, out_pptx]:
                with zipfile.ZipFile(pptx_file, 'w') as zip_file:
                    zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
                    zip_file.writestr('_rels/.rels', '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>''')
                    zip_file.writestr('ppt/presentation.xml', '''<?xml version="1.0"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:sldIdLst></p:sldIdLst>
</p:presentation>''')
            
            # Mock the entire pipeline
            with patch.object(tester.renderer, 'convert_pptx_to_images') as mock_convert:
                with patch.object(tester.comparator, 'compare_images') as mock_compare:
                    # Setup conversion results
                    mock_images = [temp_path / f"slide_{i}.png" for i in range(2)]
                    for img in mock_images:
                        img.touch()
                    
                    mock_convert.side_effect = [mock_images, mock_images]
                    
                    # Setup comparison results
                    mock_compare.return_value = VisualComparisonResult(
                        similarity_score=0.88,
                        pixel_difference_count=1200,
                        total_pixels=10000,
                        comparison_method="structural_similarity",
                        metadata={"slides_compared": 2}
                    )
                    
                    # Run comprehensive test
                    methods = [ComparisonMethod.STRUCTURAL_SIMILARITY, ComparisonMethod.PIXEL_PERFECT]
                    result = tester.run_regression_test(
                        ref_pptx, out_pptx, "integration_test",
                        similarity_threshold=0.85, comparison_methods=methods
                    )
                    
                    # Verify results
                    assert result.passed is True
                    assert len(result.comparison_results) == len(methods)
                    assert "structural_similarity" in result.comparison_results
                    assert "pixel_perfect" in result.comparison_results
                    assert result.execution_time > 0
                    
                    # Verify conversion was called correctly
                    assert mock_convert.call_count == 2  # Once for ref, once for output
                    
                    # Verify comparison was called for each method and slide
                    expected_calls = len(methods) * len(mock_images)  # 2 methods * 2 slides
                    assert mock_compare.call_count == expected_calls


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
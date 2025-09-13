#!/usr/bin/env python3
"""
Tests for workflow validation system.

This module tests the complete SVG→DrawML→PPTX pipeline validation
including all stages, error handling, and batch processing.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from tools.workflow_validator import (
    WorkflowValidator,
    SVGParser,
    DrawMLValidator,
    PipelineStage,
    ValidationSeverity,
    ValidationIssue,
    StageResult,
    WorkflowValidationResult,
    batch_validate_workflows
)


class TestSVGParser:
    """Test SVG parsing functionality."""
    
    def test_svg_parser_initialization(self):
        """Test SVG parser initialization."""
        parser = SVGParser()
        assert len(parser.supported_elements) > 0
        assert 'rect' in parser.supported_elements
        assert 'circle' in parser.supported_elements
        assert 'path' in parser.supported_elements
    
    def test_parse_valid_svg(self):
        """Test parsing valid SVG content."""
        parser = SVGParser()
        
        with tempfile.NamedTemporaryFile(suffix='.svg', mode='w', delete=False) as f:
            f.write('''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="red"/>
    <circle cx="50" cy="50" r="25" fill="blue"/>
    <text x="20" y="80">Test</text>
</svg>''')
            f.flush()
            
            success, metadata, issues = parser.parse_svg(Path(f.name))
        
        assert success is True
        assert metadata['viewport']['width'] == 100.0
        assert metadata['viewport']['height'] == 100.0
        assert metadata['elements']['rect'] == 1
        assert metadata['elements']['circle'] == 1
        assert metadata['elements']['text'] == 1
        assert 'rect' in metadata['features_used']
        assert 'circle' in metadata['features_used']
        assert 'text' in metadata['features_used']
        assert metadata['complexity_score'] > 0
        
        # Clean up
        Path(f.name).unlink()
    
    def test_parse_svg_with_complex_features(self):
        """Test parsing SVG with complex features."""
        parser = SVGParser()
        
        with tempfile.NamedTemporaryFile(suffix='.svg', mode='w', delete=False) as f:
            f.write('''<?xml version="1.0"?>
<svg width="200px" height="150pt" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad1">
            <stop offset="0%" stop-color="red"/>
            <stop offset="100%" stop-color="blue"/>
        </linearGradient>
        <filter id="blur">
            <feGaussianBlur stdDeviation="2"/>
        </filter>
    </defs>
    <path d="M10,10 L50,50 Q100,25 150,50" fill="url(#grad1)" filter="url(#blur)"/>
</svg>''')
            f.flush()
            
            success, metadata, issues = parser.parse_svg(Path(f.name))
        
        assert success is True
        assert metadata['viewport']['width'] == 200.0
        assert metadata['viewport']['height'] == 150.0
        assert 'path' in metadata['elements']
        assert 'linearGradient' in metadata['elements']
        assert 'filter' in metadata['elements']
        assert 'complex_paths' in metadata['features_used']
        assert 'gradients' in metadata['features_used']
        assert 'filters' in metadata['features_used']
        assert metadata['complexity_score'] > 3.0  # Complex elements should increase score
        
        # Clean up
        Path(f.name).unlink()
    
    def test_parse_svg_with_unsupported_elements(self):
        """Test parsing SVG with unsupported elements."""
        parser = SVGParser()
        
        with tempfile.NamedTemporaryFile(suffix='.svg', mode='w', delete=False) as f:
            f.write('''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80"/>
    <foreignObject width="100" height="50">
        <div xmlns="http://www.w3.org/1999/xhtml">HTML content</div>
    </foreignObject>
    <customElement attr="value"/>
</svg>''')
            f.flush()
            
            success, metadata, issues = parser.parse_svg(Path(f.name))
        
        assert success is True
        assert len(issues) >= 2  # Should have warnings for unsupported elements
        warning_issues = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        assert len(warning_issues) >= 2
        assert any('foreignObject' in issue.message for issue in warning_issues)
        assert any('customElement' in issue.message for issue in warning_issues)
        
        # Clean up
        Path(f.name).unlink()
    
    def test_parse_invalid_svg(self):
        """Test parsing invalid SVG content."""
        parser = SVGParser()
        
        with tempfile.NamedTemporaryFile(suffix='.svg', mode='w', delete=False) as f:
            f.write('''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80"
    <!-- Missing closing tag and quote -->
</svg>''')
            f.flush()
            
            success, metadata, issues = parser.parse_svg(Path(f.name))
        
        assert success is False
        assert len(issues) > 0
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        assert len(critical_issues) > 0
        assert any('XML parsing error' in issue.message for issue in critical_issues)
        
        # Clean up
        Path(f.name).unlink()
    
    def test_parse_nonexistent_svg(self):
        """Test parsing nonexistent SVG file."""
        parser = SVGParser()
        
        success, metadata, issues = parser.parse_svg(Path("/nonexistent/file.svg"))
        
        assert success is False
        assert len(issues) > 0
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        assert len(critical_issues) > 0
        assert any('file not found' in issue.message.lower() for issue in critical_issues)


class TestDrawMLValidator:
    """Test DrawML validation functionality."""
    
    def test_drawml_validator_initialization(self):
        """Test DrawML validator initialization."""
        validator = DrawMLValidator()
        assert len(validator.required_namespaces) > 0
        assert 'http://schemas.openxmlformats.org/drawingml/2006/main' in validator.required_namespaces
    
    def test_validate_valid_drawml(self):
        """Test validating valid DrawML content."""
        validator = DrawMLValidator()
        
        drawml_content = '''<?xml version="1.0"?>
<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <a:graphicData>
        <a:sp>
            <a:spPr>
                <a:xfrm>
                    <a:off x="100" y="100"/>
                    <a:ext cx="200" cy="200"/>
                </a:xfrm>
                <a:prstGeom prst="rect"/>
                <a:solidFill>
                    <a:srgbClr val="FF0000"/>
                </a:solidFill>
            </a:spPr>
            <a:txBody>
                <a:bodyPr/>
                <a:p>
                    <a:r>
                        <a:t>Text content</a:t>
                    </a:r>
                </a:p>
            </a:txBody>
        </a:sp>
    </a:graphicData>
</a:graphic>'''
        
        success, metrics, issues = validator.validate_drawml(drawml_content)
        
        assert success is True
        assert metrics['element_count'] > 5
        assert metrics['namespace_count'] >= 1
        assert metrics['shape_count'] >= 1
        assert metrics['text_elements'] >= 1
        assert len(issues) == 0  # No issues expected for valid content
    
    def test_validate_minimal_drawml(self):
        """Test validating minimal DrawML content."""
        validator = DrawMLValidator()
        
        minimal_content = '''<?xml version="1.0"?>
<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <a:graphicData/>
</a:graphic>'''
        
        success, metrics, issues = validator.validate_drawml(minimal_content)
        
        assert success is False  # Too minimal
        assert len(issues) > 0
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert len(error_issues) > 0
        assert any('too minimal' in issue.message.lower() for issue in error_issues)
    
    def test_validate_invalid_drawml(self):
        """Test validating invalid DrawML content."""
        validator = DrawMLValidator()
        
        invalid_content = '''<?xml version="1.0"?>
<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <a:graphicData>
        <unclosed_tag>
    </a:graphicData>
</a:graphic>'''
        
        success, metrics, issues = validator.validate_drawml(invalid_content)
        
        assert success is False
        assert len(issues) > 0
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        assert len(critical_issues) > 0
    
    def test_validate_empty_drawml(self):
        """Test validating empty DrawML content."""
        validator = DrawMLValidator()
        
        success, metrics, issues = validator.validate_drawml("")
        
        assert success is False
        assert len(issues) > 0
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        assert len(critical_issues) > 0


class TestWorkflowValidator:
    """Test main workflow validator functionality."""
    
    def test_workflow_validator_initialization(self):
        """Test workflow validator initialization."""
        validator = WorkflowValidator()
        assert validator.accuracy_threshold == 0.85
        assert validator.visual_threshold == 0.80
        assert validator.max_duration == 300.0
        assert isinstance(validator.svg_parser, SVGParser)
        assert isinstance(validator.drawml_validator, DrawMLValidator)
    
    def test_workflow_validator_custom_thresholds(self):
        """Test workflow validator with custom thresholds."""
        validator = WorkflowValidator(
            accuracy_threshold=0.90,
            visual_threshold=0.85,
            max_duration=120.0
        )
        assert validator.accuracy_threshold == 0.90
        assert validator.visual_threshold == 0.85
        assert validator.max_duration == 120.0
    
    def test_validate_workflow_with_valid_svg(self):
        """Test complete workflow validation with valid SVG."""
        validator = WorkflowValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.svg', mode='w', delete=False) as f:
            f.write('''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
</svg>''')
            f.flush()
            
            # Mock visual tester to avoid LibreOffice dependency
            with patch.object(validator.visual_tester, 'run_regression_test') as mock_visual:
                mock_visual.return_value = Mock(
                    passed=True,
                    actual_similarity=0.95,
                    execution_time=1.0,
                    error_message=None
                )
                
                result = validator.validate_workflow(Path(f.name))
        
        assert isinstance(result, WorkflowValidationResult)
        assert result.success is True
        assert result.overall_accuracy > 0.8
        assert len(result.stage_results) == 7  # All 7 stages
        assert result.total_duration > 0
        
        # Check that all stages are present
        expected_stages = list(PipelineStage)
        for stage in expected_stages:
            assert stage in result.stage_results
        
        # Check summary
        assert 'overall_accuracy' in result.summary
        assert 'successful_stages' in result.summary
        assert 'recommendation' in result.summary
        
        # Clean up
        Path(f.name).unlink()
    
    def test_validate_workflow_with_invalid_svg(self):
        """Test workflow validation with invalid SVG."""
        validator = WorkflowValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.svg', mode='w', delete=False) as f:
            f.write('''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80"
    <!-- Invalid XML -->
</svg>''')
            f.flush()
            
            result = validator.validate_workflow(Path(f.name))
        
        assert isinstance(result, WorkflowValidationResult)
        assert result.success is False
        assert result.overall_accuracy < 0.8  # Adjusted expectation
        
        # Should have critical issues in SVG parsing stage
        svg_parsing_result = result.stage_results.get(PipelineStage.SVG_PARSING)
        assert svg_parsing_result is not None
        assert not svg_parsing_result.success
        
        critical_issues = [i for i in svg_parsing_result.issues if i.severity == ValidationSeverity.CRITICAL]
        assert len(critical_issues) > 0
        
        # Workflow should be short-circuited due to critical parsing errors
        # So we should have fewer than all 7 stages
        assert len(result.stage_results) <= 2  # Only input and parsing stages
        
        # Clean up
        Path(f.name).unlink()
    
    def test_validate_workflow_with_nonexistent_file(self):
        """Test workflow validation with nonexistent file."""
        validator = WorkflowValidator()
        
        result = validator.validate_workflow(Path("/nonexistent/file.svg"))
        
        assert isinstance(result, WorkflowValidationResult)
        assert result.success is False
        assert result.overall_accuracy == 0.0
        
        # Should fail at SVG input stage
        svg_input_result = result.stage_results.get(PipelineStage.SVG_INPUT)
        assert svg_input_result is not None
        assert not svg_input_result.success
    
    def test_validate_workflow_with_reference_pptx(self):
        """Test workflow validation with reference PPTX for visual comparison."""
        validator = WorkflowValidator()
        
        # Create test SVG
        with tempfile.NamedTemporaryFile(suffix='.svg', mode='w', delete=False) as svg_file:
            svg_file.write('''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="50" r="40" fill="green"/>
</svg>''')
            svg_file.flush()
            svg_path = Path(svg_file.name)
        
        # Create mock reference PPTX
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as ref_file:
            import zipfile
            with zipfile.ZipFile(ref_file, 'w') as zip_file:
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>''')
            ref_path = Path(ref_file.name)
        
        # Mock visual tester
        with patch.object(validator.visual_tester, 'run_regression_test') as mock_visual:
            mock_visual.return_value = Mock(
                passed=True,
                actual_similarity=0.88,
                execution_time=2.5,
                error_message=None
            )
            
            result = validator.validate_workflow(svg_path, ref_path)
        
        assert isinstance(result, WorkflowValidationResult)
        
        # Visual validation should have been attempted
        visual_result = result.stage_results.get(PipelineStage.VISUAL_VALIDATION)
        assert visual_result is not None
        assert 'visual_similarity' in visual_result.metrics
        assert visual_result.metrics['visual_similarity'] == 0.88
        
        # Clean up
        svg_path.unlink()
        ref_path.unlink()


class TestDataStructures:
    """Test workflow validation data structures."""
    
    def test_validation_issue_serialization(self):
        """Test ValidationIssue serialization."""
        issue = ValidationIssue(
            PipelineStage.SVG_PARSING,
            ValidationSeverity.WARNING,
            "Test warning message",
            {"detail": "test detail"}
        )
        
        issue_dict = issue.to_dict()
        
        assert issue_dict['stage'] == PipelineStage.SVG_PARSING
        assert issue_dict['severity'] == ValidationSeverity.WARNING
        assert issue_dict['message'] == "Test warning message"
        assert issue_dict['details']['detail'] == "test detail"
    
    def test_stage_result_serialization(self):
        """Test StageResult serialization."""
        issues = [
            ValidationIssue(
                PipelineStage.SVG_INPUT,
                ValidationSeverity.INFO,
                "Info message"
            )
        ]
        
        result = StageResult(
            PipelineStage.SVG_INPUT,
            True,
            1.5,
            issues,
            {"metric": "value"},
            {"artifact": "path"}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['stage'] == PipelineStage.SVG_INPUT
        assert result_dict['success'] is True
        assert result_dict['duration'] == 1.5
        assert len(result_dict['issues']) == 1
        assert result_dict['metrics']['metric'] == "value"
        assert result_dict['artifacts']['artifact'] == "path"
    
    def test_workflow_validation_result_serialization(self):
        """Test WorkflowValidationResult serialization."""
        stage_results = {
            PipelineStage.SVG_INPUT: StageResult(
                PipelineStage.SVG_INPUT,
                True,
                0.1,
                [],
                {}
            )
        }
        
        result = WorkflowValidationResult(
            "test_workflow_123",
            "test.svg",
            True,
            2.5,
            stage_results,
            0.95,
            {"test": "summary"}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['workflow_id'] == "test_workflow_123"
        assert result_dict['input_file'] == "test.svg"
        assert result_dict['success'] is True
        assert result_dict['total_duration'] == 2.5
        assert result_dict['overall_accuracy'] == 0.95
        assert 'svg_input' in result_dict['stage_results']
        assert result_dict['summary']['test'] == "summary"


class TestBatchValidation:
    """Test batch workflow validation functionality."""
    
    def test_batch_validate_workflows_empty_list(self):
        """Test batch validation with empty SVG list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            results = batch_validate_workflows([], output_dir=temp_path / "results")
            
            assert len(results) == 0
            
            # Check summary file was created
            summary_file = temp_path / "results" / "batch_workflow_summary.json"
            assert summary_file.exists()
            
            with open(summary_file) as f:
                summary = json.load(f)
            
            assert summary['total_workflows'] == 0
            assert summary['successful_validations'] == 0
            assert summary['average_accuracy'] == 0.0
    
    def test_batch_validate_workflows_single_file(self):
        """Test batch validation with single SVG file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test SVG
            svg_file = temp_path / "test.svg"
            with open(svg_file, 'w') as f:
                f.write('''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="0" y="0" width="100" height="100" fill="red"/>
</svg>''')
            
            results = batch_validate_workflows([svg_file], output_dir=temp_path / "results")
            
            assert len(results) == 1
            assert "test.svg" in results
            
            result = results["test.svg"]
            assert isinstance(result, WorkflowValidationResult)
            
            # Check individual result file was created
            result_file = temp_path / "results" / "test_workflow_result.json"
            assert result_file.exists()
            
            # Check summary file
            summary_file = temp_path / "results" / "batch_workflow_summary.json"
            assert summary_file.exists()
            
            with open(summary_file) as f:
                summary = json.load(f)
            
            assert summary['total_workflows'] == 1
            assert summary['successful_validations'] >= 0
            assert summary['average_accuracy'] >= 0.0


class TestWorkflowStages:
    """Test individual workflow stage validation."""
    
    def test_validate_svg_input_stage(self):
        """Test SVG input stage validation."""
        validator = WorkflowValidator()
        
        # Test with valid file
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as f:
            f.write(b'<svg>test</svg>')
            f.flush()
            
            result = validator._validate_svg_input(Path(f.name))
        
        assert isinstance(result, StageResult)
        assert result.stage == PipelineStage.SVG_INPUT
        assert result.success is True
        assert 'file_size' in result.metrics
        assert result.metrics['file_size'] > 0
        
        Path(f.name).unlink()
    
    def test_validate_svg_input_large_file(self):
        """Test SVG input validation with large file."""
        validator = WorkflowValidator()
        
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as f:
            # Create large content
            large_content = '<svg>' + 'x' * (15 * 1024 * 1024) + '</svg>'  # 15MB
            f.write(large_content.encode())
            f.flush()
            
            result = validator._validate_svg_input(Path(f.name))
        
        assert result.success is True  # Should still succeed
        assert len(result.issues) > 0  # But with warnings
        warning_issues = [i for i in result.issues if i.severity == ValidationSeverity.WARNING]
        assert len(warning_issues) > 0
        assert any('Large SVG file' in issue.message for issue in warning_issues)
        
        Path(f.name).unlink()
    
    def test_accuracy_calculation(self):
        """Test overall accuracy calculation."""
        validator = WorkflowValidator()
        
        # Create mock stage results
        stage_results = {
            PipelineStage.SVG_INPUT: StageResult(
                PipelineStage.SVG_INPUT, True, 0.1, [], {}
            ),
            PipelineStage.SVG_PARSING: StageResult(
                PipelineStage.SVG_PARSING, True, 0.2, 
                [ValidationIssue(PipelineStage.SVG_PARSING, ValidationSeverity.WARNING, "Warning")], {}
            ),
            PipelineStage.VISUAL_VALIDATION: StageResult(
                PipelineStage.VISUAL_VALIDATION, True, 0.3, [], 
                {'visual_similarity': 0.85}
            )
        }
        
        accuracy = validator._calculate_overall_accuracy(stage_results)
        
        assert 0.0 <= accuracy <= 1.0
        # Should be reduced due to warning but still reasonably high
        assert accuracy > 0.7
    
    def test_recommendation_generation(self):
        """Test recommendation generation."""
        validator = WorkflowValidator()
        
        # Test different scenarios
        recommendations = [
            validator._get_recommendation(0.95, 0, 0),  # High accuracy, no issues
            validator._get_recommendation(0.75, 0, 0),  # Medium accuracy
            validator._get_recommendation(0.65, 0, 0),  # Low accuracy
            validator._get_recommendation(0.85, 0, 3),  # Multiple errors
            validator._get_recommendation(0.90, 1, 0),  # Critical issues
        ]
        
        assert "APPROVED" in recommendations[0]
        assert "ACCEPTABLE" in recommendations[1] or "IMPROVE" in recommendations[1]
        assert "IMPROVE" in recommendations[2]
        assert "REVIEW" in recommendations[3]
        assert "REJECT" in recommendations[4]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
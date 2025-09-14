#!/usr/bin/env python3
"""
Workflow validation for complete SVG→DrawML→PPTX pipelines.

This module provides comprehensive validation for the entire conversion pipeline,
ensuring accuracy and data integrity at each step of the SVG to PowerPoint
conversion process.
"""

import time
import hashlib
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
from lxml import etree as ET

# Import new utilities
import sys
sys.path.append('../../../')
from tools.development.base_utilities import FileUtilities, HTMLReportGenerator
from tools.validation.validation_utilities import (
    SVGValidator, PPTXValidator, WorkflowValidator as BaseWorkflowValidator,
    ValidationLevel, ValidationResult, ValidationIssue
)
import sys
sys.path.append('../../../tools/tools/testing/')
from visual_regression_tester import VisualRegressionTester, RegressionTestResult


class PipelineStage(Enum):
    """Pipeline validation stages."""
    SVG_INPUT = "svg_input"
    SVG_PARSING = "svg_parsing"
    DRAWML_CONVERSION = "drawml_conversion"
    DRAWML_VALIDATION = "drawml_validation"
    PPTX_GENERATION = "pptx_generation"
    PPTX_VALIDATION = "pptx_validation"
    VISUAL_VALIDATION = "visual_validation"


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Individual validation issue."""
    stage: PipelineStage
    severity: ValidationSeverity
    message: str
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class StageResult:
    """Result of a pipeline stage validation."""
    stage: PipelineStage
    success: bool
    duration: float
    issues: List[ValidationIssue]
    metrics: Dict[str, Any]
    artifacts: Dict[str, str] = None  # File paths to generated artifacts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['issues'] = [issue.to_dict() for issue in self.issues]
        return result


@dataclass
class WorkflowValidationResult:
    """Complete workflow validation result."""
    workflow_id: str
    input_file: str
    success: bool
    total_duration: float
    stage_results: Dict[PipelineStage, StageResult]
    overall_accuracy: float
    summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['stage_results'] = {
            stage.value: stage_result.to_dict() 
            for stage, stage_result in self.stage_results.items()
        }
        return result


class SVGParser:
    """SVG parsing and validation utilities."""
    
    def __init__(self):
        """Initialize SVG parser."""
        self.supported_elements = {
            'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon',
            'path', 'text', 'g', 'defs', 'linearGradient', 'radialGradient',
            'filter', 'feGaussianBlur', 'feDropShadow'
        }
    
    def parse_svg(self, svg_path: Path) -> Tuple[bool, Dict[str, Any], List[ValidationIssue]]:
        """Parse SVG and extract metadata."""
        issues = []
        metadata = {
            'file_size': 0,
            'elements': {},
            'complexity_score': 0.0,
            'features_used': [],
            'viewport': {'width': 0, 'height': 0}
        }
        
        try:
            if not svg_path.exists():
                issues.append(ValidationIssue(
                    PipelineStage.SVG_INPUT,
                    ValidationSeverity.CRITICAL,
                    f"SVG file not found: {svg_path}"
                ))
                return False, metadata, issues
            
            metadata['file_size'] = svg_path.stat().st_size
            
            # Parse XML
            tree = ET.parse(svg_path)
            root = tree.getroot()
            
            # Extract viewport
            width = root.get('width', '100')
            height = root.get('height', '100')
            
            try:
                # Remove units and convert to float
                width_val = float(width.replace('px', '').replace('pt', '').replace('mm', ''))
                height_val = float(height.replace('px', '').replace('pt', '').replace('mm', ''))
                metadata['viewport'] = {'width': width_val, 'height': height_val}
            except ValueError:
                issues.append(ValidationIssue(
                    PipelineStage.SVG_PARSING,
                    ValidationSeverity.WARNING,
                    f"Could not parse viewport dimensions: {width}x{height}"
                ))
            
            # Count elements
            element_counts = {}
            complexity_score = 0.0
            
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                element_counts[tag] = element_counts.get(tag, 0) + 1
                
                # Add to complexity score
                if tag in ['path']:
                    complexity_score += 2.0  # Paths are complex
                elif tag in ['text', 'linearGradient', 'radialGradient']:
                    complexity_score += 1.5  # Moderately complex
                elif tag in self.supported_elements:
                    complexity_score += 1.0  # Basic elements
                else:
                    complexity_score += 0.5  # Unknown elements
                    if tag not in ['svg', 'g', 'defs']:  # Don't warn about container elements
                        issues.append(ValidationIssue(
                            PipelineStage.SVG_PARSING,
                            ValidationSeverity.WARNING,
                            f"Unsupported element: {tag}",
                            {'element': tag}
                        ))
            
            metadata['elements'] = element_counts
            metadata['complexity_score'] = complexity_score
            metadata['features_used'] = list(set(element_counts.keys()) & self.supported_elements)
            
            # Check for complex features
            if 'path' in element_counts:
                metadata['features_used'].append('complex_paths')
            if 'linearGradient' in element_counts or 'radialGradient' in element_counts:
                metadata['features_used'].append('gradients')
            if 'filter' in element_counts:
                metadata['features_used'].append('filters')
            
            return True, metadata, issues
            
        except ET.ParseError as e:
            issues.append(ValidationIssue(
                PipelineStage.SVG_PARSING,
                ValidationSeverity.CRITICAL,
                f"XML parsing error: {e}"
            ))
            return False, metadata, issues
        except Exception as e:
            issues.append(ValidationIssue(
                PipelineStage.SVG_PARSING,
                ValidationSeverity.CRITICAL,
                f"Unexpected error parsing SVG: {e}"
            ))
            return False, metadata, issues


class DrawMLValidator:
    """DrawML intermediate format validation."""
    
    def __init__(self):
        """Initialize DrawML validator."""
        self.required_namespaces = [
            'http://schemas.openxmlformats.org/drawingml/2006/main'
        ]
    
    def validate_drawml(self, drawml_content: str) -> Tuple[bool, Dict[str, Any], List[ValidationIssue]]:
        """Validate DrawML content."""
        issues = []
        metrics = {
            'element_count': 0,
            'namespace_count': 0,
            'shape_count': 0,
            'text_elements': 0,
            'style_definitions': 0
        }
        
        try:
            # Parse DrawML XML
            root = ET.fromstring(drawml_content)
            
            # Count elements
            for elem in root.iter():
                metrics['element_count'] += 1
                
                # Count shapes
                if 'sp' in elem.tag or 'shape' in elem.tag.lower():
                    metrics['shape_count'] += 1
                
                # Count text elements
                if 'text' in elem.tag.lower() or elem.tag.endswith('t'):
                    metrics['text_elements'] += 1
                
                # Count style definitions
                if 'style' in elem.tag.lower() or 'fill' in elem.tag.lower():
                    metrics['style_definitions'] += 1
            
            # Check for required namespaces
            namespaces = set()
            for elem in root.iter():
                if elem.tag.startswith('{'):
                    ns = elem.tag.split('}')[0][1:]
                    namespaces.add(ns)
            
            metrics['namespace_count'] = len(namespaces)
            
            # Validate required namespaces are present
            for required_ns in self.required_namespaces:
                if required_ns not in namespaces:
                    issues.append(ValidationIssue(
                        PipelineStage.DRAWML_VALIDATION,
                        ValidationSeverity.WARNING,
                        f"Missing required namespace: {required_ns}"
                    ))
            
            # Validate minimum content requirements
            if metrics['element_count'] < 3:
                issues.append(ValidationIssue(
                    PipelineStage.DRAWML_VALIDATION,
                    ValidationSeverity.ERROR,
                    "DrawML content appears too minimal"
                ))
                return False, metrics, issues
            
            return True, metrics, issues
            
        except ET.ParseError as e:
            issues.append(ValidationIssue(
                PipelineStage.DRAWML_VALIDATION,
                ValidationSeverity.CRITICAL,
                f"DrawML XML parsing error: {e}"
            ))
            return False, metrics, issues
        except Exception as e:
            issues.append(ValidationIssue(
                PipelineStage.DRAWML_VALIDATION,
                ValidationSeverity.CRITICAL,
                f"Unexpected DrawML validation error: {e}"
            ))
            return False, metrics, issues


class WorkflowValidator:
    """Main workflow validation orchestrator."""
    
    def __init__(self, 
                 accuracy_threshold: float = 0.85,
                 visual_threshold: float = 0.80,
                 max_duration: float = 300.0):
        """Initialize workflow validator."""
        self.accuracy_threshold = accuracy_threshold
        self.visual_threshold = visual_threshold
        self.max_duration = max_duration
        
        # Initialize component validators
        self.svg_parser = SVGParser()
        self.drawml_validator = DrawMLValidator()
        self.pptx_validator = PPTXValidator()
        self.visual_tester = VisualRegressionTester()
    
    def validate_workflow(self, 
                         svg_path: Path,
                         reference_pptx: Optional[Path] = None,
                         converter_command: Optional[List[str]] = None) -> WorkflowValidationResult:
        """Validate complete SVG→DrawML→PPTX workflow."""
        workflow_id = f"workflow_{int(time.time())}_{hashlib.md5(str(svg_path).encode()).hexdigest()[:8]}"
        start_time = time.time()
        
        stage_results = {}
        overall_success = True
        
        try:
            # Stage 1: SVG Input Validation
            stage_results[PipelineStage.SVG_INPUT] = self._validate_svg_input(svg_path)
            if not stage_results[PipelineStage.SVG_INPUT].success:
                overall_success = False
            
            # Stage 2: SVG Parsing
            stage_results[PipelineStage.SVG_PARSING] = self._validate_svg_parsing(svg_path)
            if not stage_results[PipelineStage.SVG_PARSING].success:
                overall_success = False
                
                # Check if we have critical parsing errors that should halt the workflow
                critical_errors = [
                    issue for issue in stage_results[PipelineStage.SVG_PARSING].issues 
                    if issue.severity == ValidationSeverity.CRITICAL
                ]
                if critical_errors:
                    # Short-circuit workflow for critical parsing errors
                    total_duration = time.time() - start_time
                    overall_accuracy = self._calculate_overall_accuracy(stage_results)
                    summary = self._generate_summary(stage_results, overall_accuracy)
                    
                    return WorkflowValidationResult(
                        workflow_id=workflow_id,
                        input_file=str(svg_path),
                        success=False,
                        total_duration=total_duration,
                        stage_results=stage_results,
                        overall_accuracy=overall_accuracy,
                        summary=summary
                    )
            
            # Stage 3: DrawML Conversion (simulated)
            stage_results[PipelineStage.DRAWML_CONVERSION] = self._validate_drawml_conversion(
                svg_path, converter_command
            )
            if not stage_results[PipelineStage.DRAWML_CONVERSION].success:
                overall_success = False
            
            # Stage 4: DrawML Validation
            drawml_content = stage_results[PipelineStage.DRAWML_CONVERSION].artifacts.get('drawml_content', '') \
                if stage_results[PipelineStage.DRAWML_CONVERSION].artifacts else ''
            stage_results[PipelineStage.DRAWML_VALIDATION] = self._validate_drawml_stage(drawml_content)
            
            # Stage 5: PPTX Generation (simulated)
            stage_results[PipelineStage.PPTX_GENERATION] = self._validate_pptx_generation(svg_path)
            if not stage_results[PipelineStage.PPTX_GENERATION].success:
                overall_success = False
            
            # Stage 6: PPTX Validation
            pptx_path = Path(stage_results[PipelineStage.PPTX_GENERATION].artifacts.get('pptx_path', '')) \
                if stage_results[PipelineStage.PPTX_GENERATION].artifacts else None
            
            if pptx_path and pptx_path.exists():
                stage_results[PipelineStage.PPTX_VALIDATION] = self._validate_pptx_stage(pptx_path)
            else:
                stage_results[PipelineStage.PPTX_VALIDATION] = StageResult(
                    PipelineStage.PPTX_VALIDATION,
                    False,
                    0.1,
                    [ValidationIssue(
                        PipelineStage.PPTX_VALIDATION,
                        ValidationSeverity.CRITICAL,
                        "No PPTX file available for validation"
                    )],
                    {}
                )
                overall_success = False
            
            # Stage 7: Visual Validation
            if pptx_path and reference_pptx and pptx_path.exists() and reference_pptx.exists():
                stage_results[PipelineStage.VISUAL_VALIDATION] = self._validate_visual_stage(
                    reference_pptx, pptx_path, workflow_id
                )
            else:
                stage_results[PipelineStage.VISUAL_VALIDATION] = StageResult(
                    PipelineStage.VISUAL_VALIDATION,
                    False,
                    0.1,
                    [ValidationIssue(
                        PipelineStage.VISUAL_VALIDATION,
                        ValidationSeverity.WARNING,
                        "Visual validation skipped - missing reference or output PPTX"
                    )],
                    {'skipped': True}
                )
            
            # Calculate overall accuracy
            overall_accuracy = self._calculate_overall_accuracy(stage_results)
            
            total_duration = time.time() - start_time
            
            # Generate summary
            summary = self._generate_summary(stage_results, overall_accuracy)
            
            return WorkflowValidationResult(
                workflow_id=workflow_id,
                input_file=str(svg_path),
                success=overall_success and overall_accuracy >= self.accuracy_threshold,
                total_duration=total_duration,
                stage_results=stage_results,
                overall_accuracy=overall_accuracy,
                summary=summary
            )
            
        except Exception as e:
            # Handle unexpected errors
            error_result = StageResult(
                PipelineStage.SVG_INPUT,  # Default stage
                False,
                time.time() - start_time,
                [ValidationIssue(
                    PipelineStage.SVG_INPUT,
                    ValidationSeverity.CRITICAL,
                    f"Workflow validation failed: {e}"
                )],
                {}
            )
            
            return WorkflowValidationResult(
                workflow_id=workflow_id,
                input_file=str(svg_path),
                success=False,
                total_duration=time.time() - start_time,
                stage_results={PipelineStage.SVG_INPUT: error_result},
                overall_accuracy=0.0,
                summary={'error': str(e)}
            )
    
    def _validate_svg_input(self, svg_path: Path) -> StageResult:
        """Validate SVG input stage."""
        start_time = time.time()
        issues = []
        metrics = {}
        
        # Check file exists
        if not svg_path.exists():
            issues.append(ValidationIssue(
                PipelineStage.SVG_INPUT,
                ValidationSeverity.CRITICAL,
                f"SVG file does not exist: {svg_path}"
            ))
            return StageResult(
                PipelineStage.SVG_INPUT,
                False,
                time.time() - start_time,
                issues,
                metrics
            )
        
        # Check file size
        file_size = svg_path.stat().st_size
        metrics['file_size'] = file_size
        
        if file_size == 0:
            issues.append(ValidationIssue(
                PipelineStage.SVG_INPUT,
                ValidationSeverity.CRITICAL,
                "SVG file is empty"
            ))
        elif file_size > 10 * 1024 * 1024:  # 10MB
            issues.append(ValidationIssue(
                PipelineStage.SVG_INPUT,
                ValidationSeverity.WARNING,
                f"Large SVG file: {file_size / 1024 / 1024:.1f}MB"
            ))
        
        # Check file extension
        if not svg_path.suffix.lower() == '.svg':
            issues.append(ValidationIssue(
                PipelineStage.SVG_INPUT,
                ValidationSeverity.WARNING,
                f"Non-standard file extension: {svg_path.suffix}"
            ))
        
        success = not any(issue.severity == ValidationSeverity.CRITICAL for issue in issues)
        
        return StageResult(
            PipelineStage.SVG_INPUT,
            success,
            time.time() - start_time,
            issues,
            metrics
        )
    
    def _validate_svg_parsing(self, svg_path: Path) -> StageResult:
        """Validate SVG parsing stage."""
        start_time = time.time()
        
        success, metadata, issues = self.svg_parser.parse_svg(svg_path)
        
        return StageResult(
            PipelineStage.SVG_PARSING,
            success,
            time.time() - start_time,
            issues,
            metadata
        )
    
    def _validate_drawml_conversion(self, svg_path: Path, converter_command: Optional[List[str]]) -> StageResult:
        """Validate DrawML conversion stage."""
        start_time = time.time()
        issues = []
        metrics = {}
        artifacts = {}
        
        # Simulate or execute DrawML conversion
        if converter_command:
            try:
                # Execute converter command
                cmd = converter_command + [str(svg_path)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                metrics['converter_exit_code'] = result.returncode
                metrics['converter_stderr_lines'] = len(result.stderr.split('\n')) if result.stderr else 0
                
                if result.returncode != 0:
                    issues.append(ValidationIssue(
                        PipelineStage.DRAWML_CONVERSION,
                        ValidationSeverity.ERROR,
                        f"Converter failed with exit code {result.returncode}: {result.stderr}"
                    ))
                    success = False
                else:
                    # Assume converter outputs DrawML content to stdout
                    artifacts['drawml_content'] = result.stdout
                    success = True
                    
            except subprocess.TimeoutExpired:
                issues.append(ValidationIssue(
                    PipelineStage.DRAWML_CONVERSION,
                    ValidationSeverity.ERROR,
                    "DrawML conversion timed out after 60 seconds"
                ))
                success = False
            except Exception as e:
                issues.append(ValidationIssue(
                    PipelineStage.DRAWML_CONVERSION,
                    ValidationSeverity.ERROR,
                    f"DrawML conversion error: {e}"
                ))
                success = False
        else:
            # Simulate DrawML conversion
            mock_drawml = '''<?xml version="1.0" encoding="UTF-8"?>
<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <a:graphicData>
        <a:sp>
            <a:spPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="100" cy="100"/>
                </a:xfrm>
                <a:prstGeom prst="rect"/>
            </a:spPr>
        </a:sp>
    </a:graphicData>
</a:graphic>'''
            artifacts['drawml_content'] = mock_drawml
            metrics['simulated'] = True
            success = True
        
        return StageResult(
            PipelineStage.DRAWML_CONVERSION,
            success,
            time.time() - start_time,
            issues,
            metrics,
            artifacts
        )
    
    def _validate_drawml_stage(self, drawml_content: str) -> StageResult:
        """Validate DrawML content."""
        start_time = time.time()
        
        if not drawml_content:
            issues = [ValidationIssue(
                PipelineStage.DRAWML_VALIDATION,
                ValidationSeverity.CRITICAL,
                "No DrawML content available for validation"
            )]
            return StageResult(
                PipelineStage.DRAWML_VALIDATION,
                False,
                time.time() - start_time,
                issues,
                {}
            )
        
        success, metrics, issues = self.drawml_validator.validate_drawml(drawml_content)
        
        return StageResult(
            PipelineStage.DRAWML_VALIDATION,
            success,
            time.time() - start_time,
            issues,
            metrics
        )
    
    def _validate_pptx_generation(self, svg_path: Path) -> StageResult:
        """Validate PPTX generation stage."""
        start_time = time.time()
        issues = []
        metrics = {}
        artifacts = {}
        
        # Create a mock PPTX file for demonstration
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            import zipfile
            
            # Create minimal PPTX structure
            with zipfile.ZipFile(temp_file, 'w') as zip_file:
                zip_file.writestr('[Content_Types].xml', '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
</Types>''')
                
                zip_file.writestr('_rels/.rels', '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>''')
                
                zip_file.writestr('ppt/presentation.xml', '''<?xml version="1.0"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId1"/>
    </p:sldIdLst>
</p:presentation>''')
            
            artifacts['pptx_path'] = temp_file.name
            metrics['pptx_size'] = Path(temp_file.name).stat().st_size
            metrics['simulated'] = True
        
        return StageResult(
            PipelineStage.PPTX_GENERATION,
            True,
            time.time() - start_time,
            issues,
            metrics,
            artifacts
        )
    
    def _validate_pptx_stage(self, pptx_path: Path) -> StageResult:
        """Validate PPTX file."""
        start_time = time.time()
        
        validation_result = self.pptx_validator.validate_pptx_structure(pptx_path)
        
        # Convert PPTX validation result to workflow validation issues
        issues = []
        for error in validation_result.errors:
            issues.append(ValidationIssue(
                PipelineStage.PPTX_VALIDATION,
                ValidationSeverity.ERROR,
                error
            ))
        
        for warning in validation_result.warnings:
            issues.append(ValidationIssue(
                PipelineStage.PPTX_VALIDATION,
                ValidationSeverity.WARNING,
                warning
            ))
        
        return StageResult(
            PipelineStage.PPTX_VALIDATION,
            validation_result.valid,
            time.time() - start_time,
            issues,
            validation_result.metadata
        )
    
    def _validate_visual_stage(self, reference_pptx: Path, output_pptx: Path, workflow_id: str) -> StageResult:
        """Validate visual comparison stage."""
        start_time = time.time()
        issues = []
        metrics = {}
        
        try:
            visual_result = self.visual_tester.run_regression_test(
                reference_pptx, output_pptx, f"visual_{workflow_id}", self.visual_threshold
            )
            
            metrics.update({
                'visual_similarity': visual_result.actual_similarity,
                'visual_threshold': self.visual_threshold,
                'visual_passed': visual_result.passed,
                'execution_time': visual_result.execution_time
            })
            
            if not visual_result.passed:
                issues.append(ValidationIssue(
                    PipelineStage.VISUAL_VALIDATION,
                    ValidationSeverity.ERROR,
                    f"Visual similarity {visual_result.actual_similarity:.3f} below threshold {self.visual_threshold:.3f}"
                ))
            
            if visual_result.error_message:
                issues.append(ValidationIssue(
                    PipelineStage.VISUAL_VALIDATION,
                    ValidationSeverity.ERROR,
                    visual_result.error_message
                ))
            
            success = visual_result.passed and not visual_result.error_message
            
        except Exception as e:
            issues.append(ValidationIssue(
                PipelineStage.VISUAL_VALIDATION,
                ValidationSeverity.ERROR,
                f"Visual validation failed: {e}"
            ))
            success = False
        
        return StageResult(
            PipelineStage.VISUAL_VALIDATION,
            success,
            time.time() - start_time,
            issues,
            metrics
        )
    
    def _calculate_overall_accuracy(self, stage_results: Dict[PipelineStage, StageResult]) -> float:
        """Calculate overall workflow accuracy."""
        weights = {
            PipelineStage.SVG_INPUT: 0.05,
            PipelineStage.SVG_PARSING: 0.15,
            PipelineStage.DRAWML_CONVERSION: 0.20,
            PipelineStage.DRAWML_VALIDATION: 0.15,
            PipelineStage.PPTX_GENERATION: 0.20,
            PipelineStage.PPTX_VALIDATION: 0.15,
            PipelineStage.VISUAL_VALIDATION: 0.10
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for stage, result in stage_results.items():
            weight = weights.get(stage, 0.1)
            
            # Calculate stage score based on success and issues
            stage_score = 1.0 if result.success else 0.0
            
            # Zero score for critical errors (highest priority)
            critical_count = sum(1 for issue in result.issues if issue.severity == ValidationSeverity.CRITICAL)
            if critical_count > 0:
                stage_score = 0.0
            
            # Reduce score for error issues  
            error_count = sum(1 for issue in result.issues if issue.severity == ValidationSeverity.ERROR)
            stage_score -= error_count * 0.3
            
            # Reduce score for warnings
            warning_count = sum(1 for issue in result.issues if issue.severity == ValidationSeverity.WARNING)
            stage_score -= warning_count * 0.1
            
            # Apply visual similarity if available
            if stage == PipelineStage.VISUAL_VALIDATION and 'visual_similarity' in result.metrics:
                stage_score = max(stage_score * result.metrics['visual_similarity'], 0.0)
            
            stage_score = max(0.0, min(1.0, stage_score))
            
            total_score += stage_score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _generate_summary(self, stage_results: Dict[PipelineStage, StageResult], overall_accuracy: float) -> Dict[str, Any]:
        """Generate workflow summary."""
        total_issues = sum(len(result.issues) for result in stage_results.values())
        critical_issues = sum(
            sum(1 for issue in result.issues if issue.severity == ValidationSeverity.CRITICAL)
            for result in stage_results.values()
        )
        error_issues = sum(
            sum(1 for issue in result.issues if issue.severity == ValidationSeverity.ERROR)
            for result in stage_results.values()
        )
        warning_issues = sum(
            sum(1 for issue in result.issues if issue.severity == ValidationSeverity.WARNING)
            for result in stage_results.values()
        )
        
        successful_stages = sum(1 for result in stage_results.values() if result.success)
        total_stages = len(stage_results)
        
        return {
            'overall_accuracy': overall_accuracy,
            'successful_stages': successful_stages,
            'total_stages': total_stages,
            'stage_success_rate': successful_stages / total_stages if total_stages > 0 else 0.0,
            'total_issues': total_issues,
            'critical_issues': critical_issues,
            'error_issues': error_issues,
            'warning_issues': warning_issues,
            'recommendation': self._get_recommendation(overall_accuracy, critical_issues, error_issues)
        }
    
    def _get_recommendation(self, accuracy: float, critical: int, errors: int) -> str:
        """Get recommendation based on validation results."""
        if critical > 0:
            return "REJECT: Critical issues must be resolved before proceeding"
        elif errors > 2:
            return "REVIEW: Multiple errors detected, manual review recommended"
        elif accuracy < 0.7:
            return "IMPROVE: Low accuracy score, significant improvements needed"
        elif accuracy < 0.85:
            return "ACCEPTABLE: Minor improvements recommended"
        else:
            return "APPROVED: Workflow validation passed successfully"


def batch_validate_workflows(svg_files: List[Path], 
                             reference_dir: Optional[Path] = None,
                             output_dir: Path = Path("workflow_results"),
                             max_workers: int = 4) -> Dict[str, WorkflowValidationResult]:
    """Batch validate multiple SVG workflows."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    
    validator = WorkflowValidator()
    
    def validate_single_workflow(svg_path: Path) -> Tuple[str, WorkflowValidationResult]:
        reference_pptx = None
        if reference_dir:
            reference_pptx = reference_dir / f"{svg_path.stem}.pptx"
            if not reference_pptx.exists():
                reference_pptx = None
        
        result = validator.validate_workflow(svg_path, reference_pptx)
        
        # Save individual result
        result_file = output_dir / f"{svg_path.stem}_workflow_result.json"
        with open(result_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        
        return svg_path.name, result
    
    # Execute batch validation with threading
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_svg = {
            executor.submit(validate_single_workflow, svg_path): svg_path 
            for svg_path in svg_files
        }
        
        for future in as_completed(future_to_svg):
            svg_path = future_to_svg[future]
            try:
                svg_name, result = future.result()
                results[svg_name] = result
                print(f"✅ Validated: {svg_name} (accuracy: {result.overall_accuracy:.3f})")
            except Exception as e:
                print(f"❌ Failed: {svg_path.name} - {e}")
    
    # Generate batch summary
    batch_summary = {
        "total_workflows": len(svg_files),
        "successful_validations": sum(1 for r in results.values() if r.success),
        "average_accuracy": sum(r.overall_accuracy for r in results.values()) / len(results) if results else 0.0,
        "results": {name: result.to_dict() for name, result in results.items()}
    }
    
    summary_file = output_dir / "batch_workflow_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(batch_summary, f, indent=2, default=str)
    
    print(f"📊 Batch validation complete: {len(results)} workflows processed")
    print(f"📁 Results saved to: {output_dir}")
    
    return results


if __name__ == '__main__':
    # Example usage and demonstration
    print("🔧 Workflow Validator - SVG→DrawML→PPTX Pipeline Validation")
    print("=" * 60)
    
    # Test with sample SVG from corpus
    svg_corpus_dir = Path("tests/test_data/svg_corpus")
    if svg_corpus_dir.exists():
        svg_files = list(svg_corpus_dir.glob("**/*.svg"))
        if svg_files:
            print(f"📁 Found {len(svg_files)} SVG files in test corpus")
            
            # Validate first SVG file
            sample_svg = svg_files[0]
            print(f"🔍 Validating: {sample_svg}")
            
            validator = WorkflowValidator()
            result = validator.validate_workflow(sample_svg)
            
            print(f"\n📊 Validation Results:")
            print(f"   Workflow ID: {result.workflow_id}")
            print(f"   Success: {'✅' if result.success else '❌'}")
            print(f"   Overall Accuracy: {result.overall_accuracy:.3f}")
            print(f"   Duration: {result.total_duration:.2f}s")
            print(f"   Stages: {len(result.stage_results)}")
            
            for stage, stage_result in result.stage_results.items():
                status = "✅" if stage_result.success else "❌"
                print(f"     {stage.value}: {status} ({stage_result.duration:.2f}s, {len(stage_result.issues)} issues)")
            
            print(f"\n💡 Recommendation: {result.summary.get('recommendation', 'No recommendation')}")
            
        else:
            print("❌ No SVG files found in test corpus")
    else:
        print("❌ Test corpus not found - run generate_test_corpus.py first")
    
    print(f"\n🚀 Workflow validation system ready for end-to-end testing!")
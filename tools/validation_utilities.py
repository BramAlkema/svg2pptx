#!/usr/bin/env python3
"""
Validation utilities for SVG2PPTX tools.

This module provides specialized validation classes and utilities that extend
the base validation framework for SVG, PPTX, and workflow validation tasks.
"""

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from tools.base_utilities import BaseValidator, BaseReport


class ValidationLevel(Enum):
    """Validation thoroughness levels."""
    MINIMAL = "minimal"
    STANDARD = "standard" 
    COMPREHENSIVE = "comprehensive"


@dataclass
class ValidationIssue:
    """Structured validation issue."""
    severity: str  # "error", "warning", "info"
    category: str  # "structure", "content", "format", etc.
    message: str
    location: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation of issue."""
        loc = f" at {self.location}" if self.location else ""
        return f"[{self.severity.upper()}] {self.category}: {self.message}{loc}"


@dataclass
class ValidationResult:
    """Comprehensive validation result."""
    is_valid: bool
    validator_name: str
    target: str
    issues: List[ValidationIssue]
    metadata: Dict[str, Any]
    validation_level: ValidationLevel
    
    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for issue in self.issues if issue.severity == "error")
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for issue in self.issues if issue.severity == "warning")
    
    def get_issues_by_severity(self, severity: str) -> List[ValidationIssue]:
        """Get issues filtered by severity level."""
        return [issue for issue in self.issues if issue.severity == severity]


class SVGValidator(BaseValidator):
    """Specialized SVG file validation."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        """Initialize SVG validator."""
        super().__init__("SVGValidator")
        self.validation_level = validation_level
        self.required_namespaces = {
            'svg': 'http://www.w3.org/2000/svg',
            'xlink': 'http://www.w3.org/1999/xlink'
        }
    
    def validate(self, svg_path: Path) -> ValidationResult:
        """Validate SVG file structure and content.
        
        Args:
            svg_path: Path to SVG file
            
        Returns:
            ValidationResult with detailed analysis
        """
        issues = []
        metadata = {}
        
        try:
            # Basic file validation
            if not svg_path.exists():
                issues.append(ValidationIssue(
                    "error", "file", f"SVG file not found: {svg_path}"
                ))
                return ValidationResult(
                    False, self.name, str(svg_path), issues, metadata, self.validation_level
                )
            
            # Parse SVG
            tree = ET.parse(str(svg_path))
            root = tree.getroot()
            
            # Basic structure validation
            if root.tag != '{http://www.w3.org/2000/svg}svg':
                issues.append(ValidationIssue(
                    "error", "structure", "Root element is not SVG"
                ))
            
            # Extract metadata
            metadata.update({
                'file_size': svg_path.stat().st_size,
                'root_tag': root.tag,
                'width': root.get('width'),
                'height': root.get('height'),
                'viewBox': root.get('viewBox'),
                'element_count': len(list(root.iter()))
            })
            
            # Namespace validation
            self._validate_namespaces(root, issues)
            
            # Content validation based on level
            if self.validation_level != ValidationLevel.MINIMAL:
                self._validate_content(root, issues, metadata)
            
            if self.validation_level == ValidationLevel.COMPREHENSIVE:
                self._validate_comprehensive(root, issues, metadata)
                
        except ET.ParseError as e:
            issues.append(ValidationIssue(
                "error", "parsing", f"XML parsing error: {e}"
            ))
        except Exception as e:
            issues.append(ValidationIssue(
                "error", "unexpected", f"Unexpected validation error: {e}"
            ))
        
        is_valid = not any(issue.severity == "error" for issue in issues)
        return ValidationResult(
            is_valid, self.name, str(svg_path), issues, metadata, self.validation_level
        )
    
    def _validate_namespaces(self, root: ET.Element, issues: List[ValidationIssue]) -> None:
        """Validate required namespaces are present."""
        for prefix, uri in self.required_namespaces.items():
            if uri not in [ns for ns in root.nsmap.values()] if hasattr(root, 'nsmap') else []:
                # Fallback for ElementTree without nsmap
                if f'{{{uri}}}' not in str(root.tag):
                    issues.append(ValidationIssue(
                        "warning", "namespace", f"Missing namespace: {prefix} ({uri})"
                    ))
    
    def _validate_content(self, root: ET.Element, issues: List[ValidationIssue], 
                         metadata: Dict[str, Any]) -> None:
        """Validate SVG content elements."""
        # Count element types
        element_counts = {}
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            element_counts[tag] = element_counts.get(tag, 0) + 1
        
        metadata['element_types'] = element_counts
        
        # Check for common issues
        if 'defs' in element_counts and element_counts['defs'] > 1:
            issues.append(ValidationIssue(
                "warning", "structure", "Multiple <defs> elements found"
            ))
        
        # Validate dimensions
        if not root.get('width') and not root.get('height') and not root.get('viewBox'):
            issues.append(ValidationIssue(
                "warning", "dimensions", "No explicit dimensions or viewBox defined"
            ))
    
    def _validate_comprehensive(self, root: ET.Element, issues: List[ValidationIssue],
                               metadata: Dict[str, Any]) -> None:
        """Comprehensive validation including advanced checks."""
        # Check for unused definitions
        defined_ids = {elem.get('id') for elem in root.iter() if elem.get('id')}
        referenced_ids = set()
        
        # Find all references (url(#id), href="#id", etc.)
        for elem in root.iter():
            for attr_value in elem.attrib.values():
                if isinstance(attr_value, str):
                    if attr_value.startswith('url(#') and attr_value.endswith(')'):
                        ref_id = attr_value[5:-1]
                        referenced_ids.add(ref_id)
                    elif attr_value.startswith('#'):
                        referenced_ids.add(attr_value[1:])
        
        unused_ids = defined_ids - referenced_ids
        if unused_ids:
            issues.append(ValidationIssue(
                "info", "optimization", f"Unused IDs found: {', '.join(unused_ids)}"
            ))
        
        metadata['defined_ids'] = len(defined_ids)
        metadata['referenced_ids'] = len(referenced_ids)
        metadata['unused_ids'] = len(unused_ids)


class PPTXValidator(BaseValidator):
    """Specialized PPTX file validation."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        """Initialize PPTX validator."""
        super().__init__("PPTXValidator")
        self.validation_level = validation_level
    
    def validate(self, pptx_path: Path) -> ValidationResult:
        """Validate PPTX file structure and content.
        
        Args:
            pptx_path: Path to PPTX file
            
        Returns:
            ValidationResult with detailed analysis
        """
        issues = []
        metadata = {}
        
        try:
            if not pptx_path.exists():
                issues.append(ValidationIssue(
                    "error", "file", f"PPTX file not found: {pptx_path}"
                ))
                return ValidationResult(
                    False, self.name, str(pptx_path), issues, metadata, self.validation_level
                )
            
            # Basic ZIP validation
            with zipfile.ZipFile(pptx_path, 'r') as zip_file:
                zip_info = zip_file.infolist()
                metadata['file_count'] = len(zip_info)
                metadata['file_size'] = pptx_path.stat().st_size
                
                # Check required PPTX structure
                required_files = [
                    '[Content_Types].xml',
                    '_rels/.rels',
                    'ppt/presentation.xml'
                ]
                
                zip_files = {info.filename for info in zip_info}
                for required_file in required_files:
                    if required_file not in zip_files:
                        issues.append(ValidationIssue(
                            "error", "structure", f"Missing required file: {required_file}"
                        ))
                
                # Count slides
                slide_count = len([f for f in zip_files if f.startswith('ppt/slides/slide') and f.endswith('.xml')])
                metadata['slide_count'] = slide_count
                
                if slide_count == 0:
                    issues.append(ValidationIssue(
                        "warning", "content", "No slides found in presentation"
                    ))
                
                # Additional validation based on level
                if self.validation_level != ValidationLevel.MINIMAL:
                    self._validate_content_types(zip_file, issues, metadata)
                
                if self.validation_level == ValidationLevel.COMPREHENSIVE:
                    self._validate_relationships(zip_file, issues, metadata)
                    
        except zipfile.BadZipFile:
            issues.append(ValidationIssue(
                "error", "format", "Invalid ZIP file format"
            ))
        except Exception as e:
            issues.append(ValidationIssue(
                "error", "unexpected", f"Unexpected validation error: {e}"
            ))
        
        is_valid = not any(issue.severity == "error" for issue in issues)
        return ValidationResult(
            is_valid, self.name, str(pptx_path), issues, metadata, self.validation_level
        )
    
    def _validate_content_types(self, zip_file: zipfile.ZipFile, 
                               issues: List[ValidationIssue], metadata: Dict[str, Any]) -> None:
        """Validate content types definition."""
        try:
            content_types = zip_file.read('[Content_Types].xml')
            root = ET.fromstring(content_types)
            
            # Count content types
            default_types = len(root.findall('.//{http://schemas.openxmlformats.org/package/2006/content-types}Default'))
            override_types = len(root.findall('.//{http://schemas.openxmlformats.org/package/2006/content-types}Override'))
            
            metadata['default_content_types'] = default_types
            metadata['override_content_types'] = override_types
            
        except Exception as e:
            issues.append(ValidationIssue(
                "warning", "content_types", f"Could not validate content types: {e}"
            ))
    
    def _validate_relationships(self, zip_file: zipfile.ZipFile,
                               issues: List[ValidationIssue], metadata: Dict[str, Any]) -> None:
        """Validate relationship integrity."""
        try:
            # Check main relationships
            main_rels = zip_file.read('_rels/.rels')
            root = ET.fromstring(main_rels)
            
            relationship_count = len(root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'))
            metadata['main_relationships'] = relationship_count
            
            # Check presentation relationships if they exist
            try:
                ppt_rels = zip_file.read('ppt/_rels/presentation.xml.rels')
                ppt_root = ET.fromstring(ppt_rels)
                ppt_rel_count = len(ppt_root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'))
                metadata['presentation_relationships'] = ppt_rel_count
            except KeyError:
                issues.append(ValidationIssue(
                    "warning", "relationships", "Missing presentation relationships file"
                ))
                
        except Exception as e:
            issues.append(ValidationIssue(
                "warning", "relationships", f"Could not validate relationships: {e}"
            ))


class WorkflowValidator(BaseValidator):
    """End-to-end workflow validation."""
    
    def __init__(self, 
                 svg_validator: Optional[SVGValidator] = None,
                 pptx_validator: Optional[PPTXValidator] = None,
                 validation_level: ValidationLevel = ValidationLevel.STANDARD):
        """Initialize workflow validator."""
        super().__init__("WorkflowValidator")
        self.svg_validator = svg_validator or SVGValidator(validation_level)
        self.pptx_validator = pptx_validator or PPTXValidator(validation_level)
        self.validation_level = validation_level
    
    def validate_conversion(self, svg_path: Path, pptx_path: Path) -> Dict[str, ValidationResult]:
        """Validate complete SVG to PPTX conversion workflow.
        
        Args:
            svg_path: Path to source SVG file
            pptx_path: Path to output PPTX file
            
        Returns:
            Dictionary with validation results for each stage
        """
        results = {}
        
        # Validate source SVG
        results['svg'] = self.svg_validator.validate(svg_path)
        
        # Validate output PPTX
        results['pptx'] = self.pptx_validator.validate(pptx_path)
        
        # Workflow-specific validation
        issues = []
        metadata = {}
        
        if results['svg'].is_valid and results['pptx'].is_valid:
            # Cross-validation between SVG and PPTX
            svg_meta = results['svg'].metadata
            pptx_meta = results['pptx'].metadata
            
            # Check if conversion preserved content appropriately
            if pptx_meta.get('slide_count', 0) == 0:
                issues.append(ValidationIssue(
                    "error", "conversion", "Conversion produced empty presentation"
                ))
            
            metadata['svg_elements'] = svg_meta.get('element_count', 0)
            metadata['pptx_slides'] = pptx_meta.get('slide_count', 0)
            metadata['conversion_ratio'] = (
                pptx_meta.get('slide_count', 0) / max(1, svg_meta.get('element_count', 1))
            )
        
        is_valid = (results['svg'].is_valid and results['pptx'].is_valid and 
                   not any(issue.severity == "error" for issue in issues))
        
        results['workflow'] = ValidationResult(
            is_valid, self.name, f"{svg_path} -> {pptx_path}", 
            issues, metadata, self.validation_level
        )
        
        return results


# Convenience imports
__all__ = [
    'ValidationLevel',
    'ValidationIssue', 
    'ValidationResult',
    'SVGValidator',
    'PPTXValidator',
    'WorkflowValidator'
]
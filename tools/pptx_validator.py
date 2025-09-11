#!/usr/bin/env python3
"""
PPTX validation and comparison utilities.

This module provides comprehensive validation for PPTX files including
structure validation, content comparison, and accuracy measurement
against reference files.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import hashlib
import difflib
from dataclasses import dataclass, asdict
from enum import Enum
import re


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"
    STANDARD = "standard" 
    LENIENT = "lenient"


class ComparisonResult(Enum):
    """Comparison result types."""
    IDENTICAL = "identical"
    SIMILAR = "similar"
    DIFFERENT = "different"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Result of PPTX validation."""
    valid: bool
    score: float  # 0.0 to 1.0
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ComparisonMetrics:
    """Metrics for PPTX comparison."""
    structural_similarity: float
    content_similarity: float
    visual_similarity: float
    element_count_match: float
    attribute_match: float
    overall_accuracy: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class PPTXValidator:
    """Comprehensive PPTX validation and comparison."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        """Initialize validator with specified validation level."""
        self.validation_level = validation_level
        self.namespace_map = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }
    
    def validate_pptx_structure(self, pptx_path: Path) -> ValidationResult:
        """Validate PPTX file structure and integrity."""
        errors = []
        warnings = []
        metadata = {}
        
        try:
            if not pptx_path.exists():
                return ValidationResult(
                    valid=False,
                    score=0.0,
                    errors=[f"File not found: {pptx_path}"],
                    warnings=[],
                    metadata={}
                )
            
            # Check file is a valid ZIP
            with zipfile.ZipFile(pptx_path, 'r') as zip_file:
                metadata['file_size'] = pptx_path.stat().st_size
                metadata['zip_entries'] = len(zip_file.namelist())
                
                # Check required PPTX files
                required_files = [
                    '[Content_Types].xml',
                    '_rels/.rels',
                    'ppt/presentation.xml'
                ]
                
                missing_files = []
                for required_file in required_files:
                    if required_file not in zip_file.namelist():
                        missing_files.append(required_file)
                
                if missing_files:
                    errors.extend([f"Missing required file: {f}" for f in missing_files])
                
                # Parse presentation.xml
                try:
                    presentation_xml = zip_file.read('ppt/presentation.xml')
                    presentation_tree = ET.fromstring(presentation_xml)
                    
                    # Count slides
                    slide_id_list = presentation_tree.find('.//p:sldIdLst', self.namespace_map)
                    slide_count = len(slide_id_list) if slide_id_list is not None else 0
                    metadata['slide_count'] = slide_count
                    
                    if slide_count == 0:
                        warnings.append("No slides found in presentation")
                    
                except ET.ParseError as e:
                    errors.append(f"XML parse error in presentation.xml: {e}")
                except Exception as e:
                    errors.append(f"Error reading presentation.xml: {e}")
                
                # Validate slide files
                slide_files = [f for f in zip_file.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
                metadata['slide_files'] = len(slide_files)
                
                element_count = 0
                for slide_file in slide_files:
                    try:
                        slide_xml = zip_file.read(slide_file)
                        slide_tree = ET.fromstring(slide_xml)
                        
                        # Count drawing elements
                        elements = slide_tree.findall('.//a:*', self.namespace_map)
                        element_count += len(elements)
                        
                    except ET.ParseError as e:
                        errors.append(f"XML parse error in {slide_file}: {e}")
                    except Exception as e:
                        warnings.append(f"Error reading {slide_file}: {e}")
                
                metadata['total_elements'] = element_count
                
        except zipfile.BadZipFile:
            errors.append("File is not a valid ZIP archive")
        except Exception as e:
            errors.append(f"Unexpected error during validation: {e}")
        
        # Calculate validation score
        score = self._calculate_validation_score(errors, warnings, metadata)
        
        return ValidationResult(
            valid=len(errors) == 0,
            score=score,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    def compare_pptx_files(self, reference_path: Path, output_path: Path) -> Tuple[ComparisonResult, ComparisonMetrics, Dict[str, Any]]:
        """Compare two PPTX files for accuracy measurement."""
        try:
            # Validate both files first
            ref_validation = self.validate_pptx_structure(reference_path)
            out_validation = self.validate_pptx_structure(output_path)
            
            if not ref_validation.valid or not out_validation.valid:
                return (
                    ComparisonResult.ERROR,
                    ComparisonMetrics(0, 0, 0, 0, 0, 0),
                    {"error": "One or both files failed validation"}
                )
            
            # Extract and compare content
            ref_content = self._extract_pptx_content(reference_path)
            out_content = self._extract_pptx_content(output_path)
            
            # Calculate similarity metrics
            structural_sim = self._calculate_structural_similarity(ref_content, out_content)
            content_sim = self._calculate_content_similarity(ref_content, out_content)
            visual_sim = self._calculate_visual_similarity(ref_content, out_content)
            element_match = self._calculate_element_count_match(ref_content, out_content)
            attr_match = self._calculate_attribute_match(ref_content, out_content)
            
            # Overall accuracy score
            overall_accuracy = (structural_sim + content_sim + visual_sim + element_match + attr_match) / 5.0
            
            metrics = ComparisonMetrics(
                structural_similarity=structural_sim,
                content_similarity=content_sim,
                visual_similarity=visual_sim,
                element_count_match=element_match,
                attribute_match=attr_match,
                overall_accuracy=overall_accuracy
            )
            
            # Determine comparison result
            if overall_accuracy >= 0.95:
                result = ComparisonResult.IDENTICAL
            elif overall_accuracy >= 0.80:
                result = ComparisonResult.SIMILAR
            else:
                result = ComparisonResult.DIFFERENT
            
            details = {
                "reference_metadata": ref_validation.metadata,
                "output_metadata": out_validation.metadata,
                "differences": self._generate_difference_report(ref_content, out_content)
            }
            
            return (result, metrics, details)
            
        except Exception as e:
            return (
                ComparisonResult.ERROR,
                ComparisonMetrics(0, 0, 0, 0, 0, 0),
                {"error": str(e)}
            )
    
    def _extract_pptx_content(self, pptx_path: Path) -> Dict[str, Any]:
        """Extract structured content from PPTX file."""
        content = {
            "slides": [],
            "master_slides": [],
            "layouts": [],
            "themes": []
        }
        
        with zipfile.ZipFile(pptx_path, 'r') as zip_file:
            # Extract slide content
            slide_files = [f for f in zip_file.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
            slide_files.sort()  # Ensure consistent ordering
            
            for slide_file in slide_files:
                try:
                    slide_xml = zip_file.read(slide_file)
                    slide_tree = ET.fromstring(slide_xml)
                    
                    slide_content = {
                        "file": slide_file,
                        "shapes": [],
                        "text_elements": [],
                        "drawing_elements": []
                    }
                    
                    # Extract shapes and elements
                    for sp in slide_tree.findall('.//p:sp', self.namespace_map):
                        shape_data = self._extract_shape_data(sp)
                        slide_content["shapes"].append(shape_data)
                    
                    # Extract text elements
                    for text_elem in slide_tree.findall('.//a:t', self.namespace_map):
                        if text_elem.text:
                            slide_content["text_elements"].append(text_elem.text.strip())
                    
                    # Extract drawing elements
                    for drawing_elem in slide_tree.findall('.//a:*[@*]', self.namespace_map):
                        elem_data = {
                            "tag": drawing_elem.tag,
                            "attributes": dict(drawing_elem.attrib)
                        }
                        slide_content["drawing_elements"].append(elem_data)
                    
                    content["slides"].append(slide_content)
                    
                except ET.ParseError:
                    continue  # Skip malformed slides
                except Exception:
                    continue  # Skip problematic slides
        
        return content
    
    def _extract_shape_data(self, shape_element: ET.Element) -> Dict[str, Any]:
        """Extract data from a shape element."""
        shape_data = {
            "type": "unknown",
            "geometry": {},
            "style": {},
            "text": ""
        }
        
        try:
            # Get shape type
            preset_geom = shape_element.find('.//a:prstGeom', self.namespace_map)
            if preset_geom is not None:
                shape_data["type"] = preset_geom.get('prst', 'unknown')
            
            # Get geometry data
            xfrm = shape_element.find('.//a:xfrm', self.namespace_map)
            if xfrm is not None:
                off = xfrm.find('a:off', self.namespace_map)
                ext = xfrm.find('a:ext', self.namespace_map)
                
                if off is not None:
                    shape_data["geometry"]["x"] = off.get('x', '0')
                    shape_data["geometry"]["y"] = off.get('y', '0')
                
                if ext is not None:
                    shape_data["geometry"]["width"] = ext.get('cx', '0')
                    shape_data["geometry"]["height"] = ext.get('cy', '0')
            
            # Get style information
            solid_fill = shape_element.find('.//a:solidFill', self.namespace_map)
            if solid_fill is not None:
                color_elem = solid_fill.find('a:srgbClr', self.namespace_map)
                if color_elem is not None:
                    shape_data["style"]["fill_color"] = color_elem.get('val', '')
            
            # Get text content
            text_elements = shape_element.findall('.//a:t', self.namespace_map)
            text_content = ' '.join([t.text for t in text_elements if t.text])
            shape_data["text"] = text_content.strip()
            
        except Exception:
            pass  # Return partial data on error
        
        return shape_data
    
    def _calculate_structural_similarity(self, ref_content: Dict, out_content: Dict) -> float:
        """Calculate structural similarity between PPTX contents."""
        try:
            ref_slides = len(ref_content.get("slides", []))
            out_slides = len(out_content.get("slides", []))
            
            if ref_slides == 0 and out_slides == 0:
                return 1.0
            
            if ref_slides == 0 or out_slides == 0:
                return 0.0
            
            # Compare slide count
            slide_ratio = min(ref_slides, out_slides) / max(ref_slides, out_slides)
            
            # Compare shapes per slide
            shape_similarities = []
            for i in range(min(ref_slides, out_slides)):
                ref_shapes = len(ref_content["slides"][i].get("shapes", []))
                out_shapes = len(out_content["slides"][i].get("shapes", []))
                
                if ref_shapes == 0 and out_shapes == 0:
                    shape_similarities.append(1.0)
                elif ref_shapes == 0 or out_shapes == 0:
                    shape_similarities.append(0.0)
                else:
                    shape_similarities.append(min(ref_shapes, out_shapes) / max(ref_shapes, out_shapes))
            
            avg_shape_similarity = sum(shape_similarities) / len(shape_similarities) if shape_similarities else 0.0
            
            return (slide_ratio + avg_shape_similarity) / 2.0
            
        except Exception:
            return 0.0
    
    def _calculate_content_similarity(self, ref_content: Dict, out_content: Dict) -> float:
        """Calculate content similarity (text, attributes)."""
        try:
            ref_texts = []
            out_texts = []
            
            # Collect all text elements
            for slide in ref_content.get("slides", []):
                ref_texts.extend(slide.get("text_elements", []))
            
            for slide in out_content.get("slides", []):
                out_texts.extend(slide.get("text_elements", []))
            
            if not ref_texts and not out_texts:
                return 1.0
            
            if not ref_texts or not out_texts:
                return 0.0
            
            # Calculate text similarity using sequence matcher
            ref_text = ' '.join(ref_texts)
            out_text = ' '.join(out_texts)
            
            matcher = difflib.SequenceMatcher(None, ref_text, out_text)
            return matcher.ratio()
            
        except Exception:
            return 0.0
    
    def _calculate_visual_similarity(self, ref_content: Dict, out_content: Dict) -> float:
        """Calculate visual similarity (colors, positions, sizes)."""
        try:
            similarities = []
            
            ref_slides = ref_content.get("slides", [])
            out_slides = out_content.get("slides", [])
            
            for i in range(min(len(ref_slides), len(out_slides))):
                ref_shapes = ref_slides[i].get("shapes", [])
                out_shapes = out_slides[i].get("shapes", [])
                
                if not ref_shapes and not out_shapes:
                    similarities.append(1.0)
                    continue
                
                if not ref_shapes or not out_shapes:
                    similarities.append(0.0)
                    continue
                
                # Compare shape visual properties
                shape_matches = 0
                for ref_shape in ref_shapes:
                    best_match = 0.0
                    for out_shape in out_shapes:
                        match = self._compare_shape_visual_properties(ref_shape, out_shape)
                        best_match = max(best_match, match)
                    shape_matches += best_match
                
                slide_similarity = shape_matches / len(ref_shapes) if ref_shapes else 0.0
                similarities.append(slide_similarity)
            
            return sum(similarities) / len(similarities) if similarities else 0.0
            
        except Exception:
            return 0.0
    
    def _compare_shape_visual_properties(self, ref_shape: Dict, out_shape: Dict) -> float:
        """Compare visual properties of two shapes."""
        try:
            matches = 0
            total_props = 0
            
            # Compare shape type
            total_props += 1
            if ref_shape.get("type") == out_shape.get("type"):
                matches += 1
            
            # Compare geometry (approximate)
            ref_geom = ref_shape.get("geometry", {})
            out_geom = out_shape.get("geometry", {})
            
            for prop in ["width", "height"]:
                if prop in ref_geom and prop in out_geom:
                    total_props += 1
                    try:
                        ref_val = float(ref_geom[prop])
                        out_val = float(out_geom[prop])
                        if ref_val > 0 and out_val > 0:
                            ratio = min(ref_val, out_val) / max(ref_val, out_val)
                            if ratio > 0.9:  # 90% similarity threshold
                                matches += 1
                    except (ValueError, ZeroDivisionError):
                        pass
            
            # Compare style properties
            ref_style = ref_shape.get("style", {})
            out_style = out_shape.get("style", {})
            
            for prop in ["fill_color"]:
                if prop in ref_style and prop in out_style:
                    total_props += 1
                    if ref_style[prop] == out_style[prop]:
                        matches += 1
            
            return matches / total_props if total_props > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_element_count_match(self, ref_content: Dict, out_content: Dict) -> float:
        """Calculate element count matching accuracy."""
        try:
            ref_total = sum(len(slide.get("drawing_elements", [])) for slide in ref_content.get("slides", []))
            out_total = sum(len(slide.get("drawing_elements", [])) for slide in out_content.get("slides", []))
            
            if ref_total == 0 and out_total == 0:
                return 1.0
            
            if ref_total == 0 or out_total == 0:
                return 0.0
            
            return min(ref_total, out_total) / max(ref_total, out_total)
            
        except Exception:
            return 0.0
    
    def _calculate_attribute_match(self, ref_content: Dict, out_content: Dict) -> float:
        """Calculate attribute matching accuracy."""
        try:
            # This is a simplified version - could be expanded for more detailed attribute comparison
            ref_attrs = set()
            out_attrs = set()
            
            for slide in ref_content.get("slides", []):
                for elem in slide.get("drawing_elements", []):
                    for attr_name, attr_value in elem.get("attributes", {}).items():
                        ref_attrs.add(f"{attr_name}:{attr_value}")
            
            for slide in out_content.get("slides", []):
                for elem in slide.get("drawing_elements", []):
                    for attr_name, attr_value in elem.get("attributes", {}).items():
                        out_attrs.add(f"{attr_name}:{attr_value}")
            
            if not ref_attrs and not out_attrs:
                return 1.0
            
            if not ref_attrs or not out_attrs:
                return 0.0
            
            intersection = len(ref_attrs.intersection(out_attrs))
            union = len(ref_attrs.union(out_attrs))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _generate_difference_report(self, ref_content: Dict, out_content: Dict) -> List[str]:
        """Generate detailed difference report."""
        differences = []
        
        try:
            ref_slides = len(ref_content.get("slides", []))
            out_slides = len(out_content.get("slides", []))
            
            if ref_slides != out_slides:
                differences.append(f"Slide count mismatch: reference={ref_slides}, output={out_slides}")
            
            # Compare slides
            for i in range(min(ref_slides, out_slides)):
                ref_slide = ref_content["slides"][i]
                out_slide = out_content["slides"][i]
                
                ref_shapes = len(ref_slide.get("shapes", []))
                out_shapes = len(out_slide.get("shapes", []))
                
                if ref_shapes != out_shapes:
                    differences.append(f"Slide {i+1} shape count mismatch: reference={ref_shapes}, output={out_shapes}")
                
                ref_texts = ref_slide.get("text_elements", [])
                out_texts = out_slide.get("text_elements", [])
                
                if len(ref_texts) != len(out_texts):
                    differences.append(f"Slide {i+1} text element count mismatch: reference={len(ref_texts)}, output={len(out_texts)}")
        
        except Exception as e:
            differences.append(f"Error generating difference report: {e}")
        
        return differences
    
    def _calculate_validation_score(self, errors: List[str], warnings: List[str], metadata: Dict[str, Any]) -> float:
        """Calculate overall validation score."""
        if errors:
            return 0.0
        
        score = 1.0
        
        # Reduce score for warnings
        score -= len(warnings) * 0.1
        
        # Ensure minimum elements
        element_count = metadata.get('total_elements', 0)
        if element_count == 0:
            score -= 0.3
        
        # Ensure slides exist
        slide_count = metadata.get('slide_count', 0)
        if slide_count == 0:
            score -= 0.5
        
        return max(0.0, min(1.0, score))


def create_reference_pptx_database(corpus_path: Path, output_path: Path) -> Dict[str, Any]:
    """Create reference database of expected PPTX outputs for test corpus."""
    database = {
        "created": "2025-09-11",
        "corpus_path": str(corpus_path),
        "references": {}
    }
    
    # This would be populated with actual reference files
    # For now, creating structure for expected references
    
    corpus_metadata_path = corpus_path / "corpus_metadata.json"
    if corpus_metadata_path.exists():
        with open(corpus_metadata_path, 'r') as f:
            corpus_metadata = json.load(f)
        
        for file_name, file_info in corpus_metadata.get("test_files", {}).items():
            reference_key = file_name.replace('.svg', '.pptx')
            database["references"][reference_key] = {
                "svg_source": file_name,
                "expected_elements": file_info.get("expected_elements", 1),
                "complexity": file_info.get("complexity", "basic"),
                "features": file_info.get("features", []),
                "accuracy_threshold": 0.85,  # Minimum accuracy for pass
                "reference_file": f"references/{reference_key}",
                "validation_notes": []
            }
    
    # Save database
    with open(output_path, 'w') as f:
        json.dump(database, f, indent=2)
    
    return database


if __name__ == '__main__':
    # Example usage and testing
    validator = PPTXValidator(ValidationLevel.STANDARD)
    
    # Create reference database
    corpus_path = Path("tests/test_data/svg_corpus")
    if corpus_path.exists():
        db_path = Path("tests/test_data/pptx_references/reference_database.json")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        database = create_reference_pptx_database(corpus_path, db_path)
        print(f"✅ Created reference database with {len(database['references'])} entries")
        print(f"📁 Database saved to: {db_path}")
    else:
        print("❌ SVG corpus not found - run generate_test_corpus.py first")
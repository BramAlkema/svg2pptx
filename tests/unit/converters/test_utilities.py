#!/usr/bin/env python3
"""
Test utilities for missing SVG elements testing.

Provides reusable utility functions, fixtures, and helpers for comprehensive
testing of missing SVG elements in the SVG2PPTX converter.
"""

from lxml import etree as ET
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import json
import os
from unittest.mock import Mock, MagicMock

# Import pytest only when needed
try:
    import pytest
except ImportError:
    pytest = None


class SVGElementParser:
    """Advanced SVG element parser for comprehensive testing"""
    
    def __init__(self, svg_content: str):
        """Initialize parser with SVG content"""
        self.svg_content = svg_content
        self.root = None
        self.namespaces = {'svg': 'http://www.w3.org/2000/svg'}
        self._parse()
    
    def _parse(self):
        """Parse SVG content with error handling"""
        try:
            # Register namespace to handle xmlns properly
            ET.register_namespace('', 'http://www.w3.org/2000/svg')
            self.root = ET.fromstring(self.svg_content)
        except ET.ParseError as e:
            self.root = None
            self.parse_error = str(e)
    
    def find_elements(self, element_name: str) -> List[ET.Element]:
        """Find all elements of given name"""
        if not self.root:
            return []
        
        # Search both with and without namespace
        elements = []
        elements.extend(self.root.findall(f'.//{element_name}'))
        elements.extend(self.root.findall(f'.//svg:{element_name}', self.namespaces))
        
        return elements
    
    def get_element_attributes(self, element: ET.Element) -> Dict[str, str]:
        """Extract all attributes from element"""
        return element.attrib.copy()
    
    def has_element(self, element_name: str) -> bool:
        """Check if SVG contains specific element"""
        return len(self.find_elements(element_name)) > 0
    
    def get_element_tree_info(self) -> Dict[str, Any]:
        """Get comprehensive information about SVG element tree"""
        if not self.root:
            return {'error': 'Failed to parse SVG'}
        
        def analyze_element(element):
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            info = {
                'tag': tag,
                'attributes': element.attrib.copy(),
                'text': element.text.strip() if element.text else None,
                'children_count': len(list(element)),
                'children': []
            }
            
            for child in element:
                info['children'].append(analyze_element(child))
            
            return info
        
        return {
            'root_tag': self.root.tag.split('}')[-1] if '}' in self.root.tag else self.root.tag,
            'root_attributes': self.root.attrib.copy(),
            'total_elements': len(list(self.root.iter())),
            'element_types': list(set(
                elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag 
                for elem in self.root.iter()
            )),
            'tree_structure': analyze_element(self.root)
        }
    
    def find_missing_elements(self) -> Dict[str, bool]:
        """Check for presence of all missing SVG elements"""
        missing_elements = [
            'polyline', 'tspan', 'image', 'symbol', 'use', 
            'pattern', 'feGaussianBlur', 'feDropShadow', 
            'defs', 'style'
        ]
        
        return {
            element: self.has_element(element) 
            for element in missing_elements
        }


class PPTXMockValidator:
    """Mock PPTX validator for testing conversion output"""
    
    def __init__(self):
        """Initialize mock validator"""
        self.expected_shapes = []
        self.validation_rules = {}
    
    def add_expected_shape(self, shape_type: str, properties: Dict[str, Any]):
        """Add expected shape for validation"""
        self.expected_shapes.append({
            'type': shape_type,
            'properties': properties
        })
    
    def validate_polyline_conversion(self, mock_pptx_data: Dict) -> bool:
        """Validate polyline to PPTX conversion"""
        required_properties = [
            'shape_type', 'path_data', 'stroke_properties'
        ]
        
        return all(prop in mock_pptx_data for prop in required_properties)
    
    def validate_image_conversion(self, mock_pptx_data: Dict) -> bool:
        """Validate image to PPTX conversion"""
        required_properties = [
            'shape_type', 'image_data', 'position', 'size'
        ]
        
        return all(prop in mock_pptx_data for prop in required_properties)
    
    def validate_filter_conversion(self, mock_pptx_data: Dict) -> bool:
        """Validate filter effect to PPTX conversion"""
        required_properties = [
            'shape_type', 'effect_properties'
        ]
        
        return all(prop in mock_pptx_data for prop in required_properties)
    
    def create_mock_pptx_output(self, element_type: str, svg_attributes: Dict) -> Dict[str, Any]:
        """Create mock PPTX output based on element type and attributes"""
        mock_outputs = {
            'polyline': {
                'shape_type': 'freeform',
                'path_data': svg_attributes.get('points', ''),
                'stroke_properties': {
                    'color': svg_attributes.get('stroke', 'black'),
                    'width': int(svg_attributes.get('stroke-width', '1'))
                },
                'fill_properties': {
                    'type': svg_attributes.get('fill', 'none')
                }
            },
            'image': {
                'shape_type': 'picture',
                'image_data': svg_attributes.get('href', ''),
                'position': {
                    'x': int(svg_attributes.get('x', '0')),
                    'y': int(svg_attributes.get('y', '0'))
                },
                'size': {
                    'width': int(svg_attributes.get('width', '100')),
                    'height': int(svg_attributes.get('height', '100'))
                }
            },
            'feDropShadow': {
                'shape_type': 'shape_with_effect',
                'effect_properties': {
                    'type': 'drop_shadow',
                    'offset_x': float(svg_attributes.get('dx', '2')),
                    'offset_y': float(svg_attributes.get('dy', '2')),
                    'blur_radius': float(svg_attributes.get('stdDeviation', '1')),
                    'color': svg_attributes.get('flood-color', 'black')
                }
            }
        }
        
        return mock_outputs.get(element_type, {})


class DataManager:
    """Manages test data files and directories"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize with base directory"""
        self.base_dir = base_dir or Path(tempfile.gettempdir()) / "svg2pptx_test_data"
        self.svg_samples_dir = self.base_dir / "svg_samples"
        self.expected_outputs_dir = self.base_dir / "expected_outputs"
        
    def setup_directories(self):
        """Create directory structure"""
        self.base_dir.mkdir(exist_ok=True)
        self.svg_samples_dir.mkdir(exist_ok=True)
        self.expected_outputs_dir.mkdir(exist_ok=True)
        
        return {
            'base': self.base_dir,
            'svg_samples': self.svg_samples_dir,
            'expected_outputs': self.expected_outputs_dir
        }
    
    def create_svg_sample(self, filename: str, svg_content: str) -> Path:
        """Create SVG sample file"""
        if not filename.endswith('.svg'):
            filename += '.svg'
        
        svg_file = self.svg_samples_dir / filename
        svg_file.write_text(svg_content, encoding='utf-8')
        return svg_file
    
    def create_expected_output(self, filename: str, expected_data: Dict) -> Path:
        """Create expected output JSON file"""
        if not filename.endswith('.json'):
            filename += '.json'
        
        output_file = self.expected_outputs_dir / filename
        output_file.write_text(json.dumps(expected_data, indent=2), encoding='utf-8')
        return output_file
    
    def load_svg_sample(self, filename: str) -> str:
        """Load SVG sample content"""
        if not filename.endswith('.svg'):
            filename += '.svg'
        
        svg_file = self.svg_samples_dir / filename
        if svg_file.exists():
            return svg_file.read_text(encoding='utf-8')
        return ""
    
    def load_expected_output(self, filename: str) -> Dict:
        """Load expected output data"""
        if not filename.endswith('.json'):
            filename += '.json'
        
        output_file = self.expected_outputs_dir / filename
        if output_file.exists():
            return json.loads(output_file.read_text(encoding='utf-8'))
        return {}
    
    def cleanup(self):
        """Clean up test data directories"""
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)


class PerformanceBenchmarker:
    """Performance benchmarking utilities for testing"""
    
    def __init__(self):
        """Initialize benchmarker"""
        self.benchmarks = {}
        self.thresholds = {
            'parsing_time': 0.1,  # 100ms for parsing
            'conversion_time': 0.5,  # 500ms for conversion
            'memory_usage': 50 * 1024 * 1024  # 50MB memory limit
        }
    
    def benchmark_svg_parsing(self, svg_content: str) -> Dict[str, float]:
        """Benchmark SVG parsing performance"""
        import time
        import psutil
        import os
        
        # Measure parsing time
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss
        
        parser = SVGElementParser(svg_content)
        element_info = parser.get_element_tree_info()
        
        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss
        
        return {
            'parsing_time': end_time - start_time,
            'memory_used': end_memory - start_memory,
            'elements_parsed': element_info.get('total_elements', 0),
            'elements_per_second': element_info.get('total_elements', 0) / max(end_time - start_time, 0.001)
        }
    
    def validate_performance_thresholds(self, benchmark_results: Dict[str, float]) -> Dict[str, bool]:
        """Validate that performance meets thresholds"""
        validation_results = {}
        
        for metric, threshold in self.thresholds.items():
            if metric in benchmark_results:
                validation_results[metric] = benchmark_results[metric] <= threshold
        
        return validation_results


# Test Fixture Functions
def create_mock_converter(element_name: str, should_succeed: bool = True) -> Mock:
    """Create mock converter for specific element"""
    mock_converter = Mock()
    mock_converter.element_name = element_name
    mock_converter.supports_element.return_value = True
    
    if should_succeed:
        mock_converter.convert.return_value = f"<mock_pptx_output_for_{element_name}>"
    else:
        mock_converter.convert.side_effect = Exception(f"Conversion failed for {element_name}")
    
    return mock_converter


def create_comprehensive_test_suite():
    """Create comprehensive test suite with all utilities"""
    return {
        'parser': SVGElementParser,
        'validator': PPTXMockValidator,
        'data_manager': DataManager,
        'benchmarker': PerformanceBenchmarker,
        'mock_creator': create_mock_converter
    }


# Integration Test Helpers
def run_missing_element_detection_test(svg_content: str) -> Dict[str, Any]:
    """Run comprehensive missing element detection test"""
    parser = SVGElementParser(svg_content)
    
    return {
        'parsing_successful': parser.root is not None,
        'missing_elements_found': parser.find_missing_elements(),
        'element_tree_info': parser.get_element_tree_info(),
        'total_missing_elements': sum(parser.find_missing_elements().values())
    }


def simulate_conversion_pipeline(svg_content: str, target_elements: List[str]) -> Dict[str, Any]:
    """Simulate full conversion pipeline for testing"""
    parser = SVGElementParser(svg_content)
    validator = PPTXMockValidator()
    
    results = {
        'parsing_results': run_missing_element_detection_test(svg_content),
        'conversion_results': {},
        'validation_results': {}
    }
    
    for element_name in target_elements:
        elements = parser.find_elements(element_name)
        if elements:
            for i, element in enumerate(elements):
                mock_output = validator.create_mock_pptx_output(
                    element_name, 
                    parser.get_element_attributes(element)
                )
                
                results['conversion_results'][f'{element_name}_{i}'] = mock_output
                
                # Validate based on element type
                if element_name == 'polyline':
                    results['validation_results'][f'{element_name}_{i}'] = validator.validate_polyline_conversion(mock_output)
                elif element_name == 'image':
                    results['validation_results'][f'{element_name}_{i}'] = validator.validate_image_conversion(mock_output)
                elif element_name in ['feGaussianBlur', 'feDropShadow']:
                    results['validation_results'][f'{element_name}_{i}'] = validator.validate_filter_conversion(mock_output)
    
    return results


# Content Comparison Helper Functions
class ContentComparisonHelpers:
    """Helper functions for comparing expected vs actual test content"""
    
    @staticmethod
    def compare_svg_elements(expected: ET.Element, actual: ET.Element, tolerance: float = 0.1) -> Dict[str, Any]:
        """Compare two SVG elements with tolerance for numeric values"""
        comparison_result = {
            'tags_match': expected.tag == actual.tag,
            'attribute_differences': {},
            'text_matches': True,
            'children_count_matches': len(list(expected)) == len(list(actual)),
            'overall_match': True
        }
        
        # Compare attributes with numeric tolerance
        expected_attrs = expected.attrib
        actual_attrs = actual.attrib
        
        all_attrs = set(expected_attrs.keys()) | set(actual_attrs.keys())
        
        for attr in all_attrs:
            expected_val = expected_attrs.get(attr)
            actual_val = actual_attrs.get(attr)
            
            if expected_val != actual_val:
                # Try numeric comparison with tolerance
                try:
                    exp_num = float(expected_val) if expected_val else 0
                    act_num = float(actual_val) if actual_val else 0
                    
                    if abs(exp_num - act_num) <= tolerance:
                        comparison_result['attribute_differences'][attr] = {
                            'status': 'within_tolerance',
                            'expected': expected_val,
                            'actual': actual_val,
                            'difference': abs(exp_num - act_num)
                        }
                    else:
                        comparison_result['attribute_differences'][attr] = {
                            'status': 'mismatch',
                            'expected': expected_val,
                            'actual': actual_val
                        }
                        comparison_result['overall_match'] = False
                except (ValueError, TypeError):
                    # Non-numeric comparison
                    comparison_result['attribute_differences'][attr] = {
                        'status': 'mismatch',
                        'expected': expected_val,
                        'actual': actual_val
                    }
                    comparison_result['overall_match'] = False
        
        # Compare text content
        expected_text = (expected.text or '').strip()
        actual_text = (actual.text or '').strip()
        comparison_result['text_matches'] = expected_text == actual_text
        
        if not comparison_result['text_matches']:
            comparison_result['overall_match'] = False
        
        return comparison_result
    
    @staticmethod
    def compare_pptx_shapes(expected: Dict[str, Any], actual: Dict[str, Any], tolerance: float = 1.0) -> Dict[str, Any]:
        """Compare expected vs actual PPTX shape data with tolerance"""
        comparison_result = {
            'shape_type_matches': expected.get('shape_type') == actual.get('shape_type'),
            'position_differences': {},
            'size_differences': {},
            'style_differences': {},
            'overall_match': True
        }
        
        # Compare position with tolerance
        exp_pos = expected.get('position', {})
        act_pos = actual.get('position', {})
        
        for coord in ['x', 'y']:
            exp_val = exp_pos.get(coord, 0)
            act_val = act_pos.get(coord, 0)
            diff = abs(exp_val - act_val)
            
            comparison_result['position_differences'][coord] = {
                'expected': exp_val,
                'actual': act_val,
                'difference': diff,
                'within_tolerance': diff <= tolerance
            }
            
            if diff > tolerance:
                comparison_result['overall_match'] = False
        
        # Compare size with tolerance
        exp_size = expected.get('size', {})
        act_size = actual.get('size', {})
        
        for dimension in ['width', 'height']:
            exp_val = exp_size.get(dimension, 0)
            act_val = act_size.get(dimension, 0)
            diff = abs(exp_val - act_val)
            
            comparison_result['size_differences'][dimension] = {
                'expected': exp_val,
                'actual': act_val,
                'difference': diff,
                'within_tolerance': diff <= tolerance
            }
            
            if diff > tolerance:
                comparison_result['overall_match'] = False
        
        # Compare style properties
        style_properties = ['stroke', 'fill', 'effects', 'text_runs']
        for prop in style_properties:
            exp_val = expected.get(prop)
            act_val = actual.get(prop)
            
            if exp_val != act_val:
                comparison_result['style_differences'][prop] = {
                    'expected': exp_val,
                    'actual': act_val,
                    'matches': exp_val == act_val
                }
                if exp_val != act_val:
                    comparison_result['overall_match'] = False
        
        return comparison_result
    
    @staticmethod
    def generate_comparison_report(comparisons: List[Dict[str, Any]], test_name: str) -> str:
        """Generate human-readable comparison report"""
        report = [f"=== Comparison Report: {test_name} ===\n"]
        
        total_comparisons = len(comparisons)
        passed_comparisons = sum(1 for comp in comparisons if comp.get('overall_match', False))
        
        report.append(f"Total Comparisons: {total_comparisons}")
        report.append(f"Passed: {passed_comparisons}")
        report.append(f"Failed: {total_comparisons - passed_comparisons}")
        report.append(f"Success Rate: {(passed_comparisons/total_comparisons*100):.1f}%\n")
        
        # Detailed results
        for i, comparison in enumerate(comparisons):
            status = "✅ PASS" if comparison.get('overall_match', False) else "❌ FAIL"
            report.append(f"Comparison {i+1}: {status}")
            
            if not comparison.get('overall_match', False):
                # Add failure details
                if 'attribute_differences' in comparison:
                    for attr, diff in comparison['attribute_differences'].items():
                        if diff['status'] == 'mismatch':
                            report.append(f"  - Attribute '{attr}': expected '{diff['expected']}', got '{diff['actual']}'")
                
                if 'position_differences' in comparison:
                    for coord, diff in comparison['position_differences'].items():
                        if not diff['within_tolerance']:
                            report.append(f"  - Position {coord}: expected {diff['expected']}, got {diff['actual']} (diff: {diff['difference']:.2f})")
                
                if 'style_differences' in comparison:
                    for prop, diff in comparison['style_differences'].items():
                        if not diff['matches']:
                            report.append(f"  - Style {prop}: expected {diff['expected']}, got {diff['actual']}")
            
            report.append("")
        
        return "\n".join(report)
    
    @staticmethod
    def create_test_assertion_data(comparison_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create structured data for test assertions"""
        return {
            'passed': comparison_result.get('overall_match', False),
            'failures': [],
            'warnings': [],
            'details': comparison_result
        }


class TestExecutionHelpers:
    """Helper functions for test execution and result processing"""
    
    @staticmethod
    def run_element_conversion_test(svg_content: str, element_name: str, expected_fixture: Any) -> Dict[str, Any]:
        """Run conversion test for specific element"""
        parser = SVGElementParser(svg_content)
        elements = parser.find_elements(element_name)
        
        if not elements:
            return {
                'success': False,
                'error': f'No {element_name} elements found in SVG',
                'element_count': 0
            }
        
        # Mock conversion (since actual converters don't exist yet)
        validator = PPTXMockValidator()
        mock_results = []
        
        for element in elements:
            attrs = parser.get_element_attributes(element)
            mock_output = validator.create_mock_pptx_output(element_name, attrs)
            mock_results.append(mock_output)
        
        # Compare with expected fixture
        comparisons = []
        if isinstance(expected_fixture, list):
            for i, (expected, actual) in enumerate(zip(expected_fixture, mock_results)):
                comparison = ContentComparisonHelpers.compare_pptx_shapes(
                    expected.__dict__ if hasattr(expected, '__dict__') else expected,
                    actual
                )
                comparisons.append(comparison)
        else:
            if mock_results:
                comparison = ContentComparisonHelpers.compare_pptx_shapes(
                    expected_fixture.__dict__ if hasattr(expected_fixture, '__dict__') else expected_fixture,
                    mock_results[0]
                )
                comparisons.append(comparison)
        
        return {
            'success': True,
            'element_count': len(elements),
            'comparisons': comparisons,
            'overall_success': all(comp.get('overall_match', False) for comp in comparisons)
        }
    
    @staticmethod
    def create_test_summary(test_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Create summary of multiple test results"""
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result.get('overall_success', False))
        
        element_coverage = {}
        for element_name, result in test_results.items():
            element_coverage[element_name] = {
                'tested': result.get('success', False),
                'passed': result.get('overall_success', False),
                'element_count': result.get('element_count', 0)
            }
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'element_coverage': element_coverage
        }


if __name__ == "__main__":
    # Demonstrate utility functions
    sample_svg = '''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
        <polyline points="10,10 50,25 90,10" stroke="blue" stroke-width="2" fill="none"/>
        <image x="10" y="10" width="100" height="80" href="test.jpg"/>
    </svg>
    '''
    
    result = run_missing_element_detection_test(sample_svg)
    print("Missing element detection test:", result)
    
    pipeline_result = simulate_conversion_pipeline(sample_svg, ['polyline', 'image'])
    print("Conversion pipeline simulation:", pipeline_result)
    
    # Demonstrate comparison helpers
    helpers = ContentComparisonHelpers()
    test_helpers = TestExecutionHelpers()
    
    # Mock comparison example
    expected = {'shape_type': 'freeform', 'position': {'x': 10, 'y': 10}}
    actual = {'shape_type': 'freeform', 'position': {'x': 11, 'y': 9}}
    
    comparison = helpers.compare_pptx_shapes(expected, actual, tolerance=2.0)
    print("Comparison example:", comparison)
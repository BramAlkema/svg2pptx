#!/usr/bin/env python3
"""
Comprehensive Kitchen Sink Debug System for SVG2PPTX
=====================================================

This system provides exhaustive debugging for ALL conversion pathways:
- Shapes (rect, circle, ellipse, line, polygon, polyline)
- Paths (simple, complex, curves, arcs)
- Text (positioning, fonts, sizing)
- Transforms (matrix, translate, scale, rotate)
- Gradients (linear, radial)
- Filters and effects
- Coordinate transformations
- Viewport mapping
- Service dependencies
- Converter registry
"""

import sys
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional
import traceback
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

class ComprehensiveDebugSystem:
    """Kitchen sink debug system for complete SVG2PPTX analysis."""

    def __init__(self):
        self.debug_data = {
            'timestamp': datetime.now().isoformat(),
            'svg_analysis': {},
            'conversion_analysis': {},
            'pptx_analysis': {},
            'coordinate_analysis': {},
            'service_analysis': {},
            'error_analysis': {},
            'performance_analysis': {},
            'recommendations': []
        }

    def analyze_svg_completely(self, svg_file: str) -> Dict[str, Any]:
        """Complete SVG analysis - every element, attribute, and structure."""
        print("🔍 COMPLETE SVG ANALYSIS")
        print("=" * 50)

        with open(svg_file, 'r') as f:
            svg_content = f.read()

        svg_root = ET.fromstring(svg_content.encode('utf-8'))

        analysis = {
            'file_info': {
                'filename': svg_file,
                'size_bytes': len(svg_content),
                'line_count': len(svg_content.split('\n'))
            },
            'root_attributes': dict(svg_root.attrib),
            'elements_by_type': {},
            'coordinate_systems': {},
            'style_analysis': {},
            'transform_analysis': {},
            'gradient_analysis': {},
            'text_analysis': {},
            'path_analysis': {},
            'shape_analysis': {},
            'namespace_analysis': {}
        }

        # Analyze all elements by type
        all_elements = svg_root.iter()
        for elem in all_elements:
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

            if tag not in analysis['elements_by_type']:
                analysis['elements_by_type'][tag] = []

            elem_data = {
                'tag': tag,
                'attributes': dict(elem.attrib),
                'text_content': elem.text.strip() if elem.text else None,
                'children_count': len(list(elem)),
                'namespace': elem.tag.split('}')[0] if '}' in elem.tag else None
            }
            analysis['elements_by_type'][tag].append(elem_data)

        # Coordinate system analysis
        viewbox = svg_root.get('viewBox', '')
        width = svg_root.get('width', '')
        height = svg_root.get('height', '')

        analysis['coordinate_systems'] = {
            'viewBox': viewbox,
            'width': width,
            'height': height,
            'viewBox_parsed': self._parse_viewbox(viewbox),
            'implicit_dimensions': self._get_implicit_dimensions(width, height)
        }

        # Shape analysis with positioning
        for shape_type in ['rect', 'circle', 'ellipse', 'line', 'polygon', 'polyline']:
            shapes = svg_root.findall(f'.//{shape_type}')
            if shapes:
                analysis['shape_analysis'][shape_type] = []
                for i, shape in enumerate(shapes):
                    shape_data = {
                        'index': i,
                        'attributes': dict(shape.attrib),
                        'computed_bounds': self._compute_shape_bounds(shape),
                        'style_properties': self._parse_style_attribute(shape.get('style', '')),
                        'transforms': self._extract_transforms(shape)
                    }
                    analysis['shape_analysis'][shape_type].append(shape_data)

        # Path analysis
        paths = svg_root.findall('.//path')
        if paths:
            analysis['path_analysis'] = []
            for i, path in enumerate(paths):
                path_data = {
                    'index': i,
                    'attributes': dict(path.attrib),
                    'd_attribute': path.get('d', ''),
                    'path_commands': self._parse_path_commands(path.get('d', '')),
                    'computed_bounds': self._compute_path_bounds(path.get('d', '')),
                    'style_properties': self._parse_style_attribute(path.get('style', '')),
                    'transforms': self._extract_transforms(path)
                }
                analysis['path_analysis'].append(path_data)

        # Text analysis
        texts = svg_root.findall('.//text')
        if texts:
            analysis['text_analysis'] = []
            for i, text in enumerate(texts):
                text_data = {
                    'index': i,
                    'attributes': dict(text.attrib),
                    'text_content': text.text or '',
                    'position': {
                        'x': text.get('x', '0'),
                        'y': text.get('y', '0')
                    },
                    'font_properties': {
                        'family': text.get('font-family', ''),
                        'size': text.get('font-size', ''),
                        'weight': text.get('font-weight', ''),
                        'style': text.get('font-style', '')
                    },
                    'style_properties': self._parse_style_attribute(text.get('style', '')),
                    'transforms': self._extract_transforms(text),
                    'text_anchor': text.get('text-anchor', 'start')
                }
                analysis['text_analysis'].append(text_data)

        # Gradient analysis
        gradients = svg_root.findall('.//linearGradient') + svg_root.findall('.//radialGradient')
        if gradients:
            analysis['gradient_analysis'] = []
            for i, grad in enumerate(gradients):
                grad_data = {
                    'index': i,
                    'type': grad.tag.split('}')[-1],
                    'id': grad.get('id', ''),
                    'attributes': dict(grad.attrib),
                    'stops': []
                }

                stops = grad.findall('.//stop')
                for stop in stops:
                    stop_data = {
                        'offset': stop.get('offset', ''),
                        'color': stop.get('stop-color', ''),
                        'opacity': stop.get('stop-opacity', ''),
                        'style': stop.get('style', '')
                    }
                    grad_data['stops'].append(stop_data)

                analysis['gradient_analysis'].append(grad_data)

        self.debug_data['svg_analysis'] = analysis

        # Print summary
        print(f"📄 SVG File: {svg_file}")
        print(f"📐 ViewBox: {viewbox}")
        print(f"📏 Dimensions: {width} x {height}")
        print(f"🔢 Total Elements: {sum(len(elems) for elems in analysis['elements_by_type'].values())}")
        print(f"📝 Element Types: {list(analysis['elements_by_type'].keys())}")

        for elem_type, elems in analysis['elements_by_type'].items():
            if elem_type in ['rect', 'circle', 'ellipse', 'line', 'polygon', 'polyline', 'path', 'text']:
                print(f"   {elem_type}: {len(elems)} elements")

        return analysis

    def debug_conversion_process(self, svg_file: str, output_file: str) -> Dict[str, Any]:
        """Debug the complete conversion process with detailed logging."""
        print("\n🔧 CONVERSION PROCESS DEBUG")
        print("=" * 50)

        conversion_debug = {
            'input_file': svg_file,
            'output_file': output_file,
            'services_debug': {},
            'converter_debug': {},
            'coordinate_debug': {},
            'viewport_debug': {},
            'registry_debug': {},
            'errors': [],
            'warnings': [],
            'performance': {}
        }

        try:
            # Import and debug services
            from core.services.conversion_services import ConversionServices
            from src.svg2pptx import convert_svg_to_pptx

            print("🔨 Creating ConversionServices...")
            services = ConversionServices.create_default()

            # Debug services
            conversion_debug['services_debug'] = {
                'unit_converter': str(type(services.unit_converter)),
                'viewport_handler': str(type(getattr(services, 'viewport_handler', None))),
                'font_service': str(type(getattr(services, 'font_service', None))),
                'gradient_service': str(type(getattr(services, 'gradient_service', None))),
                'pattern_service': str(type(getattr(services, 'pattern_service', None))),
                'clip_service': str(type(getattr(services, 'clip_service', None))),
                'style_parser': str(type(getattr(services, 'style_parser', None))),
                'font_processor': str(type(getattr(services, 'font_processor', None)))
            }

            print("🔄 Starting conversion process...")

            # Debug viewport mapping
            print("🗺️  Analyzing viewport mapping...")
            with open(svg_file, 'r') as f:
                svg_content = f.read()

            svg_root = ET.fromstring(svg_content.encode('utf-8'))

            from core.viewbox.core import ViewportEngine

            STANDARD_SLIDE_WIDTH_EMU = 9144000   # 10 inches
            STANDARD_SLIDE_HEIGHT_EMU = 6858000  # 7.5 inches

            viewport_mapping = (ViewportEngine(services.unit_converter)
                               .for_svg(svg_root)
                               .with_slide_size(STANDARD_SLIDE_WIDTH_EMU, STANDARD_SLIDE_HEIGHT_EMU)
                               .top_left()
                               .meet()
                               .resolve_single())

            conversion_debug['viewport_debug'] = {
                'scale_x': float(viewport_mapping['scale_x']),
                'scale_y': float(viewport_mapping['scale_y']),
                'translate_x': float(viewport_mapping['translate_x']),
                'translate_y': float(viewport_mapping['translate_y']),
                'viewport_width': int(viewport_mapping['viewport_width']),
                'viewport_height': int(viewport_mapping['viewport_height']),
                'content_width': int(viewport_mapping['content_width']),
                'content_height': int(viewport_mapping['content_height'])
            }

            # Test coordinate transformation
            test_coordinates = [
                (0, 0, 'Origin'),
                (200, 150, 'Center'),
                (400, 300, 'Max'),
                (50, 50, 'Rectangle'),
                (85, 130, 'Circle'),
                (190, 70, 'Ellipse')
            ]

            conversion_debug['coordinate_debug'] = []
            for svg_x, svg_y, desc in test_coordinates:
                emu_x = int(svg_x * viewport_mapping['scale_x'] + viewport_mapping['translate_x'])
                emu_y = int(svg_y * viewport_mapping['scale_y'] + viewport_mapping['translate_y'])
                inch_x = emu_x / 914400
                inch_y = emu_y / 914400

                coord_data = {
                    'description': desc,
                    'svg_coordinates': [svg_x, svg_y],
                    'emu_coordinates': [emu_x, emu_y],
                    'inch_coordinates': [round(inch_x, 3), round(inch_y, 3)]
                }
                conversion_debug['coordinate_debug'].append(coord_data)

            # Perform conversion
            print("✨ Converting SVG to PPTX...")
            import time
            start_time = time.time()

            result = convert_svg_to_pptx(svg_file, output_file)

            end_time = time.time()
            conversion_debug['performance'] = {
                'conversion_time_seconds': round(end_time - start_time, 3),
                'output_file_size': Path(output_file).stat().st_size if Path(output_file).exists() else 0
            }

            print(f"✅ Conversion completed in {conversion_debug['performance']['conversion_time_seconds']}s")
            print(f"📦 Output file size: {conversion_debug['performance']['output_file_size']} bytes")

        except Exception as e:
            error_data = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'traceback': traceback.format_exc()
            }
            conversion_debug['errors'].append(error_data)
            print(f"❌ Conversion error: {e}")
            traceback.print_exc()

        self.debug_data['conversion_analysis'] = conversion_debug
        return conversion_debug

    def analyze_pptx_output(self, pptx_file: str) -> Dict[str, Any]:
        """Complete PPTX analysis - every shape, position, property."""
        print("\n📊 COMPLETE PPTX ANALYSIS")
        print("=" * 50)

        analysis = {
            'file_info': {
                'filename': pptx_file,
                'file_size': Path(pptx_file).stat().st_size if Path(pptx_file).exists() else 0
            },
            'structure_analysis': {},
            'shape_analysis': {},
            'text_analysis': {},
            'coordinate_analysis': {},
            'style_analysis': {},
            'content_validation': {}
        }

        try:
            with zipfile.ZipFile(pptx_file, 'r') as zip_file:
                # Analyze PPTX structure
                file_list = zip_file.namelist()
                analysis['structure_analysis'] = {
                    'total_files': len(file_list),
                    'slides': [f for f in file_list if f.startswith('ppt/slides/slide')],
                    'relationships': [f for f in file_list if f.endswith('.rels')],
                    'media': [f for f in file_list if f.startswith('ppt/media/')],
                    'theme': [f for f in file_list if f.startswith('ppt/theme/')]
                }

                # Analyze slide content
                slide_xml = zip_file.read('ppt/slides/slide1.xml').decode('utf-8')

                root = ET.fromstring(slide_xml)
                namespaces = {
                    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
                    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
                }

                # Find all shapes
                shapes = root.findall('.//p:sp', namespaces)

                analysis['shape_analysis'] = {
                    'total_shapes': len(shapes),
                    'shapes': []
                }

                analysis['text_analysis'] = {
                    'total_text_shapes': 0,
                    'text_shapes': []
                }

                analysis['coordinate_analysis'] = {
                    'coordinate_ranges': {},
                    'positioning_data': []
                }

                # Analyze each shape in detail
                for i, shape in enumerate(shapes):
                    shape_data = self._analyze_pptx_shape(shape, namespaces, i)
                    analysis['shape_analysis']['shapes'].append(shape_data)

                    # Collect coordinate data
                    if 'positioning' in shape_data:
                        pos_data = {
                            'shape_index': i,
                            'shape_name': shape_data.get('name', f'Shape {i+1}'),
                            'x_emu': shape_data['positioning']['x_emu'],
                            'y_emu': shape_data['positioning']['y_emu'],
                            'x_inches': shape_data['positioning']['x_inches'],
                            'y_inches': shape_data['positioning']['y_inches'],
                            'width_emu': shape_data['positioning']['width_emu'],
                            'height_emu': shape_data['positioning']['height_emu']
                        }
                        analysis['coordinate_analysis']['positioning_data'].append(pos_data)

                    # Collect text data
                    if shape_data.get('is_text_shape'):
                        analysis['text_analysis']['total_text_shapes'] += 1
                        text_data = {
                            'shape_index': i,
                            'text_content': shape_data.get('text_content', ''),
                            'font_properties': shape_data.get('font_properties', {}),
                            'positioning': shape_data.get('positioning', {})
                        }
                        analysis['text_analysis']['text_shapes'].append(text_data)

                # Calculate coordinate ranges
                if analysis['coordinate_analysis']['positioning_data']:
                    x_coords = [pos['x_inches'] for pos in analysis['coordinate_analysis']['positioning_data']]
                    y_coords = [pos['y_inches'] for pos in analysis['coordinate_analysis']['positioning_data']]

                    analysis['coordinate_analysis']['coordinate_ranges'] = {
                        'x_min': min(x_coords),
                        'x_max': max(x_coords),
                        'y_min': min(y_coords),
                        'y_max': max(y_coords),
                        'slide_usage_x': max(x_coords) - min(x_coords),
                        'slide_usage_y': max(y_coords) - min(y_coords)
                    }

        except Exception as e:
            analysis['error'] = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'traceback': traceback.format_exc()
            }
            print(f"❌ PPTX analysis error: {e}")

        self.debug_data['pptx_analysis'] = analysis

        # Print summary
        print(f"📦 PPTX File: {pptx_file}")
        print(f"📏 File size: {analysis['file_info']['file_size']} bytes")

        if 'error' not in analysis:
            print(f"🔢 Total shapes: {analysis['shape_analysis']['total_shapes']}")
            print(f"📝 Text shapes: {analysis['text_analysis']['total_text_shapes']}")
        else:
            print("❌ PPTX analysis failed - file may not have been created")

        if analysis['coordinate_analysis']['coordinate_ranges']:
            ranges = analysis['coordinate_analysis']['coordinate_ranges']
            print(f"📐 Coordinate ranges:")
            print(f"   X: {ranges['x_min']:.2f}\" to {ranges['x_max']:.2f}\" (span: {ranges['slide_usage_x']:.2f}\")")
            print(f"   Y: {ranges['y_min']:.2f}\" to {ranges['y_max']:.2f}\" (span: {ranges['slide_usage_y']:.2f}\")")

        return analysis

    def _analyze_pptx_shape(self, shape: ET.Element, namespaces: Dict[str, str], index: int) -> Dict[str, Any]:
        """Detailed analysis of a single PPTX shape."""
        shape_data = {
            'index': index,
            'is_text_shape': False,
            'geometry_type': None,
            'positioning': {},
            'styling': {},
            'content': {}
        }

        # Get shape name
        name_elem = shape.find('.//p:cNvPr', namespaces)
        if name_elem is not None:
            shape_data['name'] = name_elem.get('name', f'Shape {index+1}')
            shape_data['id'] = name_elem.get('id', '')

        # Get positioning
        xfrm = shape.find('.//a:xfrm', namespaces)
        if xfrm is not None:
            off = xfrm.find('a:off', namespaces)
            ext = xfrm.find('a:ext', namespaces)

            if off is not None and ext is not None:
                x_emu = int(off.get('x', 0))
                y_emu = int(off.get('y', 0))
                w_emu = int(ext.get('cx', 0))
                h_emu = int(ext.get('cy', 0))

                shape_data['positioning'] = {
                    'x_emu': x_emu,
                    'y_emu': y_emu,
                    'width_emu': w_emu,
                    'height_emu': h_emu,
                    'x_inches': round(x_emu / 914400, 3),
                    'y_inches': round(y_emu / 914400, 3),
                    'width_inches': round(w_emu / 914400, 3),
                    'height_inches': round(h_emu / 914400, 3)
                }

        # Check geometry type
        preset_geom = shape.find('.//a:prstGeom', namespaces)
        custom_geom = shape.find('.//a:custGeom', namespaces)

        if preset_geom is not None:
            shape_data['geometry_type'] = 'preset'
            shape_data['geometry_preset'] = preset_geom.get('prst', '')
        elif custom_geom is not None:
            shape_data['geometry_type'] = 'custom'
            # Analyze custom geometry paths
            path_list = custom_geom.find('.//a:pathLst', namespaces)
            if path_list is not None:
                paths = path_list.findall('.//a:path', namespaces)
                shape_data['custom_paths'] = len(paths)

        # Check if text shape
        txBody = shape.find('.//p:txBody', namespaces)
        if txBody is not None:
            shape_data['is_text_shape'] = True

            # Get text content
            text_runs = txBody.findall('.//a:t', namespaces)
            text_content = ''.join([run.text or '' for run in text_runs])
            shape_data['text_content'] = text_content

            # Get font properties
            rPr = txBody.find('.//a:rPr', namespaces)
            if rPr is not None:
                shape_data['font_properties'] = {
                    'size_pts': int(rPr.get('sz', '1200')) / 100 if rPr.get('sz') else None,
                    'bold': rPr.get('b') == '1',
                    'italic': rPr.get('i') == '1',
                    'lang': rPr.get('lang', ''),
                }

                # Get font typeface
                latin = rPr.find('.//a:latin', namespaces)
                if latin is not None:
                    shape_data['font_properties']['typeface'] = latin.get('typeface', '')

        return shape_data

    def compare_svg_to_pptx(self) -> Dict[str, Any]:
        """Compare SVG input to PPTX output for accuracy analysis."""
        print("\n🔍 SVG ↔ PPTX COMPARISON")
        print("=" * 50)

        comparison = {
            'element_mapping': [],
            'coordinate_accuracy': [],
            'text_accuracy': [],
            'style_preservation': [],
            'overall_fidelity': {}
        }

        svg_analysis = self.debug_data.get('svg_analysis', {})
        pptx_analysis = self.debug_data.get('pptx_analysis', {})

        if not svg_analysis or not pptx_analysis:
            print("❌ Missing SVG or PPTX analysis data")
            return comparison

        # Compare text elements
        svg_texts = svg_analysis.get('text_analysis', [])
        pptx_texts = pptx_analysis.get('text_analysis', {}).get('text_shapes', [])

        print(f"📝 Comparing {len(svg_texts)} SVG texts to {len(pptx_texts)} PPTX texts")

        for i, svg_text in enumerate(svg_texts):
            if i < len(pptx_texts):
                pptx_text = pptx_texts[i]

                # Compare positions
                svg_x = float(svg_text['position']['x']) if svg_text['position']['x'] else 0
                svg_y = float(svg_text['position']['y']) if svg_text['position']['y'] else 0

                pptx_x = pptx_text['positioning']['x_inches']
                pptx_y = pptx_text['positioning']['y_inches']

                # Convert SVG to expected PPTX coordinates
                expected_pptx_x = (svg_x / 400) * 10.0  # Assuming 400px SVG -> 10" slide
                expected_pptx_y = (svg_y / 300) * 7.5   # Assuming 300px SVG -> 7.5" slide

                x_error = abs(pptx_x - expected_pptx_x)
                y_error = abs(pptx_y - expected_pptx_y)

                text_comparison = {
                    'svg_index': i,
                    'svg_text': svg_text['text_content'],
                    'pptx_text': pptx_text['text_content'],
                    'svg_position': [svg_x, svg_y],
                    'expected_pptx_position': [expected_pptx_x, expected_pptx_y],
                    'actual_pptx_position': [pptx_x, pptx_y],
                    'position_error': [x_error, y_error],
                    'position_accuracy': 'good' if (x_error < 0.5 and y_error < 0.5) else 'poor'
                }

                comparison['text_accuracy'].append(text_comparison)

                print(f"  Text {i+1}: '{svg_text['text_content'][:20]}...'")
                print(f"    Position accuracy: {text_comparison['position_accuracy']}")
                print(f"    Error: ({x_error:.2f}, {y_error:.2f}) inches")

        # Calculate overall fidelity metrics
        if comparison['text_accuracy']:
            good_positions = sum(1 for t in comparison['text_accuracy'] if t['position_accuracy'] == 'good')
            total_positions = len(comparison['text_accuracy'])

            comparison['overall_fidelity'] = {
                'text_position_accuracy': round((good_positions / total_positions) * 100, 1),
                'total_text_elements': total_positions,
                'correctly_positioned': good_positions
            }

            print(f"\n📊 Overall Fidelity:")
            print(f"   Text position accuracy: {comparison['overall_fidelity']['text_position_accuracy']}%")
            print(f"   Correctly positioned: {good_positions}/{total_positions}")

        self.debug_data['comparison_analysis'] = comparison
        return comparison

    def generate_recommendations(self) -> List[str]:
        """Generate specific recommendations based on analysis."""
        recommendations = []

        svg_analysis = self.debug_data.get('svg_analysis', {})
        pptx_analysis = self.debug_data.get('pptx_analysis', {})
        comparison = self.debug_data.get('comparison_analysis', {})
        conversion = self.debug_data.get('conversion_analysis', {})

        # Check for coordinate issues
        if comparison.get('overall_fidelity', {}).get('text_position_accuracy', 0) < 80:
            recommendations.append("🎯 CRITICAL: Text positioning accuracy is below 80%. Check viewport mapping and coordinate transformation.")

        # Check for missing viewport mapping
        if conversion.get('errors'):
            for error in conversion['errors']:
                if 'viewport_mapping' in error['error_message']:
                    recommendations.append("🗺️ Fix viewport mapping propagation to all converters.")

        # Check for font size issues
        pptx_texts = pptx_analysis.get('text_analysis', {}).get('text_shapes', [])
        small_fonts = [t for t in pptx_texts if t.get('font_properties', {}).get('size_pts', 0) < 18]
        if small_fonts:
            recommendations.append(f"📝 {len(small_fonts)} text elements have fonts smaller than 18pt. Consider boosting for readability.")

        # Check for coordinate range issues
        coord_ranges = pptx_analysis.get('coordinate_analysis', {}).get('coordinate_ranges', {})
        if coord_ranges:
            if coord_ranges.get('x_min', 0) < -1:
                recommendations.append("📐 Some elements are positioned outside the left slide boundary.")
            if coord_ranges.get('y_min', 0) < -1:
                recommendations.append("📐 Some elements are positioned outside the top slide boundary.")

        # Check for service issues
        services_debug = conversion.get('services_debug', {})
        for service_name, service_type in services_debug.items():
            if 'None' in service_type:
                recommendations.append(f"🔧 {service_name} is not properly initialized.")

        self.debug_data['recommendations'] = recommendations
        return recommendations

    def save_debug_report(self, output_file: str = "comprehensive_debug_report.json"):
        """Save complete debug report to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(self.debug_data, f, indent=2, default=str)

        print(f"\n💾 Debug report saved to: {output_file}")
        return output_file

    def generate_html_report(self, output_file: str = "comprehensive_debug_report.html"):
        """Generate HTML report with visual analysis."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SVG2PPTX Comprehensive Debug Report</title>
    <style>
        body {{ font-family: 'Courier New', monospace; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; background: #f9f9f9; }}
        .error {{ border-left-color: #ff4444; background: #fff5f5; }}
        .success {{ border-left-color: #44ff44; background: #f5fff5; }}
        .warning {{ border-left-color: #ffaa00; background: #fffaf0; }}
        .code {{ background: #f0f0f0; padding: 10px; border-radius: 4px; overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #007acc; color: white; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #e7f3ff; border-radius: 4px; }}
        .recommendations {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 SVG2PPTX Comprehensive Debug Report</h1>
        <p><strong>Generated:</strong> {self.debug_data['timestamp']}</p>

        <div class="section">
            <h2>📄 SVG Analysis Summary</h2>
            {self._generate_svg_summary_html()}
        </div>

        <div class="section">
            <h2>🔧 Conversion Analysis</h2>
            {self._generate_conversion_summary_html()}
        </div>

        <div class="section">
            <h2>📊 PPTX Analysis Summary</h2>
            {self._generate_pptx_summary_html()}
        </div>

        <div class="section">
            <h2>🎯 Accuracy Comparison</h2>
            {self._generate_comparison_html()}
        </div>

        <div class="section recommendations">
            <h2>💡 Recommendations</h2>
            {self._generate_recommendations_html()}
        </div>

        <div class="section">
            <h2>📋 Raw Debug Data</h2>
            <div class="code">
                <pre>{json.dumps(self.debug_data, indent=2, default=str)}</pre>
            </div>
        </div>
    </div>
</body>
</html>
"""

        with open(output_file, 'w') as f:
            f.write(html_content)

        print(f"📊 HTML report generated: {output_file}")
        return output_file

    def _generate_svg_summary_html(self) -> str:
        svg_analysis = self.debug_data.get('svg_analysis', {})
        if not svg_analysis:
            return "<p>No SVG analysis data available.</p>"

        elements = svg_analysis.get('elements_by_type', {})
        coord_system = svg_analysis.get('coordinate_systems', {})

        html = f"""
        <div class="metric">📐 ViewBox: {coord_system.get('viewBox', 'Not set')}</div>
        <div class="metric">📏 Dimensions: {coord_system.get('width', '?')} × {coord_system.get('height', '?')}</div>
        <div class="metric">🔢 Total Elements: {sum(len(elems) for elems in elements.values())}</div>

        <h3>Element Breakdown:</h3>
        <table>
            <tr><th>Element Type</th><th>Count</th><th>Sample Attributes</th></tr>
        """

        for elem_type, elems in elements.items():
            if elem_type in ['rect', 'circle', 'ellipse', 'line', 'polygon', 'polyline', 'path', 'text']:
                sample_attrs = elems[0]['attributes'] if elems else {}
                html += f"""
                <tr>
                    <td>{elem_type}</td>
                    <td>{len(elems)}</td>
                    <td>{', '.join(list(sample_attrs.keys())[:5])}</td>
                </tr>
                """

        html += "</table>"
        return html

    def _generate_conversion_summary_html(self) -> str:
        conversion = self.debug_data.get('conversion_analysis', {})
        if not conversion:
            return "<p>No conversion analysis data available.</p>"

        performance = conversion.get('performance', {})
        viewport = conversion.get('viewport_debug', {})
        errors = conversion.get('errors', [])

        html = f"""
        <div class="metric">⏱️ Conversion Time: {performance.get('conversion_time_seconds', '?')}s</div>
        <div class="metric">📦 Output Size: {performance.get('output_file_size', 0)} bytes</div>
        <div class="metric">⚠️ Errors: {len(errors)}</div>

        <h3>Viewport Mapping:</h3>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Scale X</td><td>{viewport.get('scale_x', '?')}</td></tr>
            <tr><td>Scale Y</td><td>{viewport.get('scale_y', '?')}</td></tr>
            <tr><td>Translate X</td><td>{viewport.get('translate_x', '?')}</td></tr>
            <tr><td>Translate Y</td><td>{viewport.get('translate_y', '?')}</td></tr>
        </table>
        """

        if errors:
            html += "<h3>Errors:</h3>"
            for error in errors:
                html += f'<div class="error">❌ {error.get("error_type", "Unknown")}: {error.get("error_message", "No message")}</div>'

        return html

    def _generate_pptx_summary_html(self) -> str:
        pptx_analysis = self.debug_data.get('pptx_analysis', {})
        if not pptx_analysis:
            return "<p>No PPTX analysis data available.</p>"

        shape_analysis = pptx_analysis.get('shape_analysis', {})
        text_analysis = pptx_analysis.get('text_analysis', {})
        coord_analysis = pptx_analysis.get('coordinate_analysis', {})

        html = f"""
        <div class="metric">📦 Total Shapes: {shape_analysis.get('total_shapes', 0)}</div>
        <div class="metric">📝 Text Shapes: {text_analysis.get('total_text_shapes', 0)}</div>
        """

        coord_ranges = coord_analysis.get('coordinate_ranges', {})
        if coord_ranges:
            html += f"""
            <div class="metric">📐 X Range: {coord_ranges.get('x_min', 0):.2f}" to {coord_ranges.get('x_max', 0):.2f}"</div>
            <div class="metric">📐 Y Range: {coord_ranges.get('y_min', 0):.2f}" to {coord_ranges.get('y_max', 0):.2f}"</div>
            """

        return html

    def _generate_comparison_html(self) -> str:
        comparison = self.debug_data.get('comparison_analysis', {})
        if not comparison:
            return "<p>No comparison analysis data available.</p>"

        fidelity = comparison.get('overall_fidelity', {})
        text_accuracy = comparison.get('text_accuracy', [])

        html = f"""
        <div class="metric">🎯 Text Position Accuracy: {fidelity.get('text_position_accuracy', 0)}%</div>
        <div class="metric">✅ Correctly Positioned: {fidelity.get('correctly_positioned', 0)}/{fidelity.get('total_text_elements', 0)}</div>

        <h3>Text Element Analysis:</h3>
        <table>
            <tr><th>Index</th><th>Text</th><th>Expected Position</th><th>Actual Position</th><th>Error</th><th>Status</th></tr>
        """

        for text_comp in text_accuracy:
            expected = text_comp['expected_pptx_position']
            actual = text_comp['actual_pptx_position']
            error = text_comp['position_error']
            status = text_comp['position_accuracy']

            status_class = 'success' if status == 'good' else 'error'

            html += f"""
            <tr class="{status_class}">
                <td>{text_comp['svg_index']}</td>
                <td>{text_comp['svg_text'][:20]}...</td>
                <td>({expected[0]:.2f}, {expected[1]:.2f})</td>
                <td>({actual[0]:.2f}, {actual[1]:.2f})</td>
                <td>({error[0]:.2f}, {error[1]:.2f})</td>
                <td>{status}</td>
            </tr>
            """

        html += "</table>"
        return html

    def _generate_recommendations_html(self) -> str:
        recommendations = self.debug_data.get('recommendations', [])

        if not recommendations:
            return "<p>✅ No issues detected. System appears to be working correctly.</p>"

        html = "<ul>"
        for rec in recommendations:
            html += f"<li>{rec}</li>"
        html += "</ul>"

        return html

    # Helper methods for parsing SVG elements
    def _parse_viewbox(self, viewbox: str) -> Dict[str, float]:
        if not viewbox:
            return {}

        try:
            parts = viewbox.strip().split()
            if len(parts) == 4:
                return {
                    'min_x': float(parts[0]),
                    'min_y': float(parts[1]),
                    'width': float(parts[2]),
                    'height': float(parts[3])
                }
        except (ValueError, IndexError):
            pass

        return {}

    def _get_implicit_dimensions(self, width: str, height: str) -> Dict[str, Any]:
        try:
            w = float(width.replace('px', '').replace('pt', '')) if width else None
            h = float(height.replace('px', '').replace('pt', '')) if height else None
            return {'width': w, 'height': h}
        except (ValueError, AttributeError):
            return {'width': None, 'height': None}

    def _compute_shape_bounds(self, shape: ET.Element) -> Dict[str, float]:
        """Compute bounding box for shape elements."""
        tag = shape.tag.split('}')[-1]

        try:
            if tag == 'rect':
                x = float(shape.get('x', 0))
                y = float(shape.get('y', 0))
                w = float(shape.get('width', 0))
                h = float(shape.get('height', 0))
                return {'min_x': x, 'min_y': y, 'max_x': x + w, 'max_y': y + h}

            elif tag == 'circle':
                cx = float(shape.get('cx', 0))
                cy = float(shape.get('cy', 0))
                r = float(shape.get('r', 0))
                return {'min_x': cx - r, 'min_y': cy - r, 'max_x': cx + r, 'max_y': cy + r}

            elif tag == 'ellipse':
                cx = float(shape.get('cx', 0))
                cy = float(shape.get('cy', 0))
                rx = float(shape.get('rx', 0))
                ry = float(shape.get('ry', 0))
                return {'min_x': cx - rx, 'min_y': cy - ry, 'max_x': cx + rx, 'max_y': cy + ry}

            elif tag == 'line':
                x1 = float(shape.get('x1', 0))
                y1 = float(shape.get('y1', 0))
                x2 = float(shape.get('x2', 0))
                y2 = float(shape.get('y2', 0))
                return {'min_x': min(x1, x2), 'min_y': min(y1, y2), 'max_x': max(x1, x2), 'max_y': max(y1, y2)}

        except (ValueError, TypeError):
            pass

        return {}

    def _compute_path_bounds(self, path_data: str) -> Dict[str, Any]:
        """Basic path bounds calculation."""
        # This is a simplified version - full implementation would parse all path commands
        return {'note': 'Path bounds calculation not implemented in debug system'}

    def _parse_style_attribute(self, style: str) -> Dict[str, str]:
        """Parse CSS style attribute."""
        if not style:
            return {}

        styles = {}
        for declaration in style.split(';'):
            if ':' in declaration:
                prop, value = declaration.split(':', 1)
                styles[prop.strip()] = value.strip()

        return styles

    def _extract_transforms(self, element: ET.Element) -> List[str]:
        """Extract transform attribute."""
        transform = element.get('transform', '')
        return [transform] if transform else []

    def _parse_path_commands(self, path_data: str) -> List[str]:
        """Extract path commands."""
        if not path_data:
            return []

        # Simple command extraction
        commands = []
        current_command = ""

        for char in path_data:
            if char.isalpha():
                if current_command:
                    commands.append(current_command.strip())
                current_command = char
            else:
                current_command += char

        if current_command:
            commands.append(current_command.strip())

        return commands


def main():
    """Run comprehensive debug analysis."""
    print("🚀 SVG2PPTX COMPREHENSIVE DEBUG SYSTEM")
    print("=" * 60)

    debug_system = ComprehensiveDebugSystem()

    # Analyze SVG
    debug_system.analyze_svg_completely('w3c_working_test.svg')

    # Debug conversion process
    debug_system.debug_conversion_process('w3c_working_test.svg', 'w3c_comprehensive_debug_test.pptx')

    # Analyze PPTX output
    debug_system.analyze_pptx_output('w3c_comprehensive_debug_test.pptx')

    # Compare accuracy
    debug_system.compare_svg_to_pptx()

    # Generate recommendations
    debug_system.generate_recommendations()

    # Save reports
    debug_system.save_debug_report('comprehensive_debug_report.json')
    debug_system.generate_html_report('comprehensive_debug_report.html')

    print("\n🎉 COMPREHENSIVE DEBUG ANALYSIS COMPLETE!")
    print("📊 Reports generated:")
    print("   • comprehensive_debug_report.json (raw data)")
    print("   • comprehensive_debug_report.html (visual report)")
    print("   • w3c_comprehensive_debug_test.pptx (test output)")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
E2E Pipeline Debug Analyzer

Comprehensive analysis of the SVG-to-PowerPoint conversion pipeline
to identify where fidelity issues occur. This tool examines each step
of the conversion process and provides detailed debugging information.
"""

import sys
import json
import time
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
import re

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.svg2pptx import convert_svg_to_pptx
from core.paths import create_path_system
from src.svg2drawingml import SVGToDrawingMLConverter


class E2EDebugAnalyzer:
    """Comprehensive E2E pipeline analyzer."""

    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent
        self.analysis_data = {
            "timestamp": datetime.now().isoformat(),
            "pipeline_steps": [],
            "fidelity_issues": [],
            "performance_metrics": {},
            "component_analysis": {}
        }

    def log_step(self, step_name, status, details=None, timing=None):
        """Log a pipeline step with status and details."""
        step_data = {
            "step": step_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {},
            "timing_ms": timing
        }
        self.analysis_data["pipeline_steps"].append(step_data)

        status_icon = "✅" if status == "success" else "❌" if status == "error" else "⚠️"
        timing_str = f" ({timing:.1f}ms)" if timing else ""
        print(f"{status_icon} {step_name}{timing_str}")

        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")

    def analyze_svg_input(self, svg_file):
        """Analyze the SVG input file for complexity and potential issues."""
        start_time = time.time()

        try:
            with open(svg_file, 'r') as f:
                svg_content = f.read()

            # Parse SVG structure
            root = ET.fromstring(svg_content)

            # Count elements
            elements = {
                'path': len(root.findall('.//{http://www.w3.org/2000/svg}path')),
                'text': len(root.findall('.//{http://www.w3.org/2000/svg}text')),
                'rect': len(root.findall('.//{http://www.w3.org/2000/svg}rect')),
                'circle': len(root.findall('.//{http://www.w3.org/2000/svg}circle')),
                'ellipse': len(root.findall('.//{http://www.w3.org/2000/svg}ellipse')),
                'line': len(root.findall('.//{http://www.w3.org/2000/svg}line')),
                'polygon': len(root.findall('.//{http://www.w3.org/2000/svg}polygon')),
                'polyline': len(root.findall('.//{http://www.w3.org/2000/svg}polyline')),
                'g': len(root.findall('.//{http://www.w3.org/2000/svg}g'))
            }

            # Analyze path complexity
            path_complexity = self._analyze_path_complexity(root)

            # Check for advanced features
            advanced_features = self._check_advanced_svg_features(root, svg_content)

            # Get SVG dimensions
            width = root.get('width', 'unknown')
            height = root.get('height', 'unknown')
            viewBox = root.get('viewBox', 'none')

            details = {
                "file_size": len(svg_content),
                "dimensions": f"{width} × {height}",
                "viewBox": viewBox,
                "total_elements": sum(elements.values()),
                "element_breakdown": elements,
                "path_complexity": path_complexity,
                "advanced_features": advanced_features
            }

            timing = (time.time() - start_time) * 1000
            self.log_step("SVG Input Analysis", "success", details, timing)

            return True

        except Exception as e:
            timing = (time.time() - start_time) * 1000
            self.log_step("SVG Input Analysis", "error", {"error": str(e)}, timing)
            return False

    def _analyze_path_complexity(self, svg_root):
        """Analyze the complexity of path elements."""
        complexity_data = {
            "total_paths": 0,
            "command_types": {},
            "relative_commands": 0,
            "absolute_commands": 0,
            "scientific_notation": 0,
            "complex_arcs": 0,
            "bezier_curves": 0
        }

        paths = svg_root.findall('.//{http://www.w3.org/2000/svg}path')
        complexity_data["total_paths"] = len(paths)

        for path in paths:
            d_attr = path.get('d', '')
            if not d_attr:
                continue

            # Count command types
            commands = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]', d_attr)
            for cmd in commands:
                if cmd.lower() in complexity_data["command_types"]:
                    complexity_data["command_types"][cmd.lower()] += 1
                else:
                    complexity_data["command_types"][cmd.lower()] = 1

                if cmd.islower():
                    complexity_data["relative_commands"] += 1
                else:
                    complexity_data["absolute_commands"] += 1

            # Check for scientific notation
            if re.search(r'\d+\.?\d*[eE][+-]?\d+', d_attr):
                complexity_data["scientific_notation"] += 1

            # Check for complex arcs (with rotation or large-arc-flag)
            arc_matches = re.findall(r'[Aa]\s*[\d\.\-e\s,]+', d_attr)
            for arc in arc_matches:
                numbers = re.findall(r'[\d\.\-e]+', arc)
                if len(numbers) >= 7:  # rx, ry, rotation, large-arc, sweep, x, y
                    rotation = float(numbers[2]) if len(numbers) > 2 else 0
                    large_arc = int(float(numbers[3])) if len(numbers) > 3 else 0
                    if rotation != 0 or large_arc:
                        complexity_data["complex_arcs"] += 1

            # Check for bezier curves
            if re.search(r'[CcSsQqTt]', d_attr):
                complexity_data["bezier_curves"] += 1

        return complexity_data

    def _check_advanced_svg_features(self, svg_root, svg_content):
        """Check for advanced SVG features that might cause issues."""
        features = {
            "gradients": len(svg_root.findall('.//{http://www.w3.org/2000/svg}linearGradient')) +
                        len(svg_root.findall('.//{http://www.w3.org/2000/svg}radialGradient')),
            "patterns": len(svg_root.findall('.//{http://www.w3.org/2000/svg}pattern')),
            "filters": len(svg_root.findall('.//{http://www.w3.org/2000/svg}filter')),
            "masks": len(svg_root.findall('.//{http://www.w3.org/2000/svg}mask')),
            "clipPaths": len(svg_root.findall('.//{http://www.w3.org/2000/svg}clipPath')),
            "animations": len(svg_root.findall('.//{http://www.w3.org/2000/svg}animate')) +
                         len(svg_root.findall('.//{http://www.w3.org/2000/svg}animateTransform')),
            "transforms": len(re.findall(r'transform\s*=', svg_content)),
            "css_styles": 1 if '<style' in svg_content or 'style=' in svg_content else 0,
            "external_refs": len(re.findall(r'xlink:href|href\s*=', svg_content))
        }

        return features

    def analyze_pathsystem_processing(self, svg_file):
        """Analyze PathSystem component processing."""
        start_time = time.time()

        try:
            # Create PathSystem
            path_system = create_path_system(800, 600, (0, 0, 800, 600))

            # Read SVG and extract paths
            with open(svg_file, 'r') as f:
                svg_content = f.read()

            root = ET.fromstring(svg_content)
            paths = root.findall('.//{http://www.w3.org/2000/svg}path')

            processing_results = []
            total_commands = 0
            total_xml_size = 0

            for i, path in enumerate(paths):
                d_attr = path.get('d', '')
                if not d_attr:
                    continue

                try:
                    result = path_system.process_path(d_attr)
                    processing_results.append({
                        "path_index": i,
                        "input_length": len(d_attr),
                        "commands_generated": len(result.commands),
                        "xml_size": len(result.path_xml),
                        "success": True
                    })
                    total_commands += len(result.commands)
                    total_xml_size += len(result.path_xml)

                except Exception as e:
                    processing_results.append({
                        "path_index": i,
                        "input_length": len(d_attr),
                        "error": str(e),
                        "success": False
                    })

            details = {
                "paths_processed": len(processing_results),
                "successful_paths": sum(1 for r in processing_results if r["success"]),
                "failed_paths": sum(1 for r in processing_results if not r["success"]),
                "total_commands": total_commands,
                "total_xml_size": total_xml_size,
                "avg_commands_per_path": total_commands / len(processing_results) if processing_results else 0,
                "processing_details": processing_results
            }

            timing = (time.time() - start_time) * 1000
            self.log_step("PathSystem Processing", "success", details, timing)

            return True

        except Exception as e:
            timing = (time.time() - start_time) * 1000
            self.log_step("PathSystem Processing", "error", {"error": str(e)}, timing)
            return False

    def analyze_svg2drawingml_conversion(self, svg_file):
        """Analyze the SVG to DrawingML conversion process."""
        start_time = time.time()

        try:
            converter = SVGToDrawingMLConverter()

            # Convert SVG
            result = converter.convert_file(str(svg_file))

            # Analyze the result
            details = {
                "output_size": len(result),
                "contains_path_elements": "<a:path" in result,
                "contains_shape_elements": "<p:sp" in result,
                "contains_text_elements": "<a:t>" in result,
                "xml_structure_valid": result.startswith("<?xml") or result.startswith("<"),
                "drawingml_namespaces": "xmlns:a=" in result and "xmlns:p=" in result
            }

            # Count various elements in output
            details.update({
                "path_count": result.count("<a:path"),
                "shape_count": result.count("<p:sp"),
                "text_run_count": result.count("<a:t>"),
                "transform_count": result.count("xfrm")
            })

            timing = (time.time() - start_time) * 1000
            self.log_step("SVG2DrawingML Conversion", "success", details, timing)

            return True

        except Exception as e:
            timing = (time.time() - start_time) * 1000
            self.log_step("SVG2DrawingML Conversion", "error", {"error": str(e)}, timing)
            return False

    def analyze_pptx_structure(self, pptx_file):
        """Analyze the generated PPTX file structure."""
        start_time = time.time()

        try:
            import zipfile

            structure_analysis = {
                "file_size": Path(pptx_file).stat().st_size,
                "is_valid_zip": False,
                "contains_slide": False,
                "contains_relationships": False,
                "slide_content_size": 0,
                "xml_files": [],
                "media_files": []
            }

            # Check if it's a valid zip file
            try:
                with zipfile.ZipFile(pptx_file, 'r') as zip_file:
                    structure_analysis["is_valid_zip"] = True
                    file_list = zip_file.namelist()

                    # Check for key PPTX components
                    structure_analysis["contains_slide"] = any("slide" in f for f in file_list)
                    structure_analysis["contains_relationships"] = "_rels/" in file_list

                    # Categorize files
                    for file_path in file_list:
                        if file_path.endswith('.xml'):
                            structure_analysis["xml_files"].append(file_path)
                        elif any(file_path.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                            structure_analysis["media_files"].append(file_path)

                    # Read slide content if available
                    slide_files = [f for f in file_list if "slide" in f and f.endswith('.xml')]
                    if slide_files:
                        slide_content = zip_file.read(slide_files[0])
                        structure_analysis["slide_content_size"] = len(slide_content)

            except zipfile.BadZipFile:
                structure_analysis["is_valid_zip"] = False

            timing = (time.time() - start_time) * 1000
            self.log_step("PPTX Structure Analysis", "success", structure_analysis, timing)

            return True

        except Exception as e:
            timing = (time.time() - start_time) * 1000
            self.log_step("PPTX Structure Analysis", "error", {"error": str(e)}, timing)
            return False

    def identify_fidelity_issues(self, svg_file, pptx_screenshot=None):
        """Identify potential fidelity issues in the conversion."""
        issues = []

        # Check for common fidelity problems
        try:
            with open(svg_file, 'r') as f:
                svg_content = f.read()

            root = ET.fromstring(svg_content)

            # Issue 1: Text positioning and fonts
            text_elements = root.findall('.//{http://www.w3.org/2000/svg}text')
            if text_elements:
                font_families = set()
                for text in text_elements:
                    font_family = text.get('font-family', '')
                    if font_family:
                        font_families.add(font_family)

                if font_families:
                    issues.append({
                        "category": "text_rendering",
                        "severity": "medium",
                        "description": f"Text elements with {len(font_families)} different fonts may not render identically",
                        "fonts_used": list(font_families),
                        "recommendation": "Verify font availability in PowerPoint"
                    })

            # Issue 2: Complex path commands
            paths = root.findall('.//{http://www.w3.org/2000/svg}path')
            complex_paths = 0
            for path in paths:
                d_attr = path.get('d', '')
                if 'A' in d_attr or 'a' in d_attr:  # Arc commands
                    complex_paths += 1

            if complex_paths > 0:
                issues.append({
                    "category": "path_complexity",
                    "severity": "low",
                    "description": f"{complex_paths} paths contain arc commands which are converted to bezier curves",
                    "recommendation": "Check arc rendering fidelity in PowerPoint output"
                })

            # Issue 3: Transforms
            transform_count = len(re.findall(r'transform\s*=', svg_content))
            if transform_count > 0:
                issues.append({
                    "category": "transforms",
                    "severity": "medium",
                    "description": f"{transform_count} elements have transform attributes",
                    "recommendation": "Verify coordinate transformations are applied correctly"
                })

            # Issue 4: Advanced SVG features
            if '<gradient' in svg_content:
                issues.append({
                    "category": "gradients",
                    "severity": "high",
                    "description": "Gradients detected - may not convert with full fidelity",
                    "recommendation": "Check gradient rendering in PowerPoint"
                })

            if '<filter' in svg_content:
                issues.append({
                    "category": "filters",
                    "severity": "high",
                    "description": "SVG filters detected - not supported in PowerPoint",
                    "recommendation": "Filters will be ignored in conversion"
                })

            self.analysis_data["fidelity_issues"] = issues

            details = {
                "total_issues": len(issues),
                "high_severity": len([i for i in issues if i["severity"] == "high"]),
                "medium_severity": len([i for i in issues if i["severity"] == "medium"]),
                "low_severity": len([i for i in issues if i["severity"] == "low"]),
                "issues": issues
            }

            self.log_step("Fidelity Issue Analysis", "success", details)

            return True

        except Exception as e:
            self.log_step("Fidelity Issue Analysis", "error", {"error": str(e)})
            return False

    def generate_comprehensive_report(self):
        """Generate a comprehensive E2E debug report."""
        report_file = self.output_dir / "e2e_debug_report.json"

        # Add summary metrics
        self.analysis_data["summary"] = {
            "total_steps": len(self.analysis_data["pipeline_steps"]),
            "successful_steps": len([s for s in self.analysis_data["pipeline_steps"] if s["status"] == "success"]),
            "failed_steps": len([s for s in self.analysis_data["pipeline_steps"] if s["status"] == "error"]),
            "total_issues": len(self.analysis_data["fidelity_issues"]),
            "high_priority_issues": len([i for i in self.analysis_data["fidelity_issues"] if i["severity"] == "high"])
        }

        with open(report_file, 'w') as f:
            json.dump(self.analysis_data, f, indent=2)

        print(f"\n📋 Comprehensive E2E debug report saved: {report_file}")

        # Print summary
        summary = self.analysis_data["summary"]
        print(f"\n📊 Analysis Summary:")
        print(f"   Steps: {summary['successful_steps']}/{summary['total_steps']} successful")
        print(f"   Issues: {summary['total_issues']} total ({summary['high_priority_issues']} high priority)")

        return report_file

    def run_complete_analysis(self, svg_file, pptx_file=None):
        """Run complete E2E analysis."""
        print("=" * 80)
        print("🔍 E2E Pipeline Debug Analysis")
        print("=" * 80)

        # Generate PPTX if not provided
        if not pptx_file:
            pptx_file = self.output_dir / f"{Path(svg_file).stem}_debug.pptx"
            print(f"🔄 Converting {svg_file} to {pptx_file}")
            try:
                convert_svg_to_pptx(str(svg_file), str(pptx_file))
            except Exception as e:
                print(f"❌ Conversion failed: {e}")
                return False

        # Run all analysis steps
        steps = [
            ("Analyze SVG Input", lambda: self.analyze_svg_input(svg_file)),
            ("Analyze PathSystem Processing", lambda: self.analyze_pathsystem_processing(svg_file)),
            ("Analyze SVG2DrawingML Conversion", lambda: self.analyze_svg2drawingml_conversion(svg_file)),
            ("Analyze PPTX Structure", lambda: self.analyze_pptx_structure(pptx_file)),
            ("Identify Fidelity Issues", lambda: self.identify_fidelity_issues(svg_file))
        ]

        print("\n🔧 Running pipeline analysis steps:")
        for step_name, step_func in steps:
            print(f"\n{step_name}:")
            step_func()

        # Generate comprehensive report
        report_file = self.generate_comprehensive_report()

        print("\n🎉 E2E analysis completed!")
        return True


def main():
    """Run the E2E debug analyzer."""
    deliverables_dir = Path(__file__).parent
    svg_file = deliverables_dir / "test_complex_paths.svg"

    if not svg_file.exists():
        print(f"❌ SVG file not found: {svg_file}")
        return False

    analyzer = E2EDebugAnalyzer(deliverables_dir)
    return analyzer.run_complete_analysis(svg_file)


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
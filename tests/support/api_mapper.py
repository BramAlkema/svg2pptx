#!/usr/bin/env python3
"""
API Analysis & Mapping Tool for Test Suite Modernization

This tool systematically identifies API mismatches between test expectations
and actual module implementations, providing automated fix recommendations.

Usage:
    python tests/support/api_mapper.py
    python tests/support/api_mapper.py --fix-files
"""

import ast
import importlib
import inspect
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass
import argparse
import sys

@dataclass
class APIMismatch:
    """Represents an API mismatch found in test files."""
    file_path: str
    line_number: int
    test_method: str
    expected_method: str
    actual_methods: List[str]
    suggested_fix: str
    confidence: str  # 'high', 'medium', 'low'

@dataclass
class ModuleAPI:
    """Represents the actual API of a source module."""
    module_name: str
    classes: Dict[str, List[str]]  # class_name -> method_names
    functions: List[str]
    constants: List[str]

class APIMapper:
    """Analyzes test files and maps API mismatches to actual implementations."""

    def __init__(self, test_dir: str = "tests", src_dir: str = "src"):
        self.test_dir = Path(test_dir)
        self.src_dir = Path(src_dir)
        self.mismatches = []
        self.module_apis = {}
        self.common_patterns = self._load_common_patterns()

    def _load_common_patterns(self) -> Dict[str, str]:
        """Load common API migration patterns."""
        return {
            # SVG2PPTX module patterns
            'load_svg': 'convert_file',
            'SVG2PPTX': 'SVGToPowerPointConverter',

            # Converter patterns
            'ConverterRegistry': 'Use services.converter_registry',
            'FilterPipeline': 'FilterRegistry',
            'FilterIntegrator': 'FilterChain',
            'CompositingEngine': 'Use FilterChain.apply()',

            # Service injection patterns
            'manual_mock_setup': 'ConversionServices.create_default()',

            # Units patterns
            'ViewportContext': 'ConversionContext',
            'UnitConverter': 'UnitEngine',

            # Preprocessing patterns
            'PreprocessingPipeline': 'Optimizer',
        }

    def analyze_all_modules(self) -> None:
        """Analyze all source modules to build API reference."""
        print("🔍 Analyzing source module APIs...")

        for py_file in self.src_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            try:
                module_api = self._analyze_module(py_file)
                if module_api:
                    self.module_apis[module_api.module_name] = module_api
                    print(f"   ✅ {module_api.module_name}")
            except Exception as e:
                print(f"   ❌ {py_file}: {e}")

    def _analyze_module(self, py_file: Path) -> ModuleAPI:
        """Analyze a single Python module to extract its API."""
        # Convert file path to module name
        try:
            rel_path = py_file.relative_to(Path.cwd())
        except ValueError:
            # Handle absolute paths that aren't relative to cwd
            rel_path = py_file.relative_to(self.src_dir.parent)
        module_name = str(rel_path.with_suffix('')).replace('/', '.')

        try:
            # Parse the AST instead of importing to avoid dependency issues
            with open(py_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            classes = {}
            functions = []
            constants = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(item.name)
                    classes[node.name] = methods

                elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                    # Top-level functions only
                    functions.append(node.name)

                elif isinstance(node, ast.Assign) and node.col_offset == 0:
                    # Top-level constants
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            constants.append(target.id)

            return ModuleAPI(module_name, classes, functions, constants)

        except Exception as e:
            print(f"Error analyzing {py_file}: {e}")
            return None

    def scan_test_files(self) -> None:
        """Scan all test files for API mismatches."""
        print("\n🔍 Scanning test files for API mismatches...")

        for test_file in self.test_dir.rglob("test_*.py"):
            try:
                self._scan_test_file(test_file)
                print(f"   ✅ {test_file.relative_to(self.test_dir)}")
            except Exception as e:
                print(f"   ❌ {test_file}: {e}")

    def _scan_test_file(self, test_file: Path) -> None:
        """Scan a single test file for API mismatches."""
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')

        # Look for import statements to identify target modules
        target_modules = self._extract_imports(content)

        # Scan for method calls that might be mismatched
        for line_num, line in enumerate(lines, 1):
            self._check_line_for_mismatches(test_file, line_num, line, target_modules)

    def _extract_imports(self, content: str) -> Set[str]:
        """Extract imported modules from test content."""
        imports = set()

        # Parse imports
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith('src.'):
                        imports.add(node.module)
        except:
            # Fallback to regex if AST parsing fails
            import_pattern = r'from\s+(src\.\S+)\s+import'
            imports.update(re.findall(import_pattern, content))

        return imports

    def _check_line_for_mismatches(self, test_file: Path, line_num: int, line: str, target_modules: Set[str]) -> None:
        """Check a single line for potential API mismatches."""
        line = line.strip()

        # Check for common mismatch patterns
        for old_pattern, new_pattern in self.common_patterns.items():
            if old_pattern in line:
                # Try to find the containing test method
                test_method = self._find_containing_test_method(test_file, line_num)

                # Determine confidence based on context
                confidence = self._assess_confidence(line, old_pattern, target_modules)

                mismatch = APIMismatch(
                    file_path=str(test_file),
                    line_number=line_num,
                    test_method=test_method,
                    expected_method=old_pattern,
                    actual_methods=[new_pattern],
                    suggested_fix=line.replace(old_pattern, new_pattern),
                    confidence=confidence
                )
                self.mismatches.append(mismatch)

    def _find_containing_test_method(self, test_file: Path, line_num: int) -> str:
        """Find the test method containing the given line."""
        try:
            with open(test_file, 'r') as f:
                lines = f.readlines()

            # Search backwards for the nearest def test_ method
            for i in range(line_num - 1, -1, -1):
                line = lines[i].strip()
                if line.startswith('def test_'):
                    return line.split('(')[0].replace('def ', '')

            return "unknown_test"
        except:
            return "unknown_test"

    def _assess_confidence(self, line: str, pattern: str, target_modules: Set[str]) -> str:
        """Assess confidence level of the mismatch detection."""
        # High confidence: clear method call pattern
        if f".{pattern}(" in line or f"= {pattern}(" in line:
            return "high"

        # Medium confidence: pattern in context of target modules
        if any(module in line for module in target_modules):
            return "medium"

        # Low confidence: pattern found but unclear context
        return "low"

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        print("\n📊 Generating analysis report...")

        # Group mismatches by file and confidence
        by_file = {}
        confidence_counts = {"high": 0, "medium": 0, "low": 0}

        for mismatch in self.mismatches:
            file_path = mismatch.file_path
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(mismatch)
            confidence_counts[mismatch.confidence] += 1

        # Generate summary statistics
        total_test_files = len(list(self.test_dir.rglob("test_*.py")))
        affected_files = len(by_file)

        report = {
            "summary": {
                "total_test_files": total_test_files,
                "affected_files": affected_files,
                "total_mismatches": len(self.mismatches),
                "confidence_distribution": confidence_counts
            },
            "modules_analyzed": len(self.module_apis),
            "common_patterns": self.common_patterns,
            "mismatches_by_file": by_file,
            "high_priority_fixes": [m for m in self.mismatches if m.confidence == "high"]
        }

        return report

    def save_report(self, report: Dict[str, Any], output_file: str = "tests/support/api_analysis_report.json") -> None:
        """Save analysis report to JSON file."""
        # Convert dataclasses to dictionaries for JSON serialization
        serializable_report = self._make_serializable(report)

        with open(output_file, 'w') as f:
            json.dump(serializable_report, f, indent=2, default=str)

        print(f"📄 Report saved to: {output_file}")

    def _make_serializable(self, obj: Any) -> Any:
        """Convert dataclasses to dictionaries for JSON serialization."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, APIMismatch):
            return {
                "file_path": obj.file_path,
                "line_number": obj.line_number,
                "test_method": obj.test_method,
                "expected_method": obj.expected_method,
                "actual_methods": obj.actual_methods,
                "suggested_fix": obj.suggested_fix,
                "confidence": obj.confidence
            }
        else:
            return obj

    def print_summary(self, report: Dict[str, Any]) -> None:
        """Print human-readable summary of the analysis."""
        summary = report["summary"]

        print("\n" + "="*60)
        print("📋 API ANALYSIS SUMMARY")
        print("="*60)
        print(f"📁 Total test files analyzed: {summary['total_test_files']}")
        print(f"🔧 Files with API mismatches: {summary['affected_files']}")
        print(f"⚠️  Total mismatches found: {summary['total_mismatches']}")
        print()
        print("🎯 Confidence Distribution:")
        for level, count in summary['confidence_distribution'].items():
            print(f"   {level.capitalize()}: {count}")

        print("\n🔥 High Priority Fixes:")
        high_priority = report["high_priority_fixes"][:10]  # Show top 10
        for mismatch in high_priority:
            # Handle both dict and APIMismatch objects
            if isinstance(mismatch, dict):
                file_path, line_num, expected, actual = mismatch["file_path"], mismatch["line_number"], mismatch["expected_method"], mismatch["actual_methods"][0]
            else:
                file_path, line_num, expected, actual = mismatch.file_path, mismatch.line_number, mismatch.expected_method, mismatch.actual_methods[0]

            try:
                file_rel = Path(file_path).relative_to(Path.cwd())
            except ValueError:
                file_rel = Path(file_path)
            print(f"   {file_rel}:{line_num} - {expected} → {actual}")

        if len(report["high_priority_fixes"]) > 10:
            print(f"   ... and {len(report['high_priority_fixes']) - 10} more")

    def generate_fix_recommendations(self) -> Dict[str, List[str]]:
        """Generate automated fix recommendations."""
        fixes = {}

        for mismatch in self.mismatches:
            if mismatch.confidence == "high":
                file_path = mismatch.file_path
                if file_path not in fixes:
                    fixes[file_path] = []

                fix_instruction = {
                    "line": mismatch.line_number,
                    "old": mismatch.expected_method,
                    "new": mismatch.actual_methods[0],
                    "suggested_line": mismatch.suggested_fix
                }
                fixes[file_path].append(fix_instruction)

        return fixes

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="API Analysis & Mapping Tool")
    parser.add_argument("--output", "-o", default="tests/support/api_analysis_report.json",
                       help="Output file for analysis report")
    parser.add_argument("--fixes", "-f", default="tests/support/api_fixes.json",
                       help="Output file for fix recommendations")

    args = parser.parse_args()

    print("🚀 Starting API Analysis & Mapping...")

    # Initialize mapper
    mapper = APIMapper()

    # Analyze source modules
    mapper.analyze_all_modules()

    # Scan test files
    mapper.scan_test_files()

    # Generate and save reports
    report = mapper.generate_report()
    mapper.save_report(report, args.output)

    # Generate fix recommendations
    fixes = mapper.generate_fix_recommendations()
    with open(args.fixes, 'w') as f:
        json.dump(fixes, f, indent=2)

    # Print summary
    mapper.print_summary(report)

    print(f"\n✅ Analysis complete!")
    print(f"📄 Full report: {args.output}")
    print(f"🔧 Fix recommendations: {args.fixes}")

if __name__ == "__main__":
    main()
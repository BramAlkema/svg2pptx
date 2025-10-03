#!/usr/bin/env python3
"""
Pipeline Integration Verification Script
Systematically checks which components are actually integrated vs isolated.
"""

import os
import sys
import ast
import re
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict

class PipelineIntegrationVerifier:
    def __init__(self, project_root: str = "."):
        self.root = Path(project_root)
        self.core_path = self.root / "core"
        self.src_path = self.root / "src"
        self.pipeline_file = self.core_path / "pipeline" / "converter.py"

        self.results = {
            'production_integrated': [],
            'test_only': [],
            'isolated': [],
            'missing_files': [],
            'partial_integration': []
        }

        self.components = self._discover_components()

    def _discover_components(self) -> Dict[str, Path]:
        """Discover all converter/mapper/filter/service components"""
        components = {}

        # Search patterns for different component types
        patterns = [
            ('core/map/', r'.*_mapper\.py$', 'Mapper'),
            ('core/converters/font/handlers/', r'.*_handler\.py$', 'Handler'),
            ('core/converters/font/', r'.*_converter\.py$', 'Converter'),
            ('core/converters/', r'.*\.py$', 'Converter'),
            ('core/filters/', r'.*\.py$', 'Filter'),
            ('core/services/', r'.*\.py$', 'Service'),
            ('core/animations/', r'.*\.py$', 'Animation'),
            ('core/color/', r'.*\.py$', 'Color'),
        ]

        for base_path, pattern, component_type in patterns:
            search_path = self.root / base_path
            if search_path.exists():
                for file_path in search_path.rglob("*.py"):
                    if re.match(pattern, file_path.name) and not file_path.name.startswith('__'):
                        # Extract class name from file
                        class_name = self._extract_main_class(file_path)
                        if class_name:
                            components[class_name] = file_path

        return components

    def _extract_main_class(self, file_path: Path) -> str:
        """Extract the main class name from a Python file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            tree = ast.parse(content)
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

            # Prefer class names that match the file name pattern
            file_base = file_path.stem
            for class_name in classes:
                if file_base.lower().replace('_', '') in class_name.lower():
                    return class_name

            # Return the first class if no pattern match
            return classes[0] if classes else None

        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return None

    def check_pipeline_integration(self, component: str, file_path: Path) -> str:
        """Check how a component is integrated into the pipeline"""

        # Check 1: Direct import/usage in main pipeline
        if self._is_used_in_pipeline(component):
            return 'production_integrated'

        # Check 2: Used in tests
        if self._is_used_in_tests(component):
            # Check if it's ONLY in tests
            if not self._is_imported_by_core(component, exclude_tests=True):
                return 'test_only'
            else:
                return 'partial_integration'

        # Check 3: Not used anywhere
        if not self._is_imported_anywhere(component):
            return 'isolated'

        return 'partial_integration'

    def _is_used_in_pipeline(self, component: str) -> bool:
        """Check if component is directly used in main pipeline"""
        if not self.pipeline_file.exists():
            return False

        try:
            content = self.pipeline_file.read_text()

            # Check for direct class name usage
            if component in content:
                return True

            # Check for import statements
            import_patterns = [
                rf'from.*import.*{component}',
                rf'import.*{component}',
            ]

            for pattern in import_patterns:
                if re.search(pattern, content):
                    return True

        except Exception as e:
            print(f"Warning: Could not read pipeline file: {e}")

        return False

    def _is_used_in_tests(self, component: str) -> bool:
        """Check if component is used in test files"""
        test_dirs = [self.root / "tests"]

        for test_dir in test_dirs:
            if test_dir.exists():
                for test_file in test_dir.rglob("*.py"):
                    try:
                        content = test_file.read_text()
                        if component in content:
                            return True
                    except Exception:
                        continue
        return False

    def _is_imported_by_core(self, component: str, exclude_tests: bool = False) -> bool:
        """Check if component is imported by core modules"""
        search_dirs = [self.core_path]
        if not exclude_tests:
            search_dirs.append(self.root / "tests")

        for search_dir in search_dirs:
            if search_dir.exists():
                for py_file in search_dir.rglob("*.py"):
                    if exclude_tests and "test" in str(py_file):
                        continue

                    try:
                        content = py_file.read_text()
                        if component in content:
                            return True
                    except Exception:
                        continue
        return False

    def _is_imported_anywhere(self, component: str) -> bool:
        """Check if component is imported anywhere in the project"""
        return self._is_imported_by_core(component, exclude_tests=False)

    def analyze_mapper_integration(self) -> Dict[str, str]:
        """Specifically analyze mapper integration in CleanSlateConverter"""
        mappers_used = {}

        if self.pipeline_file.exists():
            try:
                content = self.pipeline_file.read_text()

                # Find mapper initialization
                mapper_pattern = r"self\.mappers\s*=\s*\{([^}]+)\}"
                match = re.search(mapper_pattern, content, re.DOTALL)

                if match:
                    mappers_block = match.group(1)
                    # Extract mapper assignments
                    assignment_pattern = r"'([^']+)':\s*([A-Za-z_][A-Za-z0-9_]*)"
                    assignments = re.findall(assignment_pattern, mappers_block)

                    for element_type, mapper_class in assignments:
                        mappers_used[element_type] = mapper_class

            except Exception as e:
                print(f"Warning: Could not analyze mapper integration: {e}")

        return mappers_used

    def analyze_service_integration(self) -> List[str]:
        """Analyze which services are wired in ConversionServices"""
        services_file = self.core_path / "services" / "conversion_services.py"
        services_used = []

        if services_file.exists():
            try:
                content = services_file.read_text()

                # Find create_default method
                create_default_pattern = r"def create_default\(.*?\):(.*?)(?=def|\Z)"
                match = re.search(create_default_pattern, content, re.DOTALL)

                if match:
                    method_body = match.group(1)
                    # Extract service instantiations
                    service_pattern = r"([a-z_]+)=([A-Za-z_][A-Za-z0-9_]*)\("
                    services = re.findall(service_pattern, method_body)

                    for service_var, service_class in services:
                        services_used.append(f"{service_var} -> {service_class}")

            except Exception as e:
                print(f"Warning: Could not analyze service integration: {e}")

        return services_used

    def run_verification(self) -> Dict:
        """Run complete verification and return results"""
        print("🔍 Analyzing Pipeline Integration...")
        print(f"Found {len(self.components)} components to analyze\n")

        # Analyze each component
        for component, file_path in self.components.items():
            if not file_path.exists():
                self.results['missing_files'].append(component)
                continue

            integration_status = self.check_pipeline_integration(component, file_path)
            self.results[integration_status].append({
                'name': component,
                'file': str(file_path.relative_to(self.root))
            })

        # Special analysis for key integrations
        self.mapper_analysis = self.analyze_mapper_integration()
        self.service_analysis = self.analyze_service_integration()

        return self.results

    def print_report(self):
        """Print detailed verification report"""
        print("=" * 70)
        print("📊 PIPELINE INTEGRATION VERIFICATION REPORT")
        print("=" * 70)

        # Summary
        total = sum(len(components) for components in self.results.values())
        print(f"\n📈 SUMMARY ({total} components analyzed):")
        for status, components in self.results.items():
            print(f"  {status.replace('_', ' ').title()}: {len(components)}")

        # Detailed breakdown
        for status, components in self.results.items():
            if components:
                print(f"\n🔍 {status.replace('_', ' ').upper()} ({len(components)}):")
                for comp in components:
                    if isinstance(comp, dict):
                        print(f"  ✓ {comp['name']} ({comp['file']})")
                    else:
                        print(f"  ✓ {comp}")

        # Mapper analysis
        print(f"\n📋 MAPPER INTEGRATION (CleanSlateConverter):")
        if self.mapper_analysis:
            for element_type, mapper_class in self.mapper_analysis.items():
                print(f"  '{element_type}' -> {mapper_class}")
        else:
            print("  ⚠️  Could not determine mapper integration")

        # Service analysis
        print(f"\n🔧 SERVICE INTEGRATION (ConversionServices):")
        if self.service_analysis:
            for service in self.service_analysis:
                print(f"  {service}")
        else:
            print("  ⚠️  Could not determine service integration")

        # Critical findings
        print(f"\n🚨 CRITICAL FINDINGS:")

        # Font Handler System Check
        font_handlers = [comp for comp in self.results['test_only'] + self.results['isolated']
                        if isinstance(comp, dict) and 'Handler' in comp['name']]
        if font_handlers:
            print(f"  ❌ Font Handlers isolated: {len(font_handlers)} handlers not in production")
            for handler in font_handlers:
                print(f"     - {handler['name']}")

        # SmartFontConverter Check
        smart_converter = any(comp.get('name', '') == 'SmartFontConverter'
                            for comp_list in self.results.values()
                            for comp in comp_list if isinstance(comp, dict))
        if smart_converter:
            smart_status = next((status for status, comp_list in self.results.items()
                               for comp in comp_list
                               if isinstance(comp, dict) and comp.get('name') == 'SmartFontConverter'),
                              'unknown')
            print(f"  ⚠️  SmartFontConverter status: {smart_status}")

        # TextMapper vs FontHandler integration
        text_mapper_integrated = 'TextMapper' in self.mapper_analysis.values()
        print(f"  {'✅' if text_mapper_integrated else '❌'} TextMapper in production: {text_mapper_integrated}")

        print("\n" + "=" * 70)

def main():
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = "."

    verifier = PipelineIntegrationVerifier(project_root)
    verifier.run_verification()
    verifier.print_report()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Audit all converters for ConversionServices dependency compliance.

This script identifies:
1. Converters that inherit from BaseConverter but don't require ConversionServices
2. Converters with incorrect __init__ signatures
3. Converters with missing type annotations
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Any

class ConverterAuditor:
    """Auditor for converter dependency compliance."""

    def __init__(self, src_path: str = "src/converters"):
        self.src_path = Path(src_path)
        self.issues = []

    def audit_all(self):
        """Run complete audit of all converter files."""
        print("🔍 Auditing converter dependency compliance...")

        # Find all Python files in converters directory
        py_files = list(self.src_path.rglob("*.py"))
        print(f"Found {len(py_files)} Python files to audit")

        for file_path in py_files:
            if file_path.name == "__init__.py":
                continue

            print(f"\n📁 Auditing {file_path}")
            self.audit_file(file_path)

        self.print_summary()
        return self.issues

    def audit_file(self, file_path: Path):
        """Audit a single file for converter compliance."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse the AST
            tree = ast.parse(content, filename=str(file_path))

            # Find all class definitions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self.audit_class(node, file_path, content)

        except Exception as e:
            self.issues.append({
                'file': str(file_path),
                'type': 'parse_error',
                'message': f"Failed to parse file: {str(e)}"
            })

    def audit_class(self, class_node: ast.ClassDef, file_path: Path, content: str):
        """Audit a single class for converter compliance."""
        class_name = class_node.name

        # Check if this class inherits from BaseConverter
        inherits_from_base = self.inherits_from_baseconverter(class_node)

        if not inherits_from_base:
            # Not a converter, skip
            return

        print(f"  ✓ Found converter: {class_name}")

        # Find __init__ method
        init_method = None
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                init_method = node
                break

        if not init_method:
            self.issues.append({
                'file': str(file_path),
                'class': class_name,
                'type': 'missing_init',
                'message': f"Converter {class_name} inherits from BaseConverter but has no __init__ method"
            })
            return

        # Audit the __init__ method
        self.audit_init_method(init_method, class_name, file_path)

    def inherits_from_baseconverter(self, class_node: ast.ClassDef) -> bool:
        """Check if class inherits from BaseConverter."""
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseConverter":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "BaseConverter":
                return True
        return False

    def audit_init_method(self, init_node: ast.FunctionDef, class_name: str, file_path: Path):
        """Audit the __init__ method of a converter."""
        args = init_node.args.args

        # Skip 'self' parameter
        if len(args) < 2:
            self.issues.append({
                'file': str(file_path),
                'class': class_name,
                'type': 'missing_services_param',
                'message': f"__init__ method missing 'services' parameter"
            })
            return

        # Check if second parameter is 'services'
        services_param = args[1]  # First is 'self', second should be 'services'

        if services_param.arg != "services":
            self.issues.append({
                'file': str(file_path),
                'class': class_name,
                'type': 'wrong_param_name',
                'message': f"Second parameter should be 'services', got '{services_param.arg}'"
            })

        # Check if services parameter has correct type annotation
        if not services_param.annotation:
            self.issues.append({
                'file': str(file_path),
                'class': class_name,
                'type': 'missing_type_annotation',
                'message': f"'services' parameter missing type annotation"
            })
        else:
            # Check if it's the correct type
            type_name = self.get_annotation_name(services_param.annotation)
            if type_name != "ConversionServices":
                self.issues.append({
                    'file': str(file_path),
                    'class': class_name,
                    'type': 'wrong_type_annotation',
                    'message': f"'services' parameter should be ConversionServices, got {type_name}"
                })

        # Check if services has a default value (it shouldn't for BaseConverter compliance)
        defaults = init_node.args.defaults
        if len(defaults) >= len(args) - 1:  # -1 for 'self'
            # Services parameter has a default value
            services_default_index = 1 - (len(args) - len(defaults))  # Calculate index in defaults
            if services_default_index >= 0:
                default_value = defaults[services_default_index]
                if isinstance(default_value, ast.Constant) and default_value.value is None:
                    self.issues.append({
                        'file': str(file_path),
                        'class': class_name,
                        'type': 'optional_services',
                        'message': f"'services' parameter should be mandatory, not optional (services=None)"
                    })

    def get_annotation_name(self, annotation) -> str:
        """Get the name of a type annotation."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            return annotation.attr
        else:
            return str(annotation)

    def print_summary(self):
        """Print summary of audit results."""
        print(f"\n{'='*60}")
        print(f"🔍 CONVERTER DEPENDENCY AUDIT RESULTS")
        print(f"{'='*60}")

        if not self.issues:
            print("✅ All converters comply with dependency injection requirements!")
            return

        # Group issues by type
        issues_by_type = {}
        for issue in self.issues:
            issue_type = issue['type']
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)

        print(f"❌ Found {len(self.issues)} compliance issues:")
        print()

        for issue_type, issues in issues_by_type.items():
            print(f"🔸 {issue_type.upper().replace('_', ' ')}: {len(issues)} issues")
            for issue in issues:
                class_name = issue.get('class', 'N/A')
                file_name = Path(issue['file']).name
                print(f"   • {class_name} in {file_name}: {issue['message']}")
            print()

        print("💡 RECOMMENDATIONS:")
        print("1. Add ConversionServices type annotation: def __init__(self, services: ConversionServices)")
        print("2. Make services parameter mandatory (no default None)")
        print("3. Call super().__init__(services) in constructor")
        print("4. Import ConversionServices from core.services.conversion_services")


if __name__ == "__main__":
    auditor = ConverterAuditor()
    issues = auditor.audit_all()

    if issues:
        exit(1)  # Indicate failure for CI/CD
    else:
        exit(0)  # Success
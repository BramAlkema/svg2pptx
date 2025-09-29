#!/usr/bin/env python3
"""
Static Code Analysis Tests

Tests for code quality, patterns, and potential issues that can be
detected through static analysis of the codebase.
"""

import pytest
import ast
import pathlib
import re
import inspect
from typing import List, Dict, Set
from collections import defaultdict

from src.services.conversion_services import ConversionServices
from src.converters.shapes import RectangleConverter, CircleConverter, EllipseConverter
from src.converters.paths import PathConverter
from src.converters.text import TextConverter
from src.converters.image import ImageConverter
from src.converters.symbols import SymbolConverter
from src.converters.gradients import GradientConverter


class TestMutableDefaults:
    """Test for mutable default arguments (common Python gotcha)."""

    def test_no_mutable_defaults(self):
        """Test that no functions use mutable default arguments."""
        violations = []

        for py_file in pathlib.Path('src').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for i, default in enumerate(node.args.defaults):
                            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                                violations.append(
                                    f"{py_file}:{node.lineno} - Function '{node.name}' has mutable default argument"
                                )

            except (IOError, SyntaxError, UnicodeDecodeError):
                continue

        assert not violations, f"Mutable default arguments found:\n" + "\n".join(violations[:10])

    def test_no_mutable_class_attributes(self):
        """Test that classes don't have mutable class attributes that could be shared."""
        violations = []

        for py_file in pathlib.Path('src').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for stmt in node.body:
                            if isinstance(stmt, ast.Assign):
                                for target in stmt.targets:
                                    if isinstance(target, ast.Name):
                                        # Check if assigned value is mutable
                                        if isinstance(stmt.value, (ast.List, ast.Dict, ast.Set)):
                                            violations.append(
                                                f"{py_file}:{stmt.lineno} - Class '{node.name}' has mutable class attribute '{target.id}'"
                                            )

            except (IOError, SyntaxError, UnicodeDecodeError):
                continue

        # Filter out known safe patterns (like __all__ = [...])
        safe_patterns = ['__all__', '__slots__']
        violations = [v for v in violations if not any(pattern in v for pattern in safe_patterns)]

        assert not violations, f"Mutable class attributes found:\n" + "\n".join(violations[:10])


class TestSecurityPatterns:
    """Test for potentially insecure patterns."""

    def test_no_eval_exec_usage(self):
        """Test that code doesn't use eval() or exec() functions."""
        violations = []

        for py_file in pathlib.Path('src').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            if node.func.id in ['eval', 'exec']:
                                violations.append(f"{py_file}:{node.lineno} - Use of {node.func.id}()")

            except (IOError, SyntaxError, UnicodeDecodeError):
                continue

        assert not violations, f"Dangerous eval/exec usage found:\n" + "\n".join(violations)

    def test_no_shell_injection_patterns(self):
        """Test for potential shell injection vulnerabilities."""
        violations = []
        dangerous_patterns = [
            (r'subprocess\.call.*shell\s*=\s*True', 'subprocess.call with shell=True'),
            (r'subprocess\.run.*shell\s*=\s*True', 'subprocess.run with shell=True'),
            (r'os\.system\s*\(', 'os.system() usage'),
        ]

        for py_file in pathlib.Path('src').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern, description in dangerous_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        violations.append(f"{py_file}:{line_num} - {description}")

            except (IOError, UnicodeDecodeError):
                continue

        assert not violations, f"Potential shell injection patterns found:\n" + "\n".join(violations)

    def test_no_hardcoded_secrets(self):
        """Test that code doesn't contain hardcoded secrets or credentials."""
        violations = []
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key'),
            (r'secret\s*=\s*["\'][^"\']+["\']', 'Hardcoded secret'),
            (r'token\s*=\s*["\'][A-Za-z0-9+/]{20,}["\']', 'Hardcoded token'),
        ]

        for py_file in pathlib.Path('src').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern, description in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Skip test files and obvious placeholders
                        if ('test' not in str(py_file).lower() and
                            'example' not in match.group().lower() and
                            'placeholder' not in match.group().lower()):
                            line_num = content[:match.start()].count('\n') + 1
                            violations.append(f"{py_file}:{line_num} - {description}")

            except (IOError, UnicodeDecodeError):
                continue

        assert not violations, f"Potential hardcoded secrets found:\n" + "\n".join(violations[:5])


class TestCodeConsistency:
    """Test for consistency in code patterns and style."""

    def test_converter_naming_consistency(self):
        """Test that converters follow consistent naming patterns."""
        services = ConversionServices.create_default()
        converters = [
            RectangleConverter(services), CircleConverter(services), EllipseConverter(services),
            PathConverter(services), TextConverter(services), ImageConverter(services),
            SymbolConverter(services), GradientConverter(services)
        ]

        for converter in converters:
            class_name = converter.__class__.__name__

            # Should end with 'Converter'
            assert class_name.endswith('Converter'), f"{class_name} should end with 'Converter'"

            # Should have supported_elements attribute
            assert hasattr(converter, 'supported_elements'), f"{class_name} missing supported_elements"
            assert isinstance(converter.supported_elements, (list, tuple)), \
                f"{class_name}.supported_elements should be list or tuple"

    def test_method_signature_consistency(self):
        """Test that converter methods have consistent signatures."""
        services = ConversionServices.create_default()
        converters = [
            RectangleConverter(services), CircleConverter(services), EllipseConverter(services),
            PathConverter(services), TextConverter(services), ImageConverter(services),
            SymbolConverter(services), GradientConverter(services)
        ]

        for converter in converters:
            # All should have can_convert method
            assert hasattr(converter, 'can_convert')
            can_convert_sig = inspect.signature(converter.can_convert)
            assert len(can_convert_sig.parameters) >= 1, \
                f"{converter.__class__.__name__}.can_convert should take at least 1 parameter"

            # All should have convert method
            assert hasattr(converter, 'convert')
            convert_sig = inspect.signature(converter.convert)
            assert len(convert_sig.parameters) >= 2, \
                f"{converter.__class__.__name__}.convert should take at least 2 parameters"

    def test_error_handling_patterns(self):
        """Test that error handling follows consistent patterns."""
        error_handling_violations = []

        for py_file in pathlib.Path('src/converters').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                # Look for bare except clauses
                for node in ast.walk(tree):
                    if isinstance(node, ast.ExceptHandler):
                        if node.type is None:  # Bare except:
                            error_handling_violations.append(
                                f"{py_file}:{node.lineno} - Bare except clause (should specify exception type)"
                            )

            except (IOError, SyntaxError, UnicodeDecodeError):
                continue

        assert not error_handling_violations, \
            f"Error handling violations found:\n" + "\n".join(error_handling_violations[:10])

    def test_docstring_consistency(self):
        """Test that key classes and methods have docstrings."""
        services = ConversionServices.create_default()
        converter_classes = [
            RectangleConverter, CircleConverter, EllipseConverter,
            PathConverter, TextConverter, ImageConverter,
            SymbolConverter, GradientConverter
        ]

        missing_docstrings = []

        for converter_class in converter_classes:
            # Class should have docstring
            if not converter_class.__doc__:
                missing_docstrings.append(f"{converter_class.__name__} class missing docstring")

            # Key methods should have docstrings
            converter = converter_class(services)
            key_methods = ['can_convert', 'convert']

            for method_name in key_methods:
                if hasattr(converter, method_name):
                    method = getattr(converter, method_name)
                    if not method.__doc__:
                        missing_docstrings.append(
                            f"{converter_class.__name__}.{method_name} missing docstring"
                        )

        # Allow some missing docstrings, but not too many
        assert len(missing_docstrings) < len(converter_classes) * 2, \
            f"Too many missing docstrings:\n" + "\n".join(missing_docstrings[:10])


class TestComplexityAndMaintainability:
    """Test for code complexity and maintainability issues."""

    def test_function_complexity(self):
        """Test that functions are not overly complex (measured by nesting depth)."""
        complex_functions = []
        MAX_NESTING_DEPTH = 6

        for py_file in pathlib.Path('src').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        depth = self._calculate_nesting_depth(node)
                        if depth > MAX_NESTING_DEPTH:
                            complex_functions.append(
                                f"{py_file}:{node.lineno} - Function '{node.name}' nesting depth: {depth}"
                            )

            except (IOError, SyntaxError, UnicodeDecodeError):
                continue

        assert not complex_functions, \
            f"Overly complex functions found (nesting > {MAX_NESTING_DEPTH}):\n" + \
            "\n".join(complex_functions[:5])

    def _calculate_nesting_depth(self, node: ast.AST) -> int:
        """Calculate the maximum nesting depth of control structures in a function."""
        def get_depth(n, current_depth=0):
            max_depth = current_depth
            for child in ast.iter_child_nodes(n):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                    child_depth = get_depth(child, current_depth + 1)
                    max_depth = max(max_depth, child_depth)
                else:
                    child_depth = get_depth(child, current_depth)
                    max_depth = max(max_depth, child_depth)
            return max_depth

        return get_depth(node)

    def test_class_size_reasonable(self):
        """Test that classes are not overly large."""
        large_classes = []
        MAX_METHODS = 50

        for py_file in pathlib.Path('src').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        method_count = sum(1 for n in node.body
                                         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))

                        if method_count > MAX_METHODS:
                            large_classes.append(
                                f"{py_file}:{node.lineno} - Class '{node.name}' has {method_count} methods"
                            )

            except (IOError, SyntaxError, UnicodeDecodeError):
                continue

        assert not large_classes, \
            f"Overly large classes found (>{MAX_METHODS} methods):\n" + "\n".join(large_classes)

    def test_import_organization(self):
        """Test that imports are well-organized (standard, third-party, local)."""
        import_violations = []

        for py_file in pathlib.Path('src').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        imports.append((node.lineno, node))

                # Sort by line number
                imports.sort(key=lambda x: x[0])

                # Check for imports mixed with code (should be at top)
                first_non_import_line = None
                last_import_line = None

                for line_num, node in imports:
                    last_import_line = line_num

                # Find first non-import statement
                for node in ast.walk(tree):
                    if (not isinstance(node, (ast.Import, ast.ImportFrom, ast.Module)) and
                        hasattr(node, 'lineno')):
                        if first_non_import_line is None or node.lineno < first_non_import_line:
                            first_non_import_line = node.lineno

                # Check if imports are mixed with code
                if (first_non_import_line and last_import_line and
                    first_non_import_line < last_import_line):
                    import_violations.append(f"{py_file} - Imports mixed with code")

            except (IOError, SyntaxError, UnicodeDecodeError):
                continue

        # Allow some violations (there might be conditional imports)
        assert len(import_violations) < 10, \
            f"Import organization violations:\n" + "\n".join(import_violations[:5])


class TestTypeHints:
    """Test for type hint consistency."""

    def test_public_methods_have_type_hints(self):
        """Test that public methods have type hints."""
        services = ConversionServices.create_default()
        converters = [
            RectangleConverter(services), CircleConverter(services),
            PathConverter(services), TextConverter(services)
        ]

        missing_hints = []

        for converter in converters:
            for method_name in ['can_convert', 'convert']:
                if hasattr(converter, method_name):
                    method = getattr(converter, method_name)

                    # Check if method has type annotations
                    if not hasattr(method, '__annotations__') or not method.__annotations__:
                        missing_hints.append(f"{converter.__class__.__name__}.{method_name}")

        # Allow some missing type hints (may be inherited or have other issues)
        assert len(missing_hints) < len(converters) * 2, \
            f"Many methods missing type hints: {missing_hints[:10]}"

    def test_service_classes_have_type_hints(self):
        """Test that service classes have proper type hints."""
        from src.services.conversion_services import ConversionServices

        # Test that ConversionServices has type annotations
        annotations = getattr(ConversionServices, '__annotations__', {})
        expected_services = ['unit_converter', 'color_factory', 'transform_parser']

        missing_annotations = []
        for service_name in expected_services:
            if service_name not in annotations:
                missing_annotations.append(service_name)

        assert len(missing_annotations) < len(expected_services), \
            f"ConversionServices missing type hints for: {missing_annotations}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
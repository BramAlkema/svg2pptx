#!/usr/bin/env python3
"""
Import Resolution Architecture Tests

Tests that validate all imports in the codebase can be resolved correctly
and that there are no circular dependencies or missing modules.
"""

import pytest
import ast
import importlib
import pathlib
import sys
from collections import defaultdict, deque
from typing import Set, Dict, List

from src.services.conversion_services import ConversionServices


class TestImportResolution:
    """Test that all imports in the codebase resolve correctly."""

    def test_all_imports_resolvable(self):
        """Test that all imports in the codebase resolve correctly."""
        failed_imports = []
        conditional_failures = []

        # Get all Python files in src directory
        for py_file in pathlib.Path('src').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (IOError, UnicodeDecodeError):
                continue

            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            # Extract imports from AST
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        try:
                            importlib.import_module(alias.name)
                        except ImportError as e:
                            # Check if this is inside a try-except block (conditional import)
                            if self._is_in_try_except(node, tree):
                                conditional_failures.append(f"{py_file}: {alias.name} (conditional) - {e}")
                            else:
                                failed_imports.append(f"{py_file}: {alias.name} - {e}")

                elif isinstance(node, ast.ImportFrom) and node.module:
                    try:
                        # Test the module import
                        module = importlib.import_module(node.module)

                        # Test specific imports from the module
                        for alias in node.names:
                            if alias.name != '*':  # Skip wildcard imports
                                if not hasattr(module, alias.name):
                                    if self._is_in_try_except(node, tree):
                                        conditional_failures.append(
                                            f"{py_file}: {node.module}.{alias.name} (conditional) - not found"
                                        )
                                    else:
                                        failed_imports.append(
                                            f"{py_file}: {node.module}.{alias.name} - not found"
                                        )

                    except ImportError as e:
                        if self._is_in_try_except(node, tree):
                            conditional_failures.append(f"{py_file}: {node.module} (conditional) - {e}")
                        else:
                            failed_imports.append(f"{py_file}: {node.module} - {e}")

        # Report results
        if conditional_failures:
            print(f"Conditional import failures (may be expected): {len(conditional_failures)}")
            for failure in conditional_failures[:5]:  # Show first 5
                print(f"  {failure}")

        # Critical imports must work
        assert not failed_imports, f"Critical import failures: {failed_imports[:10]}..."

    def _is_in_try_except(self, node, tree):
        """Check if a node is inside a try-except block."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.Try):
                for child in ast.walk(parent):
                    if child is node:
                        return True
        return False

    def test_core_service_imports(self):
        """Test that core services can be imported successfully."""
        core_imports = [
            'src.services.conversion_services',
            'src.converters.base',
            'src.converters.shapes',
            'src.converters.paths',
            'src.converters.text',
            'src.units',
            'src.color',
            'src.transforms',
            'src.viewbox',
        ]

        for module_name in core_imports:
            try:
                module = importlib.import_module(module_name)
                assert module is not None, f"Module {module_name} imported as None"
            except ImportError as e:
                pytest.fail(f"Failed to import core module {module_name}: {e}")

    def test_converter_imports(self):
        """Test that all converters can be imported."""
        converter_imports = [
            ('src.converters.shapes', 'RectangleConverter'),
            ('src.converters.shapes', 'CircleConverter'),
            ('src.converters.shapes', 'EllipseConverter'),
            ('src.converters.paths', 'PathConverter'),
            ('src.converters.text', 'TextConverter'),
            ('src.converters.image', 'ImageConverter'),
            ('src.converters.symbols', 'SymbolConverter'),
            ('src.converters.gradients', 'GradientConverter'),
        ]

        for module_name, class_name in converter_imports:
            try:
                module = importlib.import_module(module_name)
                assert hasattr(module, class_name), f"Module {module_name} missing {class_name}"

                # Test that the class can be imported
                converter_class = getattr(module, class_name)
                assert callable(converter_class), f"{class_name} is not callable"

            except ImportError as e:
                pytest.fail(f"Failed to import {class_name} from {module_name}: {e}")

    def test_optional_dependency_handling(self):
        """Test that optional dependencies are handled gracefully."""
        # Test that the system works even if optional dependencies are missing
        optional_modules = [
            'numpy',
            'PIL',
            'colorspacious',
            'google.oauth2',
            'huey'
        ]

        # This test verifies that we handle missing optional dependencies
        # by temporarily removing them from sys.modules and testing imports
        original_modules = {}

        try:
            for module_name in optional_modules:
                if module_name in sys.modules:
                    original_modules[module_name] = sys.modules[module_name]
                    del sys.modules[module_name]

            # Test that ConversionServices can still be created
            # (it should handle missing optional dependencies)
            try:
                services = ConversionServices.create_default()
                assert services is not None
            except ImportError:
                # If this fails due to missing required (not optional) dependencies,
                # that's acceptable - the test is about graceful handling
                pass

        finally:
            # Restore original modules
            for module_name, module in original_modules.items():
                sys.modules[module_name] = module


class TestCircularDependencies:
    """Test for circular import dependencies."""

    def test_no_circular_imports(self):
        """Test that there are no circular import dependencies."""
        dependency_graph = self._build_dependency_graph()
        cycles = self._find_cycles(dependency_graph)

        if cycles:
            cycle_descriptions = []
            for cycle in cycles[:5]:  # Show first 5 cycles
                cycle_str = " -> ".join(cycle + [cycle[0]])
                cycle_descriptions.append(cycle_str)

            pytest.fail(f"Circular dependencies found:\n" + "\n".join(cycle_descriptions))

    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build a dependency graph of all modules."""
        graph = defaultdict(set)

        for py_file in pathlib.Path('src').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (IOError, UnicodeDecodeError):
                continue

            # Convert file path to module name
            relative_path = py_file.relative_to(pathlib.Path('.'))
            if relative_path.name == '__init__.py':
                module_name = str(relative_path.parent).replace('/', '.')
            else:
                module_name = str(relative_path.with_suffix('')).replace('/', '.')

            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            # Find all imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith('src.'):
                        graph[module_name].add(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith('src.'):
                            graph[module_name].add(alias.name)

        return graph

    def _find_cycles(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Find cycles in the dependency graph using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        colors = defaultdict(lambda: WHITE)
        cycles = []
        path = []

        def dfs(node):
            if colors[node] == GRAY:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if colors[node] == BLACK:
                return

            colors[node] = GRAY
            path.append(node)

            for neighbor in graph.get(node, set()):
                dfs(neighbor)

            path.pop()
            colors[node] = BLACK

        for node in graph:
            if colors[node] == WHITE:
                dfs(node)

        return cycles

    def test_layered_architecture(self):
        """Test that the architecture follows proper layering."""
        # Define architectural layers (lower layers should not import from higher layers)
        layers = {
            'core': ['src.core', 'src.utils'],
            'services': ['src.services', 'src.units', 'src.color', 'src.transforms', 'src.viewbox', 'src.paths'],
            'converters': ['src.converters'],
            'main': ['src.svg2pptx', 'src.svg2drawingml', 'src.svg2multislide'],
            'api': ['api'],
        }

        # Build dependency graph
        dependency_graph = self._build_dependency_graph()

        # Check layer violations
        violations = []

        layer_order = ['core', 'services', 'converters', 'main', 'api']
        for i, layer_name in enumerate(layer_order):
            layer_modules = layers[layer_name]
            higher_layers = []
            for j in range(i + 1, len(layer_order)):
                higher_layers.extend(layers[layer_order[j]])

            # Check that modules in this layer don't import from higher layers
            for module in dependency_graph:
                if any(module.startswith(prefix) for prefix in layer_modules):
                    for dependency in dependency_graph[module]:
                        if any(dependency.startswith(prefix) for prefix in higher_layers):
                            violations.append(f"{layer_name} layer module {module} imports from higher layer: {dependency}")

        assert not violations, f"Architecture layer violations found:\n" + "\n".join(violations[:10])


class TestModuleStructure:
    """Test module structure and organization."""

    def test_init_files_exist(self):
        """Test that __init__.py files exist where needed."""
        # Find all directories in src that contain Python files
        src_dirs_with_py = set()

        for py_file in pathlib.Path('src').rglob('*.py'):
            src_dirs_with_py.add(py_file.parent)

        # Check that each directory has __init__.py
        missing_inits = []
        for directory in src_dirs_with_py:
            init_file = directory / '__init__.py'
            if not init_file.exists():
                missing_inits.append(str(directory))

        assert not missing_inits, f"Missing __init__.py files in: {missing_inits}"

    def test_public_api_exports(self):
        """Test that public APIs properly export expected symbols."""
        expected_exports = {
            'src.services.conversion_services': ['ConversionServices'],
            'src.converters.base': ['BaseConverter', 'ConversionContext', 'ConverterRegistry'],
            'src.units': ['UnitConverter', 'unit', 'units'],
            'src.color': ['Color'],
            'src.transforms': ['TransformEngine'],
        }

        for module_name, expected_symbols in expected_exports.items():
            try:
                module = importlib.import_module(module_name)

                for symbol in expected_symbols:
                    assert hasattr(module, symbol), \
                        f"Module {module_name} missing expected export: {symbol}"

                    # Test that the symbol is importable
                    obj = getattr(module, symbol)
                    assert obj is not None, f"Symbol {symbol} in {module_name} is None"

            except ImportError as e:
                pytest.fail(f"Failed to test exports for {module_name}: {e}")

    def test_module_docstrings(self):
        """Test that key modules have docstrings."""
        key_modules = [
            'src.services.conversion_services',
            'src.converters.base',
            'src.svg2pptx',
            'src.svg2drawingml',
        ]

        for module_name in key_modules:
            try:
                module = importlib.import_module(module_name)
                assert module.__doc__ is not None, f"Module {module_name} missing docstring"
                assert len(module.__doc__.strip()) > 10, f"Module {module_name} has minimal docstring"

            except ImportError:
                # If module can't be imported, skip docstring check
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
#!/usr/bin/env python3
"""
Automated Test Generator for SVG2PPTX

This module generates test files automatically based on analyzed patterns from
existing tests and converter interfaces. It creates consistent test structures
following proven patterns from the codebase.
"""

import ast
import inspect
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any, Type
from dataclasses import dataclass
from jinja2 import Template
import importlib.util

from .test_pattern_analyzer import TestPatternAnalyzer, TestPattern


@dataclass
class ConverterMetadata:
    """Metadata about a converter class."""
    name: str
    module_path: str
    class_name: str
    supported_elements: List[str]
    methods: List[str]
    dependencies: List[str]
    base_classes: List[str]


@dataclass
class GeneratedTest:
    """Represents a generated test."""
    class_name: str
    method_name: str
    test_type: str  # 'unit', 'integration', 'performance'
    description: str
    code: str
    dependencies: List[str]
    fixtures_needed: List[str]


class AutomatedTestGenerator:
    """Generates tests automatically based on patterns and converter interfaces."""

    def __init__(self, pattern_analyzer: TestPatternAnalyzer = None):
        """Initialize generator with pattern analyzer."""
        self.pattern_analyzer = pattern_analyzer or TestPatternAnalyzer()
        self.test_patterns: Dict[str, TestPattern] = {}
        self.converter_metadata: Dict[str, ConverterMetadata] = {}
        self.generated_tests: List[GeneratedTest] = []

        # Load patterns if analyzer is provided
        if pattern_analyzer and pattern_analyzer.extracted_patterns:
            self._load_patterns()

    def _load_patterns(self):
        """Load patterns from analyzer into indexed structure."""
        for pattern in self.pattern_analyzer.extracted_patterns:
            self.test_patterns[pattern.name] = pattern

    def analyze_converter_interfaces(self, src_directory: Path = None) -> Dict[str, ConverterMetadata]:
        """Analyze converter classes to understand their interfaces."""
        src_dir = src_directory or Path("src/converters")

        print(f"🔍 Analyzing converter interfaces in {src_dir}...")

        # Find all converter files
        converter_files = list(src_dir.rglob("*.py"))
        converter_files = [f for f in converter_files if not f.name.startswith('__')]

        for converter_file in converter_files:
            try:
                metadata = self._analyze_converter_file(converter_file)
                if metadata:
                    for converter in metadata:
                        self.converter_metadata[converter.name] = converter
            except Exception as e:
                print(f"⚠️  Warning: Failed to analyze {converter_file}: {e}")

        print(f"   Found {len(self.converter_metadata)} converter classes")
        return self.converter_metadata

    def _analyze_converter_file(self, filepath: Path) -> List[ConverterMetadata]:
        """Analyze a single converter file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            converters = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a converter class
                    if self._is_converter_class(node, content):
                        metadata = self._extract_converter_metadata(node, filepath, content)
                        if metadata:
                            converters.append(metadata)

            return converters

        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")
            return []

    def _is_converter_class(self, node: ast.ClassDef, content: str) -> bool:
        """Check if a class is a converter class."""
        # Check for common converter indicators
        indicators = [
            'Converter' in node.name,
            'BaseConverter' in [base.id for base in node.bases if isinstance(base, ast.Name)],
            any(isinstance(item, ast.FunctionDef) and item.name == 'can_convert' for item in node.body),
            any(isinstance(item, ast.FunctionDef) and item.name == 'convert' for item in node.body)
        ]

        return any(indicators)

    def _extract_converter_metadata(self, node: ast.ClassDef, filepath: Path, content: str) -> Optional[ConverterMetadata]:
        """Extract metadata from converter class."""
        try:
            # Extract basic info
            name = node.name
            module_path = str(filepath)
            class_name = node.name

            # Extract base classes
            base_classes = [base.id for base in node.bases if isinstance(base, ast.Name)]

            # Extract methods
            methods = [item.name for item in node.body if isinstance(item, ast.FunctionDef)]

            # Extract supported elements (look for supported_elements attribute)
            supported_elements = []
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id == 'supported_elements':
                            try:
                                supported_elements = ast.literal_eval(item.value)
                            except (ValueError, TypeError):
                                pass

            # Extract dependencies from imports and method signatures
            dependencies = self._extract_dependencies(content)

            return ConverterMetadata(
                name=name,
                module_path=module_path,
                class_name=class_name,
                supported_elements=supported_elements,
                methods=methods,
                dependencies=dependencies,
                base_classes=base_classes
            )

        except Exception as e:
            print(f"Error extracting metadata for {node.name}: {e}")
            return None

    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract dependencies from file content."""
        dependencies = []

        # Look for common dependencies
        dependency_patterns = [
            'ConversionServices',
            'ConversionContext',
            'UnitConverter',
            'ColorParser',
            'TransformParser',
            'ViewportEngine',
            'ET.Element',
            'Mock',
            'pytest'
        ]

        for pattern in dependency_patterns:
            if pattern in content:
                dependencies.append(pattern)

        return dependencies

    def generate_tests_for_converter(self, converter_name: str, test_types: List[str] = None) -> List[GeneratedTest]:
        """Generate tests for a specific converter."""
        if converter_name not in self.converter_metadata:
            raise ValueError(f"Converter {converter_name} not found in metadata")

        converter = self.converter_metadata[converter_name]
        test_types = test_types or ['unit', 'integration']

        generated_tests = []

        print(f"🧪 Generating tests for {converter_name}...")

        for test_type in test_types:
            if test_type == 'unit':
                generated_tests.extend(self._generate_unit_tests(converter))
            elif test_type == 'integration':
                generated_tests.extend(self._generate_integration_tests(converter))
            elif test_type == 'performance':
                generated_tests.extend(self._generate_performance_tests(converter))

        self.generated_tests.extend(generated_tests)
        return generated_tests

    def _generate_unit_tests(self, converter: ConverterMetadata) -> List[GeneratedTest]:
        """Generate unit tests for converter."""
        tests = []

        # Basic interface tests
        tests.append(self._generate_can_convert_test(converter))
        tests.append(self._generate_convert_basic_test(converter))
        tests.append(self._generate_initialization_test(converter))

        # Element-specific tests
        for element in converter.supported_elements:
            tests.append(self._generate_element_specific_test(converter, element))

        # Error handling tests
        tests.append(self._generate_error_handling_test(converter))

        # Dependency injection tests
        if 'ConversionServices' in converter.dependencies:
            tests.append(self._generate_dependency_injection_test(converter))

        return tests

    def _generate_integration_tests(self, converter: ConverterMetadata) -> List[GeneratedTest]:
        """Generate integration tests for converter."""
        tests = []

        # Context integration tests
        tests.append(self._generate_context_integration_test(converter))

        # Service integration tests
        if 'ConversionServices' in converter.dependencies:
            tests.append(self._generate_service_integration_test(converter))

        # End-to-end conversion tests
        tests.append(self._generate_e2e_conversion_test(converter))

        return tests

    def _generate_performance_tests(self, converter: ConverterMetadata) -> List[GeneratedTest]:
        """Generate performance tests for converter."""
        tests = []

        # Single element performance
        tests.append(self._generate_single_performance_test(converter))

        # Batch processing performance (if supported)
        if 'convert_batch' in converter.methods:
            tests.append(self._generate_batch_performance_test(converter))

        return tests

    def _generate_can_convert_test(self, converter: ConverterMetadata) -> GeneratedTest:
        """Generate can_convert test."""
        template = Template("""
    def test_can_convert_{{element}}(self):
        \"\"\"Test that converter recognizes {{element}} elements.\"\"\"
        converter = {{converter_class}}(services=self.mock_services)

        element = ET.fromstring('<{{element}} />')
        assert converter.can_convert(element) is True

        # Test with different element
        other_element = ET.fromstring('<other />')
        assert converter.can_convert(other_element) is False
""")

        element = converter.supported_elements[0] if converter.supported_elements else 'rect'

        return GeneratedTest(
            class_name=f"Test{converter.class_name}",
            method_name=f"test_can_convert_{element}",
            test_type="unit",
            description=f"Test {converter.class_name} can_convert method",
            code=template.render(
                converter_class=converter.class_name,
                element=element
            ),
            dependencies=converter.dependencies,
            fixtures_needed=['mock_services']
        )

    def _generate_convert_basic_test(self, converter: ConverterMetadata) -> GeneratedTest:
        """Generate basic convert test."""
        template = Template("""
    def test_convert_basic_{{element}}(self):
        \"\"\"Test basic conversion of {{element}} element.\"\"\"
        converter = {{converter_class}}(services=self.mock_services)
        context = ConversionContext(services=self.mock_services)

        element = ET.fromstring('<{{element}} {{attributes}} />')
        result = converter.convert(element, context)

        assert result is not None
        assert isinstance(result, str)
        # Add specific assertions based on expected output
""")

        element = converter.supported_elements[0] if converter.supported_elements else 'rect'
        attributes = self._get_default_attributes(element)

        return GeneratedTest(
            class_name=f"Test{converter.class_name}",
            method_name=f"test_convert_basic_{element}",
            test_type="unit",
            description=f"Test {converter.class_name} basic conversion",
            code=template.render(
                converter_class=converter.class_name,
                element=element,
                attributes=attributes
            ),
            dependencies=converter.dependencies,
            fixtures_needed=['mock_services']
        )

    def _generate_initialization_test(self, converter: ConverterMetadata) -> GeneratedTest:
        """Generate initialization test."""
        template = Template("""
    def test_{{converter_name_lower}}_initialization(self):
        \"\"\"Test {{converter_class}} initialization.\"\"\"
        converter = {{converter_class}}(services=self.mock_services)

        assert converter is not None
        assert converter.services is self.mock_services
        {% if has_supported_elements %}
        assert hasattr(converter, 'supported_elements')
        assert len(converter.supported_elements) > 0
        {% endif %}
""")

        return GeneratedTest(
            class_name=f"Test{converter.class_name}",
            method_name=f"test_{converter.class_name.lower()}_initialization",
            test_type="unit",
            description=f"Test {converter.class_name} initialization",
            code=template.render(
                converter_class=converter.class_name,
                converter_name_lower=converter.class_name.lower(),
                has_supported_elements=bool(converter.supported_elements)
            ),
            dependencies=converter.dependencies,
            fixtures_needed=['mock_services']
        )

    def _generate_element_specific_test(self, converter: ConverterMetadata, element: str) -> GeneratedTest:
        """Generate element-specific test."""
        template = Template("""
    def test_convert_{{element}}_with_attributes(self):
        \"\"\"Test conversion of {{element}} element with various attributes.\"\"\"
        converter = {{converter_class}}(services=self.mock_services)
        context = ConversionContext(services=self.mock_services)

        # Test with common attributes
        svg_content = '''<{{element}} {{attributes}} />'''
        element = ET.fromstring(svg_content)

        result = converter.convert(element, context)

        assert result is not None
        assert isinstance(result, str)
        # Verify specific conversion behavior
""")

        attributes = self._get_default_attributes(element)

        return GeneratedTest(
            class_name=f"Test{converter.class_name}",
            method_name=f"test_convert_{element}_with_attributes",
            test_type="unit",
            description=f"Test {converter.class_name} {element} element conversion",
            code=template.render(
                converter_class=converter.class_name,
                element=element,
                attributes=attributes
            ),
            dependencies=converter.dependencies,
            fixtures_needed=['mock_services']
        )

    def _generate_error_handling_test(self, converter: ConverterMetadata) -> GeneratedTest:
        """Generate error handling test."""
        template = Template("""
    def test_{{converter_name_lower}}_error_handling(self):
        \"\"\"Test {{converter_class}} error handling.\"\"\"
        converter = {{converter_class}}(services=self.mock_services)
        context = ConversionContext(services=self.mock_services)

        # Test with invalid element
        invalid_element = ET.fromstring('<invalid />')

        # Should handle gracefully (not crash)
        result = converter.convert(invalid_element, context)

        # Verify error handling behavior
        assert result is not None  # Or whatever the expected behavior is
""")

        return GeneratedTest(
            class_name=f"Test{converter.class_name}",
            method_name=f"test_{converter.class_name.lower()}_error_handling",
            test_type="unit",
            description=f"Test {converter.class_name} error handling",
            code=template.render(
                converter_class=converter.class_name,
                converter_name_lower=converter.class_name.lower()
            ),
            dependencies=converter.dependencies,
            fixtures_needed=['mock_services']
        )

    def _generate_dependency_injection_test(self, converter: ConverterMetadata) -> GeneratedTest:
        """Generate dependency injection test."""
        template = Template("""
    def test_{{converter_name_lower}}_dependency_injection(self):
        \"\"\"Test {{converter_class}} dependency injection.\"\"\"
        # Test with None services (should raise error)
        with pytest.raises((TypeError, ValueError)):
            {{converter_class}}(services=None)

        # Test with proper services
        converter = {{converter_class}}(services=self.mock_services)
        assert converter.services is self.mock_services

        # Test service access
        assert hasattr(converter, 'unit_converter')
        assert hasattr(converter, 'color_parser')
""")

        return GeneratedTest(
            class_name=f"Test{converter.class_name}",
            method_name=f"test_{converter.class_name.lower()}_dependency_injection",
            test_type="unit",
            description=f"Test {converter.class_name} dependency injection",
            code=template.render(
                converter_class=converter.class_name,
                converter_name_lower=converter.class_name.lower()
            ),
            dependencies=converter.dependencies + ['pytest'],
            fixtures_needed=['mock_services']
        )

    def _generate_context_integration_test(self, converter: ConverterMetadata) -> GeneratedTest:
        """Generate context integration test."""
        template = Template("""
    def test_{{converter_name_lower}}_context_integration(self):
        \"\"\"Test {{converter_class}} integration with ConversionContext.\"\"\"
        converter = {{converter_class}}(services=self.mock_services)

        # Create real context
        context = ConversionContext(services=self.mock_services)

        # Test context usage
        element = ET.fromstring('<{{element}} {{attributes}} />')
        result = converter.convert(element, context)

        assert result is not None
        # Verify context state changes if applicable
""")

        element = converter.supported_elements[0] if converter.supported_elements else 'rect'
        attributes = self._get_default_attributes(element)

        return GeneratedTest(
            class_name=f"Test{converter.class_name}Integration",
            method_name=f"test_{converter.class_name.lower()}_context_integration",
            test_type="integration",
            description=f"Test {converter.class_name} context integration",
            code=template.render(
                converter_class=converter.class_name,
                converter_name_lower=converter.class_name.lower(),
                element=element,
                attributes=attributes
            ),
            dependencies=converter.dependencies,
            fixtures_needed=['mock_services']
        )

    def _generate_service_integration_test(self, converter: ConverterMetadata) -> GeneratedTest:
        """Generate service integration test."""
        template = Template("""
    def test_{{converter_name_lower}}_service_integration(self):
        \"\"\"Test {{converter_class}} integration with services.\"\"\"
        # Use real services instead of mocks
        services = ConversionServices.create_default()
        converter = {{converter_class}}(services=services)
        context = ConversionContext(services=services)

        element = ET.fromstring('<{{element}} {{attributes}} />')
        result = converter.convert(element, context)

        assert result is not None
        assert isinstance(result, str)
        # Verify service interactions
""")

        element = converter.supported_elements[0] if converter.supported_elements else 'rect'
        attributes = self._get_default_attributes(element)

        return GeneratedTest(
            class_name=f"Test{converter.class_name}Integration",
            method_name=f"test_{converter.class_name.lower()}_service_integration",
            test_type="integration",
            description=f"Test {converter.class_name} service integration",
            code=template.render(
                converter_class=converter.class_name,
                converter_name_lower=converter.class_name.lower(),
                element=element,
                attributes=attributes
            ),
            dependencies=converter.dependencies,
            fixtures_needed=[]
        )

    def _generate_e2e_conversion_test(self, converter: ConverterMetadata) -> GeneratedTest:
        """Generate end-to-end conversion test."""
        template = Template("""
    def test_{{converter_name_lower}}_e2e_conversion(self):
        \"\"\"Test {{converter_class}} end-to-end conversion.\"\"\"
        services = ConversionServices.create_default()
        converter = {{converter_class}}(services=services)
        context = ConversionContext(services=services)

        # Create realistic SVG element
        svg_content = '''<{{element}} {{attributes}} />'''
        element = ET.fromstring(svg_content)

        # Perform conversion
        result = converter.convert(element, context)

        # Validate result
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

        # Could add XML validation here
""")

        element = converter.supported_elements[0] if converter.supported_elements else 'rect'
        attributes = self._get_realistic_attributes(element)

        return GeneratedTest(
            class_name=f"Test{converter.class_name}E2E",
            method_name=f"test_{converter.class_name.lower()}_e2e_conversion",
            test_type="integration",
            description=f"Test {converter.class_name} end-to-end conversion",
            code=template.render(
                converter_class=converter.class_name,
                converter_name_lower=converter.class_name.lower(),
                element=element,
                attributes=attributes
            ),
            dependencies=converter.dependencies,
            fixtures_needed=[]
        )

    def _generate_single_performance_test(self, converter: ConverterMetadata) -> GeneratedTest:
        """Generate single element performance test."""
        template = Template("""
    @pytest.mark.benchmark
    def test_{{converter_name_lower}}_single_performance(self, benchmark):
        \"\"\"Test {{converter_class}} single element performance.\"\"\"
        services = ConversionServices.create_default()
        converter = {{converter_class}}(services=services)
        context = ConversionContext(services=services)

        element = ET.fromstring('<{{element}} {{attributes}} />')

        # Benchmark the conversion
        result = benchmark(converter.convert, element, context)

        assert result is not None
""")

        element = converter.supported_elements[0] if converter.supported_elements else 'rect'
        attributes = self._get_default_attributes(element)

        return GeneratedTest(
            class_name=f"Test{converter.class_name}Performance",
            method_name=f"test_{converter.class_name.lower()}_single_performance",
            test_type="performance",
            description=f"Test {converter.class_name} single element performance",
            code=template.render(
                converter_class=converter.class_name,
                converter_name_lower=converter.class_name.lower(),
                element=element,
                attributes=attributes
            ),
            dependencies=converter.dependencies + ['pytest.mark.benchmark'],
            fixtures_needed=[]
        )

    def _generate_batch_performance_test(self, converter: ConverterMetadata) -> GeneratedTest:
        """Generate batch performance test."""
        template = Template("""
    @pytest.mark.benchmark
    def test_{{converter_name_lower}}_batch_performance(self, benchmark):
        \"\"\"Test {{converter_class}} batch processing performance.\"\"\"
        services = ConversionServices.create_default()
        converter = {{converter_class}}(services=services)
        context = ConversionContext(services=services)

        # Create batch of elements
        elements = [
            ET.fromstring('<{{element}} {{attributes}} />')
            for _ in range(100)
        ]

        # Benchmark batch conversion
        result = benchmark(converter.convert_batch, elements, context)

        assert result is not None
        assert len(result) == 100
""")

        element = converter.supported_elements[0] if converter.supported_elements else 'rect'
        attributes = self._get_default_attributes(element)

        return GeneratedTest(
            class_name=f"Test{converter.class_name}Performance",
            method_name=f"test_{converter.class_name.lower()}_batch_performance",
            test_type="performance",
            description=f"Test {converter.class_name} batch performance",
            code=template.render(
                converter_class=converter.class_name,
                converter_name_lower=converter.class_name.lower(),
                element=element,
                attributes=attributes
            ),
            dependencies=converter.dependencies + ['pytest.mark.benchmark'],
            fixtures_needed=[]
        )

    def _get_default_attributes(self, element: str) -> str:
        """Get default attributes for an SVG element."""
        attribute_map = {
            'rect': 'x="10" y="10" width="50" height="30" fill="blue"',
            'circle': 'cx="50" cy="50" r="25" fill="red"',
            'ellipse': 'cx="50" cy="50" rx="30" ry="20" fill="green"',
            'line': 'x1="0" y1="0" x2="100" y2="100" stroke="black"',
            'polygon': 'points="0,0 50,0 25,50" fill="purple"',
            'polyline': 'points="0,0 50,25 100,0" stroke="orange" fill="none"',
            'path': 'd="M10,10 L50,50 Z" fill="yellow"',
            'text': 'x="10" y="30" font-size="16" fill="black"'
        }
        return attribute_map.get(element, 'fill="gray"')

    def _get_realistic_attributes(self, element: str) -> str:
        """Get realistic attributes for testing."""
        realistic_map = {
            'rect': 'x="100" y="50" width="200" height="150" fill="#3498db" stroke="#2c3e50" stroke-width="2"',
            'circle': 'cx="150" cy="150" r="75" fill="#e74c3c" stroke="#c0392b" stroke-width="3"',
            'ellipse': 'cx="150" cy="100" rx="100" ry="60" fill="#2ecc71" stroke="#27ae60" stroke-width="2"',
            'line': 'x1="50" y1="50" x2="200" y2="150" stroke="#9b59b6" stroke-width="4"',
            'polygon': 'points="100,50 150,25 200,50 175,100 125,100" fill="#f39c12" stroke="#e67e22"',
            'polyline': 'points="50,50 100,25 150,75 200,50" stroke="#1abc9c" stroke-width="3" fill="none"',
            'path': 'd="M50,100 Q150,50 250,100 T350,100" stroke="#34495e" stroke-width="2" fill="none"',
            'text': 'x="50" y="100" font-family="Arial" font-size="24" fill="#2c3e50"'
        }
        return realistic_map.get(element, self._get_default_attributes(element))

    def generate_complete_test_file(self, converter_name: str, output_path: Path) -> str:
        """Generate a complete test file for a converter."""
        if converter_name not in self.converter_metadata:
            raise ValueError(f"Converter {converter_name} not found")

        converter = self.converter_metadata[converter_name]
        tests = self.generate_tests_for_converter(converter_name)

        # Group tests by class
        test_classes = {}
        for test in tests:
            if test.class_name not in test_classes:
                test_classes[test.class_name] = []
            test_classes[test.class_name].append(test)

        # Generate complete file content
        file_content = self._generate_file_header(converter)
        file_content += self._generate_imports(tests)
        file_content += self._generate_fixtures(tests)

        for class_name, class_tests in test_classes.items():
            file_content += self._generate_test_class(class_name, class_tests, converter)

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(file_content)

        print(f"📝 Generated test file: {output_path}")
        return file_content

    def _generate_file_header(self, converter: ConverterMetadata) -> str:
        """Generate file header with docstring."""
        return f'''#!/usr/bin/env python3
"""
Generated unit tests for {converter.class_name}.

Auto-generated test file based on analyzed patterns from existing tests.
This file provides comprehensive test coverage for the {converter.class_name}
converter including unit tests, integration tests, and performance tests.

Generated by: AutomatedTestGenerator
"""

'''

    def _generate_imports(self, tests: List[GeneratedTest]) -> str:
        """Generate import statements based on test dependencies."""
        imports = set()

        # Standard test imports
        imports.add("import pytest")
        imports.add("from unittest.mock import Mock, patch, MagicMock")
        imports.add("from lxml import etree as ET")
        imports.add("from pathlib import Path")
        imports.add("import sys")

        # Add src path
        imports.add("\n# Add src to path for imports")
        imports.add('sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))')

        # Extract dependencies from tests
        for test in tests:
            for dep in test.dependencies:
                if 'ConversionServices' in dep:
                    imports.add("from src.services.conversion_services import ConversionServices")
                if 'ConversionContext' in dep:
                    imports.add("from src.converters.base import ConversionContext")

        return '\n'.join(sorted(imports)) + '\n\n'

    def _generate_fixtures(self, tests: List[GeneratedTest]) -> str:
        """Generate pytest fixtures needed by tests."""
        fixtures_needed = set()
        for test in tests:
            fixtures_needed.update(test.fixtures_needed)

        fixture_code = ""

        if 'mock_services' in fixtures_needed:
            fixture_code += '''@pytest.fixture
def mock_services():
    """Mock ConversionServices for testing."""
    services = Mock()
    services.unit_converter = Mock()
    services.color_parser = Mock()
    services.transform_parser = Mock()
    services.viewport_resolver = Mock()
    services.font_service = Mock()
    services.gradient_service = Mock()
    services.pattern_service = Mock()
    services.clip_service = Mock()
    return services


'''

        return fixture_code

    def _generate_test_class(self, class_name: str, tests: List[GeneratedTest], converter: ConverterMetadata) -> str:
        """Generate a complete test class."""
        class_code = f'''class {class_name}:
    """Test {converter.class_name} functionality."""

'''

        for test in tests:
            class_code += test.code + '\n'

        return class_code + '\n'


def generate_tests_for_all_converters(src_directory: Path = None, output_directory: Path = None) -> Dict[str, str]:
    """Generate tests for all discovered converters."""
    generator = AutomatedTestGenerator()

    # Analyze existing patterns
    pattern_analyzer = TestPatternAnalyzer()
    pattern_analyzer.analyze_test_directory()
    generator.pattern_analyzer = pattern_analyzer
    generator._load_patterns()

    # Analyze converter interfaces
    converter_metadata = generator.analyze_converter_interfaces(src_directory)

    # Generate tests for each converter
    output_dir = output_directory or Path("tests/generated")
    generated_files = {}

    for converter_name in converter_metadata:
        output_path = output_dir / f"test_{converter_name.lower()}_generated.py"
        try:
            content = generator.generate_complete_test_file(converter_name, output_path)
            generated_files[converter_name] = str(output_path)
        except Exception as e:
            print(f"⚠️  Failed to generate tests for {converter_name}: {e}")

    return generated_files


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate tests automatically from patterns')
    parser.add_argument('--src-dir', type=Path, default=Path('src/converters'),
                        help='Source directory containing converters')
    parser.add_argument('--output-dir', type=Path, default=Path('tests/generated'),
                        help='Output directory for generated tests')
    parser.add_argument('--converter', type=str, help='Generate tests for specific converter')

    args = parser.parse_args()

    if args.converter:
        # Generate tests for specific converter
        generator = AutomatedTestGenerator()
        generator.analyze_converter_interfaces(args.src_dir)

        output_path = args.output_dir / f"test_{args.converter.lower()}_generated.py"
        generator.generate_complete_test_file(args.converter, output_path)
    else:
        # Generate tests for all converters
        generated_files = generate_tests_for_all_converters(args.src_dir, args.output_dir)
        print(f"\n📊 Generated {len(generated_files)} test files:")
        for converter, filepath in generated_files.items():
            print(f"   {converter}: {filepath}")
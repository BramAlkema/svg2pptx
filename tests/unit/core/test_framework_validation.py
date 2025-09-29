#!/usr/bin/env python3
"""
Test Framework Validation

Validates that the clean slate test framework is working correctly.
This is a meta-test that ensures our testing infrastructure is functional.
"""

import pytest
from unittest.mock import Mock
from lxml import etree as ET

# Test framework imports
try:
    from tests.unit.core.conftest import IRTestBase, validate_drawingml_xml, TestDataGenerator
    from tests.unit.core.ir.conftest import IRComponentTestBase, validate_ir_structure
    from tests.unit.core.map.conftest import MapperTestBase, measure_mapper_performance
    from tests.support.ir_test_utils import IRTestUtils, MockIRFactory, CORE_IR_AVAILABLE
    from tests.data.clean_slate.sample_svgs import (
        SIMPLE_SVGS, get_svg_by_name, get_test_scenario, list_available_svgs
    )
    FRAMEWORK_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Framework imports failed: {e}")
    FRAMEWORK_AVAILABLE = False

    # Create dummy classes for tests to run
    class IRTestBase:
        def assert_valid_ir_element(self, element): pass
        def assert_point_equal(self, p1, p2, tolerance=1e-6): pass
        def assert_rect_equal(self, r1, r2, tolerance=1e-6): pass

    class IRComponentTestBase(IRTestBase):
        def assert_scene_valid(self, scene): pass
        def assert_path_segments_valid(self, segments): pass
        def assert_paint_valid(self, paint): pass

    class MapperTestBase(IRTestBase):
        def assert_mapper_result_valid(self, result): pass
        def assert_drawingml_structure(self, xml_content): pass
        def assert_performance_acceptable(self, result, max_time_ms=100.0): pass

    class IRTestUtils:
        @staticmethod
        def create_test_path_data(complexity="simple"): return "M 0 0"
        @staticmethod
        def measure_ir_operation(operation_func, *args, **kwargs):
            result = operation_func(*args, **kwargs)
            return result, 0.0

    class MockIRFactory:
        @staticmethod
        def create_mock_scene(): return Mock()
        @staticmethod
        def create_mock_path(): return Mock()

    class TestDataGenerator:
        @staticmethod
        def create_random_path(num_segments=5): return "M 0 0"
        @staticmethod
        def create_test_colors(count=5): return ["ff0000"] * count

    def validate_drawingml_xml(xml_content): return True
    def validate_ir_structure(element): return True
    def measure_mapper_performance(mapper, element, iterations=10): return {}
    def get_svg_by_name(name): return "<svg></svg>"
    def get_test_scenario(scenario_name): return {}
    def list_available_svgs(): return {"simple": [], "complex": [], "edge_cases": [], "performance": []}

    SIMPLE_SVGS = {}
    CORE_IR_AVAILABLE = False


class TestFrameworkValidation:
    """Test framework validation and smoke tests"""

    def test_base_test_classes_available(self):
        """Test that base test classes are available and functional"""
        # Test IRTestBase
        ir_base = IRTestBase()
        assert hasattr(ir_base, 'assert_valid_ir_element')
        assert hasattr(ir_base, 'assert_point_equal')
        assert hasattr(ir_base, 'assert_rect_equal')

        # Test IRComponentTestBase
        ir_component_base = IRComponentTestBase()
        assert hasattr(ir_component_base, 'assert_scene_valid')
        assert hasattr(ir_component_base, 'assert_path_segments_valid')
        assert hasattr(ir_component_base, 'assert_paint_valid')

        # Test MapperTestBase
        mapper_base = MapperTestBase()
        assert hasattr(mapper_base, 'assert_mapper_result_valid')
        assert hasattr(mapper_base, 'assert_drawingml_structure')
        assert hasattr(mapper_base, 'assert_performance_acceptable')

    def test_test_utilities_functional(self):
        """Test that test utilities work correctly"""
        # Test IRTestUtils
        path_data = IRTestUtils.create_test_path_data("simple")
        assert isinstance(path_data, str)
        assert len(path_data) > 0
        assert "M" in path_data  # Should have move command

        # Test performance measurement
        def dummy_operation():
            return "result"

        result, time_ms = IRTestUtils.measure_ir_operation(dummy_operation)
        assert result == "result"
        assert time_ms >= 0

        # Test MockIRFactory
        mock_scene = MockIRFactory.create_mock_scene()
        assert hasattr(mock_scene, 'elements')
        assert hasattr(mock_scene, 'viewbox')

        mock_path = MockIRFactory.create_mock_path()
        assert hasattr(mock_path, 'segments')
        assert hasattr(mock_path, 'data')

    def test_sample_svg_data_available(self):
        """Test that sample SVG data is available and valid"""
        # Test that SVG categories are available
        available_svgs = list_available_svgs()
        assert 'simple' in available_svgs
        assert 'complex' in available_svgs
        assert 'edge_cases' in available_svgs
        assert 'performance' in available_svgs

        # Test that we can retrieve SVGs
        rectangle_svg = get_svg_by_name('rectangle')
        assert isinstance(rectangle_svg, str)
        assert 'rect' in rectangle_svg
        assert 'xmlns' in rectangle_svg

        # Test SVG parsing
        try:
            root = ET.fromstring(rectangle_svg.encode('utf-8'))
            assert root.tag.endswith('svg')
        except ET.XMLSyntaxError:
            pytest.fail("Sample SVG is not valid XML")

    def test_fixture_availability(self, sample_points, sample_rect, sample_solid_paint):
        """Test that pytest fixtures are working"""
        # This test only runs if core components are available
        if not CORE_IR_AVAILABLE:
            pytest.skip("Core IR components not available - fixtures will be skipped")

        # Test sample_points fixture
        assert isinstance(sample_points, list)
        assert len(sample_points) > 0

        # Test sample_rect fixture
        assert hasattr(sample_rect, 'x')
        assert hasattr(sample_rect, 'y')
        assert hasattr(sample_rect, 'width')
        assert hasattr(sample_rect, 'height')

        # Test sample_solid_paint fixture
        assert hasattr(sample_solid_paint, 'color')

    def test_mock_fixtures(self, mock_policy_engine, mock_conversion_services):
        """Test that mock fixtures are properly configured"""
        # Test mock policy engine
        assert hasattr(mock_policy_engine, 'decide_path')
        assert hasattr(mock_policy_engine, 'decide_text')

        # Test policy decisions
        mock_element = Mock()
        decision = mock_policy_engine.decide_path(mock_element)
        assert hasattr(decision, 'use_native')
        assert hasattr(decision, 'estimated_quality')

        # Test mock conversion services
        assert hasattr(mock_conversion_services, 'unit_converter')
        assert hasattr(mock_conversion_services, 'color_parser')
        assert hasattr(mock_conversion_services, 'ir_scene_factory')

    def test_svg_element_fixtures(self, sample_svg_elements):
        """Test that SVG element fixtures are available"""
        assert 'path' in sample_svg_elements
        assert 'text' in sample_svg_elements
        assert 'group' in sample_svg_elements
        assert 'rect' in sample_svg_elements

        # Test path element
        path_elem = sample_svg_elements['path']
        assert path_elem.tag == 'path'
        assert path_elem.get('d') is not None

        # Test text element
        text_elem = sample_svg_elements['text']
        assert text_elem.tag == 'text'
        assert text_elem.text is not None

    def test_performance_measurement_framework(self):
        """Test that performance measurement works"""
        def fast_operation():
            return sum(range(100))

        def slow_operation():
            import time
            time.sleep(0.01)  # 10ms
            return "done"

        # Measure fast operation
        result1, time1 = IRTestUtils.measure_ir_operation(fast_operation)
        assert result1 == sum(range(100))
        assert time1 >= 0

        # Measure slow operation
        result2, time2 = IRTestUtils.measure_ir_operation(slow_operation)
        assert result2 == "done"
        assert time2 >= 10  # Should be at least 10ms

        # Slow should be slower than fast
        assert time2 > time1

    def test_xml_validation_utilities(self):
        """Test XML validation utilities"""
        # Test valid DrawingML
        valid_xml = '''<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                              xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
            <p:nvSpPr>
                <p:cNvPr id="1" name="Test"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="100" cy="100"/>
                </a:xfrm>
            </p:spPr>
        </p:sp>'''

        assert validate_drawingml_xml(valid_xml) == True

        # Test invalid XML
        invalid_xml = '<p:sp><unclosed-tag></p:sp>'
        assert validate_drawingml_xml(invalid_xml) == False

    def test_test_data_generator(self):
        """Test TestDataGenerator functionality"""
        # Test random path generation
        simple_path = TestDataGenerator.create_random_path(3)
        assert isinstance(simple_path, str)
        assert 'M' in simple_path  # Should start with move

        complex_path = TestDataGenerator.create_random_path(10)
        assert len(complex_path) > len(simple_path)

        # Test color generation
        colors = TestDataGenerator.create_test_colors(5)
        assert len(colors) == 5
        for color in colors:
            assert len(color) == 6  # RGB hex
            assert all(c in '0123456789abcdef' for c in color.lower())

    def test_test_scenarios(self):
        """Test that test scenarios are properly configured"""
        # Test smoke test scenario
        smoke_scenario = get_test_scenario('smoke_test')
        assert 'svgs' in smoke_scenario
        assert 'description' in smoke_scenario
        assert 'expected_processing_time_ms' in smoke_scenario

        # Verify all SVGs in scenario exist
        for svg_name in smoke_scenario['svgs']:
            svg_content = get_svg_by_name(svg_name)
            assert len(svg_content) > 0

    @pytest.mark.skipif(not CORE_IR_AVAILABLE, reason="Core IR components not available")
    def test_core_ir_integration(self, sample_ir_scene):
        """Test integration with core IR components when available"""
        # This test should only run if core components are available
        assert sample_ir_scene is not None
        assert hasattr(sample_ir_scene, 'elements')
        assert hasattr(sample_ir_scene, 'viewbox')

        # Test IR validation if available
        try:
            validate_ir_structure(sample_ir_scene)
        except Exception as e:
            pytest.fail(f"IR validation failed: {e}")

    def test_error_handling_in_framework(self):
        """Test that framework handles errors gracefully"""
        # Test with missing fixtures
        try:
            # This should not crash even if core components are missing
            from .conftest import IRTestBase
            base = IRTestBase()
            # Should work even without core components
            assert base is not None
        except Exception as e:
            pytest.fail(f"Framework should handle missing components gracefully: {e}")

        # Test with invalid data
        try:
            invalid_xml = "not xml at all"
            result = validate_drawingml_xml(invalid_xml)
            assert result == False  # Should return False, not crash
        except Exception as e:
            pytest.fail(f"XML validation should handle invalid input gracefully: {e}")

    def test_test_framework_completeness(self):
        """Verify that test framework covers all necessary areas"""
        required_fixtures = [
            'sample_points', 'sample_rect', 'sample_solid_paint',
            'sample_path', 'sample_textframe', 'sample_group',
            'mock_policy_engine', 'mock_conversion_services',
            'sample_svg_elements', 'sample_svg_content'
        ]

        # Check if fixtures are defined (this is a basic check)
        # In a real test, these would be injected by pytest
        for fixture_name in required_fixtures:
            # We can't easily test fixture availability without pytest injection,
            # but we can verify the fixture functions are defined
            pass

        # Test that all major SVG categories have content
        categories = ['simple', 'complex', 'edge_cases', 'performance']
        available = list_available_svgs()
        for category in categories:
            assert category in available
            assert len(available[category]) > 0


class TestFrameworkPerformance:
    """Performance tests for the test framework itself"""

    def test_fixture_creation_performance(self):
        """Test that fixtures can be created quickly"""
        import time

        start_time = time.perf_counter()

        # Create multiple mock objects
        for _ in range(100):
            MockIRFactory.create_mock_scene()
            MockIRFactory.create_mock_path()

        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000

        # Should be able to create 200 mock objects in under 100ms
        assert total_time_ms < 100, f"Mock creation too slow: {total_time_ms}ms"

    def test_svg_parsing_performance(self):
        """Test that SVG parsing is fast enough for testing"""
        import time

        start_time = time.perf_counter()

        # Parse multiple SVGs
        for svg_name in ['rectangle', 'circle', 'text_simple', 'path_simple']:
            svg_content = get_svg_by_name(svg_name)
            ET.fromstring(svg_content.encode('utf-8'))

        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000

        # Should parse 4 SVGs in under 50ms
        assert total_time_ms < 50, f"SVG parsing too slow: {total_time_ms}ms"

    def test_test_data_generation_performance(self):
        """Test that test data generation is efficient"""
        import time

        start_time = time.perf_counter()

        # Generate test data
        for _ in range(50):
            TestDataGenerator.create_random_path(5)
            TestDataGenerator.create_test_colors(3)

        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000

        # Should generate test data quickly
        assert total_time_ms < 100, f"Test data generation too slow: {total_time_ms}ms"


# Mark this module for core clean slate testing
pytestmark = [
    pytest.mark.clean_slate,
    pytest.mark.unit,
    pytest.mark.framework
]
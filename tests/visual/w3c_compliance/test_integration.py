#!/usr/bin/env python3
"""
W3C Compliance Integration Tests

Comprehensive test suite for W3C SVG compliance testing infrastructure.
Includes unit tests, integration tests, and end-to-end compliance testing.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Import modules to test
from .w3c_test_manager import W3CTestSuiteManager, W3CTestCase
from .libreoffice_controller import LibreOfficePlaywrightController, LibreOfficeConfig
from .svg_pptx_comparator import SVGPPTXComparator, ComplianceLevel
from .compliance_runner import W3CComplianceTestRunner, ComplianceConfig, TestSuite


# Test Fixtures

@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_svg_content():
    """Simple SVG content for testing."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <rect x="50" y="50" width="100" height="100" fill="blue" stroke="black" stroke-width="2"/>
    <circle cx="100" cy="100" r="30" fill="red" opacity="0.7"/>
    <text x="100" y="180" text-anchor="middle" font-family="Arial" font-size="14">W3C Test</text>
</svg>'''


@pytest.fixture
def sample_svg_file(temp_dir, sample_svg_content):
    """Create sample SVG file for testing."""
    svg_path = temp_dir / "test_basic_shapes.svg"
    svg_path.write_text(sample_svg_content)
    return svg_path


@pytest.fixture
def mock_test_case(sample_svg_file):
    """Create mock W3C test case."""
    return W3CTestCase(
        name="test_basic_shapes",
        category="basic-shapes",
        svg_path=sample_svg_file,
        description="Test basic shapes rendering",
        tags={"basic", "shapes"},
        difficulty="basic",
        expected_features={"rect", "circle", "text"}
    )


@pytest.fixture
def compliance_config(temp_dir):
    """Test compliance configuration."""
    return ComplianceConfig(
        test_suite=TestSuite.BASIC,
        w3c_version="1.1",
        max_tests=5,
        comparison_tolerance=0.80,
        output_dir=temp_dir / "compliance_results",
        libreoffice_headless=True,
        libreoffice_port=8101  # Different port to avoid conflicts
    )


# Unit Tests

class TestW3CTestSuiteManager:
    """Test W3C test suite management."""

    def test_init(self, temp_dir):
        """Test manager initialization."""
        manager = W3CTestSuiteManager(temp_dir / "test_data")
        assert manager.test_data_dir.name == "test_data"
        assert not manager.is_loaded

    @patch('requests.get')
    def test_download_test_suite_mock(self, mock_get, temp_dir):
        """Test test suite download with mocked response."""
        # Mock response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {'content-length': '1000'}
        mock_response.iter_content.return_value = [b'fake zip content']
        mock_get.return_value = mock_response

        manager = W3CTestSuiteManager(temp_dir)

        # Mock extraction to avoid dealing with real ZIP
        with patch.object(manager, '_extract_test_suite', return_value=True):
            result = manager.download_test_suite("1.1")
            assert result is True

    def test_get_categories(self, temp_dir):
        """Test category retrieval."""
        manager = W3CTestSuiteManager(temp_dir)

        # Mock some test cases
        manager._categories = {
            "basic-shapes": ["test1", "test2"],
            "paths": ["test3"]
        }

        categories = manager.get_categories()
        assert "basic-shapes" in categories
        assert categories["basic-shapes"]["test_count"] == 2

    def test_get_basic_compliance_suite(self, temp_dir):
        """Test basic compliance suite selection."""
        manager = W3CTestSuiteManager(temp_dir)

        # Mock test cases
        manager._test_cases = {
            "basic-shapes-circle": Mock(name="basic-shapes-circle"),
            "other-test": Mock(name="other-test")
        }

        suite = manager.get_basic_compliance_suite()
        # Should return empty list since mocked test cases don't match expected names
        assert isinstance(suite, list)


class TestLibreOfficeController:
    """Test LibreOffice automation controller."""

    def test_init(self):
        """Test controller initialization."""
        config = LibreOfficeConfig(headless=True, port=8102)
        controller = LibreOfficePlaywrightController(config)

        assert controller.config.headless is True
        assert controller.config.port == 8102
        assert not controller.is_running

    def test_build_soffice_command(self):
        """Test LibreOffice command building."""
        config = LibreOfficeConfig(headless=True, port=8103)
        controller = LibreOfficePlaywrightController(config)

        cmd = controller._build_soffice_command()
        assert 'soffice' in cmd
        assert '--headless' in cmd
        assert any('8103' in arg for arg in cmd)

    @pytest.mark.asyncio
    async def test_kill_existing_processes(self):
        """Test killing existing LibreOffice processes."""
        controller = LibreOfficePlaywrightController()

        # This should not raise an exception
        await controller._kill_existing_processes()


class TestSVGPPTXComparator:
    """Test SVG to PPTX visual comparison."""

    def test_init(self):
        """Test comparator initialization."""
        comparator = SVGPPTXComparator(tolerance=0.90)
        assert comparator.tolerance == 0.90

    def test_normalize_image_sizes(self, temp_dir):
        """Test image normalization."""
        from PIL import Image

        comparator = SVGPPTXComparator()

        # Create test images with different sizes
        img1 = Image.new('RGB', (100, 100), color='red')
        img2 = Image.new('RGB', (200, 150), color='blue')

        normalized_img1, normalized_img2 = comparator._normalize_image_sizes(img1, img2)

        # Should be resized to smaller dimensions
        assert normalized_img1.size == (100, 100)
        assert normalized_img2.size == (100, 100)

    def test_determine_compliance_level(self):
        """Test compliance level determination."""
        from .svg_pptx_comparator import ComparisonMetrics

        comparator = SVGPPTXComparator()

        # High compliance metrics
        high_metrics = ComparisonMetrics(overall_score=0.95)
        level = comparator._determine_compliance_level(high_metrics)
        assert level == ComplianceLevel.FULL

        # Low compliance metrics
        low_metrics = ComparisonMetrics(overall_score=0.40)
        level = comparator._determine_compliance_level(low_metrics)
        assert level == ComplianceLevel.FAIL


class TestW3CComplianceTestRunner:
    """Test compliance test runner."""

    def test_init(self, compliance_config):
        """Test runner initialization."""
        runner = W3CComplianceTestRunner(compliance_config)
        assert runner.config == compliance_config
        assert not runner.is_initialized

    def test_select_test_cases_basic(self, compliance_config):
        """Test basic test case selection."""
        runner = W3CComplianceTestRunner(compliance_config)

        # Mock test manager
        runner.test_manager = Mock()
        runner.test_manager.get_basic_compliance_suite.return_value = [
            Mock(name="test1"),
            Mock(name="test2")
        ]

        test_cases = runner._select_test_cases()
        assert len(test_cases) == 2
        runner.test_manager.get_basic_compliance_suite.assert_called_once()

    def test_select_test_cases_custom(self, compliance_config):
        """Test custom test case selection."""
        compliance_config.test_suite = TestSuite.CUSTOM
        compliance_config.custom_test_names = ["test1", "test2"]

        runner = W3CComplianceTestRunner(compliance_config)

        # Mock test manager
        runner.test_manager = Mock()
        runner.test_manager.get_test_case.side_effect = lambda name: Mock(name=name) if name in ["test1", "test2"] else None

        test_cases = runner._select_test_cases()
        assert len(test_cases) == 2

    def test_identify_common_issues(self, compliance_config):
        """Test common issue identification."""
        runner = W3CComplianceTestRunner(compliance_config)

        # Mock results with issues
        from .svg_pptx_comparator import FeatureCompliance

        mock_results = [
            Mock(feature_compliance=[
                FeatureCompliance("gradients", ComplianceLevel.FAIL, 0.3, ["Gradient not rendered"])
            ]),
            Mock(feature_compliance=[
                FeatureCompliance("gradients", ComplianceLevel.FAIL, 0.2, ["Gradient not rendered"])
            ])
        ]

        issues = runner._identify_common_issues(mock_results)
        assert any("Gradient not rendered" in issue for issue in issues)


# Integration Tests

@pytest.mark.integration
class TestW3CComplianceIntegration:
    """Integration tests requiring real components."""

    @pytest.mark.skip(reason="Requires LibreOffice installation")
    @pytest.mark.asyncio
    async def test_full_compliance_pipeline(self, mock_test_case, compliance_config):
        """Test complete compliance testing pipeline."""
        # This would require LibreOffice to be installed
        runner = W3CComplianceTestRunner(compliance_config)

        # Initialize (would fail without LibreOffice)
        # success = await runner.initialize()
        # assert success

        # Run single test
        # result = await runner.run_single_test(mock_test_case.name)
        # assert result is not None


# Performance Tests

@pytest.mark.performance
class TestPerformance:
    """Performance tests for compliance testing."""

    @pytest.mark.skip(reason="Performance test - requires real setup")
    def test_batch_processing_performance(self, compliance_config):
        """Test performance of batch compliance testing."""
        pass


# Mock Factories

def create_mock_test_cases(count: int = 5):
    """Create mock test cases for testing."""
    test_cases = []
    for i in range(count):
        test_case = Mock()
        test_case.name = f"test_case_{i+1}"
        test_case.category = "basic-shapes"
        test_case.svg_path = Path(f"/fake/path/test_{i+1}.svg")
        test_case.description = f"Test case {i+1}"
        test_case.tags = {"basic"}
        test_case.expected_features = {"rect", "circle"}
        test_cases.append(test_case)
    return test_cases


def create_mock_comparison_result(success: bool = True, compliance_level: ComplianceLevel = ComplianceLevel.HIGH):
    """Create mock comparison result."""
    from .svg_pptx_comparator import ComparisonResult, ComparisonMetrics

    result = Mock(spec=ComparisonResult)
    result.success = success
    result.overall_compliance = compliance_level
    result.test_case = Mock()
    result.test_case.name = "mock_test"
    result.test_case.category = "basic-shapes"

    if success:
        result.metrics = ComparisonMetrics(overall_score=0.85)
        result.error_message = None
    else:
        result.metrics = None
        result.error_message = "Mock error"

    result.feature_compliance = []
    return result


# Utility Functions

def setup_mock_w3c_environment(temp_dir: Path):
    """Set up mock W3C testing environment."""
    # Create directory structure
    test_data_dir = temp_dir / "w3c_tests"
    test_data_dir.mkdir(parents=True)

    # Create mock SVG files
    svg_dir = test_data_dir / "suites" / "w3c_svg_1.1"
    svg_dir.mkdir(parents=True)

    sample_svgs = [
        "basic-shapes-rect.svg",
        "basic-shapes-circle.svg",
        "paths-simple.svg",
        "text-basic.svg",
        "gradients-linear.svg"
    ]

    for svg_name in sample_svgs:
        svg_path = svg_dir / svg_name
        svg_path.write_text('''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
</svg>''')

    return test_data_dir


# Pytest Configuration

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring full setup"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test (slow)"
    )


# Test Data Generators

@pytest.fixture(scope="session")
def w3c_test_environment(tmp_path_factory):
    """Create W3C test environment for session."""
    temp_dir = tmp_path_factory.mktemp("w3c_tests")
    return setup_mock_w3c_environment(temp_dir)


# Parametrized Tests

@pytest.mark.parametrize("compliance_level,expected_score", [
    (ComplianceLevel.FULL, 0.95),
    (ComplianceLevel.HIGH, 0.85),
    (ComplianceLevel.MEDIUM, 0.70),
    (ComplianceLevel.LOW, 0.50),
    (ComplianceLevel.FAIL, 0.0),
])
def test_compliance_thresholds(compliance_level, expected_score):
    """Test compliance level thresholds."""
    comparator = SVGPPTXComparator()
    threshold = comparator.compliance_thresholds[compliance_level]
    assert threshold >= expected_score


@pytest.mark.parametrize("test_suite_type", [
    TestSuite.BASIC,
    TestSuite.COMPREHENSIVE,
    TestSuite.FEATURES,
    TestSuite.CUSTOM
])
def test_test_suite_selection(test_suite_type, compliance_config):
    """Test different test suite types."""
    compliance_config.test_suite = test_suite_type
    runner = W3CComplianceTestRunner(compliance_config)

    # Mock dependencies
    runner.test_manager = Mock()
    runner.test_manager.get_basic_compliance_suite.return_value = []
    runner.test_manager.get_comprehensive_suite.return_value = []
    runner.test_manager.get_test_cases.return_value = []
    runner.test_manager.get_test_case.return_value = None

    # Should not raise exception
    test_cases = runner._select_test_cases()
    assert isinstance(test_cases, list)
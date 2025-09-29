"""
Pytest configuration for multislide integration tests.

Provides multislide-specific fixtures and configuration for integration testing
between multislide components and the broader SVG2PPTX system.
"""

import pytest
from pathlib import Path
from typing import Dict, Any, Generator
from unittest.mock import Mock, patch
import tempfile

# Import test utilities
from tests.support.multislide import (
    TestFileManager,
    SVGTestLoader,
    PerformanceProfiler,
    load_expected_output
)


@pytest.fixture(scope="module")
def integration_test_data_dir() -> Path:
    """Test data directory for integration tests."""
    return Path(__file__).parent.parent.parent / "data" / "multislide"


@pytest.fixture(scope="module")
def integration_svg_loader(integration_test_data_dir: Path) -> SVGTestLoader:
    """SVG test loader for integration tests."""
    return SVGTestLoader(integration_test_data_dir)


@pytest.fixture(scope="module")
def integration_file_manager(integration_test_data_dir: Path) -> TestFileManager:
    """File manager for integration tests."""
    return TestFileManager(integration_test_data_dir)


@pytest.fixture
def integration_temp_dir() -> Generator[Path, None, None]:
    """Temporary directory for integration test outputs."""
    with tempfile.TemporaryDirectory(prefix="multislide_integration_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def real_conversion_services():
    """Real conversion services for integration testing."""
    try:
        from core.services.conversion_services import ConversionServices
        return ConversionServices.create_default()
    except ImportError:
        pytest.skip("ConversionServices not available for integration testing")


@pytest.fixture
def integration_performance_profiler() -> PerformanceProfiler:
    """Performance profiler for integration tests."""
    return PerformanceProfiler()


@pytest.fixture(scope="module")
def integration_test_samples(integration_svg_loader: SVGTestLoader) -> Dict[str, Any]:
    """Load all test samples for integration testing."""
    samples = {}

    categories = ['animation_sequences', 'nested_documents', 'layer_groups', 'section_markers', 'edge_cases']

    for category in categories:
        try:
            category_samples = integration_svg_loader.load_all_samples(category)
            for sample_name, svg_element in category_samples.items():
                full_name = f"{category}/{sample_name}"
                samples[full_name] = {
                    'svg_element': svg_element,
                    'category': category,
                    'filename': sample_name
                }
        except Exception as e:
            # Log but don't fail if some samples are missing
            print(f"Warning: Could not load samples from {category}: {e}")

    return samples


@pytest.fixture
def integration_expected_outputs(integration_file_manager: TestFileManager) -> Dict[str, Any]:
    """Load expected outputs for integration testing."""
    expected_outputs = {}

    expected_files = [
        'simple_fade_animation_expected',
        'department_slides_expected',
        'explicit_slide_boundaries_expected',
        'single_slide_only_expected',
        'overlapping_boundaries_expected'
    ]

    for expected_file in expected_files:
        try:
            expected = load_expected_output(expected_file)
            if expected:
                expected_outputs[expected_file] = expected
        except Exception as e:
            print(f"Warning: Could not load expected output {expected_file}: {e}")

    return expected_outputs


@pytest.fixture
def integration_test_config() -> Dict[str, Any]:
    """Configuration for integration testing."""
    return {
        'performance': {
            'max_processing_time': 10.0,  # seconds
            'max_memory_usage': 200 * 1024 * 1024,  # 200MB
        },
        'validation': {
            'strict_mode': False,  # More lenient for integration
            'allow_missing_expected_outputs': True,
            'slide_count_tolerance': 1,  # Allow ±1 slide difference
        },
        'detection': {
            'animation_threshold': 0.05,
            'nesting_depth_limit': 15,
            'element_count_limit': 5000,
        },
        'conversion': {
            'slide_width': 9144000,
            'slide_height': 6858000,
            'default_dpi': 96,
            'quality': 'high'
        }
    }


@pytest.fixture
def mock_pptx_dependencies():
    """Mock PPTX-related dependencies for integration tests."""
    mocks = {}

    with patch('pptx.Presentation') as mock_pres:
        mock_instance = Mock()
        mock_instance.slides = Mock()
        mock_instance.slide_layouts = [Mock() for _ in range(10)]  # Mock layouts
        mock_instance.slides.add_slide.return_value = Mock()
        mock_pres.return_value = mock_instance
        mocks['presentation'] = mock_instance

        with patch('pptx.util.Inches') as mock_inches:
            mock_inches.side_effect = lambda x: x * 914400  # Convert to EMU
            mocks['inches'] = mock_inches

            with patch('pptx.util.Pt') as mock_pt:
                mock_pt.side_effect = lambda x: x * 12700  # Convert to EMU
                mocks['pt'] = mock_pt

                yield mocks


@pytest.fixture(params=[
    'animation_sequences/simple_fade_animation.svg',
    'nested_documents/simple_nested_slides.svg',
    'layer_groups/department_slides.svg',
    'section_markers/explicit_slide_boundaries.svg',
    'edge_cases/single_slide_only.svg'
])
def integration_test_sample(request, integration_svg_loader: SVGTestLoader):
    """Parametrized fixture for integration test samples."""
    category, filename = request.param.split('/', 1)
    try:
        svg_element = integration_svg_loader.load_sample(category, filename)
        return {
            'svg_element': svg_element,
            'category': category,
            'filename': filename,
            'test_id': request.param
        }
    except FileNotFoundError:
        pytest.skip(f"Test sample not found: {request.param}")


@pytest.fixture
def integration_conversion_pipeline():
    """Mock conversion pipeline for integration testing."""
    pipeline = Mock()

    # Mock preprocessing stage
    pipeline.preprocess = Mock(return_value=Mock())

    # Mock multislide detection stage
    pipeline.detect_multislide = Mock(return_value={
        'is_multislide': True,
        'slide_count': 3,
        'detection_method': 'integration_test'
    })

    # Mock conversion stage
    pipeline.convert_to_pptx = Mock(return_value=b"Mock PPTX data")

    # Mock validation stage
    pipeline.validate_output = Mock(return_value=True)

    return pipeline


# Performance testing fixtures for integration
@pytest.fixture
def integration_performance_benchmarks() -> Dict[str, Any]:
    """Performance benchmarks for integration testing."""
    return {
        'detection_time': {
            'simple': 0.1,    # seconds
            'medium': 0.5,
            'complex': 2.0,
            'stress': 10.0
        },
        'conversion_time': {
            'simple': 0.5,
            'medium': 2.0,
            'complex': 5.0,
            'stress': 30.0
        },
        'memory_usage': {
            'simple': 10 * 1024 * 1024,   # 10MB
            'medium': 50 * 1024 * 1024,   # 50MB
            'complex': 100 * 1024 * 1024, # 100MB
            'stress': 500 * 1024 * 1024   # 500MB
        }
    }


# Test markers for integration tests
def pytest_configure(config):
    """Configure integration-specific test markers."""
    config.addinivalue_line(
        "markers", "multislide_integration: marks tests as multislide integration tests"
    )
    config.addinivalue_line(
        "markers", "end_to_end_flow: marks tests for complete multislide flow"
    )
    config.addinivalue_line(
        "markers", "cross_component: marks tests for cross-component integration"
    )
    config.addinivalue_line(
        "markers", "performance_integration: marks performance integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark integration tests."""
    for item in items:
        # Add multislide_integration marker to all tests in this directory
        item.add_marker(pytest.mark.multislide_integration)

        # Add specific markers based on test name
        test_name = item.name.lower()
        if 'end_to_end' in test_name or 'e2e' in test_name:
            item.add_marker(pytest.mark.end_to_end_flow)
        if 'cross' in test_name or 'component' in test_name:
            item.add_marker(pytest.mark.cross_component)
        if 'performance' in test_name or 'benchmark' in test_name:
            item.add_marker(pytest.mark.performance_integration)
            item.add_marker(pytest.mark.slow)
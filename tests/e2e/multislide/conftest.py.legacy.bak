"""
Pytest configuration for multislide end-to-end tests.

Provides fixtures and configuration for end-to-end testing of complete
multislide workflows from SVG input to PPTX output.
"""

import pytest
from pathlib import Path
from typing import Dict, Any, Generator, Optional
import tempfile
import shutil

# Import test utilities
from tests.support.multislide import (
    TestFileManager,
    SVGTestLoader,
    PerformanceProfiler
)


@pytest.fixture(scope="session")
def e2e_test_data_dir() -> Path:
    """Test data directory for E2E tests."""
    return Path(__file__).parent.parent.parent / "data" / "multislide"


@pytest.fixture(scope="session")
def e2e_output_dir() -> Generator[Path, None, None]:
    """Output directory for E2E test results."""
    output_dir = Path(__file__).parent / "test_outputs"
    output_dir.mkdir(exist_ok=True)

    yield output_dir

    # Cleanup old test outputs (keep last 5 runs)
    if output_dir.exists():
        test_runs = sorted([d for d in output_dir.iterdir() if d.is_dir()],
                          key=lambda x: x.stat().st_mtime, reverse=True)
        for old_run in test_runs[5:]:  # Keep only last 5
            shutil.rmtree(old_run, ignore_errors=True)


@pytest.fixture
def e2e_test_run_dir(e2e_output_dir: Path) -> Generator[Path, None, None]:
    """Individual test run directory."""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = e2e_output_dir / f"run_{timestamp}_{pytest.current_test_id}"
    run_dir.mkdir(exist_ok=True)

    yield run_dir


@pytest.fixture(scope="session")
def e2e_svg_loader(e2e_test_data_dir: Path) -> SVGTestLoader:
    """SVG test loader for E2E tests."""
    return SVGTestLoader(e2e_test_data_dir)


@pytest.fixture(scope="session")
def e2e_file_manager(e2e_test_data_dir: Path) -> TestFileManager:
    """File manager for E2E tests."""
    return TestFileManager(e2e_test_data_dir)


@pytest.fixture
def e2e_performance_profiler() -> PerformanceProfiler:
    """Performance profiler for E2E tests."""
    return PerformanceProfiler()


@pytest.fixture(scope="session")
def e2e_test_config() -> Dict[str, Any]:
    """Configuration for E2E testing."""
    return {
        'performance': {
            'max_processing_time': 30.0,  # seconds
            'max_memory_usage': 1024 * 1024 * 1024,  # 1GB
        },
        'validation': {
            'strict_mode': True,
            'validate_pptx_structure': True,
            'validate_slide_content': True,
            'validate_visual_fidelity': False,  # Requires additional tools
        },
        'output': {
            'save_intermediate_files': True,
            'save_debug_info': True,
            'compress_outputs': False,
        },
        'conversion': {
            'slide_width': 9144000,
            'slide_height': 6858000,
            'default_dpi': 96,
            'quality': 'high',
            'preserve_animations': True,
        }
    }


@pytest.fixture(scope="session")
def e2e_test_scenarios() -> Dict[str, Dict[str, Any]]:
    """Complete E2E test scenarios."""
    return {
        'simple_presentation': {
            'input_file': 'animation_sequences/simple_fade_animation.svg',
            'expected_slides': 3,
            'expected_duration': 6.0,
            'description': 'Simple fade animation converted to PPTX slides'
        },
        'complex_business_presentation': {
            'input_file': 'layer_groups/department_slides.svg',
            'expected_slides': 4,
            'expected_content': ['Engineering', 'Marketing', 'Sales', 'Operations'],
            'description': 'Business department presentation with layer-based slides'
        },
        'nested_content': {
            'input_file': 'nested_documents/deep_hierarchy.svg',
            'expected_slides': 4,
            'max_nesting_depth': 5,
            'description': 'Complex nested SVG structure with deep hierarchy'
        },
        'explicit_boundaries': {
            'input_file': 'section_markers/explicit_slide_boundaries.svg',
            'expected_slides': 4,
            'boundary_markers': ['data-slide-number', 'slide-boundary'],
            'description': 'Presentation with explicit slide boundary markers'
        },
        'edge_case_handling': {
            'input_file': 'edge_cases/overlapping_boundaries.svg',
            'expected_slides': 3,
            'conflict_resolution': True,
            'description': 'Edge case with overlapping slide boundaries'
        },
        'performance_stress': {
            'input_file': 'edge_cases/performance_stress.svg',
            'expected_slides': 2,
            'element_count': 1000,
            'max_processing_time': 15.0,
            'description': 'Performance stress test with large element count'
        },
        'negative_test': {
            'input_file': 'edge_cases/single_slide_only.svg',
            'expected_slides': 1,
            'should_be_multislide': False,
            'description': 'Single slide that should NOT be detected as multislide'
        }
    }


@pytest.fixture
def e2e_svg_to_pptx_converter():
    """Complete SVG to PPTX converter for E2E testing."""
    try:
        # Try to import real converter
        from src.converters.multislide import MultislideConverter
        from core.services.conversion_services import ConversionServices

        services = ConversionServices.create_default()
        return MultislideConverter(services)
    except ImportError:
        # Use mock converter for testing
        from unittest.mock import Mock

        mock_converter = Mock()
        mock_converter.can_convert.return_value = True
        mock_converter.convert.return_value = b"Mock PPTX data"
        mock_converter.detect_slides.return_value = {
            'is_multislide': True,
            'slide_count': 3,
            'detection_method': 'e2e_test'
        }

        return mock_converter


@pytest.fixture
def e2e_pptx_validator():
    """PPTX file validator for E2E testing."""
    def validate_pptx_file(file_path: Path) -> Dict[str, Any]:
        """Validate PPTX file structure and content."""
        results = {
            'is_valid': False,
            'slide_count': 0,
            'errors': [],
            'warnings': []
        }

        try:
            # Check file exists and has content
            if not file_path.exists():
                results['errors'].append(f"PPTX file does not exist: {file_path}")
                return results

            if file_path.stat().st_size == 0:
                results['errors'].append("PPTX file is empty")
                return results

            # Try to read as ZIP (PPTX is a ZIP file)
            import zipfile
            try:
                with zipfile.ZipFile(file_path, 'r') as pptx_zip:
                    # Check for required PPTX structure
                    required_files = [
                        '[Content_Types].xml',
                        '_rels/.rels',
                        'ppt/presentation.xml'
                    ]

                    for required_file in required_files:
                        if required_file not in pptx_zip.namelist():
                            results['errors'].append(f"Missing required file: {required_file}")

                    # Count slides
                    slide_files = [f for f in pptx_zip.namelist() if f.startswith('ppt/slides/slide')]
                    results['slide_count'] = len(slide_files)

                    if not results['errors']:
                        results['is_valid'] = True

            except zipfile.BadZipFile:
                results['errors'].append("File is not a valid ZIP/PPTX file")

        except Exception as e:
            results['errors'].append(f"Validation error: {str(e)}")

        return results

    return validate_pptx_file


@pytest.fixture(params=[
    'simple_presentation',
    'complex_business_presentation',
    'nested_content',
    'explicit_boundaries'
])
def e2e_scenario(request, e2e_test_scenarios: Dict[str, Dict[str, Any]]):
    """Parametrized E2E test scenario fixture."""
    scenario_name = request.param
    return {
        'name': scenario_name,
        **e2e_test_scenarios[scenario_name]
    }


@pytest.fixture
def e2e_test_metrics():
    """Collect E2E test metrics."""
    metrics = {
        'processing_times': [],
        'memory_usage': [],
        'file_sizes': [],
        'slide_counts': [],
        'error_counts': []
    }

    yield metrics

    # Could save metrics to file for analysis
    # This would be useful for performance regression testing


@pytest.fixture
def e2e_cleanup_handler():
    """Handle cleanup of E2E test artifacts."""
    created_files = []

    def register_file(file_path: Path):
        """Register a file for cleanup."""
        created_files.append(file_path)

    yield register_file

    # Cleanup (if needed - temp directories handle most of this)
    for file_path in created_files:
        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors


# Comprehensive E2E workflow fixture
@pytest.fixture
def e2e_multislide_workflow(
    e2e_svg_to_pptx_converter,
    e2e_pptx_validator,
    e2e_performance_profiler: PerformanceProfiler,
    e2e_test_run_dir: Path
):
    """Complete E2E workflow for multislide conversion."""
    def run_workflow(svg_file_path: Path, expected_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run complete E2E workflow."""
        workflow_results = {
            'success': False,
            'processing_time': 0,
            'memory_usage': 0,
            'input_file': str(svg_file_path),
            'output_file': None,
            'slide_count': 0,
            'detection_results': None,
            'conversion_results': None,
            'validation_results': None,
            'errors': []
        }

        try:
            with e2e_performance_profiler.profile():
                # Step 1: Load SVG
                with open(svg_file_path, 'rb') as f:
                    svg_content = f.read()

                # Step 2: Detect multislide structure
                from lxml import etree
                svg_element = etree.fromstring(svg_content)

                detection_results = e2e_svg_to_pptx_converter.detect_slides(svg_element)
                workflow_results['detection_results'] = detection_results

                # Step 3: Convert to PPTX
                if detection_results.get('is_multislide', False):
                    pptx_data = e2e_svg_to_pptx_converter.convert(svg_element)

                    # Save PPTX file
                    output_file = e2e_test_run_dir / f"{svg_file_path.stem}_output.pptx"
                    with open(output_file, 'wb') as f:
                        f.write(pptx_data)

                    workflow_results['output_file'] = str(output_file)
                    workflow_results['conversion_results'] = {'pptx_size': len(pptx_data)}

                    # Step 4: Validate PPTX
                    validation_results = e2e_pptx_validator(output_file)
                    workflow_results['validation_results'] = validation_results
                    workflow_results['slide_count'] = validation_results.get('slide_count', 0)

                    workflow_results['success'] = validation_results.get('is_valid', False)
                else:
                    workflow_results['success'] = True  # Single slide is valid too

            # Get performance metrics
            metrics = e2e_performance_profiler.metrics
            workflow_results['processing_time'] = metrics.get('processing_time', 0)
            workflow_results['memory_usage'] = metrics.get('memory_usage', 0)

        except Exception as e:
            workflow_results['errors'].append(str(e))
            workflow_results['success'] = False

        return workflow_results

    return run_workflow


# Test markers for E2E tests
def pytest_configure(config):
    """Configure E2E-specific test markers."""
    config.addinivalue_line(
        "markers", "multislide_e2e: marks tests as multislide E2E tests"
    )
    config.addinivalue_line(
        "markers", "full_workflow: marks tests for complete workflow"
    )
    config.addinivalue_line(
        "markers", "pptx_validation: marks tests that validate PPTX output"
    )
    config.addinivalue_line(
        "markers", "performance_e2e: marks E2E performance tests"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark E2E tests."""
    for item in items:
        # Add multislide_e2e marker to all tests in this directory
        item.add_marker(pytest.mark.multislide_e2e)

        # Add specific markers based on test name
        test_name = item.name.lower()
        if 'workflow' in test_name:
            item.add_marker(pytest.mark.full_workflow)
        if 'pptx' in test_name or 'validation' in test_name:
            item.add_marker(pytest.mark.pptx_validation)
        if 'performance' in test_name or 'stress' in test_name:
            item.add_marker(pytest.mark.performance_e2e)
            item.add_marker(pytest.mark.slow)


# Add current test ID to pytest namespace for use in fixtures
def pytest_runtest_setup(item):
    """Set up current test ID for fixtures."""
    pytest.current_test_id = item.nodeid.replace('::', '_').replace('/', '_')
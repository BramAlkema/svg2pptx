"""
General test utilities for multislide testing.

Provides common utilities, fixtures, and helper functions
for multislide test scenarios.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import pytest
from lxml import etree


@dataclass
class TestSlideExpectation:
    """Expected data for a test slide."""
    slide_number: int
    elements: List[str]
    content_summary: str
    background_color: Optional[str] = None
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class TestCaseExpectation:
    """Expected results for a complete test case."""
    test_case: str
    detection_strategy: str
    is_multislide: bool
    slide_count: int
    detection_method: str
    slides: List[TestSlideExpectation]
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['slides'] = [slide.to_dict() for slide in self.slides]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCaseExpectation':
        """Create from dictionary."""
        slides = [TestSlideExpectation(**slide) for slide in data.get('slides', [])]
        return cls(
            test_case=data['test_case'],
            detection_strategy=data['detection_strategy'],
            is_multislide=data['is_multislide'],
            slide_count=data['slide_count'],
            detection_method=data['detection_method'],
            slides=slides,
            metadata=data.get('metadata')
        )


class TestFileManager:
    """Manages test files and temporary directories."""

    def __init__(self, test_data_dir: Optional[Path] = None):
        """Initialize file manager."""
        self.test_data_dir = test_data_dir or Path(__file__).parent.parent.parent / "data" / "multislide"
        self.temp_dirs = []

    @contextmanager
    def temp_directory(self):
        """Create temporary directory context manager."""
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        self.temp_dirs.append(temp_path)

        try:
            yield temp_path
        finally:
            # Cleanup handled by pytest fixtures
            pass

    def get_sample_path(self, category: str, filename: str) -> Path:
        """Get path to test sample file."""
        return self.test_data_dir / "svg_samples" / category / filename

    def get_expected_output_path(self, test_case: str) -> Path:
        """Get path to expected output file."""
        return self.test_data_dir / "expected_outputs" / f"{test_case}_expected.json"

    def load_test_catalog(self) -> Dict[str, Any]:
        """Load test data catalog."""
        catalog_path = self.test_data_dir / "test_data_catalog.json"

        if not catalog_path.exists():
            return {}

        with open(catalog_path, 'r') as f:
            return json.load(f)

    def save_test_result(
        self,
        test_case: str,
        result: Dict[str, Any],
        temp_dir: Path
    ) -> Path:
        """Save test result to temporary file."""
        result_path = temp_dir / f"{test_case}_result.json"

        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        return result_path


class AssertionHelper:
    """Helper for common test assertions."""

    @staticmethod
    def assert_slide_detection(
        actual: Dict[str, Any],
        expected: TestCaseExpectation,
        strict: bool = True
    ):
        """Assert slide detection results match expectations."""
        # Basic structure assertions
        assert actual['is_multislide'] == expected.is_multislide, \
            f"Multislide detection mismatch: expected {expected.is_multislide}, got {actual['is_multislide']}"

        assert actual['slide_count'] == expected.slide_count, \
            f"Slide count mismatch: expected {expected.slide_count}, got {actual['slide_count']}"

        if expected.detection_method:
            assert actual.get('detection_method') == expected.detection_method, \
                f"Detection method mismatch: expected {expected.detection_method}, got {actual.get('detection_method')}"

        # Slides assertion
        actual_slides = actual.get('slides', [])
        assert len(actual_slides) == len(expected.slides), \
            f"Slides list length mismatch: expected {len(expected.slides)}, got {len(actual_slides)}"

        if strict:
            for i, (actual_slide, expected_slide) in enumerate(zip(actual_slides, expected.slides)):
                AssertionHelper._assert_slide_match(actual_slide, expected_slide, i)

    @staticmethod
    def _assert_slide_match(
        actual_slide: Dict[str, Any],
        expected_slide: TestSlideExpectation,
        slide_index: int
    ):
        """Assert individual slide matches expectation."""
        assert actual_slide.get('slide_number') == expected_slide.slide_number, \
            f"Slide {slide_index} number mismatch"

        # Check elements if specified
        if expected_slide.elements:
            actual_elements = actual_slide.get('elements', [])
            for expected_element in expected_slide.elements:
                assert expected_element in actual_elements, \
                    f"Slide {slide_index} missing expected element: {expected_element}"

        # Check content summary if specified
        if expected_slide.content_summary:
            actual_summary = actual_slide.get('content_summary', '')
            assert expected_slide.content_summary.lower() in actual_summary.lower(), \
                f"Slide {slide_index} content summary doesn't match"

    @staticmethod
    def assert_animation_timeline(
        actual: Dict[str, Any],
        expected_duration: float,
        expected_keyframes: int,
        tolerance: float = 0.1
    ):
        """Assert animation timeline properties."""
        metadata = actual.get('metadata', {})
        actual_duration = metadata.get('total_duration', 0)

        assert abs(actual_duration - expected_duration) <= tolerance, \
            f"Duration mismatch: expected {expected_duration}, got {actual_duration}"

        slides = actual.get('slides', [])
        total_keyframes = sum(
            len(slide.get('animation_triggers', []))
            for slide in slides
        )

        assert total_keyframes >= expected_keyframes, \
            f"Insufficient keyframes: expected at least {expected_keyframes}, got {total_keyframes}"

    @staticmethod
    def assert_layer_organization(
        actual: Dict[str, Any],
        expected_layers: List[str]
    ):
        """Assert layer-based organization."""
        slides = actual.get('slides', [])
        actual_layers = [
            slide.get('layer_id', '')
            for slide in slides
            if slide.get('layer_id')
        ]

        for expected_layer in expected_layers:
            assert any(expected_layer in layer for layer in actual_layers), \
                f"Missing expected layer: {expected_layer}"

    @staticmethod
    def assert_performance_metrics(
        actual: Dict[str, Any],
        max_processing_time: float,
        max_memory_usage: Optional[int] = None
    ):
        """Assert performance metrics are within acceptable bounds."""
        metadata = actual.get('metadata', {})
        processing_time = metadata.get('processing_time', 0)

        assert processing_time <= max_processing_time, \
            f"Processing time exceeded limit: {processing_time}s > {max_processing_time}s"

        if max_memory_usage:
            memory_usage = metadata.get('memory_usage', 0)
            assert memory_usage <= max_memory_usage, \
                f"Memory usage exceeded limit: {memory_usage} > {max_memory_usage}"


class TestDataGenerator:
    """Generates test data for dynamic testing."""

    @staticmethod
    def create_simple_svg(
        width: int = 800,
        height: int = 600,
        slide_count: int = 3
    ) -> etree.Element:
        """Create simple SVG with basic slide structure."""
        from .svg_helpers import SVGTestBuilder

        builder = SVGTestBuilder(width, height)

        for i in range(slide_count):
            slide_group = builder.add_slide_group(
                f'slide_{i + 1}',
                css_class='slide-boundary'
            )

            # Add background
            builder.add_rect(
                slide_group,
                0, i * height,
                width, height,
                fill=f'hsl({i * 120}, 70%, 95%)'
            )

            # Add title
            builder.add_text(
                slide_group,
                width // 2, (i * height) + 50,
                f'Slide {i + 1}',
                font_size=24,
                text_anchor='middle'
            )

        return builder.root

    @staticmethod
    def create_animated_svg(
        slide_count: int = 3,
        duration: float = 6.0
    ) -> etree.Element:
        """Create SVG with animation-based slides."""
        from .svg_helpers import SVGTestBuilder

        builder = SVGTestBuilder()
        slide_duration = duration / slide_count

        for i in range(slide_count):
            slide_group = builder.add_slide_group(f'slide_{i + 1}')

            # Add animated rectangle
            rect = builder.add_rect(
                slide_group,
                100, 100,
                200, 100,
                fill='blue'
            )

            # Add opacity animation
            start_time = i * slide_duration
            end_time = (i + 1) * slide_duration

            opacity_values = ['0'] * slide_count
            opacity_values[i] = '1'

            builder.add_animation(
                rect,
                'opacity',
                ';'.join(opacity_values),
                f'{duration}s',
                ';'.join([str(j / slide_count) for j in range(slide_count + 1)])
            )

        return builder.root

    @staticmethod
    def create_layered_svg(
        layer_names: List[str]
    ) -> etree.Element:
        """Create SVG with layer-based organization."""
        from .svg_helpers import SVGTestBuilder

        builder = SVGTestBuilder()

        for i, layer_name in enumerate(layer_names):
            layer_group = builder.add_slide_group(
                f'layer_{layer_name.lower()}',
                css_class='layer-group'
            )

            # Add layer content
            builder.add_rect(
                layer_group,
                50, 50 + (i * 150),
                700, 120,
                fill=f'hsl({i * 60}, 60%, 90%)'
            )

            builder.add_text(
                layer_group,
                400, 110 + (i * 150),
                layer_name,
                font_size=20,
                text_anchor='middle'
            )

        return builder.root


class PerformanceProfiler:
    """Simple performance profiler for tests."""

    def __init__(self):
        """Initialize profiler."""
        self.start_time = None
        self.end_time = None
        self.memory_start = None
        self.memory_peak = None

    def start(self):
        """Start profiling."""
        import time
        import psutil
        import os

        self.start_time = time.time()
        process = psutil.Process(os.getpid())
        self.memory_start = process.memory_info().rss

    def stop(self):
        """Stop profiling and return metrics."""
        import time
        import psutil
        import os

        self.end_time = time.time()
        process = psutil.Process(os.getpid())
        memory_end = process.memory_info().rss

        return {
            'processing_time': self.end_time - self.start_time if self.start_time else 0,
            'memory_usage': memory_end - self.memory_start if self.memory_start else 0,
            'memory_peak': max(memory_end, self.memory_start or 0)
        }

    @contextmanager
    def profile(self):
        """Context manager for profiling."""
        self.start()
        try:
            yield self
        finally:
            metrics = self.stop()
            self.metrics = metrics


def parametrize_test_samples(category: Optional[str] = None):
    """Pytest parametrize decorator for test samples."""
    def decorator(func):
        # Load test catalog to get sample parameters
        file_manager = TestFileManager()
        catalog = file_manager.load_test_catalog()

        if not catalog:
            return pytest.mark.skip("No test catalog available")(func)

        categories = catalog.get('test_data_catalog', {}).get('categories', {})

        if category and category in categories:
            samples = categories[category].get('samples', [])
        else:
            # All samples from all categories
            samples = []
            for cat_data in categories.values():
                samples.extend(cat_data.get('samples', []))

        if not samples:
            return pytest.mark.skip(f"No samples found for category: {category}")(func)

        # Create parameter list
        param_list = [
            (sample['filename'], sample.get('expected_output'))
            for sample in samples
        ]

        return pytest.mark.parametrize(
            'sample_filename,expected_output_file',
            param_list,
            ids=[sample['filename'] for sample in samples]
        )(func)

    return decorator


def skip_if_no_expected_output(expected_output_file):
    """Skip test if no expected output file is available."""
    if not expected_output_file:
        pytest.skip("No expected output file for comparison")


def load_expected_output(test_case: str) -> Optional[TestCaseExpectation]:
    """Load expected output for test case."""
    file_manager = TestFileManager()
    expected_path = file_manager.get_expected_output_path(test_case)

    if not expected_path.exists():
        return None

    with open(expected_path, 'r') as f:
        data = json.load(f)

    return TestCaseExpectation.from_dict(data['expected_result'])
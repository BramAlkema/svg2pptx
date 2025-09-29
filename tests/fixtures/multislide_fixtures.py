"""
Multislide-specific test fixtures.

Provides fixtures for testing multislide detection, conversion,
and document generation functionality.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any, Generator, Optional, List
from unittest.mock import Mock, patch
from lxml import etree

# Import test support utilities
from tests.support.multislide import (
    MockConversionServices,
    SVGTestBuilder,
    SVGTestLoader,
    TestFileManager,
    PerformanceProfiler,
    TestCaseExpectation,
    create_mock_services,
    create_mock_slide_detector
)


@pytest.fixture(scope="session")
def multislide_test_data_dir() -> Path:
    """Provide path to multislide test data directory."""
    return Path(__file__).parent.parent / "data" / "multislide"


@pytest.fixture(scope="session")
def multislide_svg_samples_dir(multislide_test_data_dir: Path) -> Path:
    """Provide path to multislide SVG samples directory."""
    return multislide_test_data_dir / "svg_samples"


@pytest.fixture(scope="session")
def multislide_expected_outputs_dir(multislide_test_data_dir: Path) -> Path:
    """Provide path to multislide expected outputs directory."""
    return multislide_test_data_dir / "expected_outputs"


@pytest.fixture
def multislide_temp_dir() -> Generator[Path, None, None]:
    """Provide temporary directory for multislide test files."""
    with tempfile.TemporaryDirectory(prefix="multislide_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def multislide_mock_services() -> MockConversionServices:
    """Provide mock conversion services configured for multislide testing."""
    return create_mock_services(
        unit_converter={
            '100px': 914400,  # 100 pixels in EMU
            '1in': 914400,    # 1 inch in EMU
            '72pt': 914400,   # 72 points in EMU
            '96px': 914400    # 96 pixels = 1 inch
        },
        viewport_handler={
            'slide_width': 9144000,   # 10 inches in EMU
            'slide_height': 6858000,  # 7.5 inches in EMU
            'viewbox': (0, 0, 1024, 768)
        },
        font_service={
            'font_mappings': {
                'Arial': 'Arial',
                'Helvetica': 'Arial',
                'sans-serif': 'Arial',
                'Times': 'Times New Roman',
                'serif': 'Times New Roman',
                'monospace': 'Courier New'
            },
            'default_font': 'Arial'
        },
        animation_service={
            'timeline_data': {
                'total_duration': 6.0,
                'keyframes': [],
                'slides': []
            }
        }
    )


@pytest.fixture
def multislide_svg_builder() -> SVGTestBuilder:
    """Provide SVG test builder for creating multislide test SVGs."""
    return SVGTestBuilder(width=1024, height=768)


@pytest.fixture
def multislide_test_loader(multislide_test_data_dir: Path) -> SVGTestLoader:
    """Provide SVG test loader for loading multislide test samples."""
    return SVGTestLoader(multislide_test_data_dir)


@pytest.fixture
def multislide_file_manager(multislide_test_data_dir: Path) -> TestFileManager:
    """Provide test file manager for managing multislide test files."""
    return TestFileManager(multislide_test_data_dir)


@pytest.fixture
def multislide_performance_profiler() -> PerformanceProfiler:
    """Provide performance profiler for measuring multislide test performance."""
    return PerformanceProfiler()


# SVG Element Fixtures for Different Detection Strategies


@pytest.fixture
def explicit_boundary_svg(multislide_svg_builder: SVGTestBuilder) -> etree.Element:
    """Provide SVG with explicit slide boundaries for testing."""
    builder = multislide_svg_builder

    # Slide 1
    slide1 = builder.add_slide_group(
        'slide-1',
        css_class='slide-boundary',
        transform='translate(0, 0)'
    )
    slide1.set('data-slide-number', '1')
    builder.add_rect(slide1, 0, 0, 1024, 768, fill='#f8f9fa')
    builder.add_text(slide1, 512, 100, 'Slide 1: Introduction', font_size=32, text_anchor='middle')

    # Slide 2
    slide2 = builder.add_slide_group(
        'slide-2',
        css_class='slide-boundary',
        transform='translate(0, 768)'
    )
    slide2.set('data-slide-number', '2')
    builder.add_rect(slide2, 0, 0, 1024, 768, fill='#e8f4fd')
    builder.add_text(slide2, 512, 100, 'Slide 2: Content', font_size=32, text_anchor='middle')

    # Slide 3
    slide3 = builder.add_slide_group(
        'slide-3',
        css_class='slide-boundary',
        transform='translate(0, 1536)'
    )
    slide3.set('data-slide-number', '3')
    builder.add_rect(slide3, 0, 0, 1024, 768, fill='#e8f5e8')
    builder.add_text(slide3, 512, 100, 'Slide 3: Conclusion', font_size=32, text_anchor='middle')

    return builder.root


@pytest.fixture
def animation_sequence_svg(multislide_svg_builder: SVGTestBuilder) -> etree.Element:
    """Provide SVG with animation sequences for testing."""
    builder = multislide_svg_builder

    # Slide 1 content
    slide1_group = builder.add_slide_group('slide1')
    rect1 = builder.add_rect(slide1_group, 100, 100, 200, 150, fill='blue')
    text1 = builder.add_text(slide1_group, 200, 175, 'Slide 1', font_size=18, text_anchor='middle', fill='white')

    # Animation: visible 0-2s
    builder.add_animation(rect1, 'opacity', '1;1;0;0', '6s', '0;0.33;0.34;1')
    builder.add_animation(text1, 'opacity', '1;1;0;0', '6s', '0;0.33;0.34;1')

    # Slide 2 content
    slide2_group = builder.add_slide_group('slide2')
    rect2 = builder.add_rect(slide2_group, 100, 100, 200, 150, fill='green')
    text2 = builder.add_text(slide2_group, 200, 175, 'Slide 2', font_size=18, text_anchor='middle', fill='white')

    # Animation: visible 2-4s
    builder.add_animation(rect2, 'opacity', '0;0;1;1;0;0', '6s', '0;0.33;0.34;0.66;0.67;1')
    builder.add_animation(text2, 'opacity', '0;0;1;1;0;0', '6s', '0;0.33;0.34;0.66;0.67;1')

    # Slide 3 content
    slide3_group = builder.add_slide_group('slide3')
    rect3 = builder.add_rect(slide3_group, 100, 100, 200, 150, fill='red')
    text3 = builder.add_text(slide3_group, 200, 175, 'Slide 3', font_size=18, text_anchor='middle', fill='white')

    # Animation: visible 4-6s
    builder.add_animation(rect3, 'opacity', '0;0;0;0;1;1', '6s', '0;0.66;0.67;0.67;0.68;1')
    builder.add_animation(text3, 'opacity', '0;0;0;0;1;1', '6s', '0;0.66;0.67;0.67;0.68;1')

    return builder.root


@pytest.fixture
def nested_document_svg(multislide_svg_builder: SVGTestBuilder) -> etree.Element:
    """Provide SVG with nested documents for testing."""
    builder = multislide_svg_builder

    # Outer container
    outer_group = builder.add_slide_group('presentation_root')
    builder.add_rect(outer_group, 0, 0, 1024, 768, fill='#2c3e50')

    # Nested slide 1
    nested1 = builder.add_nested_svg(outer_group, 50, 50, 924, 200, '0 0 924 200')
    nested1.set('id', 'slide_section_1')
    builder.add_rect(nested1, 0, 0, 924, 200, fill='#34495e')
    builder.add_text(nested1, 462, 100, 'Header Section', font_size=24, text_anchor='middle', fill='white')

    # Nested slide 2
    nested2 = builder.add_nested_svg(outer_group, 50, 300, 924, 300, '0 0 924 300')
    nested2.set('id', 'slide_section_2')
    builder.add_rect(nested2, 0, 0, 924, 300, fill='#ecf0f1')
    builder.add_text(nested2, 462, 150, 'Main Content', font_size=24, text_anchor='middle', fill='#2c3e50')

    # Nested slide 3
    nested3 = builder.add_nested_svg(outer_group, 50, 650, 924, 100, '0 0 924 100')
    nested3.set('id', 'slide_section_3')
    builder.add_rect(nested3, 0, 0, 924, 100, fill='#7f8c8d')
    builder.add_text(nested3, 462, 50, 'Footer Section', font_size=18, text_anchor='middle', fill='white')

    return builder.root


@pytest.fixture
def layer_group_svg(multislide_svg_builder: SVGTestBuilder) -> etree.Element:
    """Provide SVG with layer groups for testing."""
    builder = multislide_svg_builder

    # Layer 1: Background
    bg_layer = builder.add_slide_group('layer_background', css_class='layer-group')
    builder.add_rect(bg_layer, 0, 0, 1024, 768, fill='#f8f9fa')

    # Layer 2: Header
    header_layer = builder.add_slide_group('layer_header', css_class='layer-group')
    builder.add_rect(header_layer, 0, 0, 1024, 100, fill='#007bff')
    builder.add_text(header_layer, 512, 50, 'Presentation Title', font_size=28, text_anchor='middle', fill='white')

    # Layer 3: Content
    content_layer = builder.add_slide_group('layer_content', css_class='layer-group')
    builder.add_rect(content_layer, 50, 150, 924, 500, fill='white', stroke='#dee2e6', stroke_width='2')
    builder.add_text(content_layer, 512, 400, 'Main Content Area', font_size=24, text_anchor='middle')

    # Layer 4: Footer
    footer_layer = builder.add_slide_group('layer_footer', css_class='layer-group')
    builder.add_rect(footer_layer, 0, 700, 1024, 68, fill='#6c757d')
    builder.add_text(footer_layer, 512, 734, 'Footer Information', font_size=16, text_anchor='middle', fill='white')

    return builder.root


@pytest.fixture
def section_marker_svg(multislide_svg_builder: SVGTestBuilder) -> etree.Element:
    """Provide SVG with section markers for testing."""
    builder = multislide_svg_builder

    # Section 1: Introduction
    intro_section = builder.add_slide_group('section_introduction')
    builder.add_rect(intro_section, 0, 0, 1024, 768, fill='#f8f9fa')

    # Section title
    title1 = builder.add_text(intro_section, 512, 100, 'Introduction', font_size=48, text_anchor='middle', fill='#212529')
    title1.set('class', 'section-title')

    # Separator line
    line1 = etree.SubElement(intro_section, 'line')
    line1.set('x1', '200')
    line1.set('y1', '120')
    line1.set('x2', '824')
    line1.set('y2', '120')
    line1.set('stroke', '#007bff')
    line1.set('stroke-width', '3')

    # Section 2: Content
    content_section = builder.add_slide_group('section_content', transform='translate(0, 768)')
    builder.add_rect(content_section, 0, 0, 1024, 768, fill='#e8f4fd')

    title2 = builder.add_text(content_section, 512, 100, 'Main Content', font_size=48, text_anchor='middle', fill='#0056b3')
    title2.set('class', 'section-title')

    # Section 3: Conclusion
    conclusion_section = builder.add_slide_group('section_conclusion', transform='translate(0, 1536)')
    builder.add_rect(conclusion_section, 0, 0, 1024, 768, fill='#e8f5e8')

    title3 = builder.add_text(conclusion_section, 512, 100, 'Conclusion', font_size=48, text_anchor='middle', fill='#155724')
    title3.set('class', 'section-title')

    return builder.root


@pytest.fixture
def empty_svg(multislide_svg_builder: SVGTestBuilder) -> etree.Element:
    """Provide empty SVG for edge case testing."""
    return multislide_svg_builder.root


@pytest.fixture
def single_slide_svg(multislide_svg_builder: SVGTestBuilder) -> etree.Element:
    """Provide single slide SVG (should NOT be detected as multislide)."""
    builder = multislide_svg_builder

    # Single cohesive content
    builder.add_rect(builder.root, 0, 0, 1024, 768, fill='#f8f9fa')

    # Header
    header_rect = builder.add_rect(builder.root, 50, 50, 924, 80, fill='#007bff')
    builder.add_text(builder.root, 512, 90, 'Annual Report 2024', font_size=24, text_anchor='middle', fill='white')

    # Content area
    content_rect = builder.add_rect(builder.root, 100, 160, 824, 500, fill='white', stroke='#dee2e6', stroke_width='2')
    builder.add_text(builder.root, 512, 400, 'Unified content layout - not multislide', font_size=18, text_anchor='middle')

    return builder.root


# Expected Results Fixtures


@pytest.fixture
def expected_explicit_boundary_result() -> Dict[str, Any]:
    """Expected result for explicit boundary detection."""
    return {
        'is_multislide': True,
        'slide_count': 3,
        'detection_method': 'explicit_boundaries',
        'slides': [
            {
                'slide_number': 1,
                'elements': ['slide-1'],
                'content_summary': 'Introduction slide',
                'data_attributes': {'slide-number': '1'}
            },
            {
                'slide_number': 2,
                'elements': ['slide-2'],
                'content_summary': 'Content slide',
                'data_attributes': {'slide-number': '2'}
            },
            {
                'slide_number': 3,
                'elements': ['slide-3'],
                'content_summary': 'Conclusion slide',
                'data_attributes': {'slide-number': '3'}
            }
        ]
    }


@pytest.fixture
def expected_animation_sequence_result() -> Dict[str, Any]:
    """Expected result for animation sequence detection."""
    return {
        'is_multislide': True,
        'slide_count': 3,
        'detection_method': 'animation_keyframes',
        'slides': [
            {
                'slide_number': 1,
                'start_time': 0.0,
                'end_time': 2.0,
                'elements': ['slide1']
            },
            {
                'slide_number': 2,
                'start_time': 2.0,
                'end_time': 4.0,
                'elements': ['slide2']
            },
            {
                'slide_number': 3,
                'start_time': 4.0,
                'end_time': 6.0,
                'elements': ['slide3']
            }
        ],
        'metadata': {
            'total_duration': 6.0,
            'animation_complexity': 'simple'
        }
    }


@pytest.fixture
def expected_single_slide_result() -> Dict[str, Any]:
    """Expected result for single slide (negative test)."""
    return {
        'is_multislide': False,
        'slide_count': 1,
        'detection_method': 'none',
        'reason': 'unified_content_layout'
    }


# Test Configuration Fixtures


@pytest.fixture(scope="session")
def multislide_test_config() -> Dict[str, Any]:
    """Configuration for multislide testing."""
    return {
        'performance': {
            'max_processing_time': 5.0,  # seconds
            'max_memory_usage': 100 * 1024 * 1024,  # 100MB
        },
        'detection': {
            'animation_threshold': 0.1,  # minimum animation duration
            'nesting_depth_limit': 10,
            'element_count_limit': 10000,
        },
        'validation': {
            'strict_mode': True,
            'allow_missing_expected_outputs': True,
            'slide_count_tolerance': 0,  # Exact match required
        },
        'conversion': {
            'slide_width': 9144000,  # EMU
            'slide_height': 6858000,  # EMU
            'default_dpi': 96,
        }
    }


@pytest.fixture
def multislide_test_catalog(multislide_file_manager: TestFileManager) -> Dict[str, Any]:
    """Load multislide test catalog."""
    return multislide_file_manager.load_test_catalog()


# Mock Fixtures


@pytest.fixture
def mock_slide_detector():
    """Provide mock slide detector with configurable results."""
    return create_mock_slide_detector()


@pytest.fixture
def configured_slide_detector():
    """Provide pre-configured mock slide detector."""
    detector = create_mock_slide_detector()

    # Configure results for known test cases
    detector.configure_detection_result('explicit_boundary_test', {
        'is_multislide': True,
        'slide_count': 3,
        'detection_method': 'explicit_boundaries'
    })

    detector.configure_detection_result('animation_sequence_test', {
        'is_multislide': True,
        'slide_count': 3,
        'detection_method': 'animation_keyframes'
    })

    detector.configure_detection_result('single_slide_test', {
        'is_multislide': False,
        'slide_count': 1,
        'detection_method': 'none'
    })

    return detector


# Parametrized Test Fixtures


@pytest.fixture(params=[
    'animation_sequences/simple_fade_animation.svg',
    'animation_sequences/complex_transform_animation.svg',
    'nested_documents/simple_nested_slides.svg',
    'layer_groups/department_slides.svg',
    'section_markers/explicit_slide_boundaries.svg'
])
def multislide_sample_file(request, multislide_test_loader: SVGTestLoader):
    """Parametrized fixture that provides different multislide samples."""
    category, filename = request.param.split('/', 1)
    return multislide_test_loader.load_sample(category, filename)


@pytest.fixture(params=[
    ('explicit_boundaries', 'explicit_boundary_svg'),
    ('animation_keyframes', 'animation_sequence_svg'),
    ('nested_documents', 'nested_document_svg'),
    ('layer_groups', 'layer_group_svg'),
    ('section_markers', 'section_marker_svg')
])
def detection_strategy_test_case(request):
    """Parametrized fixture for different detection strategies."""
    strategy, svg_fixture_name = request.param
    return strategy, svg_fixture_name
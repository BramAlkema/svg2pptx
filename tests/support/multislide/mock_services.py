"""
Mock services for multislide testing.

Provides mock implementations of conversion services and dependencies
for isolated testing of multislide functionality.
"""

from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import Mock, MagicMock
from lxml import etree


class MockConversionServices:
    """Mock implementation of ConversionServices for testing."""

    def __init__(self):
        """Initialize mock services with default behavior."""
        self.unit_converter = MockUnitConverter()
        self.viewport_handler = MockViewportHandler()
        self.font_service = MockFontService()
        self.gradient_service = MockGradientService()
        self.pattern_service = MockPatternService()
        self.clip_service = MockClipService()
        self.filter_service = MockFilterService()
        self.animation_service = MockAnimationService()

    @classmethod
    def create_default(cls) -> 'MockConversionServices':
        """Create default mock services instance."""
        return cls()

    def configure_mock_behavior(self, **kwargs):
        """Configure specific mock behaviors."""
        for service_name, behavior in kwargs.items():
            if hasattr(self, service_name):
                getattr(self, service_name).configure(behavior)


class MockUnitConverter:
    """Mock unit converter for EMU conversions."""

    def __init__(self):
        """Initialize with standard conversion ratios."""
        self.px_to_emu_ratio = 9144  # Approximate EMU per pixel
        self.configured_conversions = {}

    def px_to_emu(self, px_value: float) -> int:
        """Convert pixels to EMU."""
        if px_value in self.configured_conversions:
            return self.configured_conversions[px_value]
        return int(px_value * self.px_to_emu_ratio)

    def emu_to_px(self, emu_value: int) -> float:
        """Convert EMU to pixels."""
        return emu_value / self.px_to_emu_ratio

    def parse_length(self, value: str, default_unit: str = 'px') -> int:
        """Parse length string to EMU."""
        if value in self.configured_conversions:
            return self.configured_conversions[value]

        # Simple parsing for common units
        if value.endswith('px'):
            return self.px_to_emu(float(value[:-2]))
        elif value.endswith('pt'):
            return self.px_to_emu(float(value[:-2]) * 1.33)  # Approximate pt to px
        elif value.endswith('%'):
            return int(float(value[:-1]) * 100)  # Mock percentage handling
        else:
            return self.px_to_emu(float(value))

    def configure(self, conversions: Dict[Any, Any]):
        """Configure specific conversion values."""
        self.configured_conversions.update(conversions)


class MockViewportHandler:
    """Mock viewport handler for slide dimensions."""

    def __init__(self):
        """Initialize with default slide dimensions."""
        self.slide_width = 9144000  # 10 inches in EMU
        self.slide_height = 6858000  # 7.5 inches in EMU
        self.current_viewbox = (0, 0, 800, 600)

    def get_slide_dimensions(self) -> Tuple[int, int]:
        """Get current slide dimensions in EMU."""
        return (self.slide_width, self.slide_height)

    def set_viewbox(self, viewbox: Tuple[float, float, float, float]):
        """Set the current SVG viewBox."""
        self.current_viewbox = viewbox

    def map_coordinates(self, x: float, y: float) -> Tuple[int, int]:
        """Map SVG coordinates to slide coordinates."""
        vx, vy, vw, vh = self.current_viewbox
        scale_x = self.slide_width / vw
        scale_y = self.slide_height / vh

        mapped_x = int((x - vx) * scale_x)
        mapped_y = int((y - vy) * scale_y)

        return (mapped_x, mapped_y)

    def configure(self, config: Dict[str, Any]):
        """Configure viewport behavior."""
        if 'slide_width' in config:
            self.slide_width = config['slide_width']
        if 'slide_height' in config:
            self.slide_height = config['slide_height']
        if 'viewbox' in config:
            self.current_viewbox = config['viewbox']


class MockFontService:
    """Mock font service for text rendering."""

    def __init__(self):
        """Initialize with default font mappings."""
        self.font_mappings = {
            'Arial': 'Arial',
            'Times': 'Times New Roman',
            'Courier': 'Courier New'
        }
        self.default_font = 'Arial'

    def resolve_font_family(self, font_family: str) -> str:
        """Resolve font family name."""
        return self.font_mappings.get(font_family, self.default_font)

    def calculate_text_metrics(
        self,
        text: str,
        font_family: str,
        font_size: float
    ) -> Dict[str, float]:
        """Calculate text metrics (mocked)."""
        # Simple character-based calculation
        char_width = font_size * 0.6
        text_width = len(text) * char_width
        text_height = font_size

        return {
            'width': text_width,
            'height': text_height,
            'baseline': text_height * 0.8
        }

    def configure(self, config: Dict[str, Any]):
        """Configure font service behavior."""
        if 'font_mappings' in config:
            self.font_mappings.update(config['font_mappings'])
        if 'default_font' in config:
            self.default_font = config['default_font']


class MockGradientService:
    """Mock gradient service for gradient fills."""

    def __init__(self):
        """Initialize gradient service."""
        self.gradients = {}
        self.next_id = 1

    def create_gradient(self, gradient_def: etree.Element) -> str:
        """Create a gradient and return its ID."""
        gradient_id = f"grad_{self.next_id}"
        self.next_id += 1

        # Store gradient definition
        self.gradients[gradient_id] = {
            'type': gradient_def.tag.split('}')[-1],  # Remove namespace
            'stops': len(gradient_def.xpath('.//svg:stop', namespaces={'svg': 'http://www.w3.org/2000/svg'}))
        }

        return gradient_id

    def get_gradient_info(self, gradient_id: str) -> Optional[Dict[str, Any]]:
        """Get gradient information."""
        return self.gradients.get(gradient_id)

    def configure(self, config: Dict[str, Any]):
        """Configure gradient service behavior."""
        if 'gradients' in config:
            self.gradients.update(config['gradients'])


class MockPatternService:
    """Mock pattern service for pattern fills."""

    def __init__(self):
        """Initialize pattern service."""
        self.patterns = {}
        self.next_id = 1

    def create_pattern(self, pattern_def: etree.Element) -> str:
        """Create a pattern and return its ID."""
        pattern_id = f"pattern_{self.next_id}"
        self.next_id += 1

        self.patterns[pattern_id] = {
            'width': pattern_def.get('width', '100%'),
            'height': pattern_def.get('height', '100%'),
            'elements': len(list(pattern_def))
        }

        return pattern_id

    def configure(self, config: Dict[str, Any]):
        """Configure pattern service behavior."""
        if 'patterns' in config:
            self.patterns.update(config['patterns'])


class MockClipService:
    """Mock clipping service for clip paths."""

    def __init__(self):
        """Initialize clip service."""
        self.clip_paths = {}
        self.next_id = 1

    def create_clip_path(self, clip_def: etree.Element) -> str:
        """Create a clip path and return its ID."""
        clip_id = f"clip_{self.next_id}"
        self.next_id += 1

        self.clip_paths[clip_id] = {
            'shapes': len(list(clip_def))
        }

        return clip_id

    def configure(self, config: Dict[str, Any]):
        """Configure clip service behavior."""
        if 'clip_paths' in config:
            self.clip_paths.update(config['clip_paths'])


class MockFilterService:
    """Mock filter service for SVG filters."""

    def __init__(self):
        """Initialize filter service."""
        self.filters = {}
        self.next_id = 1

    def create_filter(self, filter_def: etree.Element) -> str:
        """Create a filter and return its ID."""
        filter_id = f"filter_{self.next_id}"
        self.next_id += 1

        self.filters[filter_id] = {
            'effects': len(list(filter_def))
        }

        return filter_id

    def configure(self, config: Dict[str, Any]):
        """Configure filter service behavior."""
        if 'filters' in config:
            self.filters.update(config['filters'])


class MockAnimationService:
    """Mock animation service for SVG animations."""

    def __init__(self):
        """Initialize animation service."""
        self.animations = []
        self.timeline_data = {}

    def parse_animation(self, anim_element: etree.Element) -> Dict[str, Any]:
        """Parse animation element."""
        animation_data = {
            'element_id': anim_element.getparent().get('id', 'unknown'),
            'attribute': anim_element.get('attributeName', ''),
            'duration': anim_element.get('dur', '0s'),
            'values': anim_element.get('values', ''),
            'keyTimes': anim_element.get('keyTimes', '')
        }

        self.animations.append(animation_data)
        return animation_data

    def build_timeline(self, svg_element: etree.Element) -> Dict[str, Any]:
        """Build animation timeline from SVG."""
        animations = svg_element.xpath(
            "//svg:animate | //svg:animateTransform",
            namespaces={'svg': 'http://www.w3.org/2000/svg'}
        )

        timeline = {
            'total_duration': 0,
            'keyframes': [],
            'slides': []
        }

        for anim in animations:
            anim_data = self.parse_animation(anim)
            timeline['keyframes'].append(anim_data)

            # Extract duration
            dur = anim_data['duration']
            if dur.endswith('s'):
                duration = float(dur[:-2])
                timeline['total_duration'] = max(timeline['total_duration'], duration)

        self.timeline_data = timeline
        return timeline

    def get_slide_boundaries(self) -> List[Tuple[float, float]]:
        """Get slide time boundaries from timeline."""
        if not self.timeline_data:
            return [(0, 0)]

        # Simple implementation - divide timeline equally
        total_duration = self.timeline_data['total_duration']
        keyframe_count = len(self.timeline_data['keyframes'])

        if keyframe_count <= 1:
            return [(0, total_duration)]

        boundaries = []
        slide_duration = total_duration / keyframe_count

        for i in range(keyframe_count):
            start_time = i * slide_duration
            end_time = (i + 1) * slide_duration
            boundaries.append((start_time, end_time))

        return boundaries

    def configure(self, config: Dict[str, Any]):
        """Configure animation service behavior."""
        if 'timeline_data' in config:
            self.timeline_data = config['timeline_data']
        if 'animations' in config:
            self.animations = config['animations']


class MockSlideDetector:
    """Mock slide detector for testing multislide detection."""

    def __init__(self):
        """Initialize mock detector."""
        self.detection_results = {}
        self.configured_strategies = {}

    def detect_slides(
        self,
        svg_element: etree.Element,
        strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock slide detection."""
        svg_title = svg_element.find('.//{http://www.w3.org/2000/svg}title')
        svg_id = svg_title.text if svg_title is not None else 'unknown'

        # Return configured result if available
        if svg_id in self.detection_results:
            return self.detection_results[svg_id]

        # Default mock result
        return {
            'is_multislide': True,
            'slide_count': 3,
            'detection_method': strategy or 'mock_detection',
            'slides': [
                {'slide_number': 1, 'elements': ['slide_1']},
                {'slide_number': 2, 'elements': ['slide_2']},
                {'slide_number': 3, 'elements': ['slide_3']}
            ]
        }

    def configure_detection_result(self, svg_id: str, result: Dict[str, Any]):
        """Configure detection result for specific SVG."""
        self.detection_results[svg_id] = result

    def configure_strategy(self, strategy: str, behavior: Dict[str, Any]):
        """Configure behavior for specific detection strategy."""
        self.configured_strategies[strategy] = behavior


class MockMultiSlideDocument:
    """Mock MultiSlideDocument for testing."""

    def __init__(self, slides: Optional[List[Dict[str, Any]]] = None):
        """Initialize mock document."""
        self.slides = slides or []
        self.metadata = {}
        self.conversion_context = None

    def add_slide(self, slide_data: Dict[str, Any]):
        """Add slide to document."""
        self.slides.append(slide_data)

    def get_slide_count(self) -> int:
        """Get number of slides."""
        return len(self.slides)

    def get_slide(self, index: int) -> Optional[Dict[str, Any]]:
        """Get slide by index."""
        if 0 <= index < len(self.slides):
            return self.slides[index]
        return None

    def set_metadata(self, metadata: Dict[str, Any]):
        """Set document metadata."""
        self.metadata = metadata

    def to_pptx_bytes(self) -> bytes:
        """Mock PPTX generation."""
        return b"Mock PPTX data"

    def save(self, file_path: str):
        """Mock save to file."""
        with open(file_path, 'wb') as f:
            f.write(self.to_pptx_bytes())


def create_mock_services(**overrides) -> MockConversionServices:
    """Factory function to create mock services with overrides."""
    services = MockConversionServices()

    for service_name, config in overrides.items():
        if hasattr(services, service_name):
            getattr(services, service_name).configure(config)

    return services


def create_mock_slide_detector(**detection_results) -> MockSlideDetector:
    """Factory function to create mock slide detector with configured results."""
    detector = MockSlideDetector()

    for svg_id, result in detection_results.items():
        detector.configure_detection_result(svg_id, result)

    return detector
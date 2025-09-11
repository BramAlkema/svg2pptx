"""
Tests for Multi-slide Detection and Conversion

Tests the multi-slide functionality including:
- Slide boundary detection algorithms
- Animation sequence detection
- Nested SVG page detection
- Layer group identification
- Section marker recognition
- Conversion strategy recommendation
- Multi-slide document generation
"""

import pytest
from lxml import etree as ET
from unittest.mock import Mock, patch, MagicMock
from src.multislide.detection import (
    SlideDetector, SlideBoundary, SlideType,
    SlideDetector
)
from src.multislide.document import MultiSlideDocument, SlideContent
from src.svg2multislide import MultiSlideConverter


class TestSlideDetector:
    """Test slide boundary detection functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.detector = SlideDetector()

    def test_initialization(self):
        """Test detector initialization"""
        detector = SlideDetector()
        assert detector.enable_animation_detection is True
        assert detector.enable_nested_svg_detection is True
        assert detector.enable_layer_detection is True
        assert detector.animation_threshold == 3
        assert hasattr(detector, 'detection_stats')

    def test_custom_initialization(self):
        """Test detector with custom settings"""
        detector = SlideDetector(
            enable_animation_detection=False,
            animation_threshold=5
        )
        assert detector.enable_animation_detection is False
        assert detector.animation_threshold == 5

    def test_detect_boundaries_empty_svg(self):
        """Test boundary detection on empty SVG"""
        svg_xml = "<svg></svg>"
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector.detect_boundaries(svg_root)
        
        assert len(boundaries) == 0
        assert self.detector.detection_stats['animation_keyframes'] == 0
        assert self.detector.detection_stats['nested_svgs'] == 0


class TestExplicitMarkerDetection:
    """Test detection of explicit slide markers"""

    def setup_method(self):
        """Set up test fixtures"""
        self.detector = SlideDetector()

    def test_detect_data_slide_break_true(self):
        """Test detection of data-slide-break="true" markers"""
        svg_xml = """
        <svg>
            <g data-slide-break="true" id="slide1">
                <rect x="0" y="0" width="100" height="100"/>
            </g>
            <g data-slide-break="true" id="slide2">
                <circle cx="50" cy="50" r="25"/>
            </g>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_explicit_markers(svg_root)
        
        assert len(boundaries) == 2
        assert all(b.boundary_type == SlideType.SECTION_MARKER for b in boundaries)
        assert all(b.confidence == 1.0 for b in boundaries)
        assert boundaries[0].element.get('id') == 'slide1'
        assert boundaries[1].element.get('id') == 'slide2'

    def test_detect_data_slide_break_numeric(self):
        """Test detection of data-slide-break="1" markers"""
        svg_xml = """
        <svg>
            <rect data-slide-break="1" x="0" y="0" width="100" height="100"/>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_explicit_markers(svg_root)
        
        assert len(boundaries) == 1
        assert boundaries[0].confidence == 1.0

    def test_no_explicit_markers(self):
        """Test when no explicit markers are present"""
        svg_xml = """
        <svg>
            <rect x="0" y="0" width="100" height="100"/>
            <circle cx="50" cy="50" r="25"/>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_explicit_markers(svg_root)
        
        assert len(boundaries) == 0


class TestAnimationDetection:
    """Test animation keyframe detection"""

    def setup_method(self):
        """Set up test fixtures"""
        self.detector = SlideDetector(animation_threshold=2)

    def test_detect_animation_elements(self):
        """Test detection of animation elements"""
        svg_xml = """
        <svg>
            <rect x="0" y="0" width="100" height="100">
                <animate attributeName="x" values="0;100;0" dur="2s" begin="0s"/>
                <animate attributeName="y" values="0;50;0" dur="2s" begin="0s"/>
                <animateTransform attributeName="transform" type="rotate" 
                                values="0;360" dur="2s" begin="1s"/>
            </rect>
            <circle cx="50" cy="50" r="25">
                <animate attributeName="r" values="25;50;25" dur="3s" begin="1s"/>
            </circle>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_animation_keyframes(svg_root)
        
        # Should detect time groups with multiple simultaneous animations
        assert len(boundaries) >= 1
        assert all(b.boundary_type == SlideType.ANIMATION_KEYFRAME for b in boundaries)

    def test_animation_below_threshold(self):
        """Test animation detection below threshold"""
        svg_xml = """
        <svg>
            <rect x="0" y="0" width="100" height="100">
                <animate attributeName="x" values="0;100" dur="2s"/>
            </rect>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_animation_keyframes(svg_root)
        
        # Should not detect boundaries if below threshold
        assert len(boundaries) == 0

    def test_group_animations_by_time(self):
        """Test grouping animations by start time"""
        # Create mock animation elements
        anim1 = Mock()
        anim1.get.return_value = "0s"
        
        anim2 = Mock()
        anim2.get.return_value = "1s"
        
        anim3 = Mock()
        anim3.get.return_value = "0s"
        
        animations = [anim1, anim2, anim3]
        
        time_groups = self.detector._group_animations_by_time(animations)
        
        assert len(time_groups) == 2
        assert len(time_groups[0.0]) == 2  # anim1 and anim3
        assert len(time_groups[1.0]) == 1  # anim2

    def test_group_animations_invalid_time(self):
        """Test grouping animations with invalid time values"""
        anim1 = Mock()
        anim1.get.return_value = "invalid"
        
        anim2 = Mock()
        anim2.get.return_value = "2.5s"
        
        animations = [anim1, anim2]
        
        time_groups = self.detector._group_animations_by_time(animations)
        
        assert 0.0 in time_groups  # Invalid time defaults to 0
        assert 2.5 in time_groups
        assert len(time_groups[0.0]) == 1
        assert len(time_groups[2.5]) == 1


class TestNestedSVGDetection:
    """Test nested SVG element detection"""

    def setup_method(self):
        """Set up test fixtures"""
        self.detector = SlideDetector()

    def test_detect_nested_svg_with_dimensions(self):
        """Test detection of nested SVG with explicit dimensions"""
        svg_xml = """
        <svg viewBox="0 0 800 600">
            <svg x="0" y="0" width="400" height="300" id="page1">
                <rect x="0" y="0" width="400" height="300" fill="red"/>
            </svg>
            <svg x="400" y="0" width="400" height="300" id="page2">
                <rect x="0" y="0" width="400" height="300" fill="blue"/>
            </svg>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_nested_svgs(svg_root)
        
        assert len(boundaries) == 2
        assert all(b.boundary_type == SlideType.NESTED_SVG for b in boundaries)
        assert boundaries[0].element.get('id') == 'page1'
        assert boundaries[1].element.get('id') == 'page2'

    def test_detect_page_like_dimensions(self):
        """Test detection based on page-like dimensions"""
        svg_xml = """
        <svg>
            <svg width="8.5in" height="11in" id="letter-page">
                <text x="10" y="30">Letter size page</text>
            </svg>
            <svg width="210mm" height="297mm" id="a4-page">
                <text x="10" y="30">A4 size page</text>
            </svg>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_nested_svgs(svg_root)
        
        assert len(boundaries) == 2
        # Should have high confidence for page-like dimensions
        assert all(b.confidence > 0.8 for b in boundaries)

    def test_detect_page_keywords(self):
        """Test detection based on 'page' keywords in id/class"""
        svg_xml = """
        <svg>
            <svg width="100" height="100" id="page-content" class="slide-page">
                <rect x="0" y="0" width="100" height="100"/>
            </svg>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_nested_svgs(svg_root)
        
        assert len(boundaries) == 1
        assert boundaries[0].confidence > 0.8  # High confidence for page keywords

    def test_skip_root_svg(self):
        """Test that root SVG element is skipped"""
        svg_xml = """
        <svg width="800" height="600">
            <rect x="0" y="0" width="800" height="600"/>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_nested_svgs(svg_root)
        
        assert len(boundaries) == 0  # Root SVG should be skipped


class TestLayerGroupDetection:
    """Test layer group detection"""

    def setup_method(self):
        """Set up test fixtures"""
        self.detector = SlideDetector()

    def test_detect_layer_groups_by_id(self):
        """Test detection of layer groups by ID"""
        svg_xml = """
        <svg>
            <g id="layer1">
                <rect x="0" y="0" width="100" height="100"/>
                <circle cx="50" cy="50" r="25"/>
                <text x="10" y="20">Layer 1</text>
            </g>
            <g id="background-layer">
                <rect x="0" y="0" width="800" height="600" fill="white"/>
                <path d="M0,0 L800,600"/>
                <ellipse cx="400" cy="300" rx="200" ry="150"/>
            </g>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_layer_groups(svg_root)
        
        assert len(boundaries) == 2
        assert all(b.boundary_type == SlideType.LAYER_GROUP for b in boundaries)
        assert boundaries[0].confidence == 0.7

    def test_detect_layer_groups_by_class(self):
        """Test detection of layer groups by class"""
        svg_xml = """
        <svg>
            <g class="slide-layer" id="slide1">
                <rect x="0" y="0" width="100" height="100"/>
                <circle cx="50" cy="50" r="25"/>
                <text x="10" y="20">Slide content</text>
            </g>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_layer_groups(svg_root)
        
        assert len(boundaries) == 1
        assert 'slide-layer' in boundaries[0].element.get('class')

    def test_ignore_groups_without_content(self):
        """Test that groups without significant content are ignored"""
        svg_xml = """
        <svg>
            <g id="layer-empty">
                <!-- Not enough content elements -->
                <text x="0" y="0">Just one element</text>
            </g>
            <g id="layer-full">
                <rect x="0" y="0" width="100" height="100"/>
                <circle cx="50" cy="50" r="25"/>
                <text x="10" y="20">Enough content</text>
            </g>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_layer_groups(svg_root)
        
        # Should only detect the group with sufficient content
        assert len(boundaries) == 1
        assert boundaries[0].element.get('id') == 'layer-full'

    def test_layer_keywords(self):
        """Test detection based on layer-related keywords"""
        keywords = ['layer', 'slide', 'page', 'step', 'frame']
        
        for keyword in keywords:
            svg_xml = f"""
            <svg>
                <g id="{keyword}-content">
                    <rect x="0" y="0" width="100" height="100"/>
                    <circle cx="50" cy="50" r="25"/>
                    <text x="10" y="20">Content</text>
                </g>
            </svg>
            """
            svg_root = ET.fromstring(svg_xml)
            
            boundaries = self.detector._detect_layer_groups(svg_root)
            
            assert len(boundaries) == 1, f"Failed to detect keyword: {keyword}"


class TestSectionMarkerDetection:
    """Test section marker detection"""

    def setup_method(self):
        """Set up test fixtures"""
        self.detector = SlideDetector()

    def test_detect_section_text(self):
        """Test detection of section marker text"""
        svg_xml = """
        <svg>
            <text x="10" y="30" font-size="24">Section 1</text>
            <text x="10" y="60" font-size="12">Regular content text here</text>
            <text x="10" y="90" font-size="20">Chapter Introduction</text>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_section_markers(svg_root)
        
        # Should detect section-like text
        assert len(boundaries) >= 1
        assert any(b.boundary_type == SlideType.SECTION_MARKER for b in boundaries)

    def test_detect_large_font_size(self):
        """Test detection based on large font size"""
        svg_xml = """
        <svg>
            <text x="10" y="30" font-size="24px">Large Heading</text>
            <text x="10" y="60" font-size="12px">Normal text</text>
            <text x="10" y="90" font-size="28pt">Another Heading</text>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_section_markers(svg_root)
        
        # Should detect large text elements
        assert len(boundaries) == 2
        assert all(b.boundary_type == SlideType.SECTION_MARKER for b in boundaries)

    def test_ignore_long_text(self):
        """Test that very long text is not considered a section marker"""
        svg_xml = """
        <svg>
            <text x="10" y="30">This is a very long paragraph of text that should not be considered a section marker because it contains too many characters and is clearly body content rather than a heading</text>
            <text x="10" y="60">Short Title</text>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_section_markers(svg_root)
        
        # Should only detect the short text
        assert len(boundaries) <= 1
        if boundaries:
            assert "Short Title" in boundaries[0].metadata.get('text_content', '')

    def test_ignore_numeric_text(self):
        """Test that numeric text is ignored"""
        svg_xml = """
        <svg>
            <text x="10" y="30">Data: 12345</text>
            <text x="10" y="60">Section Header</text>
        </svg>
        """
        svg_root = ET.fromstring(svg_xml)
        
        boundaries = self.detector._detect_section_markers(svg_root)
        
        # Should ignore text with numbers (likely data)
        section_texts = [b.metadata.get('text_content', '') for b in boundaries]
        assert not any('12345' in text for text in section_texts)


class TestConversionStrategyRecommendation:
    """Test conversion strategy recommendation logic"""

    def setup_method(self):
        """Set up test fixtures"""
        self.detector = SlideDetector()

    def test_no_boundaries_single_slide(self):
        """Test recommendation when no boundaries detected"""
        boundaries = []
        
        strategy = self.detector.recommend_conversion_strategy(boundaries)
        
        assert strategy['strategy'] == 'single_slide'
        assert strategy['confidence'] == 1.0
        assert 'No slide boundaries detected' in strategy['reason']

    def test_animation_sequence_strategy(self):
        """Test recommendation for animation sequence"""
        boundaries = [
            Mock(boundary_type=SlideType.ANIMATION_KEYFRAME, confidence=0.9),
            Mock(boundary_type=SlideType.ANIMATION_KEYFRAME, confidence=0.8),
            Mock(boundary_type=SlideType.ANIMATION_KEYFRAME, confidence=0.85),
            Mock(boundary_type=SlideType.ANIMATION_KEYFRAME, confidence=0.9)
        ]
        
        # Mock the value attribute for the enum
        for b in boundaries:
            b.boundary_type.value = 'animation_keyframe'
        
        strategy = self.detector.recommend_conversion_strategy(boundaries)
        
        assert strategy['strategy'] == 'animation_sequence'
        assert '4 animation keyframes' in strategy['reason']
        assert strategy['boundary_count'] == 4

    def test_nested_pages_strategy(self):
        """Test recommendation for nested SVG pages"""
        boundaries = [
            Mock(boundary_type=SlideType.NESTED_SVG, confidence=0.95),
            Mock(boundary_type=SlideType.NESTED_SVG, confidence=0.9)
        ]
        
        for b in boundaries:
            b.boundary_type.value = 'nested_svg'
        
        strategy = self.detector.recommend_conversion_strategy(boundaries)
        
        assert strategy['strategy'] == 'nested_pages'
        assert '2 nested SVG pages' in strategy['reason']

    def test_layer_slides_strategy(self):
        """Test recommendation for layer-based slides"""
        boundaries = [
            Mock(boundary_type=SlideType.LAYER_GROUP, confidence=0.7),
            Mock(boundary_type=SlideType.LAYER_GROUP, confidence=0.8)
        ]
        
        for b in boundaries:
            b.boundary_type.value = 'layer_group'
        
        strategy = self.detector.recommend_conversion_strategy(boundaries)
        
        assert strategy['strategy'] == 'layer_slides'
        assert '2 layer groups' in strategy['reason']

    def test_section_slides_strategy(self):
        """Test recommendation for section-based slides"""
        boundaries = [
            Mock(boundary_type=SlideType.SECTION_MARKER, confidence=0.6),
            Mock(boundary_type=SlideType.SECTION_MARKER, confidence=0.8)
        ]
        
        for b in boundaries:
            b.boundary_type.value = 'section_marker'
        
        strategy = self.detector.recommend_conversion_strategy(boundaries)
        
        assert strategy['strategy'] == 'section_slides'
        assert '2 section markers' in strategy['reason']

    def test_mixed_boundaries_strategy(self):
        """Test recommendation for mixed boundary types"""
        boundaries = [
            Mock(boundary_type=SlideType.LAYER_GROUP, confidence=0.7),
            Mock(boundary_type=SlideType.SECTION_MARKER, confidence=0.6)
        ]
        
        boundaries[0].boundary_type.value = 'layer_group'
        boundaries[1].boundary_type.value = 'section_marker'
        
        strategy = self.detector.recommend_conversion_strategy(boundaries)
        
        assert strategy['strategy'] == 'content_slides'
        assert '2 mixed slide boundaries' in strategy['reason']

    def test_confidence_calculation(self):
        """Test average confidence calculation"""
        boundaries = [
            Mock(boundary_type=SlideType.LAYER_GROUP, confidence=0.8),
            Mock(boundary_type=SlideType.LAYER_GROUP, confidence=0.6)
        ]
        
        for b in boundaries:
            b.boundary_type.value = 'layer_group'
        
        strategy = self.detector.recommend_conversion_strategy(boundaries)
        
        assert strategy['confidence'] == 0.7  # Average of 0.8 and 0.6


class TestSlidePlanGeneration:
    """Test slide plan generation"""

    def setup_method(self):
        """Set up test fixtures"""
        self.detector = SlideDetector()

    def test_generate_plan_no_boundaries(self):
        """Test plan generation with no boundaries"""
        svg_root = Mock()
        svg_root.get.return_value = "100"  # Mock width/height/viewBox
        
        plan = self.detector.generate_slide_plan(svg_root, boundaries=[])
        
        assert plan['slide_count'] == 1
        assert len(plan['slides']) == 1
        assert plan['slides'][0]['slide_id'] == 1
        assert plan['slides'][0]['title'] == 'SVG Content'
        assert plan['slides'][0]['content_source'] == 'full_svg'

    def test_generate_plan_with_boundaries(self):
        """Test plan generation with detected boundaries"""
        svg_root = Mock()
        svg_root.get.return_value = "100"
        
        boundaries = [
            Mock(title="Slide 1", boundary_type=SlideType.LAYER_GROUP, 
                 confidence=0.8, metadata={'layer': 'info'}),
            Mock(title="Slide 2", boundary_type=SlideType.SECTION_MARKER, 
                 confidence=0.7, metadata={'text': 'content'})
        ]
        
        boundaries[0].boundary_type.value = 'layer_group'
        boundaries[1].boundary_type.value = 'section_marker'
        boundaries[0].element = Mock()
        boundaries[1].element = Mock()
        
        plan = self.detector.generate_slide_plan(svg_root, boundaries=boundaries)
        
        assert plan['slide_count'] == 2
        assert len(plan['slides']) == 2
        
        # Check first slide
        assert plan['slides'][0]['slide_id'] == 1
        assert plan['slides'][0]['title'] == "Slide 1"
        assert plan['slides'][0]['content_source'] == 'layer_group'
        assert plan['slides'][0]['confidence'] == 0.8
        
        # Check second slide
        assert plan['slides'][1]['slide_id'] == 2
        assert plan['slides'][1]['title'] == "Slide 2"
        assert plan['slides'][1]['content_source'] == 'section_marker'

    def test_generate_plan_with_svg_info(self):
        """Test that plan includes SVG information"""
        svg_root = Mock()
        svg_root.get = Mock(side_effect=lambda attr: {
            'width': '800',
            'height': '600',
            'viewBox': '0 0 800 600'
        }.get(attr))
        
        plan = self.detector.generate_slide_plan(svg_root, boundaries=[])
        
        assert plan['svg_info']['width'] == '800'
        assert plan['svg_info']['height'] == '600'
        assert plan['svg_info']['viewBox'] == '0 0 800 600'

    def test_generate_plan_includes_detection_stats(self):
        """Test that plan includes detection statistics"""
        svg_root = Mock()
        svg_root.get.return_value = "100"
        
        # Set up detection stats
        self.detector.detection_stats = {
            'animation_keyframes': 2,
            'nested_svgs': 1,
            'layer_groups': 3
        }
        
        plan = self.detector.generate_slide_plan(svg_root, boundaries=[])
        
        assert 'detection_stats' in plan
        assert plan['detection_stats']['animation_keyframes'] == 2
        assert plan['detection_stats']['layer_groups'] == 3


class TestMultiSlideConverterIntegration:
    """Integration tests for multi-slide converter"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = MultiSlideConverter()

    def test_converter_initialization(self):
        """Test multi-slide converter initialization"""
        converter = MultiSlideConverter(
            enable_multislide_detection=False,
            animation_threshold=5
        )
        
        assert converter.enable_multislide_detection is False
        assert converter.slide_detector.animation_threshold == 5
        assert hasattr(converter, 'conversion_stats')

    def test_convert_with_boundaries_detection(self):
        """Test conversion with automatic boundary detection"""
        svg_xml = """
        <svg viewBox="0 0 800 600">
            <g id="layer1" class="slide-layer">
                <rect x="0" y="0" width="400" height="300" fill="red"/>
                <text x="10" y="30">Slide 1 Content</text>
                <circle cx="200" cy="150" r="50"/>
            </g>
            <g id="layer2" class="slide-layer">
                <rect x="400" y="300" width="400" height="300" fill="blue"/>
                <text x="410" y="330">Slide 2 Content</text>
                <ellipse cx="600" cy="450" rx="100" ry="75"/>
            </g>
        </svg>
        """
        svg_element = ET.fromstring(svg_xml)
        
        with patch('src.svg2multislide.MultiSlideDocument') as MockDoc:
            mock_doc_instance = Mock()
            MockDoc.return_value = mock_doc_instance
            
            with patch.object(self.converter, '_convert_to_single_slide') as mock_single:
                mock_single.return_value = {'success': True, 'slide_count': 1}
                
                from pathlib import Path
                result = self.converter._convert_svg_element(
                    svg_element, Path('/tmp/test.pptx'), {}
                )
        
        # Should attempt multi-slide detection
        assert 'conversion_type' in result

    def test_fallback_to_single_slide(self):
        """Test fallback to single slide conversion"""
        simple_svg = """
        <svg>
            <rect x="0" y="0" width="100" height="100" fill="red"/>
        </svg>
        """
        svg_element = ET.fromstring(simple_svg)
        
        with patch.object(self.converter, '_convert_to_single_slide') as mock_single:
            mock_single.return_value = {
                'success': True, 
                'slide_count': 1, 
                'conversion_type': 'single_slide_fallback'
            }
            
            from pathlib import Path
            result = self.converter._convert_svg_element(
                svg_element, Path('/tmp/test.pptx'), {}
            )
        
        assert result['conversion_type'] == 'single_slide_fallback'
        mock_single.assert_called_once()

    @patch('src.svg2multislide.ET.parse')
    def test_convert_multiple_svg_files(self, mock_parse):
        """Test conversion of multiple SVG files"""
        # Mock file parsing
        mock_tree = Mock()
        mock_svg_root = Mock()
        mock_tree.getroot.return_value = mock_svg_root
        mock_parse.return_value = mock_tree
        
        with patch('src.svg2multislide.MultiSlideDocument') as MockDoc:
            mock_doc_instance = Mock()
            MockDoc.return_value = mock_doc_instance
            mock_doc_instance.slides = [Mock(), Mock()]  # 2 slides
            
            from pathlib import Path
            svg_paths = [Path('/tmp/slide1.svg'), Path('/tmp/slide2.svg')]
            
            # Mock path existence
            with patch.object(Path, 'exists', return_value=True):
                result = self.converter._convert_multiple_svgs(
                    svg_paths, Path('/tmp/output.pptx'), {}
                )
        
        assert result['success'] is True
        assert result['conversion_type'] == 'multi_file_batch'
        assert result['slide_count'] == 2
        mock_doc_instance.generate_pptx.assert_called_once()

    def test_conversion_statistics_tracking(self):
        """Test that conversion statistics are properly tracked"""
        self.converter.conversion_stats = {}
        
        # Initialize stats
        self.converter._convert_svg_element.__globals__['self'] = self.converter
        
        # Test that stats are initialized
        simple_svg = ET.fromstring("<svg><rect x='0' y='0' width='100' height='100'/></svg>")
        
        with patch.object(self.converter, '_convert_to_single_slide') as mock_single:
            mock_single.return_value = {'success': True, 'slide_count': 1}
            
            from pathlib import Path
            self.converter._convert_svg_element(simple_svg, Path('/tmp/test.pptx'), {})
        
        # Check that stats were set
        assert 'input_type' in self.converter.conversion_stats
        assert self.converter.conversion_stats['input_type'] == 'svg_element'
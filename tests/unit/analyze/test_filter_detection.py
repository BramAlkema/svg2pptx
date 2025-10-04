"""
Unit tests for filter type detection in SVG Analyzer API.

Tests that all 17 SVG filter primitives are correctly detected and mapped.
"""

import pytest
from lxml import etree as ET
from core.analyze.api_adapter import SVGAnalyzerAPI
from core.analyze.constants import FILTER_NAME_MAP


class TestFilterDetection:
    """Test filter type detection with proper name mapping."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return SVGAnalyzerAPI()

    def test_all_17_filter_primitives_mapped(self):
        """Test that FILTER_NAME_MAP contains all 17 SVG filter primitives."""
        expected_filters = {
            'feBlend', 'feColorMatrix', 'feComponentTransfer', 'feComposite',
            'feConvolveMatrix', 'feDiffuseLighting', 'feDisplacementMap',
            'feDropShadow', 'feFlood', 'feGaussianBlur', 'feImage',
            'feMerge', 'feMorphology', 'feOffset', 'feSpecularLighting',
            'feTile', 'feTurbulence'
        }

        assert set(FILTER_NAME_MAP.keys()) == expected_filters
        assert len(FILTER_NAME_MAP) == 17

    def test_detect_single_blur_filter(self, analyzer):
        """Test detection of feGaussianBlur filter."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="blur1">
                    <feGaussianBlur stdDeviation="5"/>
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert 'blur' in filter_types
        assert len(filter_types) == 1

    def test_detect_drop_shadow_filter(self, analyzer):
        """Test detection of feDropShadow filter."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="shadow1">
                    <feDropShadow dx="2" dy="2" stdDeviation="3"/>
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert 'dropshadow' in filter_types
        assert len(filter_types) == 1

    def test_detect_all_17_filters_simultaneously(self, analyzer):
        """Test detection when all 17 filter types are present."""
        # Create SVG with all 17 filter primitives
        filter_elements = []
        for fe_name in FILTER_NAME_MAP.keys():
            filter_elements.append(f'<{fe_name}/>')

        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="all_filters">
                    {''.join(filter_elements)}
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        # Should detect all 17 unique filter types
        assert len(filter_types) == 17
        # Verify all mapped names are present
        for simple_name in FILTER_NAME_MAP.values():
            assert simple_name in filter_types

    def test_detect_multiple_instances_same_filter(self, analyzer):
        """Test that multiple instances of same filter only counted once."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="blur1">
                    <feGaussianBlur stdDeviation="3"/>
                </filter>
                <filter id="blur2">
                    <feGaussianBlur stdDeviation="5"/>
                </filter>
                <filter id="blur3">
                    <feGaussianBlur stdDeviation="7"/>
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert filter_types == {'blur'}
        assert len(filter_types) == 1

    def test_detect_complex_filter_with_multiple_primitives(self, analyzer):
        """Test detection of complex filter with multiple primitives."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="complex">
                    <feGaussianBlur in="SourceGraphic" stdDeviation="2"/>
                    <feOffset dx="2" dy="2"/>
                    <feBlend mode="normal"/>
                    <feColorMatrix type="matrix" values="..."/>
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert 'blur' in filter_types
        assert 'offset' in filter_types
        assert 'blend' in filter_types
        assert 'colormatrix' in filter_types
        assert len(filter_types) == 4

    def test_detect_no_filters(self, analyzer):
        """Test detection when no filters present."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <rect width="100" height="100" fill="blue"/>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert len(filter_types) == 0
        assert filter_types == set()

    def test_filter_name_mapping_accuracy(self):
        """Test that filter name mapping is correct for all 17 primitives."""
        expected_mappings = {
            'feBlend': 'blend',
            'feColorMatrix': 'colormatrix',
            'feComponentTransfer': 'componenttransfer',
            'feComposite': 'composite',
            'feConvolveMatrix': 'convolvematrix',
            'feDiffuseLighting': 'diffuselighting',
            'feDisplacementMap': 'displacementmap',
            'feDropShadow': 'dropshadow',
            'feFlood': 'flood',
            'feGaussianBlur': 'blur',
            'feImage': 'image',
            'feMerge': 'merge',
            'feMorphology': 'morphology',
            'feOffset': 'offset',
            'feSpecularLighting': 'specularlighting',
            'feTile': 'tile',
            'feTurbulence': 'turbulence'
        }

        assert FILTER_NAME_MAP == expected_mappings

    def test_detect_lighting_filters(self, analyzer):
        """Test detection of lighting effect filters."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="lighting">
                    <feDiffuseLighting>
                        <fePointLight x="100" y="100" z="50"/>
                    </feDiffuseLighting>
                    <feSpecularLighting>
                        <feDistantLight azimuth="45" elevation="30"/>
                    </feSpecularLighting>
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert 'diffuselighting' in filter_types
        assert 'specularlighting' in filter_types
        assert len(filter_types) == 2

    def test_detect_displacement_and_turbulence(self, analyzer):
        """Test detection of displacement and turbulence filters."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="distortion">
                    <feTurbulence type="fractalNoise" baseFrequency="0.05"/>
                    <feDisplacementMap in="SourceGraphic" scale="50"/>
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert 'turbulence' in filter_types
        assert 'displacementmap' in filter_types
        assert len(filter_types) == 2

    def test_detect_tile_and_merge(self, analyzer):
        """Test detection of feTile and feMerge filters."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="pattern">
                    <feTile/>
                    <feMerge>
                        <feMergeNode/>
                        <feMergeNode/>
                    </feMerge>
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert 'tile' in filter_types
        assert 'merge' in filter_types
        assert len(filter_types) == 2

    def test_detect_convolve_matrix(self, analyzer):
        """Test detection of feConvolveMatrix filter."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="sharpen">
                    <feConvolveMatrix order="3" kernelMatrix="0 -1 0 -1 5 -1 0 -1 0"/>
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert 'convolvematrix' in filter_types
        assert len(filter_types) == 1

    def test_detect_component_transfer(self, analyzer):
        """Test detection of feComponentTransfer filter."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="adjust">
                    <feComponentTransfer>
                        <feFuncR type="linear" slope="1.5"/>
                        <feFuncG type="linear" slope="1.5"/>
                        <feFuncB type="linear" slope="1.5"/>
                    </feComponentTransfer>
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert 'componenttransfer' in filter_types
        assert len(filter_types) == 1

    def test_detect_composite_filter(self, analyzer):
        """Test detection of feComposite filter."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="composite">
                    <feComposite in="SourceGraphic" in2="SourceAlpha" operator="in"/>
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert 'composite' in filter_types
        assert len(filter_types) == 1

    def test_detect_morphology_filter(self, analyzer):
        """Test detection of feMorphology filter."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="morph">
                    <feMorphology operator="dilate" radius="2"/>
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert 'morphology' in filter_types
        assert len(filter_types) == 1

    def test_detect_flood_and_image_filters(self, analyzer):
        """Test detection of feFlood and feImage filters."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="special">
                    <feFlood flood-color="blue" flood-opacity="0.5"/>
                    <feImage href="image.png"/>
                </filter>
            </defs>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert 'flood' in filter_types
        assert 'image' in filter_types
        assert len(filter_types) == 2


class TestFilterDetectionRegression:
    """Regression tests to ensure old naive parsing is fixed."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return SVGAnalyzerAPI()

    def test_gaussian_blur_not_broken_by_naive_replace(self, analyzer):
        """Test that feGaussianBlur correctly maps to 'blur' (not 'gaussianblur')."""
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <filter><feGaussianBlur stdDeviation="5"/></filter>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        assert 'blur' in filter_types
        # Old naive code would produce 'gaussianblur' (incorrect)
        assert 'gaussianblur' not in filter_types

    def test_no_naive_string_replacement_artifacts(self, analyzer):
        """Test that naive .replace('fe', '') doesn't create wrong names."""
        # If naive replace was used, 'feOffset' -> 'Offset' -> 'offset' (correct by luck)
        # But 'feMerge' -> 'Merge' -> 'merge' (correct by luck)
        # However 'feImage' -> 'Image' -> 'image' (correct by luck)
        # The issue is when filters have complex names

        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <filter>
                <feComponentTransfer/>
                <feConvolveMatrix/>
                <feDiffuseLighting/>
            </filter>
        </svg>
        '''
        svg_root = ET.fromstring(svg.encode('utf-8'))
        filter_types = analyzer._detect_filter_types(svg_root)

        # With mapping: correct names
        assert 'componenttransfer' in filter_types
        assert 'convolvematrix' in filter_types
        assert 'diffuselighting' in filter_types

        # Old naive approach would produce broken names like:
        # 'ComponentTransfer', 'ConvolveMatrix', 'DiffuseLighting'
        assert 'ComponentTransfer' not in filter_types
        assert 'ConvolveMatrix' not in filter_types

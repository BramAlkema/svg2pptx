#!/usr/bin/env python3
"""
End-to-end visual tests for CustGeom clipping functionality.

Tests custGeom generation with real-world SVG files, validates output quality,
and performs performance benchmarks.
"""

import pytest
import time
import json
from pathlib import Path
from unittest.mock import Mock
from lxml import etree as ET
from typing import Dict

from core.converters.custgeom_generator import CustGeomGenerator
from core.converters.clippath_analyzer import ClipPathAnalyzer
from core.converters.masking import MaskingConverter
from core.converters.clippath_types import ClipPathDefinition, ClippingType
from core.converters.base import ConversionContext
from core.services.conversion_services import ConversionServices


class TestCustGeomClipping:
    """Visual and performance tests for CustGeom clipping."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services
        self.mock_services = Mock(spec=ConversionServices)
        self.mock_services.unit_converter = Mock()
        self.mock_services.unit_converter.convert_to_emu = Mock(return_value=914400)

        # Create converters
        self.custgeom_generator = CustGeomGenerator(self.mock_services)
        self.clippath_analyzer = ClipPathAnalyzer(self.mock_services)
        self.masking_converter = MaskingConverter(self.mock_services)

        # Create mock context
        self.context = Mock(spec=ConversionContext)
        self.context.get_next_shape_id = Mock(return_value="12345")
        self.context.viewbox_width = 300
        self.context.viewbox_height = 200

        # Test data directory
        self.test_data_dir = Path(__file__).parent.parent.parent / "data" / "w3c_clippath_tests"

    def load_svg_file(self, filename: str) -> ET.Element:
        """Load SVG file from test data directory."""
        svg_path = self.test_data_dir / filename
        return ET.parse(str(svg_path)).getroot()

    def extract_clippath_definitions(self, svg_root: ET.Element) -> Dict[str, ClipPathDefinition]:
        """Extract clipPath definitions from SVG."""
        clippath_defs = {}

        for clippath in svg_root.findall('.//{http://www.w3.org/2000/svg}clipPath'):
            clip_id = clippath.get('id')
            if clip_id:
                # Extract shapes and path data
                shapes = list(clippath)
                path_data = None

                # If there's a single path element, extract its data
                paths = clippath.findall('.//{http://www.w3.org/2000/svg}path')
                if len(paths) == 1:
                    path_data = paths[0].get('d')

                clip_def = ClipPathDefinition(
                    id=clip_id,
                    units=clippath.get('clipPathUnits', 'userSpaceOnUse'),
                    clip_rule=clippath.get('clip-rule', 'nonzero'),
                    path_data=path_data,
                    shapes=shapes if not path_data else None,
                    clipping_type=ClippingType.PATH_BASED if path_data else ClippingType.SHAPE_BASED
                )
                clippath_defs[clip_id] = clip_def

        return clippath_defs

    def test_basic_rect_clip_conversion(self):
        """Test basic rectangle clipPath conversion."""
        svg_root = self.load_svg_file("basic_rect_clip.svg")
        clippath_defs = self.extract_clippath_definitions(svg_root)

        assert 'rectClip' in clippath_defs
        clip_def = clippath_defs['rectClip']

        # Test custGeom capability
        can_generate = self.custgeom_generator.can_generate_custgeom(clip_def)
        assert can_generate, "Should be able to generate custGeom for basic rectangle"

        # Test custGeom generation
        custgeom_xml = self.custgeom_generator.generate_custgeom_xml(clip_def, self.context)

        assert '<a:custGeom>' in custgeom_xml
        assert '<a:rect l="0" t="0"' in custgeom_xml
        assert '<a:pathLst>' in custgeom_xml
        assert '<a:moveTo>' in custgeom_xml
        assert '<a:close/>' in custgeom_xml

    def test_circle_clip_conversion(self):
        """Test circle clipPath conversion."""
        svg_root = self.load_svg_file("circle_clip.svg")
        clippath_defs = self.extract_clippath_definitions(svg_root)

        assert 'circleClip' in clippath_defs
        clip_def = clippath_defs['circleClip']

        can_generate = self.custgeom_generator.can_generate_custgeom(clip_def)
        assert can_generate, "Should be able to generate custGeom for circle"

        custgeom_xml = self.custgeom_generator.generate_custgeom_xml(clip_def, self.context)

        assert '<a:custGeom>' in custgeom_xml
        assert '<a:pathLst>' in custgeom_xml
        # Circle is currently approximated as rectangle
        assert '<a:moveTo>' in custgeom_xml

    def test_path_clip_conversion(self):
        """Test path-based clipPath conversion."""
        svg_root = self.load_svg_file("path_clip.svg")
        clippath_defs = self.extract_clippath_definitions(svg_root)

        assert 'starClip' in clippath_defs
        clip_def = clippath_defs['starClip']

        can_generate = self.custgeom_generator.can_generate_custgeom(clip_def)
        assert can_generate, "Should be able to generate custGeom for star path"

        custgeom_xml = self.custgeom_generator.generate_custgeom_xml(clip_def, self.context)

        assert '<a:custGeom>' in custgeom_xml
        assert '<a:pathLst>' in custgeom_xml
        assert '<a:moveTo>' in custgeom_xml
        assert '<a:lnTo>' in custgeom_xml
        assert '<a:close/>' in custgeom_xml

    def test_objectboundingbox_clip_conversion(self):
        """Test objectBoundingBox clipPath conversion."""
        svg_root = self.load_svg_file("objectboundingbox_clip.svg")
        clippath_defs = self.extract_clippath_definitions(svg_root)

        assert 'bboxClip' in clippath_defs
        clip_def = clippath_defs['bboxClip']

        # Verify units are correctly parsed
        assert clip_def.units == 'objectBoundingBox'

        can_generate = self.custgeom_generator.can_generate_custgeom(clip_def)
        assert can_generate, "Should be able to generate custGeom for objectBoundingBox"

        custgeom_xml = self.custgeom_generator.generate_custgeom_xml(clip_def, self.context)

        assert '<a:custGeom>' in custgeom_xml
        # objectBoundingBox should use full coordinate range
        assert 'w="21600" h="21600"' in custgeom_xml

    def test_polygon_clip_conversion(self):
        """Test polygon clipPath conversion."""
        svg_root = self.load_svg_file("polygon_clip.svg")
        clippath_defs = self.extract_clippath_definitions(svg_root)

        assert 'polygonClip' in clippath_defs
        clip_def = clippath_defs['polygonClip']

        can_generate = self.custgeom_generator.can_generate_custgeom(clip_def)
        assert can_generate, "Should be able to generate custGeom for polygon"

        custgeom_xml = self.custgeom_generator.generate_custgeom_xml(clip_def, self.context)

        assert '<a:custGeom>' in custgeom_xml
        assert '<a:pathLst>' in custgeom_xml
        assert '<a:moveTo>' in custgeom_xml
        assert '<a:lnTo>' in custgeom_xml
        assert '<a:close/>' in custgeom_xml

    def test_nested_clip_analysis(self):
        """Test nested clipPath analysis."""
        svg_root = self.load_svg_file("nested_clip.svg")
        clippath_defs = self.extract_clippath_definitions(svg_root)

        assert 'innerClip' in clippath_defs
        clip_def = clippath_defs['innerClip']

        # Nested clips should be detected by analyzer
        analysis = self.clippath_analyzer.analyze_clippath(
            svg_root.find('.//{http://www.w3.org/2000/svg}rect'),
            clippath_defs,
            'url(#innerClip)'
        )

        # Should be classified as NESTED due to clip-path reference in clipPath content
        from core.converters.clippath_types import ClipPathComplexity
        assert analysis.complexity in [ClipPathComplexity.NESTED, ClipPathComplexity.COMPLEX]

    def test_performance_benchmarks(self):
        """Test performance of custGeom generation."""
        svg_files = [
            "basic_rect_clip.svg",
            "circle_clip.svg",
            "path_clip.svg",
            "objectboundingbox_clip.svg",
            "polygon_clip.svg"
        ]

        performance_results = {}

        for svg_file in svg_files:
            svg_root = self.load_svg_file(svg_file)
            clippath_defs = self.extract_clippath_definitions(svg_root)

            # Measure custGeom generation time
            start_time = time.perf_counter()

            for clip_id, clip_def in clippath_defs.items():
                if self.custgeom_generator.can_generate_custgeom(clip_def):
                    custgeom_xml = self.custgeom_generator.generate_custgeom_xml(clip_def, self.context)

            end_time = time.perf_counter()
            generation_time = (end_time - start_time) * 1000  # Convert to milliseconds

            performance_results[svg_file] = {
                'generation_time_ms': generation_time,
                'clippath_count': len(clippath_defs),
                'output_size_chars': len(custgeom_xml) if clippath_defs else 0
            }

        # Verify performance is reasonable (less than 10ms per clipPath)
        for svg_file, results in performance_results.items():
            if results['clippath_count'] > 0:
                time_per_clippath = results['generation_time_ms'] / results['clippath_count']
                assert time_per_clippath < 10, f"CustGeom generation too slow for {svg_file}: {time_per_clippath:.2f}ms"

        # Log performance results for analysis
        print("\nCustGeom Generation Performance Results:")
        print(json.dumps(performance_results, indent=2))

    def test_end_to_end_masking_converter_integration(self):
        """Test end-to-end integration with MaskingConverter."""
        svg_root = self.load_svg_file("basic_rect_clip.svg")
        clippath_defs = self.extract_clippath_definitions(svg_root)

        # Set up masking converter with clipPath definitions
        self.masking_converter.clippath_definitions = clippath_defs

        # Find element with clip-path attribute
        clipped_element = svg_root.find('.//{http://www.w3.org/2000/svg}rect[@clip-path]')
        assert clipped_element is not None

        clip_ref = clipped_element.get('clip-path')
        assert clip_ref == 'url(#rectClip)'

        # Test full conversion pipeline
        result = self.masking_converter._apply_clipping(clipped_element, clip_ref, self.context)

        # Should generate custGeom output
        assert result is not None
        assert '<a:custGeom>' in result
        assert 'ClippedShape' in result or 'ClippingShape' in result

    def test_custgeom_xml_validation(self):
        """Test that generated custGeom XML is well-formed."""
        svg_root = self.load_svg_file("path_clip.svg")
        clippath_defs = self.extract_clippath_definitions(svg_root)

        clip_def = clippath_defs['starClip']
        custgeom_xml = self.custgeom_generator.generate_custgeom_xml(clip_def, self.context)

        # Test XML parsing
        try:
            # Wrap in root element for parsing
            xml_content = f'<root xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">{custgeom_xml}</root>'
            parsed = ET.fromstring(xml_content)
            assert parsed is not None
        except ET.XMLSyntaxError as e:
            pytest.fail(f"Generated custGeom XML is not well-formed: {e}")

        # Test required elements are present
        assert custgeom_xml.count('<a:custGeom>') == 1
        assert custgeom_xml.count('</a:custGeom>') == 1
        assert custgeom_xml.count('<a:pathLst>') == 1
        assert custgeom_xml.count('</a:pathLst>') == 1

    def test_coordinate_accuracy_validation(self):
        """Test coordinate accuracy in custGeom generation."""
        svg_root = self.load_svg_file("objectboundingbox_clip.svg")
        clippath_defs = self.extract_clippath_definitions(svg_root)

        clip_def = clippath_defs['bboxClip']
        custgeom_xml = self.custgeom_generator.generate_custgeom_xml(clip_def, self.context)

        # objectBoundingBox with rect x="0.2" y="0.2" width="0.6" height="0.6"
        # Should be converted to DrawingML coordinates

        # Check for appropriate coordinate scaling
        assert '4320' in custgeom_xml or '4321' in custgeom_xml  # 0.2 * 21600 = 4320 (start)
        assert '17280' in custgeom_xml or '17281' in custgeom_xml  # 0.8 * 21600 = 17280 (end = start + width)

    def test_all_test_files_load_successfully(self):
        """Test that all test SVG files can be loaded and parsed."""
        test_files = list(self.test_data_dir.glob("*.svg"))
        assert len(test_files) >= 5, "Should have at least 5 test SVG files"

        for svg_file in test_files:
            try:
                svg_root = ET.parse(str(svg_file)).getroot()
                assert svg_root is not None

                # Should have clipPath definitions
                clippath_elements = svg_root.findall('.//{http://www.w3.org/2000/svg}clipPath')
                assert len(clippath_elements) >= 1, f"File {svg_file.name} should have clipPath definitions"

            except Exception as e:
                pytest.fail(f"Failed to load test file {svg_file.name}: {e}")

    def test_edge_case_documentation(self):
        """Test and document edge cases and limitations."""
        edge_cases = []

        # Test empty clipPath
        empty_clip = ClipPathDefinition(
            id='empty',
            units='userSpaceOnUse',
            clip_rule='nonzero',
            clipping_type=ClippingType.PATH_BASED
        )

        can_generate = self.custgeom_generator.can_generate_custgeom(empty_clip)
        if not can_generate:
            edge_cases.append("Empty clipPath cannot generate custGeom")

        # Test very complex path
        complex_clip = ClipPathDefinition(
            id='complex',
            units='userSpaceOnUse',
            clip_rule='nonzero',
            path_data='M 0 0 C 100 100 200 200 300 300 Q 400 400 500 500 A 50 50 0 1 1 100 100 Z',
            clipping_type=ClippingType.PATH_BASED
        )

        can_generate = self.custgeom_generator.can_generate_custgeom(complex_clip)
        if can_generate:
            try:
                custgeom_xml = self.custgeom_generator.generate_custgeom_xml(complex_clip, self.context)
                edge_cases.append("Complex paths with arcs are supported (converted to available commands)")
            except Exception as e:
                edge_cases.append(f"Complex paths fail: {e}")

        # Document findings
        print("\nEdge Cases and Limitations:")
        for case in edge_cases:
            print(f"- {case}")

        # Should have documented at least some edge cases
        assert len(edge_cases) > 0, "Should document edge cases"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
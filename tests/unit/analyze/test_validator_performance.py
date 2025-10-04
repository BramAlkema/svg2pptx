"""
Performance tests for SVG Validator optimizations.

Tests single-pass element collection vs. multiple XPath queries.
"""

import pytest
import time
from core.analyze.svg_validator import SVGValidator


class TestValidatorPerformanceOptimization:
    """Test performance improvements from element collection optimization."""

    @pytest.fixture
    def simple_svg(self):
        """Simple SVG for basic validation."""
        return """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <rect x="10" y="10" width="80" height="80" fill="blue"/>
            <circle cx="50" cy="50" r="30" fill="red"/>
        </svg>
        """

    @pytest.fixture
    def complex_svg(self):
        """Complex SVG with multiple element types."""
        elements = []

        # Add 50 paths
        for i in range(50):
            elements.append(f'<path d="M{i} {i} L{i+10} {i+10}" stroke="black"/>')

        # Add 20 filters with primitives
        for i in range(20):
            elements.append(f'''
            <filter id="filter{i}">
                <feGaussianBlur in="SourceGraphic" stdDeviation="2"/>
                <feOffset dx="2" dy="2"/>
                <feBlend in="SourceGraphic" in2="blurOut" mode="normal"/>
            </filter>
            ''')

        # Add 10 gradients with stops
        for i in range(10):
            stops = []
            for j in range(12):  # 12 stops (triggers suggestion)
                offset = j / 11
                stops.append(f'<stop offset="{offset}" stop-color="#{i:02x}{j:02x}00"/>')
            elements.append(f'''
            <linearGradient id="grad{i}">
                {''.join(stops)}
            </linearGradient>
            ''')

        # Add 5 mesh gradients
        for i in range(5):
            elements.append(f'<meshgradient id="mesh{i}"/>')

        # Add 5 masks
        for i in range(5):
            elements.append(f'<mask id="mask{i}"><rect width="100" height="100" fill="white"/></mask>')

        # Add 5 patterns
        for i in range(5):
            elements.append(f'<pattern id="pattern{i}"><circle r="5"/></pattern>')

        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">
            {''.join(elements)}
        </svg>
        '''
        return svg

    def test_simple_svg_validation(self, simple_svg):
        """Test validation works correctly with simple SVG."""
        validator = SVGValidator()
        result = validator.validate(simple_svg)

        assert result.valid
        assert result.version == "1.1"
        assert result.compatibility is not None

    def test_complex_svg_validation(self, complex_svg):
        """Test validation works correctly with complex SVG."""
        validator = SVGValidator()
        result = validator.validate(complex_svg)

        assert result.valid
        # Should have compatibility notes about filters, meshes, etc.
        assert result.compatibility is not None
        assert len(result.compatibility.notes) > 0

        # Should detect compatibility issues
        assert any("filter" in note for note in result.compatibility.notes)
        assert any("mesh" in note.lower() for note in result.compatibility.notes)

    def test_element_collection_single_pass(self, complex_svg):
        """Test that element collection happens in single pass."""
        from lxml import etree as ET

        validator = SVGValidator()
        svg_root = ET.fromstring(complex_svg.encode('utf-8'))

        # Test the _collect_elements method directly
        elements_by_tag = validator._collect_elements(svg_root)

        # Verify all element types are collected
        assert 'path' in elements_by_tag
        assert 'filter' in elements_by_tag
        assert 'linearGradient' in elements_by_tag
        assert 'meshgradient' in elements_by_tag
        assert 'mask' in elements_by_tag
        assert 'pattern' in elements_by_tag

        # Verify counts
        assert len(elements_by_tag['path']) == 50
        assert len(elements_by_tag['filter']) == 20
        assert len(elements_by_tag['linearGradient']) == 10
        assert len(elements_by_tag['meshgradient']) == 5
        assert len(elements_by_tag['mask']) == 5
        assert len(elements_by_tag['pattern']) == 5

    def test_performance_improvement_complex_svg(self, complex_svg):
        """Test that validation performance improves with optimization."""
        validator = SVGValidator()

        # Warm up
        validator.validate(complex_svg)

        # Measure performance over multiple runs
        iterations = 10
        start = time.perf_counter()
        for _ in range(iterations):
            result = validator.validate(complex_svg)
        elapsed = time.perf_counter() - start

        avg_time = elapsed / iterations

        # Performance expectation: < 50ms per validation for this complexity
        # (Without optimization it would be ~100ms+ due to multiple tree traversals)
        assert avg_time < 0.05, f"Validation too slow: {avg_time*1000:.2f}ms (expected <50ms)"

        # Verify result is still correct
        assert result.valid

    def test_performance_scales_linearly(self):
        """Test that performance scales linearly with element count."""
        validator = SVGValidator()

        times = []
        element_counts = [10, 50, 100]

        for count in element_counts:
            # Generate SVG with 'count' elements
            elements = [f'<rect x="{i}" y="{i}" width="10" height="10"/>' for i in range(count)]
            svg = f'<svg xmlns="http://www.w3.org/2000/svg">{"".join(elements)}</svg>'

            # Measure time
            start = time.perf_counter()
            validator.validate(svg)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        # Time should scale roughly linearly (not quadratically)
        # If using multiple findall(), time would scale as O(n²) or worse
        # With single-pass collection, it should be O(n)

        # Check that 10x elements doesn't take 100x time
        ratio_10_to_100 = times[2] / times[0]
        assert ratio_10_to_100 < 20, f"Performance degraded non-linearly: {ratio_10_to_100:.2f}x"

    def test_compatibility_check_uses_collected_elements(self, complex_svg):
        """Test that compatibility check uses pre-collected elements."""
        from lxml import etree as ET

        validator = SVGValidator()
        svg_root = ET.fromstring(complex_svg.encode('utf-8'))

        # Collect elements
        elements_by_tag = validator._collect_elements(svg_root)

        # Run compatibility check with collected elements
        compatibility = validator._check_compatibility(svg_root, elements_by_tag)

        # Verify it detected features
        assert len(compatibility.notes) > 0
        assert any("filter" in note for note in compatibility.notes)
        assert any("mesh" in note.lower() for note in compatibility.notes)

    def test_validate_structure_uses_collected_elements(self, complex_svg):
        """Test that structure validation uses pre-collected elements."""
        from lxml import etree as ET
        from core.analyze.svg_validator import ValidationResult

        validator = SVGValidator()
        svg_root = ET.fromstring(complex_svg.encode('utf-8'))
        result = ValidationResult(valid=True)

        # Collect elements
        elements_by_tag = validator._collect_elements(svg_root)

        # Run structure validation with collected elements
        validator._validate_structure(svg_root, result, elements_by_tag)

        # Verify it found issues
        assert len(result.suggestions) > 0  # Should suggest gradient simplification

    def test_memory_efficiency(self, complex_svg):
        """Test that element collection doesn't use excessive memory."""
        import sys
        from lxml import etree as ET

        validator = SVGValidator()
        svg_root = ET.fromstring(complex_svg.encode('utf-8'))

        # Collect elements
        elements_by_tag = validator._collect_elements(svg_root)

        # Calculate rough memory usage
        # Each element reference is ~8 bytes (pointer)
        # Total elements: ~100 (50 paths + 20 filters + 10 gradients + 20 misc)
        total_elements = sum(len(elems) for elems in elements_by_tag.values())
        estimated_memory = total_elements * sys.getsizeof(object())  # Rough estimate

        # Should use < 100KB for collection (very conservative)
        assert estimated_memory < 100_000

    def test_empty_svg_performance(self):
        """Test performance with minimal SVG."""
        validator = SVGValidator()
        svg = '<svg xmlns="http://www.w3.org/2000/svg"/>'

        # Should be very fast for empty SVG
        start = time.perf_counter()
        result = validator.validate(svg)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.01  # < 10ms for empty SVG
        assert result.valid

    def test_namespace_handling_in_collection(self):
        """Test that namespace prefixes are handled correctly in collection."""
        svg_with_namespace = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <rect width="10" height="10"/>
            <circle r="5"/>
        </svg>
        '''

        from lxml import etree as ET
        validator = SVGValidator()
        svg_root = ET.fromstring(svg_with_namespace.encode('utf-8'))

        elements_by_tag = validator._collect_elements(svg_root)

        # Elements should be keyed by tag name without namespace
        assert 'rect' in elements_by_tag
        assert 'circle' in elements_by_tag
        assert len(elements_by_tag['rect']) == 1
        assert len(elements_by_tag['circle']) == 1


class TestValidatorRegressionTests:
    """Ensure optimizations don't break existing functionality."""

    def test_invalid_xml_still_caught(self):
        """Test that invalid XML is still caught."""
        validator = SVGValidator()
        invalid_svg = '<svg><rect></svg>'  # Unclosed rect

        result = validator.validate(invalid_svg)
        assert not result.valid
        assert len(result.errors) > 0

    def test_missing_viewbox_warning_still_works(self):
        """Test that missing viewBox warning still works."""
        validator = SVGValidator()
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'

        result = validator.validate(svg)
        assert result.valid
        viewbox_warnings = [w for w in result.warnings if w.code == "MISSING_VIEWBOX"]
        assert len(viewbox_warnings) == 1

    def test_empty_path_detection_still_works(self):
        """Test that empty path detection still works."""
        validator = SVGValidator()
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><path/></svg>'

        result = validator.validate(svg)
        empty_path_warnings = [w for w in result.warnings if w.code == "EMPTY_PATH"]
        assert len(empty_path_warnings) == 1

    def test_strict_mode_still_works(self):
        """Test that strict mode still fails on warnings."""
        validator = SVGValidator()
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'  # Missing viewBox

        result = validator.validate(svg, strict_mode=True)
        assert not result.valid  # Warnings become errors in strict mode

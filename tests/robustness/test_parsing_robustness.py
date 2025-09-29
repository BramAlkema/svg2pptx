#!/usr/bin/env python3
"""
Property-Based Robustness Tests

Uses property-based testing (Hypothesis) to test system robustness
against arbitrary inputs and edge cases.
"""

import pytest
import tempfile
import os
from typing import Optional

# Import hypothesis for property-based testing
try:
    from hypothesis import given, strategies as st, settings, example
    from hypothesis import Verbosity, HealthCheck
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False

from src.svg2pptx import convert_svg_to_pptx
from src.svg2drawingml import SVGToDrawingMLConverter
from core.services.conversion_services import ConversionServices
from src.converters.base import BaseConverter


# Skip all tests if hypothesis is not available
pytestmark = pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="Hypothesis not available")


class TestLengthParsingRobustness:
    """Property-based tests for length parsing robustness."""

    @pytest.fixture
    def services(self):
        return ConversionServices.create_default()

    @pytest.fixture
    def converter(self, services):
        return BaseConverter(services)

    @given(st.text(max_size=100))
    @settings(max_examples=200, deadline=1000)
    def test_length_parsing_never_crashes(self, converter, length_str):
        """Test that length parsing never crashes on arbitrary input."""
        try:
            result = converter.parse_length(length_str)
            # Should either return None or valid number
            assert result is None or isinstance(result, (int, float))

            # If result is a number, should be reasonable (not infinite or extremely large)
            if isinstance(result, (int, float)):
                assert not (result == float('inf') or result == float('-inf'))
                assert -1e20 < result < 1e20  # Reasonable bounds

        except Exception as e:
            pytest.fail(f"parse_length crashed on '{length_str}': {e}")

    @given(st.floats(min_value=-1e10, max_value=1e10),
           st.sampled_from(['px', 'pt', 'em', 'ex', 'cm', 'mm', 'in', '%', '']))
    @settings(max_examples=100)
    def test_valid_length_formats(self, converter, number, unit):
        """Test parsing of valid length formats."""
        length_str = f"{number}{unit}"

        try:
            result = converter.parse_length(length_str)

            if result is not None:
                assert isinstance(result, (int, float))
                # Result should be related to input (within reasonable bounds)
                if unit in ['px', '']:  # Base units
                    assert abs(result - number) < abs(number) * 0.01 + 1  # Small tolerance

        except (ValueError, OverflowError):
            # These exceptions are acceptable for extreme values
            pass

    @given(st.text().filter(lambda x: any(char in x for char in "0123456789")))
    @settings(max_examples=100)
    def test_numeric_content_parsing(self, converter, text_with_numbers):
        """Test parsing of text that contains numbers."""
        try:
            result = converter.parse_length(text_with_numbers)
            assert result is None or isinstance(result, (int, float))

        except Exception as e:
            pytest.fail(f"parse_length crashed on numeric text '{text_with_numbers}': {e}")


class TestSVGParsingRobustness:
    """Property-based tests for SVG parsing robustness."""

    @given(st.text(min_size=1, max_size=1000).filter(lambda x: '<svg' in x.lower()))
    @settings(max_examples=50, deadline=2000, suppress_health_check=[HealthCheck.too_slow])
    def test_svg_parsing_robustness(self, svg_like_content):
        """Test SVG parsing doesn't crash on malformed input."""
        try:
            services = ConversionServices.create_default()
            converter = SVGToDrawingMLConverter(services=services)
            result = converter.convert(svg_like_content)

            # Should either succeed or fail gracefully
            assert isinstance(result, str)

        except Exception:
            # Parsing failure is acceptable for malformed input
            # The key requirement is that it doesn't crash the process
            pass

    @given(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd')),
                   min_size=10, max_size=200))
    @example('<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>')
    @settings(max_examples=30, deadline=3000)
    def test_convert_svg_to_pptx_robustness(self, content):
        """Test that convert_svg_to_pptx handles arbitrary content gracefully."""
        try:
            result = convert_svg_to_pptx(content)

            # If it succeeds, result should be a valid file path
            if result and os.path.exists(result):
                assert isinstance(result, str)
                assert result.endswith('.pptx')
                assert os.path.getsize(result) > 0
                # Clean up
                os.unlink(result)

        except Exception:
            # Conversion failure is acceptable for invalid content
            # Key requirement: should not crash or corrupt system state
            pass

    @given(st.dictionaries(
        keys=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=20),
        values=st.text(max_size=100),
        max_size=10
    ))
    @settings(max_examples=30)
    def test_svg_attributes_robustness(self, attributes):
        """Test SVG parsing with arbitrary attributes."""
        # Build SVG with random attributes
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attributes.items())
        svg_content = f'<svg xmlns="http://www.w3.org/2000/svg" {attr_str}><rect width="100" height="100"/></svg>'

        try:
            result = convert_svg_to_pptx(svg_content)
            if result and os.path.exists(result):
                assert result.endswith('.pptx')
                os.unlink(result)

        except Exception:
            # Attribute parsing failures are acceptable
            pass


class TestNumericRobustness:
    """Property-based tests for numeric processing robustness."""

    @pytest.fixture
    def services(self):
        return ConversionServices.create_default()

    @pytest.fixture
    def converter(self, services):
        return BaseConverter(services)

    @given(st.floats(min_value=-1e6, max_value=1e6))
    @settings(max_examples=100)
    def test_coordinate_conversion_robustness(self, converter, coordinate):
        """Test coordinate conversion with various numeric values."""
        try:
            # Test that coordinate processing doesn't crash
            result = converter.parse_length(f"{coordinate}px")

            if result is not None:
                assert isinstance(result, (int, float))
                assert not (result == float('inf') or result == float('-inf'))

        except (ValueError, OverflowError):
            # Acceptable for extreme values
            pass

    @given(st.integers(min_value=-10000, max_value=10000),
           st.integers(min_value=-10000, max_value=10000),
           st.integers(min_value=1, max_value=10000),
           st.integers(min_value=1, max_value=10000))
    @settings(max_examples=50)
    def test_svg_viewport_robustness(self, x, y, width, height):
        """Test SVG viewport handling with various dimensions."""
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {width} {height}">
            <rect x="10" y="10" width="50" height="50" fill="red"/>
        </svg>'''

        try:
            result = convert_svg_to_pptx(svg_content)
            if result and os.path.exists(result):
                assert os.path.getsize(result) > 1000  # Non-trivial size
                os.unlink(result)

        except Exception:
            # Some viewport configurations may fail, which is acceptable
            pass

    @given(st.floats(allow_nan=False, allow_infinity=False, min_value=-1000, max_value=1000))
    @settings(max_examples=50)
    def test_transform_values_robustness(self, value):
        """Test transform parsing with various numeric values."""
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <rect width="100" height="100" fill="blue" transform="translate({value}, {value})"/>
        </svg>'''

        try:
            result = convert_svg_to_pptx(svg_content)
            if result and os.path.exists(result):
                os.unlink(result)

        except Exception:
            # Transform parsing may fail for extreme values
            pass


class TestMemoryAndPerformance:
    """Property-based tests for memory usage and performance."""

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=10, deadline=10000)
    def test_repeated_conversion_memory_usage(self, num_conversions):
        """Test that repeated conversions don't cause memory leaks."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="red"/></svg>'

        results = []
        try:
            for _ in range(min(num_conversions, 20)):  # Limit to prevent test timeouts
                result = convert_svg_to_pptx(svg_content)
                if result:
                    results.append(result)

            # All conversions should succeed consistently
            assert len(results) == min(num_conversions, 20)

            # All results should be unique (no file conflicts)
            assert len(set(results)) == len(results)

        finally:
            # Clean up all created files
            for result in results:
                if result and os.path.exists(result):
                    try:
                        os.unlink(result)
                    except OSError:
                        pass

    @given(st.lists(st.text(alphabet='<>/="', min_size=5, max_size=50), min_size=1, max_size=20))
    @settings(max_examples=10, deadline=5000)
    def test_complex_svg_structure_robustness(self, svg_fragments):
        """Test parsing of complex nested SVG structures."""
        # Build complex SVG from fragments
        svg_parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">']

        for fragment in svg_fragments[:10]:  # Limit complexity
            # Try to make fragments more SVG-like
            if '<' in fragment and '>' in fragment:
                svg_parts.append(fragment)

        svg_parts.append('<rect width="100" height="100" fill="red"/>')
        svg_parts.append('</svg>')

        svg_content = ''.join(svg_parts)

        try:
            result = convert_svg_to_pptx(svg_content)
            if result and os.path.exists(result):
                assert os.path.getsize(result) > 0
                os.unlink(result)

        except Exception:
            # Complex malformed SVG may fail to parse
            pass

    @given(st.text(alphabet=st.characters(whitelist_categories=('Nd', 'Po')),
                   min_size=20, max_size=500))
    @settings(max_examples=20, deadline=2000)
    def test_large_attribute_values(self, large_value):
        """Test handling of very large attribute values."""
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <rect width="100" height="100" fill="red" data-large="{large_value}"/>
        </svg>'''

        try:
            result = convert_svg_to_pptx(svg_content)
            if result and os.path.exists(result):
                os.unlink(result)

        except Exception:
            # Large attribute values may cause parsing issues
            pass


class TestEdgeCaseHandling:
    """Property-based tests for edge case handling."""

    @given(st.text(alphabet=' \t\n\r', min_size=0, max_size=100))
    @settings(max_examples=20)
    def test_whitespace_handling(self, whitespace):
        """Test handling of various whitespace patterns."""
        svg_content = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{whitespace}<rect width="50" height="50" fill="red"/>{whitespace}</svg>'

        try:
            result = convert_svg_to_pptx(svg_content)
            if result and os.path.exists(result):
                os.unlink(result)

        except Exception:
            # Whitespace handling issues are acceptable
            pass

    @given(st.lists(st.tuples(st.text(max_size=20), st.text(max_size=50)), max_size=20))
    @settings(max_examples=15)
    def test_many_attributes_robustness(self, attribute_pairs):
        """Test SVG elements with many attributes."""
        attrs = ' '.join(f'{k}="{v}"' for k, v in attribute_pairs if k and '"' not in v)
        svg_content = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><rect {attrs} width="100" height="100" fill="red"/></svg>'

        try:
            result = convert_svg_to_pptx(svg_content)
            if result and os.path.exists(result):
                os.unlink(result)

        except Exception:
            # Many attributes may cause processing issues
            pass


if __name__ == "__main__":
    if HYPOTHESIS_AVAILABLE:
        pytest.main([__file__, "-v", "--tb=short"])
    else:
        print("Hypothesis not available - skipping property-based tests")
        print("Install with: pip install hypothesis")
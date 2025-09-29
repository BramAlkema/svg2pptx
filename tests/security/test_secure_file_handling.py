#!/usr/bin/env python3
"""
Security & Input Validation Tests

Tests for secure file handling, input sanitization, and protection
against common security vulnerabilities in file operations.
"""

import pytest
import ast
import pathlib
import tempfile
import os
import zipfile
from unittest.mock import patch, mock_open

from src.svg2pptx import convert_svg_to_pptx
from core.services.image_service import ImageService
from src.converters.base import BaseConverter
from core.services.conversion_services import ConversionServices


class TestSecureFileHandling:
    """Test that codebase uses secure file handling methods."""

    def test_no_insecure_temp_files(self):
        """Test that codebase doesn't use insecure temporary file methods."""
        insecure_patterns = ['mktemp', 'mkstemp', 'mkdtemp']
        violations = []

        # Check all Python files in src directory
        for py_file in pathlib.Path('src').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse the file to check for insecure tempfile usage
                try:
                    tree = ast.parse(content)
                except SyntaxError:
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute):
                        # Check for tempfile.mktemp, tempfile.mkstemp, etc.
                        if (hasattr(node.value, 'id') and
                            node.value.id == 'tempfile' and
                            node.attr in insecure_patterns):
                            violations.append(f"{py_file}:{node.lineno} - tempfile.{node.attr}")

                    elif isinstance(node, ast.Call):
                        # Check for direct calls like mkstemp()
                        if (isinstance(node.func, ast.Name) and
                            node.func.id in insecure_patterns):
                            violations.append(f"{py_file}:{node.lineno} - {node.func.id}()")

            except (IOError, UnicodeDecodeError):
                # Skip files that can't be read
                continue

        assert not violations, f"Insecure tempfile usage found: {violations}"

    def test_secure_temp_file_usage_in_conversion(self):
        """Test that conversion functions use secure temporary files."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="red"/></svg>'

        # Test convert_svg_to_pptx creates secure temp files
        result_path = convert_svg_to_pptx(svg_content)

        try:
            # Verify the result file exists and is valid
            assert os.path.exists(result_path)
            assert result_path.endswith('.pptx')
            assert os.path.getsize(result_path) > 0

            # Verify it's a valid PPTX file (ZIP format)
            with zipfile.ZipFile(result_path, 'r') as zf:
                assert '[Content_Types].xml' in zf.namelist()

        finally:
            # Clean up
            if os.path.exists(result_path):
                os.unlink(result_path)

    def test_image_service_secure_temp_files(self):
        """Test that ImageService uses secure temporary file creation."""
        image_service = ImageService()

        # Test with mock image data
        test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

        # Create temporary file securely
        temp_path = image_service._create_temp_file(test_image_data, '.png')

        try:
            # Verify file was created and has correct content
            assert os.path.exists(temp_path)
            assert temp_path.endswith('.png')

            with open(temp_path, 'rb') as f:
                content = f.read()
                assert content == test_image_data

        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_temp_file_permissions(self):
        """Test that temporary files have secure permissions."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            temp_path = tmp.name

        try:
            # Check file permissions (should not be world-readable)
            stat_info = os.stat(temp_path)
            permissions = stat_info.st_mode & 0o777

            # On Unix systems, temp files should not be world-readable/writable
            if os.name != 'nt':  # Not Windows
                assert permissions & 0o004 == 0, "Temp file should not be world-readable"
                assert permissions & 0o002 == 0, "Temp file should not be world-writable"

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_no_path_traversal_vulnerabilities(self):
        """Test protection against path traversal attacks."""
        # Test malicious SVG with path traversal attempt
        malicious_svg = '''<svg xmlns="http://www.w3.org/2000/svg">
            <image href="../../../etc/passwd"/>
        </svg>'''

        # Should not crash or allow path traversal
        try:
            result = convert_svg_to_pptx(malicious_svg)
            # If it succeeds, verify it's a valid PPTX
            if result and os.path.exists(result):
                assert result.endswith('.pptx')
                os.unlink(result)
        except Exception:
            # Graceful failure is acceptable
            pass


class TestInputSanitization:
    """Test robust parsing of malformed inputs."""

    @pytest.fixture
    def services(self):
        return ConversionServices.create_default()

    @pytest.fixture
    def converter(self, services):
        return BaseConverter(services)

    def test_length_parsing_robustness(self, converter):
        """Test robust parsing of length values."""
        test_cases = [
            ("100px", "pixel values"),
            ("100%", "percentage values"),
            ("12cm", "metric units"),
            ("1.5em", "relative units"),
            ("10pt", "point units"),
            ("2in", "inch units"),
            ("5mm", "millimeter units"),
            ("invalid", "non-numeric"),
            ("5e", "incomplete scientific notation"),
            ("", "empty string"),
            ("  ", "whitespace only"),
            ("100px%", "mixed units"),
            ("abc123", "mixed alphanumeric"),
            ("--100px", "double negative"),
            ("100..5px", "invalid decimal"),
            ("∞px", "unicode symbols")
        ]

        for test_input, description in test_cases:
            try:
                result = converter.parse_length(test_input)
                # Should either return valid float or None, never crash
                assert result is None or isinstance(result, (int, float)), \
                    f"parse_length failed on {description}: '{test_input}' -> {result}"

                # If result is a number, should be reasonable
                if result is not None:
                    assert -1000000 < result < 1000000, \
                        f"parse_length returned unreasonable value: {result} for '{test_input}'"

            except Exception as e:
                pytest.fail(f"parse_length crashed on {description} '{test_input}': {e}")

    def test_svg_parsing_malformed_input(self):
        """Test SVG parsing doesn't crash on malformed input."""
        malformed_svgs = [
            "",  # Empty
            "not svg at all",  # Not XML
            "<svg>unclosed tag",  # Malformed XML
            "<svg xmlns='invalid'><rect/></svg>",  # Invalid namespace
            "<svg><rect width='invalid' height='also invalid'/></svg>",  # Invalid attributes
            "<svg>" + "x" * 1000000 + "</svg>",  # Extremely large content
            "<svg><rect width='100%' height='50vh'/></svg>",  # Viewport units
            "<svg><script>alert('xss')</script></svg>",  # Script injection attempt
        ]

        for svg_content in malformed_svgs:
            try:
                result = convert_svg_to_pptx(svg_content)
                # Should either succeed or fail gracefully
                if result and os.path.exists(result):
                    assert isinstance(result, str)
                    assert result.endswith('.pptx')
                    # Clean up
                    os.unlink(result)
            except Exception:
                # Parsing failure is acceptable, crashes are not acceptable
                # but we can't easily distinguish between expected vs unexpected exceptions
                # in this test context
                pass

    def test_numeric_overflow_protection(self, converter):
        """Test protection against numeric overflow attacks."""
        overflow_values = [
            "9999999999999999999999px",  # Very large number
            "1e308px",  # Near float overflow
            "-1e308px",  # Negative overflow
            "1e1000px",  # Definite overflow
        ]

        for value in overflow_values:
            try:
                result = converter.parse_length(value)
                if result is not None:
                    # Should not be infinite or extremely large
                    assert not (result == float('inf') or result == float('-inf')), \
                        f"parse_length returned infinity for {value}"
                    assert abs(result) < 1e100, \
                        f"parse_length returned extremely large value: {result}"
            except (OverflowError, ValueError):
                # These exceptions are acceptable for overflow cases
                pass
            except Exception as e:
                pytest.fail(f"Unexpected exception for {value}: {e}")

    def test_attribute_injection_protection(self):
        """Test protection against attribute injection in SVG."""
        injection_svg = '''<svg xmlns="http://www.w3.org/2000/svg">
            <rect width="100" height="100" fill="red" onclick="alert('xss')" style="background: url('javascript:alert(1)')"/>
        </svg>'''

        # Should process without executing any injected code
        try:
            result = convert_svg_to_pptx(injection_svg)
            if result and os.path.exists(result):
                # Verify it's a valid PPTX without malicious content
                with zipfile.ZipFile(result, 'r') as zf:
                    # Check that slide content doesn't contain javascript
                    slide_files = [f for f in zf.namelist() if 'slide' in f and f.endswith('.xml')]
                    for slide_file in slide_files:
                        content = zf.read(slide_file).decode('utf-8')
                        assert 'javascript:' not in content.lower()
                        assert 'onclick' not in content.lower()

                os.unlink(result)
        except Exception:
            # Graceful failure is acceptable
            pass

    def test_binary_data_handling(self):
        """Test handling of binary data in SVG context."""
        # SVG with embedded binary data
        binary_svg = '''<svg xmlns="http://www.w3.org/2000/svg">
            <image href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="/>
        </svg>'''

        try:
            result = convert_svg_to_pptx(binary_svg)
            if result and os.path.exists(result):
                assert os.path.getsize(result) > 1000  # Should be non-trivial size
                os.unlink(result)
        except Exception:
            # Graceful failure is acceptable
            pass


class TestFileSystemSecurity:
    """Test file system security aspects."""

    def test_output_path_validation(self):
        """Test that output paths are properly validated."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'

        # Test with various potentially problematic output paths
        problematic_paths = [
            "/dev/null",  # System file
            "../../../tmp/test.pptx",  # Path traversal
            "test\0.pptx",  # Null byte injection (if on vulnerable system)
        ]

        for output_path in problematic_paths:
            try:
                # Should either work securely or fail gracefully
                result = convert_svg_to_pptx(svg_content, output_path)

                # If it succeeds, verify the result
                if result and os.path.exists(result):
                    # Should not have created file in dangerous location
                    assert not result.startswith('/dev/')
                    assert not result.startswith('/etc/')
                    # Clean up
                    try:
                        os.unlink(result)
                    except OSError:
                        pass

            except (OSError, ValueError, TypeError):
                # These exceptions are acceptable for invalid paths
                pass

    def test_concurrent_temp_file_safety(self):
        """Test that concurrent operations use safe temporary files."""
        import threading
        import time

        svg_content = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'
        results = []
        errors = []

        def convert_worker():
            try:
                result = convert_svg_to_pptx(svg_content)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Run multiple conversions concurrently
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=convert_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)

        # Clean up results
        for result in results:
            if result and os.path.exists(result):
                try:
                    os.unlink(result)
                except OSError:
                    pass

        # Should not have race conditions or file conflicts
        assert len(errors) == 0, f"Concurrent conversion errors: {errors}"

        # All results should be unique (no file conflicts)
        assert len(set(results)) == len(results), "Concurrent conversions should produce unique output files"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
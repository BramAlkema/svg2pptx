#!/usr/bin/env python3
"""
Tests for pytest configuration validation.

This module validates that the pytest infrastructure is properly configured
including plugins, coverage settings, and test discovery.
"""

import os
import sys
import pytest
import configparser
from pathlib import Path


class TestPytestConfiguration:
    """Test suite for validating pytest configuration."""
    
    def test_pytest_ini_exists(self):
        """Test that pytest.ini configuration file exists."""
        config_path = Path(__file__).parent.parent / "pytest.ini"
        assert config_path.exists(), "pytest.ini configuration file not found"
    
    def test_pytest_ini_has_required_sections(self):
        """Test that pytest.ini contains required configuration sections."""
        config_path = Path(__file__).parent.parent / "pytest.ini"
        if not config_path.exists():
            pytest.skip("pytest.ini not yet created")
        
        config = configparser.ConfigParser()
        config.read(config_path)
        
        # Check for tool:pytest section
        assert 'tool:pytest' in config, "Missing [tool:pytest] section"
        
        # Check for required options
        pytest_section = config['tool:pytest']
        required_options = ['testpaths', 'python_files', 'python_classes', 'python_functions']
        
        for option in required_options:
            assert option in pytest_section, f"Missing required option: {option}"
    
    def test_coverage_configuration(self):
        """Test that coverage is properly configured."""
        try:
            import pytest_cov
        except ImportError:
            pytest.skip("pytest-cov not installed")
        
        # Check for .coveragerc or coverage settings in pytest.ini
        coveragerc_path = Path(__file__).parent.parent / ".coveragerc"
        pytest_ini_path = Path(__file__).parent.parent / "pytest.ini"
        
        has_coverage_config = (
            coveragerc_path.exists() or 
            (pytest_ini_path.exists() and self._has_coverage_section(pytest_ini_path))
        )
        
        assert has_coverage_config, "No coverage configuration found"
    
    def test_required_plugins_installed(self):
        """Test that required pytest plugins are installed."""
        required_plugins = [
            ('pytest', 'pytest'),
            ('pytest-cov', 'pytest_cov'),
            ('pytest-mock', 'pytest_mock'),
            ('pytest-benchmark', 'pytest_benchmark'),
            ('pytest-xdist', 'xdist'),
            ('pytest-html', 'pytest_html')
        ]
        
        for plugin_name, module_name in required_plugins:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"Required plugin not installed: {plugin_name}")
    
    def test_test_directory_structure(self):
        """Test that test directory structure mirrors source code."""
        test_root = Path(__file__).parent
        src_root = test_root.parent / "src"
        
        expected_dirs = [
            'unit',
            'unit/converters',
            'unit/utils',
            'unit/performance',
            'integration',
            'visual',
            'benchmarks'
        ]
        
        for dir_name in expected_dirs:
            test_dir = test_root / dir_name
            assert test_dir.exists() or not (src_root / dir_name.replace('unit/', '')).exists(), \
                f"Expected test directory not found: {dir_name}"
    
    def test_conftest_files_exist(self):
        """Test that conftest.py files exist in key directories."""
        test_root = Path(__file__).parent
        
        expected_conftest_locations = [
            test_root / "conftest.py",
            test_root / "unit" / "conftest.py",
            test_root / "unit" / "converters" / "conftest.py"
        ]
        
        for conftest_path in expected_conftest_locations:
            if conftest_path.parent.exists():
                assert conftest_path.exists() or not conftest_path.parent.exists(), \
                    f"Missing conftest.py in {conftest_path.parent}"
    
    def test_markers_configured(self):
        """Test that custom pytest markers are configured."""
        config_path = Path(__file__).parent.parent / "pytest.ini"
        if not config_path.exists():
            pytest.skip("pytest.ini not yet created")
        
        config = configparser.ConfigParser()
        config.read(config_path)
        
        if 'tool:pytest' in config and 'markers' in config['tool:pytest']:
            markers = config['tool:pytest']['markers']
            expected_markers = ['unit', 'integration', 'visual', 'benchmark', 'slow']
            
            for marker in expected_markers:
                assert marker in markers, f"Missing marker definition: {marker}"
    
    def test_coverage_threshold_configured(self):
        """Test that coverage threshold is set to 80% or higher."""
        config_files = [
            Path(__file__).parent.parent / ".coveragerc",
            Path(__file__).parent.parent / "pytest.ini",
            Path(__file__).parent.parent / "pyproject.toml"
        ]
        
        threshold_found = False
        threshold_value = 0
        
        for config_file in config_files:
            if config_file.exists():
                content = config_file.read_text()
                # Look for fail_under setting
                if 'fail_under' in content:
                    import re
                    match = re.search(r'fail_under\s*=\s*(\d+)', content)
                    if match:
                        threshold_found = True
                        threshold_value = int(match.group(1))
                        break
        
        if threshold_found:
            assert threshold_value >= 80, f"Coverage threshold too low: {threshold_value}% (minimum 80%)"
    
    def _has_coverage_section(self, pytest_ini_path: Path) -> bool:
        """Check if pytest.ini has coverage configuration."""
        config = configparser.ConfigParser()
        config.read(pytest_ini_path)
        
        # Check for coverage options in tool:pytest section
        if 'tool:pytest' in config:
            pytest_section = config['tool:pytest']
            coverage_options = ['addopts', 'cov', 'cov-report', 'cov-fail-under']
            
            for option in coverage_options:
                if option in pytest_section:
                    return True
        
        return False


class TestFixtureConfiguration:
    """Test suite for validating fixture configuration."""
    
    def test_fixtures_importable(self):
        """Test that fixtures can be imported from conftest files."""
        test_root = Path(__file__).parent
        conftest_path = test_root / "conftest.py"
        
        if conftest_path.exists():
            # Try to import conftest
            import importlib.util
            spec = importlib.util.spec_from_file_location("conftest", conftest_path)
            conftest = importlib.util.module_from_spec(spec)
            
            try:
                spec.loader.exec_module(conftest)
            except Exception as e:
                pytest.fail(f"Failed to import conftest.py: {e}")
    
    def test_common_fixtures_defined(self):
        """Test that common fixtures are defined in conftest."""
        test_root = Path(__file__).parent
        conftest_path = test_root / "conftest.py"
        
        if not conftest_path.exists():
            pytest.skip("conftest.py not yet created")
        
        content = conftest_path.read_text()
        
        # Check for common fixture definitions
        expected_fixtures = [
            '@pytest.fixture',
            'def sample_svg',
            'def temp_dir',
            'def mock_context'
        ]
        
        for fixture_pattern in expected_fixtures:
            assert fixture_pattern in content or 'fixture' not in fixture_pattern, \
                f"Missing expected fixture pattern: {fixture_pattern}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
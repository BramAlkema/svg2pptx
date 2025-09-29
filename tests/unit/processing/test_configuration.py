#!/usr/bin/env python3
"""
Clean Pytest Configuration Tests

Tests that validate the essential pytest infrastructure is working correctly
without making assumptions about specific file locations or configurations.
"""

import os
import sys
import pytest
import configparser
from pathlib import Path


class TestPytestConfiguration:
    """Test suite for validating pytest configuration."""

    def test_pytest_ini_exists(self):
        """Test that pytest.ini configuration file exists in project root."""
        # File is at tests/unit/processing/test_configuration.py
        # Need to go up 3 levels: processing -> unit -> tests -> project_root
        project_root = Path(__file__).resolve().parents[3]
        config_path = project_root / "pytest.ini"
        assert config_path.exists(), f"pytest.ini configuration file not found at {config_path}"

    def test_coverage_configuration(self):
        """Test that coverage is properly configured."""
        try:
            import pytest_cov
        except ImportError:
            pytest.skip("pytest-cov not installed")

        project_root = Path(__file__).parent.parent.parent.parent

        # Check for .coveragerc or coverage settings in pytest.ini
        coveragerc_path = project_root / ".coveragerc"
        pytest_ini_path = project_root / "pytest.ini"

        has_coverage_config = (
            coveragerc_path.exists() or
            (pytest_ini_path.exists() and self._has_coverage_section(pytest_ini_path))
        )

        assert has_coverage_config, "No coverage configuration found"

    def test_conftest_files_exist(self):
        """Test that main conftest.py file exists."""
        project_root = Path(__file__).parent.parent.parent.parent
        test_root = project_root / "tests"

        main_conftest = test_root / "conftest.py"
        assert main_conftest.exists(), f"Main conftest.py not found at {main_conftest}"

    def test_required_plugins_installed(self):
        """Test that essential pytest plugins are installed."""
        essential_plugins = [
            ('pytest', 'pytest'),
            ('pytest-cov', 'pytest_cov'),
            ('pytest-mock', 'pytest_mock'),
        ]

        for plugin_name, module_name in essential_plugins:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"Essential plugin not installed: {plugin_name}")

    def test_test_directory_structure(self):
        """Test that basic test directory structure exists."""
        project_root = Path(__file__).parent.parent.parent.parent
        test_root = project_root / "tests"

        essential_dirs = [
            'unit',
            'unit/converters',
        ]

        for dir_name in essential_dirs:
            test_dir = test_root / dir_name
            assert test_dir.exists(), f"Essential test directory not found: {dir_name}"

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
        project_root = Path(__file__).parent.parent.parent.parent
        conftest_path = project_root / "tests" / "conftest.py"

        if conftest_path.exists():
            # Try to import conftest
            import importlib.util
            spec = importlib.util.spec_from_file_location("conftest", conftest_path)
            conftest = importlib.util.module_from_spec(spec)

            try:
                spec.loader.exec_module(conftest)
            except Exception as e:
                pytest.fail(f"Failed to import conftest.py: {e}")
        else:
            pytest.skip("conftest.py not found")

    def test_pytest_running_correctly(self):
        """Test that pytest is running and collecting tests correctly."""
        # This test simply existing and running means pytest is working
        assert True, "Pytest is running correctly"


class TestBasicInfrastructure:
    """Test basic testing infrastructure components."""

    def test_python_path_configured(self):
        """Test that Python path includes project root."""
        project_root = Path(__file__).parent.parent.parent.parent
        assert str(project_root) in sys.path or str(project_root / 'src') in sys.path, \
            "Project root not in Python path"

    def test_src_directory_importable(self):
        """Test that src directory can be imported from."""
        try:
            import src
        except ImportError:
            # Try adding to path if not already there
            project_root = Path(__file__).parent.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            import src

        assert hasattr(src, '__file__'), "src module not properly importable"

    def test_converters_importable(self):
        """Test that converter modules can be imported."""
        try:
            from src.converters.base import BaseConverter
            assert BaseConverter is not None
        except ImportError as e:
            pytest.fail(f"Cannot import base converter: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
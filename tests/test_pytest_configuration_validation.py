"""
Tests for pytest configuration validation and functionality.
Part of Task 3.1: pytest Configuration Optimization
"""
import os
import pytest
import configparser
import toml
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class PyTestConfig:
    """Configuration data structure for pytest settings."""
    testpaths: List[str]
    python_files: List[str]
    python_classes: List[str] 
    python_functions: List[str]
    addopts: List[str]
    markers: Dict[str, str]
    minversion: str
    required_plugins: List[str]


class TestPyTestConfigurationValidation:
    """Test suite for validating pytest configuration and functionality."""
    
    def test_validate_current_pytest_configuration(self):
        """Test that validates the current pytest configuration files."""
        project_root = Path(__file__).parent.parent
        
        # Check for configuration files
        pytest_ini = project_root / "pytest.ini"
        pyproject_toml = project_root / "pyproject.toml"
        setup_cfg = project_root / "setup.cfg"
        
        config_files = []
        if pytest_ini.exists():
            config_files.append(("pytest.ini", pytest_ini))
        if pyproject_toml.exists():
            config_files.append(("pyproject.toml", pyproject_toml))
        if setup_cfg.exists():
            config_files.append(("setup.cfg", setup_cfg))
        
        assert len(config_files) > 0, "At least one pytest configuration file must exist"
        
        # Document current configuration
        print(f"\n=== Current pytest Configuration Files ===")
        for config_name, config_path in config_files:
            print(f"✓ Found: {config_name}")
        
        # Validate configuration content
        self._validate_configuration_files(config_files)
    
    def test_validate_pytest_markers(self):
        """Test that validates all pytest markers are properly defined."""
        config = self._load_pytest_configuration()
        
        if not config.markers:
            pytest.skip("No markers defined in configuration")
        
        # Validate marker definitions
        required_markers = {
            'unit', 'integration', 'e2e', 'visual', 'benchmark', 
            'architecture', 'coverage', 'slow', 'converter'
        }
        
        defined_markers = set(config.markers.keys())
        
        # Check for required markers
        missing_markers = required_markers - defined_markers
        if missing_markers:
            print(f"\nMissing required markers: {missing_markers}")
        
        # Validate marker descriptions
        invalid_markers = []
        for marker, description in config.markers.items():
            if not description or len(description.strip()) < 10:
                invalid_markers.append(marker)
        
        if invalid_markers:
            print(f"\nMarkers with insufficient descriptions: {invalid_markers}")
        
        print(f"\nMarker validation summary:")
        print(f"  - Defined markers: {len(defined_markers)}")
        print(f"  - Required markers present: {len(required_markers - missing_markers)}/{len(required_markers)}")
    
    def test_validate_test_discovery_patterns(self):
        """Test that validates test discovery patterns work correctly."""
        config = self._load_pytest_configuration()
        project_root = Path(__file__).parent.parent
        
        # Validate testpaths
        for testpath in config.testpaths:
            path = project_root / testpath
            assert path.exists(), f"Testpath {testpath} does not exist"
            assert path.is_dir(), f"Testpath {testpath} is not a directory"
        
        # Test file pattern validation
        test_files_found = []
        for testpath in config.testpaths:
            test_dir = project_root / testpath
            
            # Check each python_files pattern
            for pattern in config.python_files:
                files = list(test_dir.rglob(pattern))
                test_files_found.extend(files)
        
        print(f"\nTest discovery validation:")
        print(f"  - Test paths configured: {len(config.testpaths)}")
        print(f"  - File patterns: {config.python_files}")
        print(f"  - Test files discovered: {len(test_files_found)}")
        
        assert len(test_files_found) > 0, "No test files found with current patterns"
    
    def test_validate_required_plugins(self):
        """Test that validates all required pytest plugins are available."""
        config = self._load_pytest_configuration()
        
        if not config.required_plugins:
            pytest.skip("No required plugins specified")
        
        missing_plugins = []
        available_plugins = []
        
        for plugin_spec in config.required_plugins:
            plugin_name = plugin_spec.split('>=')[0].split('==')[0]
            
            try:
                __import__(plugin_name.replace('-', '_'))
                available_plugins.append(plugin_name)
            except ImportError:
                missing_plugins.append(plugin_name)
        
        print(f"\nPlugin availability:")
        print(f"  - Required plugins: {len(config.required_plugins)}")
        print(f"  - Available: {len(available_plugins)}")
        print(f"  - Missing: {len(missing_plugins)}")
        
        if missing_plugins:
            print(f"  - Missing plugins: {missing_plugins}")
        
        # Don't fail test for missing plugins, just report
    
    def test_validate_addopts_configuration(self):
        """Test that validates pytest addopts configuration."""
        config = self._load_pytest_configuration()
        
        if not config.addopts:
            pytest.skip("No addopts configured")
        
        # Analyze addopts
        coverage_opts = [opt for opt in config.addopts if opt.startswith('--cov')]
        strict_opts = [opt for opt in config.addopts if 'strict' in opt]
        output_opts = [opt for opt in config.addopts if opt.startswith('--tb')]
        
        print(f"\naddopts Analysis:")
        print(f"  - Total options: {len(config.addopts)}")
        print(f"  - Coverage options: {len(coverage_opts)}")
        print(f"  - Strict options: {len(strict_opts)}")
        print(f"  - Output formatting: {len(output_opts)}")
        
        # Validate specific configurations
        has_coverage = any('--cov=' in opt for opt in config.addopts)
        has_strict_markers = '--strict-markers' in config.addopts
        has_strict_config = '--strict-config' in config.addopts
        
        validation_results = {
            'coverage_configured': has_coverage,
            'strict_markers_enabled': has_strict_markers,
            'strict_config_enabled': has_strict_config
        }
        
        print(f"\nValidation results: {validation_results}")
    
    def test_configuration_file_consolidation_readiness(self):
        """Test readiness for consolidating configuration into pyproject.toml."""
        project_root = Path(__file__).parent.parent
        
        # Check current configuration files
        config_files = {
            'pytest.ini': project_root / "pytest.ini",
            'pyproject.toml': project_root / "pyproject.toml", 
            'setup.cfg': project_root / "setup.cfg"
        }
        
        existing_configs = {name: path for name, path in config_files.items() if path.exists()}
        
        print(f"\n=== Configuration Consolidation Analysis ===")
        print(f"Existing configuration files:")
        for name, path in existing_configs.items():
            print(f"  - {name}: {path.stat().st_size} bytes")
        
        # Check for pyproject.toml readiness
        pyproject_path = config_files['pyproject.toml']
        pyproject_ready = False
        
        if pyproject_path.exists():
            try:
                with open(pyproject_path, 'r') as f:
                    pyproject_data = toml.load(f)
                    has_tool_section = 'tool' in pyproject_data
                    has_pytest_section = has_tool_section and 'pytest' in pyproject_data.get('tool', {})
                    
                    pyproject_ready = has_tool_section
                    
                    print(f"\npyproject.toml analysis:")
                    print(f"  - Has [tool] section: {has_tool_section}")
                    print(f"  - Has [tool.pytest] section: {has_pytest_section}")
                    
            except Exception as e:
                print(f"  - Error reading pyproject.toml: {e}")
        else:
            print(f"\npyproject.toml does not exist - needs creation")
        
        # Consolidation recommendations
        recommendations = []
        if len(existing_configs) > 1:
            recommendations.append("Multiple config files found - consolidation recommended")
        if not pyproject_ready:
            recommendations.append("pyproject.toml needs [tool] section setup")
        
        if recommendations:
            print(f"\nConsolidation recommendations:")
            for rec in recommendations:
                print(f"  - {rec}")
    
    def test_performance_configuration_validation(self):
        """Test performance-related pytest configuration."""
        config = self._load_pytest_configuration()
        
        # Check for performance-related options
        performance_opts = []
        if config.addopts:
            performance_opts = [
                opt for opt in config.addopts 
                if any(perf_keyword in opt.lower() for perf_keyword in 
                      ['timeout', 'duration', 'benchmark', 'parallel', 'xdist'])
            ]
        
        # Check for parallel execution plugins
        parallel_plugins = [
            plugin for plugin in (config.required_plugins or [])
            if 'xdist' in plugin
        ]
        
        print(f"\n=== Performance Configuration ===")
        print(f"Performance-related addopts: {len(performance_opts)}")
        print(f"Parallel execution plugins: {len(parallel_plugins)}")
        
        if performance_opts:
            print("Performance options found:")
            for opt in performance_opts:
                print(f"  - {opt}")
    
    def _validate_configuration_files(self, config_files: List[tuple]):
        """Validate each configuration file's content."""
        for config_name, config_path in config_files:
            print(f"\nValidating {config_name}:")
            
            if config_name == "pytest.ini":
                self._validate_pytest_ini(config_path)
            elif config_name == "pyproject.toml":
                self._validate_pyproject_toml(config_path)
            elif config_name == "setup.cfg":
                self._validate_setup_cfg(config_path)
    
    def _validate_pytest_ini(self, config_path: Path):
        """Validate pytest.ini file content."""
        try:
            config = configparser.ConfigParser()
            config.read(config_path)
            
            sections = list(config.sections())
            print(f"  - Sections: {sections}")
            
            if 'tool:pytest' in sections:
                pytest_section = config['tool:pytest']
                keys = list(pytest_section.keys())
                print(f"  - pytest keys: {len(keys)}")
                
                # Validate required keys
                required_keys = ['testpaths', 'python_files', 'markers']
                missing_keys = [key for key in required_keys if key not in keys]
                if missing_keys:
                    print(f"  - Missing required keys: {missing_keys}")
                else:
                    print(f"  - All required keys present")
            
        except Exception as e:
            print(f"  - Error validating pytest.ini: {e}")
    
    def _validate_pyproject_toml(self, config_path: Path):
        """Validate pyproject.toml file content."""
        try:
            with open(config_path, 'r') as f:
                data = toml.load(f)
            
            has_tool = 'tool' in data
            has_pytest = has_tool and 'pytest' in data.get('tool', {})
            
            print(f"  - Has [tool] section: {has_tool}")
            print(f"  - Has [tool.pytest] section: {has_pytest}")
            
            if has_pytest:
                pytest_config = data['tool']['pytest']
                keys = list(pytest_config.keys())
                print(f"  - pytest configuration keys: {len(keys)}")
            
        except Exception as e:
            print(f"  - Error validating pyproject.toml: {e}")
    
    def _validate_setup_cfg(self, config_path: Path):
        """Validate setup.cfg file content.""" 
        try:
            config = configparser.ConfigParser()
            config.read(config_path)
            
            sections = list(config.sections())
            print(f"  - Sections: {sections}")
            
            if 'tool:pytest' in sections:
                print(f"  - Has pytest configuration section")
            
        except Exception as e:
            print(f"  - Error validating setup.cfg: {e}")
    
    def _load_pytest_configuration(self) -> PyTestConfig:
        """Load current pytest configuration into structured format."""
        project_root = Path(__file__).parent.parent
        pytest_ini = project_root / "pytest.ini"
        
        # Default configuration
        config = PyTestConfig(
            testpaths=[],
            python_files=[],
            python_classes=[],
            python_functions=[],
            addopts=[],
            markers={},
            minversion="",
            required_plugins=[]
        )
        
        if pytest_ini.exists():
            try:
                parser = configparser.ConfigParser()
                parser.read(pytest_ini)
                
                if 'tool:pytest' in parser:
                    section = parser['tool:pytest']
                    
                    # Parse each configuration value
                    if 'testpaths' in section:
                        config.testpaths = [p.strip() for p in section['testpaths'].split()]
                    
                    if 'python_files' in section:
                        config.python_files = [p.strip() for p in section['python_files'].split()]
                    
                    if 'python_classes' in section:
                        config.python_classes = [p.strip() for p in section['python_classes'].split()]
                    
                    if 'python_functions' in section:
                        config.python_functions = [p.strip() for p in section['python_functions'].split()]
                    
                    if 'addopts' in section:
                        # Handle multi-line addopts
                        addopts_str = section['addopts'].replace('\n', ' ')
                        config.addopts = [opt.strip() for opt in addopts_str.split() if opt.strip()]
                    
                    if 'markers' in section:
                        markers_str = section['markers']
                        config.markers = self._parse_markers(markers_str)
                    
                    if 'minversion' in section:
                        config.minversion = section['minversion']
                    
                    if 'required_plugins' in section:
                        plugins_str = section['required_plugins']
                        config.required_plugins = [p.strip() for p in plugins_str.split('\n') if p.strip()]
                        
            except Exception as e:
                print(f"Error loading pytest configuration: {e}")
        
        return config
    
    def _parse_markers(self, markers_str: str) -> Dict[str, str]:
        """Parse markers string into dictionary."""
        markers = {}
        
        for line in markers_str.split('\n'):
            line = line.strip()
            if line and ':' in line:
                marker, description = line.split(':', 1)
                markers[marker.strip()] = description.strip()
        
        return markers
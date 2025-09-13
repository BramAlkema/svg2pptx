"""
Tests for analyzing current test file naming conventions.
Part of Task 1.1: Test File Organization and Naming Standardization
"""
import os
import re
import pytest
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class TestFileInfo:
    """Information about a test file and its naming pattern."""
    path: Path
    filename: str
    directory: str
    category: str  # unit, integration, e2e, visual, etc.
    naming_pattern: str
    follows_standard: bool
    suggested_name: str = ""


class TestNamingConventionAnalysis:
    """Test suite for analyzing current naming conventions across all test files."""
    
    def test_analyze_current_naming_patterns(self):
        """Test that analyzes all existing test files and categorizes their naming patterns."""
        test_files = self._get_all_test_files()
        
        # Analyze patterns
        naming_patterns = self._analyze_naming_patterns(test_files)
        
        # Basic validation
        assert len(test_files) > 0, "No test files found"
        assert len(naming_patterns) > 0, "No naming patterns identified"
        
        # Document findings for manual review
        self._document_findings(test_files, naming_patterns)
    
    def test_identify_inconsistent_naming(self):
        """Test that identifies files with inconsistent naming patterns."""
        test_files = self._get_all_test_files()
        
        inconsistent_files = []
        standard_patterns = self._get_standard_patterns()
        
        for file_info in test_files:
            if not self._matches_standard_pattern(file_info, standard_patterns):
                inconsistent_files.append(file_info)
        
        # Log inconsistencies for remediation
        if inconsistent_files:
            print(f"\nFound {len(inconsistent_files)} files with inconsistent naming:")
            for file_info in inconsistent_files:
                print(f"  - {file_info.path}")
    
    def test_validate_directory_structure(self):
        """Test that validates the current directory structure organization."""
        expected_dirs = {
            'tests/unit', 'tests/integration', 'tests/e2e_api', 
            'tests/e2e_visual', 'tests/e2e_library', 'tests/architecture',
            'tests/coverage', 'tests/visual', 'tests/benchmarks'
        }
        
        project_root = Path(__file__).parent.parent
        
        for expected_dir in expected_dirs:
            dir_path = project_root / expected_dir
            if dir_path.exists():
                print(f"✓ Found directory: {expected_dir}")
            else:
                print(f"✗ Missing directory: {expected_dir}")
    
    def test_suggest_standardized_names(self):
        """Test that generates standardized name suggestions for all test files."""
        test_files = self._get_all_test_files()
        suggestions = {}
        
        for file_info in test_files:
            if not file_info.follows_standard:
                suggested_name = self._generate_suggested_name(file_info)
                suggestions[str(file_info.path)] = suggested_name
        
        # Document suggestions
        if suggestions:
            print(f"\nGenerated {len(suggestions)} naming suggestions:")
            for current_name, suggested_name in suggestions.items():
                print(f"  {current_name} -> {suggested_name}")
    
    def _get_all_test_files(self) -> List[TestFileInfo]:
        """Get information about all test files in the project."""
        project_root = Path(__file__).parent.parent
        test_files = []
        
        # Find all Python test files
        for py_file in project_root.glob('tests/**/*.py'):
            if py_file.name.startswith('test_') or py_file.name.endswith('_test.py'):
                if py_file.name != '__init__.py':
                    file_info = self._analyze_file(py_file)
                    test_files.append(file_info)
        
        return test_files
    
    def _analyze_file(self, file_path: Path) -> TestFileInfo:
        """Analyze a single test file and determine its properties."""
        relative_path = file_path.relative_to(Path(__file__).parent.parent)
        directory = str(relative_path.parent)
        
        # Determine category based on directory
        category = self._determine_category(directory)
        
        # Analyze naming pattern
        naming_pattern = self._determine_naming_pattern(file_path.name)
        
        # Check if follows standard
        follows_standard = self._follows_standard_naming(file_path.name, category)
        
        return TestFileInfo(
            path=relative_path,
            filename=file_path.name,
            directory=directory,
            category=category,
            naming_pattern=naming_pattern,
            follows_standard=follows_standard
        )
    
    def _determine_category(self, directory: str) -> str:
        """Determine the test category based on directory path."""
        if 'unit' in directory:
            return 'unit'
        elif 'integration' in directory:
            return 'integration'
        elif 'e2e' in directory:
            return 'e2e'
        elif 'visual' in directory:
            return 'visual'
        elif 'benchmark' in directory:
            return 'benchmark'
        elif 'architecture' in directory:
            return 'architecture'
        elif 'coverage' in directory:
            return 'coverage'
        else:
            return 'misc'
    
    def _determine_naming_pattern(self, filename: str) -> str:
        """Determine the naming pattern used by a file."""
        if filename.startswith('test_') and filename.endswith('.py'):
            return 'test_prefix'
        elif filename.endswith('_test.py'):
            return 'test_suffix'
        else:
            return 'other'
    
    def _follows_standard_naming(self, filename: str, category: str) -> bool:
        """Check if a filename follows the standard naming convention."""
        # Standard patterns based on technical spec
        standard_patterns = {
            'unit': r'^test_[a-z_]+\.py$',
            'integration': r'^test_[a-z_]+\.py$',
            'e2e': r'^test_[a-z_]+_e2e\.py$',
            'visual': r'^test_[a-z_]+_visual\.py$',
            'benchmark': r'^test_[a-z_]+_benchmark\.py$',
            'architecture': r'^test_[a-z_]+\.py$',
            'coverage': r'^test_[a-z_]+\.py$',
            'misc': r'^test_[a-z_]+\.py$'
        }
        
        pattern = standard_patterns.get(category, r'^test_[a-z_]+\.py$')
        return bool(re.match(pattern, filename))
    
    def _analyze_naming_patterns(self, test_files: List[TestFileInfo]) -> Dict[str, int]:
        """Analyze and count different naming patterns."""
        patterns = {}
        
        for file_info in test_files:
            pattern = file_info.naming_pattern
            patterns[pattern] = patterns.get(pattern, 0) + 1
        
        return patterns
    
    def _get_standard_patterns(self) -> Dict[str, str]:
        """Get the standard naming patterns for different test categories."""
        return {
            'unit': 'test_<component_name>.py',
            'integration': 'test_<integration_scenario>.py',
            'e2e': 'test_<workflow_name>_e2e.py',
            'visual': 'test_<visual_aspect>_visual.py',
            'benchmark': 'test_<performance_aspect>_benchmark.py'
        }
    
    def _matches_standard_pattern(self, file_info: TestFileInfo, standard_patterns: Dict[str, str]) -> bool:
        """Check if a file matches the standard pattern for its category."""
        return file_info.follows_standard
    
    def _generate_suggested_name(self, file_info: TestFileInfo) -> str:
        """Generate a suggested standardized name for a file."""
        # Extract core component name from current filename
        base_name = file_info.filename.replace('test_', '').replace('.py', '')
        
        # Apply category-specific naming
        if file_info.category == 'e2e':
            return f"test_{base_name}_e2e.py"
        elif file_info.category == 'visual':
            return f"test_{base_name}_visual.py"
        elif file_info.category == 'benchmark':
            return f"test_{base_name}_benchmark.py"
        else:
            return f"test_{base_name}.py"
    
    def _document_findings(self, test_files: List[TestFileInfo], patterns: Dict[str, int]):
        """Document the analysis findings."""
        print(f"\n=== Test File Naming Convention Analysis ===")
        print(f"Total test files analyzed: {len(test_files)}")
        print(f"\nNaming patterns found:")
        for pattern, count in patterns.items():
            print(f"  - {pattern}: {count} files")
        
        # Category breakdown
        categories = {}
        for file_info in test_files:
            cat = file_info.category
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"\nFiles by category:")
        for category, count in categories.items():
            print(f"  - {category}: {count} files")
        
        # Standards compliance
        compliant = sum(1 for f in test_files if f.follows_standard)
        non_compliant = len(test_files) - compliant
        
        print(f"\nStandards compliance:")
        print(f"  - Compliant: {compliant} files ({compliant/len(test_files)*100:.1f}%)")
        print(f"  - Non-compliant: {non_compliant} files ({non_compliant/len(test_files)*100:.1f}%)")
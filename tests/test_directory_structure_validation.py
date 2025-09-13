"""
Tests for directory structure validation and organization.
Part of Task 2.1: Directory Structure Consolidation
"""
import os
import pytest
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class DirectoryInfo:
    """Information about a test directory and its structure."""
    path: Path
    name: str
    level: int
    file_count: int
    subdirs: List[str]
    expected_purpose: str
    follows_standard: bool


class TestDirectoryStructureValidation:
    """Test suite for validating and organizing test directory structure."""
    
    def test_validate_current_directory_structure(self):
        """Test that validates the current directory structure organization."""
        project_root = Path(__file__).parent.parent
        tests_dir = project_root / "tests"
        
        # Get current directory structure
        directory_structure = self._analyze_directory_structure(tests_dir)
        
        # Basic validation
        assert tests_dir.exists(), "Tests directory must exist"
        assert len(directory_structure) > 0, "Tests directory must contain subdirectories"
        
        # Document current structure for analysis
        self._document_directory_structure(directory_structure)
    
    def test_identify_consolidation_opportunities(self):
        """Test that identifies directories that can be consolidated or reorganized."""
        project_root = Path(__file__).parent.parent
        tests_dir = project_root / "tests"
        
        consolidation_opportunities = []
        
        # Analyze root-level test files (should be moved to subdirectories)
        root_test_files = list(tests_dir.glob("test_*.py"))
        if root_test_files:
            consolidation_opportunities.append({
                "type": "root_level_files",
                "count": len(root_test_files),
                "recommendation": "Move to appropriate subdirectories",
                "files": [f.name for f in root_test_files[:5]]  # Show first 5
            })
        
        # Check for scattered similar test types
        similar_dirs = self._find_similar_directories(tests_dir)
        for similar_group in similar_dirs:
            if len(similar_group) > 1:
                consolidation_opportunities.append({
                    "type": "similar_directories",
                    "directories": similar_group,
                    "recommendation": "Consider consolidating into single directory"
                })
        
        # Document opportunities
        print(f"\nIdentified {len(consolidation_opportunities)} consolidation opportunities:")
        for i, opportunity in enumerate(consolidation_opportunities, 1):
            print(f"  {i}. {opportunity['type']}: {opportunity.get('count', len(opportunity.get('directories', [])))}")
    
    def test_validate_expected_directory_hierarchy(self):
        """Test that validates directories follow expected hierarchy patterns."""
        expected_structure = self._get_expected_directory_structure()
        project_root = Path(__file__).parent.parent
        tests_dir = project_root / "tests"
        
        validation_results = []
        
        for expected_dir, properties in expected_structure.items():
            dir_path = tests_dir / expected_dir
            
            result = {
                "directory": expected_dir,
                "exists": dir_path.exists(),
                "expected_purpose": properties["purpose"],
                "expected_structure": properties.get("structure", "flat")
            }
            
            if dir_path.exists():
                # Count files and subdirs
                py_files = list(dir_path.glob("*.py"))
                subdirs = [d for d in dir_path.iterdir() if d.is_dir()]
                
                result.update({
                    "file_count": len(py_files),
                    "subdir_count": len(subdirs),
                    "has_init": (dir_path / "__init__.py").exists()
                })
            
            validation_results.append(result)
        
        # Document validation results
        self._document_hierarchy_validation(validation_results)
        
        # Basic assertions
        essential_dirs = ["unit", "integration", "e2e_api"]
        for essential_dir in essential_dirs:
            dir_path = tests_dir / essential_dir
            assert dir_path.exists(), f"Essential directory {essential_dir} must exist"
    
    def test_validate_init_file_presence(self):
        """Test that validates __init__.py files are present where needed."""
        project_root = Path(__file__).parent.parent
        tests_dir = project_root / "tests"
        
        init_file_status = []
        
        # Check all test directories
        for dir_path in tests_dir.rglob("*"):
            if dir_path.is_dir() and dir_path != tests_dir:
                init_file = dir_path / "__init__.py"
                
                status = {
                    "directory": str(dir_path.relative_to(tests_dir)),
                    "has_init": init_file.exists(),
                    "needs_init": self._should_have_init_file(dir_path),
                    "file_count": len(list(dir_path.glob("*.py")))
                }
                
                init_file_status.append(status)
        
        # Find directories that need __init__.py files
        missing_init = [s for s in init_file_status if s["needs_init"] and not s["has_init"]]
        
        print(f"\nDirectories missing __init__.py files: {len(missing_init)}")
        for status in missing_init:
            print(f"  - {status['directory']} ({status['file_count']} Python files)")
    
    def test_detect_orphaned_files(self):
        """Test that detects test files that don't belong in their current location."""
        project_root = Path(__file__).parent.parent
        tests_dir = project_root / "tests"
        
        orphaned_files = []
        
        # Check each Python file to see if it's in the right location
        for py_file in tests_dir.rglob("test_*.py"):
            if py_file.name == "__init__.py":
                continue
                
            current_location = py_file.parent
            suggested_location = self._suggest_file_location(py_file)
            
            if suggested_location != str(current_location.relative_to(tests_dir)):
                orphaned_files.append({
                    "file": str(py_file.relative_to(tests_dir)),
                    "current_location": str(current_location.relative_to(tests_dir)),
                    "suggested_location": suggested_location,
                    "reason": self._get_relocation_reason(py_file)
                })
        
        print(f"\nOrphaned files found: {len(orphaned_files)}")
        for orphan in orphaned_files[:10]:  # Show first 10
            print(f"  - {orphan['file']} -> {orphan['suggested_location']}")
    
    def _analyze_directory_structure(self, tests_dir: Path) -> List[DirectoryInfo]:
        """Analyze the current directory structure."""
        directories = []
        
        for dir_path in tests_dir.rglob("*"):
            if dir_path.is_dir() and dir_path != tests_dir:
                relative_path = dir_path.relative_to(tests_dir)
                level = len(relative_path.parts)
                
                # Count Python files
                py_files = list(dir_path.glob("*.py"))
                subdirs = [d.name for d in dir_path.iterdir() if d.is_dir()]
                
                dir_info = DirectoryInfo(
                    path=relative_path,
                    name=dir_path.name,
                    level=level,
                    file_count=len(py_files),
                    subdirs=subdirs,
                    expected_purpose=self._determine_expected_purpose(dir_path.name),
                    follows_standard=self._follows_standard_structure(dir_path.name, level)
                )
                
                directories.append(dir_info)
        
        return directories
    
    def _document_directory_structure(self, directories: List[DirectoryInfo]):
        """Document the current directory structure."""
        print(f"\n=== Current Directory Structure Analysis ===")
        print(f"Total directories analyzed: {len(directories)}")
        
        # Group by level
        by_level = {}
        for dir_info in directories:
            level = dir_info.level
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(dir_info)
        
        for level in sorted(by_level.keys()):
            print(f"\nLevel {level} directories:")
            for dir_info in by_level[level]:
                indent = "  " * level
                print(f"{indent}- {dir_info.name}/ ({dir_info.file_count} files, {len(dir_info.subdirs)} subdirs)")
    
    def _get_expected_directory_structure(self) -> Dict[str, Dict]:
        """Get the expected directory structure specification."""
        return {
            "unit": {
                "purpose": "Unit tests for individual components",
                "structure": "hierarchical",
                "subdirs": ["converters", "utils", "batch", "api"]
            },
            "integration": {
                "purpose": "Integration tests for multiple components", 
                "structure": "flat"
            },
            "e2e_integration": {
                "purpose": "End-to-end integration tests",
                "structure": "flat"
            },
            "e2e_api": {
                "purpose": "End-to-end API tests",
                "structure": "flat"
            },
            "e2e_library": {
                "purpose": "End-to-end library tests",
                "structure": "flat"
            },
            "e2e_visual": {
                "purpose": "End-to-end visual tests",
                "structure": "flat"
            },
            "visual": {
                "purpose": "Visual regression tests",
                "structure": "flat"
            },
            "benchmarks": {
                "purpose": "Performance benchmark tests",
                "structure": "flat"
            },
            "architecture": {
                "purpose": "Architecture and consistency tests",
                "structure": "flat"
            },
            "coverage": {
                "purpose": "Coverage analysis tests",
                "structure": "flat"
            }
        }
    
    def _find_similar_directories(self, tests_dir: Path) -> List[List[str]]:
        """Find directories with similar purposes that could be consolidated."""
        similar_groups = []
        
        # Find E2E-related directories
        e2e_dirs = []
        for dir_path in tests_dir.iterdir():
            if dir_path.is_dir() and ("e2e" in dir_path.name.lower() or "end" in dir_path.name.lower()):
                e2e_dirs.append(dir_path.name)
        
        if len(e2e_dirs) > 1:
            similar_groups.append(e2e_dirs)
        
        # Find performance-related directories
        perf_dirs = []
        for dir_path in tests_dir.iterdir():
            if dir_path.is_dir() and any(term in dir_path.name.lower() for term in ["benchmark", "performance", "perf"]):
                perf_dirs.append(dir_path.name)
        
        if len(perf_dirs) > 1:
            similar_groups.append(perf_dirs)
        
        return similar_groups
    
    def _document_hierarchy_validation(self, results: List[Dict]):
        """Document directory hierarchy validation results."""
        print(f"\n=== Directory Hierarchy Validation ===")
        
        existing = [r for r in results if r["exists"]]
        missing = [r for r in results if not r["exists"]]
        
        print(f"Existing directories: {len(existing)}")
        for result in existing:
            init_status = "✓" if result.get("has_init") else "✗"
            print(f"  - {result['directory']}/ ({result['file_count']} files) {init_status}")
        
        if missing:
            print(f"\nMissing expected directories: {len(missing)}")
            for result in missing:
                print(f"  - {result['directory']}/ (purpose: {result['expected_purpose']})")
    
    def _should_have_init_file(self, dir_path: Path) -> bool:
        """Determine if a directory should have an __init__.py file."""
        # Directories with Python files should have __init__.py
        py_files = list(dir_path.glob("*.py"))
        has_python_files = len([f for f in py_files if f.name != "__init__.py"]) > 0
        
        # Skip certain directories
        skip_dirs = {"__pycache__", ".pytest_cache", "fixtures"}
        if dir_path.name in skip_dirs:
            return False
            
        return has_python_files
    
    def _suggest_file_location(self, py_file: Path) -> str:
        """Suggest the appropriate location for a test file."""
        filename = py_file.name
        
        # E2E tests
        if "_e2e.py" in filename:
            if "api" in filename.lower():
                return "e2e_api"
            elif "visual" in filename.lower():
                return "e2e_visual"
            elif "library" in filename.lower():
                return "e2e_library"
            else:
                return "e2e_integration"
        
        # Visual tests
        if "_visual.py" in filename:
            return "visual"
        
        # Benchmark tests
        if "_benchmark.py" in filename or "benchmark" in filename.lower():
            return "benchmarks"
        
        # Architecture tests
        if "architecture" in filename.lower() or "consistency" in filename.lower():
            return "architecture"
        
        # Coverage tests
        if "coverage" in filename.lower():
            return "coverage"
        
        # Integration tests
        if "integration" in filename.lower():
            return "integration"
        
        # Converter tests
        if "converter" in filename.lower():
            return "unit/converters"
        
        # Utility tests
        if any(term in filename.lower() for term in ["util", "helper", "color", "transform"]):
            return "unit/utils"
        
        # Batch tests
        if "batch" in filename.lower():
            return "unit/batch"
        
        # API tests
        if "api" in filename.lower() and "_e2e" not in filename:
            return "unit/api"
        
        # Default to unit tests
        return "unit"
    
    def _get_relocation_reason(self, py_file: Path) -> str:
        """Get the reason why a file should be relocated."""
        filename = py_file.name
        
        if "_e2e.py" in filename:
            return "E2E tests should be in e2e_* directories"
        if "_visual.py" in filename:
            return "Visual tests should be in visual/ directory"
        if "_benchmark.py" in filename:
            return "Benchmark tests should be in benchmarks/ directory"
        if "converter" in filename.lower():
            return "Converter tests should be in unit/converters/"
        
        return "Better organization in appropriate subdirectory"
    
    def _determine_expected_purpose(self, dir_name: str) -> str:
        """Determine the expected purpose of a directory based on its name."""
        if "unit" in dir_name:
            return "Unit tests"
        elif "integration" in dir_name:
            return "Integration tests" 
        elif "e2e" in dir_name:
            return "End-to-end tests"
        elif "visual" in dir_name:
            return "Visual regression tests"
        elif "benchmark" in dir_name:
            return "Performance tests"
        elif "architecture" in dir_name:
            return "Architecture tests"
        elif "coverage" in dir_name:
            return "Coverage analysis"
        else:
            return "General test directory"
    
    def _follows_standard_structure(self, dir_name: str, level: int) -> bool:
        """Check if directory follows standard structure conventions."""
        standard_top_level = {
            "unit", "integration", "e2e_integration", "e2e_api", 
            "e2e_library", "e2e_visual", "visual", "benchmarks", 
            "architecture", "coverage"
        }
        
        if level == 1:  # Top level
            return dir_name in standard_top_level
        
        # For deeper levels, be more permissive
        return True
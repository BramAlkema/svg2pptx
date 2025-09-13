#!/usr/bin/env python3
"""
Script to migrate test files to consolidated directory structure.
Part of Task 2.4: Migrate test files to consolidated structure
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


class DirectoryMigrator:
    """Handles migration of test files to consolidated structure."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        
        # Track migrations for verification
        self.migrations_performed = []
        
    def migrate_to_consolidated_structure(self):
        """Migrate all files to the new consolidated directory structure."""
        print("=== Migrating to Consolidated Directory Structure ===\n")
        
        # Phase 1: Create new directory structure
        self._create_new_directory_structure()
        
        # Phase 2: Migrate files by category
        self._migrate_converter_tests()
        self._migrate_validation_tests()
        self._migrate_performance_tests()
        self._migrate_processing_tests()
        self._migrate_quality_tests()
        
        # Phase 3: Consolidate E2E directories
        self._consolidate_e2e_directories()
        
        print(f"\nCompleted directory consolidation:")
        print(f"  - Files migrated: {len(self.migrations_performed)}")
        print(f"  - New directory structure created")
        
        return self.migrations_performed
    
    def _create_new_directory_structure(self):
        """Create the new consolidated directory structure."""
        print("Phase 1: Creating new directory structure...")
        
        new_directories = [
            "unit/converters",
            "unit/validation", 
            "unit/processing",
            "unit/utils",
            "unit/batch",
            "unit/api",
            "e2e/api",
            "e2e/visual", 
            "e2e/library",
            "e2e/integration",
            "performance/benchmarks",
            "performance/profiling",
            "quality/architecture",
            "quality/coverage",
            "quality/consistency",
            "support/mocks",
            "support/fixtures",
            "support/helpers",
            "support/generators",
            "data/svg/basic",
            "data/svg/complex",
            "data/svg/edge_cases",
            "data/expected",
            "data/fixtures"
        ]
        
        for dir_path in new_directories:
            full_path = self.tests_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            
            # Create __init__.py files
            init_file = full_path / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                print(f"  ✓ Created {dir_path}/__init__.py")
        
        # Create top-level __init__.py files
        for top_level in ["unit", "e2e", "performance", "quality", "support", "data"]:
            init_file = self.tests_dir / top_level / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                print(f"  ✓ Created {top_level}/__init__.py")
    
    def _migrate_converter_tests(self):
        """Migrate converter-related test files."""
        print("\nPhase 2a: Migrating converter tests...")
        
        converter_files = [
            "test_animations_converter.py",
            "test_base_converter.py", 
            "test_filters_converter.py",
            "test_gradients_converter.py",
            "test_markers_additional.py",
            "test_markers_converter.py",
            "test_markers_final.py",
            "test_masking_converter.py",
            "test_styles_processor.py",
            "test_symbols_converter.py",
            "test_text_path_converter.py"
        ]
        
        target_dir = self.tests_dir / "unit" / "converters"
        
        for filename in converter_files:
            self._move_file_if_exists(filename, target_dir)
    
    def _migrate_validation_tests(self):
        """Migrate validation-related test files."""
        print("\nPhase 2b: Migrating validation tests...")
        
        validation_files = [
            "test_accuracy_measurement.py",
            "test_pptx_validation.py",
            "test_pptx_validation_complete.py",
            "test_pptx_validation_comprehensive.py", 
            "test_pptx_validation_final.py",
            "test_visual_regression.py",
            "test_workflow_validator.py"
        ]
        
        target_dir = self.tests_dir / "unit" / "validation"
        
        for filename in validation_files:
            self._move_file_if_exists(filename, target_dir)
    
    def _migrate_performance_tests(self):
        """Migrate performance-related test files."""
        print("\nPhase 2c: Migrating performance tests...")
        
        performance_files = [
            "test_performance_speedrun_benchmark.py",
            "test_performance_speedrun_cache.py", 
            "test_performance_speedrun_optimizer.py"
        ]
        
        target_dir = self.tests_dir / "performance" / "benchmarks"
        
        for filename in performance_files:
            self._move_file_if_exists(filename, target_dir)
            
        # Also move existing benchmarks directory content
        old_benchmarks = self.tests_dir / "benchmarks"
        if old_benchmarks.exists():
            for file_path in old_benchmarks.glob("*.py"):
                if file_path.name != "__init__.py":
                    self._move_file(file_path, target_dir)
    
    def _migrate_processing_tests(self):
        """Migrate core processing test files."""
        print("\nPhase 2d: Migrating processing tests...")
        
        processing_files = [
            "test_configuration.py",
            "test_end_to_end_workflow.py",
            "test_module_imports.py"
        ]
        
        target_dir = self.tests_dir / "unit" / "processing"
        
        for filename in processing_files:
            self._move_file_if_exists(filename, target_dir)
    
    def _migrate_quality_tests(self):
        """Migrate quality-related test files.""" 
        print("\nPhase 2e: Migrating quality tests...")
        
        # Move coverage tests
        coverage_files = ["test_coverage_configuration.py"]
        coverage_target = self.tests_dir / "quality" / "coverage"
        
        for filename in coverage_files:
            self._move_file_if_exists(filename, coverage_target)
        
        # Move existing coverage directory content
        old_coverage = self.tests_dir / "coverage"
        if old_coverage.exists():
            for file_path in old_coverage.glob("*.py"):
                if file_path.name != "__init__.py":
                    self._move_file(file_path, coverage_target)
        
        # Move existing architecture directory content
        old_architecture = self.tests_dir / "architecture"
        architecture_target = self.tests_dir / "quality" / "architecture"
        
        if old_architecture.exists():
            for file_path in old_architecture.glob("*.py"):
                if file_path.name != "__init__.py":
                    self._move_file(file_path, architecture_target)
    
    def _consolidate_e2e_directories(self):
        """Consolidate all E2E directories under e2e/."""
        print("\nPhase 3: Consolidating E2E directories...")
        
        e2e_mappings = {
            "e2e_api": "e2e/api",
            "e2e_visual": "e2e/visual",
            "e2e_library": "e2e/library", 
            "e2e_integration": "e2e/integration"
        }
        
        for old_dir, new_dir in e2e_mappings.items():
            old_path = self.tests_dir / old_dir
            new_path = self.tests_dir / new_dir
            
            if old_path.exists():
                # Move all Python files
                for file_path in old_path.glob("*.py"):
                    if file_path.name != "__init__.py":
                        self._move_file(file_path, new_path)
                        
                # Move subdirectories if any
                for sub_path in old_path.iterdir():
                    if sub_path.is_dir() and sub_path.name != "__pycache__":
                        target_sub = new_path / sub_path.name
                        if not target_sub.exists():
                            shutil.move(str(sub_path), str(target_sub))
                            print(f"  ✓ Moved directory {old_dir}/{sub_path.name} -> {new_dir}/{sub_path.name}")
    
    def _move_file_if_exists(self, filename: str, target_dir: Path):
        """Move a file from tests root to target directory if it exists."""
        source_file = self.tests_dir / filename
        if source_file.exists():
            self._move_file(source_file, target_dir)
    
    def _move_file(self, source_file: Path, target_dir: Path):
        """Move a file to target directory and track the migration."""
        target_file = target_dir / source_file.name
        
        if target_file.exists():
            print(f"  ⚠️  Target already exists: {target_file.name}")
            return False
        
        try:
            shutil.move(str(source_file), str(target_file))
            print(f"  ✅ Moved: {source_file.name} -> {target_dir.name}/")
            
            # Track migration
            self.migrations_performed.append((str(source_file), str(target_file)))
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to move {source_file.name}: {e}")
            return False
    
    def _cleanup_empty_directories(self):
        """Clean up empty directories after migration."""
        print("\nPhase 4: Cleaning up empty directories...")
        
        directories_to_check = [
            "benchmarks",
            "coverage", 
            "architecture",
            "e2e_api",
            "e2e_visual",
            "e2e_library",
            "e2e_integration"
        ]
        
        for dir_name in directories_to_check:
            dir_path = self.tests_dir / dir_name
            if dir_path.exists() and self._is_directory_empty(dir_path):
                try:
                    shutil.rmtree(dir_path)
                    print(f"  ✅ Removed empty directory: {dir_name}")
                except Exception as e:
                    print(f"  ⚠️  Could not remove {dir_name}: {e}")
    
    def _is_directory_empty(self, dir_path: Path) -> bool:
        """Check if directory is empty (ignoring __pycache__ and __init__.py)."""
        contents = list(dir_path.iterdir())
        
        # Filter out cache and empty init files
        meaningful_contents = []
        for item in contents:
            if item.name == "__pycache__":
                continue
            if item.name == "__init__.py" and item.stat().st_size == 0:
                continue
            meaningful_contents.append(item)
        
        return len(meaningful_contents) == 0
    
    def preview_migration(self):
        """Preview what changes would be made without executing them."""
        print("=== Preview of Directory Migration ===\n")
        
        migrations = [
            ("Converter tests", ["test_animations_converter.py", "test_base_converter.py", "test_filters_converter.py"], "unit/converters/"),
            ("Validation tests", ["test_accuracy_measurement.py", "test_pptx_validation.py"], "unit/validation/"),
            ("Performance tests", ["test_performance_speedrun_benchmark.py"], "performance/benchmarks/"),
            ("Processing tests", ["test_configuration.py", "test_module_imports.py"], "unit/processing/"),
            ("E2E directories", ["e2e_api -> e2e/api", "e2e_visual -> e2e/visual"], "consolidated"),
        ]
        
        total_files = 0
        for category, examples, target in migrations:
            print(f"{category} -> {target}")
            for example in examples:
                print(f"  - {example}")
            total_files += len(examples)
            print()
        
        print(f"Estimated files to migrate: {total_files}+")


if __name__ == "__main__":
    migrator = DirectoryMigrator()
    
    # Show preview first
    migrator.preview_migration()
    
    print("=" * 50)
    response = input("Proceed with migration? (y/N): ").strip().lower()
    
    if response == 'y':
        migrations = migrator.migrate_to_consolidated_structure()
        
        if migrations:
            print(f"\n=== Migration Summary ===")
            print(f"Successfully migrated {len(migrations)} files")
            
            # Cleanup empty directories
            migrator._cleanup_empty_directories()
        
        print("\nNext step: Update test discovery configurations")
    else:
        print("Migration cancelled.")
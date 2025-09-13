#!/usr/bin/env python3
"""
Script to implement standardized naming convention for test files.
Part of Task 1.3: Implement standardized naming convention
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


class TestFileStandardizer:
    """Handles standardization of test file names and organization."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        
        # Track renames for import statement updates
        self.renames_performed = []
        
    def standardize_naming_conventions(self):
        """Implement standardized naming conventions across all test files."""
        print("=== Implementing Standardized Test File Naming ===\n")
        
        # Phase 1: Fix the 7 identified non-compliant files
        self._fix_non_compliant_files()
        
        # Phase 2: Apply consistent suffixes where needed
        self._apply_naming_suffixes()
        
        print(f"\nCompleted naming standardization:")
        print(f"  - Files renamed: {len(self.renames_performed)}")
        
        return self.renames_performed
    
    def _fix_non_compliant_files(self):
        """Fix the 7 specifically identified non-compliant files."""
        print("Phase 1: Fixing non-compliant files...")
        
        # Files that need E2E suffix
        e2e_files = [
            ("tests/e2e_library/test_svg_test_library.py", "tests/e2e_library/test_svg_library_e2e.py"),
            ("tests/integration/test_comprehensive_e2e.py", "tests/e2e_integration/test_comprehensive_e2e.py"),  
            ("tests/integration/test_converter_specific_e2e.py", "tests/e2e_integration/test_converter_specific_e2e.py"),
            ("tests/integration/test_core_module_e2e.py", "tests/e2e_integration/test_core_module_e2e.py"),
        ]
        
        # Files that need visual suffix
        visual_files = [
            ("tests/visual/test_golden_standards.py", "tests/visual/test_golden_standards_visual.py"),
        ]
        
        # Create e2e_integration directory if needed
        e2e_integration_dir = self.tests_dir / "e2e_integration"
        if not e2e_integration_dir.exists():
            e2e_integration_dir.mkdir(parents=True)
            print(f"  Created directory: {e2e_integration_dir}")
            
            # Create __init__.py
            (e2e_integration_dir / "__init__.py").touch()
        
        # Rename E2E files and move to correct directory
        for old_path, new_path in e2e_files:
            self._rename_file(old_path, new_path)
        
        # Rename visual files
        for old_path, new_path in visual_files:
            self._rename_file(old_path, new_path)
    
    def _apply_naming_suffixes(self):
        """Apply consistent naming suffixes based on directory structure."""
        print("\nPhase 2: Applying naming suffixes...")
        
        suffix_mappings = {
            "e2e_api": "_e2e",
            "e2e_visual": "_e2e", 
            "e2e_library": "_e2e",
            "e2e_integration": "_e2e",
            "visual": "_visual",
            "benchmarks": "_benchmark"
        }
        
        for directory, suffix in suffix_mappings.items():
            self._apply_suffix_to_directory(directory, suffix)
    
    def _apply_suffix_to_directory(self, directory: str, suffix: str):
        """Apply naming suffix to all files in a directory."""
        dir_path = self.tests_dir / directory
        
        if not dir_path.exists():
            return
            
        for file_path in dir_path.glob("test_*.py"):
            if file_path.name == "__init__.py":
                continue
                
            # Check if file already has the suffix
            if not file_path.name.endswith(f"{suffix}.py"):
                # Generate new name with suffix
                base_name = file_path.stem  # removes .py
                if base_name.startswith("test_"):
                    # Insert suffix before .py
                    new_name = f"{base_name}{suffix}.py"
                    new_path = file_path.parent / new_name
                    
                    self._rename_file(str(file_path), str(new_path))
    
    def _rename_file(self, old_path: str, new_path: str):
        """Safely rename a file and track the change."""
        old_file = Path(old_path)
        new_file = Path(new_path)
        
        if not old_file.exists():
            print(f"  ⚠️  File not found: {old_path}")
            return False
            
        if new_file.exists():
            print(f"  ⚠️  Target already exists: {new_path}")
            return False
        
        # Ensure target directory exists
        new_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Perform the rename
        try:
            shutil.move(str(old_file), str(new_file))
            print(f"  ✅ Renamed: {old_file.name} -> {new_file.name}")
            
            # Track for import updates
            self.renames_performed.append((str(old_file), str(new_file)))
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to rename {old_path}: {e}")
            return False
    
    def generate_import_updates(self) -> List[Tuple[str, str]]:
        """Generate list of import statement updates needed."""
        import_updates = []
        
        for old_path, new_path in self.renames_performed:
            # Convert file paths to import statements
            old_import = self._path_to_import(old_path)
            new_import = self._path_to_import(new_path)
            
            if old_import and new_import:
                import_updates.append((old_import, new_import))
        
        return import_updates
    
    def _path_to_import(self, file_path: str) -> str:
        """Convert file path to import statement format."""
        path = Path(file_path)
        
        # Remove .py extension
        parts = list(path.parts)
        if parts[-1].endswith('.py'):
            parts[-1] = parts[-1][:-3]
        
        # Find tests directory and create relative import
        try:
            tests_index = parts.index('tests')
            import_parts = parts[tests_index:]
            return '.'.join(import_parts)
        except ValueError:
            return ""
    
    def preview_changes(self):
        """Preview what changes would be made without executing them."""
        print("=== Preview of Naming Changes ===\n")
        
        # Show non-compliant files that would be fixed
        non_compliant_files = [
            ("tests/e2e_library/test_svg_test_library.py", "test_svg_library_e2e.py"),
            ("tests/integration/test_comprehensive_e2e.py", "e2e_integration/test_comprehensive_e2e.py"),
            ("tests/integration/test_converter_specific_e2e.py", "e2e_integration/test_converter_specific_e2e.py"),
            ("tests/integration/test_core_module_e2e.py", "e2e_integration/test_core_module_e2e.py"),
            ("tests/visual/test_golden_standards.py", "test_golden_standards_visual.py"),
        ]
        
        print("Non-compliant files to be fixed:")
        for old_path, new_name in non_compliant_files:
            print(f"  {old_path} -> {new_name}")
        
        print(f"\nTotal files affected: {len(non_compliant_files)}")


if __name__ == "__main__":
    standardizer = TestFileStandardizer()
    
    # Show preview first
    standardizer.preview_changes()
    
    print("\n" + "="*50)
    response = input("Proceed with standardization? (y/N): ").strip().lower()
    
    if response == 'y':
        renames = standardizer.standardize_naming_conventions()
        
        if renames:
            import_updates = standardizer.generate_import_updates()
            
            print(f"\n=== Import Updates Needed ===")
            for old_import, new_import in import_updates:
                print(f"  {old_import} -> {new_import}")
                
            print(f"\nNext step: Update {len(import_updates)} import references")
    else:
        print("Standardization cancelled.")
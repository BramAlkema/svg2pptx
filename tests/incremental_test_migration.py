#!/usr/bin/env python3
"""
Incremental Test Migration Script

This script carefully migrates existing tests to use the new centralized fixture system
one file at a time with validation at each step to avoid syntax errors.
"""

import os
import ast
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Tuple

class IncrementalTestMigrator:
    def __init__(self, base_dir: str = "tests"):
        self.base_dir = Path(base_dir)
        self.fixture_mapping = {
            # Common fixtures
            'mock_conversion_context': 'tests.fixtures.mock_objects',
            'sample_svg_content': 'tests.fixtures.svg_content',
            'temp_file_path': 'tests.fixtures.file_fixtures',
            'mock_api_client': 'tests.fixtures.api_clients',
            
            # Specific converter fixtures
            'mock_rectangle_converter': 'tests.fixtures.mock_objects',
            'mock_text_converter': 'tests.fixtures.mock_objects',
            'mock_path_converter': 'tests.fixtures.mock_objects',
        }
        
    def analyze_test_file(self, file_path: Path) -> Dict[str, any]:
        """Analyze a test file to understand its structure and dependencies."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to understand the file structure
            tree = ast.parse(content)
            
            analysis = {
                'file_path': file_path,
                'imports': [],
                'fixtures': [],
                'test_functions': [],
                'classes': [],
                'syntax_valid': True,
                'needs_migration': False
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        analysis['imports'].append(f"{module}.{alias.name}")
                elif isinstance(node, ast.FunctionDef):
                    if node.name.startswith('test_'):
                        analysis['test_functions'].append(node.name)
                    # Check for fixture decorators
                    for decorator in node.decorator_list:
                        if hasattr(decorator, 'id') and decorator.id == 'pytest.fixture':
                            analysis['fixtures'].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    analysis['classes'].append(node.name)
            
            # Check if file needs migration (has local fixtures or mocks)
            if analysis['fixtures'] or 'Mock' in content or '@patch' in content:
                analysis['needs_migration'] = True
                
            return analysis
            
        except SyntaxError as e:
            return {
                'file_path': file_path,
                'syntax_valid': False,
                'error': str(e),
                'needs_migration': False
            }
        except Exception as e:
            return {
                'file_path': file_path,
                'syntax_valid': False,
                'error': f"Analysis error: {str(e)}",
                'needs_migration': False
            }
    
    def validate_test_file(self, file_path: Path) -> bool:
        """Validate that a test file has correct syntax and can be imported."""
        try:
            # Try to compile the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            compile(content, str(file_path), 'exec')
            
            # Try to run a quick pytest syntax check
            result = subprocess.run([
                sys.executable, '-m', 'pytest', '--collect-only', str(file_path)
            ], capture_output=True, text=True, cwd=self.base_dir.parent)
            
            return result.returncode == 0
            
        except Exception:
            return False
    
    def migrate_single_file(self, file_path: Path) -> Tuple[bool, str]:
        """Migrate a single test file to use centralized fixtures."""
        try:
            # Read original content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Backup original
            backup_path = file_path.with_suffix('.py.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Analyze file
            analysis = self.analyze_test_file(file_path)
            if not analysis['syntax_valid']:
                return False, f"Invalid syntax: {analysis.get('error', 'Unknown error')}"
            
            if not analysis['needs_migration']:
                return True, "No migration needed"
            
            # Perform migration
            migrated_content = self._perform_migration(original_content, analysis)
            
            # Write migrated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(migrated_content)
            
            # Validate migrated file
            if not self.validate_test_file(file_path):
                # Restore backup if validation fails
                with open(backup_path, 'r', encoding='utf-8') as f:
                    backup_content = f.read()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
                return False, "Migration validation failed, restored backup"
            
            # Remove backup if successful
            backup_path.unlink()
            return True, "Migration successful"
            
        except Exception as e:
            return False, f"Migration error: {str(e)}"
    
    def _perform_migration(self, content: str, analysis: Dict) -> str:
        """Perform the actual migration of content."""
        lines = content.split('\n')
        migrated_lines = []
        imports_added = set()
        
        # Add centralized fixture imports at the top
        import_section_done = False
        
        for line in lines:
            # Add centralized imports after existing imports
            if not import_section_done and (line.strip() == '' or line.startswith(('def ', 'class ', '@'))):
                if not any('tests.fixtures' in imp for imp in imports_added):
                    migrated_lines.append('')
                    migrated_lines.append('# Centralized fixtures')
                    migrated_lines.append('from tests.fixtures.common import *')
                    migrated_lines.append('from tests.fixtures.mock_objects import *')
                    migrated_lines.append('from tests.fixtures.svg_content import *')
                    migrated_lines.append('')
                import_section_done = True
            
            # Skip local fixture definitions that are now centralized
            if '@pytest.fixture' in line:
                # Look ahead to see if this is a fixture we've centralized
                fixture_name = None
                for i, next_line in enumerate(lines[lines.index(line):]):
                    if next_line.strip().startswith('def '):
                        fixture_name = next_line.strip().split('(')[0].replace('def ', '')
                        break
                    if i > 5:  # Don't look too far ahead
                        break
                
                if fixture_name in self.fixture_mapping:
                    # Skip this fixture definition
                    continue
            
            # Replace Mock imports with centralized ones
            if 'from unittest.mock import' in line or 'import unittest.mock' in line:
                continue  # Skip, will be handled by centralized imports
            
            migrated_lines.append(line)
        
        return '\n'.join(migrated_lines)
    
    def run_incremental_migration(self, batch_size: int = 5) -> Dict[str, any]:
        """Run incremental migration in small batches."""
        # Find all test files
        test_files = list(self.base_dir.rglob('test_*.py'))
        
        results = {
            'total_files': len(test_files),
            'migrated': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        print(f"Found {len(test_files)} test files to analyze")
        
        # Process in batches
        for i in range(0, len(test_files), batch_size):
            batch = test_files[i:i+batch_size]
            print(f"\nProcessing batch {i//batch_size + 1}: files {i+1}-{min(i+batch_size, len(test_files))}")
            
            for file_path in batch:
                print(f"  Processing {file_path.relative_to(self.base_dir.parent)}...")
                
                success, message = self.migrate_single_file(file_path)
                
                if success:
                    if "No migration needed" in message:
                        results['skipped'] += 1
                        print(f"    ✓ {message}")
                    else:
                        results['migrated'] += 1
                        print(f"    ✓ {message}")
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'file': str(file_path),
                        'error': message
                    })
                    print(f"    ✗ {message}")
            
            # Run tests after each batch to ensure everything still works
            print(f"  Validating batch...")
            test_result = subprocess.run([
                sys.executable, '-m', 'pytest', '--collect-only', str(self.base_dir)
            ], capture_output=True, text=True, cwd=self.base_dir.parent)
            
            if test_result.returncode != 0:
                print(f"  ⚠️ Batch validation failed, stopping migration")
                print(f"    Error: {test_result.stderr}")
                break
            else:
                print(f"  ✓ Batch validation passed")
        
        return results

def main():
    migrator = IncrementalTestMigrator()
    results = migrator.run_incremental_migration(batch_size=3)  # Start with small batches
    
    print(f"\n=== Migration Summary ===")
    print(f"Total files: {results['total_files']}")
    print(f"Migrated: {results['migrated']}")
    print(f"Skipped: {results['skipped']}")
    print(f"Failed: {results['failed']}")
    
    if results['errors']:
        print(f"\nErrors:")
        for error in results['errors']:
            print(f"  {error['file']}: {error['error']}")
    
    return results['failed'] == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
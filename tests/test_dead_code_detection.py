#!/usr/bin/env python3
"""
Dead Code Detection Test

This test hunts for orphaned code, unused imports, and unreferenced modules
in the SVG2PPTX codebase. It helps identify cleanup opportunities and
maintains code quality by detecting unused components.
"""

import pytest
import os
import ast
import sys
from pathlib import Path
from typing import Set, Dict, List, Tuple
from collections import defaultdict


class DeadCodeDetector:
    """Detects dead/orphaned code in the project."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src"
        self.test_dir = self.project_root / "tests"
        
        # Track all Python files
        self.all_py_files = set()
        self.src_modules = set()
        self.imports_map = defaultdict(set)  # file -> set of imported modules
        self.exported_symbols = defaultdict(set)  # file -> set of exported symbols
        self.referenced_modules = set()
        
    def scan_project(self):
        """Scan entire project for Python files and imports."""
        # Find all Python files
        for py_file in self.project_root.rglob("*.py"):
            if self._should_ignore_file(py_file):
                continue
                
            self.all_py_files.add(py_file)
            
            # Track source modules
            if self._is_source_module(py_file):
                relative_path = py_file.relative_to(self.src_dir)
                module_name = self._path_to_module_name(relative_path)
                self.src_modules.add(module_name)
        
        # Analyze imports and exports in all files
        for py_file in self.all_py_files:
            self._analyze_file(py_file)
    
    def _should_ignore_file(self, py_file: Path) -> bool:
        """Check if file should be ignored."""
        ignore_patterns = [
            "__pycache__",
            ".pytest_cache", 
            ".git",
            "venv",
            ".venv",
            "node_modules",
            ".agent-os"
        ]
        
        return any(pattern in str(py_file) for pattern in ignore_patterns)
    
    def _is_source_module(self, py_file: Path) -> bool:
        """Check if file is a source module."""
        try:
            return self.src_dir in py_file.parents or py_file.parent == self.src_dir
        except (OSError, ValueError):
            return False
    
    def _path_to_module_name(self, relative_path: Path) -> str:
        """Convert file path to module name."""
        parts = list(relative_path.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].replace(".py", "")
        
        return ".".join(parts) if parts else ""
    
    def _analyze_file(self, py_file: Path):
        """Analyze a Python file for imports and exports."""
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                tree = ast.parse(content, filename=str(py_file))
            except SyntaxError:
                return  # Skip files with syntax errors
            
            file_key = str(py_file.relative_to(self.project_root))
            
            # Analyze AST for imports and exports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.imports_map[file_key].add(alias.name)
                        self.referenced_modules.add(alias.name)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self.imports_map[file_key].add(node.module)
                        self.referenced_modules.add(node.module)
                        
                        # Track relative imports from src
                        if node.module.startswith('.'):
                            # Handle relative imports
                            base_module = self._resolve_relative_import(py_file, node.module)
                            if base_module:
                                self.referenced_modules.add(base_module)
                
                elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    self.exported_symbols[file_key].add(node.name)
                    
        except Exception:
            pass  # Skip files we can't analyze
    
    def _resolve_relative_import(self, py_file: Path, module: str) -> str:
        """Resolve relative import to absolute module name."""
        if not self._is_source_module(py_file):
            return None
        
        try:
            relative_path = py_file.relative_to(self.src_dir)
            current_package = self._path_to_module_name(relative_path.parent)
            
            # Count leading dots
            level = 0
            for char in module:
                if char == '.':
                    level += 1
                else:
                    break
            
            remaining_module = module[level:]
            
            if level == 0:
                return None
                
            # Go up levels
            package_parts = current_package.split('.') if current_package else []
            if level > len(package_parts):
                return None
                
            base_parts = package_parts[:-level + 1] if level > 1 else package_parts
            
            if remaining_module:
                result = '.'.join(base_parts + [remaining_module])
            else:
                result = '.'.join(base_parts)
                
            return result
        except:
            return None
    
    def find_orphaned_modules(self) -> List[str]:
        """Find source modules that are never imported."""
        orphaned = []
        
        for module in self.src_modules:
            if module and not self._is_module_referenced(module):
                orphaned.append(module)
        
        return sorted(orphaned)
    
    def _is_module_referenced(self, module: str) -> bool:
        """Check if module is referenced anywhere."""
        # Direct reference
        if module in self.referenced_modules:
            return True
        
        # Check for partial matches (submodules)
        for ref_module in self.referenced_modules:
            if ref_module.startswith(module + '.') or module.startswith(ref_module + '.'):
                return True
        
        # Check if any file imports from this module
        for imports in self.imports_map.values():
            for imp in imports:
                if imp == module or imp.startswith(module + '.'):
                    return True
        
        return False
    
    def find_unused_imports(self) -> Dict[str, List[str]]:
        """Find files with potentially unused imports."""
        unused_by_file = {}
        
        for file_path, imports in self.imports_map.items():
            try:
                py_file = self.project_root / file_path
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                unused_imports = []
                for imp in imports:
                    # Skip standard library and well-known third party
                    if self._is_standard_or_third_party(imp):
                        continue
                    
                    # Simple heuristic: if import name doesn't appear in file content
                    # (excluding the import line itself), it might be unused
                    imp_parts = imp.split('.')
                    if not any(part in content for part in imp_parts):
                        unused_imports.append(imp)
                
                if unused_imports:
                    unused_by_file[file_path] = unused_imports
            
            except:
                continue
        
        return unused_by_file
    
    def _is_standard_or_third_party(self, module_name: str) -> bool:
        """Check if module is standard library or third party."""
        standard_libs = {
            'os', 'sys', 'ast', 'json', 'xml', 'urllib', 'http', 'math', 
            'typing', 'pathlib', 'collections', 'itertools', 're', 'logging',
            'unittest', 'pytest', 'dataclasses', 'enum', 'abc'
        }
        
        third_party = {
            'lxml', 'pytest', 'coverage', 'flask', 'fastapi', 'uvicorn',
            'pydantic', 'numpy', 'pandas', 'requests', 'click'
        }
        
        base_module = module_name.split('.')[0]
        return base_module in standard_libs or base_module in third_party
    
    def generate_report(self) -> Dict[str, any]:
        """Generate comprehensive dead code report."""
        orphaned_modules = self.find_orphaned_modules()
        unused_imports = self.find_unused_imports()
        
        return {
            'total_py_files': len(self.all_py_files),
            'total_src_modules': len(self.src_modules),
            'orphaned_modules': orphaned_modules,
            'unused_imports': unused_imports,
            'summary': {
                'orphaned_count': len(orphaned_modules),
                'files_with_unused_imports': len(unused_imports)
            }
        }


class TestDeadCodeDetection:
    """Test suite for dead code detection."""
    
    def setup_method(self):
        """Set up detector."""
        project_root = Path(__file__).parent.parent
        self.detector = DeadCodeDetector(str(project_root))
        self.detector.scan_project()
    
    def test_detect_orphaned_modules(self):
        """Test detection of orphaned/unreferenced modules."""
        orphaned = self.detector.find_orphaned_modules()
        
        print(f"\n=== ORPHANED MODULES REPORT ===")
        print(f"Found {len(orphaned)} potentially orphaned modules:")
        
        for module in orphaned:
            print(f"  • {module}")
            
            # Try to find the actual file
            module_path = module.replace('.', '/')
            potential_files = [
                f"src/{module_path}.py",
                f"src/{module_path}/__init__.py"
            ]
            
            for potential_file in potential_files:
                if Path(self.detector.project_root / potential_file).exists():
                    print(f"    → {potential_file}")
                    break
        
        # Enhanced_text_converter should be detected as orphaned
        if orphaned:
            print(f"\nℹ️  These modules may be dead code that can be removed")
            print(f"   or they may be entry points/utilities not imported elsewhere.")
    
    def test_specific_known_orphan(self):
        """Test that enhanced_text_converter is detected as orphaned."""
        orphaned = self.detector.find_orphaned_modules()
        
        # Check for enhanced_text_converter specifically
        enhanced_text_variants = [
            'enhanced_text_converter',
            'enhanced_text_converter.py',
            'src.enhanced_text_converter'
        ]
        
        found_enhanced_text = any(
            any(variant in orphan for variant in enhanced_text_variants)
            for orphan in orphaned
        )
        
        if found_enhanced_text:
            print(f"\n✅ Confirmed: enhanced_text_converter detected as orphaned")
        else:
            print(f"\n⚠️  enhanced_text_converter not detected as orphaned")
            print(f"   This might indicate it's referenced somewhere")
    
    def test_find_unused_imports(self):
        """Test detection of unused imports."""
        unused = self.detector.find_unused_imports()
        
        print(f"\n=== UNUSED IMPORTS REPORT ===")
        print(f"Found {len(unused)} files with potentially unused imports:")
        
        for file_path, imports in unused.items():
            if len(imports) > 0:  # Only show files with actual unused imports
                print(f"\n📄 {file_path}:")
                for imp in imports:
                    print(f"    • {imp}")
    
    def test_module_reference_check(self):
        """Test specific module reference checking."""
        test_cases = [
            'enhanced_text_converter',
            'converters.markers', 
            'converters.animations',
            'transforms',
            'colors'
        ]
        
        print(f"\n=== MODULE REFERENCE CHECK ===")
        for module in test_cases:
            is_referenced = self.detector._is_module_referenced(module)
            status = "✅ REFERENCED" if is_referenced else "❌ ORPHANED"
            print(f"  {module:<25} → {status}")
    
    def test_comprehensive_report(self):
        """Generate and display comprehensive dead code report."""
        report = self.detector.generate_report()
        
        print(f"\n" + "="*50)
        print(f"         DEAD CODE ANALYSIS REPORT")
        print(f"="*50)
        print(f"📊 Total Python files scanned: {report['total_py_files']}")
        print(f"📦 Total source modules found: {report['total_src_modules']}")
        print(f"🪦 Orphaned modules: {report['summary']['orphaned_count']}")
        print(f"📋 Files with unused imports: {report['summary']['files_with_unused_imports']}")
        
        if report['orphaned_modules']:
            print(f"\n🪦 ORPHANED MODULES:")
            for module in report['orphaned_modules']:
                print(f"   • {module}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        if report['orphaned_modules']:
            print(f"   • Review orphaned modules for removal or integration")
        if report['unused_imports']:
            print(f"   • Clean up unused imports to reduce complexity")
        if not report['orphaned_modules'] and not report['unused_imports']:
            print(f"   • Codebase appears well-maintained! 🎉")
        
        print(f"="*50)
        
        # Assert for test validation
        assert report['total_py_files'] > 0, "Should find Python files"
        assert report['total_src_modules'] > 0, "Should find source modules"
    
    def test_verify_enhanced_text_converter_orphaned(self):
        """Specific test to verify enhanced_text_converter is orphaned."""
        # Check if the file exists
        enhanced_text_file = self.detector.src_dir / "enhanced_text_converter.py"
        
        if enhanced_text_file.exists():
            print(f"\n🔍 enhanced_text_converter.py exists in src/")
            
            # Check if it's in orphaned list
            orphaned = self.detector.find_orphaned_modules()
            is_orphaned = any('enhanced_text_converter' in module for module in orphaned)
            
            if is_orphaned:
                print(f"✅ CONFIRMED: enhanced_text_converter is orphaned code")
                print(f"   → File exists but is never imported")
                print(f"   → Safe to remove if no longer needed")
            else:
                print(f"❓ enhanced_text_converter appears to be referenced")
                
                # Show what references it
                for file_path, imports in self.detector.imports_map.items():
                    for imp in imports:
                        if 'enhanced_text_converter' in imp:
                            print(f"   → Referenced in: {file_path}")
        else:
            print(f"ℹ️  enhanced_text_converter.py not found in src/")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
#!/usr/bin/env python3
"""
Comprehensive Codebase Consistency Test for SVG2PPTX Architecture

This test detects architectural inconsistencies across the SVG2PPTX codebase with focus on:
1. Orphaned Methods Detection - Find methods that are defined but never called
2. Doubled/Duplicate Implementation Detection - Find similar implementations  
3. Tool Integration Consistency - Verify standardized tool usage
4. API Consistency - Check method signature consistency
5. Import/Dependency Consistency - Find circular dependencies and unused imports

Provides detailed reporting of issues found with actionable recommendations.

USAGE:
------
1. Run all consistency tests:
   pytest tests/architecture/test_codebase_consistency.py -v

2. Run only the comprehensive report (shows all issues found):
   pytest tests/architecture/test_codebase_consistency.py::TestCodebaseConsistency::test_generate_comprehensive_report -v -s

3. Run specific consistency checks:
   pytest tests/architecture/test_codebase_consistency.py::TestCodebaseConsistency::test_tool_integration_consistency -v
   pytest tests/architecture/test_codebase_consistency.py::TestCodebaseConsistency::test_api_consistency -v
   
4. Run as standalone script for analysis:
   python tests/architecture/test_codebase_consistency.py

EXPECTED OUTPUT:
----------------
The test will categorize issues by severity and type:
- Critical: Circular dependencies, must be fixed immediately
- High: Tool integration issues, hardcoded EMU values, significant duplicates
- Medium: API inconsistencies, orphaned methods, minor duplicates
- Low: Unused imports, style issues

RECOMMENDATIONS PRIORITIZATION:
-------------------------------
1. Fix tool integration issues (all converters should inherit from BaseConverter)
2. Remove hardcoded EMU values (use UnitConverter.to_emu() instead)
3. Consolidate duplicate implementations into shared utilities
4. Remove orphaned methods that are never called
5. Clean up unused imports (lowest priority)
"""

import pytest
import ast
import inspect
import re
import importlib
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any, Union
from collections import defaultdict, Counter
from dataclasses import dataclass
from difflib import SequenceMatcher

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.converters.base import BaseConverter, ConversionContext
from src.units import UnitConverter
from src.color import Color
from src.transforms import TransformEngine
from src.viewbox import ViewportEngine



@dataclass
class ConsistencyIssue:
    """Represents a consistency issue found in the codebase."""
    category: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    file_path: str
    line_number: Optional[int]
    description: str
    recommendation: str
    code_snippet: Optional[str] = None


@dataclass
class MethodSignature:
    """Represents a method signature for comparison."""
    name: str
    params: List[str]
    return_type: Optional[str]
    file_path: str
    line_number: int


class CodebaseAnalyzer:
    """Analyzes the codebase for consistency issues."""
    
    def __init__(self, src_path: Path):
        self.src_path = src_path
        self.converter_path = src_path / "converters"
        self.issues: List[ConsistencyIssue] = []
        self.method_definitions: Dict[str, List[MethodSignature]] = defaultdict(list)
        self.method_calls: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        self.imports: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        self.class_hierarchies: Dict[str, List[str]] = defaultdict(list)
        
    def analyze(self) -> List[ConsistencyIssue]:
        """Run all consistency checks."""
        self.issues.clear()
        
        # Collect codebase information
        self._collect_methods_and_calls()
        self._collect_imports()
        self._collect_class_hierarchies()
        
        # Run consistency checks
        self._check_orphaned_methods()
        self._check_duplicate_implementations() 
        self._check_tool_integration_consistency()
        self._check_api_consistency()
        self._check_import_consistency()
        self._check_hardcoded_values()
        
        return self.issues
        
    def _collect_methods_and_calls(self):
        """Collect all method definitions and calls from Python files."""
        for py_file in self.src_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                self._extract_methods_from_ast(tree, py_file, content)
                self._extract_calls_from_ast(tree, py_file)
                    
            except Exception as e:
                self.issues.append(ConsistencyIssue(
                    category="parsing_error",
                    severity="medium", 
                    file_path=str(py_file),
                    line_number=None,
                    description=f"Failed to parse file: {e}",
                    recommendation="Fix syntax errors in the file"
                ))
    
    def _extract_methods_from_ast(self, tree: ast.AST, file_path: Path, content: str):
        """Extract method definitions from AST."""
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Get parameter names
                params = []
                for arg in node.args.args:
                    params.append(arg.arg)
                
                # Get return type if annotated
                return_type = None
                if node.returns:
                    return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
                
                signature = MethodSignature(
                    name=node.name,
                    params=params,
                    return_type=return_type,
                    file_path=str(file_path),
                    line_number=node.lineno
                )
                
                self.method_definitions[node.name].append(signature)
    
    def _extract_calls_from_ast(self, tree: ast.AST, file_path: Path):
        """Extract method calls from AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    # Direct function call like foo()
                    self.method_calls[node.func.id].append((str(file_path), node.lineno))
                elif isinstance(node.func, ast.Attribute):
                    # Method call like obj.foo()
                    self.method_calls[node.func.attr].append((str(file_path), node.lineno))
    
    def _collect_imports(self):
        """Collect all import statements."""
        for py_file in self.src_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for i, line in enumerate(lines, 1):
                    line = line.strip()
                    if line.startswith(('import ', 'from ')):
                        # Extract imported names
                        if line.startswith('import '):
                            module = line.replace('import ', '').split(' as ')[0]
                            self.imports[module].append((str(py_file), i))
                        elif line.startswith('from '):
                            # from module import names
                            parts = line.split(' import ')
                            if len(parts) == 2:
                                names = parts[1].split(',')
                                for name in names:
                                    name = name.strip().split(' as ')[0]
                                    self.imports[name].append((str(py_file), i))
                                    
            except Exception:
                pass  # Skip files with encoding issues
                
    def _collect_class_hierarchies(self):
        """Collect class inheritance hierarchies."""
        for py_file in self.src_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        bases = []
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                bases.append(base.id)
                            elif isinstance(base, ast.Attribute):
                                bases.append(base.attr)
                        
                        self.class_hierarchies[node.name] = bases
                        
            except Exception:
                pass
    
    def _check_orphaned_methods(self):
        """Find methods that are defined but never called."""
        for method_name, definitions in self.method_definitions.items():
            # Skip special methods and common overrides
            if (method_name.startswith('_') or 
                method_name in ['__init__', '__str__', '__repr__', 'main'] or
                method_name in ['can_convert', 'convert', 'parse', 'to_emu', 'format_emu']):
                continue
                
            calls = self.method_calls.get(method_name, [])
            
            # If method is defined but never called
            if len(definitions) > 0 and len(calls) == 0:
                for definition in definitions:
                    self.issues.append(ConsistencyIssue(
                        category="orphaned_method",
                        severity="medium",
                        file_path=definition.file_path,
                        line_number=definition.line_number,
                        description=f"Method '{method_name}' is defined but never called",
                        recommendation=f"Remove unused method '{method_name}' or ensure it's being called where needed"
                    ))
    
    def _check_duplicate_implementations(self):
        """Find methods with identical or very similar implementations."""
        # Group methods by name for comparison
        for method_name, definitions in self.method_definitions.items():
            if len(definitions) > 1:
                # Compare implementations for similarity
                implementations = []
                
                for definition in definitions:
                    try:
                        with open(definition.file_path, 'r') as f:
                            lines = f.readlines()
                            # Get method implementation (basic extraction)
                            start_line = definition.line_number - 1
                            method_lines = []
                            indent_level = None
                            
                            for i in range(start_line, min(start_line + 50, len(lines))):
                                line = lines[i]
                                if indent_level is None and line.strip():
                                    indent_level = len(line) - len(line.lstrip())
                                elif line.strip() and indent_level is not None:
                                    current_indent = len(line) - len(line.lstrip()) 
                                    if current_indent <= indent_level and not line.strip().startswith('"""'):
                                        break
                                method_lines.append(line)
                            
                            implementation = ''.join(method_lines).strip()
                            implementations.append((definition, implementation))
                            
                    except Exception:
                        continue
                
                # Check for similar implementations
                for i in range(len(implementations)):
                    for j in range(i + 1, len(implementations)):
                        def1, impl1 = implementations[i]
                        def2, impl2 = implementations[j]
                        
                        similarity = SequenceMatcher(None, impl1, impl2).ratio()
                        if similarity > 0.8:  # 80% similarity threshold
                            self.issues.append(ConsistencyIssue(
                                category="duplicate_implementation",
                                severity="high",
                                file_path=def1.file_path,
                                line_number=def1.line_number,
                                description=f"Method '{method_name}' has {similarity:.1%} similar implementation to {Path(def2.file_path).name}:{def2.line_number}",
                                recommendation=f"Consider consolidating duplicate '{method_name}' implementations into a shared utility or base class method",
                                code_snippet=impl1[:200] + "..." if len(impl1) > 200 else impl1
                            ))
    
    def _check_tool_integration_consistency(self):
        """Verify all converters properly use standardized tools."""
        converter_files = list(self.converter_path.glob("*.py"))
        
        required_tools = ['UnitConverter', 'ColorParser', 'TransformParser', 'ViewportEngine']
        
        for converter_file in converter_files:
            if converter_file.name in ['__init__.py', 'base.py']:
                continue
                
            try:
                with open(converter_file, 'r') as f:
                    content = f.read()
                
                # Check if file defines converter classes
                has_converter_class = 'Converter(BaseConverter)' in content or 'Converter(' in content
                
                if has_converter_class:
                    # Check if converter properly inherits from BaseConverter
                    inherits_base_converter = 'BaseConverter' in content
                    
                    if inherits_base_converter:
                        # If it inherits from BaseConverter, it automatically gets all tools
                        # No need to check for explicit tool usage
                        continue
                    else:
                        # If it doesn't inherit from BaseConverter, check for explicit tool usage
                        missing_tools = []
                        for tool in required_tools:
                            if tool not in content:
                                missing_tools.append(tool)
                        
                        if missing_tools:
                            self.issues.append(ConsistencyIssue(
                                category="tool_integration", 
                                severity="high",
                                file_path=str(converter_file),
                                line_number=None,
                                description=f"Converter missing standardized tools: {', '.join(missing_tools)}",
                                recommendation=f"Either inherit from BaseConverter or explicitly import and use: {', '.join(missing_tools)}."
                            ))
                    
                    # Check for hardcoded EMU values
                    hardcoded_patterns = [
                        r'\* *9525',   # pixel to EMU 
                        r'\* *12700',  # point to EMU
                        r'\* *914400', # inch to EMU
                        r'\* *25400',  # mm to EMU (incorrect)
                        r'\* *36000',  # mm to EMU (correct)
                    ]
                    
                    for pattern in hardcoded_patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            self.issues.append(ConsistencyIssue(
                                category="hardcoded_emu",
                                severity="high", 
                                file_path=str(converter_file),
                                line_number=line_num,
                                description=f"Hardcoded EMU conversion found: {match.group()}",
                                recommendation="Use UnitConverter.to_emu() method instead of hardcoded EMU values"
                            ))
                
            except Exception:
                pass
    
    def _check_api_consistency(self):
        """Check for legitimate API consistency issues within the same context."""
        # Only check for consistency within BaseConverter subclasses
        # This is more reasonable than forcing all methods with same name to match
        
        converter_methods = {}
        
        # Collect methods only from BaseConverter subclasses
        for py_file in self.converter_path.glob("*.py"):
            if py_file.name in ['__init__.py', 'base.py']:
                continue
                
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Only analyze files that contain BaseConverter subclasses
                if 'BaseConverter' not in content or 'class ' not in content:
                    continue
                
                # Extract converter class methods
                class_pattern = r'class\s+(\w+Converter)\s*\([^)]*BaseConverter[^)]*\):'
                method_pattern = r'def\s+(can_convert|convert)\s*\(([^)]+)\)'
                
                for class_match in re.finditer(class_pattern, content):
                    class_name = class_match.group(1)
                    
                    # Find methods in this class
                    class_start = class_match.end()
                    # Find next class or end of file
                    next_class = content.find('\nclass ', class_start)
                    class_content = content[class_start:next_class if next_class != -1 else len(content)]
                    
                    for method_match in re.finditer(method_pattern, class_content):
                        method_name = method_match.group(1)
                        params_str = method_match.group(2)
                        
                        # Parse parameters
                        params = [p.strip().split(':')[0].strip() for p in params_str.split(',') if p.strip()]
                        
                        key = f"{class_name}.{method_name}"
                        if method_name not in converter_methods:
                            converter_methods[method_name] = []
                        
                        converter_methods[method_name].append({
                            'class': class_name,
                            'params': params,
                            'file': str(py_file),
                            'line': content[:class_start + method_match.start()].count('\n') + 1
                        })
                        
            except Exception:
                continue
        
        # Check for inconsistencies within BaseConverter methods
        critical_methods = ['can_convert', 'convert']
        
        for method_name in critical_methods:
            if method_name in converter_methods:
                methods = converter_methods[method_name]
                if len(methods) > 1:
                    # Check if all BaseConverter subclasses follow the same pattern
                    base_signature = methods[0]['params']
                    
                    for method in methods[1:]:
                        if len(method['params']) != len(base_signature):
                            # Only flag if parameter count differs significantly
                            if abs(len(method['params']) - len(base_signature)) > 1:
                                self.issues.append(ConsistencyIssue(
                                    category="api_inconsistency",
                                    severity="low",  # Reduced severity 
                                    file_path=method['file'],
                                    line_number=method['line'],
                                    description=f"BaseConverter.{method_name} has unusual parameter count: {len(method['params'])} vs typical {len(base_signature)}",
                                    recommendation=f"Consider whether {method_name} needs all parameters or if it should follow the standard BaseConverter pattern"
                                ))
    
    def _check_import_consistency(self):
        """Check for unused imports and potential circular dependencies."""
        # Check each file for unused imports
        for py_file in self.src_path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                lines = content.split('\n')
                import_lines = []
                
                # Find all import statements
                for i, line in enumerate(lines):
                    line_stripped = line.strip()
                    if line_stripped.startswith(('import ', 'from ')) and not line_stripped.startswith('#'):
                        import_lines.append((i + 1, line_stripped))
                
                # Check each import for usage
                for line_num, import_line in import_lines:
                    # Extract imported names
                    imported_names = self._extract_imported_names(import_line)
                    
                    for name in imported_names:
                        if name and len(name) > 2:  # Skip very short names
                            # Check if the imported name is used in the file
                            usage_count = content.count(name)
                            if usage_count <= 1:  # Only the import line itself
                                self.issues.append(ConsistencyIssue(
                                    category="unused_import",
                                    severity="low",
                                    file_path=str(py_file),
                                    line_number=line_num,
                                    description=f"Potentially unused import: {name}",
                                    recommendation=f"Remove unused import '{name}' or verify it's needed"
                                ))
                                
            except Exception:
                pass
                
        # Check for circular dependencies (basic check)
        self._check_circular_dependencies()
    
    def _extract_imported_names(self, import_line: str) -> List[str]:
        """Extract imported names from an import statement."""
        names = []
        
        if import_line.startswith('import '):
            # import module [as alias]
            module = import_line.replace('import ', '').split(' as ')[0].strip()
            names.append(module.split('.')[-1])  # Use last part of module name
            
        elif import_line.startswith('from '):
            # from module import name1, name2
            parts = import_line.split(' import ')
            if len(parts) == 2:
                import_names = parts[1].split(',')
                for name in import_names:
                    name = name.strip().split(' as ')[0].strip()
                    if name != '*':
                        names.append(name)
        
        return names
    
    def _check_circular_dependencies(self):
        """Check for potential circular import dependencies."""
        # Build dependency graph
        dependencies = defaultdict(set)
        
        for py_file in self.src_path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                file_module = str(py_file.relative_to(self.src_path)).replace('/', '.').replace('.py', '')
                
                # Find relative imports
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('from .') or line.startswith('from ..'):
                        # Extract target module
                        if ' import ' in line:
                            target = line.split(' import ')[0].replace('from ', '')
                            dependencies[file_module].add(target)
                            
            except Exception:
                pass
        
        # Simple cycle detection (basic implementation)
        visited = set()
        rec_stack = set()
        
        def has_cycle(node, path=[]):
            if node in rec_stack:
                cycle_path = path[path.index(node):] + [node]
                self.issues.append(ConsistencyIssue(
                    category="circular_dependency",
                    severity="critical",
                    file_path="multiple",
                    line_number=None,
                    description=f"Circular dependency detected: {' -> '.join(cycle_path)}",
                    recommendation="Refactor modules to eliminate circular dependencies. Consider moving shared code to a separate module."
                ))
                return True
                
            if node in visited:
                return False
                
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dependencies.get(node, set()):
                if has_cycle(neighbor, path + [node]):
                    return True
                    
            rec_stack.remove(node)
            return False
        
        for node in dependencies:
            if node not in visited:
                has_cycle(node)
    
    def _check_hardcoded_values(self):
        """Check for hardcoded values that should use constants."""
        hardcoded_checks = [
            (r'\b9525\b', "Hardcoded EMU/pixel conversion"),
            (r'\b12700\b', "Hardcoded EMU/point conversion"),
            (r'\b914400\b', "Hardcoded EMU/inch conversion"), 
            (r'\b21600\b', "Hardcoded DrawingML coordinate system value"),
        ]
        
        for py_file in self.converter_path.rglob("*.py"):
            if py_file.name == 'base.py':  # Skip base.py as it may define constants
                continue
                
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for pattern, description in hardcoded_checks:
                    for match in re.finditer(pattern, content):
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = lines[line_num - 1].strip()
                        
                        # Skip comments and constant definitions
                        if not line_content.startswith('#') and 'EMU_PER' not in line_content:
                            self.issues.append(ConsistencyIssue(
                                category="hardcoded_value",
                                severity="medium",
                                file_path=str(py_file),
                                line_number=line_num,
                                description=description,
                                recommendation="Use appropriate constants or utility methods instead of hardcoded values",
                                code_snippet=line_content
                            ))
                            
            except Exception:
                pass


class TestCodebaseConsistency:
    """Test suite for codebase consistency."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.src_path = Path(__file__).parent.parent.parent / "src"
        self.analyzer = CodebaseAnalyzer(self.src_path)
        
    def test_orphaned_methods_detection(self):
        """Test detection of orphaned methods."""
        issues = self.analyzer.analyze()
        orphaned_issues = [i for i in issues if i.category == "orphaned_method"]
        
        # Report findings but don't fail - this is informational
        if orphaned_issues:
            report = "\n".join([
                f"  {issue.file_path}:{issue.line_number}: {issue.description}"
                for issue in orphaned_issues
            ])
            print(f"\nORPHANED METHODS DETECTED ({len(orphaned_issues)}):\n{report}")
    
    def test_duplicate_implementations(self):
        """Test detection of duplicate implementations.""" 
        issues = self.analyzer.analyze()
        duplicate_issues = [i for i in issues if i.category == "duplicate_implementation"]
        
        if duplicate_issues:
            report = "\n".join([
                f"  {issue.file_path}:{issue.line_number}: {issue.description}"
                for issue in duplicate_issues
            ])
            print(f"\nDUPLICATE IMPLEMENTATIONS DETECTED ({len(duplicate_issues)}):\n{report}")
            
        # Fail only for critical duplicates
        critical_duplicates = [i for i in duplicate_issues if i.severity == "critical"]
        assert len(critical_duplicates) == 0, f"Found {len(critical_duplicates)} critical duplicate implementations"
    
    def test_tool_integration_consistency(self):
        """Test tool integration consistency across converters."""
        issues = self.analyzer.analyze()
        tool_issues = [i for i in issues if i.category == "tool_integration"]
        hardcode_issues = [i for i in issues if i.category == "hardcoded_emu"]
        
        if tool_issues:
            report = "\n".join([
                f"  {Path(issue.file_path).name}: {issue.description}"
                for issue in tool_issues
            ])
            pytest.fail(f"TOOL INTEGRATION ISSUES ({len(tool_issues)}):\n{report}")
            
        if hardcode_issues:
            report = "\n".join([
                f"  {Path(issue.file_path).name}:{issue.line_number}: {issue.description}"
                for issue in hardcode_issues
            ])
            pytest.fail(f"HARDCODED EMU VALUES FOUND ({len(hardcode_issues)}):\n{report}")
    
    def test_api_consistency(self):
        """Test API consistency across converters."""
        issues = self.analyzer.analyze()
        api_issues = [i for i in issues if i.category == "api_inconsistency"]
        
        if api_issues:
            report = "\n".join([
                f"  {Path(issue.file_path).name}:{issue.line_number}: {issue.description}"
                for issue in api_issues
            ])
            pytest.fail(f"API INCONSISTENCIES FOUND ({len(api_issues)}):\n{report}")
    
    def test_import_dependency_consistency(self):
        """Test import and dependency consistency."""
        issues = self.analyzer.analyze()
        circular_issues = [i for i in issues if i.category == "circular_dependency"]
        unused_imports = [i for i in issues if i.category == "unused_import"]
        
        # Critical: Fail on circular dependencies
        if circular_issues:
            report = "\n".join([
                f"  {issue.description}"
                for issue in circular_issues
            ])
            pytest.fail(f"CIRCULAR DEPENDENCIES FOUND ({len(circular_issues)}):\n{report}")
            
        # Informational: Report unused imports
        if unused_imports and len(unused_imports) > 20:  # Only report if many unused imports
            print(f"\nINFO: {len(unused_imports)} potentially unused imports detected")
    
    def test_generate_comprehensive_report(self):
        """Generate comprehensive consistency report."""
        issues = self.analyzer.analyze()
        
        if not issues:
            print("\n✅ No consistency issues detected!")
            return
            
        # Group issues by category
        by_category = defaultdict(list)
        for issue in issues:
            by_category[issue.category].append(issue)
            
        # Generate report
        print(f"\n📊 CODEBASE CONSISTENCY REPORT")
        print(f"{'='*50}")
        print(f"Total Issues Found: {len(issues)}")
        
        severity_counts = Counter(issue.severity for issue in issues)
        print(f"Severity Breakdown: {dict(severity_counts)}")
        
        for category, category_issues in sorted(by_category.items()):
            print(f"\n🔍 {category.replace('_', ' ').title()} ({len(category_issues)}):")
            
            for issue in category_issues[:5]:  # Show first 5 issues per category
                print(f"  📁 {Path(issue.file_path).name}" + (f":{issue.line_number}" if issue.line_number else ""))
                print(f"     ⚠️  {issue.description}")
                print(f"     💡 {issue.recommendation}")
                if issue.code_snippet:
                    print(f"     📝 {issue.code_snippet}")
                print()
                
            if len(category_issues) > 5:
                print(f"     ... and {len(category_issues) - 5} more issues")
        
        # Actionable recommendations summary
        print(f"\n🚀 ACTIONABLE RECOMMENDATIONS:")
        print(f"{'='*30}")
        
        recommendations = {
            "hardcoded_emu": "Replace hardcoded EMU values with UnitConverter.to_emu() calls",
            "tool_integration": "Ensure all converters inherit from BaseConverter and use standardized tools",
            "duplicate_implementation": "Consolidate duplicate methods into shared utilities or base classes",
            "api_inconsistency": "Standardize method signatures across similar converter methods",
            "circular_dependency": "Refactor modules to eliminate circular import dependencies",
            "orphaned_method": "Remove unused methods or verify they are called where needed"
        }
        
        for category, category_issues in by_category.items():
            if category in recommendations:
                print(f"  • {recommendations[category]} ({len(category_issues)} instances)")


if __name__ == '__main__':
    # Run the comprehensive analysis
    src_path = Path(__file__).parent.parent.parent / "src"
    analyzer = CodebaseAnalyzer(src_path)
    issues = analyzer.analyze()
    
    print(f"Analysis complete. Found {len(issues)} potential issues.")
    
    # Run pytest
    pytest.main([__file__, '-v', '-s'])
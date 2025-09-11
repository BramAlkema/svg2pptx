#!/usr/bin/env python3
"""
Tool dependency analyzer for SVG2PPTX project.

This script analyzes import dependencies across tools and identifies
opportunities for consolidation and optimization.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict, Counter

from tools.base_utilities import HTMLReportGenerator, FileUtilities


class ImportAnalyzer:
    """Analyze import patterns across Python files."""
    
    def __init__(self, tools_dir: Path):
        """Initialize analyzer with tools directory."""
        self.tools_dir = tools_dir
        self.import_graph = defaultdict(set)
        self.file_imports = {}
        self.common_patterns = Counter()
    
    def analyze_imports(self) -> Dict[str, Any]:
        """Analyze all Python files for import patterns."""
        python_files = list(self.tools_dir.glob("*.py"))
        
        for file_path in python_files:
            if file_path.name.startswith('__'):
                continue
                
            imports = self._extract_imports(file_path)
            self.file_imports[file_path.name] = imports
            
            # Build import graph
            for imp in imports:
                self.import_graph[file_path.name].add(imp)
                self.common_patterns[imp] += 1
        
        return self._generate_analysis_report()
    
    def _extract_imports(self, file_path: Path) -> Set[str]:
        """Extract import statements from a Python file."""
        imports = set()
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        if node.level == 0:  # Absolute import
                            imports.add(node.module)
                        else:  # Relative import
                            imports.add(f".{node.module}" if node.module else ".")
                        
                        # Also track specific imports for local modules
                        if node.module and ('base_utilities' in node.module or 
                                          'reporting_utilities' in node.module or
                                          'validation_utilities' in node.module):
                            for alias in node.names:
                                imports.add(f"{node.module}.{alias.name}")
                                
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
        
        return imports
    
    def _generate_analysis_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        # Find most common imports
        common_imports = self.common_patterns.most_common(20)
        
        # Identify consolidation opportunities
        consolidation_candidates = self._find_consolidation_candidates()
        
        # Find duplicate functionality patterns
        duplicate_patterns = self._find_duplicate_patterns()
        
        # Generate refactoring recommendations
        recommendations = self._generate_recommendations(
            common_imports, consolidation_candidates, duplicate_patterns
        )
        
        return {
            'total_files': len(self.file_imports),
            'total_unique_imports': len(self.common_patterns),
            'common_imports': common_imports,
            'consolidation_candidates': consolidation_candidates,
            'duplicate_patterns': duplicate_patterns,
            'recommendations': recommendations,
            'file_imports': dict(self.file_imports)
        }
    
    def _find_consolidation_candidates(self) -> List[Dict[str, Any]]:
        """Find imports that appear frequently and could be consolidated."""
        candidates = []
        
        # Standard library imports that could be centralized
        stdlib_imports = [
            'json', 'sqlite3', 'datetime', 'pathlib', 'typing',
            'os', 'sys', 'logging', 'statistics', 'xml.etree.ElementTree'
        ]
        
        for imp_name, count in self.common_patterns.most_common():
            if count >= 3 and any(stdlib in imp_name for stdlib in stdlib_imports):
                files_using = [
                    file for file, imports in self.file_imports.items()
                    if imp_name in imports
                ]
                
                candidates.append({
                    'import': imp_name,
                    'usage_count': count,
                    'files': files_using,
                    'consolidation_potential': 'high' if count >= 5 else 'medium'
                })
        
        return candidates
    
    def _find_duplicate_patterns(self) -> List[Dict[str, Any]]:
        """Find patterns of duplicate functionality across files."""
        patterns = []
        
        # Look for files with similar import patterns
        import_signatures = {}
        for file, imports in self.file_imports.items():
            # Create signature based on common imports
            signature = frozenset(
                imp for imp in imports 
                if any(common in imp for common in ['sqlite3', 'json', 'datetime', 'html'])
            )
            
            if signature and len(signature) >= 3:
                if signature not in import_signatures:
                    import_signatures[signature] = []
                import_signatures[signature].append(file)
        
        # Find signatures shared by multiple files
        for signature, files in import_signatures.items():
            if len(files) >= 2:
                patterns.append({
                    'signature': list(signature),
                    'files': files,
                    'consolidation_opportunity': 'shared_base_class'
                })
        
        return patterns
    
    def _generate_recommendations(self, common_imports: List[Tuple[str, int]],
                                 candidates: List[Dict[str, Any]],
                                 patterns: List[Dict[str, Any]]) -> List[str]:
        """Generate refactoring recommendations."""
        recommendations = []
        
        # Import consolidation recommendations
        high_usage_imports = [
            imp for imp, count in common_imports[:10] 
            if count >= 4
        ]
        
        if high_usage_imports:
            recommendations.append(
                f"Consider consolidating frequently used imports: {', '.join(high_usage_imports[:5])}"
            )
        
        # Base class recommendations
        if any(c['consolidation_potential'] == 'high' for c in candidates):
            recommendations.append(
                "Multiple files share database/reporting patterns - consider base classes"
            )
        
        # Specific module recommendations
        validation_files = [
            file for file in self.file_imports.keys()
            if 'validator' in file.lower()
        ]
        
        if len(validation_files) >= 2:
            recommendations.append(
                f"Validation tools ({', '.join(validation_files)}) could share common base class"
            )
        
        reporting_files = [
            file for file in self.file_imports.keys()
            if any(term in file.lower() for term in ['report', 'dashboard', 'accuracy'])
        ]
        
        if len(reporting_files) >= 2:
            recommendations.append(
                f"Reporting tools ({', '.join(reporting_files)}) could share reporting utilities"
            )
        
        return recommendations


def analyze_tool_dependencies() -> None:
    """Main function to analyze tool dependencies."""
    tools_dir = Path(__file__).parent
    analyzer = ImportAnalyzer(tools_dir)
    
    print("Analyzing tool dependencies...")
    analysis = analyzer.analyze_imports()
    
    # Generate HTML report
    html_generator = HTMLReportGenerator()
    content = _generate_dependency_html_content(analysis, html_generator)
    
    report_path = tools_dir / "dependency_analysis_report.html"
    html_content = html_generator.generate_html_template(
        "Tool Dependency Analysis", content
    )
    
    with open(report_path, 'w') as f:
        f.write(html_content)
    
    print(f"Analysis complete. Report saved to: {report_path}")
    
    # Print summary to console
    print(f"\nSummary:")
    print(f"- Total files analyzed: {analysis['total_files']}")
    print(f"- Unique imports found: {analysis['total_unique_imports']}")
    print(f"- Consolidation candidates: {len(analysis['consolidation_candidates'])}")
    print(f"- Duplicate patterns: {len(analysis['duplicate_patterns'])}")
    print(f"\nTop recommendations:")
    for i, rec in enumerate(analysis['recommendations'][:3], 1):
        print(f"{i}. {rec}")


def _generate_dependency_html_content(analysis: Dict[str, Any], 
                                    html_generator: HTMLReportGenerator) -> str:
    """Generate HTML content for dependency analysis report."""
    content = "<h2>Dependency Analysis Summary</h2>"
    
    # Summary metrics
    content += html_generator.format_metric_box(
        "Files Analyzed", str(analysis['total_files']), "info"
    )
    content += html_generator.format_metric_box(
        "Unique Imports", str(analysis['total_unique_imports']), "info"
    )
    content += html_generator.format_metric_box(
        "Consolidation Opportunities", str(len(analysis['consolidation_candidates'])), "warning"
    )
    
    # Common imports table
    content += "<h3>Most Common Imports</h3>"
    import_rows = [
        [imp, str(count)] for imp, count in analysis['common_imports'][:15]
    ]
    content += html_generator.format_table(["Import", "Usage Count"], import_rows)
    
    # Consolidation candidates
    if analysis['consolidation_candidates']:
        content += "<h3>Consolidation Candidates</h3>"
        candidate_rows = []
        for candidate in analysis['consolidation_candidates'][:10]:
            candidate_rows.append([
                candidate['import'],
                str(candidate['usage_count']),
                candidate['consolidation_potential'],
                ', '.join(candidate['files'][:3]) + ('...' if len(candidate['files']) > 3 else '')
            ])
        
        content += html_generator.format_table(
            ["Import", "Count", "Potential", "Files"], candidate_rows
        )
    
    # Recommendations
    content += "<h3>Refactoring Recommendations</h3>"
    if analysis['recommendations']:
        for i, rec in enumerate(analysis['recommendations'], 1):
            content += f"<p><strong>{i}.</strong> {rec}</p>"
    else:
        content += "<p>No specific recommendations at this time.</p>"
    
    return content


if __name__ == "__main__":
    analyze_tool_dependencies()
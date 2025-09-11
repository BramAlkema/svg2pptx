#!/usr/bin/env python3
"""
SVG Test Library Analysis Tool

Analyzes the real-world SVG test library to provide insights about
coverage, categorization, and readiness for E2E testing.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict, Counter
import logging

from svg_test_library import SVGTestLibrary


logger = logging.getLogger(__name__)


class SVGLibraryAnalyzer:
    """Analyze SVG test library for completeness and coverage."""
    
    def __init__(self, library_path: Path = None):
        """Initialize analyzer.
        
        Args:
            library_path: Path to SVG test library
        """
        if library_path is None:
            library_path = Path("tests/test_data/real_world_svgs")
        
        self.library_path = library_path
        self.library = SVGTestLibrary(library_path)
        
        # Load existing metadata
        if (library_path / "metadata.json").exists():
            with open(library_path / "metadata.json", 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}
    
    def analyze_coverage(self) -> Dict[str, Any]:
        """Analyze converter module coverage across the library.
        
        Returns:
            Coverage analysis results
        """
        coverage_report = self.library.get_coverage_report()
        
        # Detailed analysis
        analysis = {
            'total_files': coverage_report['total_files'],
            'baseline_met': coverage_report['baseline_met'],
            'complexity_distribution': coverage_report['complexity_distribution'],
            'source_tool_distribution': coverage_report['source_tool_distribution'],
            'converter_module_coverage': coverage_report['converter_module_coverage']
        }
        
        # Additional analysis
        analysis['coverage_gaps'] = self._identify_coverage_gaps()
        analysis['feature_matrix'] = self._build_feature_matrix()
        analysis['quality_score'] = self._calculate_quality_score()
        analysis['recommendations'] = self._generate_recommendations()
        
        return analysis
    
    def _identify_coverage_gaps(self) -> Dict[str, List[str]]:
        """Identify gaps in converter module coverage."""
        gaps = {
            'low_coverage_modules': [],
            'missing_features': [],
            'underrepresented_sources': []
        }
        
        # Check converter module coverage
        all_modules = ['shapes', 'paths', 'text', 'gradients', 'filters', 
                      'animations', 'markers', 'masking', 'image', 'groups']
        
        for module in all_modules:
            files = self.library.get_files_by_converter_module(module)
            if len(files) < 3:  # Threshold for adequate coverage
                gaps['low_coverage_modules'].append(module)
        
        # Check feature representation
        all_features = set()
        for metadata in self.metadata.values():
            all_features.update(metadata.get('features', []))
        
        expected_features = [
            'shapes', 'paths', 'text', 'gradients', 'filters', 'animations',
            'transforms', 'patterns', 'masking', 'css_styles'
        ]
        
        for feature in expected_features:
            if feature not in all_features:
                gaps['missing_features'].append(feature)
        
        # Check source tool representation
        source_counts = Counter(metadata.get('source_tool', 'unknown') 
                               for metadata in self.metadata.values())
        
        for tool in ['figma', 'illustrator', 'inkscape']:
            if source_counts.get(tool, 0) < 5:
                gaps['underrepresented_sources'].append(tool)
        
        return gaps
    
    def _build_feature_matrix(self) -> Dict[str, Dict[str, int]]:
        """Build a matrix of features vs source tools."""
        matrix = defaultdict(lambda: defaultdict(int))
        
        for metadata in self.metadata.values():
            source_tool = metadata.get('source_tool', 'unknown')
            features = metadata.get('features', [])
            
            for feature in features:
                matrix[feature][source_tool] += 1
        
        return dict(matrix)
    
    def _calculate_quality_score(self) -> Dict[str, float]:
        """Calculate quality scores for the library."""
        total_files = len(self.metadata)
        
        if total_files == 0:
            return {'overall': 0.0, 'coverage': 0.0, 'diversity': 0.0, 'completeness': 0.0}
        
        # Coverage score (0-100)
        all_modules = ['shapes', 'paths', 'text', 'gradients', 'filters', 
                      'animations', 'markers', 'masking', 'image', 'groups']
        
        covered_modules = 0
        for module in all_modules:
            files = self.library.get_files_by_converter_module(module)
            if len(files) >= 2:  # At least 2 files per module
                covered_modules += 1
        
        coverage_score = (covered_modules / len(all_modules)) * 100
        
        # Diversity score (source tools and complexity)
        source_tools = set(metadata.get('source_tool', 'unknown') 
                          for metadata in self.metadata.values())
        complexity_levels = set(metadata.get('complexity', 'unknown') 
                               for metadata in self.metadata.values())
        
        # Ideal: 4+ source tools, 3 complexity levels
        diversity_score = min(100, (len(source_tools) / 4 + len(complexity_levels) / 3) * 50)
        
        # Completeness score (baseline + feature coverage)
        baseline_score = min(100, (total_files / 50) * 100)  # 50 files target
        
        all_features = set()
        for metadata in self.metadata.values():
            all_features.update(metadata.get('features', []))
        
        expected_features = 10  # Number of major feature categories
        feature_score = min(100, (len(all_features) / expected_features) * 100)
        
        completeness_score = (baseline_score + feature_score) / 2
        
        # Overall score
        overall_score = (coverage_score + diversity_score + completeness_score) / 3
        
        return {
            'overall': round(overall_score, 1),
            'coverage': round(coverage_score, 1),
            'diversity': round(diversity_score, 1),
            'completeness': round(completeness_score, 1)
        }
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate actionable recommendations for improving the library."""
        recommendations = []
        
        gaps = self._identify_coverage_gaps()
        quality = self._calculate_quality_score()
        total_files = len(self.metadata)
        
        # File count recommendations
        if total_files < 50:
            recommendations.append({
                'category': 'Collection',
                'priority': 'High',
                'action': f'Collect {50 - total_files} more SVG files to reach baseline',
                'benefit': 'Ensures comprehensive test coverage'
            })
        
        # Converter module coverage
        if gaps['low_coverage_modules']:
            recommendations.append({
                'category': 'Coverage',
                'priority': 'High',
                'action': f'Add files that exercise: {", ".join(gaps["low_coverage_modules"])}',
                'benefit': 'Improves converter module test coverage'
            })
        
        # Source tool diversity
        if gaps['underrepresented_sources']:
            recommendations.append({
                'category': 'Diversity',
                'priority': 'Medium',
                'action': f'Collect more files from: {", ".join(gaps["underrepresented_sources"])}',
                'benefit': 'Ensures real-world tool representation'
            })
        
        # Feature coverage
        if gaps['missing_features']:
            recommendations.append({
                'category': 'Features',
                'priority': 'Medium',
                'action': f'Add files with features: {", ".join(gaps["missing_features"])}',
                'benefit': 'Complete feature coverage for testing'
            })
        
        # Quality-based recommendations
        if quality['coverage'] < 70:
            recommendations.append({
                'category': 'Quality',
                'priority': 'High',
                'action': 'Focus on converter module coverage improvement',
                'benefit': 'Increases test reliability and bug detection'
            })
        
        if quality['diversity'] < 60:
            recommendations.append({
                'category': 'Quality',
                'priority': 'Medium',
                'action': 'Increase source tool and complexity diversity',
                'benefit': 'Better represents real-world usage patterns'
            })
        
        return recommendations
    
    def generate_report(self) -> str:
        """Generate comprehensive analysis report.
        
        Returns:
            Markdown-formatted analysis report
        """
        analysis = self.analyze_coverage()
        
        report = f"""# SVG Test Library Analysis Report
        
## Overview

- **Total Files**: {analysis['total_files']}
- **Baseline Met**: {'✅ Yes' if analysis['baseline_met'] else '❌ No (need 50+ files)'}
- **Quality Score**: {analysis['quality_score']['overall']}/100

## Quality Breakdown

| Metric | Score | Status |
|--------|-------|--------|
| Coverage | {analysis['quality_score']['coverage']}/100 | {'✅' if analysis['quality_score']['coverage'] >= 70 else '⚠️' if analysis['quality_score']['coverage'] >= 50 else '❌'} |
| Diversity | {analysis['quality_score']['diversity']}/100 | {'✅' if analysis['quality_score']['diversity'] >= 70 else '⚠️' if analysis['quality_score']['diversity'] >= 50 else '❌'} |
| Completeness | {analysis['quality_score']['completeness']}/100 | {'✅' if analysis['quality_score']['completeness'] >= 70 else '⚠️' if analysis['quality_score']['completeness'] >= 50 else '❌'} |

## Complexity Distribution

"""
        
        for complexity, count in analysis['complexity_distribution'].items():
            report += f"- **{complexity.title()}**: {count} files\n"
        
        report += f"""
## Source Tool Distribution

"""
        
        for tool, count in analysis['source_tool_distribution'].items():
            report += f"- **{tool.title()}**: {count} files\n"
        
        report += f"""
## Converter Module Coverage

| Module | Files | Coverage % |
|--------|-------|------------|
"""
        
        for module, data in analysis['converter_module_coverage'].items():
            coverage_pct = data['coverage_percentage']
            status = '✅' if coverage_pct >= 40 else '⚠️' if coverage_pct >= 20 else '❌'
            report += f"| {module} | {data['file_count']} | {coverage_pct:.1f}% {status} |\n"
        
        # Feature matrix
        report += f"""
## Feature Matrix

| Feature | """
        
        # Get all source tools for header
        all_tools = set()
        for tool_data in analysis['feature_matrix'].values():
            all_tools.update(tool_data.keys())
        all_tools = sorted(all_tools)
        
        for tool in all_tools:
            report += f"{tool.title()} | "
        report += "\n|---------|"
        for _ in all_tools:
            report += "---------|"
        report += "\n"
        
        for feature, tool_data in analysis['feature_matrix'].items():
            report += f"| {feature} | "
            for tool in all_tools:
                count = tool_data.get(tool, 0)
                report += f"{count} | "
            report += "\n"
        
        # Recommendations
        if analysis['recommendations']:
            report += f"""
## 🎯 Recommendations

"""
            for i, rec in enumerate(analysis['recommendations'], 1):
                priority_emoji = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}.get(rec['priority'], '⚪')
                report += f"""### {i}. {rec['category']} {priority_emoji}

**Action**: {rec['action']}  
**Benefit**: {rec['benefit']}  
**Priority**: {rec['priority']}

"""
        
        # Coverage gaps details
        gaps = analysis['coverage_gaps']
        if any(gaps.values()):
            report += f"""
## 📊 Coverage Gap Analysis

"""
            
            if gaps['low_coverage_modules']:
                report += f"**Low Coverage Modules**: {', '.join(gaps['low_coverage_modules'])}\n\n"
            
            if gaps['missing_features']:
                report += f"**Missing Features**: {', '.join(gaps['missing_features'])}\n\n"
            
            if gaps['underrepresented_sources']:
                report += f"**Underrepresented Sources**: {', '.join(gaps['underrepresented_sources'])}\n\n"
        
        report += f"""
## 📈 Next Steps

1. **Collection Priority**: Focus on high-priority recommendations first
2. **Quality Threshold**: Aim for 70+ scores in all quality metrics
3. **Baseline Target**: Collect {max(0, 50 - analysis['total_files'])} more files to reach 50-file baseline
4. **Module Coverage**: Ensure each converter module has at least 3 test files
5. **Regular Review**: Re-run analysis after adding new files

---
*Generated by SVG Test Library Analyzer*
"""
        
        return report
    
    def export_analysis(self, output_path: Path = None) -> Path:
        """Export analysis results to JSON and markdown files.
        
        Args:
            output_path: Directory to save analysis files
            
        Returns:
            Path to generated report
        """
        if output_path is None:
            output_path = self.library_path / "analysis"
        
        output_path.mkdir(exist_ok=True)
        
        # Export detailed analysis as JSON
        analysis = self.analyze_coverage()
        json_path = output_path / "library_analysis.json"
        with open(json_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        # Export report as markdown
        report = self.generate_report()
        report_path = output_path / "ANALYSIS_REPORT.md"
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Analysis exported to: {output_path}")
        return report_path


def main():
    """Main CLI interface for SVG library analysis."""
    parser = argparse.ArgumentParser(description="Analyze SVG test library")
    parser.add_argument('--library-path', type=Path, help="Path to SVG test library")
    parser.add_argument('--output', type=Path, help="Output directory for analysis files")
    parser.add_argument('--format', choices=['json', 'markdown', 'both'], default='both',
                       help="Output format")
    parser.add_argument('--verbose', '-v', action='store_true', help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
    
    # Initialize analyzer
    analyzer = SVGLibraryAnalyzer(args.library_path)
    
    if args.format in ['json', 'both']:
        analysis = analyzer.analyze_coverage()
        if args.output:
            json_path = args.output / "library_analysis.json"
            json_path.parent.mkdir(exist_ok=True)
            with open(json_path, 'w') as f:
                json.dump(analysis, f, indent=2)
            print(f"📊 Analysis exported to: {json_path}")
        else:
            print(json.dumps(analysis, indent=2))
    
    if args.format in ['markdown', 'both']:
        report = analyzer.generate_report()
        if args.output:
            report_path = analyzer.export_analysis(args.output)
            print(f"📋 Report generated: {report_path}")
        else:
            print(report)


if __name__ == "__main__":
    main()
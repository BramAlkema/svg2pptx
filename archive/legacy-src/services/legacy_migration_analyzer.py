#!/usr/bin/env python3
"""
Legacy Migration Analyzer

Analyzes the codebase for legacy patterns that need migration
to the new ConversionServices architecture.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class LegacyPatternType(Enum):
    """Types of legacy patterns to migrate."""
    DIRECT_SERVICE_IMPORT = "direct_service_import"
    DIRECT_SERVICE_INSTANTIATION = "direct_service_instantiation"
    MANUAL_DEPENDENCY_SETUP = "manual_dependency_setup"
    OLD_CONTEXT_CREATION = "old_context_creation"
    HARDCODED_SERVICE_CONFIG = "hardcoded_service_config"


@dataclass
class LegacyPattern:
    """Represents a legacy pattern found in the code."""
    file_path: str
    line_number: int
    pattern_type: LegacyPatternType
    code_snippet: str
    suggested_fix: str
    priority: str  # "high", "medium", "low"


class LegacyMigrationAnalyzer:
    """Analyzes codebase for legacy patterns that need migration."""

    def __init__(self, src_directory: str = "src"):
        """Initialize analyzer with source directory."""
        self.src_dir = Path(src_directory)
        self.legacy_patterns: List[LegacyPattern] = []

        # Define patterns to look for
        self.direct_import_patterns = [
            r'from\s+\.\.units\s+import\s+UnitConverter',
            r'from\s+src\.units\s+import\s+UnitConverter',
            r'from\s+\.\.color\s+import\s+Color',
            r'from\s+src\.color\s+import\s+Color',
            r'from\s+\.\.transforms\s+import\s+TransformEngine',
            r'from\s+src\.transforms\s+import\s+TransformEngine',
            r'from\s+\.\.viewbox\s+import\s+ViewportEngine',
            r'from\s+src\.viewbox\s+import\s+ViewportEngine',
        ]

        self.direct_instantiation_patterns = [
            r'UnitConverter\(\)',
            r'Color\(\)',
            r'TransformEngine\(\)',
            r'ViewportEngine\(',
            r'StyleParser\(\)',
            r'CoordinateTransformer\(\)',
        ]

        # Files to exclude from analysis
        self.excluded_files = {
            'src/services/conversion_services.py',  # Service definitions
            'src/services/service_adapters.py',    # Adapter definitions
            'src/units/__init__.py',               # Unit system core
            'src/units/core.py',                   # Unit system core
            'src/color/__init__.py',               # Color system core
            'src/color/core.py',                   # Color system core
            'src/transforms/__init__.py',          # Transform system core
            'src/viewbox/__init__.py',             # Viewport system core
            'src/viewbox/core.py',                 # Viewport system core
        }

    def analyze_legacy_patterns(self) -> List[LegacyPattern]:
        """Analyze all Python files for legacy patterns."""
        self.legacy_patterns = []

        python_files = self._find_python_files()

        for file_path in python_files:
            if str(file_path) in self.excluded_files:
                continue

            self._analyze_file(file_path)

        return self.legacy_patterns

    def _find_python_files(self) -> List[Path]:
        """Find all Python files in source directory."""
        return list(self.src_dir.rglob("*.py"))

    def _analyze_file(self, file_path: Path):
        """Analyze a single file for legacy patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # Check for direct imports
            self._check_direct_imports(file_path, lines)

            # Check for direct instantiation
            self._check_direct_instantiation(file_path, lines)

            # Check for manual dependency setup
            self._check_manual_dependency_setup(file_path, lines)

            # Check for old context creation patterns
            self._check_old_context_creation(file_path, lines)

        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")

    def _check_direct_imports(self, file_path: Path, lines: List[str]):
        """Check for direct service imports."""
        for line_num, line in enumerate(lines, 1):
            for pattern in self.direct_import_patterns:
                if re.search(pattern, line):
                    # Skip if it's in a try/except block for backward compatibility
                    if 'try:' in lines[max(0, line_num-3):line_num]:
                        continue

                    self.legacy_patterns.append(LegacyPattern(
                        file_path=str(file_path),
                        line_number=line_num,
                        pattern_type=LegacyPatternType.DIRECT_SERVICE_IMPORT,
                        code_snippet=line.strip(),
                        suggested_fix="Use ConversionServices instead: services.unit_converter, etc.",
                        priority="medium"
                    ))

    def _check_direct_instantiation(self, file_path: Path, lines: List[str]):
        """Check for direct service instantiation."""
        for line_num, line in enumerate(lines, 1):
            for pattern in self.direct_instantiation_patterns:
                if re.search(pattern, line) and 'ConversionServices' not in line:
                    self.legacy_patterns.append(LegacyPattern(
                        file_path=str(file_path),
                        line_number=line_num,
                        pattern_type=LegacyPatternType.DIRECT_SERVICE_INSTANTIATION,
                        code_snippet=line.strip(),
                        suggested_fix="Use ConversionServices.create_default() or inject services",
                        priority="high"
                    ))

    def _check_manual_dependency_setup(self, file_path: Path, lines: List[str]):
        """Check for manual dependency setup patterns."""
        dependency_setup_indicators = [
            r'unit_converter\s*=\s*UnitConverter',
            r'color_parser\s*=\s*Color',
            r'transform_parser\s*=\s*TransformEngine',
            r'viewport_resolver\s*=\s*ViewportEngine'
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern in dependency_setup_indicators:
                if re.search(pattern, line):
                    self.legacy_patterns.append(LegacyPattern(
                        file_path=str(file_path),
                        line_number=line_num,
                        pattern_type=LegacyPatternType.MANUAL_DEPENDENCY_SETUP,
                        code_snippet=line.strip(),
                        suggested_fix="Use ConversionServices for centralized dependency management",
                        priority="high"
                    ))

    def _check_old_context_creation(self, file_path: Path, lines: List[str]):
        """Check for old context creation patterns."""
        old_context_patterns = [
            r'ConversionContext\(\)\s*$',  # No parameters
            r'ConversionContext\(svg_root\)',  # Only SVG root
            r'ConversionContext\([^)]*\)\s*(?!.*services)',  # Parameters but no services
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern in old_context_patterns:
                if re.search(pattern, line):
                    # Check if services parameter is provided in the next few lines
                    context_lines = lines[line_num-1:line_num+3]
                    if not any('services=' in context_line for context_line in context_lines):
                        self.legacy_patterns.append(LegacyPattern(
                            file_path=str(file_path),
                            line_number=line_num,
                            pattern_type=LegacyPatternType.OLD_CONTEXT_CREATION,
                            code_snippet=line.strip(),
                            suggested_fix="Add services parameter: ConversionContext(svg_root, services=services)",
                            priority="medium"
                        ))

    def generate_migration_report(self) -> str:
        """Generate migration report."""
        if not self.legacy_patterns:
            return "✅ No legacy patterns found - migration complete!"

        report = ["🔄 Legacy Migration Analysis Report"]
        report.append("=" * 50)
        report.append(f"Found {len(self.legacy_patterns)} legacy patterns requiring migration\n")

        # Group by pattern type
        patterns_by_type = {}
        for pattern in self.legacy_patterns:
            if pattern.pattern_type not in patterns_by_type:
                patterns_by_type[pattern.pattern_type] = []
            patterns_by_type[pattern.pattern_type].append(pattern)

        # Generate report by type
        for pattern_type, patterns in patterns_by_type.items():
            report.append(f"\n{pattern_type.value.upper()} ({len(patterns)} occurrences):")
            report.append("-" * 40)

            for pattern in patterns[:10]:  # Limit to first 10 per type
                report.append(f"📁 File: {pattern.file_path}:{pattern.line_number}")
                report.append(f"   Code: {pattern.code_snippet}")
                report.append(f"   Fix: {pattern.suggested_fix}")
                report.append(f"   Priority: {pattern.priority.upper()}")
                report.append("")

            if len(patterns) > 10:
                report.append(f"   ... and {len(patterns) - 10} more occurrences")

        # Summary by priority
        high_priority = len([p for p in self.legacy_patterns if p.priority == "high"])
        medium_priority = len([p for p in self.legacy_patterns if p.priority == "medium"])
        low_priority = len([p for p in self.legacy_patterns if p.priority == "low"])

        report.append(f"\n📊 PRIORITY BREAKDOWN:")
        report.append(f"High priority (immediate action needed): {high_priority}")
        report.append(f"Medium priority (should be migrated): {medium_priority}")
        report.append(f"Low priority (can be migrated later): {low_priority}")

        return "\n".join(report)

    def get_migration_plan(self) -> Dict[str, List[str]]:
        """Generate step-by-step migration plan."""
        plan = {
            "immediate": [],
            "short_term": [],
            "long_term": []
        }

        # Group files by priority
        high_priority_files = set()
        medium_priority_files = set()
        low_priority_files = set()

        for pattern in self.legacy_patterns:
            if pattern.priority == "high":
                high_priority_files.add(pattern.file_path)
            elif pattern.priority == "medium":
                medium_priority_files.add(pattern.file_path)
            else:
                low_priority_files.add(pattern.file_path)

        # Create migration steps
        if high_priority_files:
            plan["immediate"].append("🔥 IMMEDIATE (High Priority Files):")
            for file_path in sorted(high_priority_files):
                plan["immediate"].append(f"  - Migrate {file_path}")

        if medium_priority_files:
            plan["short_term"].append("📋 SHORT TERM (Medium Priority Files):")
            for file_path in sorted(medium_priority_files):
                plan["short_term"].append(f"  - Migrate {file_path}")

        if low_priority_files:
            plan["long_term"].append("📅 LONG TERM (Low Priority Files):")
            for file_path in sorted(low_priority_files):
                plan["long_term"].append(f"  - Migrate {file_path}")

        return plan


def main():
    """Run legacy migration analysis."""
    analyzer = LegacyMigrationAnalyzer()
    patterns = analyzer.analyze_legacy_patterns()

    print(analyzer.generate_migration_report())

    if patterns:
        print("\n" + "=" * 50)
        print("🚀 MIGRATION PLAN")
        print("=" * 50)

        plan = analyzer.get_migration_plan()
        for phase, steps in plan.items():
            if steps:
                print(f"\n{phase.upper()}:")
                for step in steps:
                    print(step)

    return len(patterns) == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
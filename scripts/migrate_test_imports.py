#!/usr/bin/env python3
"""
Migrate test imports from src.* to core.*

This script automatically updates test files to use the new core/ module structure
instead of the legacy src/ structure.

Usage:
    python scripts/migrate_test_imports.py tests/unit/batch/ --dry-run
    python scripts/migrate_test_imports.py tests/ --verify
    python scripts/migrate_test_imports.py tests/unit/batch/test_models.py
"""

import ast
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ImportStatement:
    """Represents an import statement found in a test file."""
    module: str
    names: List[str]
    line_number: int
    original_line: str
    import_type: str  # 'import' or 'from'


@dataclass
class MigrationResult:
    """Result of migrating a single file."""
    filepath: Path
    status: str  # 'migrated', 'unchanged', 'skip', 'manual_review', 'error'
    changes: List[Dict]
    errors: List[str]
    verification_passed: Optional[bool] = None


class TestMigrator:
    """Migrate test imports from src.* to core.*"""

    # Simple 1:1 module renames
    SIMPLE_MAPPINGS = {
        # Batch processing
        'src.batch.models': 'core.batch.models',
        'src.batch.file_manager': 'core.batch.file_manager',
        'src.batch.drive_controller': 'core.batch.drive_controller',
        'src.batch.worker': 'core.batch.worker',
        'src.batch.drive_tasks': 'core.batch.drive_tasks',
        'src.batch.simple_api': 'core.batch.simple_api',

        # Converters - simple renames
        'src.converters.gradients': 'core.converters.gradients',
        'src.converters.custgeom_generator': 'core.converters.custgeom_generator',
        'src.converters.masking': 'core.converters.masking',
        'src.converters.marker_processor': 'core.converters.marker_processor',
        'src.converters.switch_converter': 'core.converters.switch_converter',

        # Filters
        'src.converters.filters': 'core.filters',
        'src.converters.filters.converter': 'core.services.filter_service',

        # Services
        'src.services.conversion_services': 'core.services.conversion_services',
        'src.services.gradient_service': 'core.services.gradient_service',
        'src.services.filter_service': 'core.services.filter_service',
        'src.services.font_service': 'core.services.font_service',
        'src.services.legacy_migration_analyzer': 'core.services.legacy_migration_analyzer',

        # IR and types
        'src.ir': 'core.ir',
        'src.ir.scene': 'core.ir.scene',
        'src.ir.paint': 'core.ir.paint',
        'src.ir.text': 'core.ir.text',

        # Pipeline
        'src.pipeline': 'core.pipeline',
        'src.pipeline.converter': 'core.pipeline.converter',

        # Performance
        'src.performance': 'core.performance',
        'src.performance.cache': 'core.performance.cache',

        # Units
        'src.units': 'core.units',
        'src.units.core': 'core.units.core',

        # Policy
        'src.policy': 'core.policy',
        'src.policy.engine': 'core.policy.engine',
        'src.policy.config': 'core.policy.config',
    }

    # Modules that moved or were refactored (need manual review)
    COMPLEX_MAPPINGS = {
        'src.converters.base': 'MANUAL_REVIEW: Could be core.units.core.ConversionContext or core.map.base',
        'src.converters.clippath_analyzer': 'MANUAL_REVIEW: Use core.policy.engine.PolicyEngine instead',
        'src.converters.animation_converter': 'MANUAL_REVIEW: Check core.animations or core.converters',
        'src.preprocessing': 'MANUAL_REVIEW: Some in core.pre, some never migrated',
    }

    # Modules that were never migrated (should skip tests)
    ARCHIVE_MODULES = {
        'src.svg2pptx': 'archive/legacy-src/svg2pptx.py',
        'src.emf_packaging': 'archive/legacy-src/emf_packaging.py',
        'src.emf_blob': 'archive/legacy-src/emf_blob.py',
        'src.emf_tiles': 'archive/legacy-src/emf_tiles.py',
        'src.ooxml_templates': 'archive/legacy-src/ooxml_templates.py',
        'src.svg2drawingml': 'archive/legacy-src/svg2drawingml.py',
        'src.pptx': 'archive/legacy-src/pptx/',
        'src.config': 'DEPRECATED: No longer exists',
    }

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.stats = {
            'migrated': 0,
            'unchanged': 0,
            'manual_review': 0,
            'skip': 0,
            'error': 0,
        }

    def scan_imports(self, filepath: Path) -> List[ImportStatement]:
        """Extract all src.* import statements using AST parsing."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=str(filepath))
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Failed to parse {filepath}: {e}")
            return []

        imports = []
        lines = content.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith('src.'):
                        line_text = lines[node.lineno - 1] if node.lineno <= len(lines) else ''
                        imports.append(ImportStatement(
                            module=alias.name,
                            names=[alias.asname or alias.name],
                            line_number=node.lineno,
                            original_line=line_text.strip(),
                            import_type='import'
                        ))
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith('src.'):
                    line_text = lines[node.lineno - 1] if node.lineno <= len(lines) else ''
                    imports.append(ImportStatement(
                        module=node.module,
                        names=[alias.name for alias in node.names],
                        line_number=node.lineno,
                        original_line=line_text.strip(),
                        import_type='from'
                    ))

        return imports

    def migrate_file(self, filepath: Path, dry_run: bool = True) -> MigrationResult:
        """Migrate a single test file."""
        imports = self.scan_imports(filepath)

        if not imports:
            return MigrationResult(
                filepath=filepath,
                status='unchanged',
                changes=[],
                errors=[]
            )

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return MigrationResult(
                filepath=filepath,
                status='error',
                changes=[],
                errors=[f"Failed to read file: {e}"]
            )

        original_content = content
        changes = []
        needs_manual_review = False
        should_skip = False

        for imp in imports:
            # Check if it's an archive module
            if any(imp.module.startswith(arch) for arch in self.ARCHIVE_MODULES):
                should_skip = True
                changes.append({
                    'line': imp.line_number,
                    'old': imp.original_line,
                    'status': 'SKIP',
                    'reason': f'Archive module: {imp.module} - test should be skipped or moved to orphaned'
                })
                continue

            # Check if it needs manual review
            if any(imp.module.startswith(comp) for comp in self.COMPLEX_MAPPINGS):
                needs_manual_review = True
                reason = next((v for k, v in self.COMPLEX_MAPPINGS.items() if imp.module.startswith(k)), '')
                changes.append({
                    'line': imp.line_number,
                    'old': imp.original_line,
                    'status': 'MANUAL_REVIEW',
                    'reason': reason
                })
                continue

            # Simple mapping
            mapping_found = False
            for src_module, core_module in self.SIMPLE_MAPPINGS.items():
                if imp.module == src_module or imp.module.startswith(src_module + '.'):
                    # Replace the module name
                    new_module = imp.module.replace(src_module, core_module, 1)
                    old_line = imp.original_line
                    new_line = old_line.replace(imp.module, new_module)

                    content = content.replace(old_line, new_line)
                    changes.append({
                        'line': imp.line_number,
                        'old': old_line,
                        'new': new_line,
                        'status': 'MIGRATED'
                    })
                    mapping_found = True
                    break

            if not mapping_found:
                needs_manual_review = True
                changes.append({
                    'line': imp.line_number,
                    'old': imp.original_line,
                    'status': 'NO_MAPPING',
                    'reason': f'No mapping found for {imp.module}'
                })

        # Determine status
        if should_skip:
            status = 'skip'
        elif needs_manual_review:
            status = 'manual_review'
        elif content == original_content:
            status = 'unchanged'
        else:
            status = 'migrated'

        # Write changes if not dry run
        if not dry_run and status == 'migrated':
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                return MigrationResult(
                    filepath=filepath,
                    status='error',
                    changes=changes,
                    errors=[f"Failed to write file: {e}"]
                )

        return MigrationResult(
            filepath=filepath,
            status=status,
            changes=changes,
            errors=[]
        )

    def verify_file(self, filepath: Path) -> bool:
        """Verify file can be collected by pytest."""
        try:
            result = subprocess.run(
                ['pytest', str(filepath), '--collect-only', '-q'],
                capture_output=True,
                text=True,
                timeout=10,
                env={'PYTHONPATH': '.'}
            )
            return result.returncode == 0
        except Exception:
            return False

    def migrate_batch(
        self,
        paths: List[Path],
        dry_run: bool = True,
        verify: bool = False
    ) -> List[MigrationResult]:
        """Migrate multiple files or directories."""
        files = []
        for path in paths:
            if path.is_file():
                files.append(path)
            elif path.is_dir():
                files.extend(path.rglob('test_*.py'))
                files.extend(path.rglob('*_test.py'))

        results = []
        for filepath in sorted(files):
            result = self.migrate_file(filepath, dry_run)

            if verify and result.status == 'migrated' and not dry_run:
                result.verification_passed = self.verify_file(filepath)

            results.append(result)
            self.stats[result.status] += 1

        return results

    def print_summary(self, results: List[MigrationResult]):
        """Print migration summary."""
        print("\n" + "="*80)
        print("MIGRATION SUMMARY")
        print("="*80)

        print(f"\nTotal files processed: {len(results)}")
        print(f"  ✅ Migrated:       {self.stats['migrated']}")
        print(f"  ⚠️  Manual review:  {self.stats['manual_review']}")
        print(f"  ⏭️  Skipped:        {self.stats['skip']}")
        print(f"  ⚪ Unchanged:      {self.stats['unchanged']}")
        print(f"  ❌ Errors:         {self.stats['error']}")

        # Show files needing manual review
        manual_review_files = [r for r in results if r.status == 'manual_review']
        if manual_review_files:
            print("\n" + "-"*80)
            print("FILES NEEDING MANUAL REVIEW:")
            print("-"*80)
            for result in manual_review_files[:10]:  # Show first 10
                print(f"\n📄 {result.filepath}")
                for change in result.changes:
                    if change.get('status') in ['MANUAL_REVIEW', 'NO_MAPPING']:
                        print(f"  Line {change['line']}: {change['old']}")
                        print(f"  → {change.get('reason', 'Unknown reason')}")

        # Show files to skip
        skip_files = [r for r in results if r.status == 'skip']
        if skip_files:
            print("\n" + "-"*80)
            print("FILES TO SKIP (Archive Dependencies):")
            print("-"*80)
            for result in skip_files[:10]:
                print(f"\n⏭️  {result.filepath}")
                for change in result.changes:
                    if change.get('status') == 'SKIP':
                        print(f"  → {change.get('reason', '')}")

        # Show verification results
        verified = [r for r in results if r.verification_passed is not None]
        if verified:
            passed = sum(1 for r in verified if r.verification_passed)
            print(f"\n✓ Verification: {passed}/{len(verified)} files can be collected by pytest")


def main():
    parser = argparse.ArgumentParser(
        description='Migrate test imports from src.* to core.*',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (preview changes)
  python scripts/migrate_test_imports.py tests/unit/batch/ --dry-run

  # Migrate and verify
  python scripts/migrate_test_imports.py tests/unit/batch/ --verify

  # Migrate specific file
  python scripts/migrate_test_imports.py tests/unit/batch/test_models.py

  # Migrate all tests (verbose)
  python scripts/migrate_test_imports.py tests/ --verbose
        """
    )

    parser.add_argument(
        'paths',
        nargs='+',
        type=Path,
        help='Test files or directories to migrate'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify migrated files with pytest --collect-only'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output'
    )

    args = parser.parse_args()

    # Validate paths
    for path in args.paths:
        if not path.exists():
            print(f"❌ Error: Path does not exist: {path}")
            sys.exit(1)

    # Run migration
    migrator = TestMigrator(verbose=args.verbose)

    mode = "DRY RUN" if args.dry_run else "MIGRATION"
    print(f"\n{'='*80}")
    print(f"TEST IMPORT {mode}")
    print(f"{'='*80}")
    print(f"Paths: {', '.join(str(p) for p in args.paths)}")
    print(f"Verify: {args.verify}")
    print()

    results = migrator.migrate_batch(args.paths, args.dry_run, args.verify)
    migrator.print_summary(results)

    # Show sample changes if dry run
    if args.dry_run and args.verbose:
        migrated = [r for r in results if r.status == 'migrated'][:3]
        if migrated:
            print("\n" + "-"*80)
            print("SAMPLE CHANGES:")
            print("-"*80)
            for result in migrated:
                print(f"\n📄 {result.filepath}")
                for change in result.changes[:5]:
                    if change.get('status') == 'MIGRATED':
                        print(f"  - {change['old']}")
                        print(f"  + {change['new']}")

    # Exit code
    if migrator.stats['error'] > 0:
        sys.exit(1)
    elif not args.dry_run and migrator.stats['migrated'] > 0:
        print(f"\n✅ Successfully migrated {migrator.stats['migrated']} files")

    sys.exit(0)


if __name__ == '__main__':
    main()

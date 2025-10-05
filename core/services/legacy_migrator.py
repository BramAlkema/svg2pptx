#!/usr/bin/env python3
"""
Legacy Migrator Tool

Automatically migrates legacy patterns to use ConversionServices.
"""

import re
from pathlib import Path
from typing import Dict


class LegacyMigrator:
    """Automatically migrates legacy patterns to ConversionServices."""

    def __init__(self, src_directory: str = "src"):
        """Initialize migrator."""
        self.src_dir = Path(src_directory)
        self.migrations_applied = 0

        # Define migration patterns
        self.migration_patterns = [
            # Direct service instantiation patterns
            # Migration patterns for direct service instantiation -> ConversionServices usage
            (
                r'(\s+)(\w+\s*=\s*)UnitConverter\(\)',
                r'\1\2services.unit_converter',
                "Migrate: UnitConverter() -> services.unit_converter",
            ),
            (
                r'(\s+)(\w+\s*=\s*)TransformEngine\(\)',
                r'\1\2services.transform_parser',
                "Migrate: TransformEngine() -> services.transform_parser",
            ),
            (
                r'(\s+)(\w+\s*=\s*)StyleParser\(\)',
                r'\1\2services.style_parser',
                "Migrate: StyleParser() -> services.style_parser",
            ),
            (
                r'(\s+)(\w+\s*=\s*)CoordinateTransformer\(\)',
                r'\1\2services.coordinate_transformer',
                "Migrate: CoordinateTransformer() -> services.coordinate_transformer",
            ),

            # Import patterns - more complex, require manual handling
        ]

    def migrate_file(self, file_path: Path, services_injection_needed: bool = True) -> bool:
        """Migrate a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Apply migration patterns
            for pattern, replacement, description in self.migration_patterns:
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    print(f"  ✅ {description}")
                    content = new_content
                    self.migrations_applied += 1

            # Add ConversionServices import if needed and not present
            if services_injection_needed and content != original_content:
                if "ConversionServices" not in content:
                    content = self._add_conversion_services_import(content, file_path)

            # Write back if changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True

        except Exception as e:
            print(f"  ❌ Error migrating {file_path}: {e}")

        return False

    def _add_conversion_services_import(self, content: str, file_path: Path) -> str:
        """Add ConversionServices import to file."""
        lines = content.split('\n')

        # Find the last import line
        last_import_line = -1
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')) and not line.strip().startswith('#'):
                last_import_line = i

        # Determine the relative import path
        relative_depth = len(file_path.relative_to(self.src_dir).parts) - 1
        import_prefix = ".." * (relative_depth + 1) if relative_depth > 0 else "."

        # Add import after last import
        if last_import_line >= 0:
            import_line = f"from {import_prefix}services.conversion_services import ConversionServices"
            lines.insert(last_import_line + 1, import_line)
        else:
            # Add at the top if no imports found
            import_line = f"from {import_prefix}services.conversion_services import ConversionServices"
            lines.insert(0, import_line)

        return '\n'.join(lines)

    def migrate_high_priority_files(self) -> dict[str, bool]:
        """Migrate high-priority files identified by the analyzer."""
        high_priority_files = [
            "src/fractional_emu.py",
            "src/paths/coordinate_system.py",
            "src/converters/animation_transform_matrix.py",
            "src/converters/symbols.py",
            "src/utils/style_parser.py",
            "src/utils/coordinate_transformer.py",
            # "src/multislide/document.py",  # Removed - replaced with Clean Slate
            "src/pptx/package_builder.py",
            "src/preprocessing/geometry_plugins.py",
            "src/preprocessing/advanced_plugins.py",
            "src/performance/cache.py",
            "src/services/viewport_service.py",
        ]

        results = {}

        for file_path_str in high_priority_files:
            file_path = Path(file_path_str)
            if file_path.exists():
                print(f"\n🔧 Migrating {file_path_str}...")
                results[file_path_str] = self.migrate_file(file_path)
            else:
                print(f"\n⚠️  File not found: {file_path_str}")
                results[file_path_str] = False

        return results

    def create_services_injection_helper(self, file_path: Path) -> str:
        """Create code template for services injection."""
        file_path.stem.title().replace('_', '')

        template = '''
# Add this to your class __init__ method:
def __init__(self, services: Optional[ConversionServices] = None, ...):
    """Initialize with ConversionServices dependency injection."""
    # Provide services or create default
    if services is None:
        services = ConversionServices.create_default()

    self.services = services

    # Now use services instead of direct instantiation:
    # OLD: self.unit_converter = UnitConverter()
    # NEW: self.unit_converter = services.unit_converter

    # OLD: self.transform_parser = TransformEngine()
    # NEW: self.transform_parser = services.transform_parser

    # Service-aware fallback pattern (recommended for robustness):
    # try:
    #     from ..services.conversion_services import ConversionServices
    #     services = ConversionServices.create_default()
    #     self.unit_converter = services.unit_converter
    # except (ImportError, RuntimeError):
    #     self.unit_converter = UnitConverter()  # Safe fallback

# Update method calls to use self.services with service-aware patterns:
# OLD: resolver = ViewportEngine()
# NEW: resolver = self.services.viewport_resolver
'''
        return template


def main():
    """Run legacy migration."""
    print("🚀 Starting Legacy Migration to ConversionServices")
    print("=" * 60)

    migrator = LegacyMigrator()

    # Migrate high-priority files
    results = migrator.migrate_high_priority_files()

    # Summary
    successful = sum(1 for success in results.values() if success)
    total = len(results)

    print("\n📊 MIGRATION SUMMARY")
    print("=" * 30)
    print(f"Files processed: {total}")
    print(f"Successfully migrated: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Total pattern replacements: {migrator.migrations_applied}")

    if successful > 0:
        print("\n✅ Migration completed successfully!")
        print("Next steps:")
        print("1. Test the migrated files")
        print("2. Update remaining manual patterns")
        print("3. Run tests to ensure nothing broke")
    else:
        print("\n⚠️  No automatic migrations applied.")
        print("Manual migration may be required for complex patterns.")


if __name__ == "__main__":
    main()
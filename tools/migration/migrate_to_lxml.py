#!/usr/bin/env python3
"""
Batch ElementTree to lxml Migration Script

This script systematically migrates all modules from xml.etree.ElementTree to lxml
for better XML processing capabilities and consistency across the codebase.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple, Dict


class LxmlMigrator:
    """Handles systematic migration from ElementTree to lxml."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backups"
        self.migration_patterns = [
            # Direct imports
            (r'import xml\.etree\.ElementTree as ET', 'from lxml import etree as ET'),
            (r'from xml\.etree import ElementTree as ET', 'from lxml import etree as ET'),
            (r'import xml\.etree\.ElementTree', 'from lxml import etree as ET'),
            (r'from xml\.etree\.ElementTree import.*', 'from lxml import etree as ET'),
        ]
        
        # Track migration results
        self.migrated_files = []
        self.failed_files = []
        self.skipped_files = []
    
    def create_backup(self, file_path: Path):
        """Create backup of file before migration."""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_path = self.backup_dir / file_path.name
        shutil.copy2(file_path, backup_path)
        print(f"  ✓ Backup created: {backup_path}")
    
    def migrate_file(self, file_path: Path) -> bool:
        """Migrate a single file from ElementTree to lxml."""
        
        print(f"\n🔄 Migrating: {file_path.relative_to(self.project_root)}")
        
        try:
            # Read original content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if migration needed
            needs_migration = any(
                re.search(pattern, content) 
                for pattern, _ in self.migration_patterns
            )
            
            if not needs_migration:
                print("  ⏭️  No migration needed")
                self.skipped_files.append(str(file_path.relative_to(self.project_root)))
                return True
            
            # Create backup
            self.create_backup(file_path)
            
            # Apply migrations
            migrated_content = content
            migration_count = 0
            
            for pattern, replacement in self.migration_patterns:
                if re.search(pattern, migrated_content):
                    migrated_content = re.sub(pattern, replacement, migrated_content)
                    migration_count += 1
                    print(f"  ✓ Applied pattern: {pattern}")
            
            # Write migrated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(migrated_content)
            
            print(f"  ✅ Migration successful ({migration_count} patterns applied)")
            self.migrated_files.append(str(file_path.relative_to(self.project_root)))
            return True
            
        except Exception as e:
            print(f"  ❌ Migration failed: {e}")
            self.failed_files.append(str(file_path.relative_to(self.project_root)))
            return False
    
    def find_files_needing_migration(self) -> List[Path]:
        """Find all Python files that need ElementTree to lxml migration."""
        
        print("🔍 Scanning for files needing migration...")
        
        files_needing_migration = []
        
        # Scan src directory
        src_dir = self.project_root / "src"
        if src_dir.exists():
            for py_file in src_dir.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check if file uses ElementTree
                    for pattern, _ in self.migration_patterns:
                        if re.search(pattern, content):
                            files_needing_migration.append(py_file)
                            break
                            
                except Exception as e:
                    print(f"⚠️  Could not scan {py_file}: {e}")
        
        print(f"📋 Found {len(files_needing_migration)} files needing migration")
        return files_needing_migration
    
    def migrate_all(self) -> Dict[str, List[str]]:
        """Migrate all files that need ElementTree to lxml migration."""
        
        print("🚀 Starting systematic lxml migration...\n")
        
        files_to_migrate = self.find_files_needing_migration()
        
        if not files_to_migrate:
            print("✨ No files need migration - all already using lxml!")
            return self.get_summary()
        
        # Sort files by importance (core modules first)
        priority_modules = [
            'base.py', 'svg2drawingml.py', 'transforms.py', 'viewbox.py',
            'groups.py', 'shapes.py', 'paths.py', 'text.py'
        ]
        
        def file_priority(file_path: Path) -> int:
            """Return priority score for file (lower = higher priority)."""
            filename = file_path.name
            if filename in priority_modules:
                return priority_modules.index(filename)
            elif 'converters' in str(file_path):
                return 100  # Converters medium priority
            elif 'performance' in str(file_path) or 'preprocessing' in str(file_path):
                return 200  # Performance/preprocessing lower priority  
            else:
                return 300  # Other files lowest priority
        
        files_to_migrate.sort(key=file_priority)
        
        # Migrate each file
        for i, file_path in enumerate(files_to_migrate, 1):
            print(f"\n[{i}/{len(files_to_migrate)}]", end=" ")
            self.migrate_file(file_path)
        
        return self.get_summary()
    
    def get_summary(self) -> Dict[str, List[str]]:
        """Get migration summary."""
        return {
            'migrated': self.migrated_files,
            'failed': self.failed_files,
            'skipped': self.skipped_files
        }
    
    def print_summary(self):
        """Print migration summary."""
        
        total = len(self.migrated_files) + len(self.failed_files) + len(self.skipped_files)
        
        print(f"\n" + "="*60)
        print(f"         LXML MIGRATION SUMMARY")
        print(f"="*60)
        print(f"📊 Total files processed: {total}")
        print(f"✅ Successfully migrated: {len(self.migrated_files)}")
        print(f"⏭️  Already using lxml: {len(self.skipped_files)}")  
        print(f"❌ Failed migrations: {len(self.failed_files)}")
        
        if self.migrated_files:
            print(f"\n✅ SUCCESSFULLY MIGRATED:")
            for file in self.migrated_files:
                print(f"   • {file}")
        
        if self.failed_files:
            print(f"\n❌ FAILED MIGRATIONS:")
            for file in self.failed_files:
                print(f"   • {file}")
        
        if self.skipped_files:
            print(f"\n⏭️  ALREADY USING LXML:")
            for file in self.skipped_files[:5]:  # Show first 5
                print(f"   • {file}")
            if len(self.skipped_files) > 5:
                print(f"   ... and {len(self.skipped_files) - 5} more")
        
        print(f"="*60)
        
        if len(self.failed_files) == 0:
            print(f"🎉 Migration completed successfully!")
        else:
            print(f"⚠️  Migration completed with {len(self.failed_files)} failures")
    
    def verify_migrations(self) -> bool:
        """Verify that migrations were successful by checking imports."""
        
        print(f"\n🔍 Verifying migrations...")
        
        verification_failed = []
        
        for file_rel_path in self.migrated_files:
            file_path = self.project_root / file_rel_path
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check that no ElementTree imports remain
                for pattern, _ in self.migration_patterns:
                    if re.search(pattern, content):
                        verification_failed.append(file_rel_path)
                        print(f"  ❌ {file_rel_path} still contains ElementTree imports")
                        break
                else:
                    # Check that lxml import exists
                    if 'from lxml import etree as ET' in content:
                        print(f"  ✅ {file_rel_path} successfully migrated")
                    else:
                        verification_failed.append(file_rel_path)
                        print(f"  ⚠️  {file_rel_path} missing lxml import")
                        
            except Exception as e:
                verification_failed.append(file_rel_path)
                print(f"  ❌ Could not verify {file_rel_path}: {e}")
        
        if verification_failed:
            print(f"\n❌ Verification failed for {len(verification_failed)} files")
            return False
        else:
            print(f"\n✅ All migrations verified successfully!")
            return True


def main():
    """Main migration script."""
    
    # Find project root (assumes script is in scripts/ directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print(f"🎯 Project root: {project_root}")
    
    # Create migrator
    migrator = LxmlMigrator(str(project_root))
    
    # Run migration
    summary = migrator.migrate_all()
    
    # Print summary
    migrator.print_summary()
    
    # Verify migrations
    migrator.verify_migrations()
    
    return summary


if __name__ == "__main__":
    main()
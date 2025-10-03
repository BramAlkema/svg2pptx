#!/usr/bin/env python3
"""
Pipeline Consolidation Implementation Script
Systematically consolidates isolated systems into the main pipeline.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Any

class PipelineConsolidator:
    def __init__(self, project_root: str = "."):
        self.root = Path(project_root)
        self.core_path = self.root / "core"
        self.backup_path = self.root / "consolidation_backup"

        self.changes_made = []
        self.errors = []

    def create_backup(self):
        """Create backup of current state before consolidation"""
        print("📦 Creating backup...")

        if self.backup_path.exists():
            shutil.rmtree(self.backup_path)

        # Backup key files that will be modified
        backup_files = [
            "core/pipeline/converter.py",
            "core/map/base.py",
            "core/services/conversion_services.py",
        ]

        for file_path in backup_files:
            src = self.root / file_path
            if src.exists():
                dst = self.backup_path / file_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                print(f"  ✓ Backed up {file_path}")

    def phase1_service_injection(self):
        """Phase 1: Add ConversionServices to CleanSlateConverter"""
        print("🔧 Phase 1: Implementing Service Dependency Injection...")

        converter_file = self.core_path / "pipeline" / "converter.py"
        if not converter_file.exists():
            self.errors.append("CleanSlateConverter file not found")
            return False

        try:
            content = converter_file.read_text()

            # Check if already modified
            if "self.services =" in content:
                print("  ⚠️  Services already injected, skipping...")
                return True

            # Add import for ConversionServices
            if "from ..services.conversion_services import ConversionServices" not in content:
                # Find appropriate place to add import
                import_section = content.find("from ..io import")
                if import_section != -1:
                    # Add after existing imports
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if "from ..io import" in line:
                            lines.insert(i + 1, "from ..services.conversion_services import ConversionServices")
                            break
                    content = '\n'.join(lines)

            # Modify _initialize_components method
            old_init = """    def _initialize_components(self) -> None:
        \"\"\"Initialize pipeline components based on configuration\"\"\"
        try:
            # Initialize parser
            self.parser = SVGParser()

            # Initialize analyzer
            self.analyzer = SVGAnalyzer()

            # Initialize policy engine with config
            policy_config = PolicyConfig()
            self.policy = PolicyEngine(policy_config)

            # Initialize mappers
            self.mappers = {
                'path': PathMapper(self.policy),
                'textframe': TextMapper(self.policy),
                'group': GroupMapper(self.policy),
                'image': ImageMapper(self.policy)
            }"""

            new_init = """    def _initialize_components(self) -> None:
        \"\"\"Initialize pipeline components based on configuration\"\"\"
        try:
            # Initialize services first
            self.services = ConversionServices.create_default()

            # Initialize parser
            self.parser = SVGParser()

            # Initialize analyzer
            self.analyzer = SVGAnalyzer()

            # Initialize policy engine with config
            policy_config = PolicyConfig()
            self.policy = PolicyEngine(policy_config)

            # Initialize mappers with services
            self.mappers = {
                'path': PathMapper(self.policy, self.services),
                'textframe': TextMapper(self.policy, self.services),
                'group': GroupMapper(self.policy, self.services),
                'image': ImageMapper(self.policy, self.services)
            }"""

            if old_init in content:
                content = content.replace(old_init, new_init)

                # Also update embedder initialization
                old_embedder = "self.embedder = DrawingMLEmbedder("
                new_embedder = "self.embedder = DrawingMLEmbedder("
                # For now, keep embedder unchanged to avoid breaking it

                converter_file.write_text(content)
                self.changes_made.append("Added ConversionServices to CleanSlateConverter")
                print("  ✓ Added service injection to CleanSlateConverter")
                return True
            else:
                self.errors.append("Could not find initialization method pattern")
                return False

        except Exception as e:
            self.errors.append(f"Phase 1 failed: {e}")
            return False

    def phase1_update_mappers(self):
        """Update mapper base class to accept services"""
        print("🗺️  Updating mapper base class...")

        mapper_base = self.core_path / "map" / "base.py"
        if not mapper_base.exists():
            self.errors.append("Mapper base class not found")
            return False

        try:
            content = mapper_base.read_text()

            # Check if already updated
            if "services: ConversionServices" in content:
                print("  ⚠️  Mapper base already updated, skipping...")
                return True

            # Update Mapper class constructor
            old_constructor = """class Mapper:
    \"\"\"Base class for all IR element mappers\"\"\"

    def __init__(self, policy: Policy):
        self.policy = policy"""

            new_constructor = """class Mapper:
    \"\"\"Base class for all IR element mappers\"\"\"

    def __init__(self, policy: Policy, services=None):
        self.policy = policy
        self.services = services"""

            if old_constructor in content:
                content = content.replace(old_constructor, new_constructor)
                mapper_base.write_text(content)
                self.changes_made.append("Updated Mapper base class for service injection")
                print("  ✓ Updated Mapper base class")
                return True
            else:
                print("  ⚠️  Mapper constructor pattern not found, manual update needed")
                return True  # Continue anyway

        except Exception as e:
            self.errors.append(f"Mapper base update failed: {e}")
            return False

    def phase2_create_font_adapter(self):
        """Phase 2: Create FontMapperAdapter"""
        print("📝 Phase 2: Creating FontMapperAdapter...")

        adapter_file = self.core_path / "map" / "font_mapper_adapter.py"

        if adapter_file.exists():
            print("  ⚠️  FontMapperAdapter already exists, skipping creation...")
            return True

        adapter_content = '''"""
FontMapperAdapter - Bridge between TextMapper interface and SmartFontConverter
Integrates the isolated FontHandler system into the main pipeline.
"""

from typing import Any, Dict
from .base import Mapper, MapperResult
from ..ir.text import TextFrame
from ..ir.base import IRElement

try:
    from ..converters.font.smart_converter import SmartFontConverter
    SMART_CONVERTER_AVAILABLE = True
except ImportError:
    SMART_CONVERTER_AVAILABLE = False
    SmartFontConverter = None

class FontMapperAdapter(Mapper):
    """Adapter that integrates SmartFontConverter into the mapper interface"""

    def __init__(self, policy, services=None):
        super().__init__(policy, services)

        if SMART_CONVERTER_AVAILABLE and services:
            try:
                self.smart_converter = SmartFontConverter(services, policy)
                self.use_smart_converter = True
            except Exception as e:
                print(f"Warning: Could not initialize SmartFontConverter: {e}")
                self.use_smart_converter = False
        else:
            self.use_smart_converter = False

        # Fallback to basic text processing
        if not self.use_smart_converter:
            from .text_mapper import TextMapper
            self.fallback_mapper = TextMapper(policy, services)

    def can_map(self, ir_element: IRElement) -> bool:
        """Check if this mapper can handle the element"""
        return hasattr(ir_element, 'element_type') and ir_element.element_type == 'textframe'

    def map(self, ir_element: IRElement) -> MapperResult:
        """Map TextFrame using SmartFontConverter or fallback"""

        if self.use_smart_converter:
            try:
                # Use advanced font processing
                result = self.smart_converter.convert_text_frame(ir_element)
                return MapperResult(
                    drawing_ml=result.drawing_ml,
                    relationships=result.relationships or [],
                    element_type='textframe',
                    success=True
                )
            except Exception as e:
                print(f"SmartFontConverter failed, using fallback: {e}")
                # Fall through to fallback

        # Use fallback TextMapper
        return self.fallback_mapper.map(ir_element)
'''

        try:
            adapter_file.write_text(adapter_content)
            self.changes_made.append("Created FontMapperAdapter")
            print("  ✓ Created FontMapperAdapter")
            return True
        except Exception as e:
            self.errors.append(f"FontMapperAdapter creation failed: {e}")
            return False

    def phase2_integrate_font_adapter(self):
        """Replace TextMapper with FontMapperAdapter in pipeline"""
        print("🔄 Integrating FontMapperAdapter into pipeline...")

        converter_file = self.core_path / "pipeline" / "converter.py"
        if not converter_file.exists():
            self.errors.append("CleanSlateConverter file not found")
            return False

        try:
            content = converter_file.read_text()

            # Add import for FontMapperAdapter
            if "from ..map.font_mapper_adapter import FontMapperAdapter" not in content:
                # Find map imports
                map_import_line = "from ..map import PathMapper, TextMapper, GroupMapper, ImageMapper"
                new_map_import = "from ..map import PathMapper, TextMapper, GroupMapper, ImageMapper\nfrom ..map.font_mapper_adapter import FontMapperAdapter"

                if map_import_line in content:
                    content = content.replace(map_import_line, new_map_import)

            # Replace TextMapper with FontMapperAdapter
            old_mapper_line = "'textframe': TextMapper(self.policy, self.services),"
            new_mapper_line = "'textframe': FontMapperAdapter(self.policy, self.services),"

            if old_mapper_line in content:
                content = content.replace(old_mapper_line, new_mapper_line)
                converter_file.write_text(content)
                self.changes_made.append("Replaced TextMapper with FontMapperAdapter")
                print("  ✓ Integrated FontMapperAdapter into pipeline")
                return True
            else:
                print("  ⚠️  TextMapper line not found, manual integration needed")
                return True

        except Exception as e:
            self.errors.append(f"FontMapperAdapter integration failed: {e}")
            return False

    def validate_changes(self):
        """Validate that changes work correctly"""
        print("✅ Validating changes...")

        try:
            # Test import
            import sys
            sys.path.insert(0, str(self.root))

            from core.pipeline.converter import CleanSlateConverter

            # Test instantiation
            converter = CleanSlateConverter()
            converter._initialize_components()

            # Check that services are available
            if hasattr(converter, 'services') and converter.services:
                print("  ✓ ConversionServices successfully integrated")
            else:
                print("  ⚠️  ConversionServices not found")

            # Check mappers
            if 'textframe' in converter.mappers:
                mapper = converter.mappers['textframe']
                mapper_type = type(mapper).__name__
                print(f"  ✓ Text mapper type: {mapper_type}")

            return True

        except Exception as e:
            self.errors.append(f"Validation failed: {e}")
            return False

    def run_consolidation(self):
        """Run the complete consolidation process"""
        print("🚀 Starting Pipeline Consolidation...")
        print("=" * 60)

        # Create backup
        self.create_backup()

        # Phase 1: Service injection
        if not self.phase1_service_injection():
            print("❌ Phase 1 failed, stopping consolidation")
            return False

        if not self.phase1_update_mappers():
            print("❌ Mapper update failed, stopping consolidation")
            return False

        # Phase 2: Font handler integration
        if not self.phase2_create_font_adapter():
            print("❌ Phase 2a failed, stopping consolidation")
            return False

        if not self.phase2_integrate_font_adapter():
            print("❌ Phase 2b failed, stopping consolidation")
            return False

        # Validate
        if not self.validate_changes():
            print("❌ Validation failed")
            return False

        # Summary
        print("\n" + "=" * 60)
        print("✅ CONSOLIDATION COMPLETE")
        print("=" * 60)

        print(f"\n📝 Changes Made ({len(self.changes_made)}):")
        for change in self.changes_made:
            print(f"  ✓ {change}")

        if self.errors:
            print(f"\n⚠️  Warnings/Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  ⚠️  {error}")

        print(f"\n💾 Backup created at: {self.backup_path}")
        print("\n🧪 Next Steps:")
        print("  1. Run tests to verify functionality")
        print("  2. Test WordArt and text-on-path features")
        print("  3. Continue with Phase 3 (filters) if desired")

        return True

def main():
    consolidator = PipelineConsolidator()
    success = consolidator.run_consolidation()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
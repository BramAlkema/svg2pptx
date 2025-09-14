#!/usr/bin/env python3
"""
Real-World SVG Collection Script

This script helps collect and organize SVG files from real design tools
(Figma, Illustrator, Inkscape, etc.) for E2E testing purposes.
"""

import os
import json
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set
import argparse
import logging
from urllib.parse import urlparse
from dataclasses import dataclass

from svg_test_library import SVGTestLibrary, SourceTool


logger = logging.getLogger(__name__)


@dataclass
class RealWorldSVGSource:
    """Information about a real-world SVG source."""
    name: str
    description: str
    url: Optional[str] = None
    local_path: Optional[Path] = None
    source_tool: str = "unknown"
    license: str = "unknown"
    complexity_expected: str = "medium"


class RealWorldSVGCollector:
    """Collect and organize real-world SVG files for testing."""
    
    def __init__(self, library_path: Path = None):
        """Initialize the collector.
        
        Args:
            library_path: Path to SVG test library
        """
        if library_path is None:
            library_path = Path("tests/test_data/real_world_svgs")
        
        self.library_path = library_path
        self.library = SVGTestLibrary(library_path)
        self.collection_log = library_path / "collection_log.json"
        self.sources_config = library_path / "svg_sources.json"
        
        # Create directory structure
        self.library_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize sources configuration
        self._init_sources_config()
    
    def _init_sources_config(self):
        """Initialize configuration file with known SVG sources."""
        if self.sources_config.exists():
            return
        
        # Curated list of real-world SVG sources
        sources = {
            "figma_community": {
                "name": "Figma Community Icons",
                "description": "SVG icons exported from Figma Community",
                "urls": [
                    "https://www.figma.com/community/file/1166831539721848736",  # Lucide icons
                    "https://www.figma.com/community/file/1076268689892988773"   # Heroicons
                ],
                "source_tool": "figma",
                "complexity_expected": "low",
                "license": "MIT"
            },
            "heroicons": {
                "name": "Heroicons",
                "description": "Beautiful hand-crafted SVG icons from Tailwind CSS team",
                "url": "https://github.com/tailwindlabs/heroicons",
                "source_tool": "illustrator",
                "complexity_expected": "low",
                "license": "MIT"
            },
            "feather_icons": {
                "name": "Feather Icons",
                "description": "Simply beautiful open source icons",
                "url": "https://github.com/feathericons/feather",
                "source_tool": "illustrator",
                "complexity_expected": "low",
                "license": "MIT"
            },
            "material_design": {
                "name": "Material Design Icons",
                "description": "Google's Material Design icon set",
                "url": "https://github.com/google/material-design-icons",
                "source_tool": "illustrator",
                "complexity_expected": "medium",
                "license": "Apache-2.0"
            },
            "inkscape_gallery": {
                "name": "Inkscape Gallery",
                "description": "Community-created artwork from Inkscape",
                "url": "https://inkscape.org/gallery/",
                "source_tool": "inkscape",
                "complexity_expected": "high",
                "license": "various"
            },
            "openclipart": {
                "name": "OpenClipart",
                "description": "Public domain clipart collection",
                "url": "https://openclipart.org/",
                "source_tool": "inkscape",
                "complexity_expected": "medium",
                "license": "public_domain"
            },
            "svgrepo": {
                "name": "SVG Repo",
                "description": "Free SVG vectors and icons",
                "url": "https://www.svgrepo.com/",
                "source_tool": "web",
                "complexity_expected": "low",
                "license": "various"
            }
        }
        
        with open(self.sources_config, 'w') as f:
            json.dump(sources, f, indent=2)
        
        logger.info(f"Created sources configuration: {self.sources_config}")
    
    def add_svg_from_file(self, svg_path: Path, source_info: Dict) -> bool:
        """Add a single SVG file to the real-world collection.
        
        Args:
            svg_path: Path to SVG file
            source_info: Information about the SVG source
            
        Returns:
            True if successfully added
        """
        if not svg_path.exists():
            logger.error(f"SVG file not found: {svg_path}")
            return False
        
        # Validate it's a proper SVG
        if not self.library.validate_svg_file(svg_path):
            logger.error(f"Invalid SVG file: {svg_path}")
            return False
        
        # Generate unique filename to avoid conflicts
        content_hash = self._get_file_hash(svg_path)
        safe_name = self._sanitize_filename(svg_path.stem)
        new_filename = f"{safe_name}_{content_hash[:8]}.svg"
        
        # Add to library with metadata
        success = self.library.add_svg_file(
            svg_path,
            source_tool=source_info.get('source_tool', 'unknown'),
            description=source_info.get('description', ''),
            tags=source_info.get('tags', [])
        )
        
        if success:
            # Log the collection
            self._log_collection(svg_path, source_info, new_filename)
            logger.info(f"Added real-world SVG: {new_filename}")
        
        return success
    
    def add_svg_from_directory(self, directory: Path, source_info: Dict) -> int:
        """Add all SVG files from a directory.
        
        Args:
            directory: Directory containing SVG files
            source_info: Source information for all files
            
        Returns:
            Number of files successfully added
        """
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return 0
        
        added_count = 0
        for svg_file in directory.rglob("*.svg"):
            # Create specific source info for this file
            file_source_info = source_info.copy()
            file_source_info['description'] = f"{source_info.get('description', '')} - {svg_file.relative_to(directory)}"
            
            if self.add_svg_from_file(svg_file, file_source_info):
                added_count += 1
        
        logger.info(f"Added {added_count} SVG files from {directory}")
        return added_count
    
    def download_and_add_figma_export(self, figma_url: str, export_settings: Dict = None) -> bool:
        """Download SVG exports from Figma and add to collection.
        
        Note: This requires Figma API access and is a placeholder for manual export process.
        
        Args:
            figma_url: Figma file URL
            export_settings: Export configuration
            
        Returns:
            True if successful
        """
        logger.warning("Figma API integration not implemented. Please manually export SVGs from Figma.")
        logger.info(f"Manual steps for {figma_url}:")
        logger.info("1. Open the Figma file")
        logger.info("2. Select elements to export")
        logger.info("3. Export as SVG")
        logger.info("4. Use add_svg_from_directory() to add the exported files")
        
        return False
    
    def collect_from_github_repo(self, repo_url: str, svg_pattern: str = "**/*.svg") -> int:
        """Clone a GitHub repo and collect SVG files.
        
        Args:
            repo_url: GitHub repository URL
            svg_pattern: Glob pattern for SVG files
            
        Returns:
            Number of files collected
        """
        import tempfile
        import subprocess
        
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_path = temp_path / repo_name
            
            try:
                # Clone repository
                logger.info(f"Cloning {repo_url}...")
                subprocess.run(['git', 'clone', repo_url, str(repo_path)], 
                             check=True, capture_output=True)
                
                # Find SVG files
                svg_files = list(repo_path.rglob("*.svg"))
                logger.info(f"Found {len(svg_files)} SVG files in {repo_name}")
                
                # Add files to collection
                source_info = {
                    'source_tool': 'web',
                    'description': f"From GitHub repo: {repo_name}",
                    'tags': ['github', 'open_source'],
                    'url': repo_url
                }
                
                added_count = 0
                for svg_file in svg_files[:20]:  # Limit to first 20 files
                    if self.add_svg_from_file(svg_file, source_info):
                        added_count += 1
                
                return added_count
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to clone repository: {e}")
                return 0
            except Exception as e:
                logger.error(f"Error collecting from GitHub repo: {e}")
                return 0
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Get SHA256 hash of file content."""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem usage."""
        import re
        # Remove or replace problematic characters
        safe = re.sub(r'[<>:"/\\|?*]', '_', filename)
        safe = re.sub(r'[^\w\-_.]', '_', safe)
        return safe[:50]  # Limit length
    
    def _log_collection(self, original_path: Path, source_info: Dict, new_filename: str):
        """Log the collection of an SVG file."""
        import datetime
        log_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'original_path': str(original_path),
            'new_filename': new_filename,
            'source_info': source_info,
            'file_size': original_path.stat().st_size
        }
        
        # Load existing log
        log_data = []
        if self.collection_log.exists():
            with open(self.collection_log, 'r') as f:
                log_data = json.load(f)
        
        # Add new entry
        log_data.append(log_entry)
        
        # Save updated log
        with open(self.collection_log, 'w') as f:
            json.dump(log_data, f, indent=2)
    
    def generate_collection_guide(self) -> str:
        """Generate a guide for manually collecting real-world SVGs.
        
        Returns:
            Markdown-formatted collection guide
        """
        guide = """# Real-World SVG Collection Guide

This guide helps you collect SVG files from various design tools for E2E testing.

## Figma Export Process

1. **Access Figma Community Files**:
   - Visit [Figma Community](https://www.figma.com/community)
   - Search for icon sets, illustrations, or UI kits
   - Open files that contain diverse SVG elements

2. **Export SVGs from Figma**:
   - Select individual elements or frames
   - Right-click → "Copy/Paste" → "Copy as SVG"
   - Or use File → Export → SVG
   - Save with descriptive names

3. **Recommended Figma Sources**:
   - Lucide Icons: Clean, minimal icons
   - Heroicons: Tailwind CSS icons
   - Material Design Icons: Google's icon set
   - Feather Icons: Simple, elegant icons

## Adobe Illustrator Export

1. **Create or Open Designs**:
   - Use existing artwork or create test designs
   - Include various shapes, paths, text, and effects

2. **Export Process**:
   - File → Export → Export As
   - Choose SVG format
   - Use "SVG 1.1" profile for compatibility
   - Include CSS properties inline

## Inkscape Export

1. **Community Artwork**:
   - Visit [Inkscape Gallery](https://inkscape.org/gallery/)
   - Download source files
   - Open in Inkscape and export as SVG

2. **Export Settings**:
   - File → Save As → Plain SVG
   - Ensure paths are not simplified
   - Include text as text (not paths)

## Web-Based SVG Sources

1. **Icon Libraries**:
   - [Heroicons](https://heroicons.com/) - Download SVG
   - [Feather Icons](https://feathericons.com/) - Copy SVG code
   - [Material Icons](https://fonts.google.com/icons) - Download SVG

2. **SVG Collections**:
   - [SVG Repo](https://www.svgrepo.com/) - Free SVG downloads
   - [OpenClipart](https://openclipart.org/) - Public domain artwork

## Organization Tips

1. **Categorize by Complexity**:
   - Simple: Basic shapes, single colors
   - Medium: Gradients, text, multiple elements
   - Complex: Filters, animations, complex paths

2. **Name Descriptively**:
   - Include source tool: `figma_icon_home.svg`
   - Include complexity: `complex_illustration_landscape.svg`
   - Include features: `gradient_button_rounded.svg`

3. **Document Sources**:
   - Keep track of original URLs
   - Note licensing information
   - Record export settings used

## Usage with Collection Script

```bash
# Add files from a directory
python tools/collect_real_world_svgs.py --directory ~/Downloads/figma_exports --source figma

# Add individual file
python tools/collect_real_world_svgs.py --file icon.svg --source illustrator --description "Material design icon"

# Collect from GitHub repository
python tools/collect_real_world_svgs.py --github https://github.com/tailwindlabs/heroicons
```

## Target Collection Goals

- **50+ unique SVG files** from different sources
- **Representation from each major tool**: Figma, Illustrator, Inkscape, Web
- **Variety in complexity**: Simple icons to complex illustrations
- **Coverage of all converter modules**: Shapes, paths, text, gradients, etc.

"""
        
        # Save guide to file
        guide_path = self.library_path / "COLLECTION_GUIDE.md"
        with open(guide_path, 'w') as f:
            f.write(guide)
        
        logger.info(f"Generated collection guide: {guide_path}")
        return guide
    
    def get_collection_status(self) -> Dict:
        """Get current collection status and recommendations.
        
        Returns:
            Status report with recommendations
        """
        coverage_report = self.library.get_coverage_report()
        
        # Analyze gaps
        recommendations = []
        
        if coverage_report['total_files'] < 50:
            recommendations.append(f"Need {50 - coverage_report['total_files']} more files to reach baseline")
        
        # Check source tool diversity
        source_tools = coverage_report.get('source_tool_distribution', {})
        missing_tools = []
        for tool in ['figma', 'illustrator', 'inkscape']:
            if source_tools.get(tool, 0) < 5:
                missing_tools.append(tool)
        
        if missing_tools:
            recommendations.append(f"Need more files from: {', '.join(missing_tools)}")
        
        # Check converter module coverage
        module_coverage = coverage_report.get('converter_module_coverage', {})
        low_coverage_modules = [
            module for module, data in module_coverage.items()
            if data['coverage_percentage'] < 40
        ]
        
        if low_coverage_modules:
            recommendations.append(f"Low coverage modules: {', '.join(low_coverage_modules)}")
        
        return {
            'current_status': coverage_report,
            'recommendations': recommendations,
            'collection_complete': len(recommendations) == 0
        }


def main():
    """Main CLI interface for real-world SVG collection."""
    parser = argparse.ArgumentParser(description="Collect real-world SVG files for E2E testing")
    parser.add_argument('--directory', type=Path, help="Directory containing SVG files to add")
    parser.add_argument('--file', type=Path, help="Single SVG file to add")
    parser.add_argument('--github', type=str, help="GitHub repository URL to collect from")
    parser.add_argument('--source', type=str, default='unknown', 
                       choices=['figma', 'illustrator', 'inkscape', 'sketch', 'web', 'unknown'],
                       help="Source tool that created the SVG")
    parser.add_argument('--description', type=str, help="Description of the SVG content")
    parser.add_argument('--tags', nargs='*', help="Tags for categorization")
    parser.add_argument('--status', action='store_true', help="Show collection status")
    parser.add_argument('--guide', action='store_true', help="Generate collection guide")
    parser.add_argument('--library-path', type=Path, help="Path to SVG test library")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Initialize collector
    collector = RealWorldSVGCollector(args.library_path)
    
    if args.guide:
        guide = collector.generate_collection_guide()
        print("📖 Collection guide generated!")
        return
    
    if args.status:
        status = collector.get_collection_status()
        print("📊 Collection Status:")
        print(f"Total files: {status['current_status']['total_files']}")
        print(f"Baseline met: {status['current_status']['baseline_met']}")
        
        if status['recommendations']:
            print("\n🎯 Recommendations:")
            for rec in status['recommendations']:
                print(f"  • {rec}")
        else:
            print("\n✅ Collection goals met!")
        return
    
    # Add files
    source_info = {
        'source_tool': args.source,
        'description': args.description or '',
        'tags': args.tags or []
    }
    
    if args.directory:
        count = collector.add_svg_from_directory(args.directory, source_info)
        print(f"✅ Added {count} SVG files from {args.directory}")
    
    elif args.file:
        success = collector.add_svg_from_file(args.file, source_info)
        if success:
            print(f"✅ Added SVG file: {args.file}")
        else:
            print(f"❌ Failed to add SVG file: {args.file}")
    
    elif args.github:
        count = collector.collect_from_github_repo(args.github)
        print(f"✅ Collected {count} SVG files from GitHub repository")
    
    else:
        print("❌ Please specify --directory, --file, --github, --status, or --guide")
        parser.print_help()


if __name__ == "__main__":
    main()
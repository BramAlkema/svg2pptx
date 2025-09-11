#!/usr/bin/env python3
"""
SVG Test Library Management System

This module provides tools for managing, validating, and categorizing
real-world SVG files used in E2E testing of the conversion pipeline.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from lxml import etree as ET

logger = logging.getLogger(__name__)


class SVGComplexity(Enum):
    """SVG complexity levels for categorization."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SourceTool(Enum):
    """Design tools that generate SVG files."""
    FIGMA = "figma"
    ILLUSTRATOR = "illustrator"
    INKSCAPE = "inkscape"
    SKETCH = "sketch"
    WEB = "web"
    UNKNOWN = "unknown"


@dataclass
class SVGMetadata:
    """Metadata for an SVG test file."""
    filename: str
    source_tool: str
    complexity: str
    features: List[str]
    converter_modules: List[str]
    file_size: int
    element_count: int
    viewport: Dict[str, Any]
    description: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class SVGTestLibrary:
    """Manages a collection of real-world SVG files for E2E testing."""
    
    def __init__(self, library_path: Path):
        """Initialize SVG test library.
        
        Args:
            library_path: Path to directory containing SVG files
        """
        self.library_path = Path(library_path)
        self.metadata_file = self.library_path / "metadata.json"
        self.metadata: Dict[str, SVGMetadata] = {}
        
        # Ensure library directory exists
        self.library_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing metadata if available
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from JSON file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    metadata_dict = json.load(f)
                
                # Convert dict to SVGMetadata objects
                for filename, data in metadata_dict.items():
                    self.metadata[filename] = SVGMetadata(**data)
                    
                logger.info(f"Loaded metadata for {len(self.metadata)} SVG files")
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
                self.metadata = {}
    
    def _save_metadata(self):
        """Save metadata to JSON file."""
        try:
            # Convert SVGMetadata objects to dicts
            metadata_dict = {
                filename: asdict(metadata) 
                for filename, metadata in self.metadata.items()
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata_dict, f, indent=2)
                
            logger.info(f"Saved metadata for {len(self.metadata)} SVG files")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def add_svg_file(self, svg_path: Path, source_tool: str = "unknown", 
                     description: str = None, tags: List[str] = None) -> bool:
        """Add an SVG file to the test library.
        
        Args:
            svg_path: Path to SVG file
            source_tool: Design tool that created the SVG
            description: Optional description of the SVG
            tags: Optional tags for categorization
            
        Returns:
            True if file was added successfully, False otherwise
        """
        if not svg_path.exists():
            logger.error(f"SVG file does not exist: {svg_path}")
            return False
        
        # Validate SVG file
        if not self.validate_svg_file(svg_path):
            logger.error(f"Invalid SVG file: {svg_path}")
            return False
        
        # Copy file to library if not already there
        library_file_path = self.library_path / svg_path.name
        if not library_file_path.exists():
            import shutil
            shutil.copy2(svg_path, library_file_path)
        
        # Extract metadata
        metadata = self.extract_metadata(library_file_path, source_tool, description, tags)
        if metadata:
            self.metadata[svg_path.name] = metadata
            self._save_metadata()
            logger.info(f"Added SVG file to library: {svg_path.name}")
            return True
        
        return False
    
    def validate_svg_file(self, svg_path: Path) -> bool:
        """Validate that a file is a proper SVG.
        
        Args:
            svg_path: Path to SVG file
            
        Returns:
            True if valid SVG, False otherwise
        """
        try:
            # Parse XML directly from file to handle declarations properly
            root = ET.parse(str(svg_path)).getroot()
            
            # Check if root element is SVG
            tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
            if tag != 'svg':
                return False
            
            # Check for basic SVG attributes
            if not (root.get('width') or root.get('viewBox')):
                logger.warning(f"SVG missing width/viewBox: {svg_path}")
            
            return True
            
        except ET.XMLSyntaxError as e:
            logger.error(f"XML syntax error in {svg_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error validating {svg_path}: {e}")
            return False
    
    def extract_metadata(self, svg_path: Path, source_tool: str = "unknown",
                        description: str = None, tags: List[str] = None) -> Optional[SVGMetadata]:
        """Extract metadata from an SVG file.
        
        Args:
            svg_path: Path to SVG file
            source_tool: Design tool that created the SVG
            description: Optional description
            tags: Optional tags
            
        Returns:
            SVGMetadata object or None if extraction failed
        """
        try:
            # Parse XML directly from file to handle declarations properly
            root = ET.parse(str(svg_path)).getroot()
            
            # Extract basic properties
            width = root.get('width', '0')
            height = root.get('height', '0')
            viewbox = root.get('viewBox', f"0 0 {width} {height}")
            
            # Parse viewBox if available
            viewport = {"width": width, "height": height}
            if viewbox:
                try:
                    vb_parts = viewbox.split()
                    if len(vb_parts) == 4:
                        viewport = {
                            "x": float(vb_parts[0]),
                            "y": float(vb_parts[1]),
                            "width": float(vb_parts[2]),
                            "height": float(vb_parts[3])
                        }
                except ValueError:
                    pass
            
            # Count elements and identify features
            element_count = len(list(root.iter()))
            features = self._identify_features(root)
            converter_modules = self._map_converter_modules(root)
            complexity = self._determine_complexity(root, features)
            
            # Get file size
            file_size = svg_path.stat().st_size
            
            metadata = SVGMetadata(
                filename=svg_path.name,
                source_tool=source_tool,
                complexity=complexity.value,
                features=features,
                converter_modules=converter_modules,
                file_size=file_size,
                element_count=element_count,
                viewport=viewport,
                description=description,
                tags=tags or []
            )
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract metadata from {svg_path}: {e}")
            return None
    
    def _identify_features(self, root: ET.Element) -> List[str]:
        """Identify SVG features present in the document.
        
        Args:
            root: SVG root element
            
        Returns:
            List of feature names
        """
        features = set()
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            # Basic shapes
            if tag in ['rect', 'circle', 'ellipse', 'polygon', 'polyline', 'line']:
                features.add('shapes')
            
            # Paths
            elif tag == 'path':
                features.add('paths')
            
            # Text
            elif tag in ['text', 'tspan', 'textPath']:
                features.add('text')
            
            # Gradients
            elif tag in ['linearGradient', 'radialGradient']:
                features.add('gradients')
            
            # Filters
            elif tag == 'filter':
                features.add('filters')
            
            # Animations
            elif tag in ['animate', 'animateTransform', 'animateMotion']:
                features.add('animations')
            
            # Markers
            elif tag == 'marker':
                features.add('markers')
            
            # Clipping and masking
            elif tag in ['clipPath', 'mask']:
                features.add('masking')
            
            # Patterns
            elif tag == 'pattern':
                features.add('patterns')
            
            # Groups and transformations
            elif tag == 'g' and elem.get('transform'):
                features.add('transforms')
            
            # Images
            elif tag == 'image':
                features.add('images')
        
        # Check for CSS styles
        style_elements = root.xpath('.//style')
        if style_elements:
            features.add('css_styles')
        
        return sorted(list(features))
    
    def _map_converter_modules(self, root: ET.Element) -> List[str]:
        """Map SVG elements to converter modules.
        
        Args:
            root: SVG root element
            
        Returns:
            List of converter module names
        """
        modules = set()
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            # Map to converter modules
            if tag in ['rect', 'circle', 'ellipse', 'polygon', 'polyline', 'line']:
                modules.add('shapes')
            elif tag == 'path':
                modules.add('paths')
            elif tag in ['text', 'tspan', 'textPath']:
                modules.add('text')
            elif tag in ['linearGradient', 'radialGradient']:
                modules.add('gradients')
            elif tag == 'filter':
                modules.add('filters')
            elif tag in ['animate', 'animateTransform', 'animateMotion']:
                modules.add('animations')
            elif tag == 'marker':
                modules.add('markers')
            elif tag in ['clipPath', 'mask']:
                modules.add('masking')
            elif tag == 'image':
                modules.add('image')
            elif tag == 'g':
                modules.add('groups')
        
        return sorted(list(modules))
    
    def _determine_complexity(self, root: ET.Element, features: List[str]) -> SVGComplexity:
        """Determine SVG complexity level.
        
        Args:
            root: SVG root element
            features: List of identified features
            
        Returns:
            SVGComplexity enum value
        """
        element_count = len(list(root.iter()))
        
        # High complexity criteria
        if (element_count > 50 or
            any(feature in features for feature in ['filters', 'animations', 'masking']) or
            len(features) > 6):
            return SVGComplexity.HIGH
        
        # Medium complexity criteria
        elif (element_count > 15 or
              any(feature in features for feature in ['gradients', 'patterns', 'transforms']) or
              len(features) > 3):
            return SVGComplexity.MEDIUM
        
        # Low complexity
        else:
            return SVGComplexity.LOW
    
    def get_files_by_complexity(self, complexity: SVGComplexity) -> List[str]:
        """Get list of files by complexity level.
        
        Args:
            complexity: Complexity level to filter by
            
        Returns:
            List of filenames
        """
        return [
            filename for filename, metadata in self.metadata.items()
            if metadata.complexity == complexity.value
        ]
    
    def get_files_by_source_tool(self, source_tool: str) -> List[str]:
        """Get list of files by source tool.
        
        Args:
            source_tool: Source tool to filter by
            
        Returns:
            List of filenames
        """
        return [
            filename for filename, metadata in self.metadata.items()
            if metadata.source_tool == source_tool
        ]
    
    def get_files_by_converter_module(self, module: str) -> List[str]:
        """Get list of files that exercise a specific converter module.
        
        Args:
            module: Converter module name
            
        Returns:
            List of filenames
        """
        return [
            filename for filename, metadata in self.metadata.items()
            if module in metadata.converter_modules
        ]
    
    def get_coverage_report(self) -> Dict[str, Any]:
        """Generate coverage report for the test library.
        
        Returns:
            Dictionary with coverage statistics
        """
        total_files = len(self.metadata)
        
        # Complexity distribution
        complexity_counts = {}
        for complexity in SVGComplexity:
            complexity_counts[complexity.value] = len(self.get_files_by_complexity(complexity))
        
        # Source tool distribution
        source_tools = set(metadata.source_tool for metadata in self.metadata.values())
        source_tool_counts = {}
        for tool in source_tools:
            source_tool_counts[tool] = len(self.get_files_by_source_tool(tool))
        
        # Converter module coverage
        all_modules = ['shapes', 'paths', 'text', 'gradients', 'filters', 
                      'animations', 'markers', 'masking', 'image', 'groups']
        module_coverage = {}
        for module in all_modules:
            files = self.get_files_by_converter_module(module)
            module_coverage[module] = {
                'file_count': len(files),
                'coverage_percentage': (len(files) / total_files * 100) if total_files > 0 else 0
            }
        
        return {
            'total_files': total_files,
            'complexity_distribution': complexity_counts,
            'source_tool_distribution': source_tool_counts,
            'converter_module_coverage': module_coverage,
            'baseline_met': total_files >= 50
        }
    
    def validate_library(self) -> Dict[str, Any]:
        """Validate the entire test library.
        
        Returns:
            Validation results
        """
        results = {
            'valid_files': 0,
            'invalid_files': 0,
            'missing_files': [],
            'validation_errors': []
        }
        
        for filename, metadata in self.metadata.items():
            file_path = self.library_path / filename
            
            if not file_path.exists():
                results['missing_files'].append(filename)
                continue
            
            if self.validate_svg_file(file_path):
                results['valid_files'] += 1
            else:
                results['invalid_files'] += 1
                results['validation_errors'].append(f"Invalid SVG: {filename}")
        
        return results


def create_sample_svg_library(library_path: Path) -> SVGTestLibrary:
    """Create a sample SVG test library for testing.
    
    Args:
        library_path: Path where to create the library
        
    Returns:
        SVGTestLibrary instance with sample files
    """
    library = SVGTestLibrary(library_path)
    
    # Sample SVG files for testing
    sample_svgs = {
        "simple_rect.svg": '''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
</svg>''',
        
        "gradient_circle.svg": '''<?xml version="1.0"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <radialGradient id="grad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" style="stop-color:yellow;stop-opacity:1" />
            <stop offset="100%" style="stop-color:red;stop-opacity:1" />
        </radialGradient>
    </defs>
    <circle cx="100" cy="100" r="80" fill="url(#grad)"/>
</svg>''',
        
        "complex_design.svg": '''<?xml version="1.0"?>
<svg width="300" height="300" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
        <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                refX="10" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="black" />
        </marker>
    </defs>
    <rect x="10" y="10" width="100" height="60" fill="url(#grad1)"/>
    <circle cx="200" cy="50" r="30" fill="green"/>
    <path d="M 50 150 Q 100 100 150 150 T 250 150" stroke="blue" 
          stroke-width="3" fill="none" marker-end="url(#arrowhead)"/>
    <text x="150" y="200" text-anchor="middle" font-family="Arial" 
          font-size="16" fill="purple">Complex SVG</text>
    <g transform="rotate(45 250 250)">
        <rect x="230" y="230" width="40" height="40" fill="orange"/>
    </g>
</svg>'''
    }
    
    # Create sample files
    for filename, content in sample_svgs.items():
        file_path = library_path / filename
        with open(file_path, 'w') as f:
            f.write(content)
        
        # Add to library with metadata
        if filename == "simple_rect.svg":
            library.add_svg_file(file_path, "inkscape", "Simple rectangle test", ["basic", "shapes"])
        elif filename == "gradient_circle.svg":
            library.add_svg_file(file_path, "illustrator", "Gradient circle test", ["gradients", "shapes"])
        elif filename == "complex_design.svg":
            library.add_svg_file(file_path, "figma", "Complex multi-element design", ["complex", "comprehensive"])
    
    return library
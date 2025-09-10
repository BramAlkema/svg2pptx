"""
Main SVG optimizer class that orchestrates preprocessing plugins.
"""

from lxml import etree as ET
from typing import List, Dict, Any, Optional
from .base import PreprocessingPlugin, PreprocessingContext, PluginRegistry
from .plugins import (
    CleanupAttrsPlugin,
    CleanupNumericValuesPlugin,
    RemoveEmptyAttrsPlugin,
    RemoveEmptyContainersPlugin,
    RemoveCommentsPlugin,
    ConvertColorsPlugin,
    CollapseGroupsPlugin,
    RemoveUnusedNamespacesPlugin,
    ConvertShapeToPathPlugin
)

from .advanced_plugins import (
    ConvertPathDataPlugin,
    MergePathsPlugin,
    ConvertTransformPlugin,
    RemoveUselessStrokeAndFillPlugin,
    RemoveHiddenElementsPlugin,
    MinifyStylesPlugin,
    SortAttributesPlugin,
    RemoveUnknownsAndDefaultsPlugin
)

from .geometry_plugins import (
    ConvertEllipseToCirclePlugin,
    SimplifyPolygonPlugin,
    OptimizeViewBoxPlugin,
    SimplifyTransformMatrixPlugin,
    RemoveEmptyDefsPlugin,
    ConvertStyleToAttrsPlugin
)


class SVGOptimizer:
    """Main SVG optimizer that applies preprocessing plugins."""
    
    MINIMAL_PLUGINS = [
        CleanupAttrsPlugin,
        RemoveEmptyAttrsPlugin,
        RemoveCommentsPlugin,
        ConvertColorsPlugin,
        RemoveUnusedNamespacesPlugin,
    ]
    
    DEFAULT_PLUGINS = MINIMAL_PLUGINS + [
        CleanupNumericValuesPlugin,
        RemoveEmptyContainersPlugin,
        RemoveUselessStrokeAndFillPlugin,
        RemoveHiddenElementsPlugin,
        ConvertEllipseToCirclePlugin,
        SortAttributesPlugin,
        RemoveUnknownsAndDefaultsPlugin,
        RemoveEmptyDefsPlugin,
    ]
    
    AGGRESSIVE_PLUGINS = DEFAULT_PLUGINS + [
        ConvertPathDataPlugin,
        MergePathsPlugin,
        ConvertTransformPlugin,
        MinifyStylesPlugin,
        SimplifyPolygonPlugin,
        OptimizeViewBoxPlugin,
        SimplifyTransformMatrixPlugin,
        ConvertStyleToAttrsPlugin,
        ConvertShapeToPathPlugin,  # Keep this last as it changes element types
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.registry = PluginRegistry()
        self._initialize_plugins()
    
    def _initialize_plugins(self):
        """Initialize plugins based on configuration."""
        plugin_config = self.config.get('plugins', {})
        
        # Determine which plugin set to use
        preset = self.config.get('preset', 'default')
        if preset == 'minimal':
            plugin_classes = self.MINIMAL_PLUGINS
        elif preset == 'aggressive':
            plugin_classes = self.AGGRESSIVE_PLUGINS
        else:
            plugin_classes = self.DEFAULT_PLUGINS
        
        # Register plugins with their configurations
        for plugin_class in plugin_classes:
            plugin_name = plugin_class.name
            individual_config = plugin_config.get(plugin_name, {})
            
            # Check if plugin is disabled
            if individual_config.get('enabled', True):
                plugin = plugin_class(individual_config)
                self.registry.register(plugin)
    
    def optimize(self, svg_content: str) -> str:
        """Optimize SVG content using registered plugins."""
        try:
            # Parse SVG - handle encoding declaration properly
            if isinstance(svg_content, str):
                # If content has XML declaration, encode to bytes first
                if svg_content.strip().startswith('<?xml'):
                    svg_bytes = svg_content.encode('utf-8')
                    root = ET.fromstring(svg_bytes)
                else:
                    root = ET.fromstring(svg_content)
            else:
                root = ET.fromstring(svg_content)
            
            # Create preprocessing context
            context = PreprocessingContext()
            context.precision = self.config.get('precision', 3)
            
            # Apply plugins multiple times if needed
            max_passes = self.config.get('multipass', False) and 3 or 1
            
            for pass_num in range(max_passes):
                context.modifications_made = False
                self._process_element_tree(root, context)
                
                # Remove elements marked for removal
                self._remove_marked_elements(root, context)
                
                # If no modifications were made, we're done
                if not context.modifications_made:
                    break
            
            # Convert back to string
            return self._element_to_string(root)
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid SVG content: {e}")
    
    def _process_element_tree(self, root: ET.Element, context: PreprocessingContext):
        """Process the entire element tree with all plugins."""
        # Process in post-order (children first) to handle removals properly
        for element in list(root):
            self._process_element_tree(element, context)
        
        # Process current element
        self._process_single_element(root, context)
    
    def _process_single_element(self, element: ET.Element, context: PreprocessingContext):
        """Process a single element with all applicable plugins."""
        plugins = self.registry.get_enabled_plugins()
        
        for plugin in plugins:
            if plugin.can_process(element, context):
                try:
                    modified = plugin.process(element, context)
                    if modified:
                        context.modifications_made = True
                except Exception as e:
                    # Log error but continue with other plugins
                    print(f"Plugin {plugin.name} failed on element {element.tag}: {e}")
    
    def _remove_marked_elements(self, root: ET.Element, context: PreprocessingContext):
        """Remove elements that were marked for removal."""
        def remove_marked_recursive(parent: ET.Element):
            for child in list(parent):
                if child in context.removed_elements:
                    parent.remove(child)
                    context.modifications_made = True
                else:
                    remove_marked_recursive(child)
        
        remove_marked_recursive(root)
        context.removed_elements.clear()
    
    def _element_to_string(self, root: ET.Element) -> str:
        """Convert element tree back to string with proper formatting."""
        # Register namespaces to avoid ns0: prefixes (skip empty prefix for lxml)
        namespaces = {
            'xlink': 'http://www.w3.org/1999/xlink'
        }
        
        for prefix, uri in namespaces.items():
            if prefix:  # Skip empty prefix for lxml compatibility
                ET.register_namespace(prefix, uri)
        
        # Convert to string
        xml_str = ET.tostring(root, encoding='unicode', method='xml')
        
        # Clean up the output
        if self.config.get('pretty', False):
            return self._prettify_xml(xml_str)
        else:
            # Normalize all whitespace for consistent output
            import re
            # Remove all newlines and normalize spaces between tags
            normalized = re.sub(r'\s+', ' ', xml_str.replace('\n', ' '))
            # Clean up spaces around tag boundaries
            normalized = re.sub(r'>\s+<', '><', normalized)
            normalized = re.sub(r'>\s+([^<])', r'>\1', normalized)
            normalized = re.sub(r'([^>])\s+<', r'\1<', normalized)
            return normalized.strip()
    
    def _prettify_xml(self, xml_str: str) -> str:
        """Add basic pretty printing to XML."""
        import re
        
        # Add newlines after major elements
        xml_str = re.sub(r'><', '>\\n<', xml_str)
        
        # Basic indentation (simplified)
        lines = xml_str.split('\\n')
        indented_lines = []
        indent_level = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('</'):
                indent_level -= 1
            
            indented_lines.append('  ' * indent_level + line)
            
            if line.startswith('<') and not line.startswith('</') and not line.endswith('/>'):
                indent_level += 1
        
        return '\\n'.join(indented_lines)
    
    def get_stats(self, context: PreprocessingContext) -> Dict[str, int]:
        """Get optimization statistics."""
        return context.stats.copy()


def create_optimizer(preset: str = "default", **kwargs) -> SVGOptimizer:
    """Create an SVG optimizer with a specific preset configuration."""
    
    presets = {
        "minimal": {
            "plugins": {
                "cleanupAttrs": {"enabled": True},
                "removeEmptyAttrs": {"enabled": True},
                "removeComments": {"enabled": True},
            }
        },
        "default": {
            "precision": 3,
            "plugins": {
                "cleanupAttrs": {"enabled": True},
                "cleanupNumericValues": {"enabled": True},
                "removeEmptyAttrs": {"enabled": True},
                "removeEmptyContainers": {"enabled": True},
                "convertColors": {"enabled": True},
                "removeUnusedNS": {"enabled": True},
            }
        },
        "aggressive": {
            "preset": "aggressive",
            "precision": 2,
            "multipass": True,
            "plugins": {
                "cleanupAttrs": {"enabled": True},
                "cleanupNumericValues": {"enabled": True},
                "removeEmptyAttrs": {"enabled": True},
                "removeEmptyContainers": {"enabled": True},
                "convertColors": {"enabled": True},
                "collapseGroups": {"enabled": True},
                "removeUnusedNS": {"enabled": True},
                "convertShapeToPath": {"enabled": True},
            }
        }
    }
    
    config = presets.get(preset, presets["default"]).copy()
    config.update(kwargs)
    
    return SVGOptimizer(config)
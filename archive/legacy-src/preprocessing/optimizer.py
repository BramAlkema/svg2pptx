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

from .resolve_clippath_plugin import ResolveClipPathsPlugin

# SVGO-style plugin aliases (kebab-case names -> plugin classes)
SVGO_ALIASES = {
    # Basic plugins
    'cleanup-attrs': CleanupAttrsPlugin,
    'cleanup-numeric-values': CleanupNumericValuesPlugin,
    'remove-empty-attrs': RemoveEmptyAttrsPlugin,
    'remove-empty-containers': RemoveEmptyContainersPlugin,
    'remove-comments': RemoveCommentsPlugin,
    'convert-colors': ConvertColorsPlugin,
    'collapse-groups': CollapseGroupsPlugin,
    'remove-unused-namespaces': RemoveUnusedNamespacesPlugin,
    'convert-shape-to-path': ConvertShapeToPathPlugin,

    # Advanced plugins
    'convert-path-data': ConvertPathDataPlugin,
    'merge-paths': MergePathsPlugin,
    'convert-transform': ConvertTransformPlugin,
    'remove-useless-stroke-and-fill': RemoveUselessStrokeAndFillPlugin,
    'remove-hidden-elements': RemoveHiddenElementsPlugin,
    'minify-styles': MinifyStylesPlugin,
    'sort-attrs': SortAttributesPlugin,
    'remove-unknowns-and-defaults': RemoveUnknownsAndDefaultsPlugin,

    # Geometry plugins
    'convert-ellipse-to-circle': ConvertEllipseToCirclePlugin,
    'simplify-polygon': SimplifyPolygonPlugin,
    'optimize-viewbox': OptimizeViewBoxPlugin,
    'simplify-transform-matrix': SimplifyTransformMatrixPlugin,
    'remove-empty-defs': RemoveEmptyDefsPlugin,
    'convert-style-to-attrs': ConvertStyleToAttrsPlugin,

    # ClipPath resolution
    'resolve-clippath': ResolveClipPathsPlugin,
}

# SVGO preset-default plugin list (mirrors SVGO's preset-default)
SVGO_PRESET_DEFAULT = [
    'cleanup-attrs',
    # 'inline-styles',          # Skip if not implemented
    # 'remove-doctype',         # Skip - not applicable
    # 'remove-xml-proc-inst',   # Skip - not applicable
    'remove-comments',
    # 'remove-metadata',        # Skip if not implemented
    # 'remove-title',           # Skip if not implemented
    # 'remove-desc',            # Skip if not implemented
    'remove-unknowns-and-defaults',
    'remove-useless-stroke-and-fill',
    'remove-unused-namespaces',
    # 'remove-editors-namespaces',  # Skip if not implemented
    'cleanup-numeric-values',
    'convert-colors',
    'remove-empty-attrs',
    'remove-hidden-elements',
    'remove-empty-containers',
    # 'remove-viewbox',         # DO NOT enable by default; use optimize-viewbox instead
    # 'cleanup-enable-background',  # Skip
    'convert-path-data',
    'convert-transform',
    # 'remove-empty-text',      # Skip if not implemented
    'collapse-groups',
    'merge-paths',
    'convert-style-to-attrs',
    'sort-attrs',
    'remove-empty-defs',
    'simplify-transform-matrix',
    'optimize-viewbox',
    'convert-ellipse-to-circle',
    'simplify-polygon',
    # 'convert-shape-to-path'   # Usually *off* in SVGO preset-default; keep optional
]

def _resolve_svgo_plugin(entry):
    """
    Resolve SVGO-style plugin configuration entries.

    Accepts:
      - "plugin-name" (string)
      - {"plugin-name": True/False} (boolean enable/disable)
      - {"plugin-name": {"param": val, ...}} (object with parameters)

    Returns:
        tuple: (plugin_class, enabled, params) or (None, False, {})
    """
    if isinstance(entry, str):
        name, enabled, params = entry, True, {}
    elif isinstance(entry, dict) and entry:
        name, val = next(iter(entry.items()))
        if isinstance(val, bool):
            enabled, params = val, {}
        elif isinstance(val, dict):
            enabled, params = True, val
        else:
            enabled, params = True, {}
    else:
        return None, False, {}

    cls = SVGO_ALIASES.get(name)
    return cls, bool(enabled), (params or {})


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
        """Initialize plugins based on configuration (supports SVGO-style config)."""
        cfg = self.config
        plugin_cfg = cfg.get('plugins', {})

        # 1) Determine plugin list:
        #    - if user passed a list -> SVGO style, use as-is (order matters)
        #    - elif 'preset' == 'aggressive' -> your aggressive list
        #    - else if 'preset' == 'svgo' or 'preset-default' -> SVGO_PRESET_DEFAULT
        #    - else -> your DEFAULT_PLUGINS
        plugin_entries = cfg.get('plugins_list')  # Allow explicit list via key
        if plugin_entries is None and isinstance(plugin_cfg, list):
            plugin_entries = plugin_cfg

        selected = []
        if plugin_entries:
            # SVGO-style list
            for entry in plugin_entries:
                cls, enabled, params = _resolve_svgo_plugin(entry)
                if cls and enabled:
                    selected.append((cls, params))
        else:
            preset = cfg.get('preset', 'default')
            if preset in ('svgo', 'preset-default'):
                for name in SVGO_PRESET_DEFAULT:
                    cls = SVGO_ALIASES.get(name)
                    if cls:
                        params = plugin_cfg.get(name, {})
                        enabled = params.get('enabled', True) if isinstance(params, dict) else True
                        if enabled:
                            selected.append((cls, params if isinstance(params, dict) else {}))
            elif preset == 'aggressive':
                for cls in self.AGGRESSIVE_PLUGINS:
                    plugin_name = getattr(cls, 'name', cls.__name__)
                    params = plugin_cfg.get(plugin_name, {})
                    if params.get('enabled', True) if isinstance(params, dict) else True:
                        selected.append((cls, params if isinstance(params, dict) else {}))
            elif preset == 'minimal':
                for cls in self.MINIMAL_PLUGINS:
                    plugin_name = getattr(cls, 'name', cls.__name__)
                    params = plugin_cfg.get(plugin_name, {})
                    if params.get('enabled', True) if isinstance(params, dict) else True:
                        selected.append((cls, params if isinstance(params, dict) else {}))
            else:
                for cls in self.DEFAULT_PLUGINS:
                    plugin_name = getattr(cls, 'name', cls.__name__)
                    params = plugin_cfg.get(plugin_name, {})
                    if params.get('enabled', True) if isinstance(params, dict) else True:
                        selected.append((cls, params if isinstance(params, dict) else {}))

        # 2) Register plugins in that order
        for cls, params in selected:
            plugin = cls(params)
            self.registry.register(plugin)

        # 3) Precision/multipass compatibility with SVGO
        #    SVGO calls it floatPrecision
        prec = self.config.get('floatPrecision', self.config.get('precision', 3))
        self.config['precision'] = prec
        if 'multipass' not in self.config and self.config.get('passCount'):
            self.config['multipass'] = True
            self.config['maxPasses'] = int(self.config['passCount'])
    
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
            
            # Apply plugins multiple times if needed (SVGO-style multipass)
            max_passes = self.config.get('maxPasses')
            if not max_passes:
                max_passes = 3 if self.config.get('multipass', False) else 1
            
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
        """Add pretty printing to XML with configurable indentation."""
        import re

        # Get indent size from config (SVGO-compatible)
        indent_size = int(self.config.get('indent', 2))
        indent_char = ' ' * indent_size

        # Add newlines after major elements
        xml_str = re.sub(r'><', '>\\n<', xml_str)

        # Basic indentation
        lines = xml_str.split('\\n')
        indented_lines = []
        indent_level = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('</'):
                indent_level -= 1

            indented_lines.append(indent_char * indent_level + line)

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


# Example SVGO-style configuration that now works:
"""
cfg = {
  "preset": "preset-default",     # or "svgo"
  "floatPrecision": 2,
  "multipass": True,
  "indent": 2,
  "plugins": [
    "cleanup-attrs",
    {"cleanup-numeric-values": {"floatPrecision": 2}},
    "remove-comments",
    "remove-empty-attrs",
    {"convert-path-data": {"straightCurves": True}},
    {"merge-paths": {"force": False}},
    "collapse-groups",
    {"convert-style-to-attrs": True},
    {"convert-shape-to-path": False}   # explicit off
  ]
}
optimizer = SVGOptimizer(cfg)
result = optimizer.optimize(svg_string)
"""
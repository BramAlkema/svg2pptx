"""
Base classes for SVG preprocessing plugins.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET


class PreprocessingPlugin(ABC):
    """Base class for SVG preprocessing plugins."""
    
    name: str = ""
    description: str = ""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
    
    @abstractmethod
    def can_process(self, element: ET.Element, context: 'PreprocessingContext') -> bool:
        """Check if this plugin can process the given element."""
        pass
    
    @abstractmethod
    def process(self, element: ET.Element, context: 'PreprocessingContext') -> bool:
        """Process the element. Return True if modifications were made."""
        pass


class PreprocessingContext:
    """Context object passed between preprocessing plugins."""
    
    def __init__(self):
        self.modifications_made = False
        self.removed_elements: List[ET.Element] = []
        self.stats: Dict[str, int] = {}
        self.precision = 3  # Default decimal precision
        
    def record_modification(self, plugin_name: str, modification_type: str):
        """Record that a modification was made."""
        self.modifications_made = True
        key = f"{plugin_name}_{modification_type}"
        self.stats[key] = self.stats.get(key, 0) + 1
    
    def mark_for_removal(self, element: ET.Element):
        """Mark an element for removal."""
        self.removed_elements.append(element)


class PluginRegistry:
    """Registry for preprocessing plugins."""
    
    def __init__(self):
        self.plugins: List[PreprocessingPlugin] = []
    
    def register(self, plugin: PreprocessingPlugin):
        """Register a preprocessing plugin."""
        self.plugins.append(plugin)
    
    def get_enabled_plugins(self) -> List[PreprocessingPlugin]:
        """Get all enabled plugins."""
        return [p for p in self.plugins if p.enabled]
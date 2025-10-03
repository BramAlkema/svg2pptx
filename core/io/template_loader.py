#!/usr/bin/env python3
"""
Template Loader for PowerPoint XML Templates

Loads and parses XML templates from the templates directory,
providing a clean interface for template-based XML generation.
"""

import os
import copy
import logging
from pathlib import Path
from typing import Dict, Optional
from lxml import etree as ET
from lxml.etree import Element

logger = logging.getLogger(__name__)

class TemplateLoader:
    """
    Loads and manages XML templates for PowerPoint generation.

    Provides caching and validation for template files.
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize template loader.

        Args:
            templates_dir: Directory containing template files.
                          Defaults to core/io/templates/
        """
        if templates_dir is None:
            # Default to templates directory relative to this file
            current_dir = Path(__file__).parent
            templates_dir = current_dir / "templates"

        self.templates_dir = Path(templates_dir)
        self._template_cache: Dict[str, Element] = {}

        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {self.templates_dir}")

        logger.info(f"TemplateLoader initialized with directory: {self.templates_dir}")

    def load_template(self, template_name: str) -> Element:
        """
        Load a template file and return the root element.

        Args:
            template_name: Name of template file (e.g., 'presentation.xml')

        Returns:
            Root element of the parsed template

        Raises:
            FileNotFoundError: If template file doesn't exist
            ET.XMLSyntaxError: If template has invalid XML
        """
        # Check cache first
        if template_name in self._template_cache:
            # Return a deep copy to prevent modifications affecting the cache
            return self._deep_copy_element(self._template_cache[template_name])

        # Load from file
        template_path = self.templates_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        try:
            # Read as bytes to handle XML declarations properly
            with open(template_path, 'rb') as f:
                template_content = f.read()

            # Parse XML from bytes
            root = ET.fromstring(template_content)

            # Cache the original
            self._template_cache[template_name] = root

            # Return a copy
            return self._deep_copy_element(root)

        except ET.XMLSyntaxError as e:
            logger.error(f"Invalid XML in template {template_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {e}")
            raise

    def _deep_copy_element(self, element: Element) -> Element:
        """
        Create a deep copy of an XML element.

        Args:
            element: Element to copy

        Returns:
            Deep copy of the element
        """
        # Use copy.deepcopy for ~3x better performance than serialize+parse
        return copy.deepcopy(element)

    def get_available_templates(self) -> list[str]:
        """
        Get list of available template files.

        Returns:
            List of template filenames
        """
        try:
            return [f.name for f in self.templates_dir.iterdir()
                   if f.is_file() and f.suffix == '.xml']
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return []

    def validate_template(self, template_name: str) -> bool:
        """
        Validate that a template file contains well-formed XML.

        Args:
            template_name: Name of template to validate

        Returns:
            True if template is valid, False otherwise
        """
        try:
            self.load_template(template_name)
            return True
        except Exception as e:
            logger.warning(f"Template validation failed for {template_name}: {e}")
            return False

    def clear_cache(self):
        """Clear the template cache."""
        self._template_cache.clear()
        logger.info("Template cache cleared")


# Singleton instance for global access
_default_loader: Optional[TemplateLoader] = None

def get_template_loader() -> TemplateLoader:
    """
    Get the default template loader instance.

    Returns:
        Default TemplateLoader instance
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = TemplateLoader()
    return _default_loader


def load_template(template_name: str) -> Element:
    """
    Convenience function to load a template using the default loader.

    Args:
        template_name: Name of template file

    Returns:
        Root element of the template
    """
    return get_template_loader().load_template(template_name)
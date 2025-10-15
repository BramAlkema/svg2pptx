"""Template loading and caching for PPTX package assembly."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Dict

from lxml import etree as ET


class TemplateStore:
    """Load PPTX XML templates and provide mutable copies on demand."""

    def __init__(self, template_root: Path | None = None) -> None:
        default_root = Path(__file__).parents[2] / 'pptx_templates' / 'clean_slate'
        self.template_root = template_root or default_root
        self._cache: Dict[str, ET._Element] = {}
        self._parser = ET.XMLParser(remove_blank_text=False)

    def load(self, relative_path: str) -> ET._Element:
        """Return a mutable copy of the requested template XML element."""
        if relative_path not in self._cache:
            template_path = self.template_root / relative_path
            if not template_path.exists():
                raise FileNotFoundError(f"Template '{relative_path}' not found at {template_path}")

            with template_path.open('rb') as handle:
                self._cache[relative_path] = ET.fromstring(handle.read(), parser=self._parser)

        return copy.deepcopy(self._cache[relative_path])


__all__ = ["TemplateStore"]

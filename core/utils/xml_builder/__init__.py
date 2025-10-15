"""XML builder package for PPTX template generation."""

from importlib import util as _importlib_util
from pathlib import Path as _Path

from .animation import AnimationGenerator
from .constants import (
    A_URI,
    CONTENT_NSMAP,
    CONTENT_TYPES_URI,
    NSMAP,
    P_URI,
    R_URI,
    RELATIONSHIPS_NSMAP,
    RELATIONSHIPS_URI,
)
from .fluent import FluentShapeBuilder
from .builder import (
    EnhancedXMLBuilder,
    enhanced_xml_builder,
    get_enhanced_xml_builder,
)
from .utils import (
    create_animation,
    create_content_types,
    create_presentation,
    create_relationships,
    create_shape,
    create_slide,
)
from .base import XMLBuilderBase

_legacy_path = _Path(__file__).resolve().parent.parent / "xml_builder.py"
_legacy_spec = _importlib_util.spec_from_file_location(
    "core.utils._xml_builder_legacy", _legacy_path
)
_legacy_module = _importlib_util.module_from_spec(_legacy_spec)
assert _legacy_spec and _legacy_spec.loader  # pragma: no cover - sanity check
_legacy_spec.loader.exec_module(_legacy_module)

XMLBuilder = _legacy_module.XMLBuilder
create_presentation_xml = _legacy_module.create_presentation_xml
create_slide_xml = _legacy_module.create_slide_xml
create_content_types_xml = _legacy_module.create_content_types_xml
create_animation_xml = _legacy_module.create_animation_xml
get_xml_builder = _legacy_module.get_xml_builder

__all__ = [
    "A_URI",
    "CONTENT_NSMAP",
    "CONTENT_TYPES_URI",
    "NSMAP",
    "P_URI",
    "R_URI",
    "RELATIONSHIPS_NSMAP",
    "RELATIONSHIPS_URI",
    "XMLBuilderBase",
    "EnhancedXMLBuilder",
    "XMLBuilder",
    "AnimationGenerator",
    "FluentShapeBuilder",
    "enhanced_xml_builder",
    "get_enhanced_xml_builder",
    "get_xml_builder",
    "create_presentation",
    "create_slide",
    "create_shape",
    "create_content_types",
    "create_relationships",
    "create_animation",
    "create_presentation_xml",
    "create_slide_xml",
    "create_content_types_xml",
    "create_animation_xml",
]

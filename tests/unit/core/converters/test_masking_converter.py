#!/usr/bin/env python3
from __future__ import annotations

import importlib
import sys
import types

import pytest
from lxml import etree as ET

# Provide lightweight stubs for optional dependencies that are absent in the
# trimmed-down test environment.
if "colorspacious" not in sys.modules:
    colorspacious_stub = types.ModuleType("colorspacious")
    colorspacious_stub.cspace_convert = lambda values, *_args, **_kwargs: values
    sys.modules["colorspacious"] = colorspacious_stub

if "core.converters.boolean_flattener" not in sys.modules:
    bf_module = types.ModuleType("core.converters.boolean_flattener")

    class _StubBooleanFlattener:
        def __init__(self, services):
            self.calls = []

        def flatten_nested_clipaths(self, clip_chain):
            self.calls.append(tuple(clip_chain))
            return "<flattened/>"

    bf_module.BooleanFlattener = _StubBooleanFlattener
    sys.modules["core.converters.boolean_flattener"] = bf_module

if "core.emf_packaging" not in sys.modules:
    emf_module = types.ModuleType("core.emf_packaging")

    class _StubEMFRelationshipManager:
        def __init__(self):
            self._counter = 0

        def add_emf_blob(self, _data, _name):
            self._counter += 1
            return f"rId{self._counter}"

    emf_module.EMFRelationshipManager = _StubEMFRelationshipManager
    sys.modules["core.emf_packaging"] = emf_module

if "core.emf_blob" not in sys.modules:
    from core.emf import emf_blob as _emf_blob_module

    sys.modules["core.emf_blob"] = _emf_blob_module

base_module = importlib.import_module("core.converters.base")
if not hasattr(base_module, "BaseConverter"):
    class _BaseConverter:
        def __init__(self, services):
            self.services = services

    base_module.BaseConverter = _BaseConverter

from core.converters.masking import MaskType, MaskingConverter
from core.converters.clippath_types import (
    ClipPathAnalysis,
    ClipPathComplexity,
    ClipPathDefinition,
    ClippingType,
)
from core.converters.base import ConversionContext
from core.services.conversion_services import ConversionServices


class StubConversionContext(ConversionContext):
    """Minimal conversion context with deterministic shape ids."""

    def __init__(self, svg_root, services):
        super().__init__(svg_root=svg_root, services=services)
        self._shape_id = 1

    def get_next_shape_id(self) -> int:
        shape_id = self._shape_id
        self._shape_id += 1
        return shape_id


@pytest.fixture(scope="module")
def services():
    svc = ConversionServices.create_default()

    # Provide compatibility shims for legacy converter helpers.
    unit_converter = svc.unit_converter
    if not hasattr(unit_converter, "convert_to_emu"):
        unit_converter.convert_to_emu = lambda value: unit_converter.to_emu(value)
    if not hasattr(unit_converter, "convert_to_user_units"):
        unit_converter.convert_to_user_units = lambda value: unit_converter.to_pixels(
            value
        )
    return svc


def _make_converter(services):
    converter = MaskingConverter(services)

    # Replace heavy dependencies with lightweight stubs for deterministic tests.
    converter.boolean_flattener = types.SimpleNamespace(
        flatten_nested_clipaths=lambda chain: "<flattened/>"
    )
    converter.custgeom_generator = types.SimpleNamespace(
        can_generate_custgeom=lambda clip_def: True,
        generate_custgeom_xml=lambda clip_def, context: "<a:custGeom/>",
    )
    return converter


def _make_context(services):
    svg_root = ET.Element("svg")
    return StubConversionContext(svg_root=svg_root, services=services)


class TestMaskDefinitions:
    def test_process_mask_definition_records_alpha_mask(self, services):
        converter = _make_converter(services)
        context = _make_context(services)

        mask_xml = """
        <mask id="alphaMask" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" mask-type="alpha"
              x="10" y="20" width="30" height="40" opacity="0.75">
          <rect x="0" y="0" width="10" height="10"/>
        </mask>
        """
        mask_element = ET.fromstring(mask_xml)

        output = converter._process_mask_definition(mask_element, context)

        assert output == ""
        assert "alphaMask" in converter.mask_definitions
        definition = converter.mask_definitions["alphaMask"]
        assert definition.mask_type == MaskType.ALPHA
        assert definition.width == pytest.approx(30.0)
        assert definition.opacity == pytest.approx(0.75)
        assert len(definition.content_elements) == 1


class TestMaskApplication:
    def test_object_bbox_mask_generates_powerpoint_output(self, services):
        converter = _make_converter(services)
        context = _make_context(services)

        mask_element = ET.fromstring(
            """
            <mask id="bboxMask" maskUnits="objectBoundingBox" maskContentUnits="objectBoundingBox">
              <rect x="0" y="0" width="1" height="1"/>
            </mask>
            """
        )
        converter._process_mask_definition(mask_element, context)

        target = ET.Element("rect", x="0", y="0", width="100", height="50", mask="url(#bboxMask)")

        output = converter._apply_mask(target, "url(#bboxMask)", context)

        assert "PowerPoint Mask Application" in output
        application = converter.masked_elements[-1]
        assert application.resolved_bounds == pytest.approx((-10.0, -5.0, 120.0, 60.0))
        assert application.requires_rasterization is False

    def test_alpha_mask_triggers_rasterization(self, services):
        converter = _make_converter(services)
        context = _make_context(services)

        mask_element = ET.fromstring(
            """
            <mask id="alphaMask" maskUnits="userSpaceOnUse" mask-type="alpha">
              <rect x="0" y="0" width="20" height="20" />
            </mask>
            """
        )
        converter._process_mask_definition(mask_element, context)

        target = ET.Element("rect", x="5", y="10", width="40", height="60", mask="url(#alphaMask)")

        output = converter._apply_mask(target, "url(#alphaMask)", context)

        assert "Rasterized Mask Output" in output
        application = converter.masked_elements[-1]
        assert application.requires_rasterization is True


class TestClipApplication:
    def test_simple_clippath_uses_custgeom(self, services):
        converter = _make_converter(services)
        context = _make_context(services)

        clip_element = ET.fromstring(
            """
            <clipPath id="clipSimple" clipPathUnits="userSpaceOnUse">
              <rect x="0" y="0" width="10" height="10"/>
            </clipPath>
            """
        )
        converter._process_clippath_definition(clip_element, context)
        clip_def = converter.clippath_definitions["clipSimple"]

        analysis = ClipPathAnalysis(
            complexity=ClipPathComplexity.SIMPLE,
            clip_chain=[clip_def],
            can_flatten=True,
            requires_emf=False,
            reason="simple clip path",
        )

        converter.clippath_analyzer = types.SimpleNamespace(
            analyze_clipping_scenario=lambda element, ctx: analysis
        )

        target = ET.Element("rect", attrib={"clip-path": "url(#clipSimple)"})

        output = converter._apply_clipping(target, "url(#clipSimple)", context)

        assert "PowerPoint Clipping Path" in output
        clip_app = converter.clipped_elements[-1]
        assert clip_app.resolved_path == "<a:custGeom/>"
        assert clip_app.powerpoint_compatible is True

    def test_complex_clippath_requests_emf(self, services):
        converter = _make_converter(services)
        context = _make_context(services)

        clip_element = ET.fromstring(
            """
            <clipPath id="clipComplex">
              <path d="M0 0 L10 0 L10 10 Z"/>
            </clipPath>
            """
        )
        converter._process_clippath_definition(clip_element, context)
        clip_def = converter.clippath_definitions["clipComplex"]

        analysis = ClipPathAnalysis(
            complexity=ClipPathComplexity.COMPLEX,
            clip_chain=[clip_def],
            can_flatten=False,
            requires_emf=True,
            reason="requires EMF fallback",
        )

        converter.clippath_analyzer = types.SimpleNamespace(
            analyze_clipping_scenario=lambda element, ctx: analysis
        )

        target = ET.Element("rect", attrib={"clip-path": "url(#clipComplex)"})

        output = converter._apply_clipping(target, "url(#clipComplex)", context)

        assert "EMF Vector Clipping" in output
        assert converter.clipped_elements == []

    def test_rasterized_clip_output_includes_analysis(self, services):
        converter = _make_converter(services)
        context = _make_context(services)

        clip_def = ClipPathDefinition(
            id="complexClip",
            units="userSpaceOnUse",
            clip_rule="nonzero",
            path_data="M0 0 L10 0 L10 10 Z",
            shapes=[],
            clipping_type=ClippingType.PATH_BASED,
        )

        analysis = ClipPathAnalysis(
            complexity=ClipPathComplexity.COMPLEX,
            clip_chain=[clip_def],
            can_flatten=False,
            requires_emf=False,
            reason="complex geometry",
            estimated_nodes=7,
        )

        element = ET.Element("path")
        output = converter._generate_rasterized_clip_output_with_analysis(element, analysis, context)

        assert "Rasterized Clipping Output" in output
        assert "complex geometry" in output
        assert "Nodes: 7" in output

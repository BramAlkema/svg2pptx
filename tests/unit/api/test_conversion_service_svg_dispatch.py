"""Regression tests for SVG dispatch in ConversionService."""

from types import SimpleNamespace

import pytest
from lxml import etree as ET

from api.services.conversion_service import ConversionService


@pytest.fixture()
def conversion_service_stub():
    """Create a ConversionService instance without initializing external services."""

    service = ConversionService.__new__(ConversionService)
    service.settings = SimpleNamespace(
        svg_preprocessing_enabled=False,
        svg_preprocessing_preset="default",
        svg_preprocessing_precision=2,
        svg_preprocessing_multipass=False,
    )
    return service


def test_minimal_svg_dispatches_real_elements(monkeypatch, conversion_service_stub):
    """Ensure the registry receives actual elements during conversion."""

    received_elements = []

    class DummyConverter:
        supported_elements = ["rect"]

        def can_convert(self, element):
            return element.tag.endswith("rect")

        def convert(self, element, context):
            return "<p:sp/>"

    class DummyRegistry:
        def __init__(self):
            self.converter = DummyConverter()

        def register_default_converters(self):
            return None

        def get_converter(self, element):
            assert isinstance(element, ET._Element)
            received_elements.append(element)
            if self.converter.can_convert(element):
                return self.converter
            return None

    class DummyContext:
        def __init__(self, svg_root):
            self.svg_root = svg_root
            self.coordinate_system = None
            self.converter_registry = None

    class DummyCoordinateSystem:
        def __init__(self, coords):
            self.viewbox = coords

    class DummyBuilder:
        def create_minimal_pptx(self, drawingml_shapes, output_path):
            pptx_bytes = b"PK" + b"\x00" * 2000
            with open(output_path, "wb") as handle:
                handle.write(pptx_bytes)

    monkeypatch.setattr(
        "api.services.conversion_service.ConverterRegistry", DummyRegistry
    )
    monkeypatch.setattr(
        "api.services.conversion_service.ConversionContext", DummyContext
    )
    monkeypatch.setattr(
        "api.services.conversion_service.CoordinateSystem", DummyCoordinateSystem
    )
    monkeypatch.setattr("api.services.conversion_service.PPTXBuilder", DummyBuilder)

    minimal_svg = (
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"10\" height=\"10\">"
        "<rect width=\"10\" height=\"10\" fill=\"red\"/></svg>"
    ).encode("utf-8")

    pptx_content = conversion_service_stub._convert_svg_to_pptx(minimal_svg, "inline")

    assert pptx_content.startswith(b"PK")
    assert len(pptx_content) > 1000
    assert len(received_elements) == 1
    assert received_elements[0].tag.endswith("rect")


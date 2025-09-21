#!/usr/bin/env python3
"""Tests for the API conversion service conversion pipeline."""

import sys
import types
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def stub_testbench_module():
    """Provide stub modules required for the conversion service tests."""

    module = types.ModuleType("testbench")

    class StubPPTXBuilder:
        def create_minimal_pptx(self, drawingml: str, output_path: str) -> None:
            """Write a minimal PPTX signature to the provided path."""
            with open(output_path, "wb") as handle:
                handle.write(b"PKstub")

    module.PPTXBuilder = StubPPTXBuilder
    sys.modules["testbench"] = module

    numpy_stub = types.ModuleType("numpy")
    numpy_stub.array = lambda data, *_, **__: data
    numpy_stub.float64 = float
    numpy_stub.int64 = int
    numpy_stub.ndarray = list
    sys.modules.setdefault("numpy", numpy_stub)

    conversion_services_stub = types.ModuleType("src.services.conversion_services")

    class StubConversionServices:
        @classmethod
        def get_default_instance(cls):  # pragma: no cover - patched in tests
            return cls()

    conversion_services_stub.ConversionServices = StubConversionServices
    conversion_services_stub.ConversionConfig = object
    sys.modules["src.services.conversion_services"] = conversion_services_stub

    converters_stub = types.ModuleType("src.converters")
    converters_stub.ConverterRegistry = object
    converters_stub.ConversionContext = object
    converters_stub.CoordinateSystem = object
    sys.modules["src.converters"] = converters_stub
    try:
        yield module
    finally:
        sys.modules.pop("testbench", None)
        if sys.modules.get("numpy") is numpy_stub:
            sys.modules.pop("numpy", None)
        sys.modules.pop("src.services.conversion_services", None)
        sys.modules.pop("src.converters", None)


def test_conversion_service_uses_shared_services_container():
    """Conversion path should share a ConversionServices container across components."""

    from api.services.conversion_service import ConversionService

    fake_services = Mock(name="ConversionServices")
    created_contexts = []
    created_registries = []

    class StubConversionContext:
        def __init__(self, svg_root=None, services=None):
            if services is None:
                raise TypeError("ConversionServices instance required")
            self.svg_root = svg_root
            self.services = services
            self.coordinate_system = None
            self.converter_registry = None
            created_contexts.append(self)

    class StubConverter:
        def __init__(self, services):
            self.services = services

        def can_convert(self, element):
            return True

        def convert(self, element, context):
            assert context.services is self.services
            return "<p:sp/>"

    class StubRegistry:
        def __init__(self, services=None):
            self.services = services
            self._converter = StubConverter(services)
            created_registries.append(self)

        def register_default_converters(self):
            return None

        def get_converter(self, element):
            return self._converter

    svg_content = (
        b"<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'>"
        b"<rect width='10' height='10'/></svg>"
    )

    class StubCoordinateSystem:
        def __init__(self, viewbox):
            self.viewbox = viewbox

    with patch(
        "src.services.conversion_services.ConversionServices.get_default_instance",
        return_value=fake_services,
    ) as mock_get_services, patch(
        "src.converters.ConverterRegistry",
        StubRegistry,
    ), patch(
        "src.converters.ConversionContext",
        StubConversionContext,
    ), patch(
        "src.converters.CoordinateSystem",
        StubCoordinateSystem,
    ), patch(
        "api.services.conversion_service.GoogleDriveService",
        return_value=Mock(),
    ), patch(
        "api.services.conversion_service.GoogleSlidesService",
        return_value=Mock(),
    ), patch(
        "api.services.conversion_service.UploadManager",
        return_value=Mock(),
    ):
        service = ConversionService()
        service.settings.svg_preprocessing_enabled = False

        pptx_bytes = service._convert_svg_to_pptx(
            svg_content, "http://example.com/sample.svg"
        )

    assert pptx_bytes.startswith(b"PK")
    assert mock_get_services.call_count == 1
    assert service.conversion_services is fake_services
    assert created_registries, "Registry should have been created"
    assert created_contexts, "Context should have been created"
    assert created_registries[0].services is fake_services
    assert created_contexts[0].services is fake_services
    assert created_contexts[0].converter_registry is created_registries[0]

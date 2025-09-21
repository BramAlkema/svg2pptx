"""Tests for SVGToDrawingMLConverter optional services handling."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Ensure src package is importable when running tests from repository root
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.services.conversion_services import ConversionServices
from src.svg2drawingml import SVGToDrawingMLConverter


SVG_WITH_DEFS = """
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <defs>
    <linearGradient id="grad1">
      <stop offset="0%" stop-color="#ffffff" />
      <stop offset="100%" stop-color="#000000" />
    </linearGradient>
    <pattern id="pat1" width="10" height="10" patternUnits="userSpaceOnUse">
      <rect width="10" height="10" fill="#cccccc" />
    </pattern>
    <filter id="filt1">
      <feGaussianBlur stdDeviation="2" />
    </filter>
  </defs>
  <rect x="0" y="0" width="50" height="50" fill="url(#grad1)" />
  <rect x="50" y="0" width="50" height="50" fill="url(#pat1)" filter="url(#filt1)" />
</svg>
""".strip()


@pytest.fixture
def mock_registry(monkeypatch):
    """Provide a mocked converter registry for SVGToDrawingMLConverter."""

    registry = Mock()
    registry.convert_element.return_value = "<a:p/>"
    monkeypatch.setattr(
        'src.svg2drawingml.ConverterRegistryFactory.get_registry',
        Mock(return_value=registry)
    )
    return registry


def test_convert_registers_defs_with_available_services(mock_registry):
    """Gradients, patterns, and filters should be registered when services exist."""

    services = ConversionServices.create_default()
    converter = SVGToDrawingMLConverter(services=services)

    result = converter.convert(SVG_WITH_DEFS)

    assert services.gradient_service is not None
    assert services.gradient_service.get_gradient('grad1') is not None
    assert services.pattern_service is not None
    assert services.pattern_service.get_pattern('pat1') is not None
    assert services.filter_service is not None
    assert services.filter_service.get_filter('filt1') is not None
    assert mock_registry.convert_element.called
    assert result


def test_convert_handles_missing_optional_services(mock_registry):
    """Converter should skip optional registrations when services are absent."""

    services = ConversionServices.create_default()
    services.gradient_service = None
    services.pattern_service = None
    services.filter_service = None

    converter = SVGToDrawingMLConverter(services=services)

    try:
        converter.convert(SVG_WITH_DEFS)
    except AttributeError as exc:  # pragma: no cover - failure path
        pytest.fail(f"Converter raised AttributeError with missing services: {exc}")

    assert mock_registry.convert_element.called

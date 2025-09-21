import pytest

from src.converters.base import ConverterRegistry
from src.converters.shapes import (
    CircleConverter,
    EllipseConverter,
    LineConverter,
    PolygonConverter,
    RectangleConverter,
)
from src.services.conversion_services import ConversionServices


@pytest.mark.parametrize(
    "converter_cls",
    [
        RectangleConverter,
        CircleConverter,
        EllipseConverter,
        PolygonConverter,
        LineConverter,
    ],
)
def test_numpy_converters_register_with_registry(converter_cls):
    services = ConversionServices.create_default()
    registry = ConverterRegistry(services=services)

    registry.register_class(converter_cls)

    registered_converter = next(
        (converter for converter in registry.converters if isinstance(converter, converter_cls)),
        None,
    )

    assert registered_converter is not None
    assert registered_converter.services is services

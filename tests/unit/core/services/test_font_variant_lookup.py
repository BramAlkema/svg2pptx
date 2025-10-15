import types

from core.services.font_service import FontService
from core.services.conversion_services import ConversionServices, FontVariantRegistry


class Dummy:
    pass


def make_conversion_services(font_service: FontService) -> ConversionServices:
    return ConversionServices(
        unit_converter=Dummy(),
        fractional_emu_converter=None,
        color_factory=Dummy,
        color_parser=Dummy(),
        transform_parser=Dummy(),
        viewport_resolver=Dummy(),
        path_system=None,
        style_parser=Dummy(),
        style_service=Dummy(),
        coordinate_transformer=Dummy(),
        font_processor=Dummy(),
        font_service=font_service,
        path_processor=Dummy(),
        pptx_builder=Dummy(),
        gradient_service=Dummy(),
        pattern_service=Dummy(),
        filter_service=Dummy(),
        image_service=Dummy(),
        font_system=None,
        config=None,
        font_registry=FontVariantRegistry(font_service),
    )


def test_font_service_find_variant_normalizes_inputs(tmp_path):
    service = FontService(enable_indexing=False)
    service._font_variants = {('acme sans', 'bold', 'italic'): tmp_path.as_posix()}

    variant = service.find_variant('Acme Sans', font_weight='700', font_style='Oblique')

    assert variant is not None
    assert variant['font_family'] == 'acme sans'
    assert variant['font_weight'] == 'bold'
    assert variant['font_style'] == 'italic'
    assert variant['path'] == tmp_path.as_posix()


def test_conversion_services_find_font_variant_delegates(tmp_path):
    service = FontService(enable_indexing=False)
    service._font_variants = {('demo', 'regular', 'normal'): tmp_path.as_posix()}

    services = make_conversion_services(service)

    result = services.find_font_variant('Demo')

    assert result is not None
    assert result['path'] == tmp_path.as_posix()
    assert result['font_family'] == 'demo'

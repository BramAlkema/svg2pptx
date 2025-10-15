import pytest

from core.data.embedded_font import EmbeddedFont
from core.ir.geometry import Point, Rect
from core.ir.text import Run, TextAnchor, TextFrame
from core.map.base import MapperResult, OutputFormat
from core.pipeline.converter import CleanSlateConverter
from core.policy.targets import TextDecision
from core.services.conversion_services import ConversionServices, FontVariantRegistry


class StubFontEmbeddingEngine:
    def __init__(self):
        self.requests = []

    def create_font_subset(self, request):
        self.requests.append(request)
        return EmbeddedFont.create_from_font(
            font_name=request.font_name,
            font_data=b"subset",
            characters=set(request.characters),
            original_size=1024,
            font_family=request.font_family,
            font_weight=request.font_weight,
            font_style=request.font_style,
        )


class StubFontService:
    def __init__(self, font_path):
        self._font_path = font_path

    def find_variant(self, font_family, font_weight=None, font_style=None):
        return {
            "font_family": font_family,
            "font_weight": font_weight or "regular",
            "font_style": font_style or "normal",
            "path": self._font_path,
        }

    def find_font_file(self, font_family, font_weight=None, font_style=None):
        return self._font_path


@pytest.fixture
def converter(tmp_path):
    font_path = tmp_path / "DemoFont.ttf"
    font_path.write_bytes(b"dummy font data")

    services = ConversionServices.create_default()
    services.font_service = StubFontService(str(font_path))
    services.font_registry = FontVariantRegistry(services.font_service)

    converter = CleanSlateConverter(services=services)
    converter.font_embedding_engine = StubFontEmbeddingEngine()
    return converter


def make_mapper_result(text):
    text_frame = TextFrame(
        origin=Point(0, 0),
        anchor=TextAnchor.START,
        bbox=Rect(0, 0, 100, 50),
        runs=[Run(text, "DemoFont", 12.0)],
    )
    decision = TextDecision.native(reasons=[])
    return MapperResult(
        element=text_frame,
        output_format=OutputFormat.NATIVE_DML,
        xml_content="<p:sp />",
        policy_decision=decision,
        metadata={},
    )


def test_prepare_embedded_fonts_reuses_cached_subset(converter):
    mapper_result = make_mapper_result("Hello")

    fonts_first = converter._prepare_embedded_fonts([mapper_result])
    assert len(fonts_first) == 1
    assert len(converter.font_embedding_engine.requests) == 1

    fonts_second = converter._prepare_embedded_fonts([mapper_result])
    assert len(fonts_second) == 1
    # No additional subset requests due to caching
    assert len(converter.font_embedding_engine.requests) == 1


def test_prepare_embedded_fonts_uses_normalized_variant(converter):
    mapper_result = make_mapper_result("World")
    fonts = converter._prepare_embedded_fonts([mapper_result])
    assert fonts[0].font_family == "DemoFont"
    assert fonts[0].font_weight == "regular"
    assert fonts[0].font_style == "normal"


def test_font_asset_manager_maps_bold_variant(tmp_path, converter):
    from core.io.font_manager import FontAssetManager

    bold_run = Run("Bold", "DemoFont", 16.0, bold=True)
    text_frame = TextFrame(
        origin=Point(0, 0),
        anchor=TextAnchor.START,
        bbox=Rect(0, 0, 100, 50),
        runs=[bold_run],
    )
    decision = TextDecision.native(reasons=[])
    mapper_result = MapperResult(
        element=text_frame,
        output_format=OutputFormat.NATIVE_DML,
        xml_content="<p:sp />",
        policy_decision=decision,
        metadata={},
    )

    fonts = converter._prepare_embedded_fonts([mapper_result])
    manager = FontAssetManager(fonts)

    family_map = manager._family_map
    assert "DemoFont" in family_map
    assert "bold" in family_map["DemoFont"]

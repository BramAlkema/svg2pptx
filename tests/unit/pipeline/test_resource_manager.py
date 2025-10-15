from __future__ import annotations

import logging
from types import SimpleNamespace

from core.data.embedded_font import EmbeddedFont
from core.ir.geometry import Point, Rect
from core.ir.text import Run, TextAnchor, TextFrame
from core.pipeline.config import PipelineConfig
from core.pipeline.resource_manager import ResourceManager


class StubFontService:
    def __init__(self) -> None:
        self.registered_paths = []

    def find_font_file(self, family: str, font_weight: str, font_style: str) -> str | None:
        return "/tmp/fake-font.ttf"

    def register_font_path(self, path: str) -> None:
        self.registered_paths.append(path)

    def find_variant(self, family: str, font_weight: str, font_style: str):
        return None


class StubFontEmbeddingEngine:
    def create_font_subset(self, request):
        return EmbeddedFont(
            font_name=request.font_name or "stub-font",
            font_data=b"fontdata",
            subset_characters=request.characters,
            original_size=1024,
            embedded_size=256,
            font_family=request.font_family,
            font_weight=request.font_weight,
            font_style=request.font_style,
        )


class StubFontFetcher:
    def fetch(self, source):
        return None


class MissingFontService:
    def __init__(self) -> None:
        self.registered_paths: list[str] = []

    def find_font_file(self, family: str, font_weight: str, font_style: str) -> str | None:
        return None

    def register_font_path(self, path: str) -> None:
        self.registered_paths.append(path)

    def find_variant(self, family: str, font_weight: str, font_style: str):
        return None


class RecordingFontFetcher:
    def __init__(self, path: str) -> None:
        self.path = path
        self.calls = 0
        self.sources = []

    def fetch(self, source):
        self.calls += 1
        self.sources.append(source)
        return self.path


class RecordingFontEmbeddingEngine:
    def __init__(self) -> None:
        self.calls = 0
        self.requests = []

    def create_font_subset(self, request):
        self.calls += 1
        self.requests.append(request)
        return EmbeddedFont(
            font_name=request.font_name or "recorded-font",
            font_data=b"subset-bytes",
            subset_characters=set(request.characters),
            original_size=2048,
            embedded_size=512,
            font_family=request.font_family or "StubFamily",
            font_weight=request.font_weight or "regular",
            font_style=request.font_style or "normal",
        )


def _make_text_frame(
    text: str = "Hello",
    font_family: str = "StubFamily",
    font_weight: str = "regular",
    font_style: str = "normal",
) -> TextFrame:
    run = Run(
        text=text,
        font_family=font_family,
        font_size_pt=12.0,
        font_weight=font_weight,
        font_style=font_style,
    )
    return TextFrame(
        origin=Point(0, 0),
        anchor=TextAnchor.START,
        bbox=Rect(0, 0, 10, 10),
        runs=[run],
    )


def test_prepare_embedded_fonts_tracks_resources():
    services = SimpleNamespace(
        font_service=StubFontService(),
        font_registry=None,
    )
    manager = ResourceManager(
        services=services,
        font_embedding_engine=StubFontEmbeddingEngine(),
        font_fetcher=StubFontFetcher(),
        config=PipelineConfig(),
        logger=logging.getLogger(__name__),
        conversion_error_cls=RuntimeError,
    )

    manager.reset_for_conversion()
    manager.set_font_face_sources([])

    mapper_results = [SimpleNamespace(metadata={}, element=_make_text_frame())]
    embedded_fonts = manager.prepare_embedded_fonts(mapper_results)

    assert embedded_fonts, "Expected embedded font to be generated"
    font = embedded_fonts[0]
    assert font.font_family == "StubFamily"
    assert font.font_weight == "regular"
    assert manager.font_outline_required is False
    assert manager.consume_font_messages() == []

    key = ("StubFamily", "regular", "normal")
    assert key in manager.fonts
    assert manager.fonts[key].characters == {"H", "e", "l", "o"}


def test_manager_records_media_and_registers_fonts():
    services = SimpleNamespace(font_service=StubFontService(), font_registry=None)
    manager = ResourceManager(
        services=services,
        font_embedding_engine=StubFontEmbeddingEngine(),
        font_fetcher=StubFontFetcher(),
        config=PipelineConfig(),
        logger=logging.getLogger(__name__),
        conversion_error_cls=RuntimeError,
    )

    manager.record_media_files([{"filename": "image.png"}])
    assert manager.images and manager.images[0]["filename"] == "image.png"

    class ComposerStub:
        def __init__(self) -> None:
            self.asset_embedder = SimpleNamespace()
            self.calls = []

            def register_embedded_fonts(fonts, slide_index):
                self.calls.append((fonts, slide_index))

            self.asset_embedder.register_embedded_fonts = register_embedded_fonts

    composer = ComposerStub()
    font = EmbeddedFont(
        font_name="Sample",
        font_data=b"data",
        subset_characters={"A"},
        original_size=100,
        embedded_size=50,
        font_family="Sample",
        font_weight="regular",
        font_style="normal",
    )
    manager.register_embedded_fonts(composer, [font], slide_index=0)
    assert composer.calls and composer.calls[0][1] == 0


def test_prepare_embedded_fonts_fetches_external_sources_and_caches(tmp_path):
    download_path = tmp_path / "stub-download.ttf"
    download_path.write_bytes(b"fake font bytes")

    services = SimpleNamespace(
        font_service=MissingFontService(),
        font_registry=None,
    )
    font_fetcher = RecordingFontFetcher(str(download_path))
    embedding_engine = RecordingFontEmbeddingEngine()

    manager = ResourceManager(
        services=services,
        font_embedding_engine=embedding_engine,
        font_fetcher=font_fetcher,
        config=PipelineConfig(),
        logger=logging.getLogger(__name__),
        conversion_error_cls=RuntimeError,
    )

    manager.reset_for_conversion()
    manager.set_font_face_sources(
        [
            {
                "font_family": "StubFamily",
                "font_weight": "regular",
                "font_style": "normal",
                "sources": ["https://fonts.example/stub.ttf"],
            }
        ]
    )

    mapper_results = [
        SimpleNamespace(metadata={}, element=_make_text_frame("Hello")),
        SimpleNamespace(metadata={}, element=_make_text_frame("Hello")),
    ]

    first_fonts = manager.prepare_embedded_fonts(mapper_results)
    second_fonts = manager.prepare_embedded_fonts(mapper_results)

    assert len(first_fonts) == 1
    embedded = first_fonts[0]
    assert embedded.font_family == "StubFamily"
    assert embedded.font_weight == "regular"

    key = ("StubFamily", "regular", "normal")
    assert key in manager.fonts
    assert manager.fonts[key].characters == {"H", "e", "l", "o"}

    assert embedding_engine.calls == 1, "Expected subsets to be cached across calls"
    assert second_fonts and second_fonts[0] is embedded

    assert set(services.font_service.registered_paths) == {str(download_path)}
    assert font_fetcher.calls >= 1
    assert font_fetcher.sources[0].url == "https://fonts.example/stub.ttf"

    assert manager.consume_font_messages() == []
    assert manager.font_outline_required is False

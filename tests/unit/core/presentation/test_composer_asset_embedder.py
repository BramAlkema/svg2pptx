from types import SimpleNamespace

from core.map.base import MapperResult, OutputFormat
from core.presentation.composer import AssetEmbedder


def make_mapper_result(
    *,
    metadata=None,
    media_files=None,
    element_type="ElementStub",
) -> MapperResult:
    element_cls = type(element_type, (), {})
    element = element_cls()
    meta = dict(metadata or {})
    return MapperResult(
        element=element,
        output_format=OutputFormat.NATIVE_DML,
        xml_content="<p:sp/>",
        policy_decision=SimpleNamespace(),
        metadata=meta,
        media_files=media_files,
    )


def test_asset_embedder_tracks_fonts_and_images():
    embedder = AssetEmbedder()

    mapper_results = [
        make_mapper_result(
            metadata={
                "font_embedding": {
                    "font_name": "Roboto",
                    "cache_key": "roboto-regular",
                    "characters": ["A", "B"],
                    "original_size": 1024,
                },
            },
            media_files=[
                {
                    "filename": "image1.png",
                    "content_type": "image/png",
                    "source": "inline",
                },
            ],
        ),
        make_mapper_result(metadata={}),
    ]

    slide_assets = embedder.prepare_scene_assets(scene=None, mapper_results=mapper_results)

    assert slide_assets["index"] == 1
    assert slide_assets["has_scene"] is False
    assert slide_assets["fonts"][0]["font_name"] == "Roboto"
    assert slide_assets["images"][0]["filename"] == "image1.png"

    tracked_font = next(iter(embedder.iter_tracked_fonts()))
    assert tracked_font["font_name"] == "Roboto"
    assert tracked_font["characters"] == ["A", "B"]
    assert tracked_font["slides"] == [1]

    tracked_image = next(iter(embedder.iter_tracked_images()))
    assert tracked_image["filename"] == "image1.png"
    assert tracked_image["slides"] == [1]


def test_asset_embedder_reset_clears_state():
    embedder = AssetEmbedder()
    embedder.prepare_scene_assets(scene=None, mapper_results=[make_mapper_result()])

    embedder.reset()

    assert list(embedder.prepared_assets) == []
    assert list(embedder.iter_tracked_fonts()) == []
    assert list(embedder.iter_tracked_images()) == []

from pathlib import Path

import pytest

from core.io.template_store import TemplateStore


@pytest.fixture
def store(tmp_path: Path) -> TemplateStore:
    return TemplateStore(template_root=tmp_path)


def test_load_returns_parser_friendly_tree(store: TemplateStore, tmp_path: Path) -> None:
    sample = tmp_path / "presentation.xml"
    sample.write_text("<root><child/></root>")

    node = store.load("presentation.xml")

    assert hasattr(node, "find")
    assert node.tag == "root"
    assert node.find("child") is not None


def test_load_caches_and_clones_templates(store: TemplateStore, tmp_path: Path) -> None:
    sample = tmp_path / "slideMaster.xml"
    sample.write_text("<master><id/></master>")

    first = store.load("slideMaster.xml")
    second = store.load("slideMaster.xml")

    assert first is not second
    assert first.find("id") is not None
    assert second.find("id") is not None


def test_load_returns_distinct_mutable_copies(store: TemplateStore, tmp_path: Path) -> None:
    sample = tmp_path / "slideLayout1.xml"
    sample.write_text("<layout><marker/></layout>")

    a = store.load("slideLayout1.xml")
    b = store.load("slideLayout1.xml")

    # Mutating one tree should not affect the cached base or the second copy.
    marker = a.find("marker")
    marker.set("id", "A")

    assert b.find("marker").get("id") is None

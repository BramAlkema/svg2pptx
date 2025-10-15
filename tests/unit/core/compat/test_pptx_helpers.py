#!/usr/bin/env python3
"""Tests for PPTX helper utilities."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.compat.pptx_manifest import PPTXManifestBuilder
from core.compat.pptx_media import MediaManager
from core.compat.pptx_slide import SlideBuilder, SlideDimensions


def test_media_manager_copies_image(tmp_path):
    image_path = tmp_path / "source.png"
    image_path.write_bytes(b"fake-image")

    manager = MediaManager()
    embed_id = manager.register_image(str(image_path))

    package_dir = tmp_path / "package"
    package_dir.mkdir()
    manager.copy_to_package(package_dir)

    media_file = package_dir / "ppt" / "media" / "image1.png"
    assert media_file.exists()

    rels = manager.get_image_relationships()
    assert len(rels) == 1
    assert embed_id in rels[0]


def test_manifest_builder_creates_structure(tmp_path):
    builder = PPTXManifestBuilder(image_extensions={"png", "jpeg"})

    builder.write_doc_props(tmp_path)
    builder.write_manifest(tmp_path)
    builder.write_theme(tmp_path)
    builder.write_layout_and_master(tmp_path)

    assert (tmp_path / "docProps" / "core.xml").exists()
    assert (tmp_path / "docProps" / "app.xml").exists()
    assert (tmp_path / "[Content_Types].xml").exists()
    assert (tmp_path / "ppt" / "presentation.xml").exists()
    assert (tmp_path / "ppt" / "theme" / "theme1.xml").exists()
    assert (tmp_path / "ppt" / "slideLayouts" / "slideLayout1.xml").exists()
    assert (tmp_path / "ppt" / "slideMasters" / "slideMaster1.xml").exists()


def test_slide_builder_renders_shapes():
    builder = SlideBuilder(SlideDimensions(width=1000, height=2000))
    xml = builder.render("<a:shape/>")
    assert "<a:shape/>" in xml
    assert "cx=\"1000\"" in xml
    assert "cy=\"2000\"" in xml


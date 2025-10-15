"""Helpers for managing media assets within PPTX packages."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable, List, Tuple


class MediaManager:
    """Copy and track media files for inclusion in the PPTX package."""

    def __init__(self):
        self.images: list[tuple[str, str, str]] = []  # (embed_id, file_path, extension)
        self.next_rel_id = 10

    def register_image(self, image_path: str) -> str:
        ext = Path(image_path).suffix.lower().lstrip('.')
        embed_id = f"rId{self.next_rel_id}"
        self.next_rel_id += 1
        self.images.append((embed_id, image_path, ext))
        return embed_id

    def copy_to_package(self, base_path: Path) -> None:
        if not self.images:
            return
        media_dir = base_path / 'ppt' / 'media'
        media_dir.mkdir(parents=True, exist_ok=True)

        for idx, (embed_id, source_path, ext) in enumerate(self.images):
            target_name = f"image{idx + 1}.{ext}"
            shutil.copy2(source_path, media_dir / target_name)
            self.images[idx] = (embed_id, f"media/{target_name}", ext)

    def get_image_relationships(self) -> List[str]:
        rels = []
        for embed_id, media_path, _ in self.images:
            rels.append(
                f'    <Relationship Id="{embed_id}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                f'Target="../{media_path}"/>',
            )
        return rels

    def image_extensions(self) -> Iterable[str]:
        return {ext for _, _, ext in self.images}


__all__ = ["MediaManager"]

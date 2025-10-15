"""Font asset manager for PPTX packaging."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from lxml import etree as ET

from ..data.embedded_font import EmbeddedFont

FONT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
FONT_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.obfuscatedFont"
FONT_PART_ROOT = Path("ppt/fonts")


@dataclass
class FontPart:
    """Represents an embedded font ready for packaging."""

    embedded_font: EmbeddedFont
    part_name: str
    relationship_id: str
    variant: str
    obfuscated_data: bytes
    guid: uuid.UUID

    @property
    def content_type(self) -> str:
        return FONT_CONTENT_TYPE

    @property
    def relationship_target(self) -> str:
        return self.part_name.replace("\\", "/")


class FontAssetManager:
    """Assigns relationship IDs and part names for embedded fonts."""

    def __init__(self, fonts: Iterable[EmbeddedFont]):
        self._original_fonts = list(fonts or [])
        self._font_parts: List[FontPart] = []
        self._family_map: dict[str, dict[str, FontPart]] = {}

        if self._original_fonts:
            self._prepare_fonts()

    @staticmethod
    def _determine_variant(font: EmbeddedFont) -> str:
        weight = font.font_weight.lower() if font.font_weight else "normal"
        style = font.font_style.lower() if font.font_style else "normal"

        is_bold = (
            "bold" in weight
            or weight in {"700", "800", "900", "black", "heavy"}
        )
        is_italic = style in {"italic", "oblique"}

        if is_bold and is_italic:
            return "boldItalic"
        if is_bold:
            return "bold"
        if is_italic:
            return "italic"
        return "regular"

    @staticmethod
    def _obfuscate_font_data(data: bytes, guid: uuid.UUID) -> bytes:
        key = guid.bytes_le  # little-endian per OOXML specification
        buffer = bytearray(data)
        limit = min(32, len(buffer))
        for i in range(limit):
            buffer[i] ^= key[i % 16]
        return bytes(buffer)

    @staticmethod
    def _sanitize_font_filename(font: EmbeddedFont, variant: str, index: int) -> str:
        safe_name = ''.join(c for c in font.font_family or font.font_name if c.isalnum()) or "Font"
        return f"{safe_name}_{variant}_{index}.odttf"

    def _prepare_fonts(self) -> None:
        for index, font in enumerate(self._original_fonts, start=1):
            variant = self._determine_variant(font)
            guid = uuid.uuid4()
            obfuscated = self._obfuscate_font_data(font.font_data, guid)
            filename = self._sanitize_font_filename(font, variant, index)
            part_path = (FONT_PART_ROOT / filename).as_posix()
            relationship_id = f"rIdFont{index}"

            part = FontPart(
                embedded_font=font,
                part_name=part_path,
                relationship_id=relationship_id,
                variant=variant,
                obfuscated_data=obfuscated,
                guid=guid,
            )

            self._font_parts.append(part)
            family = font.font_family or font.font_name
            if family not in self._family_map:
                self._family_map[family] = {}
            self._family_map[family][variant] = part

    @property
    def font_parts(self) -> List[FontPart]:
        return self._font_parts

    def write_font_parts(self, zip_file) -> None:
        for part in self._font_parts:
            zip_file.writestr(part.part_name, part.obfuscated_data)

    def append_to_presentation(self, presentation: ET._Element, namespaces: dict[str, str]) -> None:
        if not self._font_parts:
            return

        embedded_list = presentation.find('p:embeddedFontLst', namespaces=namespaces)
        if embedded_list is None:
            embedded_list = ET.SubElement(presentation, f"{{{namespaces['p']}}}embeddedFontLst")

        for family, variants in self._family_map.items():
            font_entry = ET.SubElement(embedded_list, f"{{{namespaces['p']}}}embeddedFont")
            font_elem = ET.SubElement(font_entry, f"{{{namespaces['p']}}}font")
            font_elem.set('typeface', family)
            font_elem.set('pitchFamily', '0')
            font_elem.set('charset', '0')

            self._append_variant_element(font_entry, 'embedRegular', variants.get('regular'))
            self._append_variant_element(font_entry, 'embedBold', variants.get('bold'))
            self._append_variant_element(font_entry, 'embedItalic', variants.get('italic'))
            self._append_variant_element(font_entry, 'embedBoldItalic', variants.get('boldItalic'))

    def append_to_relationships(self, relationships: ET._Element, namespaces: dict[str, str]) -> None:
        if not self._font_parts:
            return

        for part in self._font_parts:
            rel = ET.SubElement(relationships, f"{{{namespaces['rel']}}}Relationship")
            rel.set('Id', part.relationship_id)
            rel.set('Type', FONT_REL_TYPE)
            rel.set('Target', part.relationship_target)

    def append_to_content_types(self, content_types: ET._Element, namespaces: dict[str, str]) -> None:
        if not self._font_parts:
            return

        for part in self._font_parts:
            override = ET.SubElement(content_types, f"{{{namespaces['ct']}}}Override")
            override.set('PartName', f"/{part.relationship_target}")
            override.set('ContentType', part.content_type)

    @staticmethod
    def _append_variant_element(parent: ET._Element, tag: str, part: FontPart | None) -> None:
        if not part:
            return
        element = ET.SubElement(parent, f"{{{parent.tag.split('}')[0].strip('{')}}}{tag}")
        element.set(f"{{http://schemas.openxmlformats.org/officeDocument/2006/relationships}}id", part.relationship_id)


__all__ = ["FontAssetManager", "FontPart", "FONT_REL_TYPE", "FONT_CONTENT_TYPE"]

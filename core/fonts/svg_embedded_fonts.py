# core/fonts/svg_embedded_fonts.py
import re
import uuid
import zipfile
import hashlib
import os
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from lxml import etree as ET

from .font_normalizer import FontNormalizer, FontAsset

logger = logging.getLogger(__name__)

P_URI = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_URI = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_URI = "http://schemas.openxmlformats.org/drawingml/2006/main"
NSMAP = {'p': P_URI, 'r': R_URI, 'a': A_URI}

REL_PRES_FONT_TABLE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable"
REL_PRES_EMBED_FONT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
CT_FONT_TABLE = "application/vnd.openxmlformats-officedocument.presentationml.fontTable+xml"
CT_ODTTF = "application/vnd.openxmlformats-officedocument.presentationml.obfuscatedFont"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


@dataclass(frozen=True)
class EmbeddedFace:
    """Font face ready for PPTX embedding"""
    family: str
    style: Optional[str]  # normal|italic|oblique
    weight: Optional[int]  # usWeightClass (100-900)
    format: str  # TTF|OTF
    data: bytes  # normalized TTF/OTF bytes
    sha1: str  # checksum for dedupe (SHA-1 for backward compat)
    sha256: str  # SHA-256 checksum from FontNormalizer


_FONT_FACE_BLOCK = re.compile(r'@font-face\s*\{[^}]+\}', re.I | re.S)
_DECL_RE = re.compile(r'([-\w]+)\s*:\s*([^;]+);')


def _clean_css_value(v: str) -> str:
    v = v.strip()
    if v[:1] in "'\"" and v[-1:] in "'\"":
        v = v[1:-1]
    return v.strip()


def _parse_font_weight(weight_str: Optional[str]) -> Optional[int]:
    """Convert CSS font-weight to usWeightClass (100-900)"""
    if not weight_str:
        return None
    w = weight_str.strip().lower()
    # Named weights
    weight_map = {
        'normal': 400,
        'bold': 700,
        'lighter': 300,
        'bolder': 700,
    }
    if w in weight_map:
        return weight_map[w]
    # Numeric weights
    try:
        val = int(w)
        return val if 100 <= val <= 900 else None
    except ValueError:
        return None


def _parse_font_style(style_str: Optional[str]) -> Optional[str]:
    """Normalize CSS font-style to normal|italic|oblique"""
    if not style_str:
        return None
    s = style_str.strip().lower()
    return s if s in ('normal', 'italic', 'oblique') else None


def extract_embedded_faces(svg_str: str, svg_base_path: str = '.') -> List[EmbeddedFace]:
    """
    Extract and normalize embedded fonts from SVG using FontNormalizer.

    Supports:
    - TTF, OTF (native)
    - WOFF, WOFF2 (auto-converted with fonttools)
    - data: URLs, file paths, file://, http(s):// (if requests installed)

    Args:
        svg_str: SVG content as string
        svg_base_path: Base directory for resolving relative font paths (default: current directory)

    Returns:
        List of normalized fonts ready for PPTX embedding
    """
    normalizer = FontNormalizer()
    root = ET.fromstring(svg_str.encode('utf-8'))
    nss = {'svg': 'http://www.w3.org/2000/svg'}
    styles = root.xpath('.//svg:style', namespaces=nss) + root.findall('.//style')

    faces: List[EmbeddedFace] = []
    seen_sha256: set = set()  # Dedupe by SHA-256

    for sty in styles:
        css = (sty.text or "")
        for block in _FONT_FACE_BLOCK.findall(css):
            decls = {k.strip().lower(): _clean_css_value(v) for k, v in _DECL_RE.findall(block)}
            family = decls.get('font-family')
            src = decls.get('src')
            if not family or not src:
                continue

            # Parse font metadata from CSS
            css_weight = _parse_font_weight(decls.get('font-weight'))
            css_style = _parse_font_style(decls.get('font-style'))

            # Parse src: url(...) format(...), ...
            # Use the regex from font_normalizer for consistency
            from .font_normalizer import _parse_src_list
            src_items = _parse_src_list(src)

            # Try each src item until one succeeds
            asset: Optional[FontAsset] = None
            for url, format_hint in src_items:
                try:
                    asset = normalizer.normalize_from_src(
                        url,
                        format_hint=format_hint,
                        base_dir=svg_base_path
                    )
                    break  # Success
                except Exception as e:
                    logger.debug(f"Font source '{url}' failed: {e}")
                    continue

            if not asset:
                logger.warning(f"No valid font source for family '{family}'")
                continue

            # Deduplicate by SHA-256
            if asset.sha256 in seen_sha256:
                logger.debug(f"Font '{family}' already extracted (SHA-256: {asset.sha256[:8]}...)")
                continue
            seen_sha256.add(asset.sha256)

            # Create EmbeddedFace with normalized data
            # Use metadata from FontAsset when CSS doesn't provide it
            final_weight = css_weight or asset.weight or 400
            final_style = css_style or ('italic' if asset.italic else 'normal')

            # Compute SHA-1 for backward compatibility
            sha1 = hashlib.sha1(asset.embeddable_bytes).hexdigest()

            faces.append(EmbeddedFace(
                family=family,
                style=final_style,
                weight=final_weight,
                format=asset.flavor,  # TTF or OTF
                data=asset.embeddable_bytes,
                sha1=sha1,
                sha256=asset.sha256
            ))

            logger.info(
                f"Extracted font: {family} (weight={final_weight}, style={final_style}, "
                f"format={asset.flavor}, original={asset.original_format})"
            )

    return faces


def _obfuscate_odttf(raw: bytes, guid: uuid.UUID) -> bytes:
    b = bytearray(raw)
    key = guid.bytes_le
    n = min(32, len(b))
    for i in range(n):
        b[i] ^= key[i % 16]
    return bytes(b)


def _read_xml(zf: zipfile.ZipFile, name: str) -> ET._ElementTree:
    with zf.open(name) as fp:
        return ET.parse(fp)


def _write_xml(zf: zipfile.ZipFile, name: str, root: ET._Element):
    data = ET.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
    zf.writestr(name, data)


def _ensure_ct_override(ct_root: ET._Element, part: str, ctype: str):
    tag_types = f"{{{CT_NS}}}Types"
    tag_ov = f"{{{CT_NS}}}Override"
    # de-dup
    for o in ct_root.findall(tag_ov):
        if o.get('PartName') == part:
            o.set('ContentType', ctype)
            return
    ET.SubElement(ct_root, tag_ov, PartName=part, ContentType=ctype)


def embed_faces_into_pptx(pptx_path: str, faces: List[EmbeddedFace]) -> Dict[str, List[Tuple[str, str]]]:
    """
    Embed faces into pptx and return a registry {family: [(relId, partName), ...]}
    """
    if not faces:
        return {}

    registry: Dict[str, List[Tuple[str, str]]] = {}

    with zipfile.ZipFile(pptx_path, 'a') as zf:
        # Content types
        ct_tree = _read_xml(zf, '[Content_Types].xml')
        ct_root = ct_tree.getroot()
        _ensure_ct_override(ct_root, '/ppt/fontTable.xml', CT_FONT_TABLE)

        # presentation rels (presentation -> fontTable.xml)
        pres_rel = 'ppt/_rels/presentation.xml.rels'
        rel_tag = f"{{{REL_NS}}}Relationship"
        if pres_rel in zf.namelist():
            pres_rels = _read_xml(zf, pres_rel)
            pres_rels_root = pres_rels.getroot()
        else:
            pres_rels_root = ET.Element(f"{{{REL_NS}}}Relationships")
            pres_rels = ET.ElementTree(pres_rels_root)

        fonttable_rid = None
        for r in pres_rels_root.findall(rel_tag):
            if r.get('Type') == REL_PRES_FONT_TABLE:
                fonttable_rid = r.get('Id')
                break
        if not fonttable_rid:
            fonttable_rid = f"rId{1000 + len(pres_rels_root)}"
            ET.SubElement(pres_rels_root, rel_tag, Id=fonttable_rid, Type=REL_PRES_FONT_TABLE, Target="fontTable.xml")
            _write_xml(zf, pres_rel, pres_rels_root)

        # fontTable.xml + rels
        ft_part = 'ppt/fontTable.xml'
        ft_rels_part = 'ppt/_rels/fontTable.xml.rels'
        if ft_part in zf.namelist():
            ft_tree = _read_xml(zf, ft_part)
            ft_root = ft_tree.getroot()
        else:
            ft_root = ET.Element(f"{{{P_URI}}}fontTbl", nsmap=NSMAP)
            ft_tree = ET.ElementTree(ft_root)

        if ft_rels_part in zf.namelist():
            ft_rels = _read_xml(zf, ft_rels_part)
            ft_rels_root = ft_rels.getroot()
        else:
            ft_rels_root = ET.Element(f"{{{REL_NS}}}Relationships")
            ft_rels = ET.ElementTree(ft_rels_root)

        # find next index
        font_dir = 'ppt/fonts'
        next_idx = 1
        for n in zf.namelist():
            if n.startswith(f"{font_dir}/font") and n.endswith(".odttf"):
                try:
                    i = int(os.path.basename(n)[4:-6])
                    next_idx = max(next_idx, i + 1)
                except Exception:
                    pass

        # write each face
        for face in faces:
            guid = uuid.uuid4()
            odttf = _obfuscate_odttf(face.data, guid)
            part_name = f'{font_dir}/font{next_idx}.odttf'
            zf.writestr(part_name, odttf)
            _ensure_ct_override(ct_root, f'/{part_name}', CT_ODTTF)

            rel_id = f"rId{2000 + next_idx}"
            ET.SubElement(ft_rels_root, rel_tag, Id=rel_id, Type=REL_PRES_EMBED_FONT,
                          Target=f"fonts/font{next_idx}.odttf")

            emb = ET.SubElement(ft_root, f"{{{P_URI}}}embeddedFont")
            # You can add separate sets (latin/ea/cs). Minimal: one <p:font>.
            fnode = ET.SubElement(emb, f"{{{P_URI}}}font")
            fnode.set('typeface', face.family)
            fnode.set(f"{{{R_URI}}}id", rel_id)

            registry.setdefault(face.family, []).append((rel_id, part_name))
            next_idx += 1

        _write_xml(zf, ft_part, ft_root)
        _write_xml(zf, ft_rels_part, ft_rels_root)
        _write_xml(zf, '[Content_Types].xml', ct_root)

    return registry

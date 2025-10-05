from lxml import etree as ET
import re

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NSMAP = {"a": A}
ANGLE_UNITS_PER_DEG = 60000

def _strip_hash(s: str | None) -> str:
    s = (s or "").strip()
    return s[1:] if s.startswith("#") else s

def _deg_to_ppu(deg: float) -> int:
    return int(round(deg * ANGLE_UNITS_PER_DEG))

def _first_number(s: str | None) -> float | None:
    if not s:
        return None
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None

def _parse(xml: str) -> ET._Element:
    # Always wrap with xmlns:a to guarantee stable 'a:' prefix
    if "xmlns:a" not in xml:
        xml = f'<a:timing xmlns:a="{A}">{xml}</a:timing>'
        root = ET.fromstring(xml)
        # unwrap if wrapper contains a single <a:timing>
        if len(root) == 1 and root[0].tag.endswith("timing"):
            return root[0]
        return root
    return ET.fromstring(xml)

def _attr_name(anim: ET._Element) -> str | None:
    cb = anim.find("a:cBhvr", namespaces=NSMAP)
    if cb is None:
        return None
    lst = cb.find("a:attrNameLst", namespaces=NSMAP)
    if lst is None:
        return None
    for an in lst.findall("a:attrName", namespaces=NSMAP):
        if an.text:
            return an.text.strip()
    return None

def _tav_vals(anim: ET._Element) -> list[str]:
    vals = []
    for tav in anim.findall(".//a:tav", namespaces=NSMAP):
        v = tav.find("a:val", namespaces=NSMAP)
        if v is not None and "val" in v.attrib:
            vals.append(v.attrib["val"]); continue
        sv = tav.find("a:strVal", namespaces=NSMAP)
        if sv is not None and "val" in sv.attrib:
            vals.append(sv.attrib["val"]); continue
    return vals

def _normalise_colours(anim: ET._Element) -> None:
    for val_node in anim.findall(".//a:val", namespaces=NSMAP):
        sv = val_node.find("a:strVal", namespaces=NSMAP)
        if sv is not None and "val" in sv.attrib:
            # lift attribute up before clearing children
            val_node.attrib["val"] = _strip_hash(sv.attrib["val"])
            for c in list(val_node):
                val_node.remove(c)
        elif "val" in val_node.attrib:
            val_node.attrib["val"] = _strip_hash(val_node.attrib["val"])
    # handle bare <a:strVal> under <a:tav>
    for tav in anim.findall(".//a:tav", namespaces=NSMAP):
        if tav.find("a:val", namespaces=NSMAP) is None:
            sv = tav.find("a:strVal", namespaces=NSMAP)
            if sv is not None and "val" in sv.attrib:
                v = ET.Element("{%s}val" % A)
                v.attrib["val"] = _strip_hash(sv.attrib["val"])
                tav.remove(sv)
                tav.append(v)

def _inject_animrot_by(anim: ET._Element) -> None:
    vals = _tav_vals(anim)
    if len(vals) < 2:
        by = ET.Element("{%s}by" % A); by.attrib["val"] = "0"; anim.append(by); return
    start = _first_number(vals[0]) or 0.0
    end = _first_number(vals[-1]) or start
    delta = end - start
    by = ET.Element("{%s}by" % A)
    by.attrib["val"] = str(_deg_to_ppu(delta))
    anim.append(by)

def normalize_animation_xml(xml: str) -> str:
    """
    - fill → <a:animClr> with hex colours cleaned
    - transform/rotate → <a:animRot> with <a:by val="..."> injected
    Ensures 'a:' prefix, strips '#' from hex.
    """
    if not xml or "anim" not in xml:
        return xml or ""

    root = _parse(xml)

    # Find all anim elements (including root if it's an anim)
    anim_elements = []
    if root.tag.endswith('}anim'):
        anim_elements.append(root)
    anim_elements.extend(root.findall(".//a:anim", namespaces=NSMAP))

    for anim in anim_elements:
        attr = _attr_name(anim)
        if attr == "fill":
            anim.tag = "{%s}animClr" % A
            _normalise_colours(anim)
        elif attr == "transform":
            anim.tag = "{%s}animRot" % A
            _inject_animrot_by(anim)

    # Force correct prefix mapping, no ns0 junk
    result = ET.tostring(root, encoding="unicode", pretty_print=False)
    # Strip XML declaration if present
    if result.startswith('<?xml'):
        result = result.split('>', 1)[1] if '>' in result else result
    return result

def normalize_if_color_anim(xml: str, anim_def) -> str:
    """
    Normalize animation XML if it's a color animation.

    Args:
        xml: The animation XML string to normalize
        anim_def: Animation definition (unused, for signature compatibility)

    Returns:
        Normalized animation XML, or original on error
    """
    try:
        if not xml:
            return ""
        return normalize_animation_xml(xml)
    except Exception:
        return xml or ""
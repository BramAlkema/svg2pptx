"""
SVG normalization utilities used across the Clean Slate pipeline.

This helper performs three main passes:
1. Inline stylesheet rules into element style attributes
2. Promote supported style declarations to presentation attributes
3. Sort attributes for deterministic XML emission

The implementation intentionally mirrors the design captured in ADR-010.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from lxml import etree as ET

try:
    import tinycss2  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    tinycss2 = None

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
NSMAP = {"svg": SVG_NS, "xlink": XLINK_NS}

# Map supported CSS properties to SVG presentation attributes
STYLE_TO_ATTR: Dict[str, str] = {
    "fill": "fill",
    "fill-opacity": "fill-opacity",
    "fill-rule": "fill-rule",
    "stroke": "stroke",
    "stroke-opacity": "stroke-opacity",
    "stroke-width": "stroke-width",
    "stroke-linecap": "stroke-linecap",
    "stroke-linejoin": "stroke-linejoin",
    "stroke-miterlimit": "stroke-miterlimit",
    "stroke-dasharray": "stroke-dasharray",
    "stroke-dashoffset": "stroke-dashoffset",
    "opacity": "opacity",
    "font-family": "font-family",
    "font-size": "font-size",
    "font-style": "font-style",
    "font-weight": "font-weight",
    "text-anchor": "text-anchor",
    "letter-spacing": "letter-spacing",
    "word-spacing": "word-spacing",
    "direction": "direction",
    "dominant-baseline": "dominant-baseline",
    "visibility": "visibility",
    "display": "display",
    "vector-effect": "vector-effect",
    "paint-order": "paint-order",
}


@dataclass(frozen=True)
class Selector:
    """Minimal selector representation (tag, class, id, attribute, descendant)."""

    tag: Optional[str] = None
    cls: Optional[str] = None
    id_: Optional[str] = None
    attr_key: Optional[str] = None
    attr_val: Optional[str] = None
    ancestor_chain: Tuple["Selector", ...] = ()

    @staticmethod
    def parse(selector: str) -> "Selector":
        """Parse a simple CSS selector (id/class/tag/descendant)."""
        parts = [p for p in selector.strip().split() if p]

        def parse_simple(token: str) -> "Selector":
            tag = None
            cls = None
            id_ = None
            attr_key = None
            attr_val = None

            if token and token[0].isalpha():
                match = re.match(r"^[a-zA-Z_][\w:-]*", token)
                if match:
                    tag = match.group(0)

            if tag:
                tag = tag.split(".", 1)[0].split("#", 1)[0]

            if "#" in token and not id_:
                tag_part, id_part = token.split("#", 1)
                tag = tag or (tag_part if tag_part and tag_part[0].isalpha() else tag)
                id_ = id_part

            if "." in token and not cls:
                tag_part, cls_part = token.split(".", 1)
                tag = tag or (tag_part if tag_part and tag_part[0].isalpha() else tag)
                cls = cls_part

            attr_match = re.search(r"\[([\w:-]+)\s*=\s*([^\]]+)\]", token)
            if attr_match:
                attr_key = attr_match.group(1)
                attr_val = attr_match.group(2).strip('"\'')

            return Selector(tag=tag, cls=cls, id_=id_, attr_key=attr_key, attr_val=attr_val)

        if len(parts) == 1:
            return parse_simple(parts[0])

        tail = parse_simple(parts[-1])
        ancestors = tuple(parse_simple(p) for p in parts[:-1])
        return Selector(
            tail.tag,
            tail.cls,
            tail.id_,
            tail.attr_key,
            tail.attr_val,
            ancestors,
        )

    def matches(self, element: ET._Element) -> bool:
        """Check if selector matches given element (with ancestor chain)."""

        def match_simple(sel: "Selector", el: ET._Element) -> bool:
            if sel.tag and ET.QName(el).localname != sel.tag:
                return False
            if sel.id_ and el.get("id") != sel.id_:
                return False
            if sel.cls:
                cls_val = el.get("class", "")
                if sel.cls not in cls_val.split():
                    return False
            if sel.attr_key and el.get(sel.attr_key) != sel.attr_val:
                return False
            return True

        if not match_simple(self, element):
            return False

        current = element.getparent()
        for ancestor in reversed(self.ancestor_chain):
            found = False
            while current is not None:
                if match_simple(ancestor, current):
                    found = True
                    current = current.getparent()
                    break
                current = current.getparent()
            if not found:
                return False
        return True


@dataclass
class Rule:
    """CSS rule with selector, declarations, specificity, and source order."""

    selector: Selector
    declarations: List[Tuple[str, str]]
    specificity: Tuple[int, int, int]
    order: int


def _specificity(selector: Selector) -> Tuple[int, int, int]:
    ids = int(bool(selector.id_))
    classes = int(bool(selector.cls)) + int(bool(selector.attr_key))
    tags = int(bool(selector.tag))
    for ancestor in selector.ancestor_chain:
        ids += int(bool(ancestor.id_))
        classes += int(bool(ancestor.cls)) + int(bool(ancestor.attr_key))
        tags += int(bool(ancestor.tag))
    return ids, classes, tags


def _parse_css_rules(css_text: str) -> List[Rule]:
    rules: List[Rule] = []
    order = 0

    if tinycss2:
        for node in tinycss2.parse_stylesheet(css_text, skip_whitespace=True, skip_comments=True):
            if node.type != "qualified-rule":
                continue
            selector_text = tinycss2.serialize(node.prelude).strip()
            declarations: List[Tuple[str, str]] = []
            for declaration in tinycss2.parse_declaration_list(node.content, skip_whitespace=True, skip_comments=True):
                if declaration.type == "declaration" and declaration.value:
                    prop = declaration.lower_name
                    value = tinycss2.serialize(declaration.value).strip()
                    declarations.append((prop, value))
            for selector_fragment in [s.strip() for s in selector_text.split(",") if s.strip()]:
                selector = Selector.parse(selector_fragment)
                rules.append(Rule(selector, declarations, _specificity(selector), order))
                order += 1
        return rules

    # Fallback parser (simple regex-based)
    for block in re.finditer(r"([^{]+)\{([^}]+)\}", css_text, re.S):
        selector_block = block.group(1)
        body = block.group(2)
        declarations: List[Tuple[str, str]] = []
        for declaration in re.finditer(r"([\w-]+)\s*:\s*([^;]+);?", body):
            declarations.append((declaration.group(1).strip().lower(), declaration.group(2).strip()))
        for selector_fragment in [s.strip() for s in selector_block.split(",") if s.strip()]:
            selector = Selector.parse(selector_fragment)
            rules.append(Rule(selector, declarations, _specificity(selector), order))
            order += 1
    return rules


def parse_style_attr(style: str) -> Dict[str, str]:
    """Parse inline style attribute into dict of property -> value."""
    declarations: Dict[str, str] = {}
    for match in re.finditer(r"([\w-]+)\s*:\s*([^;]+)", style or ""):
        declarations[match.group(1).strip().lower()] = match.group(2).strip()
    return declarations


def serialize_style(declarations: Dict[str, str]) -> str:
    """Serialize style dict to stable string form."""
    return ";".join(f"{prop}:{declarations[prop]}" for prop in sorted(declarations.keys()))


def inline_styles(doc: ET._ElementTree) -> None:
    """Inline global <style> rules into inline style attributes."""
    style_nodes = doc.xpath("//svg:style", namespaces=NSMAP)
    if not style_nodes:
        return

    css_text = "\n".join("".join(node.itertext()) for node in style_nodes)
    rules = _parse_css_rules(css_text)
    if not rules:
        return

    all_elements = doc.xpath("//*")
    for element in all_elements:
        if not isinstance(element.tag, str):
            continue
        if ET.QName(element).localname == "style":
            continue

        matched_rules = [rule for rule in rules if rule.selector.matches(element)]
        if not matched_rules:
            continue

        matched_rules.sort(key=lambda rule: (rule.specificity, rule.order))
        current_styles = parse_style_attr(element.get("style", ""))
        for rule in matched_rules:
            for prop, value in rule.declarations:
                if prop not in current_styles:
                    current_styles[prop] = value
        if current_styles:
            element.set("style", serialize_style(current_styles))

    for style_node in style_nodes:
        parent = style_node.getparent()
        if parent is not None:
            parent.remove(style_node)


def convert_style_to_attrs(doc: ET._ElementTree) -> None:
    """Promote supported style declarations to presentation attributes."""
    for element in doc.xpath("//*"):
        if not isinstance(element.tag, str):
            continue

        style_map = parse_style_attr(element.get("style", ""))
        if not style_map:
            continue

        remaining: Dict[str, str] = {}
        for prop, value in style_map.items():
            attr = STYLE_TO_ATTR.get(prop)
            if attr:
                element.set(attr, value)
            else:
                remaining[prop] = value

        if remaining:
            element.set("style", serialize_style(remaining))
        elif "style" in element.attrib:
            del element.attrib["style"]


def sort_attributes(doc: ET._ElementTree) -> None:
    """Sort element attributes for deterministic output."""
    for element in doc.iter():
        if not isinstance(element.tag, str):
            continue
        if element.attrib:
            items = sorted(element.attrib.items(), key=lambda item: item[0])
            for key in list(element.attrib.keys()):
                del element.attrib[key]
            for key, value in items:
                element.set(key, value)


def normalize_svg_string(svg_text: str) -> str:
    """Normalize SVG string according to ADR-010 guidelines."""
    parser = ET.XMLParser(remove_blank_text=False, recover=False)
    root = ET.fromstring(svg_text.encode("utf-8"), parser=parser)
    tree = ET.ElementTree(root)

    inline_styles(tree)
    convert_style_to_attrs(tree)
    sort_attributes(tree)

    # Emit Unicode text without XML declaration so downstream parsing can use
    # the string directly (lxml rejects Unicode strings that include an
    # explicit encoding declaration).
    return ET.tostring(root, encoding="unicode", xml_declaration=False)


def normalize_svg_file(path_in: str, path_out: Optional[str] = None) -> None:
    """Normalize SVG from a file, optionally writing to another path."""
    with open(path_in, "r", encoding="utf-8") as source:
        svg_text = source.read()
    normalized = normalize_svg_string(svg_text)
    with open(path_out or path_in, "w", encoding="utf-8") as destination:
        destination.write(normalized)

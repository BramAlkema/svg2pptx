#!/usr/bin/env python3
"""
Safe XML iteration helpers for lxml.

Why:
- lxml comment/PI nodes are _Element subclasses in some Cython builds.
- Naive `for child in element` and `element.iter()` will surface them and
  can blow up downstream code that expects only element nodes.

Use:
- `walk(root)` instead of `root.iter()` for full-tree traversal.
- `children(element)` instead of `for child in element`.
- `is_element(node)` when you must branch on node type.
"""

from typing import Iterator, Iterable
from lxml import etree as ET

# lxml internal node classes we want to exclude during "element-only" iteration
_EXCLUDE_NODE_TYPES = (ET._Comment, ET._ProcessingInstruction)

def is_element(node: object) -> bool:
    """True if node is a real XML element (excludes comments/PIs)."""
    return isinstance(node, ET._Element) and not isinstance(node, _EXCLUDE_NODE_TYPES)

def children(element: ET._Element) -> Iterator[ET._Element]:
    """Yield only element children (skip comments, PIs, etc.)."""
    for child in element:
        if is_element(child):
            yield child

def walk(root: ET._Element) -> Iterator[ET._Element]:
    """
    Depth-first traversal yielding elements only, in document order.
    Replaces `root.iter()` when you need to skip comments/PIs.
    """
    # Guard: sometimes callers pass comments by mistake
    if not is_element(root):
        return
    stack: list[ET._Element] = [root]
    while stack:
        el = stack.pop()
        # Yield current element
        yield el
        # Extend with element children in reverse to keep doc order
        kids = [c for c in el if is_element(c)]
        stack.extend(reversed(kids))

def iter_descendants(element: ET._Element) -> Iterator[ET._Element]:
    """Yield descendants (excluding the element itself), element-only."""
    for el in children(element):
        yield el
        yield from iter_descendants(el)

def count_elements(root: ET._Element) -> int:
    """Count all real elements in tree (excluding comments, PIs)."""
    return sum(1 for _ in walk(root))

def find_elements_by_tag(root: ET._Element, tag: str) -> Iterator[ET._Element]:
    """Find all elements with specific tag, safely ignoring comments/PIs."""
    for elem in walk(root):
        local_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if local_tag == tag:
            yield elem
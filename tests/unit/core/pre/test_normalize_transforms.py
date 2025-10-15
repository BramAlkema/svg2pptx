#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
from lxml import etree as ET

from core.pre.normalize_transforms import NormalizeTransformsPreprocessor, normalize_transform_hierarchy

SVG_NS = "http://www.w3.org/2000/svg"


def _svg(fragment: str) -> ET.Element:
    return ET.fromstring(f'<svg xmlns="{SVG_NS}" width="200px" height="100px">{fragment}</svg>')


def test_rect_translation_is_flattened():
    svg = _svg('<rect x="0" y="0" width="10" height="5" transform="translate(5,7)"/>')
    pre = NormalizeTransformsPreprocessor(flatten_simple_transforms=True)
    result = pre.process(svg)

    rect = result.find(f'{{{SVG_NS}}}rect')
    assert float(rect.get("x")) == 5.0
    assert float(rect.get("y")) == 7.0
    assert rect.get("transform") is None
    # width/height normalized to numeric strings
    assert result.get("width") == "200.0"
    assert result.get("viewBox") == "0 0 200.0 100.0"


def test_text_translation_applied_to_position():
    svg = _svg('<text x="1" y="2" transform="translate(3,4)">Hi</text>')
    result = normalize_transform_hierarchy(svg, flatten_simple=True)

    text = result.find(f'{{{SVG_NS}}}text')
    assert text.get("transform") is None
    assert float(text.get("x")) == 4.0
    assert float(text.get("y")) == 6.0


def test_path_retains_matrix_when_not_flattened():
    svg = _svg('<path d="M0 0 L1 1" transform="scale(2,3) rotate(45)"/>')
    pre = NormalizeTransformsPreprocessor(flatten_simple_transforms=False)
    result = pre.process(svg)

    path = result.find(f'{{{SVG_NS}}}path')
    transform = path.get("transform")
    assert transform.startswith("matrix(")
    # ensure matrix encodes scaling (diagonal entries non-zero)
    values = [float(x) for x in transform[len("matrix("):-1].split(",")]
    matrix = np.array([[values[0], values[2], values[4]],
                       [values[1], values[3], values[5]],
                       [0.0, 0.0, 1.0]])
    assert not np.allclose(matrix, np.eye(3))

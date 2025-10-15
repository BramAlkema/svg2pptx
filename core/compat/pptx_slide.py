"""Slide XML generation helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SlideDimensions:
    width: int
    height: int


class SlideBuilder:
    """Render minimal slide XML content with provided DrawingML shapes."""

    def __init__(self, dimensions: SlideDimensions):
        self.dimensions = dimensions

    def render(self, drawingml_shapes: str) -> str:
        shapes_clean = '\n'.join(
            line.strip() for line in drawingml_shapes.split('\n') if line.strip()
        )

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="{self.dimensions.width}" cy="{self.dimensions.height}"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="{self.dimensions.width}" cy="{self.dimensions.height}"/>
                </a:xfrm>
            </p:grpSpPr>
            {shapes_clean}
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sld>'''


__all__ = ["SlideBuilder", "SlideDimensions"]

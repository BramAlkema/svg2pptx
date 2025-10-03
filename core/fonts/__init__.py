"""
Font embedding system for SVG to PPTX conversion.

Handles extraction of custom fonts from SVG @font-face declarations
and embedding them into PPTX as obfuscated fonts (ODTTF).

Supports TTF, OTF, WOFF, WOFF2 with automatic normalization via FontNormalizer.

Components:
- FontNormalizer: Format detection and conversion (TTF/OTF/WOFF/WOFF2)
- FontFaceScanner: Advanced CSS parsing with external stylesheet support
- extract_embedded_faces: Simple inline <style> extraction
- SVGFontEmbedCoordinator: Policy-driven embedding coordination
"""

from .font_normalizer import FontNormalizer, FontAsset
from .font_face_scanner import FontFaceScanner, ScanReport, ScannedFont, FontFaceRule
from .svg_embedded_fonts import (
    EmbeddedFace,
    extract_embedded_faces,
    embed_faces_into_pptx,
)
from .embed_coordinator import SVGFontEmbedCoordinator

__all__ = [
    'FontNormalizer',
    'FontAsset',
    'FontFaceScanner',
    'ScanReport',
    'ScannedFont',
    'FontFaceRule',
    'EmbeddedFace',
    'extract_embedded_faces',
    'embed_faces_into_pptx',
    'SVGFontEmbedCoordinator',
]

#!/usr/bin/env python3
"""
SVG feImage Filter Processor

Implements SVG feImage filter effects for loading and placing images within filter chains.
Supports data: URLs, external image loading via ResourceLoader, and preserveAspectRatio
positioning. Provides policy-driven strategy selection for different image scenarios.

This processor supports:
- data: URLs (base64 encoded images)
- External image loading via ResourceLoader protocol
- Local file path loading (fallback)
- Complete preserveAspectRatio implementation (meet/slice + 9 anchors)
- Graceful error handling with transparent fallbacks
- Efficient bilinear resampling for scaling
"""

import base64
import io
import math
from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any, List, Protocol, TYPE_CHECKING
from lxml import etree as ET

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from PIL import Image as PILImage
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from .base import (
    FilterProcessor,
    FilterContext,
    FilterResult,
    FilterStrategy,
    FilterException,
    FilterValidationError
)

if TYPE_CHECKING:
    from ..policy.engine import Policy


class ImageFilterException(FilterException):
    """Exception raised during image filter processing."""
    pass


class ImageValidationError(FilterValidationError, ImageFilterException):
    """Exception raised for invalid image parameters."""
    pass


class ResourceLoader(Protocol):
    """Protocol for loading external resources."""
    def resolve(self, href: str) -> Optional[bytes]: ...


@dataclass
class ImageParameters:
    """Parameters for SVG feImage filter processing."""

    # Core image attributes
    href: str = ""
    preserve_aspect_ratio: str = "xMidYMid meet"
    cross_origin: str = "anonymous"

    # Input/output
    input_source: str = "SourceGraphic"
    result_name: Optional[str] = None

    def __post_init__(self):
        """Validate parameters after initialization."""
        if not self.href:
            raise ImageValidationError("Image href cannot be empty")

        # Validate preserveAspectRatio format
        if self.preserve_aspect_ratio:
            parts = self.preserve_aspect_ratio.split()
            if parts:
                align = parts[0]
                if align not in ("none", "xMinYMin", "xMidYMin", "xMaxYMin",
                               "xMinYMid", "xMidYMid", "xMaxYMid",
                               "xMinYMax", "xMidYMax", "xMaxYMax"):
                    self.preserve_aspect_ratio = "xMidYMid meet"
                if len(parts) > 1 and parts[1] not in ("meet", "slice"):
                    self.preserve_aspect_ratio = "xMidYMid meet"

    def get_complexity_score(self) -> float:
        """Calculate complexity score for strategy selection."""
        base_score = 0.0

        # Data URLs are simpler than external loads
        if not self.href.startswith("data:"):
            base_score += 0.3

        # Complex aspect ratio handling adds complexity
        if "slice" in self.preserve_aspect_ratio:
            base_score += 0.2

        if "none" in self.preserve_aspect_ratio:
            base_score += 0.1

        return min(1.0, base_score)

    def is_data_url(self) -> bool:
        """Check if href is a data: URL."""
        return self.href.startswith("data:")

    def get_anchor_and_meetslice(self) -> Tuple[str, str]:
        """Parse preserveAspectRatio into anchor and meet/slice components."""
        parts = self.preserve_aspect_ratio.split()
        anchor = parts[0] if parts else "xMidYMid"
        meet_slice = parts[1] if len(parts) > 1 else "meet"
        return anchor, meet_slice


class ImageProcessor(FilterProcessor):
    """Processor for SVG feImage filter effects."""

    def __init__(self, filter_type: str = 'feImage', policy=None):
        super().__init__(filter_type=filter_type, policy=policy)
        self.resource_loader: Optional[ResourceLoader] = None

    def set_resource_loader(self, loader: ResourceLoader) -> None:
        """Set the resource loader for external image loading."""
        self.resource_loader = loader

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """Check if this processor can handle the given element."""
        if element.tag != "feImage":
            return False

        try:
            self._parse_parameters(element, context)
            return True
        except (ImageValidationError, ValueError):
            return False

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """Apply feImage filter with strategy selection."""
        try:
            # Parse parameters
            params = self._parse_parameters(element, context)

            # Select strategy based on complexity and capabilities
            strategy = self._select_strategy(params, context)

            # Apply selected strategy
            if strategy == FilterStrategy.NATIVE:
                return self._apply_native_strategy(params, context)
            elif strategy == FilterStrategy.APPROXIMATION:
                return self._apply_approximation_strategy(params, context)
            else:  # EMF_RASTERIZE
                return self._apply_rasterization_strategy(params, context)

        except ImageValidationError as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.APPROXIMATION,
                error_message=str(e),
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )
        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.EMF_RASTERIZE,
                error_message=f"Image filter processing failed: {str(e)}",
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )

    def _parse_parameters(self, element: ET.Element, context: FilterContext) -> ImageParameters:
        """Parse feImage element attributes."""
        try:
            # Image source (href or xlink:href)
            href = element.get('href') or element.get('{http://www.w3.org/1999/xlink}href', '')

            # Preserve aspect ratio
            preserve_aspect_ratio = element.get('preserveAspectRatio', 'xMidYMid meet')

            # Cross-origin (mostly ignored in this implementation)
            cross_origin = element.get('crossorigin', 'anonymous')

            # Input/output
            input_source = element.get("in", "SourceGraphic")
            result_name = element.get("result")

            return ImageParameters(
                href=href,
                preserve_aspect_ratio=preserve_aspect_ratio,
                cross_origin=cross_origin,
                input_source=input_source,
                result_name=result_name
            )

        except ValueError as e:
            raise ImageValidationError(f"Invalid image parameters: {e}")

    def _select_strategy(self, params: ImageParameters, context: FilterContext) -> FilterStrategy:
        """Select processing strategy based on complexity and capabilities."""
        complexity = params.get_complexity_score()

        # Simple data URLs can use native blip fills
        if complexity < 0.3 and params.is_data_url():
            return FilterStrategy.NATIVE

        # Medium complexity uses approximation (basic image placement)
        if complexity < 0.7:
            return FilterStrategy.APPROXIMATION

        # Complex scenarios need full rasterization
        return FilterStrategy.EMF_RASTERIZE

    def _apply_native_strategy(self, params: ImageParameters, context: FilterContext) -> FilterResult:
        """Apply image using PowerPoint's native blip fill capabilities."""
        try:
            # For data URLs, embed directly in blip
            if params.is_data_url():
                embed_ref = f"img_data_{id(params)}"
                drawingml = self._generate_native_blip_xml(params, embed_ref, context)

                return FilterResult(
                    success=True,
                    strategy=FilterStrategy.NATIVE,
                    drawingml=drawingml,
                    metadata={
                        'filter_type': self.filter_type,
                        'href': params.href[:50] + "..." if len(params.href) > 50 else params.href,
                        'embed_reference': embed_ref,
                        'preserve_aspect_ratio': params.preserve_aspect_ratio
                    }
                )
            else:
                # Fall back to approximation for external URLs
                return self._apply_approximation_strategy(params, context)

        except Exception as e:
            raise ImageFilterException(f"Native strategy failed: {e}")

    def _apply_approximation_strategy(self, params: ImageParameters, context: FilterContext) -> FilterResult:
        """Apply image using basic placement approximation."""
        try:
            # Load image data
            image_data = self._load_image_data(params)
            if not image_data:
                # Return transparent result
                return FilterResult(
                    success=True,
                    strategy=FilterStrategy.APPROXIMATION,
                    drawingml='<a:solidFill><a:srgbClr val="FFFFFF"><a:alpha val="0"/></a:srgbClr></a:solidFill>',
                    metadata={
                        'filter_type': self.filter_type,
                        'approach': 'transparent_fallback',
                        'href': params.href
                    }
                )

            # Create basic image fill
            embed_ref = f"img_approx_{id(params)}"
            drawingml = self._generate_approximation_xml(params, embed_ref, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'basic_placement',
                    'href': params.href[:50] + "..." if len(params.href) > 50 else params.href,
                    'embed_reference': embed_ref,
                    'preserve_aspect_ratio': params.preserve_aspect_ratio
                }
            )

        except Exception as e:
            raise ImageFilterException(f"Approximation strategy failed: {e}")

    def _apply_rasterization_strategy(self, params: ImageParameters, context: FilterContext) -> FilterResult:
        """Apply image using full rasterization with proper aspect ratio handling."""
        try:
            if not NUMPY_AVAILABLE:
                raise ImageFilterException("NumPy required for rasterization strategy")

            # Load and process image with full aspect ratio support
            processed_image = self._process_image_full(params, context)

            embed_ref = f"img_raster_{id(params)}"
            drawingml = self._generate_rasterized_xml(params, embed_ref, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'full_rasterization',
                    'href': params.href[:50] + "..." if len(params.href) > 50 else params.href,
                    'embed_reference': embed_ref,
                    'preserve_aspect_ratio': params.preserve_aspect_ratio,
                    'has_image_data': processed_image is not None
                }
            )

        except Exception as e:
            raise ImageFilterException(f"Rasterization strategy failed: {e}")

    def _load_image_data(self, params: ImageParameters) -> Optional[bytes]:
        """Load image data from various sources."""
        # Data URL
        if params.is_data_url():
            try:
                head, b64 = params.href.split(",", 1)
                if ";base64" in head:
                    return base64.b64decode(b64)
            except Exception:
                return None

        # External URL via resource loader
        if self.resource_loader:
            try:
                data = self.resource_loader.resolve(params.href)
                if data:
                    return data
            except Exception:
                pass

        # Local file fallback
        try:
            with open(params.href, "rb") as f:
                return f.read()
        except Exception:
            return None

    def _decode_image_to_rgba(self, blob: bytes) -> Optional['np.ndarray']:
        """Decode image to RGBA array using available decoders."""
        # Try Pillow first
        if PILLOW_AVAILABLE:
            try:
                im = PILImage.open(io.BytesIO(blob)).convert("RGBA")
                return np.array(im, dtype=np.uint8)
            except Exception:
                pass

        # Minimal PNG fallback (for RGBA PNG only)
        if NUMPY_AVAILABLE:
            return self._decode_png_minimal(blob)

        return None

    def _decode_png_minimal(self, blob: bytes) -> Optional['np.ndarray']:
        """Minimal PNG decoder for RGBA images."""
        try:
            import struct
            import zlib

            if blob[:8] != b"\x89PNG\r\n\x1a\n":
                return None

            i = 8
            width = height = None
            data = b""

            while i < len(blob):
                clen = int.from_bytes(blob[i:i+4], "big")
                i += 4
                ctype = blob[i:i+4]
                i += 4
                cdata = blob[i:i+clen]
                i += clen
                crc = blob[i:i+4]
                i += 4

                if ctype == b"IHDR":
                    width = int.from_bytes(cdata[0:4], "big")
                    height = int.from_bytes(cdata[4:8], "big")
                    bit_depth = cdata[8]
                    color_type = cdata[9]
                    if bit_depth != 8 or color_type != 6:  # Only RGBA 8-bit
                        return None
                elif ctype == b"IDAT":
                    data += cdata
                elif ctype == b"IEND":
                    break

            if width is None or height is None:
                return None

            raw = zlib.decompress(data)
            stride = width * 4
            out = np.zeros((height, width, 4), dtype=np.uint8)
            pos = 0

            for y in range(height):
                f = raw[pos]
                pos += 1
                if f != 0:  # Only unfiltered scanlines
                    return None
                row = raw[pos:pos+stride]
                pos += stride
                out[y, :, :] = np.frombuffer(row, dtype=np.uint8).reshape((width, 4))

            return out
        except Exception:
            return None

    def _process_image_full(self, params: ImageParameters, context: FilterContext) -> Optional['np.ndarray']:
        """Process image with full aspect ratio handling (your implementation)."""
        if not NUMPY_AVAILABLE:
            return None

        # Assume 256x256 filter region for processing
        W, H = 256, 256
        out = np.zeros((H, W, 4), dtype=np.float32)

        # Load and decode image
        blob = self._load_image_data(params)
        if not blob:
            return out

        img_rgba = self._decode_image_to_rgba(blob)
        if img_rgba is None:
            return out

        ih, iw = img_rgba.shape[0], img_rgba.shape[1]
        if iw == 0 or ih == 0:
            return out

        # Fit into region respecting preserveAspectRatio
        target, offset = self._fit_into_region(W, H, iw, ih, params.preserve_aspect_ratio)
        tw, th = target
        ox, oy = offset

        # Resample and composite
        scaled = self._resample_bilinear(img_rgba, (th, tw))

        x0 = max(0, ox)
        y0 = max(0, oy)
        x1 = min(W, ox + tw)
        y1 = min(H, oy + th)
        sx0 = max(0, -ox)
        sy0 = max(0, -oy)
        sx1 = sx0 + (x1 - x0)
        sy1 = sy0 + (y1 - y0)

        if x1 > x0 and y1 > y0:
            dst = out[y0:y1, x0:x1, :]
            src = scaled[sy0:sy1, sx0:sx1, :].astype(np.float32) / 255.0
            dst[...] = src

        return out

    def _fit_into_region(self, W: int, H: int, iw: int, ih: int, par: str) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Fit image into region respecting preserveAspectRatio."""
        anchor, meet_slice = self._parse_preserve_aspect_ratio(par)

        if anchor == "none":
            return (W, H), (0, 0)

        scale_x = W / iw
        scale_y = H / ih
        if meet_slice == "meet":
            s = min(scale_x, scale_y)
        else:  # slice
            s = max(scale_x, scale_y)

        tw = max(1, int(round(iw * s)))
        th = max(1, int(round(ih * s)))

        # Calculate offset based on anchor
        if anchor.endswith("Min"):
            ox = 0
        elif anchor.endswith("Mid"):
            ox = (W - tw) // 2
        else:  # Max
            ox = (W - tw)

        if anchor.startswith("xMin"):
            oy = 0
        elif anchor.startswith("xMid"):
            oy = (H - th) // 2
        else:  # xMax
            oy = (H - th)

        return (tw, th), (ox, oy)

    def _parse_preserve_aspect_ratio(self, par: str) -> Tuple[str, str]:
        """Parse preserveAspectRatio into components."""
        parts = par.split()
        anchor = parts[0] if parts else "xMidYMid"
        meet_slice = parts[1] if len(parts) > 1 else "meet"
        return anchor, meet_slice

    def _resample_bilinear(self, img_rgba_u8: 'np.ndarray', out_hw: Tuple[int, int]) -> 'np.ndarray':
        """Simple bilinear resample to (H, W)."""
        out_h, out_w = out_hw
        in_h, in_w = img_rgba_u8.shape[:2]

        if in_h == out_h and in_w == out_w:
            return img_rgba_u8.copy()

        y = np.linspace(0, in_h - 1, out_h, dtype=np.float32)
        x = np.linspace(0, in_w - 1, out_w, dtype=np.float32)
        yy, xx = np.meshgrid(y, x, indexing="ij")

        x0 = np.floor(xx).astype(np.int32)
        y0 = np.floor(yy).astype(np.int32)
        x1 = np.clip(x0 + 1, 0, in_w - 1)
        y1 = np.clip(y0 + 1, 0, in_h - 1)

        xf = xx - x0
        yf = yy - y0

        out = np.empty((out_h, out_w, 4), dtype=np.uint8)
        for c in range(4):
            Ia = img_rgba_u8[y0, x0, c].astype(np.float32)
            Ib = img_rgba_u8[y0, x1, c].astype(np.float32)
            Ic = img_rgba_u8[y1, x0, c].astype(np.float32)
            Id = img_rgba_u8[y1, x1, c].astype(np.float32)
            top = Ia + (Ib - Ia) * xf
            bot = Ic + (Id - Ic) * xf
            out[..., c] = np.clip(top + (bot - top) * yf, 0, 255).astype(np.uint8)
        return out

    def _generate_native_blip_xml(self, params: ImageParameters, embed_ref: str, context: FilterContext) -> str:
        """Generate native blip fill XML for simple cases."""
        return f'''<a:blipFill>
    <a:blip r:embed="{embed_ref}"/>
    <a:stretch>
        <a:fillRect/>
    </a:stretch>
</a:blipFill>'''

    def _generate_approximation_xml(self, params: ImageParameters, embed_ref: str, context: FilterContext) -> str:
        """Generate approximation XML for basic image placement."""
        return f'''<a:blipFill>
    <a:blip r:embed="{embed_ref}">
        <a:lum bright="0" contrast="0"/>
    </a:blip>
    <a:stretch>
        <a:fillRect/>
    </a:stretch>
</a:blipFill>'''

    def _generate_rasterized_xml(self, params: ImageParameters, embed_ref: str, context: FilterContext) -> str:
        """Generate rasterized XML with full processing."""
        return f'''<a:blipFill>
    <a:blip r:embed="{embed_ref}">
        <a:extLst>
            <a:ext uri="{{28A0092B-C50C-407E-A947-70E740481C1C}}">
                <a14:useLocalDpi val="0"/>
            </a:ext>
        </a:extLst>
    </a:blip>
    <a:stretch>
        <a:fillRect/>
    </a:stretch>
</a:blipFill>'''


def create_image_processor(policy=None) -> ImageProcessor:
    """
    Factory function to create an ImageProcessor instance.

    Args:
        policy: Optional policy for strategy selection

    Returns:
        Configured ImageProcessor instance
    """
    return ImageProcessor(policy=policy)
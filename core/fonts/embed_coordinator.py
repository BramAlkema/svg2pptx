# core/fonts/embed_coordinator.py
from typing import Dict, List, Tuple, Optional
import logging
from .svg_embedded_fonts import extract_embedded_faces, embed_faces_into_pptx, EmbeddedFace


class SVGFontEmbedCoordinator:
    """
    Coordinates font embedding with policy-based decision making.

    Integrates with PolicyEngine to decide which fonts to embed based on:
    - Deduplication (SHA-1 checksum)
    - Size limits (configurable max size)
    - Feature flags (enable_font_embedding)
    """

    def __init__(self, policy=None):
        """
        Initialize font embedding coordinator.

        Args:
            policy: Optional PolicyEngine instance for embedding decisions
        """
        # Cache of embedded fonts (by SHA-1 checksum)
        self._seen_sha: set = set()
        self.policy = policy
        self.logger = logging.getLogger(__name__)

    def harvest_and_embed(self, svg_string: str, pptx_path: str, svg_base_path: str = '.') -> Dict[str, List[Tuple[str, str]]]:
        """
        Extract fonts from SVG and embed them into PPTX using policy decisions.

        Args:
            svg_string: SVG content as string
            pptx_path: Path to PPTX file to augment
            svg_base_path: Base directory for resolving relative font paths (default: current directory)

        Returns:
            Registry mapping font families to (relId, partName) tuples
        """
        # Extract all fonts from SVG
        all_faces = extract_embedded_faces(svg_string, svg_base_path)

        if not all_faces:
            return {}

        # Apply policy decisions to each font
        faces_to_embed: List[EmbeddedFace] = []

        for face in all_faces:
            # Use policy engine if available, otherwise use simple dedup
            if self.policy:
                decision = self.policy.decide_font_embedding(
                    font_family=face.family,
                    font_size_bytes=len(face.data),
                    sha1_checksum=face.sha1,
                    already_embedded=self._seen_sha
                )

                if decision.should_embed:
                    faces_to_embed.append(face)
                    self._seen_sha.add(face.sha1)
                    self.logger.debug(
                        f"Policy decision: EMBED font '{face.family}' "
                        f"({len(face.data)} bytes, reasons: {[r.value for r in decision.reasons]})"
                    )
                else:
                    self.logger.debug(
                        f"Policy decision: SKIP font '{face.family}' "
                        f"(reasons: {[r.value for r in decision.reasons]})"
                    )
            else:
                # Fallback: simple deduplication without policy
                if face.sha1 not in self._seen_sha:
                    faces_to_embed.append(face)
                    self._seen_sha.add(face.sha1)

        if not faces_to_embed:
            return {}

        # Embed fonts into PPTX
        return embed_faces_into_pptx(pptx_path, faces_to_embed)

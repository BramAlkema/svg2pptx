"""
SVG Color Profile Adapter for SVG2PPTX

Parses and manages SVG <color-profile> elements and integrates them with the
CSS Color 4 parser and ICC converter system.

Supports:
- SVG <color-profile> element parsing from <defs>
- ICC profile loading and registration
- Integration with CSS Color 4 color() functions
- ConversionContext integration for SVG processing
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SVGColorProfile:
    """Represents an SVG <color-profile> element"""
    name: str
    src: Optional[str] = None
    rendering_intent: str = "auto"
    local: Optional[str] = None

    @property
    def profile_id(self) -> str:
        """Get normalized profile identifier for lookups"""
        return self.name.replace(' ', '_').lower()


class SVGColorProfileRegistry:
    """
    Registry for SVG color profiles parsed from <color-profile> elements

    Integrates with CSS Color 4 parser and ICC converter for unified color handling
    """

    def __init__(self, icc_converter=None, css4_converter=None):
        """
        Initialize the SVG color profile registry

        Args:
            icc_converter: ICCConverter instance for profile-based conversion
            css4_converter: CSSColor4Converter instance for CSS Color 4 support
        """
        self.profiles: Dict[str, SVGColorProfile] = {}
        self.icc_converter = icc_converter
        self.css4_converter = css4_converter

        # Profile search paths
        self.profile_paths = [
            Path(__file__).parent.parent.parent / "profiles" / "icc",  # Bundled profiles
            Path.home() / "Library" / "ColorSync" / "Profiles",  # macOS system profiles
            Path("/System/Library/ColorSync/Profiles"),  # macOS system profiles
        ]

    def parse_color_profiles(self, svg_root) -> List[SVGColorProfile]:
        """
        Parse all <color-profile> elements from SVG document

        Args:
            svg_root: lxml Element representing SVG root

        Returns:
            List of parsed SVGColorProfile objects
        """
        profiles = []

        # Find all <color-profile> elements (usually in <defs>)
        color_profile_elements = svg_root.xpath('.//color-profile')

        for element in color_profile_elements:
            try:
                profile = self._parse_color_profile_element(element)
                if profile:
                    profiles.append(profile)
                    self.profiles[profile.profile_id] = profile
                    logger.debug(f"Registered SVG color profile: {profile.name}")
            except Exception as e:
                logger.warning(f"Failed to parse color-profile element: {e}")

        return profiles

    def _parse_color_profile_element(self, element) -> Optional[SVGColorProfile]:
        """Parse individual <color-profile> element"""
        name = element.get('name')
        if not name:
            logger.warning("color-profile element missing required 'name' attribute")
            return None

        # Parse attributes
        src = element.get('xlink:href') or element.get('href')
        rendering_intent = element.get('rendering-intent', 'auto')
        local = element.get('local')

        return SVGColorProfile(
            name=name,
            src=src,
            rendering_intent=rendering_intent,
            local=local
        )

    def resolve_profile_path(self, profile: SVGColorProfile) -> Optional[Path]:
        """
        Resolve the actual file path for a color profile

        Args:
            profile: SVGColorProfile to resolve

        Returns:
            Path to ICC profile file if found, None otherwise
        """
        # Try local reference first
        if profile.local:
            for search_path in self.profile_paths:
                local_path = search_path / f"{profile.local}.icc"
                if local_path.exists():
                    return local_path
                local_path = search_path / f"{profile.local}.icm"
                if local_path.exists():
                    return local_path

        # Try src reference
        if profile.src:
            # Handle different src formats
            src = profile.src

            # Remove file:// prefix if present
            if src.startswith('file://'):
                src = src[7:]

            # Try as absolute path
            src_path = Path(src)
            if src_path.exists():
                return src_path

            # Try relative to profile search paths
            for search_path in self.profile_paths:
                relative_path = search_path / src_path.name
                if relative_path.exists():
                    return relative_path

        # Try standard profile names
        standard_names = [
            f"{profile.name}.icc",
            f"{profile.name}.icm",
            f"{profile.profile_id}.icc",
            f"{profile.profile_id}.icm",
        ]

        for search_path in self.profile_paths:
            for name in standard_names:
                profile_path = search_path / name
                if profile_path.exists():
                    return profile_path

        return None

    def get_profile(self, name: str) -> Optional[SVGColorProfile]:
        """Get registered color profile by name"""
        profile_id = name.replace(' ', '_').lower()
        return self.profiles.get(profile_id)

    def convert_color_with_profile(self,
                                 color_components: Tuple[float, ...],
                                 profile_name: str,
                                 alpha: float = 1.0) -> Tuple[float, float, float, float]:
        """
        Convert color using specified SVG color profile

        Args:
            color_components: Color component values (usually RGB)
            profile_name: Name of the color profile to use
            alpha: Alpha transparency value

        Returns:
            (r, g, b, a) tuple in sRGB space
        """
        profile = self.get_profile(profile_name)
        if not profile:
            logger.warning(f"Color profile '{profile_name}' not found, using sRGB")
            return (*color_components[:3], alpha)

        # Try ICC converter first
        if self.icc_converter:
            try:
                profile_path = self.resolve_profile_path(profile)
                if profile_path:
                    result = self.icc_converter.convert_to_srgb(
                        color_components,
                        str(profile_path)
                    )
                    if result.success:
                        return (*result.color, alpha)
            except Exception as e:
                logger.debug(f"ICC conversion failed for profile {profile_name}: {e}")

        # Fallback to CSS4 converter if available
        if self.css4_converter:
            try:
                from .css_color4_parser import CSSColor

                # Map common SVG profile names to CSS Color 4 space names
                css_space_map = {
                    'srgb': 'srgb',
                    'display-p3': 'display_p3',
                    'displayp3': 'display_p3',
                    'rec2020': 'rec2020',
                    'rec-2020': 'rec2020',
                    'adobe-rgb': 'adobe_rgb',
                    'adobergb': 'adobe_rgb',
                    'prophoto-rgb': 'prophoto_rgb',
                    'prophotorgb': 'prophoto_rgb',
                }

                css_space = css_space_map.get(profile.profile_id, profile.profile_id)
                css_color = CSSColor(css_space, color_components, alpha)

                return self.css4_converter.convert_css_color(css_color)

            except Exception as e:
                logger.debug(f"CSS4 conversion failed for profile {profile_name}: {e}")

        # Ultimate fallback - treat as sRGB
        logger.warning(f"No conversion available for profile {profile_name}, treating as sRGB")
        return (*color_components[:3], alpha)

    def detect_profile_usage(self, svg_root) -> List[str]:
        """
        Detect which color profiles are referenced in the SVG

        Args:
            svg_root: lxml Element representing SVG root

        Returns:
            List of profile names found in use
        """
        used_profiles = set()

        # Look for color() functions with profile references
        # This would integrate with the CSS Color 4 parser
        if self.css4_converter:
            try:
                # Get all style attributes and content
                style_texts = []

                # Get style attributes
                for element in svg_root.xpath('.//*[@style]'):
                    style_texts.append(element.get('style', ''))

                # Get <style> element content
                for style_element in svg_root.xpath('.//style'):
                    if style_element.text:
                        style_texts.append(style_element.text)

                # Detect color functions
                for style_text in style_texts:
                    color_functions = self.css4_converter.parser.detect_color_functions(style_text)
                    for original, parsed in color_functions:
                        # Add the color space as a potentially used profile
                        used_profiles.add(parsed.space)

            except Exception as e:
                logger.debug(f"Profile usage detection failed: {e}")

        return list(used_profiles)

    def validate_profiles(self) -> Dict[str, bool]:
        """
        Validate that all registered profiles can be resolved

        Returns:
            Dictionary mapping profile names to validation status
        """
        validation_results = {}

        for profile_id, profile in self.profiles.items():
            try:
                profile_path = self.resolve_profile_path(profile)
                validation_results[profile_id] = profile_path is not None

                if profile_path:
                    logger.debug(f"Profile {profile.name} resolved to: {profile_path}")
                else:
                    logger.warning(f"Profile {profile.name} could not be resolved")

            except Exception as e:
                logger.error(f"Profile validation failed for {profile.name}: {e}")
                validation_results[profile_id] = False

        return validation_results


def create_svg_profile_registry(svg_root, icc_converter=None, css4_converter=None) -> SVGColorProfileRegistry:
    """
    Factory function to create and populate an SVG color profile registry

    Args:
        svg_root: lxml Element representing SVG root
        icc_converter: Optional ICCConverter instance
        css4_converter: Optional CSSColor4Converter instance

    Returns:
        Populated SVGColorProfileRegistry
    """
    registry = SVGColorProfileRegistry(
        icc_converter=icc_converter,
        css4_converter=css4_converter
    )

    # Parse profiles from SVG
    profiles = registry.parse_color_profiles(svg_root)

    logger.info(f"SVG color profile registry created with {len(profiles)} profiles")

    return registry


def integrate_with_conversion_context(context, svg_root):
    """
    Integrate SVG color profile parsing with ConversionContext

    This function can be called during SVG preprocessing to set up
    color profile support for the conversion process.

    Args:
        context: ConversionContext instance
        svg_root: lxml Element representing SVG root
    """
    try:
        # Get color services from context
        services = getattr(context, 'services', None)
        if not services:
            logger.debug("No services available in conversion context")
            return

        # Get converters if available
        icc_converter = getattr(services, 'icc_converter', None)
        css4_converter = getattr(services, 'css4_converter', None)

        # Create and populate registry
        registry = create_svg_profile_registry(
            svg_root,
            icc_converter=icc_converter,
            css4_converter=css4_converter
        )

        # Attach registry to context for use during conversion
        context.color_profile_registry = registry

        # Validate profiles
        validation_results = registry.validate_profiles()
        valid_count = sum(validation_results.values())
        total_count = len(validation_results)

        logger.info(f"Color profile integration: {valid_count}/{total_count} profiles validated")

    except Exception as e:
        logger.error(f"Failed to integrate color profiles with conversion context: {e}")
        # Don't fail the conversion, just continue without color profile support
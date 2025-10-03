#!/usr/bin/env python3
"""
Color Profile Registry

Central registry for managing ICC color profiles within a document.
Provides thread-safe profile registration, resolution, and caching
for SVG and CSS color profile references.
"""

from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Set, Union
import logging

from .profile_model import ColorProfileRef, normalize_profile_reference, ProfileReference

logger = logging.getLogger(__name__)


@dataclass
class ProfileRegistryConfig:
    """
    Configuration for color profile registry behavior.

    Attributes:
        enable_remote_profiles: Allow loading profiles from remote URLs
        enable_data_urls: Allow embedded profiles via data: URLs
        max_profiles: Maximum number of profiles to cache
        cache_directory: Directory for cached ICC files (None = memory only)
        default_rendering_intent: Default intent when not specified
        strict_validation: Enforce strict ICC profile validation
    """
    enable_remote_profiles: bool = False
    enable_data_urls: bool = True
    max_profiles: int = 100
    cache_directory: Optional[Path] = None
    default_rendering_intent: str = "auto"
    strict_validation: bool = True


class ColorProfileRegistry:
    """
    Thread-safe registry for managing ICC color profiles within a document.

    Provides centralized management of color profile references from SVG
    <color-profile> elements and CSS @color-profile rules, with support
    for caching, validation, and policy enforcement.
    """

    def __init__(self, config: Optional[ProfileRegistryConfig] = None,
                 asset_loader=None):
        """
        Initialize profile registry with configuration.

        Args:
            config: Registry configuration (uses defaults if None)
            asset_loader: Asset loader for ICC profile files (optional)
        """
        self.config = config or ProfileRegistryConfig()
        self._profiles: Dict[str, ColorProfileRef] = {}
        self._profile_paths: Dict[str, Optional[Path]] = {}
        self._lock = RLock()
        self._access_count: Dict[str, int] = defaultdict(int)

        # Asset loader for ICC profile files (lazy-initialized if needed)
        self._asset_loader = asset_loader

        # Built-in profiles that are always available
        self._register_builtin_profiles()

    def _register_builtin_profiles(self) -> None:
        """Register standard built-in color profiles."""
        builtin_profiles = [
            ColorProfileRef(name="srgb", local=True),
            ColorProfileRef(name="display-p3", local=True),
            ColorProfileRef(name="rec2020", local=True),
            ColorProfileRef(name="prophoto-rgb", local=True),
            ColorProfileRef(name="a98-rgb", local=True),
        ]

        for profile in builtin_profiles:
            self._profiles[profile.name] = profile
            self._profile_paths[profile.name] = None  # Built-in, no file path

    def register_svg_profile(self, element) -> bool:
        """
        Register color profile from SVG <color-profile> element.

        Args:
            element: SVG color-profile element (lxml.etree.Element)

        Returns:
            True if successfully registered, False otherwise
        """
        with self._lock:
            try:
                # Extract attributes from SVG element
                name = element.get('name')
                if not name:
                    logger.warning("SVG color-profile missing 'name' attribute")
                    return False

                href = element.get('href') or element.get('{http://www.w3.org/1999/xlink}href')
                local = element.get('local', 'true').lower() == 'true'
                rendering_intent = element.get('rendering-intent', self.config.default_rendering_intent)

                # Create profile reference with proper rendering intent conversion
                from .profile_model import RenderingIntent
                rendering_intent_enum = RenderingIntent.from_string(rendering_intent)

                profile_ref = ColorProfileRef(
                    name=name,
                    href=href,
                    local=local,
                    rendering_intent=rendering_intent_enum
                )

                return self._register_profile(profile_ref)

            except Exception as e:
                logger.error(f"Failed to register SVG profile: {e}")
                return False

    def register_css_profile(self, name: str, src: Optional[str] = None,
                           rendering_intent: Optional[str] = None) -> bool:
        """
        Register color profile from CSS @color-profile rule.

        Args:
            name: Profile name (CSS ident)
            src: Profile source URL (optional)
            rendering_intent: Rendering intent (optional)

        Returns:
            True if successfully registered, False otherwise
        """
        with self._lock:
            try:
                from .profile_model import RenderingIntent
                rendering_intent_enum = RenderingIntent.from_string(
                    rendering_intent or self.config.default_rendering_intent
                )

                profile_ref = ColorProfileRef(
                    name=name,
                    href=src,
                    local=src is None,
                    rendering_intent=rendering_intent_enum
                )

                return self._register_profile(profile_ref)

            except Exception as e:
                logger.error(f"Failed to register CSS profile '{name}': {e}")
                return False

    def register_profile(self, profile: ProfileReference) -> bool:
        """
        Register color profile reference.

        Args:
            profile: Profile reference (string name or ColorProfileRef)

        Returns:
            True if successfully registered, False otherwise
        """
        with self._lock:
            try:
                profile_ref = normalize_profile_reference(profile)
                return self._register_profile(profile_ref)

            except Exception as e:
                logger.error(f"Failed to register profile: {e}")
                return False

    def _register_profile(self, profile_ref: ColorProfileRef) -> bool:
        """Internal profile registration with policy validation."""
        # Check if profile already exists
        if profile_ref.name in self._profiles:
            existing = self._profiles[profile_ref.name]
            if existing == profile_ref:
                logger.debug(f"Profile '{profile_ref.name}' already registered")
                return True
            else:
                logger.warning(f"Profile '{profile_ref.name}' already exists with different configuration")
                return False

        # Validate against policy
        if not self._validate_profile_policy(profile_ref):
            return False

        # Check registry capacity
        if len(self._profiles) >= self.config.max_profiles:
            if not self._evict_least_used():
                logger.error("Profile registry at capacity, cannot register new profile")
                return False

        # Register the profile
        self._profiles[profile_ref.name] = profile_ref
        self._profile_paths[profile_ref.name] = None  # Will be resolved on demand

        logger.info(f"Registered color profile: {profile_ref.name}")
        return True

    def _validate_profile_policy(self, profile_ref: ColorProfileRef) -> bool:
        """Validate profile against security and policy configuration."""
        # Check remote profile policy
        if profile_ref.is_remote and not self.config.enable_remote_profiles:
            logger.warning(f"Remote profiles disabled, rejecting: {profile_ref.name}")
            return False

        # Check data URL policy
        if profile_ref.is_data_url and not self.config.enable_data_urls:
            logger.warning(f"Data URL profiles disabled, rejecting: {profile_ref.name}")
            return False

        return True

    def _evict_least_used(self) -> bool:
        """Evict least recently used profile to make space."""
        # Find non-builtin profiles that can be evicted
        builtin_names = {"srgb", "display-p3", "rec2020", "prophoto-rgb", "a98-rgb"}
        candidates = [name for name in self._profiles.keys() if name not in builtin_names]

        if not candidates:
            return False

        # If we have access counts, use them; otherwise evict first non-builtin
        if self._access_count and any(name in self._access_count for name in candidates):
            # Remove least used profile
            candidates_with_counts = {name: self._access_count.get(name, 0)
                                    for name in candidates}
            least_used = min(candidates_with_counts.keys(),
                           key=lambda x: candidates_with_counts[x])
        else:
            # No access data, just remove the first non-builtin profile
            least_used = candidates[0]

        del self._profiles[least_used]
        del self._profile_paths[least_used]
        self._access_count.pop(least_used, None)

        logger.info(f"Evicted least used profile: {least_used}")
        return True

    def resolve_profile(self, name: str) -> Optional[ColorProfileRef]:
        """
        Resolve color profile by name.

        Args:
            name: Profile name to resolve

        Returns:
            ColorProfileRef if found, None otherwise
        """
        with self._lock:
            profile = self._profiles.get(name)
            if profile:
                self._access_count[name] += 1
                logger.debug(f"Resolved profile: {name}")
            else:
                logger.debug(f"Profile not found: {name}")
            return profile

    def get_profile_path(self, name: str) -> Optional[Path]:
        """
        Get file system path for profile's ICC data.

        Args:
            name: Profile name

        Returns:
            Path to ICC file if available, None otherwise
        """
        with self._lock:
            if name not in self._profiles:
                return None

            # Return cached path if available
            cached_path = self._profile_paths.get(name)
            if cached_path and cached_path.exists():
                return cached_path

            # Built-in profiles have no file path
            profile = self._profiles[name]
            if profile.href is None:
                return None

            # Attempt to resolve path using asset loader
            if self._asset_loader:
                try:
                    data = self._asset_loader.load_profile_data(profile)
                    if data:
                        # Cache the data and get the file path if available
                        cache_key = self._asset_loader._get_cache_key(profile.href)
                        cache_entry = self._asset_loader._cache.get(cache_key)
                        if cache_entry and cache_entry.file_path:
                            self._profile_paths[name] = cache_entry.file_path
                            return cache_entry.file_path
                except Exception as e:
                    logger.warning(f"Failed to load profile data for {name}: {e}")

            logger.debug(f"No file path available for profile: {name}")
            return None

    def get_profile_data(self, name: str) -> Optional[bytes]:
        """
        Get ICC profile data for a profile.

        Args:
            name: Profile name

        Returns:
            Raw ICC profile data bytes if available, None otherwise
        """
        with self._lock:
            if name not in self._profiles:
                return None

            profile = self._profiles[name]
            if profile.href is None:
                # Built-in profiles have no external data
                return None

            # Use asset loader to get profile data
            if self._asset_loader:
                try:
                    return self._asset_loader.load_profile_data(profile)
                except Exception as e:
                    logger.warning(f"Failed to load profile data for {name}: {e}")

            return None

    def list_profiles(self) -> List[str]:
        """
        Get list of all registered profile names.

        Returns:
            List of profile names sorted alphabetically
        """
        with self._lock:
            return sorted(self._profiles.keys())

    def list_available_profiles(self) -> List[str]:
        """
        Get list of profiles that are available for use.

        Returns:
            List of available profile names
        """
        with self._lock:
            available = []
            for name, profile in self._profiles.items():
                if profile.local or profile.href is None:
                    available.append(name)
                # TODO: Check if remote/data URL profiles are cached
            return sorted(available)

    def get_registry_stats(self) -> Dict[str, Union[int, List[str]]]:
        """
        Get registry statistics for monitoring and debugging.

        Returns:
            Dictionary with registry statistics
        """
        with self._lock:
            builtin_names = {"srgb", "display-p3", "rec2020", "prophoto-rgb", "a98-rgb"}
            custom_profiles = [name for name in self._profiles.keys()
                             if name not in builtin_names]

            return {
                'total_profiles': len(self._profiles),
                'builtin_profiles': len(builtin_names),
                'custom_profiles': len(custom_profiles),
                'max_capacity': self.config.max_profiles,
                'most_used': max(self._access_count.keys(),
                               key=lambda x: self._access_count[x]) if self._access_count else None,
                'custom_profile_names': sorted(custom_profiles)
            }

    def clear_custom_profiles(self) -> int:
        """
        Clear all non-builtin profiles from registry.

        Returns:
            Number of profiles removed
        """
        with self._lock:
            builtin_names = {"srgb", "display-p3", "rec2020", "prophoto-rgb", "a98-rgb"}
            custom_names = [name for name in self._profiles.keys()
                           if name not in builtin_names]

            for name in custom_names:
                del self._profiles[name]
                del self._profile_paths[name]
                self._access_count.pop(name, None)

            logger.info(f"Cleared {len(custom_names)} custom profiles")
            return len(custom_names)

    def is_profile_available(self, name: str) -> bool:
        """
        Check if profile is registered and available for use.

        Args:
            name: Profile name to check

        Returns:
            True if profile is available, False otherwise
        """
        with self._lock:
            profile = self._profiles.get(name)
            if not profile:
                return False

            # Built-in profiles are always available
            if profile.href is None:
                return True

            # TODO: Check if remote/data profiles are cached and valid
            # This will be implemented in Task 1.3
            return profile.local
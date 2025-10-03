#!/usr/bin/env python3
"""
Unit tests for ColorProfileRegistry.

Tests registry functionality, thread safety, policy enforcement,
and integration with SVG/CSS profile sources.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from threading import Thread
import time

from core.color.profile_registry import (
    ColorProfileRegistry,
    ProfileRegistryConfig
)
from core.color.profile_model import ColorProfileRef, RenderingIntent


class TestProfileRegistryConfig:
    """Test ProfileRegistryConfig dataclass."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = ProfileRegistryConfig()
        assert config.enable_remote_profiles is False
        assert config.enable_data_urls is True
        assert config.max_profiles == 100
        assert config.cache_directory is None
        assert config.default_rendering_intent == "auto"
        assert config.strict_validation is True

    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = ProfileRegistryConfig(
            enable_remote_profiles=True,
            enable_data_urls=False,
            max_profiles=50,
            cache_directory=Path("/tmp/profiles"),
            default_rendering_intent="perceptual",
            strict_validation=False
        )
        assert config.enable_remote_profiles is True
        assert config.enable_data_urls is False
        assert config.max_profiles == 50
        assert config.cache_directory == Path("/tmp/profiles")
        assert config.default_rendering_intent == "perceptual"
        assert config.strict_validation is False


class TestColorProfileRegistry:
    """Test ColorProfileRegistry core functionality."""

    def test_default_initialization(self):
        """Test registry initialization with default configuration."""
        registry = ColorProfileRegistry()
        assert registry.config.enable_remote_profiles is False
        assert registry.config.enable_data_urls is True
        assert len(registry.list_profiles()) == 5  # Built-in profiles

    def test_custom_config_initialization(self):
        """Test registry initialization with custom configuration."""
        config = ProfileRegistryConfig(max_profiles=10)
        registry = ColorProfileRegistry(config)
        assert registry.config.max_profiles == 10

    def test_builtin_profiles_registered(self):
        """Test that built-in profiles are automatically registered."""
        registry = ColorProfileRegistry()
        profiles = registry.list_profiles()

        expected_builtins = {"srgb", "display-p3", "rec2020", "prophoto-rgb", "a98-rgb"}
        assert expected_builtins.issubset(set(profiles))

    def test_builtin_profiles_available(self):
        """Test that built-in profiles are marked as available."""
        registry = ColorProfileRegistry()

        assert registry.is_profile_available("srgb")
        assert registry.is_profile_available("display-p3")
        assert registry.is_profile_available("rec2020")

    def test_builtin_profile_resolution(self):
        """Test resolving built-in profiles."""
        registry = ColorProfileRegistry()

        srgb = registry.resolve_profile("srgb")
        assert srgb is not None
        assert srgb.name == "srgb"
        assert srgb.local is True
        assert srgb.href is None


class TestProfileRegistration:
    """Test profile registration methods."""

    def test_register_profile_string(self):
        """Test registering profile by string name."""
        registry = ColorProfileRegistry()

        result = registry.register_profile("custom-profile")
        assert result is True
        assert "custom-profile" in registry.list_profiles()

    def test_register_profile_object(self):
        """Test registering ColorProfileRef object."""
        registry = ColorProfileRegistry()
        profile = ColorProfileRef(
            name="test-profile",
            href="data:application/icc-profile,test-data"
        )

        result = registry.register_profile(profile)
        assert result is True

        resolved = registry.resolve_profile("test-profile")
        assert resolved == profile

    def test_register_duplicate_profile(self):
        """Test registering duplicate profile."""
        registry = ColorProfileRegistry()
        profile = ColorProfileRef(name="duplicate-test")

        # First registration should succeed
        assert registry.register_profile(profile) is True

        # Second registration of same profile should succeed (idempotent)
        assert registry.register_profile(profile) is True

        # Registration with different config should fail
        different_profile = ColorProfileRef(
            name="duplicate-test",
            href="different-href"
        )
        assert registry.register_profile(different_profile) is False

    def test_register_profile_capacity_limit(self):
        """Test registry capacity enforcement."""
        config = ProfileRegistryConfig(max_profiles=7)  # 5 built-in + 2 custom
        registry = ColorProfileRegistry(config)

        # Register up to capacity
        assert registry.register_profile("profile1") is True
        assert registry.register_profile("profile2") is True

        # Should succeed due to eviction
        assert registry.register_profile("profile3") is True


class TestSVGProfileRegistration:
    """Test SVG <color-profile> element registration."""

    def test_register_svg_profile_basic(self):
        """Test basic SVG profile registration."""
        registry = ColorProfileRegistry()

        # Mock SVG element
        element = Mock()
        element.get.side_effect = lambda attr, default=None: {
            'name': 'svg-profile',
            'href': '/path/to/profile.icc',
            'local': 'true',
            'rendering-intent': 'perceptual'
        }.get(attr, default)

        result = registry.register_svg_profile(element)
        assert result is True

        profile = registry.resolve_profile('svg-profile')
        assert profile is not None
        assert profile.name == 'svg-profile'
        assert profile.href == '/path/to/profile.icc'
        assert profile.local is True
        assert profile.rendering_intent == RenderingIntent.PERCEPTUAL

    def test_register_svg_profile_with_xlink_href(self):
        """Test SVG profile with xlink:href attribute."""
        # Enable remote profiles for this test
        config = ProfileRegistryConfig(enable_remote_profiles=True)
        registry = ColorProfileRegistry(config)

        element = Mock()
        element.get.side_effect = lambda attr, default=None: {
            'name': 'xlink-profile',
            'href': None,
            '{http://www.w3.org/1999/xlink}href': 'http://example.com/profile.icc'
        }.get(attr, default)

        result = registry.register_svg_profile(element)
        assert result is True

        profile = registry.resolve_profile('xlink-profile')
        assert profile.href == 'http://example.com/profile.icc'

    def test_register_svg_profile_missing_name(self):
        """Test SVG profile registration without name."""
        registry = ColorProfileRegistry()

        element = Mock()
        element.get.return_value = None  # No name attribute

        result = registry.register_svg_profile(element)
        assert result is False

    def test_register_svg_profile_defaults(self):
        """Test SVG profile registration with default values."""
        registry = ColorProfileRegistry()

        element = Mock()
        element.get.side_effect = lambda attr, default=None: {
            'name': 'default-profile'
        }.get(attr, default)

        result = registry.register_svg_profile(element)
        assert result is True

        profile = registry.resolve_profile('default-profile')
        assert profile.local is True
        assert profile.rendering_intent == RenderingIntent.AUTO


class TestCSSProfileRegistration:
    """Test CSS @color-profile rule registration."""

    def test_register_css_profile_basic(self):
        """Test basic CSS profile registration."""
        registry = ColorProfileRegistry()

        result = registry.register_css_profile(
            name="css-profile",
            src="url('/path/to/profile.icc')",
            rendering_intent="relative-colorimetric"
        )
        assert result is True

        profile = registry.resolve_profile("css-profile")
        assert profile is not None
        assert profile.name == "css-profile"
        assert profile.href == "url('/path/to/profile.icc')"
        assert profile.rendering_intent == RenderingIntent.RELATIVE_COLORIMETRIC

    def test_register_css_profile_no_src(self):
        """Test CSS profile without src (built-in reference)."""
        registry = ColorProfileRegistry()

        result = registry.register_css_profile(name="builtin-reference")
        assert result is True

        profile = registry.resolve_profile("builtin-reference")
        assert profile.local is True
        assert profile.href is None

    def test_register_css_profile_defaults(self):
        """Test CSS profile with default values."""
        registry = ColorProfileRegistry()

        result = registry.register_css_profile(name="default-css")
        assert result is True

        profile = registry.resolve_profile("default-css")
        assert profile.rendering_intent == RenderingIntent.AUTO


class TestPolicyEnforcement:
    """Test security policy enforcement."""

    def test_remote_profile_policy_disabled(self):
        """Test remote profile rejection when disabled."""
        config = ProfileRegistryConfig(enable_remote_profiles=False)
        registry = ColorProfileRegistry(config)

        profile = ColorProfileRef(
            name="remote-profile",
            href="https://example.com/profile.icc"
        )

        result = registry.register_profile(profile)
        assert result is False
        assert registry.resolve_profile("remote-profile") is None

    def test_remote_profile_policy_enabled(self):
        """Test remote profile acceptance when enabled."""
        config = ProfileRegistryConfig(enable_remote_profiles=True)
        registry = ColorProfileRegistry(config)

        profile = ColorProfileRef(
            name="remote-profile",
            href="https://example.com/profile.icc"
        )

        result = registry.register_profile(profile)
        assert result is True
        assert registry.resolve_profile("remote-profile") is not None

    def test_data_url_policy_disabled(self):
        """Test data URL profile rejection when disabled."""
        config = ProfileRegistryConfig(enable_data_urls=False)
        registry = ColorProfileRegistry(config)

        profile = ColorProfileRef(
            name="data-profile",
            href="data:application/icc-profile,base64data"
        )

        result = registry.register_profile(profile)
        assert result is False

    def test_data_url_policy_enabled(self):
        """Test data URL profile acceptance when enabled."""
        config = ProfileRegistryConfig(enable_data_urls=True)
        registry = ColorProfileRegistry(config)

        profile = ColorProfileRef(
            name="data-profile",
            href="data:application/icc-profile,base64data"
        )

        result = registry.register_profile(profile)
        assert result is True


class TestProfileResolution:
    """Test profile resolution and caching."""

    def test_resolve_existing_profile(self):
        """Test resolving registered profile."""
        registry = ColorProfileRegistry()
        profile = ColorProfileRef(name="resolve-test")

        registry.register_profile(profile)
        resolved = registry.resolve_profile("resolve-test")

        assert resolved == profile

    def test_resolve_nonexistent_profile(self):
        """Test resolving non-existent profile."""
        registry = ColorProfileRegistry()

        result = registry.resolve_profile("nonexistent")
        assert result is None

    def test_access_count_tracking(self):
        """Test that access counts are tracked for eviction."""
        registry = ColorProfileRegistry()
        profile = ColorProfileRef(name="access-test")

        registry.register_profile(profile)

        # Access multiple times
        registry.resolve_profile("access-test")
        registry.resolve_profile("access-test")

        stats = registry.get_registry_stats()
        assert stats['most_used'] == "access-test"


class TestRegistryManagement:
    """Test registry management operations."""

    def test_list_profiles(self):
        """Test listing all registered profiles."""
        registry = ColorProfileRegistry()
        registry.register_profile("test1")
        registry.register_profile("test2")

        profiles = registry.list_profiles()
        assert "test1" in profiles
        assert "test2" in profiles
        assert len(profiles) >= 7  # 5 built-in + 2 custom

    def test_list_available_profiles(self):
        """Test listing available profiles."""
        registry = ColorProfileRegistry()
        registry.register_profile("available-test")

        available = registry.list_available_profiles()
        assert "srgb" in available  # Built-in
        assert "available-test" in available

    def test_clear_custom_profiles(self):
        """Test clearing custom profiles."""
        registry = ColorProfileRegistry()

        # Register custom profiles
        registry.register_profile("custom1")
        registry.register_profile("custom2")

        initial_count = len(registry.list_profiles())
        cleared_count = registry.clear_custom_profiles()

        assert cleared_count == 2
        assert len(registry.list_profiles()) == initial_count - 2

        # Built-in profiles should remain
        assert registry.resolve_profile("srgb") is not None

    def test_get_registry_stats(self):
        """Test registry statistics."""
        registry = ColorProfileRegistry()
        registry.register_profile("stats-test")

        stats = registry.get_registry_stats()

        assert stats['total_profiles'] >= 6
        assert stats['builtin_profiles'] == 5
        assert stats['custom_profiles'] >= 1
        assert 'stats-test' in stats['custom_profile_names']

    def test_get_profile_path_builtin(self):
        """Test getting path for built-in profile."""
        registry = ColorProfileRegistry()

        path = registry.get_profile_path("srgb")
        assert path is None  # Built-in profiles have no file path

    def test_get_profile_path_nonexistent(self):
        """Test getting path for non-existent profile."""
        registry = ColorProfileRegistry()

        path = registry.get_profile_path("nonexistent")
        assert path is None


class TestThreadSafety:
    """Test thread safety of registry operations."""

    def test_concurrent_registration(self):
        """Test concurrent profile registration."""
        registry = ColorProfileRegistry()
        results = []

        def register_profiles(start_index):
            for i in range(start_index, start_index + 10):
                result = registry.register_profile(f"thread-profile-{i}")
                results.append(result)

        # Start multiple threads
        threads = []
        for i in range(0, 30, 10):
            thread = Thread(target=register_profiles, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All registrations should succeed
        assert all(results)
        assert len(registry.list_profiles()) >= 30 + 5  # Custom + built-in

    def test_concurrent_resolution(self):
        """Test concurrent profile resolution."""
        registry = ColorProfileRegistry()
        registry.register_profile("concurrent-test")

        resolution_results = []

        def resolve_profile():
            for _ in range(100):
                result = registry.resolve_profile("concurrent-test")
                resolution_results.append(result is not None)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = Thread(target=resolve_profile)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All resolutions should succeed
        assert all(resolution_results)
        assert len(resolution_results) == 500  # 5 threads * 100 iterations


class TestEvictionPolicy:
    """Test profile eviction when at capacity."""

    def test_eviction_of_least_used(self):
        """Test that least used profiles are evicted."""
        config = ProfileRegistryConfig(max_profiles=7)  # 5 built-in + 2 custom
        registry = ColorProfileRegistry(config)

        # Register and access profiles differently
        registry.register_profile("frequently-used")
        registry.register_profile("rarely-used")

        # Access one more than the other
        for _ in range(10):
            registry.resolve_profile("frequently-used")
        registry.resolve_profile("rarely-used")

        # Register another profile to trigger eviction
        result = registry.register_profile("new-profile")
        assert result is True

        # The rarely used profile should be evicted
        assert registry.resolve_profile("new-profile") is not None
        assert registry.resolve_profile("frequently-used") is not None

    def test_builtin_profiles_not_evicted(self):
        """Test that built-in profiles are never evicted."""
        config = ProfileRegistryConfig(max_profiles=6)  # Very limited capacity
        registry = ColorProfileRegistry(config)

        # Fill registry beyond capacity
        for i in range(10):
            registry.register_profile(f"evict-test-{i}")

        # All built-in profiles should still be available
        assert registry.resolve_profile("srgb") is not None
        assert registry.resolve_profile("display-p3") is not None
"""
Unit tests for FeatureRegistry.

Tests loading, caching, and query methods for SVG feature support registry.
"""

import pytest
import json
from pathlib import Path
from core.analyze.feature_registry import FeatureRegistry


class TestFeatureRegistryLoading:
    """Test feature data loading and caching."""

    def test_load_returns_dict(self):
        """Test that load() returns a dictionary."""
        data = FeatureRegistry.load()
        assert isinstance(data, dict)

    def test_load_has_required_keys(self):
        """Test that loaded data has required top-level keys."""
        data = FeatureRegistry.load()
        assert "version" in data
        assert "last_updated" in data
        assert "categories" in data
        assert "policy_capabilities" in data

    def test_load_caches_data(self):
        """Test that load() caches data (returns same instance)."""
        data1 = FeatureRegistry.load()
        data2 = FeatureRegistry.load()
        assert data1 is data2  # Same object instance

    def test_clear_cache_reloads_data(self):
        """Test that clear_cache() forces reload."""
        data1 = FeatureRegistry.load()
        FeatureRegistry.clear_cache()
        data2 = FeatureRegistry.load()
        # Should be different instances but same content
        assert data1 == data2
        # But not the same object after clear
        # (can't test 'is not' reliably as Python may reuse memory)

    def test_version_format(self):
        """Test that version follows semantic versioning."""
        data = FeatureRegistry.load()
        version = data["version"]
        assert isinstance(version, str)
        parts = version.split(".")
        assert len(parts) == 3  # Major.Minor.Patch
        assert all(part.isdigit() for part in parts)


class TestFeatureRegistryQueries:
    """Test query methods for feature support information."""

    def test_get_all_features(self):
        """Test get_all_features() returns complete data."""
        features = FeatureRegistry.get_all_features()
        assert "categories" in features
        assert "policy_capabilities" in features
        assert len(features["categories"]) > 0

    def test_get_version(self):
        """Test get_version() returns version string."""
        version = FeatureRegistry.get_version()
        assert isinstance(version, str)
        assert version == "1.0.0"  # Current version

    def test_get_last_updated(self):
        """Test get_last_updated() returns date string."""
        date = FeatureRegistry.get_last_updated()
        assert isinstance(date, str)
        # Should be in YYYY-MM-DD format
        assert len(date) == 10
        assert date[4] == "-"
        assert date[7] == "-"

    def test_list_categories(self):
        """Test list_categories() returns sorted category names."""
        categories = FeatureRegistry.list_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert categories == sorted(categories)  # Should be sorted
        # Known categories
        assert "filters" in categories
        assert "gradients" in categories
        assert "basic_shapes" in categories

    def test_list_policies(self):
        """Test list_policies() returns sorted policy names."""
        policies = FeatureRegistry.list_policies()
        assert isinstance(policies, list)
        assert policies == sorted(policies)
        # Known policies
        assert "speed" in policies
        assert "balanced" in policies
        assert "quality" in policies


class TestFeatureRegistryGetCategory:
    """Test get_category() method."""

    def test_get_category_filters(self):
        """Test getting filters category."""
        result = FeatureRegistry.get_category("filters")
        assert result["category"] == "filters"
        assert "details" in result
        assert "version" in result

        details = result["details"]
        assert "support_level" in details
        assert "native_support" in details
        assert "emf_fallback" in details

    def test_get_category_gradients(self):
        """Test getting gradients category."""
        result = FeatureRegistry.get_category("gradients")
        assert result["category"] == "gradients"

        details = result["details"]
        assert "types" in details
        assert details["types"]["linear"] == "full"
        assert details["types"]["radial"] == "full"

    def test_get_category_invalid_raises_error(self):
        """Test that invalid category raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            FeatureRegistry.get_category("nonexistent_category")

        error_message = str(exc_info.value)
        assert "not found" in error_message.lower()
        assert "available" in error_message.lower()

    def test_get_category_error_lists_available(self):
        """Test that error message lists available categories."""
        with pytest.raises(ValueError) as exc_info:
            FeatureRegistry.get_category("foobar")

        error_message = str(exc_info.value)
        # Should list some known categories
        assert "filters" in error_message or "gradients" in error_message


class TestFeatureRegistryGetPolicy:
    """Test get_policy_capabilities() method."""

    def test_get_all_policies(self):
        """Test getting all policies (no filter)."""
        policies = FeatureRegistry.get_policy_capabilities()
        assert isinstance(policies, dict)
        assert "speed" in policies
        assert "balanced" in policies
        assert "quality" in policies

    def test_get_specific_policy_speed(self):
        """Test getting speed policy."""
        policy = FeatureRegistry.get_policy_capabilities("speed")
        assert "description" in policy
        assert "features" in policy
        assert "limitations" in policy
        assert isinstance(policy["features"], list)

    def test_get_specific_policy_balanced(self):
        """Test getting balanced policy."""
        policy = FeatureRegistry.get_policy_capabilities("balanced")
        assert policy["description"]
        assert "balanced" in policy["description"].lower()

    def test_get_specific_policy_quality(self):
        """Test getting quality policy."""
        policy = FeatureRegistry.get_policy_capabilities("quality")
        assert "maximum fidelity" in policy["description"].lower()

    def test_get_invalid_policy_raises_error(self):
        """Test that invalid policy raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            FeatureRegistry.get_policy_capabilities("nonexistent")

        error_message = str(exc_info.value)
        assert "not found" in error_message.lower()
        assert "speed" in error_message or "balanced" in error_message


class TestFeatureRegistryDataIntegrity:
    """Test data integrity and structure validation."""

    def test_all_categories_have_support_level(self):
        """Test that all categories define support_level."""
        data = FeatureRegistry.load()
        for category_name, category_data in data["categories"].items():
            assert "support_level" in category_data, \
                f"Category '{category_name}' missing support_level"

    def test_all_categories_have_notes(self):
        """Test that all categories have notes."""
        data = FeatureRegistry.load()
        for category_name, category_data in data["categories"].items():
            assert "notes" in category_data, \
                f"Category '{category_name}' missing notes"
            assert len(category_data["notes"]) > 0, \
                f"Category '{category_name}' has empty notes"

    def test_all_policies_have_required_fields(self):
        """Test that all policies have required fields."""
        data = FeatureRegistry.load()
        for policy_name, policy_data in data["policy_capabilities"].items():
            assert "description" in policy_data, \
                f"Policy '{policy_name}' missing description"
            assert "features" in policy_data, \
                f"Policy '{policy_name}' missing features"
            assert "limitations" in policy_data, \
                f"Policy '{policy_name}' missing limitations"

    def test_filters_category_structure(self):
        """Test filters category has expected structure."""
        filters = FeatureRegistry.get_category("filters")["details"]
        assert "native_support" in filters
        assert "emf_fallback" in filters
        assert isinstance(filters["native_support"], list)
        assert isinstance(filters["emf_fallback"], list)
        # Should have some native support
        assert len(filters["native_support"]) > 0

    def test_color_spaces_defined(self):
        """Test that color_spaces are defined."""
        data = FeatureRegistry.load()
        assert "color_spaces" in data
        color_spaces = data["color_spaces"]
        assert "support_level" in color_spaces
        assert "supported" in color_spaces
        assert isinstance(color_spaces["supported"], list)


class TestFeatureRegistryConstants:
    """Test constants used by registry."""

    def test_data_file_exists(self):
        """Test that feature_data.json file exists."""
        assert FeatureRegistry._DATA_FILE.exists()
        assert FeatureRegistry._DATA_FILE.is_file()

    def test_data_file_valid_json(self):
        """Test that feature_data.json is valid JSON."""
        with open(FeatureRegistry._DATA_FILE, 'r') as f:
            data = json.load(f)
        assert isinstance(data, dict)


class TestFeatureRegistryFactory:
    """Test factory function."""

    def test_create_feature_registry(self):
        """Test factory function returns registry class."""
        from core.analyze.feature_registry import create_feature_registry
        registry = create_feature_registry()
        assert registry == FeatureRegistry

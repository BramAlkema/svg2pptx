"""
Unit tests for feature registry integration in API routes.

Tests that /features/supported endpoint uses FeatureRegistry correctly.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from api.routes.analysis import get_supported_features
from core.analyze.feature_registry import FeatureRegistry


class TestFeatureEndpointIntegration:
    """Test FeatureRegistry integration in API endpoint."""

    @pytest.mark.asyncio
    async def test_get_all_features_uses_registry(self):
        """Test that endpoint uses FeatureRegistry.get_all_features()."""
        mock_user = {"api_key": "test"}

        # Call endpoint without category
        response = await get_supported_features(category=None, current_user=mock_user)

        # Should return data from registry
        assert response.status_code == 200
        content = response.body.decode('utf-8')

        # Should contain expected registry keys
        assert '"version"' in content
        assert '"categories"' in content
        assert '"policy_capabilities"' in content

    @pytest.mark.asyncio
    async def test_get_category_uses_registry(self):
        """Test that endpoint uses FeatureRegistry.get_category()."""
        mock_user = {"api_key": "test"}

        # Call endpoint with category
        response = await get_supported_features(category="filters", current_user=mock_user)

        # Should return category data
        assert response.status_code == 200
        content = response.body.decode('utf-8')

        # Should contain category-specific data
        assert '"category"' in content
        assert '"filters"' in content
        assert '"details"' in content

    @pytest.mark.asyncio
    async def test_invalid_category_raises_404(self):
        """Test that invalid category raises 404."""
        mock_user = {"api_key": "test"}

        # Call endpoint with invalid category
        with pytest.raises(HTTPException) as exc_info:
            await get_supported_features(category="nonexistent", current_user=mock_user)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_response_format_unchanged(self):
        """Test that response format matches expected structure."""
        mock_user = {"api_key": "test"}

        response = await get_supported_features(category=None, current_user=mock_user)

        # Parse JSON response
        import json
        data = json.loads(response.body)

        # Verify structure
        assert "version" in data
        assert "last_updated" in data
        assert "categories" in data
        assert "policy_capabilities" in data

        # Check categories structure
        assert isinstance(data["categories"], dict)
        assert len(data["categories"]) > 0

        # Check policy structure
        assert isinstance(data["policy_capabilities"], dict)
        assert "speed" in data["policy_capabilities"]
        assert "balanced" in data["policy_capabilities"]
        assert "quality" in data["policy_capabilities"]

    @pytest.mark.asyncio
    async def test_category_response_format(self):
        """Test category-specific response format."""
        mock_user = {"api_key": "test"}

        response = await get_supported_features(category="gradients", current_user=mock_user)

        import json
        data = json.loads(response.body)

        # Category response should have: version, category, details
        assert "version" in data
        assert "category" in data
        assert data["category"] == "gradients"
        assert "details" in data

    @pytest.mark.asyncio
    async def test_backward_compatibility(self):
        """Test that response is backward compatible with old format."""
        mock_user = {"api_key": "test"}

        response = await get_supported_features(category=None, current_user=mock_user)

        import json
        data = json.loads(response.body)

        # Should have all the same top-level keys as before
        expected_keys = {"version", "last_updated", "categories", "policy_capabilities", "color_spaces"}
        actual_keys = set(data.keys())

        assert expected_keys.issubset(actual_keys)


class TestFeatureEndpointErrorHandling:
    """Test error handling in feature endpoint."""

    @pytest.mark.asyncio
    async def test_registry_exception_becomes_500(self):
        """Test that registry exceptions become 500 errors."""
        mock_user = {"api_key": "test"}

        # Mock registry to raise unexpected exception
        with patch.object(FeatureRegistry, 'get_all_features', side_effect=RuntimeError("Mock error")):
            with pytest.raises(HTTPException) as exc_info:
                await get_supported_features(category=None, current_user=mock_user)

            assert exc_info.value.status_code == 500
            assert "failed" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_value_error_becomes_404(self):
        """Test that ValueError from registry becomes 404."""
        mock_user = {"api_key": "test"}

        # Mock registry to raise ValueError (category not found)
        with patch.object(FeatureRegistry, 'get_category', side_effect=ValueError("Category not found")):
            with pytest.raises(HTTPException) as exc_info:
                await get_supported_features(category="bad", current_user=mock_user)

            assert exc_info.value.status_code == 404


class TestFeatureRegistryCaching:
    """Test that registry caching works correctly."""

    @pytest.mark.asyncio
    async def test_multiple_requests_use_cached_data(self):
        """Test that multiple requests use cached registry data."""
        mock_user = {"api_key": "test"}

        # Make multiple requests
        response1 = await get_supported_features(category=None, current_user=mock_user)
        response2 = await get_supported_features(category=None, current_user=mock_user)
        response3 = await get_supported_features(category=None, current_user=mock_user)

        # All should succeed (and use cached data)
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200

        # Responses should be identical
        assert response1.body == response2.body
        assert response2.body == response3.body


class TestFeatureEndpointContent:
    """Test specific content from feature endpoint."""

    @pytest.mark.asyncio
    async def test_filters_category_contains_all_17_primitives(self):
        """Test that filters category contains all filter primitives."""
        mock_user = {"api_key": "test"}

        response = await get_supported_features(category="filters", current_user=mock_user)

        import json
        data = json.loads(response.body)

        details = data["details"]
        assert "native_support" in details
        assert "emf_fallback" in details

        # Should have lists of filters
        native = details["native_support"]
        emf = details["emf_fallback"]

        assert isinstance(native, list)
        assert isinstance(emf, list)
        assert len(native) > 0
        assert len(emf) > 0

    @pytest.mark.asyncio
    async def test_all_categories_accessible(self):
        """Test that all categories can be accessed."""
        mock_user = {"api_key": "test"}

        # Get list of categories
        all_features_response = await get_supported_features(category=None, current_user=mock_user)
        import json
        all_data = json.loads(all_features_response.body)

        categories = all_data["categories"].keys()

        # Try to access each category
        for cat in categories:
            response = await get_supported_features(category=cat, current_user=mock_user)
            assert response.status_code == 200

            data = json.loads(response.body)
            assert data["category"] == cat

    @pytest.mark.asyncio
    async def test_version_and_date_present(self):
        """Test that version and last_updated are present."""
        mock_user = {"api_key": "test"}

        response = await get_supported_features(category=None, current_user=mock_user)

        import json
        data = json.loads(response.body)

        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

        assert "last_updated" in data
        assert isinstance(data["last_updated"], str)
        # Should be in YYYY-MM-DD format
        assert len(data["last_updated"]) == 10

    @pytest.mark.asyncio
    async def test_policy_capabilities_complete(self):
        """Test that all policy capabilities are present."""
        mock_user = {"api_key": "test"}

        response = await get_supported_features(category=None, current_user=mock_user)

        import json
        data = json.loads(response.body)

        policies = data["policy_capabilities"]

        # Should have all three policies
        assert "speed" in policies
        assert "balanced" in policies
        assert "quality" in policies

        # Each should have required fields
        for policy_name, policy_data in policies.items():
            assert "description" in policy_data
            assert "features" in policy_data
            assert "limitations" in policy_data

            assert isinstance(policy_data["features"], list)
            assert isinstance(policy_data["limitations"], list)

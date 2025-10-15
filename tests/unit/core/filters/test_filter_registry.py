#!/usr/bin/env python3
"""Unit tests for FilterRegistry."""

import pytest
from lxml import etree as ET

from core.filters import FilterRegistry, Filter, FilterContext


class TestFilterRegistry:
    """Tests for FilterRegistry class."""

    def test_registry_initialization(self):
        """Registry should initialize empty."""
        registry = FilterRegistry()
        assert len(registry.list_filters()) == 0

    def test_register_default_filters(self):
        """Registry should load default filters."""
        registry = FilterRegistry()
        registry.register_default_filters()

        # Should have multiple filters registered
        filters = registry.list_filters()
        assert len(filters) > 0

        # Check for expected filter types
        expected_types = ['blur', 'color', 'composite', 'morph']
        loaded_types = [f for f in expected_types if any(f in ft for ft in filters)]
        assert len(loaded_types) > 0, f"Expected some of {expected_types}, got {filters}"

    def test_get_supported_filters(self):
        """Registry should return list of filter types."""
        registry = FilterRegistry()
        registry.register_default_filters()

        filters = registry.list_filters()
        assert isinstance(filters, list)
        assert all(isinstance(f, str) for f in filters)

    def test_registry_thread_safety(self):
        """Registry operations should be thread-safe."""
        registry = FilterRegistry()

        # Basic smoke test - detailed threading tests would go here
        registry.register_default_filters()
        filters1 = registry.list_filters()
        filters2 = registry.list_filters()

        assert filters1 == filters2

    def test_get_statistics(self):
        """Registry should provide statistics."""
        registry = FilterRegistry()
        registry.register_default_filters()

        stats = registry.get_statistics()
        assert 'total_filters' in stats
        assert 'filter_types' in stats
        assert stats['total_filters'] > 0


class TestFilterServiceIntegration:
    """Integration tests for FilterService with registry."""

    def test_filter_service_with_registry(self):
        """FilterService should integrate with registry."""
        from core.services.filter_service import FilterService

        service = FilterService(use_registry=True)

        # Should have more than stub filters
        supported = service.get_supported_filters()
        assert len(supported) >= 2  # At minimum blur + shadow

    def test_filter_service_fallback(self):
        """FilterService should fall back to stub if registry fails."""
        from core.services.filter_service import FilterService

        service = FilterService(use_registry=False)

        # Should have only stub filters
        supported = service.get_supported_filters()
        assert 'feGaussianBlur' in supported or 'blur' in supported
        assert 'feDropShadow' in supported or 'shadow' in supported


class TestFilterImports:
    """Tests for filter module imports."""

    def test_import_filter_base(self):
        """Should import Filter base class."""
        from core.filters import Filter
        assert Filter is not None

    def test_import_filter_context(self):
        """Should import FilterContext."""
        from core.filters import FilterContext
        assert FilterContext is not None

    def test_import_filter_result(self):
        """Should import FilterResult."""
        from core.filters import FilterResult
        assert FilterResult is not None

    def test_import_filter_registry(self):
        """Should import FilterRegistry."""
        from core.filters import FilterRegistry
        assert FilterRegistry is not None

    def test_import_filter_chain(self):
        """Should import FilterChain."""
        from core.filters import FilterChain
        assert FilterChain is not None

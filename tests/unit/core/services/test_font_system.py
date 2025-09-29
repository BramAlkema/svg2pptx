#!/usr/bin/env python3
"""
Unit tests for FontSystem service.

Tests the comprehensive font handling including 3-tier strategy,
font metadata, and caching functionality.
"""

import pytest
from unittest.mock import Mock, patch
from core.services.font_system import FontSystem, FontSystemConfig, create_font_system
from core.ir.font_metadata import (
    FontMetadata, FontStrategy, FontAvailability,
    create_font_metadata, parse_font_weight
)


class TestFontSystem:
    """Test FontSystem core functionality."""

    def test_font_system_initialization(self):
        """Test FontSystem initializes correctly."""
        font_system = FontSystem()
        assert font_system is not None
        assert font_system._config is not None
        assert font_system._cache is not None

    def test_font_system_with_config(self):
        """Test FontSystem with custom configuration."""
        config = FontSystemConfig(
            prefer_embedding=False,
            enable_caching=False
        )
        font_system = FontSystem(config)
        assert font_system._config.prefer_embedding is False
        assert font_system._cache is None

    def test_create_font_system_factory(self):
        """Test font system factory function."""
        font_system = create_font_system()
        assert isinstance(font_system, FontSystem)

    def test_font_analysis_basic(self):
        """Test basic font analysis functionality."""
        font_system = FontSystem()

        # Create test font metadata
        font_metadata = create_font_metadata("Arial", "400", "normal", 12.0)

        # Analyze font
        result = font_system.analyze_font(font_metadata)

        # Validate result
        assert result is not None
        assert result.recommended_strategy in [
            FontStrategy.EMBEDDED, FontStrategy.SYSTEM,
            FontStrategy.PATH, FontStrategy.FALLBACK
        ]
        assert 0.0 <= result.confidence <= 1.0
        assert result.analysis_time_ms >= 0

    def test_font_analysis_caching(self):
        """Test font analysis caching."""
        font_system = FontSystem()
        font_metadata = create_font_metadata("Arial", "400", "normal", 12.0)

        # First analysis
        result1 = font_system.analyze_font(font_metadata)

        # Second analysis (should use cache)
        result2 = font_system.analyze_font(font_metadata)

        # Results should be identical (from cache)
        assert result1.recommended_strategy == result2.recommended_strategy
        assert result1.confidence == result2.confidence

    def test_css_font_weight_parsing(self):
        """Test CSS font weight parsing."""
        assert FontSystem.parse_css_font_weight("normal") == 400
        assert FontSystem.parse_css_font_weight("bold") == 700
        assert FontSystem.parse_css_font_weight("600") == 600
        assert FontSystem.parse_css_font_weight("thin") == 100
        assert FontSystem.parse_css_font_weight("black") == 900
        assert FontSystem.parse_css_font_weight("invalid") == 400

    def test_css_font_style_normalization(self):
        """Test CSS font style normalization."""
        assert FontSystem.normalize_css_font_style("normal") == "normal"
        assert FontSystem.normalize_css_font_style("italic") == "italic"
        assert FontSystem.normalize_css_font_style("oblique") == "italic"
        assert FontSystem.normalize_css_font_style("inherit") == "normal"
        assert FontSystem.normalize_css_font_style("invalid") == "normal"

    def test_register_embedded_font(self):
        """Test embedded font registration."""
        font_system = FontSystem()
        font_system.register_embedded_font("Custom Font")

        # Font should now be in embedded set
        assert "Custom Font" in font_system._embedded_fonts

    def test_cache_management(self):
        """Test cache management functionality."""
        font_system = FontSystem()

        # Check initial cache stats
        stats = font_system.get_cache_stats()
        assert stats["caching_enabled"] is True
        assert stats["cache_size"] == 0

        # Add some cached results
        font_metadata = create_font_metadata("Test Font", "400", "normal", 12.0)
        font_system.analyze_font(font_metadata)

        # Check cache size increased
        stats_after = font_system.get_cache_stats()
        assert stats_after["cache_size"] == 1

        # Clear cache
        font_system.clear_cache()
        stats_cleared = font_system.get_cache_stats()
        assert stats_cleared["cache_size"] == 0


class TestFontSystemConfig:
    """Test FontSystemConfig."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = FontSystemConfig()
        assert config.prefer_embedding is True
        assert config.enable_caching is True
        assert config.enable_path_conversion is True
        assert config.default_fallback_chain == ['Arial', 'Helvetica', 'sans-serif']

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = FontSystemConfig(
            prefer_embedding=False,
            embedding_size_limit_mb=5.0,
            confidence_threshold=0.9
        )
        assert config.prefer_embedding is False
        assert config.embedding_size_limit_mb == 5.0
        assert config.confidence_threshold == 0.9


class TestFontAnalysisIntegration:
    """Test font analysis integration scenarios."""

    def test_3_tier_strategy_embedded(self):
        """Test 3-tier strategy preferring embedded fonts."""
        config = FontSystemConfig(prefer_embedding=True)
        font_system = FontSystem(config)

        font_metadata = create_font_metadata("Arial", "400", "normal", 12.0)
        result = font_system.analyze_font(font_metadata)

        # Should prefer embedded or system strategy
        assert result.recommended_strategy in [FontStrategy.EMBEDDED, FontStrategy.SYSTEM]

    def test_3_tier_strategy_system_only(self):
        """Test 3-tier strategy with embedding disabled."""
        config = FontSystemConfig(prefer_embedding=False)
        font_system = FontSystem(config)

        font_metadata = create_font_metadata("Arial", "400", "normal", 12.0)
        result = font_system.analyze_font(font_metadata)

        # Should use system, path, or fallback strategy
        assert result.recommended_strategy in [
            FontStrategy.SYSTEM, FontStrategy.PATH, FontStrategy.FALLBACK
        ]

    def test_font_analysis_error_handling(self):
        """Test font analysis with simulated errors."""
        font_system = FontSystem()

        # Create invalid font metadata that might cause errors
        with patch.object(font_system, '_determine_font_strategy', side_effect=Exception("Test error")):
            font_metadata = create_font_metadata("Invalid Font", "400", "normal", 12.0)
            result = font_system.analyze_font(font_metadata)

            # Should fall back to FALLBACK strategy
            assert result.recommended_strategy == FontStrategy.FALLBACK
            assert result.confidence == 0.0
            assert "Analysis failed" in result.notes[0]


class TestFontSystemPerformance:
    """Test FontSystem performance characteristics."""

    def test_analysis_performance(self):
        """Test font analysis performance."""
        font_system = FontSystem()
        font_metadata = create_font_metadata("Arial", "400", "normal", 12.0)

        result = font_system.analyze_font(font_metadata)

        # Analysis should complete quickly
        assert result.analysis_time_ms < 1000  # Less than 1 second

    def test_cache_performance(self):
        """Test caching improves performance."""
        font_system = FontSystem()
        font_metadata = create_font_metadata("Arial", "400", "normal", 12.0)

        # First analysis (no cache)
        result1 = font_system.analyze_font(font_metadata)
        time1 = result1.analysis_time_ms

        # Second analysis (cached)
        result2 = font_system.analyze_font(font_metadata)
        time2 = result2.analysis_time_ms

        # Cached analysis should be faster or equal
        assert time2 <= time1


if __name__ == "__main__":
    pytest.main([__file__])
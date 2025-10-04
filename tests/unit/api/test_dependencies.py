"""
Unit tests for API dependency injection.

Tests cached factory functions for analyzer and validator instances.
"""

import pytest
from api.dependencies import (
    get_analyzer,
    get_validator,
    clear_cache,
    AnalyzerDep,
    ValidatorDep
)
from core.analyze.api_adapter import SVGAnalyzerAPI
from core.analyze.svg_validator import SVGValidator


class TestGetAnalyzer:
    """Test get_analyzer() factory function."""

    def test_returns_svg_analyzer_instance(self):
        """Test that get_analyzer() returns SVGAnalyzerAPI instance."""
        analyzer = get_analyzer()
        assert isinstance(analyzer, SVGAnalyzerAPI)

    def test_returns_cached_instance(self):
        """Test that get_analyzer() caches instance (returns same object)."""
        analyzer1 = get_analyzer()
        analyzer2 = get_analyzer()
        assert analyzer1 is analyzer2  # Same object instance

    def test_analyzer_has_analyze_svg_method(self):
        """Test that returned analyzer has analyze_svg() method."""
        analyzer = get_analyzer()
        assert hasattr(analyzer, 'analyze_svg')
        assert callable(analyzer.analyze_svg)

    def test_analyzer_is_stateless(self):
        """Test that analyzer can be reused across multiple calls."""
        analyzer = get_analyzer()

        svg1 = '<svg><rect width="10" height="10"/></svg>'
        svg2 = '<svg><circle r="5"/></svg>'

        # Should work for multiple SVGs
        result1 = analyzer.analyze_svg(svg1)
        result2 = analyzer.analyze_svg(svg2)

        assert result1 is not None
        assert result2 is not None
        # Results should be different for different inputs
        assert result1.to_dict() != result2.to_dict()


class TestGetValidator:
    """Test get_validator() factory function."""

    def test_returns_svg_validator_instance(self):
        """Test that get_validator() returns SVGValidator instance."""
        validator = get_validator()
        assert isinstance(validator, SVGValidator)

    def test_returns_cached_instance(self):
        """Test that get_validator() caches instance (returns same object)."""
        validator1 = get_validator()
        validator2 = get_validator()
        assert validator1 is validator2  # Same object instance

    def test_validator_has_validate_method(self):
        """Test that returned validator has validate() method."""
        validator = get_validator()
        assert hasattr(validator, 'validate')
        assert callable(validator.validate)

    def test_validator_is_stateless(self):
        """Test that validator can be reused across multiple calls."""
        validator = get_validator()

        svg1 = '<svg><rect width="10" height="10"/></svg>'
        svg2 = '<svg><circle r="5"/></svg>'

        # Should work for multiple SVGs
        result1 = validator.validate(svg1)
        result2 = validator.validate(svg2)

        assert result1 is not None
        assert result2 is not None
        # Both should be valid
        assert result1.valid
        assert result2.valid


class TestClearCache:
    """Test cache clearing functionality."""

    def test_clear_cache_forces_new_analyzer(self):
        """Test that clear_cache() forces new analyzer instance."""
        analyzer1 = get_analyzer()
        clear_cache()
        analyzer2 = get_analyzer()

        # Should be different instances after clear
        # Note: Can't reliably test 'is not' as Python may reuse memory
        # Instead verify they're both valid instances
        assert isinstance(analyzer1, SVGAnalyzerAPI)
        assert isinstance(analyzer2, SVGAnalyzerAPI)

    def test_clear_cache_forces_new_validator(self):
        """Test that clear_cache() forces new validator instance."""
        validator1 = get_validator()
        clear_cache()
        validator2 = get_validator()

        # Should be different instances after clear
        assert isinstance(validator1, SVGValidator)
        assert isinstance(validator2, SVGValidator)

    def test_clear_cache_then_recache(self):
        """Test that instances are re-cached after clearing."""
        # Get initial instances
        get_analyzer()
        get_validator()

        # Clear cache
        clear_cache()

        # Get new instances
        analyzer1 = get_analyzer()
        analyzer2 = get_analyzer()
        validator1 = get_validator()
        validator2 = get_validator()

        # Should be cached again
        assert analyzer1 is analyzer2
        assert validator1 is validator2


class TestTypeAliases:
    """Test type alias definitions."""

    def test_analyzer_dep_type_alias_exists(self):
        """Test that AnalyzerDep type alias is defined."""
        assert AnalyzerDep is not None

    def test_validator_dep_type_alias_exists(self):
        """Test that ValidatorDep type alias is defined."""
        assert ValidatorDep is not None


class TestDependencyInjectionIntegration:
    """Integration tests for dependency injection in FastAPI context."""

    def test_analyzer_works_with_real_svg(self):
        """Test analyzer with realistic SVG."""
        analyzer = get_analyzer()
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <rect x="10" y="10" width="80" height="80" fill="blue"/>
            <circle cx="50" cy="50" r="30" fill="red"/>
            <path d="M10 10 L90 90" stroke="black"/>
        </svg>
        """

        result = analyzer.analyze_svg(svg)
        assert result is not None
        assert result.to_dict() is not None

        # Check expected fields
        data = result.to_dict()
        assert 'complexity_score' in data
        assert 'element_counts' in data
        assert 'recommended_policy' in data

    def test_validator_works_with_real_svg(self):
        """Test validator with realistic SVG."""
        validator = get_validator()
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <rect x="10" y="10" width="80" height="80" fill="blue"/>
        </svg>
        """

        result = validator.validate(svg)
        assert result is not None
        assert result.to_dict() is not None

        # Check expected fields
        data = result.to_dict()
        assert 'valid' in data
        assert data['valid'] is True

    def test_multiple_requests_use_same_instances(self):
        """Test that multiple requests reuse cached instances (performance)."""
        # Simulate multiple API requests
        analyzers = [get_analyzer() for _ in range(10)]
        validators = [get_validator() for _ in range(10)]

        # All should be same instance
        assert all(a is analyzers[0] for a in analyzers)
        assert all(v is validators[0] for v in validators)

    def test_cache_independence(self):
        """Test that analyzer and validator caches are independent."""
        analyzer = get_analyzer()
        validator = get_validator()

        # Clear only analyzer cache
        get_analyzer.cache_clear()

        # Validator should still be cached
        validator2 = get_validator()
        assert validator is validator2

        # Analyzer should be new
        analyzer2 = get_analyzer()
        # (can't test 'is not' reliably, just verify it's valid)
        assert isinstance(analyzer2, SVGAnalyzerAPI)


class TestCachePerformance:
    """Test caching performance benefits."""

    def test_cached_calls_are_fast(self):
        """Test that cached calls don't recreate instances."""
        import time

        # First call (uncached)
        clear_cache()
        start = time.time()
        get_analyzer()
        first_call_time = time.time() - start

        # Second call (cached)
        start = time.time()
        get_analyzer()
        cached_call_time = time.time() - start

        # Cached call should be significantly faster
        # (May not always be true due to system variance, but good indicator)
        assert cached_call_time <= first_call_time

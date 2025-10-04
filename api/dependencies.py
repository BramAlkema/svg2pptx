"""
API Dependency Injection.

Provides cached factory functions for creating and reusing analyzer and validator instances.
Uses FastAPI dependency injection and functools.lru_cache for optimal performance.
"""

from functools import lru_cache
from typing import Annotated
from fastapi import Depends

from core.analyze import create_api_analyzer
from core.analyze.api_adapter import SVGAnalyzerAPI
from core.analyze.svg_validator import create_svg_validator, SVGValidator


@lru_cache(maxsize=1)
def get_analyzer() -> SVGAnalyzerAPI:
    """
    Get cached SVG analyzer instance.

    Creates analyzer on first call, returns cached instance on subsequent calls.
    Analyzer is stateless and safe to reuse across requests.

    Returns:
        SVGAnalyzerAPI: Cached analyzer instance

    Example:
        >>> @router.post("/analyze")
        >>> async def analyze_svg(analyzer: Annotated[SVGAnalyzer, Depends(get_analyzer)]):
        >>>     result = analyzer.analyze_svg(svg_content)
    """
    return create_api_analyzer()


@lru_cache(maxsize=1)
def get_validator() -> SVGValidator:
    """
    Get cached SVG validator instance.

    Creates validator on first call, returns cached instance on subsequent calls.
    Validator is stateless and safe to reuse across requests.

    Returns:
        SVGValidator: Cached validator instance

    Example:
        >>> @router.post("/validate")
        >>> async def validate_svg(validator: Annotated[SVGValidator, Depends(get_validator)]):
        >>>     result = validator.validate(svg_content)
    """
    return create_svg_validator()


# Type aliases for cleaner endpoint signatures
AnalyzerDep = Annotated[SVGAnalyzerAPI, Depends(get_analyzer)]
ValidatorDep = Annotated[SVGValidator, Depends(get_validator)]


def clear_cache():
    """
    Clear dependency cache.

    Use for testing or when forcing fresh instances is required.
    In production, instances should remain cached for performance.

    Example:
        >>> # In test teardown
        >>> clear_cache()
    """
    get_analyzer.cache_clear()
    get_validator.cache_clear()

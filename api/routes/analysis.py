"""
SVG Analysis and Validation API Routes

Provides endpoints for analyzing SVG complexity, validating SVG files,
and querying supported features.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
import logging

from ..auth import get_current_user
from ..utils.svg_helpers import extract_svg_content
from ..dependencies import AnalyzerDep, ValidatorDep
from core.analyze import SVGAnalysisResult
from core.analyze.feature_registry import FeatureRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["analysis"])


# Request/Response Models
class AnalyzeRequest(BaseModel):
    """Request model for SVG analysis."""
    svg_content: Optional[str] = Field(None, description="SVG XML content")
    svg_url: Optional[str] = Field(None, description="URL to SVG file (alternative to content)")
    analyze_depth: Literal["basic", "detailed", "comprehensive"] = Field(
        "detailed",
        description="Analysis depth: basic, detailed, comprehensive"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "svg_content": "<svg>...</svg>",
                "analyze_depth": "detailed"
            }
        }


class ValidateRequest(BaseModel):
    """Request model for SVG validation."""
    svg_content: Optional[str] = Field(None, description="SVG XML content")
    strict_mode: bool = Field(False, description="Enable strict validation (warnings become errors)")

    class Config:
        json_schema_extra = {
            "example": {
                "svg_content": "<svg viewBox='0 0 100 100'>...</svg>",
                "strict_mode": False
            }
        }


@router.post("/svg")
async def analyze_svg(
    request: Optional[AnalyzeRequest] = None,
    svg_file: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    analyzer: AnalyzerDep = None
) -> JSONResponse:
    """
    Analyze SVG complexity and get policy recommendations.

    Accepts SVG via:
    - JSON body with `svg_content` field
    - File upload
    - URL (future enhancement)

    Returns complexity score, element counts, detected features,
    recommended policy, and performance estimates.

    Args:
        request: Analysis request with SVG content or URL
        svg_file: Optional file upload
        current_user: Authenticated user
        analyzer: Injected SVG analyzer (cached)

    Returns:
        JSON response with analysis results
    """
    try:
        # Extract SVG content using shared helper
        svg_content = await extract_svg_content(request, svg_file, max_size_mb=10)

        logger.info(f"Analyzing SVG for user {current_user.get('api_key', 'unknown')} ({len(svg_content)} bytes)")

        # Run analysis using injected analyzer
        result = analyzer.analyze_svg(svg_content)

        # Convert to dict for JSON response
        response_data = result.to_dict()

        return JSONResponse(
            content=response_data,
            status_code=200
        )

    except ValueError as e:
        # Invalid SVG XML
        logger.warning(f"Invalid SVG provided: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid SVG: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SVG analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/validate")
async def validate_svg(
    request: Optional[ValidateRequest] = None,
    svg_file: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    validator: ValidatorDep = None
) -> JSONResponse:
    """
    Validate SVG content and check compatibility.

    Performs comprehensive validation including:
    - XML well-formedness
    - SVG semantic validation
    - Attribute validation
    - Feature compatibility checking
    - PowerPoint/Google Slides compatibility

    Accepts SVG via:
    - JSON body with `svg_content` field
    - File upload

    Args:
        request: Validation request with SVG content and strict mode flag
        svg_file: Optional file upload
        current_user: Authenticated user
        validator: Injected SVG validator (cached)

    Returns:
        JSON response with validation results, errors, warnings, and compatibility report
    """
    try:
        # Extract SVG content using shared helper
        svg_content = await extract_svg_content(request, svg_file, max_size_mb=10)

        # Get strict_mode from request (default False for file uploads)
        strict_mode = request.strict_mode if request and hasattr(request, 'strict_mode') else False

        logger.info(f"Validating SVG for user {current_user.get('api_key', 'unknown')} ({len(svg_content)} bytes, strict={strict_mode})")

        # Run validation using injected validator
        result = validator.validate(svg_content, strict_mode=strict_mode)

        # Convert to dict for JSON response
        response_data = result.to_dict()

        # Determine HTTP status code based on validation result
        # 200 if valid, 400 if invalid (has errors)
        status_code = 200 if result.valid else 400

        return JSONResponse(
            content=response_data,
            status_code=status_code
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SVG validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )


@router.get("/features/supported")
async def get_supported_features(
    category: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> JSONResponse:
    """
    Get supported SVG features and capabilities.

    Returns comprehensive documentation of supported SVG elements,
    attributes, and conversion capabilities.

    Args:
        category: Optional filter by category (shapes, paths, text, gradients, filters)
        current_user: Authenticated user

    Returns:
        JSON response with feature support matrix
    """
    try:
        # Use FeatureRegistry instead of hardcoded matrix
        if category:
            # Get specific category
            features = FeatureRegistry.get_category(category)
        else:
            # Get all features
            features = FeatureRegistry.get_all_features()

        return JSONResponse(content=features, status_code=200)

    except ValueError as e:
        # Category not found
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve feature support: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve feature support information"
        )

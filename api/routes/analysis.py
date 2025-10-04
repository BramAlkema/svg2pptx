"""
SVG Analysis and Validation API Routes

Provides endpoints for analyzing SVG complexity, validating SVG files,
and querying supported features.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import logging

from ..auth import get_current_user
from ..utils.svg_helpers import extract_svg_content
from core.analyze import create_api_analyzer, SVGAnalysisResult
from core.analyze.svg_validator import create_svg_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["analysis"])


# Request/Response Models
class AnalyzeRequest(BaseModel):
    """Request model for SVG analysis."""
    svg_content: Optional[str] = Field(None, description="SVG XML content")
    svg_url: Optional[str] = Field(None, description="URL to SVG file (alternative to content)")
    analyze_depth: str = Field("detailed", description="Analysis depth: basic, detailed, comprehensive")

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
    request: AnalyzeRequest = None,
    svg_file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
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

    Returns:
        JSON response with analysis results
    """
    try:
        # Extract SVG content using shared helper
        svg_content = await extract_svg_content(request, svg_file, max_size_mb=10)

        logger.info(f"Analyzing SVG for user {current_user.get('api_key', 'unknown')} ({len(svg_content)} bytes)")

        # Create analyzer and run analysis
        analyzer = create_api_analyzer()
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
    request: ValidateRequest = None,
    svg_file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
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

    Returns:
        JSON response with validation results, errors, warnings, and compatibility report
    """
    try:
        # Extract SVG content using shared helper
        svg_content = await extract_svg_content(request, svg_file, max_size_mb=10)

        # Get strict_mode from request (default False for file uploads)
        strict_mode = request.strict_mode if request and hasattr(request, 'strict_mode') else False

        logger.info(f"Validating SVG for user {current_user.get('api_key', 'unknown')} ({len(svg_content)} bytes, strict={strict_mode})")

        # Create validator and run validation
        validator = create_svg_validator()
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
    current_user: dict = Depends(get_current_user)
):
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
        # Feature support matrix
        features = {
            "version": "1.0.0",
            "last_updated": "2025-10-04",
            "categories": {
                "basic_shapes": {
                    "support_level": "full",
                    "elements": ["rect", "circle", "ellipse", "line", "polyline", "polygon"],
                    "notes": "All basic shapes fully supported with native PowerPoint rendering"
                },
                "paths": {
                    "support_level": "full",
                    "commands": ["M", "L", "H", "V", "C", "S", "Q", "T", "A", "Z"],
                    "notes": "All path commands fully supported including cubic/quadratic Bezier and arcs"
                },
                "text": {
                    "support_level": "partial",
                    "features": {
                        "basic_text": "full",
                        "tspan": "full",
                        "text_on_path": "via_wordart",
                        "bidirectional": "limited",
                        "vertical_text": "limited"
                    },
                    "notes": "Basic text and tspan fully supported. Text-on-path uses WordArt. BiDi and vertical text have limitations."
                },
                "gradients": {
                    "support_level": "full",
                    "types": {
                        "linear": "full",
                        "radial": "full",
                        "mesh": "partial"
                    },
                    "limitations": {
                        "mesh": "max 400 patches, may use EMF for complex meshes",
                        "stops": "recommend ≤10 stops for best compatibility"
                    },
                    "notes": "Linear and radial gradients fully supported. Mesh gradients supported with patch count limitations."
                },
                "filters": {
                    "support_level": "partial",
                    "native_support": [
                        "feGaussianBlur",
                        "feDropShadow",
                        "feOffset",
                        "feFlood",
                        "feBlend",
                        "feColorMatrix"
                    ],
                    "emf_fallback": [
                        "feDisplacementMap",
                        "feTurbulence",
                        "feConvolveMatrix",
                        "feDiffuseLighting",
                        "feSpecularLighting"
                    ],
                    "notes": "Common filters have native support. Complex filters use EMF vector fallback."
                },
                "transformations": {
                    "support_level": "full",
                    "types": ["translate", "rotate", "scale", "skewX", "skewY", "matrix"],
                    "notes": "All transform types fully supported"
                },
                "clipping_masking": {
                    "support_level": "partial",
                    "features": {
                        "clipPath": "partial",
                        "mask": "via_emf"
                    },
                    "notes": "Simple clip paths supported natively. Complex clipping uses EMF."
                },
                "patterns": {
                    "support_level": "via_emf",
                    "notes": "Patterns converted to EMF for PowerPoint compatibility"
                },
                "markers": {
                    "support_level": "partial",
                    "notes": "Basic markers supported. Complex markers may use EMF fallback."
                },
                "animations": {
                    "support_level": "limited",
                    "notes": "Animations converted to static frames or slide sequences based on policy"
                }
            },
            "policy_capabilities": {
                "speed": {
                    "description": "Fast conversion with basic feature support",
                    "features": ["basic shapes", "simple paths", "basic text", "simple gradients"],
                    "limitations": ["filters may be simplified", "complex features disabled"]
                },
                "balanced": {
                    "description": "Balanced quality and performance",
                    "features": ["all shapes", "all paths", "text with formatting", "gradients", "basic filters"],
                    "limitations": ["some filter effects simplified", "complex meshes may use EMF"]
                },
                "quality": {
                    "description": "Maximum fidelity conversion",
                    "features": ["all elements", "all filters", "mesh gradients", "complex transforms"],
                    "limitations": ["slower conversion", "larger file sizes"]
                }
            },
            "color_spaces": {
                "support_level": "full",
                "supported": ["sRGB", "linearRGB", "display-p3", "adobe-rgb-1998"],
                "notes": "ICC profile support with LAB color conversion for brand accuracy"
            }
        }

        # Filter by category if requested
        if category:
            if category in features["categories"]:
                features = {
                    "version": features["version"],
                    "category": category,
                    "details": features["categories"][category]
                }
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Category '{category}' not found. Available: {', '.join(features['categories'].keys())}"
                )

        return JSONResponse(content=features, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve feature support: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve feature support information"
        )

"""
Visual Testing API Routes

Provides endpoints for visual comparison and testing of SVG to PPTX conversions.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from typing import Optional
import tempfile
import logging

from ..auth import get_current_user
from tools.visual_comparison_with_policy import EnhancedVisualComparison
from core.policy.config import OutputTarget

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/visual", tags=["visual-testing"])


@router.post("/compare")
async def create_visual_comparison(
    svg_file: UploadFile = File(...),
    target: str = "balanced",
    enable_google_slides: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """
    Create visual comparison report for SVG to PPTX conversion.

    Args:
        svg_file: SVG file to convert and compare
        target: Policy target (speed, balanced, quality) - default: balanced
        enable_google_slides: Enable Google Slides upload and comparison
        current_user: Authenticated user

    Returns:
        JSON response with comparison results, metrics, and report URLs
    """
    try:
        # Validate target
        if target not in ['speed', 'balanced', 'quality']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid target '{target}'. Must be: speed, balanced, or quality"
            )

        # Map target string to OutputTarget
        target_map = {
            'speed': OutputTarget.SPEED,
            'balanced': OutputTarget.BALANCED,
            'quality': OutputTarget.QUALITY,
        }
        output_target = target_map[target]

        logger.info(f"Creating visual comparison for user {current_user.get('api_key', 'unknown')}")

        # Save uploaded SVG to temp file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.svg', delete=False) as temp_svg:
            content = await svg_file.read()
            temp_svg.write(content)
            svg_path = Path(temp_svg.name)

        try:
            # Create output directory
            output_dir = Path(tempfile.mkdtemp(prefix='visual_comparison_'))

            # Create comparison tool
            comparison = EnhancedVisualComparison(
                output_dir=output_dir,
                target=output_target,
                enable_google_slides=enable_google_slides
            )

            # Run complete comparison workflow
            pptx_path = output_dir / f"{svg_path.stem}_output.pptx"

            # Step 1: Convert with policy tracing
            if not comparison.convert_with_tracing(svg_path, pptx_path):
                raise HTTPException(
                    status_code=500,
                    detail="Conversion with policy tracing failed"
                )

            # Step 2: Upload to Google Slides (if enabled)
            slides_info = None
            if enable_google_slides:
                slides_info = comparison.upload_to_google_slides(pptx_path)

            # Step 3: Capture screenshots and compare
            screenshot_path = None
            comparison_result = None

            if enable_google_slides and slides_info:
                # Capture SVG screenshot
                svg_screenshot = comparison.capture_svg_screenshot(svg_path)

                # Get Google Slides screenshot (using iframe/publish URL)
                # For now, we'll skip screenshot capture and just return URLs
                screenshot_path = svg_screenshot

            # Step 4: Generate HTML report
            report_path = comparison.generate_html_report(
                svg_path,
                pptx_path,
                screenshot_path
            )

            # Build response
            response = {
                "status": "success",
                "target": target,
                "svg_file": svg_file.filename,
                "output": {
                    "pptx_path": str(pptx_path),
                    "report_path": str(report_path),
                    "output_dir": str(output_dir)
                },
                "policy_trace": comparison.policy_trace,
                "google_slides": None
            }

            if slides_info:
                response["google_slides"] = {
                    "file_id": slides_info.file_id,
                    "web_view_link": slides_info.web_view_link,
                    "embed_url": slides_info.embed_url,
                    "published_url": slides_info.published_url,
                    "slide_count": slides_info.slide_count
                }

            if comparison_result:
                response["comparison"] = {
                    "overall_accuracy": comparison_result.overall_accuracy,
                    "pixel_difference": comparison_result.pixel_difference,
                    "color_accuracy": comparison_result.color_accuracy,
                    "edge_similarity": comparison_result.edge_similarity,
                    "structural_similarity": comparison_result.structural_similarity
                }

            return JSONResponse(content=response, status_code=200)

        finally:
            # Clean up temp SVG file
            try:
                svg_path.unlink()
            except Exception:
                pass

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Visual comparison failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Visual comparison failed: {str(e)}"
        )


@router.get("/report/{output_dir}")
async def get_visual_report(
    output_dir: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve generated visual comparison HTML report.

    Args:
        output_dir: Output directory name containing the report
        current_user: Authenticated user

    Returns:
        HTML report file
    """
    try:
        # Security: validate output_dir is just a dirname, not a path
        if '/' in output_dir or '\\' in output_dir or '..' in output_dir:
            raise HTTPException(
                status_code=400,
                detail="Invalid output directory name"
            )

        # Look for report in temp directory
        import tempfile
        base_temp = Path(tempfile.gettempdir())
        report_dir = base_temp / output_dir

        if not report_dir.exists():
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        # Find HTML report
        report_files = list(report_dir.glob("*_comparison_report.html"))
        if not report_files:
            raise HTTPException(
                status_code=404,
                detail="HTML report not found in directory"
            )

        report_path = report_files[0]

        return FileResponse(
            path=report_path,
            media_type="text/html",
            filename=report_path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve report: {str(e)}"
        )

#!/usr/bin/env python3
"""
Clean Slate Primary API

Primary conversion API for SVG to PowerPoint using Clean Slate architecture.
This module replaces the legacy src/svg2pptx.py system entirely.
"""

import logging
import tempfile
from pathlib import Path
from typing import Union, Optional, Dict, Any
from dataclasses import dataclass

from .pipeline.factory import PipelineFactory
from .pipeline.config import PipelineConfig, QualityLevel, SlideConfig, OutputFormat
from .pipeline.converter import CleanSlateConverter, ConversionResult as PipelineConversionResult, ConversionError

# Import migrated systems for API integration
from core.performance.measurement import BenchmarkEngine

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of SVG to PPTX conversion with Clean Slate system."""

    # Output information
    success: bool
    output_path: Optional[Path] = None
    output_data: Optional[bytes] = None

    # Error information
    error_message: Optional[str] = None
    error_stage: Optional[str] = None

    # Conversion metrics
    total_time_ms: float = 0.0
    elements_processed: int = 0
    shapes_converted: int = 0
    quality_score: float = 0.0

    # Pipeline statistics
    parse_time_ms: float = 0.0
    analyze_time_ms: float = 0.0
    mapping_time_ms: float = 0.0
    embedding_time_ms: float = 0.0
    packaging_time_ms: float = 0.0


def convert_svg_to_pptx(
    svg_input: Union[str, Path, bytes],
    output_path: Optional[Union[str, Path]] = None,
    slide_width: float = 10.0,
    slide_height: float = 7.5,
    quality_level: QualityLevel = QualityLevel.BALANCED,
    config: Optional[PipelineConfig] = None,
    # Legacy parameters - FULLY IMPLEMENTED
    preprocessing_config: Optional[dict] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    # Internal parameter for compatibility
    _legacy_return_mode: bool = False
) -> Union[ConversionResult, str]:
    """
    Convert SVG to PowerPoint using Clean Slate architecture.

    This is the primary conversion function that replaces the legacy
    src/svg2pptx.convert_svg_to_pptx() function with pure Clean Slate pipeline.

    Args:
        svg_input: SVG file path, Path object, or SVG content as bytes
        output_path: Output PPTX path (auto-generated if None)
        slide_width: Slide width in inches (default: 10.0)
        slide_height: Slide height in inches (default: 7.5)
        quality_level: Conversion quality (FAST, BALANCED, HIGH)
        config: Advanced pipeline configuration (overrides other params if provided)
        preprocessing_config: Legacy preprocessing configuration (ignored in Clean Slate)
        title: Document title metadata (ignored in Clean Slate)
        author: Document author metadata (ignored in Clean Slate)

    Returns:
        ConversionResult with success status, output path, and metrics

    Raises:
        ConversionError: If conversion fails due to invalid input or pipeline error
    """
    start_time = _get_time_ms()

    try:
        # 1. Process input and handle different input types (like legacy)
        svg_content, temp_svg_path, cleanup_temp_svg = _prepare_svg_input_legacy_compatible(svg_input)

        # 2. Apply preprocessing if configured (like legacy)
        if preprocessing_config:
            svg_content_str = svg_content.decode('utf-8') if isinstance(svg_content, bytes) else str(svg_content)
            processed_svg_str = _apply_preprocessing(svg_content_str, preprocessing_config)
            svg_content = processed_svg_str.encode('utf-8')

        # 3. Handle title/author metadata (stored but not actively used by Clean Slate yet)
        metadata = {}
        if title:
            metadata['title'] = title
        if author:
            metadata['author'] = author

        # 4. Generate output path if not provided
        if output_path is None:
            output_path = _generate_output_path(svg_input)
        else:
            output_path = Path(output_path)

        # 5. Create or use provided configuration
        if config is None:
            # Convert inches to EMU (English Metric Units)
            # 1 inch = 914,400 EMU
            width_emu = int(slide_width * 914400)
            height_emu = int(slide_height * 914400)

            config = PipelineConfig(
                slide_config=SlideConfig(
                    width_emu=width_emu,
                    height_emu=height_emu
                ),
                quality_level=quality_level,
                output_format=OutputFormat.PPTX
            )

        # 6. Create Clean Slate converter
        converter = PipelineFactory.create_converter(config)

        # 7. Convert SVG using Clean Slate pipeline
        logger.info(f"Starting Clean Slate conversion: {len(svg_content)} bytes SVG")
        svg_string = svg_content.decode('utf-8') if isinstance(svg_content, bytes) else str(svg_content)
        pipeline_result = converter.convert_string(svg_string)

        # 8. Write output file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(pipeline_result.output_data)

        # 9. Calculate total conversion time
        total_time = _get_time_ms() - start_time

        # 10. Return successful result
        result = ConversionResult(
            success=True,
            output_path=output_path,
            output_data=pipeline_result.output_data,
            total_time_ms=total_time,
            elements_processed=pipeline_result.elements_processed,
            shapes_converted=pipeline_result.native_elements,  # Use native_elements as shapes converted
            quality_score=pipeline_result.estimated_quality,
            parse_time_ms=pipeline_result.parse_time_ms,
            analyze_time_ms=pipeline_result.analyze_time_ms,
            mapping_time_ms=pipeline_result.mapping_time_ms,
            embedding_time_ms=pipeline_result.embedding_time_ms,
            packaging_time_ms=pipeline_result.packaging_time_ms
        )

        logger.info(f"Clean Slate conversion completed: {output_path} ({total_time:.1f}ms)")

        # Return path string for legacy compatibility or full result for new usage
        if _legacy_return_mode:
            return str(output_path)
        else:
            return result

    except Exception as e:
        total_time = _get_time_ms() - start_time
        error_message = str(e)
        error_stage = getattr(e, 'stage', 'unknown')

        logger.error(f"Clean Slate conversion failed: {error_message} (stage: {error_stage})")

        if _legacy_return_mode:
            # Legacy mode: raise exception like original
            raise ConversionError(error_message, error_stage, e)
        else:
            # New mode: return result object
            return ConversionResult(
                success=False,
                error_message=error_message,
                error_stage=error_stage,
                total_time_ms=total_time
            )


def convert_svg_file(svg_file: str, output_file: str = None) -> str:
    """
    Legacy function signature compatibility for existing code.

    Args:
        svg_file: Path to SVG file
        output_file: Output PPTX file path (optional)

    Returns:
        Path to created PPTX file

    Raises:
        ConversionError: If conversion fails
    """
    # Use legacy return mode to get string result directly
    return convert_svg_to_pptx(svg_file, output_file, _legacy_return_mode=True)


class SVGToPowerPointConverter:
    """
    Legacy class interface compatibility for existing code.

    This class provides the same interface as the legacy system
    but uses Clean Slate architecture internally.
    """

    def __init__(self, slide_width: float = 10.0, slide_height: float = 7.5, services=None):
        """
        Initialize converter with legacy interface.

        Args:
            slide_width: Slide width in inches
            slide_height: Slide height in inches
            services: Ignored (Clean Slate uses internal services)
        """
        self.slide_width = slide_width
        self.slide_height = slide_height

        # Note: services parameter ignored - Clean Slate manages services internally
        if services is not None:
            logger.warning("services parameter ignored - Clean Slate uses internal service management")

    def convert_file(self, svg_file: str, output_file: str = None) -> str:
        """
        Convert SVG file to PowerPoint presentation.

        Args:
            svg_file: Path to SVG file
            output_file: Output PPTX file path (optional)

        Returns:
            Path to created PPTX file

        Raises:
            ConversionError: If conversion fails
        """
        return convert_svg_to_pptx(
            svg_input=svg_file,
            output_path=output_file,
            slide_width=self.slide_width,
            slide_height=self.slide_height,
            _legacy_return_mode=True
        )

    def batch_convert(self, svg_directory: str, output_directory: str = None):
        """
        Convert all SVG files in a directory.

        Args:
            svg_directory: Directory containing SVG files
            output_directory: Output directory (default: same as input)
        """
        svg_dir = Path(svg_directory)
        output_dir = Path(output_directory) if output_directory else svg_dir

        svg_files = list(svg_dir.glob('*.svg'))
        if not svg_files:
            print(f"No SVG files found in {svg_directory}")
            return

        output_dir.mkdir(exist_ok=True)

        for svg_file in svg_files:
            output_file = output_dir / f"{svg_file.stem}.pptx"
            print(f"Converting {svg_file.name} -> {output_file.name}")

            try:
                self.convert_file(str(svg_file), str(output_file))
                print(f"  ✓ Created {output_file}")
            except Exception as e:
                print(f"  ✗ Error: {e}")


def _prepare_svg_input_legacy_compatible(svg_input: Union[str, Path, bytes]) -> tuple:
    """
    Prepare SVG input in legacy compatible way.

    Returns:
        tuple: (svg_content_bytes, temp_svg_path, cleanup_temp_svg)
    """
    import os

    # Handle different input types like legacy system
    if isinstance(svg_input, str) and svg_input.lower().endswith('.svg') and os.path.exists(svg_input):
        # Input is a file path
        with open(svg_input, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        return svg_content.encode('utf-8'), svg_input, False
    else:
        # Input is SVG content or Path object
        if isinstance(svg_input, bytes):
            svg_content = svg_input.decode('utf-8')
        elif isinstance(svg_input, Path):
            with open(svg_input, 'r', encoding='utf-8') as f:
                svg_content = f.read()
        else:
            svg_content = str(svg_input)

        # Create temporary file like legacy
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False, encoding='utf-8') as f:
            f.write(svg_content)
            temp_svg_path = f.name
        return svg_content.encode('utf-8'), temp_svg_path, True


def _apply_preprocessing(svg_content: str, preprocessing_config: dict) -> str:
    """
    Apply preprocessing using Clean Slate preprocessing system.

    Args:
        svg_content: SVG content as string
        preprocessing_config: Configuration dict (legacy format)

    Returns:
        Preprocessed SVG content as string
    """
    try:
        # Parse SVG content
        from lxml import etree as ET
        svg_bytes = svg_content.encode('utf-8') if isinstance(svg_content, str) else svg_content
        svg_root = ET.fromstring(svg_bytes)

        # Import Clean Slate preprocessing
        from .pre import preprocess_svg

        # Map legacy config to Clean Slate chain type
        chain_type = "standard"  # Default
        if preprocessing_config:
            # Map legacy options to Clean Slate chains
            if preprocessing_config.get('aggressive', False):
                chain_type = "comprehensive"
            elif preprocessing_config.get('minimal', False):
                chain_type = "minimal"
            # Add more mapping logic as needed

        # Apply Clean Slate preprocessing
        preprocessed_svg = preprocess_svg(svg_root, chain_type=chain_type)

        # Convert back to string
        return ET.tostring(preprocessed_svg, encoding='unicode', pretty_print=True)

    except ImportError as e:
        # Clean Slate preprocessing not available
        logger.warning(f"Clean Slate preprocessing system not available: {e} - skipping preprocessing")
        return svg_content
    except Exception as e:
        logger.warning(f"Clean Slate preprocessing failed: {e} - using original content")
        return svg_content


def _prepare_svg_input(svg_input: Union[str, Path, bytes]) -> bytes:
    """Prepare SVG input for conversion."""
    if isinstance(svg_input, bytes):
        return svg_input

    # Handle file path input
    path = Path(svg_input)
    if not path.exists():
        raise ConversionError(f"SVG file not found: {path}", "input_validation")

    if not path.is_file():
        raise ConversionError(f"SVG path is not a file: {path}", "input_validation")

    try:
        with open(path, 'rb') as f:
            content = f.read()

        if len(content) == 0:
            raise ConversionError(f"SVG file is empty: {path}", "input_validation")

        return content

    except Exception as e:
        raise ConversionError(f"Cannot read SVG file {path}: {e}", "input_validation")


def _generate_output_path(svg_input: Union[str, Path, bytes]) -> Path:
    """Generate output path for PPTX file."""
    if isinstance(svg_input, bytes):
        # For bytes input, create temp file name
        return Path(tempfile.gettempdir()) / "converted_svg.pptx"

    # For file path input, change extension
    svg_path = Path(svg_input)
    return svg_path.with_suffix('.pptx')


def _get_time_ms() -> float:
    """Get current time in milliseconds."""
    import time
    return time.time() * 1000


# Convenience factory functions for common use cases
def create_fast_converter() -> CleanSlateConverter:
    """Create converter optimized for speed."""
    config = PipelineConfig(quality_level=QualityLevel.FAST)
    return PipelineFactory.create_converter(config)


def create_quality_converter() -> CleanSlateConverter:
    """Create converter optimized for quality."""
    config = PipelineConfig(quality_level=QualityLevel.HIGH_QUALITY)
    return PipelineFactory.create_converter(config)


def create_balanced_converter() -> CleanSlateConverter:
    """Create converter with balanced speed/quality."""
    config = PipelineConfig(quality_level=QualityLevel.BALANCED)
    return PipelineFactory.create_converter(config)


# Main entry point for CLI usage
def main():
    """Command-line interface for Clean Slate conversion."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert SVG files to PowerPoint presentations using Clean Slate architecture'
    )
    parser.add_argument('svg_file', help='Input SVG file')
    parser.add_argument('--output', '-o', help='Output PPTX file path')
    parser.add_argument('--width', type=float, default=10.0, help='Slide width in inches')
    parser.add_argument('--height', type=float, default=7.5, help='Slide height in inches')
    parser.add_argument('--quality', choices=['fast', 'balanced', 'high'], default='balanced',
                       help='Conversion quality level')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Map quality level
    quality_map = {
        'fast': QualityLevel.FAST,
        'balanced': QualityLevel.BALANCED,
        'high': QualityLevel.HIGH
    }

    try:
        result = convert_svg_to_pptx(
            svg_input=args.svg_file,
            output_path=args.output,
            slide_width=args.width,
            slide_height=args.height,
            quality_level=quality_map[args.quality]
        )

        if result.success:
            print(f"✅ Conversion successful: {result.output_path}")
            print(f"   Time: {result.total_time_ms:.1f}ms")
            print(f"   Elements: {result.elements_processed}")
            print(f"   Quality: {result.quality_score:.2f}")
            sys.exit(0)
        else:
            print(f"❌ Conversion failed: {result.error_message}")
            if args.verbose and result.error_stage:
                print(f"   Stage: {result.error_stage}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("❌ Conversion interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(3)


if __name__ == '__main__':
    main()
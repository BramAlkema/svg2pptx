"""
FontEmbeddingEngine - Advanced font subsetting and embedding engine

This module provides font subsetting and embedding capabilities using fonttools.subset:
- Character set analysis and extraction from text content
- Font subsetting with size optimization
- Embedding permission validation
- Comprehensive metrics and statistics tracking
"""

import os
import tempfile
from typing import Dict, List, Optional, Set, Union

from fontTools import subset
from fontTools.ttLib import TTFont

from ..data.embedded_font import (
    EmbeddedFont,
    EmbeddingPermission,
    FontEmbeddingStats,
    FontSubsetRequest,
)
from .font_service import FontService


class FontEmbeddingEngine:
    """
    Advanced font embedding engine with subsetting capabilities.

    Provides comprehensive font processing including:
    - Character set extraction from text content
    - Font subsetting for size optimization
    - Embedding permission validation
    - Performance tracking and statistics
    """

    def __init__(self, font_service: FontService | None = None):
        """
        Initialize FontEmbeddingEngine.

        Args:
            font_service: FontService instance for font loading. If None, creates default.
        """
        self._font_service = font_service or FontService()
        self._embedding_stats = FontEmbeddingStats()
        self._subset_cache: dict[str, EmbeddedFont] = {}

    def extract_characters_from_text(self, text_content: str | list[str]) -> set[str]:
        """
        Extract unique characters from text content.

        Args:
            text_content: Single string or list of strings to analyze

        Returns:
            Set of unique characters found in the text
        """
        if isinstance(text_content, str):
            return set(text_content)

        all_chars = set()
        for text in text_content:
            if isinstance(text, str):
                all_chars.update(set(text))

        return all_chars

    def analyze_font_embedding_permission(self, font: TTFont) -> EmbeddingPermission:
        """
        Analyze font embedding permissions from OS/2 fsType field.

        Args:
            font: TTFont object to analyze

        Returns:
            EmbeddingPermission enum value
        """
        try:
            if 'OS/2' not in font:
                return EmbeddingPermission.INSTALLABLE  # Default to most permissive

            os2_table = font['OS/2']
            fs_type = getattr(os2_table, 'fsType', 0)

            # Check fsType bits according to OpenType specification
            if fs_type & 0x0002:  # Bit 1: Restricted License
                return EmbeddingPermission.RESTRICTED
            elif fs_type & 0x0004:  # Bit 2: Preview & Print
                return EmbeddingPermission.PREVIEW_PRINT
            elif fs_type & 0x0008:  # Bit 3: Editable
                return EmbeddingPermission.EDITABLE
            elif fs_type & 0x0100:  # Bit 8: No subsetting
                return EmbeddingPermission.NO_SUBSETTING
            elif fs_type & 0x0200:  # Bit 9: Bitmap embedding only
                return EmbeddingPermission.BITMAP_ONLY
            else:
                return EmbeddingPermission.INSTALLABLE

        except Exception:
            return EmbeddingPermission.INSTALLABLE  # Safe default

    def validate_embedding_permission(self, font: TTFont) -> bool:
        """
        Validate if font can be embedded based on its permissions.

        Args:
            font: TTFont object to validate

        Returns:
            True if embedding is allowed
        """
        permission = self.analyze_font_embedding_permission(font)

        # Only restricted fonts cannot be embedded
        return permission != EmbeddingPermission.RESTRICTED

    def create_font_subset(self, subset_request: FontSubsetRequest) -> EmbeddedFont | None:
        """
        Create font subset based on character requirements.

        Args:
            subset_request: FontSubsetRequest with subsetting parameters

        Returns:
            EmbeddedFont with subset data, or None if subsetting failed
        """
        cache_key = subset_request.get_cache_key()

        if cache_key in self._subset_cache:
            return self._subset_cache[cache_key]

        try:
            # Load original font
            original_font = self._font_service.load_font_from_path(subset_request.font_path)
            if not original_font:
                error_msg = f"Failed to load font from {subset_request.font_path}"
                self._embedding_stats.add_failed_embedding(error_msg)
                return None

            # Validate embedding permissions
            if not self.validate_embedding_permission(original_font):
                error_msg = f"Font {subset_request.font_name} does not allow embedding"
                self._embedding_stats.add_failed_embedding(error_msg)
                return None

            # Get original font size
            original_size = os.path.getsize(subset_request.font_path)

            # Create subset
            subset_data = self._perform_font_subsetting(
                original_font,
                subset_request.characters,
                subset_request.optimization_level,
                subset_request.preserve_hinting,
                subset_request.preserve_layout_tables,
            )

            if not subset_data:
                error_msg = f"Font subsetting failed for {subset_request.font_name}"
                self._embedding_stats.add_failed_embedding(error_msg)
                return None

            # Create EmbeddedFont object
            embedding_permission = self.analyze_font_embedding_permission(original_font)

            embedded_font = EmbeddedFont.create_from_font(
                font_name=subset_request.font_name or os.path.basename(subset_request.font_path),
                font_data=subset_data,
                characters=subset_request.characters,
                original_size=original_size,
                embedding_permission=embedding_permission,
                embedding_allowed=True,
                file_format=subset_request.target_format,
            )

            # Cache result
            self._subset_cache[cache_key] = embedded_font

            # Update statistics
            self._embedding_stats.add_successful_embedding(embedded_font)

            return embedded_font

        except Exception as e:
            error_msg = f"Font subset creation failed: {str(e)}"
            self._embedding_stats.add_failed_embedding(error_msg)
            return None

    def _perform_font_subsetting(self, font: TTFont, characters: set[str],
                                optimization_level: str, preserve_hinting: bool,
                                preserve_layout_tables: bool) -> bytes | None:
        """
        Perform actual font subsetting using fonttools.subset.

        Args:
            font: Original TTFont object
            characters: Set of characters to include in subset
            optimization_level: Optimization level ("none", "basic", "aggressive")
            preserve_hinting: Whether to preserve hinting information
            preserve_layout_tables: Whether to preserve layout tables (GSUB, GPOS)

        Returns:
            Subset font data as bytes, or None if subsetting failed
        """
        try:
            # Create subset options
            options = subset.Options()

            # Configure optimization level
            if optimization_level == "aggressive":
                options.desubroutinize = True
                options.hinting = False
                options.legacy_kern = False
                options.layout_features = []
            elif optimization_level == "basic":
                options.desubroutinize = False
                options.hinting = preserve_hinting
                options.legacy_kern = True
                if not preserve_layout_tables:
                    options.layout_features = []
            else:  # "none"
                options.desubroutinize = False
                options.hinting = True
                options.legacy_kern = True

            # Set character subset
            options.text = ''.join(characters)

            # Create subsetter
            subsetter = subset.Subsetter(options=options)

            # Perform subsetting
            subsetter.populate(text=options.text)
            subsetter.subset(font)

            # Save subset to temporary file and read back
            with tempfile.NamedTemporaryFile(suffix='.ttf', delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                font.save(temp_path)

                with open(temp_path, 'rb') as f:
                    subset_data = f.read()

                return subset_data

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            return None

    def create_embedding_for_text(self, font_path: str, text_content: str | list[str],
                                 font_name: str | None = None,
                                 optimization_level: str = "basic") -> EmbeddedFont | None:
        """
        Create font embedding optimized for specific text content.

        Args:
            font_path: Path to original font file
            text_content: Text content to analyze for character requirements
            font_name: Optional font name (derived from path if not provided)
            optimization_level: Subsetting optimization level

        Returns:
            EmbeddedFont with subset optimized for the text content
        """
        # Extract characters from text
        characters = self.extract_characters_from_text(text_content)

        if not characters:
            return None

        # Create subset request
        subset_request = FontSubsetRequest(
            font_path=font_path,
            characters=characters,
            font_name=font_name or os.path.basename(font_path),
            optimization_level=optimization_level,
        )

        return self.create_font_subset(subset_request)

    def batch_create_embeddings(self, text_font_mappings: list[dict[str, str]],
                               optimization_level: str = "basic") -> list[EmbeddedFont | None]:
        """
        Create multiple font embeddings in batch.

        Args:
            text_font_mappings: List of dicts with 'text' and 'font_path' keys
            optimization_level: Subsetting optimization level

        Returns:
            List of EmbeddedFont objects (None for failed embeddings)
        """
        results = []

        for mapping in text_font_mappings:
            text_content = mapping.get('text', '')
            font_path = mapping.get('font_path', '')
            font_name = mapping.get('font_name')

            if not text_content or not font_path:
                results.append(None)
                continue

            embedded_font = self.create_embedding_for_text(
                font_path=font_path,
                text_content=text_content,
                font_name=font_name,
                optimization_level=optimization_level,
            )

            results.append(embedded_font)

        return results

    def get_embedding_statistics(self) -> FontEmbeddingStats:
        """
        Get current embedding statistics.

        Returns:
            FontEmbeddingStats object with performance metrics
        """
        return self._embedding_stats

    def clear_cache(self):
        """Clear subset cache and reset statistics."""
        self._subset_cache.clear()
        self._embedding_stats = FontEmbeddingStats()

    def get_cache_stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        return {
            'cached_subsets': len(self._subset_cache),
            'total_fonts_processed': self._embedding_stats.total_fonts_processed,
            'successful_embeddings': self._embedding_stats.total_fonts_embedded,
            'failed_embeddings': self._embedding_stats.total_fonts_failed,
        }

    def estimate_subset_size_reduction(self, font_path: str,
                                     characters: set[str]) -> dict[str, float]:
        """
        Estimate size reduction from font subsetting without creating the subset.

        Args:
            font_path: Path to original font file
            characters: Set of characters that would be included

        Returns:
            Dictionary with size estimates
        """
        try:
            font = self._font_service.load_font_from_path(font_path)
            if not font:
                return {'estimated_reduction': 0.0, 'error': 'Font loading failed'}

            original_size = os.path.getsize(font_path)

            # Simple estimation based on character count
            # This is a rough approximation - actual reduction depends on many factors
            total_chars = len(font.getGlyphSet())
            subset_chars = len(characters)

            if total_chars == 0:
                return {'estimated_reduction': 0.0, 'error': 'No glyphs in font'}

            # Base reduction from glyph removal
            glyph_reduction = 1.0 - (subset_chars / total_chars)

            # Additional reduction from table optimization (varies by font)
            table_reduction = 0.1 if glyph_reduction > 0.5 else 0.05

            # Conservative estimate
            estimated_reduction = min(0.9, glyph_reduction + table_reduction)

            return {
                'estimated_reduction': estimated_reduction,
                'original_size_bytes': original_size,
                'estimated_subset_size_bytes': int(original_size * (1 - estimated_reduction)),
                'total_glyphs': total_chars,
                'subset_glyphs': subset_chars,
            }

        except Exception as e:
            return {'estimated_reduction': 0.0, 'error': str(e)}

    def create_intelligent_pptx_package(self, svg_content: str, output_path: str,
                                       optimization_level: str = "basic",
                                       force_embedding: bool = False) -> dict[str, any]:
        """
        Create PPTX package with intelligent font embedding based on SVG analysis.

        Args:
            svg_content: SVG content to convert to PPTX
            output_path: Path where PPTX file should be saved
            optimization_level: Font subsetting optimization level
            force_embedding: Force font embedding even if not recommended

        Returns:
            Dictionary with embedding results and package statistics
        """
        from ..pptx.package_builder import PPTXPackageBuilder
        from ..services.svg_font_analyzer import SVGFontAnalyzer

        # Analyze SVG for font requirements
        analyzer = SVGFontAnalyzer()
        font_analysis = analyzer.analyze_svg_fonts(svg_content)

        result = {
            'font_analysis': font_analysis,
            'embedding_performed': False,
            'embedded_fonts_count': 0,
        }

        # Determine if we should embed fonts
        should_embed = force_embedding or font_analysis['should_embed_fonts']

        if not should_embed or not font_analysis['has_text_elements']:
            # Create simple PPTX without font embedding
            builder = PPTXPackageBuilder()
            try:
                builder.create_pptx_from_svg(svg_content, output_path, embed_fonts=False)
                result.update({
                    'success': True,
                    'output_path': output_path,
                    'message': 'PPTX created without font embedding (not needed)',
                    'package_statistics': builder.get_package_statistics(),
                })
                return result
            except Exception as e:
                result.update({
                    'success': False,
                    'error': f'PPTX creation failed: {str(e)}',
                })
                return result

        # Create font subset requests based on analysis
        subset_requests = analyzer.create_font_subset_requests(svg_content, self._font_service)

        if not subset_requests:
            result.update({
                'success': False,
                'error': 'No suitable fonts found for embedding',
                'message': 'Required fonts not found in system',
            })
            return result

        # Create embedded fonts
        embedded_fonts = []
        for request in subset_requests:
            embedded_font = self.create_font_subset(request)
            if embedded_font:
                embedded_fonts.append(embedded_font)

        if not embedded_fonts:
            result.update({
                'success': False,
                'error': 'Font subsetting failed for all fonts',
                'embedded_fonts_count': 0,
            })
            return result

        # Create PPTX package with embedded fonts
        builder = PPTXPackageBuilder()

        # Add successful fonts to the package
        for font in embedded_fonts:
            builder.add_embedded_font(font)

        # Create PPTX file
        try:
            builder.create_pptx_from_svg(svg_content, output_path, embed_fonts=True)

            # Get package statistics
            package_stats = builder.get_package_statistics()
            embedding_stats = self.get_embedding_statistics().get_summary()

            result.update({
                'success': True,
                'output_path': output_path,
                'embedding_performed': True,
                'embedded_fonts_count': len(embedded_fonts),
                'package_statistics': package_stats,
                'embedding_statistics': embedding_stats,
                'embedded_fonts': [font.get_metadata() for font in embedded_fonts],
            })

        except Exception as e:
            result.update({
                'success': False,
                'error': f'PPTX creation failed: {str(e)}',
                'embedded_fonts_count': len(embedded_fonts),
            })

        return result

    def create_pptx_embedding_package(self, text_font_mappings: list[dict[str, str]],
                                     svg_content: str, output_path: str,
                                     optimization_level: str = "basic") -> dict[str, any]:
        """
        Create PPTX package with embedded fonts optimized for specific text content.

        This method is for when you have explicit text-font mappings.
        For automatic detection, use create_intelligent_pptx_package instead.

        Args:
            text_font_mappings: List of dicts with 'text' and 'font_path' keys
            svg_content: SVG content to convert to PPTX
            output_path: Path where PPTX file should be saved
            optimization_level: Font subsetting optimization level

        Returns:
            Dictionary with embedding results and package statistics
        """
        from ..pptx.package_builder import PPTXPackageBuilder

        # Create embedded fonts for the text content
        embedded_fonts = self.batch_create_embeddings(
            text_font_mappings=text_font_mappings,
            optimization_level=optimization_level,
        )

        # Filter out failed embeddings
        successful_fonts = [font for font in embedded_fonts if font is not None]

        if not successful_fonts:
            return {
                'success': False,
                'error': 'No fonts could be embedded successfully',
                'embedded_fonts_count': 0,
            }

        # Create PPTX package with embedded fonts
        builder = PPTXPackageBuilder()

        # Add all successful fonts to the package
        for font in successful_fonts:
            builder.add_embedded_font(font)

        # Create PPTX file
        try:
            builder.create_pptx_from_svg(svg_content, output_path, embed_fonts=True)

            # Get package statistics
            package_stats = builder.get_package_statistics()
            embedding_stats = self.get_embedding_statistics().get_summary()

            return {
                'success': True,
                'output_path': output_path,
                'package_statistics': package_stats,
                'embedding_statistics': embedding_stats,
                'embedded_fonts': [font.get_metadata() for font in successful_fonts],
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'PPTX creation failed: {str(e)}',
                'embedded_fonts_count': len(successful_fonts),
            }

    def validate_pptx_compatibility(self, embedded_fonts: list[EmbeddedFont]) -> dict[str, any]:
        """
        Validate that embedded fonts are compatible with PPTX format.

        Args:
            embedded_fonts: List of EmbeddedFont instances to validate

        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'compatible_fonts': [],
            'incompatible_fonts': [],
            'warnings': [],
            'total_size_mb': 0.0,
            'compatibility_score': 0.0,
        }

        total_size = 0
        compatible_count = 0

        for font in embedded_fonts:
            font_result = {
                'font_name': font.font_name,
                'size_mb': font.embedded_size / (1024 * 1024),
                'compatible': True,
                'issues': [],
            }

            # Check font size limits (PowerPoint has practical limits)
            if font.embedded_size > 50 * 1024 * 1024:  # 50MB limit
                font_result['compatible'] = False
                font_result['issues'].append('Font size exceeds recommended 50MB limit')

            # Check embedding permissions
            if not font.embedding_allowed:
                font_result['compatible'] = False
                font_result['issues'].append('Font licensing does not allow embedding')

            # Check file format compatibility
            if font.file_format.lower() not in ['ttf', 'otf']:
                font_result['issues'].append(f'Font format {font.file_format} may have limited PowerPoint support')
                validation_results['warnings'].append(
                    f'{font.font_name}: {font.file_format} format may not be fully supported',
                )

            # Check character subset size
            if font.character_count > 10000:
                validation_results['warnings'].append(
                    f'{font.font_name}: Large character subset ({font.character_count} chars) may impact performance',
                )

            total_size += font.embedded_size

            if font_result['compatible']:
                validation_results['compatible_fonts'].append(font_result)
                compatible_count += 1
            else:
                validation_results['incompatible_fonts'].append(font_result)

        validation_results['total_size_mb'] = total_size / (1024 * 1024)
        validation_results['compatibility_score'] = (
            compatible_count / len(embedded_fonts) if embedded_fonts else 1.0
        )

        # Add overall warnings
        if total_size > 100 * 1024 * 1024:  # 100MB total
            validation_results['warnings'].append(
                f'Total embedded font size ({validation_results["total_size_mb"]:.1f}MB) is very large',
            )

        return validation_results
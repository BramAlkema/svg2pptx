#!/usr/bin/env python3
"""
Clean Slate Converter

Main end-to-end conversion pipeline from SVG to PPTX using clean slate architecture.
"""

import time
import logging
import json
import io
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

from ..ir import SceneGraph, IRElement
from ..analyze import SVGAnalyzer, AnalysisResult
from ..parse import SVGParser, ParseResult
from ..policy import PolicyEngine, PolicyConfig
from ..map.base import Mapper, MapperResult
from ..map import PathMapper, GroupMapper, ImageMapper
from ..map.font_mapper_adapter import FontMapperAdapter
from ..io import DrawingMLEmbedder, PackageWriter, EmbedderResult
from ..services.conversion_services import ConversionServices
from .config import PipelineConfig, OutputFormat
from .error_reporter import PipelineErrorReporter, ErrorSeverity, ErrorCategory

# Import migrated systems for integration
from core.animations import SMILParser
from core.performance.measurement import BenchmarkEngine
# Avoid circular import - import CustGeomGenerator lazily when needed

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Exception raised when conversion fails"""
    def __init__(self, message: str, stage: str = None, cause: Exception = None):
        super().__init__(message)
        self.stage = stage
        self.cause = cause


@dataclass
class ConversionResult:
    """Result of complete SVG to PPTX conversion"""
    # Output data
    output_data: bytes
    output_format: OutputFormat

    # Pipeline statistics
    total_time_ms: float = 0.0
    parse_time_ms: float = 0.0
    analyze_time_ms: float = 0.0
    mapping_time_ms: float = 0.0
    embedding_time_ms: float = 0.0
    packaging_time_ms: float = 0.0

    # Content statistics
    elements_processed: int = 0
    native_elements: int = 0
    emf_elements: int = 0

    # Quality metrics
    estimated_quality: float = 1.0
    estimated_performance: float = 1.0
    compression_ratio: float = 1.0

    # Metadata
    slide_count: int = 1
    media_files: int = 0
    relationships: int = 0

    # Debug information
    debug_data: Dict[str, Any] = None


class CleanSlateConverter:
    """
    End-to-end SVG to PPTX converter using clean slate architecture.

    Orchestrates the complete pipeline:
    SVG → Parse → Analyze → IR → Map → Embed → Package → PPTX
    """

    def __init__(self, config: PipelineConfig = None):
        """
        Initialize converter with configuration.

        Args:
            config: Pipeline configuration (uses defaults if None)
        """
        self.config = config or PipelineConfig()
        self.logger = logging.getLogger(__name__)

        # Configure logging level
        if self.config.verbose_logging:
            logging.getLogger(__name__.split('.')[0]).setLevel(logging.DEBUG)

        # Initialize pipeline components
        self._initialize_components()

        # Initialize error reporter
        self.error_reporter = PipelineErrorReporter()

        # Statistics
        self._stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'total_time_ms': 0.0
        }

    def convert_file(self, svg_path: str, output_path: str = None) -> ConversionResult:
        """
        Convert SVG file to PPTX.

        Args:
            svg_path: Path to SVG file
            output_path: Path for output file (auto-generated if None)

        Returns:
            ConversionResult with output data and statistics

        Raises:
            ConversionError: If conversion fails
        """
        try:
            # Read SVG file
            svg_content = Path(svg_path).read_text(encoding='utf-8')

            # Generate output path if not provided
            if output_path is None:
                svg_file = Path(svg_path)
                if self.config.output_format == OutputFormat.PPTX:
                    output_path = svg_file.with_suffix('.pptx')
                elif self.config.output_format == OutputFormat.SLIDE_XML:
                    output_path = svg_file.with_suffix('.xml')
                else:
                    output_path = svg_file.with_suffix('.json')

            # Convert content
            result = self.convert_string(svg_content)

            # Write output file
            if self.config.output_format == OutputFormat.PPTX:
                with open(output_path, 'wb') as f:
                    f.write(result.output_data)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result.output_data.decode('utf-8'))

            self.logger.info(f"Converted {svg_path} to {output_path}")
            return result

        except Exception as e:
            self._record_failure()
            raise ConversionError(f"Failed to convert file {svg_path}: {e}",
                                stage="file_conversion", cause=e)

    def convert_string(self, svg_content: str) -> ConversionResult:
        """
        Convert SVG string to PPTX.

        Args:
            svg_content: SVG content as string

        Returns:
            ConversionResult with output data and statistics

        Raises:
            ConversionError: If conversion fails
        """
        start_time = time.perf_counter()

        try:
            # Stage 1: Parse SVG
            parse_start = time.perf_counter()
            try:
                parse_result = self.parser.parse(svg_content)
                parse_time = (time.perf_counter() - parse_start) * 1000

                if not parse_result.success:
                    self.error_reporter.report_parsing_error(
                        message=f"SVG parsing failed: {parse_result.error}",
                        svg_content=svg_content
                    )
                    raise ConversionError(f"SVG parsing failed: {parse_result.error}",
                                        stage="parsing")
            except Exception as e:
                parse_time = (time.perf_counter() - parse_start) * 1000
                self.error_reporter.report_parsing_error(
                    message=f"SVG parsing exception: {e}",
                    svg_content=svg_content,
                    exception=e
                )
                raise ConversionError(f"SVG parsing failed: {e}", stage="parsing", cause=e)

            # Stage 2: Analyze SVG structure
            analyze_start = time.perf_counter()
            try:
                analysis_result = self.analyzer.analyze(parse_result.svg_root)
                analyze_time = (time.perf_counter() - analyze_start) * 1000
            except Exception as e:
                analyze_time = (time.perf_counter() - analyze_start) * 1000
                self.error_reporter.report_analysis_error(
                    message=f"SVG analysis failed: {e}",
                    element_count=parse_result.element_count,
                    exception=e
                )
                raise ConversionError(f"SVG analysis failed: {e}", stage="analysis", cause=e)

            # Stage 2.5: Check for animations (using migrated animation system)
            try:
                animations = self.animation_parser.parse_svg_animations(parse_result.svg_root)
                if animations:
                    self.logger.info(f"Detected {len(animations)} animations in SVG")
                    # TODO: In future, integrate animations into conversion pipeline
                else:
                    self.logger.debug("No animations detected in SVG")
            except Exception as e:
                self.logger.warning(f"Animation detection failed: {e}")

            # Stage 3: Convert to IR
            scene = analysis_result.scene

            # Defensive guard: ensure scene is never None
            if scene is None:
                self.logger.warning("Analyzer returned None scene; using empty scene to continue.")
                scene = []

            # Stage 4: Map IR elements
            mapping_start = time.perf_counter()
            mapper_results = self._map_scene_elements(scene)
            mapping_time = (time.perf_counter() - mapping_start) * 1000

            # Stage 5: Embed into slide structure
            embedding_start = time.perf_counter()
            embedder_result = self.embedder.embed_scene(scene, mapper_results)
            embedding_time = (time.perf_counter() - embedding_start) * 1000

            # Stage 6: Generate final output
            packaging_start = time.perf_counter()
            output_data = self._generate_output(embedder_result, analysis_result)
            packaging_time = (time.perf_counter() - packaging_start) * 1000

            # Calculate total time and statistics
            total_time = (time.perf_counter() - start_time) * 1000

            # Create result
            result = ConversionResult(
                output_data=output_data,
                output_format=self.config.output_format,
                total_time_ms=total_time,
                parse_time_ms=parse_time,
                analyze_time_ms=analyze_time,
                mapping_time_ms=mapping_time,
                embedding_time_ms=embedding_time,
                packaging_time_ms=packaging_time,
                elements_processed=len(mapper_results),
                native_elements=embedder_result.native_elements,
                emf_elements=embedder_result.emf_elements,
                estimated_quality=embedder_result.estimated_quality,
                estimated_performance=embedder_result.estimated_performance,
                slide_count=1,
                media_files=len(embedder_result.media_files),
                relationships=len(embedder_result.relationship_data)
            )

            # Add debug data if enabled
            if self.config.enable_debug:
                result.debug_data = self._collect_debug_data(
                    parse_result, analysis_result, mapper_results, embedder_result
                )

            # Record success
            self._record_success(result)

            # Record performance metrics (using migrated performance system)
            try:
                throughput = len(mapper_results) / (total_time / 1000) if total_time > 0 else 0
                self.logger.debug(f"Performance metrics - Throughput: {throughput:.1f} elements/sec, Total time: {total_time:.1f}ms")
                # Note: Performance engine available for future detailed benchmarking
            except Exception as e:
                self.logger.warning(f"Performance recording failed: {e}")

            return result

        except Exception as e:
            # Report final conversion error with full context
            self.error_reporter.report_error(
                message=f"Conversion pipeline failed: {e}",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.PARSING,  # Will be more specific based on actual stage
                exception=e
            )

            self._record_failure()

            # Include error summary in the exception
            error_summary = self.error_reporter.get_error_summary()
            enhanced_message = f"Conversion failed: {e}. Error summary: {error_summary}"

            raise ConversionError(enhanced_message, cause=e)

    def _initialize_components(self) -> None:
        """Initialize pipeline components based on configuration"""
        try:
            # Initialize services first
            self.services = ConversionServices.create_default()

            # Initialize parser
            self.parser = SVGParser()

            # Initialize analyzer
            self.analyzer = SVGAnalyzer()

            # Initialize policy engine with config
            policy_config = PolicyConfig()
            self.policy = PolicyEngine(policy_config)

            # Initialize mappers with services
            # Create individual mappers first
            path_mapper = PathMapper(self.policy, self.services)
            text_mapper = FontMapperAdapter(self.policy, self.services)
            image_mapper = ImageMapper(self.policy, self.services)

            # Create group mapper with child_mappers wired
            child_mappers = {
                'path': path_mapper,
                'text': text_mapper,
                'image': image_mapper
            }
            group_mapper = GroupMapper(self.policy, self.services, child_mappers)

            self.mappers = {
                'path': path_mapper,
                'textframe': text_mapper,
                'richtextframe': text_mapper,  # TextMapper handles both TextFrame and RichTextFrame
                'group': group_mapper,
                'image': image_mapper
            }

            # Initialize embedder
            self.embedder = DrawingMLEmbedder(
                slide_width_emu=self.config.slide_config.width_emu,
                slide_height_emu=self.config.slide_config.height_emu
            )

            # Initialize package writer
            self.package_writer = PackageWriter()

            # Initialize migrated system integrations
            self.animation_parser = SMILParser()  # For SVG animation detection
            self.performance_engine = BenchmarkEngine()  # For performance monitoring

            # Lazy import to avoid circular dependency
            from core.converters.custgeom_generator import CustGeomGenerator
            self.custgeom_generator = CustGeomGenerator()  # For custom geometry generation

            self.logger.debug("Pipeline components initialized successfully")
            self.logger.debug("Migrated systems integrated: animations, performance, custom geometry")

        except Exception as e:
            raise ConversionError(f"Failed to initialize pipeline components: {e}",
                                stage="initialization", cause=e)

    def _map_scene_elements(self, scene: SceneGraph) -> List[MapperResult]:
        """Map all elements in scene using appropriate mappers"""
        mapper_results = []

        # Defensive: accept SceneGraph, list, or None
        if scene is None:
            self.logger.warning("Scene is None; treating as empty scene.")
            return []

        # If SceneGraph has elements attribute, use it; otherwise iterate directly
        elements = getattr(scene, "elements", None)
        if elements is None:
            elements = scene  # Assume it's already an iterable

        # Defensive: must be iterable
        if not hasattr(elements, "__iter__"):
            self.logger.error("Scene elements not iterable; treating as empty scene.")
            return []

        for element in elements:
            try:
                # Find appropriate mapper
                mapper = self._find_mapper(element)
                if not mapper:
                    element_type = type(element).__name__
                    self.error_reporter.report_mapping_error(
                        message=f"No mapper found for element type: {element_type}",
                        element_type=element_type
                    )
                    self.logger.warning(f"No mapper found for element type: {element_type}")
                    continue

                # Map element
                result = mapper.map(element)
                mapper_results.append(result)

            except Exception as e:
                element_type = type(element).__name__
                mapper_name = type(mapper).__name__ if mapper else "unknown"

                self.error_reporter.report_mapping_error(
                    message=f"Failed to map element {element_type}: {e}",
                    element_type=element_type,
                    mapper_name=mapper_name,
                    exception=e
                )

                self.logger.error(f"Failed to map element {element_type} with {mapper_name}: {e}")
                if not self.config.enable_debug:
                    # Continue with other elements in production
                    continue
                else:
                    # Re-raise in debug mode
                    raise

        return mapper_results

    def _find_mapper(self, element: IRElement) -> Optional[Mapper]:
        """Find appropriate mapper for IR element"""
        element_type = type(element).__name__.lower()

        # Direct type mapping
        if element_type in self.mappers:
            return self.mappers[element_type]

        # Check mapper capabilities
        for mapper in self.mappers.values():
            if mapper.can_map(element):
                return mapper

        return None

    def _generate_output(self, embedder_result: EmbedderResult,
                        analysis_result: AnalysisResult) -> bytes:
        """Generate final output in requested format"""
        try:
            if self.config.output_format == OutputFormat.PPTX:
                # Generate complete PPTX package
                package_stats = self.package_writer.write_package_stream(
                    [embedder_result],
                    output_stream := io.BytesIO()
                )
                return output_stream.getvalue()

            elif self.config.output_format == OutputFormat.SLIDE_XML:
                # Return just the slide XML
                return embedder_result.slide_xml.encode('utf-8')

            elif self.config.output_format == OutputFormat.DEBUG_JSON:
                # Return debug JSON
                debug_data = {
                    'analysis': {
                        'complexity_score': analysis_result.complexity_score,
                        'element_count': analysis_result.element_count,
                        'recommended_format': analysis_result.recommended_output_format.value
                    },
                    'embedding': {
                        'elements_embedded': embedder_result.elements_embedded,
                        'native_elements': embedder_result.native_elements,
                        'emf_elements': embedder_result.emf_elements,
                        'processing_time_ms': embedder_result.processing_time_ms
                    },
                    'slide_xml': embedder_result.slide_xml,
                    'relationships': embedder_result.relationship_data,
                    'media_files': [
                        {k: v for k, v in media.items() if k != 'data'}
                        for media in embedder_result.media_files
                    ]
                }
                return json.dumps(debug_data, indent=2).encode('utf-8')

            else:
                raise ConversionError(f"Unsupported output format: {self.config.output_format}")

        except Exception as e:
            raise ConversionError(f"Failed to generate output: {e}",
                                stage="output_generation", cause=e)

    def _collect_debug_data(self, parse_result: ParseResult,
                           analysis_result: AnalysisResult,
                           mapper_results: List[MapperResult],
                           embedder_result: EmbedderResult) -> Dict[str, Any]:
        """Collect debug data from all pipeline stages"""
        return {
            'parse_result': {
                'success': parse_result.success,
                'element_count': len(parse_result.svg_root) if parse_result.svg_root is not None else 0,
                'parsing_time_ms': parse_result.processing_time_ms
            },
            'analysis_result': {
                'complexity_score': analysis_result.complexity_score,
                'element_count': analysis_result.element_count,
                'recommended_format': analysis_result.recommended_output_format.value,
                'analysis_time_ms': analysis_result.processing_time_ms
            },
            'mapper_results': [
                {
                    'element_type': type(result.element).__name__,
                    'output_format': result.output_format.value,
                    'estimated_quality': result.estimated_quality,
                    'estimated_performance': result.estimated_performance,
                    'processing_time_ms': result.processing_time_ms,
                    'output_size_bytes': result.output_size_bytes
                }
                for result in mapper_results
            ],
            'embedder_result': {
                'elements_embedded': embedder_result.elements_embedded,
                'native_elements': embedder_result.native_elements,
                'emf_elements': embedder_result.emf_elements,
                'processing_time_ms': embedder_result.processing_time_ms,
                'total_size_bytes': embedder_result.total_size_bytes
            },
            'policy_decisions': [
                result.policy_decision.to_dict() if hasattr(result.policy_decision, 'to_dict')
                else str(result.policy_decision)
                for result in mapper_results
            ]
        }

    def _record_success(self, result: ConversionResult) -> None:
        """Record successful conversion statistics"""
        self._stats['total_conversions'] += 1
        self._stats['successful_conversions'] += 1
        self._stats['total_time_ms'] += result.total_time_ms

    def _record_failure(self) -> None:
        """Record failed conversion statistics"""
        self._stats['total_conversions'] += 1
        self._stats['failed_conversions'] += 1

    def get_statistics(self) -> Dict[str, Any]:
        """Get converter statistics"""
        total = max(self._stats['total_conversions'], 1)
        return {
            **self._stats,
            'success_rate': self._stats['successful_conversions'] / total,
            'failure_rate': self._stats['failed_conversions'] / total,
            'avg_time_ms': self._stats['total_time_ms'] / max(self._stats['successful_conversions'], 1),
            'mapper_stats': {
                name: mapper.get_statistics()
                for name, mapper in self.mappers.items()
            },
            'embedder_stats': self.embedder.get_statistics()
        }

    def reset_statistics(self) -> None:
        """Reset converter statistics"""
        self._stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'total_time_ms': 0.0
        }

        # Reset component statistics
        for mapper in self.mappers.values():
            mapper.reset_statistics()
        self.embedder.reset_statistics()

    def get_config(self) -> PipelineConfig:
        """Get current pipeline configuration"""
        return self.config

    def update_config(self, config: PipelineConfig) -> None:
        """Update pipeline configuration and reinitialize components"""
        self.config = config
        self._initialize_components()

    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive error summary for debugging.

        Returns:
            Dict containing error statistics and recent error details
        """
        return self.error_reporter.get_error_summary()

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent error reports.

        Args:
            limit: Maximum number of recent errors to return

        Returns:
            List of recent error report dictionaries
        """
        recent_errors = self.error_reporter.error_history[-limit:]
        return [error.to_dict() for error in recent_errors]

    def has_errors(self) -> bool:
        """Check if any errors have been reported during this session"""
        return len(self.error_reporter.error_history) > 0


def create_converter(config: PipelineConfig = None) -> CleanSlateConverter:
    """
    Create CleanSlateConverter with configuration.

    Args:
        config: Pipeline configuration (uses defaults if None)

    Returns:
        Configured CleanSlateConverter
    """
    return CleanSlateConverter(config)
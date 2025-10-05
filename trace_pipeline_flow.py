#!/usr/bin/env python3
"""
End-to-end pipeline tracer: SVG → Google Slides

Traces the complete data flow through all pipeline stages with detailed logging.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/pipeline_trace.log', mode='w'),
    ],
)

logger = logging.getLogger(__name__)


class PipelineTracer:
    """Traces SVG→PPTX→Drive pipeline with detailed logging at each stage"""

    def __init__(self):
        self.trace_data = {
            'stages': [],
            'transformations': [],
            'decisions': [],
        }

    def trace_stage(self, stage_name: str, data: Any, metadata: dict = None):
        """Log a pipeline stage with data snapshot"""
        logger.info(f"\n{'='*80}")
        logger.info(f"STAGE: {stage_name}")
        logger.info(f"{'='*80}")

        stage_info = {
            'name': stage_name,
            'data_type': type(data).__name__,
            'metadata': metadata or {},
        }

        # Log data summary
        if isinstance(data, (list, tuple)):
            logger.info(f"  Data: {len(data)} items")
            stage_info['count'] = len(data)
        elif isinstance(data, dict):
            logger.info(f"  Data: {len(data)} keys")
            stage_info['keys'] = list(data.keys())
        elif isinstance(data, str):
            logger.info(f"  Data: {len(data)} characters")
            stage_info['length'] = len(data)
        else:
            logger.info(f"  Data: {data}")

        self.trace_data['stages'].append(stage_info)

    def trace_transformation(self, from_type: str, to_type: str, details: dict = None):
        """Log a data transformation"""
        logger.info(f"  TRANSFORM: {from_type} → {to_type}")
        if details:
            for key, value in details.items():
                logger.info(f"    {key}: {value}")

        self.trace_data['transformations'].append({
            'from': from_type,
            'to': to_type,
            'details': details or {},
        })

    def trace_decision(self, element_type: str, decision: str, reason: str):
        """Log a policy decision"""
        logger.info(f"  DECISION: {element_type} → {decision}")
        logger.info(f"    Reason: {reason}")

        self.trace_data['decisions'].append({
            'element_type': element_type,
            'decision': decision,
            'reason': reason,
        })

    def save_trace(self, output_path: str = '/tmp/pipeline_trace.json'):
        """Save trace data to JSON"""
        with open(output_path, 'w') as f:
            json.dump(self.trace_data, f, indent=2)
        logger.info(f"\n✅ Trace saved to: {output_path}")


def trace_svg_to_pptx_full_pipeline(svg_content: str, tracer: PipelineTracer):
    """Trace SVG → PPTX using the full Clean Slate pipeline"""

    tracer.trace_stage("FULL PIPELINE: SVG → PPTX", svg_content)

    from core.pipeline.converter import CleanSlateConverter
    from core.pipeline.config import PipelineConfig

    config = PipelineConfig()
    converter = CleanSlateConverter(config=config)

    try:
        # Convert SVG string to PPTX bytes
        result = converter.convert_string(svg_content=svg_content)

        tracer.trace_transformation(
            'SVG String',
            'PPTX Bytes',
            {
                'total_time_ms': result.total_time_ms,
                'parse_time_ms': result.parse_time_ms,
                'analyze_time_ms': result.analyze_time_ms,
                'mapping_time_ms': result.mapping_time_ms,
                'embedding_time_ms': result.embedding_time_ms,
                'packaging_time_ms': result.packaging_time_ms,
                'elements_processed': result.elements_processed,
                'native_elements': result.native_elements,
                'emf_elements': result.emf_elements,
                'pptx_size_bytes': len(result.output_data),
                'estimated_quality': result.estimated_quality,
            },
        )

        # Write PPTX bytes to file
        output_path = '/tmp/traced_output.pptx'
        with open(output_path, 'wb') as f:
            f.write(result.output_data)

        logger.info(f"  ✅ Conversion successful!")
        logger.info(f"  📦 Output: {output_path} ({len(result.output_data)} bytes)")
        logger.info(f"  ⏱️  Total time: {result.total_time_ms:.2f}ms")
        logger.info(f"  📊 Elements: {result.elements_processed} ({result.native_elements} native, {result.emf_elements} EMF)")
        logger.info(f"  🎯 Quality: {result.estimated_quality:.1%}")
        return output_path

    except Exception as e:
        logger.error(f"  ❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return None


def trace_svg_to_pptx_detailed(svg_content: str, tracer: PipelineTracer):
    """Trace SVG → PPTX conversion with detailed stage logging"""

    # Stage 1: Parse SVG → IR
    tracer.trace_stage("1. PARSE: SVG → IR", svg_content)

    from core.parse.parser import SVGParser
    parser = SVGParser()
    scene_ir, parse_result = parser.parse_to_ir(svg_content)

    tracer.trace_transformation(
        'SVG String',
        'IR SceneGraph',
        {
            'success': parse_result.success,
            'elements': len(scene_ir) if scene_ir else 0,
            'processing_time_ms': parse_result.processing_time_ms,
        },
    )

    if not scene_ir:
        logger.error(f"❌ Parse failed: {parse_result.error}")
        return None

    logger.info(f"  ✅ Parsed {len(scene_ir)} IR elements")
    for i, element in enumerate(scene_ir[:5]):  # Show first 5
        logger.info(f"    [{i}] {type(element).__name__}")

    # Stage 2: Policy Decisions
    tracer.trace_stage("2. POLICY: IR → Decisions", scene_ir)

    from core.policy.engine import PolicyEngine
    from core.ir import Path, TextFrame, Group, Image

    policy_engine = PolicyEngine()
    decisions = []

    for element in scene_ir:
        if isinstance(element, Path):
            decision = policy_engine.decide_path(element)
        elif isinstance(element, TextFrame):
            decision = policy_engine.decide_text(element)
        elif isinstance(element, Group):
            decision = policy_engine.decide_group(element)
        elif isinstance(element, Image):
            decision = policy_engine.decide_image(element)
        else:
            continue

        decisions.append(decision)

        tracer.trace_decision(
            type(element).__name__,
            decision.output_format.value if hasattr(decision.output_format, 'value') else str(decision.output_format),
            decision.reasons[0] if decision.reasons else "no reason",
        )

    logger.info(f"  ✅ Generated {len(decisions)} policy decisions")

    # Stage 3: Map IR → DrawingML
    tracer.trace_stage("3. MAP: IR + Decisions → DrawingML", decisions)

    from core.map import create_path_mapper, create_text_mapper, create_group_mapper, create_image_mapper

    path_mapper = create_path_mapper(policy_engine)
    text_mapper = create_text_mapper(policy_engine)
    group_mapper = create_group_mapper(policy_engine)
    image_mapper = create_image_mapper(policy_engine)

    drawingml_results = []

    for element, decision in zip(scene_ir, decisions):
        try:
            if isinstance(element, Path):
                result = path_mapper.map(element, decision)
            elif isinstance(element, TextFrame):
                result = text_mapper.map(element, decision)
            elif isinstance(element, Group):
                result = group_mapper.map(element, decision)
            elif isinstance(element, Image):
                result = image_mapper.map(element, decision)
            else:
                continue

            drawingml_results.append(result)

            tracer.trace_transformation(
                type(element).__name__,
                'DrawingML XML',
                {
                    'output_format': result.output_format.value if hasattr(result.output_format, 'value') else str(result.output_format),
                    'xml_length': len(result.xml_content),
                    'has_metadata': bool(result.metadata),
                },
            )
        except Exception as e:
            logger.warning(f"  ⚠️  Mapping failed for {type(element).__name__}: {e}")

    logger.info(f"  ✅ Generated {len(drawingml_results)} DrawingML elements")

    # Stage 4: Build PPTX Package
    tracer.trace_stage("4. IO: DrawingML → PPTX", drawingml_results)

    from core.io.package_writer import PackageWriter
    from core.io.slide_builder import SlideBuilder

    slide_builder = SlideBuilder()

    # Build slide XML
    slide_xml = slide_builder.build_slide(drawingml_results)

    tracer.trace_transformation(
        'DrawingML Elements',
        'Slide XML',
        {
            'element_count': len(drawingml_results),
            'xml_length': len(slide_xml),
        },
    )

    # Create PPTX package
    package_writer = PackageWriter()
    pptx_path = '/tmp/traced_output.pptx'

    package_writer.write_package(
        slides=[slide_xml],
        output_path=pptx_path,
    )

    logger.info(f"  ✅ Created PPTX: {pptx_path}")
    tracer.trace_stage("5. OUTPUT: PPTX File", pptx_path)

    return pptx_path


def trace_pptx_to_drive(pptx_path: str, tracer: PipelineTracer):
    """Trace PPTX → Google Drive upload"""

    tracer.trace_stage("6. BATCH: PPTX → Drive Upload", pptx_path)

    try:
        from core.batch.coordinator import BatchCoordinator
        from core.batch.models import BatchJob

        coordinator = BatchCoordinator()

        # Create batch job
        job = BatchJob(
            job_id="trace_job_001",
            status="pending",
            total_files=1,
            drive_integration_enabled=True,
        )

        tracer.trace_transformation(
            'PPTX File',
            'Batch Job',
            {
                'job_id': job.job_id,
                'drive_enabled': job.drive_integration_enabled,
            },
        )

        # Note: Actual upload requires credentials
        logger.info("  ⚠️  Drive upload requires authentication (skipped in trace)")
        logger.info(f"  ℹ️  Job would upload: {pptx_path}")

    except ImportError as e:
        logger.warning(f"  ⚠️  Batch module not available: {e}")


def main():
    """Run complete pipeline trace"""

    logger.info("="*80)
    logger.info("SVG → PPTX → Google Slides Pipeline Tracer")
    logger.info("="*80)

    tracer = PipelineTracer()

    # Example SVG
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
        <rect x="10" y="10" width="180" height="180" fill="#FF6B6B" stroke="#333" stroke-width="2"/>
        <text x="100" y="100" text-anchor="middle" font-size="24" fill="white">Hello PPTX</text>
        <circle cx="50" cy="150" r="30" fill="#4ECDC4"/>
    </svg>'''

    # Trace SVG → PPTX using full pipeline
    pptx_path = trace_svg_to_pptx_full_pipeline(svg_content, tracer)

    if pptx_path:
        # Trace PPTX → Drive (if available)
        trace_pptx_to_drive(pptx_path, tracer)

    # Save trace data
    tracer.save_trace()

    logger.info("\n" + "="*80)
    logger.info("Pipeline Trace Complete!")
    logger.info("="*80)
    logger.info(f"  📄 Detailed log: /tmp/pipeline_trace.log")
    logger.info(f"  📊 Trace data: /tmp/pipeline_trace.json")
    logger.info(f"  📦 Output PPTX: /tmp/traced_output.pptx")


if __name__ == '__main__':
    main()

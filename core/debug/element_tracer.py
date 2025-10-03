#!/usr/bin/env python3
"""
Element Flow Tracer for SVG2PPTX Pipeline

Traces individual elements through the entire pipeline:
Parse → Analyze → IR → Map → Embed → Package

Specifically designed to track filtered elements and verify pipeline compliance.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import json
from datetime import datetime


class PipelineStage(Enum):
    """Pipeline stages"""
    PARSE = "parse"
    ANALYZE = "analyze"
    IR = "ir"
    MAP = "map"
    EMBED = "embed"
    PACKAGE = "package"


class TraceEvent(Enum):
    """Types of trace events"""
    ENTER = "enter"
    EXIT = "exit"
    TRANSFORM = "transform"
    ERROR = "error"
    WARNING = "warning"
    SKIP = "skip"


@dataclass
class TracePoint:
    """Single trace point in element's journey"""
    timestamp: float
    stage: PipelineStage
    event: TraceEvent
    element_id: str
    element_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    filters_applied: List[str] = field(default_factory=list)
    location: str = ""  # file:line
    message: str = ""


@dataclass
class ElementTrace:
    """Complete trace of a single element through pipeline"""
    element_id: str
    svg_tag: str
    has_filter: bool
    filter_ids: List[str] = field(default_factory=list)
    trace_points: List[TracePoint] = field(default_factory=list)

    # Stage summaries
    parse_stage: Optional[Dict] = None
    analyze_stage: Optional[Dict] = None
    ir_stage: Optional[Dict] = None
    map_stage: Optional[Dict] = None
    embed_stage: Optional[Dict] = None
    package_stage: Optional[Dict] = None

    # Pipeline compliance
    pipeline_compliant: bool = True
    violations: List[str] = field(default_factory=list)

    def add_trace_point(self, point: TracePoint):
        """Add trace point and update stage summaries"""
        self.trace_points.append(point)

        # Update stage summary
        stage_key = f"{point.stage.value}_stage"
        if not hasattr(self, stage_key) or getattr(self, stage_key) is None:
            setattr(self, stage_key, {
                'entered': point.timestamp,
                'events': [],
                'duration': 0.0
            })

        stage_summary = getattr(self, stage_key)
        stage_summary['events'].append({
            'event': point.event.value,
            'timestamp': point.timestamp,
            'message': point.message
        })

        # Calculate duration if exiting
        if point.event == TraceEvent.EXIT:
            stage_summary['exited'] = point.timestamp
            stage_summary['duration'] = point.timestamp - stage_summary['entered']

    def check_pipeline_compliance(self):
        """Verify element followed proper pipeline flow"""
        required_stages = [
            PipelineStage.PARSE,
            PipelineStage.IR,
            PipelineStage.MAP
        ]

        visited_stages = set(tp.stage for tp in self.trace_points)

        for stage in required_stages:
            if stage not in visited_stages:
                self.pipeline_compliant = False
                self.violations.append(f"Missing required stage: {stage.value}")

        # Check stage order
        stage_order = [tp.stage for tp in self.trace_points if tp.event == TraceEvent.ENTER]
        expected_order = [s for s in required_stages if s in visited_stages]

        if stage_order[:len(expected_order)] != expected_order:
            self.pipeline_compliant = False
            self.violations.append(f"Stage order violation: {[s.value for s in stage_order]}")

        return self.pipeline_compliant


class ElementTracer:
    """
    Traces elements through the pipeline with special focus on filtered elements.

    Usage:
        tracer = ElementTracer()
        tracer.enable()

        # In parser:
        tracer.trace_parse(element_id, svg_element, ...)

        # In analyzer:
        tracer.trace_analyze(element_id, ...)

        # Generate report:
        report = tracer.generate_report()
    """

    def __init__(self):
        self.enabled = False
        self.traces: Dict[str, ElementTrace] = {}
        self.logger = logging.getLogger(__name__)
        self.start_time = None

        # Statistics
        self.total_elements = 0
        self.filtered_elements = 0
        self.compliant_elements = 0
        self.violations_count = 0

    def enable(self):
        """Enable tracing"""
        self.enabled = True
        self.start_time = datetime.now().timestamp()
        self.logger.info("Element tracer enabled")

    def disable(self):
        """Disable tracing"""
        self.enabled = False
        self.logger.info("Element tracer disabled")

    def _get_element_id(self, element) -> str:
        """Extract or generate element ID"""
        # Try to get ID from element
        if hasattr(element, 'get'):
            elem_id = element.get('id')
            if elem_id:
                return elem_id

        # Generate from type and position
        if hasattr(element, 'tag'):
            tag = element.tag.split('}')[-1] if '}' in str(element.tag) else str(element.tag)
            return f"{tag}_{id(element)}"

        # Fallback to object id
        return f"elem_{id(element)}"

    def _detect_filters(self, element) -> tuple[bool, List[str]]:
        """Detect if element has filters applied"""
        filter_ids = []

        if hasattr(element, 'get'):
            # Check filter attribute
            filter_attr = element.get('filter')
            if filter_attr:
                if filter_attr.startswith('url(#'):
                    filter_ids.append(filter_attr[5:-1])
                else:
                    filter_ids.append(filter_attr)

            # Check style for filter
            style = element.get('style', '')
            if 'filter:' in style:
                # Parse filter from style
                for part in style.split(';'):
                    if 'filter' in part:
                        filter_val = part.split(':')[1].strip()
                        if filter_val.startswith('url(#'):
                            filter_ids.append(filter_val[5:-1])

        return len(filter_ids) > 0, filter_ids

    def trace_parse(self, element, location: str = ""):
        """Trace element entering parse stage"""
        if not self.enabled:
            return

        element_id = self._get_element_id(element)
        has_filter, filter_ids = self._detect_filters(element)

        # Create trace if doesn't exist
        if element_id not in self.traces:
            svg_tag = element.tag.split('}')[-1] if hasattr(element, 'tag') else 'unknown'
            self.traces[element_id] = ElementTrace(
                element_id=element_id,
                svg_tag=svg_tag,
                has_filter=has_filter,
                filter_ids=filter_ids
            )
            self.total_elements += 1
            if has_filter:
                self.filtered_elements += 1

        trace = self.traces[element_id]

        # Add enter event
        trace.add_trace_point(TracePoint(
            timestamp=datetime.now().timestamp(),
            stage=PipelineStage.PARSE,
            event=TraceEvent.ENTER,
            element_id=element_id,
            element_type=trace.svg_tag,
            location=location,
            filters_applied=filter_ids,
            message=f"Parsing {trace.svg_tag} element"
        ))

    def trace_parse_exit(self, element_id: str, ir_element: Any = None):
        """Trace element exiting parse stage"""
        if not self.enabled or element_id not in self.traces:
            return

        trace = self.traces[element_id]

        ir_type = type(ir_element).__name__ if ir_element else 'None'

        trace.add_trace_point(TracePoint(
            timestamp=datetime.now().timestamp(),
            stage=PipelineStage.PARSE,
            event=TraceEvent.EXIT,
            element_id=element_id,
            element_type=trace.svg_tag,
            data={'ir_type': ir_type},
            message=f"Parsed to IR: {ir_type}"
        ))

    def trace_analyze(self, element_id: str, complexity: float = 0.0, location: str = ""):
        """Trace element in analyze stage"""
        if not self.enabled or element_id not in self.traces:
            return

        trace = self.traces[element_id]

        trace.add_trace_point(TracePoint(
            timestamp=datetime.now().timestamp(),
            stage=PipelineStage.ANALYZE,
            event=TraceEvent.ENTER,
            element_id=element_id,
            element_type=trace.svg_tag,
            location=location,
            data={'complexity': complexity},
            message=f"Analyzing element (complexity: {complexity:.2f})"
        ))

    def trace_analyze_exit(self, element_id: str, complexity: float = 0.0, recommendations: list = None):
        """Trace element exiting analyze stage"""
        if not self.enabled or element_id not in self.traces:
            return

        trace = self.traces[element_id]

        trace.add_trace_point(TracePoint(
            timestamp=datetime.now().timestamp(),
            stage=PipelineStage.ANALYZE,
            event=TraceEvent.EXIT,
            element_id=element_id,
            element_type=trace.svg_tag,
            data={'complexity': complexity, 'recommendations': recommendations or []},
            message=f"Analysis complete (complexity: {complexity:.2f})"
        ))

    def trace_ir(self, element_id: str, ir_element: Any, location: str = ""):
        """Trace element in IR stage"""
        if not self.enabled or element_id not in self.traces:
            return

        trace = self.traces[element_id]

        ir_type = type(ir_element).__name__

        # Check for filter in IR element (direct attribute)
        filters_in_ir = []
        if hasattr(ir_element, 'filter') and ir_element.filter:
            filters_in_ir.append(ir_element.filter)

        # Also check metadata for backward compatibility
        if hasattr(ir_element, 'metadata') and ir_element.metadata:
            if 'filter' in ir_element.metadata:
                filter_ref = ir_element.metadata['filter']
                if filter_ref and filter_ref not in filters_in_ir:
                    filters_in_ir.append(filter_ref)

        trace.add_trace_point(TracePoint(
            timestamp=datetime.now().timestamp(),
            stage=PipelineStage.IR,
            event=TraceEvent.ENTER,
            element_id=element_id,
            element_type=ir_type,
            location=location,
            filters_applied=filters_in_ir,
            data={'ir_type': ir_type, 'has_filter_metadata': len(filters_in_ir) > 0},
            message=f"IR element created: {ir_type}"
        ))

    def trace_map(self, element_id: str, mapper_type: str, decision: str = "", location: str = ""):
        """Trace element entering map stage"""
        if not self.enabled or element_id not in self.traces:
            return

        trace = self.traces[element_id]

        trace.add_trace_point(TracePoint(
            timestamp=datetime.now().timestamp(),
            stage=PipelineStage.MAP,
            event=TraceEvent.ENTER,
            element_id=element_id,
            element_type=trace.svg_tag,
            location=location,
            data={'mapper': mapper_type, 'decision': decision},
            message=f"Mapping with {mapper_type} (decision: {decision})"
        ))

    def trace_map_exit(self, element_id: str, output_format: str, output_size: int = 0,
                       filter_applied: bool = False, filter_ref: str = None,
                       mapper_result: Any = None):
        """Trace element exiting map stage"""
        if not self.enabled or element_id not in self.traces:
            return

        trace = self.traces[element_id]

        # Extract filter metadata from mapper result if available
        filters_applied = []
        if mapper_result and hasattr(mapper_result, 'metadata'):
            metadata = mapper_result.metadata
            if metadata.get('filter_applied', False):
                filter_ref = metadata.get('filter')
                if filter_ref:
                    filters_applied.append(filter_ref)
        elif filter_applied and filter_ref:
            filters_applied.append(filter_ref)

        trace.add_trace_point(TracePoint(
            timestamp=datetime.now().timestamp(),
            stage=PipelineStage.MAP,
            event=TraceEvent.EXIT,
            element_id=element_id,
            element_type=trace.svg_tag,
            filters_applied=filters_applied,
            data={
                'output_format': output_format,
                'output_size': output_size,
                'filter_applied': len(filters_applied) > 0,
                'filters': filters_applied
            },
            message=f"Mapped to {output_format} ({output_size} bytes)" +
                    (f" with filters: {', '.join(filters_applied)}" if filters_applied else "")
        ))

    def trace_embed(self, element_id: str, xml_size: int = 0, location: str = ""):
        """Trace element in embed stage"""
        if not self.enabled or element_id not in self.traces:
            return

        trace = self.traces[element_id]

        trace.add_trace_point(TracePoint(
            timestamp=datetime.now().timestamp(),
            stage=PipelineStage.EMBED,
            event=TraceEvent.ENTER,
            element_id=element_id,
            element_type=trace.svg_tag,
            location=location,
            data={'xml_size': xml_size},
            message="Embedding in slide XML"
        ))

    def trace_embed_exit(self, element_id: str, success: bool = True):
        """Trace element exiting embed stage"""
        if not self.enabled or element_id not in self.traces:
            return

        trace = self.traces[element_id]

        trace.add_trace_point(TracePoint(
            timestamp=datetime.now().timestamp(),
            stage=PipelineStage.EMBED,
            event=TraceEvent.EXIT,
            element_id=element_id,
            element_type=trace.svg_tag,
            data={'success': success},
            message=f"Embedding {'successful' if success else 'failed'}"
        ))

    def trace_error(self, element_id: str, stage: PipelineStage, error: str, location: str = ""):
        """Trace error in pipeline"""
        if not self.enabled or element_id not in self.traces:
            return

        trace = self.traces[element_id]
        trace.pipeline_compliant = False
        trace.violations.append(f"Error in {stage.value}: {error}")

        trace.add_trace_point(TracePoint(
            timestamp=datetime.now().timestamp(),
            stage=stage,
            event=TraceEvent.ERROR,
            element_id=element_id,
            element_type=trace.svg_tag,
            location=location,
            message=f"ERROR: {error}"
        ))

    def trace_skip(self, element_id: str, stage: PipelineStage, reason: str, location: str = ""):
        """Trace element being skipped"""
        if not self.enabled or element_id not in self.traces:
            return

        trace = self.traces[element_id]

        trace.add_trace_point(TracePoint(
            timestamp=datetime.now().timestamp(),
            stage=stage,
            event=TraceEvent.SKIP,
            element_id=element_id,
            element_type=trace.svg_tag,
            location=location,
            message=f"SKIPPED: {reason}"
        ))

    def generate_report(self, focus_on_filtered: bool = True) -> Dict[str, Any]:
        """
        Generate comprehensive trace report.

        Args:
            focus_on_filtered: If True, highlight filtered elements

        Returns:
            Report dictionary with statistics and traces
        """
        # Check compliance for all traces
        for trace in self.traces.values():
            trace.check_pipeline_compliance()
            if trace.pipeline_compliant:
                self.compliant_elements += 1
            else:
                self.violations_count += len(trace.violations)

        # Separate filtered and non-filtered elements
        filtered_traces = [t for t in self.traces.values() if t.has_filter]
        unfiltered_traces = [t for t in self.traces.values() if not t.has_filter]

        # Statistics
        stats = {
            'total_elements': self.total_elements,
            'filtered_elements': self.filtered_elements,
            'unfiltered_elements': self.total_elements - self.filtered_elements,
            'compliant_elements': self.compliant_elements,
            'non_compliant_elements': self.total_elements - self.compliant_elements,
            'total_violations': self.violations_count,
            'compliance_rate': self.compliant_elements / self.total_elements if self.total_elements > 0 else 0.0
        }

        # Filter-specific stats
        filter_stats = {}
        for trace in filtered_traces:
            for filter_id in trace.filter_ids:
                if filter_id not in filter_stats:
                    filter_stats[filter_id] = {
                        'count': 0,
                        'compliant': 0,
                        'violations': []
                    }
                filter_stats[filter_id]['count'] += 1
                if trace.pipeline_compliant:
                    filter_stats[filter_id]['compliant'] += 1
                else:
                    filter_stats[filter_id]['violations'].extend(trace.violations)

        report = {
            'summary': stats,
            'filter_statistics': filter_stats,
            'filtered_elements': [self._trace_to_dict(t) for t in filtered_traces],
            'unfiltered_elements': [self._trace_to_dict(t) for t in unfiltered_traces] if not focus_on_filtered else [],
            'violations': [
                {
                    'element_id': t.element_id,
                    'svg_tag': t.svg_tag,
                    'has_filter': t.has_filter,
                    'violations': t.violations
                }
                for t in self.traces.values() if not t.pipeline_compliant
            ]
        }

        return report

    def _trace_to_dict(self, trace: ElementTrace) -> Dict:
        """Convert ElementTrace to dictionary"""
        return {
            'element_id': trace.element_id,
            'svg_tag': trace.svg_tag,
            'has_filter': trace.has_filter,
            'filter_ids': trace.filter_ids,
            'pipeline_compliant': trace.pipeline_compliant,
            'violations': trace.violations,
            'stages': {
                'parse': trace.parse_stage,
                'analyze': trace.analyze_stage,
                'ir': trace.ir_stage,
                'map': trace.map_stage,
                'embed': trace.embed_stage,
                'package': trace.package_stage
            },
            'trace_points': [
                {
                    'timestamp': tp.timestamp,
                    'stage': tp.stage.value,
                    'event': tp.event.value,
                    'location': tp.location,
                    'message': tp.message,
                    'filters_applied': tp.filters_applied,
                    'data': tp.data
                }
                for tp in trace.trace_points
            ]
        }

    def print_report(self, report: Dict = None, verbose: bool = False):
        """Print human-readable report"""
        if report is None:
            report = self.generate_report()

        print("\n" + "="*80)
        print("SVG2PPTX ELEMENT FLOW TRACER REPORT")
        print("="*80)

        stats = report['summary']
        print(f"\n📊 STATISTICS:")
        print(f"   Total elements: {stats['total_elements']}")
        print(f"   Filtered elements: {stats['filtered_elements']}")
        print(f"   Pipeline compliant: {stats['compliant_elements']} ({stats['compliance_rate']*100:.1f}%)")
        print(f"   Violations: {stats['total_violations']}")

        if report['filter_statistics']:
            print(f"\n🎨 FILTER STATISTICS:")
            for filter_id, fstats in report['filter_statistics'].items():
                print(f"   {filter_id}:")
                print(f"      Elements: {fstats['count']}")
                print(f"      Compliant: {fstats['compliant']}/{fstats['count']}")

        if report['violations']:
            print(f"\n⚠️  PIPELINE VIOLATIONS:")
            for violation in report['violations']:
                print(f"   {violation['element_id']} ({violation['svg_tag']}):")
                for v in violation['violations']:
                    print(f"      - {v}")

        if verbose and report['filtered_elements']:
            print(f"\n🔍 FILTERED ELEMENT TRACES:")
            for trace in report['filtered_elements'][:5]:  # Show first 5
                print(f"\n   {trace['element_id']} ({trace['svg_tag']}) - Filters: {trace['filter_ids']}")
                print(f"   Compliant: {'✅' if trace['pipeline_compliant'] else '❌'}")
                for tp in trace['trace_points']:
                    print(f"      [{tp['stage']}] {tp['event']}: {tp['message']}")

        print("\n" + "="*80)

    def save_report(self, filename: str, report: Dict = None):
        """Save report to JSON file"""
        if report is None:
            report = self.generate_report()

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Trace report saved to {filename}")


# Global tracer instance
_global_tracer: Optional[ElementTracer] = None


def get_tracer() -> ElementTracer:
    """Get global tracer instance"""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = ElementTracer()
    return _global_tracer


def enable_tracing():
    """Enable global tracing"""
    get_tracer().enable()


def disable_tracing():
    """Disable global tracing"""
    get_tracer().disable()

#!/usr/bin/env python3
"""
Performance Test for Text Mapper XML Generation

Measures performance of text XML generation before and after template conversion.
"""

import time
import statistics
from typing import List, Dict, Any
from lxml import etree as ET

def create_mock_text_element():
    """Create a mock text element for testing."""
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class MockBBox:
        x: float = 100.0
        y: float = 200.0
        width: float = 500.0
        height: float = 100.0

    @dataclass
    class MockTextFrame:
        content: str = "Sample text content for performance testing"
        font_family: str = "Arial"
        font_size: float = 12.0
        opacity: float = 1.0
        fill: Optional[Any] = None
        stroke: Optional[Any] = None
        clip: Optional[Any] = None

        def __post_init__(self):
            self.bbox = MockBBox()

    return MockTextFrame()

def benchmark_text_xml_generation_current(iterations: int = 1000) -> List[float]:
    """Benchmark current f-string XML generation approach."""
    times = []
    text_element = create_mock_text_element()

    for _ in range(iterations):
        start_time = time.perf_counter()

        # Simulate current f-string XML generation (from text mapper analysis)
        bbox = text_element.bbox
        x_emu = int(bbox.x * 12700)
        y_emu = int(bbox.y * 12700)
        width_emu = int(bbox.width * 12700)
        height_emu = int(bbox.height * 12700)

        # F-string XML generation (current approach)
        xml_content = f"""<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="1" name="Text"/>
        <p:cNvSpPr txBox="1"/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{width_emu}" cy="{height_emu}"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
    </p:spPr>
    <p:txBody>
        <a:bodyPr wrap="square" rtlCol="0">
            <a:spAutoFit/>
        </a:bodyPr>
        <a:lstStyle/>
        <a:p>
            <a:r>
                <a:rPr lang="en-US" sz="{int(text_element.font_size * 100)}" b="0" i="0">
                    <a:solidFill>
                        <a:srgbClr val="000000"/>
                    </a:solidFill>
                    <a:latin typeface="{text_element.font_family}"/>
                </a:rPr>
                <a:t>{text_element.content}</a:t>
            </a:r>
        </a:p>
    </p:txBody>
</p:sp>"""

        # Simulate validation by parsing the XML
        try:
            root = ET.fromstring(xml_content)
            assert root.tag.endswith('sp')
        except ET.XMLSyntaxError:
            pass  # Ignore parsing errors for benchmark

        end_time = time.perf_counter()
        times.append(end_time - start_time)

    return times

def benchmark_text_xml_generation_template(iterations: int = 1000) -> List[float]:
    """Benchmark actual template-based XML generation approach."""
    import sys
    sys.path.append('/Users/ynse/projects/svg2pptx')

    try:
        from core.utils.enhanced_xml_builder import EnhancedXMLBuilder
        builder = EnhancedXMLBuilder()

        times = []
        text_element = create_mock_text_element()

        for _ in range(iterations):
            start_time = time.perf_counter()

            # Use actual template-based generation
            bbox = text_element.bbox
            x_emu = int(bbox.x * 12700)
            y_emu = int(bbox.y * 12700)
            width_emu = int(bbox.width * 12700)
            height_emu = int(bbox.height * 12700)

            # Generate paragraph XML using template
            paragraph_element = builder.generate_text_paragraph(
                runs_xml=f"""<a:r>
                    <a:rPr lang="en-US" sz="{int(text_element.font_size * 100)}" b="0" i="0">
                        <a:solidFill>
                            <a:srgbClr val="000000"/>
                        </a:solidFill>
                        <a:latin typeface="{text_element.font_family}"/>
                    </a:rPr>
                    <a:t>{text_element.content}</a:t>
                </a:r>"""
            )
            paragraphs_xml = builder.element_to_string(paragraph_element)

            # Generate text shape using template
            text_shape_element = builder.generate_text_shape(
                text_id=1,
                x_emu=x_emu,
                y_emu=y_emu,
                width_emu=width_emu,
                height_emu=height_emu,
                paragraphs_xml=paragraphs_xml
            )

            # Convert to string
            xml_content = builder.element_to_string(text_shape_element)

            end_time = time.perf_counter()
            times.append(end_time - start_time)

        return times

    except ImportError as e:
        print(f"Could not import EnhancedXMLBuilder: {e}")
        print("Falling back to simulation...")

        # Fallback to simulation
        times = []
        text_element = create_mock_text_element()

        for _ in range(iterations):
            start_time = time.perf_counter()

            # Simple template simulation
            template_base = """<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:nvSpPr>
    <p:cNvPr id="1" name="TextFrame"/>
    <p:cNvSpPr txBox="1"/>
    <p:nvPr/>
  </p:nvSpPr>
  <p:spPr>
    <a:xfrm>
      <a:off x="0" y="0"/>
      <a:ext cx="1" cy="1"/>
    </a:xfrm>
    <a:prstGeom prst="rect">
      <a:avLst/>
    </a:prstGeom>
    <a:noFill/>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="none" rtlCol="0">
      <a:spAutoFit/>
    </a:bodyPr>
    <a:lstStyle/>
  </p:txBody>
</p:sp>"""

            bbox = text_element.bbox
            x_emu = int(bbox.x * 12700)
            y_emu = int(bbox.y * 12700)
            width_emu = int(bbox.width * 12700)
            height_emu = int(bbox.height * 12700)

            xml_content = template_base.replace('x="0"', f'x="{x_emu}"')
            xml_content = xml_content.replace('y="0"', f'y="{y_emu}"')
            xml_content = xml_content.replace('cx="1"', f'cx="{width_emu}"')
            xml_content = xml_content.replace('cy="1"', f'cy="{height_emu}"')

            end_time = time.perf_counter()
            times.append(end_time - start_time)

        return times

def analyze_performance_results(name: str, times: List[float]) -> Dict[str, float]:
    """Analyze performance results and return statistics."""
    return {
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0,
        'min': min(times),
        'max': max(times),
        'total': sum(times),
        'ops_per_second': len(times) / sum(times)
    }

def main():
    """Run performance comparison."""
    print("🚀 Text XML Generation Performance Comparison")
    print("=" * 60)

    iterations = 1000
    print(f"Running {iterations} iterations for each approach...\n")

    # Baseline: Current f-string approach
    print("📊 Measuring BASELINE (f-string XML generation)...")
    baseline_times = benchmark_text_xml_generation_current(iterations)
    baseline_stats = analyze_performance_results("F-String", baseline_times)

    print(f"✓ F-String Approach:")
    print(f"  Mean time: {baseline_stats['mean']:.6f}s")
    print(f"  Median time: {baseline_stats['median']:.6f}s")
    print(f"  Std deviation: {baseline_stats['stdev']:.6f}s")
    print(f"  Operations/sec: {baseline_stats['ops_per_second']:.1f}")

    # Template-based approach (simulated)
    print(f"\n📊 Measuring TEMPLATE-BASED (DOM manipulation)...")
    template_times = benchmark_text_xml_generation_template(iterations)
    template_stats = analyze_performance_results("Template", template_times)

    print(f"✓ Template Approach:")
    print(f"  Mean time: {template_stats['mean']:.6f}s")
    print(f"  Median time: {template_stats['median']:.6f}s")
    print(f"  Std deviation: {template_stats['stdev']:.6f}s")
    print(f"  Operations/sec: {template_stats['ops_per_second']:.1f}")

    # Performance comparison
    print(f"\n🏁 PERFORMANCE COMPARISON:")
    print("=" * 40)

    speedup = template_stats['ops_per_second'] / baseline_stats['ops_per_second']
    time_reduction = (baseline_stats['mean'] - template_stats['mean']) / baseline_stats['mean'] * 100

    print(f"Speedup factor: {speedup:.2f}x")
    print(f"Time reduction: {time_reduction:.1f}%")

    if speedup > 1.0:
        print(f"🎉 Template approach is {speedup:.2f}x FASTER!")
    else:
        print(f"⚠️  Template approach is {1/speedup:.2f}x slower")

    print(f"\nBaseline: {baseline_stats['ops_per_second']:.1f} ops/sec")
    print(f"Template: {template_stats['ops_per_second']:.1f} ops/sec")

    return {
        'baseline': baseline_stats,
        'template': template_stats,
        'speedup': speedup,
        'time_reduction_percent': time_reduction
    }

if __name__ == "__main__":
    results = main()
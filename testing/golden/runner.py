#!/usr/bin/env python3
"""
Golden Test Runner

Practical implementation that demonstrates A/B testing between
legacy and clean architecture implementations.
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Callable

from .framework import GoldenTestRunner, GoldenTestCase
from .comparators import PPTXComparator, XMLStructureComparator, PerformanceComparator, MetricsComparator
from .baselines import BaselineManager, BaselineStrategy


def create_sample_test_cases() -> List[GoldenTestCase]:
    """Create sample test cases for demonstration."""
    test_cases = []

    # Basic shapes
    test_cases.append(GoldenTestCase(
        name="basic_rectangle",
        svg_content='''<svg width="100" height="50" xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="80" height="30" fill="blue" stroke="black" stroke-width="2"/>
        </svg>''',
        expected_elements=1,
        description="Simple rectangle with fill and stroke",
        tags=["basic", "shapes", "rectangle"],
        complexity_score=5
    ))

    test_cases.append(GoldenTestCase(
        name="basic_circle",
        svg_content='''<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="40" fill="red" opacity="0.7"/>
        </svg>''',
        expected_elements=1,
        description="Circle with opacity",
        tags=["basic", "shapes", "circle"],
        complexity_score=6
    ))

    # Text
    test_cases.append(GoldenTestCase(
        name="simple_text",
        svg_content='''<svg width="200" height="60" xmlns="http://www.w3.org/2000/svg">
            <text x="10" y="30" font-family="Arial" font-size="16" fill="black">Hello World</text>
        </svg>''',
        expected_elements=1,
        description="Simple text element",
        tags=["text", "basic"],
        complexity_score=8
    ))

    # Complex text (triggers documented fixes)
    test_cases.append(GoldenTestCase(
        name="complex_text_anchor",
        svg_content='''<svg width="200" height="100" xmlns="http://www.w3.org/2000/svg">
            <text x="100" y="30" text-anchor="middle" font-family="Arial" font-size="14" fill="blue">
                Centered Text
                <tspan x="100" y="50" fill="red" font-weight="bold">Bold Line</tspan>
                <tspan x="100" y="70" font-style="italic">Italic Line</tspan>
            </text>
        </svg>''',
        expected_elements=1,
        description="Complex text with anchor and tspan styling (tests documented fixes)",
        tags=["text", "complex", "anchor", "tspan"],
        complexity_score=15
    ))

    # Paths
    test_cases.append(GoldenTestCase(
        name="simple_path",
        svg_content='''<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
            <path d="M 10 10 L 90 10 L 90 90 L 10 90 Z" fill="green" stroke="darkgreen"/>
        </svg>''',
        expected_elements=1,
        description="Simple path with lines",
        tags=["paths", "basic"],
        complexity_score=10
    ))

    # Arc path (tests a2c conversion)
    test_cases.append(GoldenTestCase(
        name="arc_path",
        svg_content='''<svg width="120" height="120" xmlns="http://www.w3.org/2000/svg">
            <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="purple" stroke-width="3"/>
        </svg>''',
        expected_elements=1,
        description="Path with arc command (tests a2c conversion)",
        tags=["paths", "arcs", "complex"],
        complexity_score=20
    ))

    # Gradients
    test_cases.append(GoldenTestCase(
        name="linear_gradient",
        svg_content='''<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
                    <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
                </linearGradient>
            </defs>
            <rect width="100" height="100" fill="url(#grad1)" />
        </svg>''',
        expected_elements=1,
        description="Rectangle with linear gradient",
        tags=["gradients", "complex"],
        complexity_score=25
    ))

    return test_cases


def mock_legacy_converter(svg_content: str) -> bytes:
    """
    Mock legacy converter for demonstration.

    In real usage, this would call the existing SVG2PPTX system.
    """
    # Simulate legacy conversion delay
    time.sleep(0.01)

    # Create mock PPTX-like output
    mock_pptx = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <p:cSld>
        <p:spTree>
            <!-- Legacy output for: {len(svg_content)} chars -->
            <p:sp>
                <p:nvSpPr><p:cNvPr id="2" name="Legacy_Shape"/></p:nvSpPr>
                <p:spPr>
                    <a:xfrm><a:off x="914400" y="685800"/><a:ext cx="1828800" cy="685800"/></a:xfrm>
                    <a:prstGeom prst="rect"/>
                    <a:solidFill><a:srgbClr val="0000FF"/></a:solidFill>
                </p:spPr>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>""".encode('utf-8')

    return mock_pptx


def mock_clean_converter(svg_content: str) -> bytes:
    """
    Mock clean architecture converter for demonstration.

    In real usage, this would call the new clean architecture pipeline.
    """
    # Simulate clean conversion (slightly faster)
    time.sleep(0.008)

    # Create mock PPTX-like output (slightly different for testing)
    mock_pptx = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <p:cSld>
        <p:spTree>
            <!-- Clean output for: {len(svg_content)} chars -->
            <p:sp>
                <p:nvSpPr><p:cNvPr id="2" name="Clean_Shape"/></p:nvSpPr>
                <p:spPr>
                    <a:xfrm><a:off x="914400" y="685800"/><a:ext cx="1828800" cy="685800"/></a:xfrm>
                    <a:prstGeom prst="rect"/>
                    <a:solidFill><a:srgbClr val="0000FF"/></a:solidFill>
                </p:spPr>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>""".encode('utf-8')

    return mock_pptx


def run_golden_test_demo(output_dir: Path = None) -> Dict[str, Any]:
    """
    Demonstrate the golden test framework.

    Args:
        output_dir: Directory for test outputs and baselines

    Returns:
        Test results summary
    """
    if output_dir is None:
        output_dir = Path("testing/golden/demo_results")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(output_dir / "golden_test.log"),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Golden Test Framework demonstration")

    # Create test runner
    runner = GoldenTestRunner(
        legacy_converter=mock_legacy_converter,
        clean_converter=mock_clean_converter,
        baseline_dir=output_dir / "baselines"
    )

    # Add comparators
    runner.add_comparator(PPTXComparator(ignore_timestamps=True))
    runner.add_comparator(XMLStructureComparator(normalize_whitespace=True))
    runner.add_comparator(PerformanceComparator(time_tolerance_percent=15.0))
    runner.add_comparator(MetricsComparator())

    # Create test cases
    test_cases = create_sample_test_cases()
    logger.info(f"Created {len(test_cases)} test cases")

    # Run test suite
    logger.info("Running golden test suite...")
    results = runner.run_test_suite(test_cases, max_failures=20)

    # Generate detailed report
    report_path = output_dir / "golden_test_report.html"
    generate_html_report(results, test_cases, report_path)

    logger.info(f"Golden test completed: {results['pass_rate']:.1%} pass rate")
    logger.info(f"Detailed report: {report_path}")

    return results


def generate_html_report(results: Dict[str, Any], test_cases: List[GoldenTestCase],
                        output_path: Path) -> None:
    """Generate HTML report of golden test results."""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Golden Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        .skip {{ color: orange; }}
        .error {{ color: darkred; }}
        .test-case {{ border: 1px solid #ddd; margin: 10px 0; padding: 10px; border-radius: 5px; }}
        .metrics {{ font-family: monospace; font-size: 12px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Golden Test Framework Report</h1>

    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Tests:</strong> {results['total_tests']}</p>
        <p><strong>Pass Rate:</strong> {results['pass_rate']:.1%}</p>
        <p><strong>Passed:</strong> <span class="pass">{results['passed']}</span></p>
        <p><strong>Failed:</strong> <span class="fail">{results['failed']}</span></p>
        <p><strong>Skipped:</strong> <span class="skip">{results['skipped']}</span></p>
        <p><strong>Errors:</strong> <span class="error">{results['errors']}</span></p>
        <p><strong>Duration:</strong> {results['duration_sec']:.2f} seconds</p>
        <p><strong>Avg Test Duration:</strong> {results['avg_test_duration']:.3f} seconds</p>
    </div>

    <h2>Results by Comparison Type</h2>
    <table>
        <tr><th>Comparison Type</th><th>Pass</th><th>Fail</th><th>Skip</th><th>Error</th></tr>
"""

    for comp_type, counts in results['by_comparison_type'].items():
        html_content += f"""
        <tr>
            <td>{comp_type}</td>
            <td class="pass">{counts['pass']}</td>
            <td class="fail">{counts['fail']}</td>
            <td class="skip">{counts['skip']}</td>
            <td class="error">{counts['error']}</td>
        </tr>
"""

    html_content += """
    </table>

    <h2>Test Cases</h2>
"""

    for test_case in test_cases:
        html_content += f"""
    <div class="test-case">
        <h3>{test_case.name}</h3>
        <p><strong>Description:</strong> {test_case.description}</p>
        <p><strong>Tags:</strong> {', '.join(test_case.tags)}</p>
        <p><strong>Complexity:</strong> {test_case.complexity_score}</p>
        <details>
            <summary>SVG Content</summary>
            <pre>{test_case.svg_content}</pre>
        </details>
    </div>
"""

    if results['worst_failures']:
        html_content += """
    <h2>Worst Failures</h2>
    <table>
        <tr><th>Test Name</th><th>Comparison Type</th><th>Differences</th><th>Error</th></tr>
"""
        for failure in results['worst_failures']:
            html_content += f"""
        <tr>
            <td>{failure['name']}</td>
            <td>{failure['type']}</td>
            <td>{failure['difference_count']}</td>
            <td>{failure.get('error', 'N/A')}</td>
        </tr>
"""
        html_content += "</table>"

    html_content += """
    <footer>
        <p><em>Generated by SVG2PPTX Golden Test Framework</em></p>
    </footer>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


if __name__ == "__main__":
    # Run demonstration
    demo_results = run_golden_test_demo()

    print("\n" + "="*60)
    print("GOLDEN TEST FRAMEWORK DEMONSTRATION")
    print("="*60)
    print(f"Pass Rate: {demo_results['pass_rate']:.1%}")
    print(f"Total Tests: {demo_results['total_tests']}")
    print(f"Duration: {demo_results['duration_sec']:.2f} seconds")
    print("="*60)
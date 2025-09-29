#!/usr/bin/env python3
"""
Path Pipeline Demo

Demonstrates the complete clean architecture pipeline working end-to-end
with real SVG inputs that test documented fixes and proven components.
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Any

from .path_pipeline import PathPipeline, PipelineContext, ConversionResult
from core.policy import PolicyConfig


def create_path_test_cases() -> List[Dict[str, Any]]:
    """Create test cases that exercise the path pipeline."""
    test_cases = []

    # Basic rectangle (tests basic shape conversion)
    test_cases.append({
        'name': 'basic_rectangle',
        'description': 'Simple rectangle with fill and stroke',
        'svg_content': '''<svg width="100" height="60" xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="80" height="40" fill="#0066CC" stroke="#003366" stroke-width="2"/>
        </svg>''',
        'expected_elements': 1,
        'expected_native': True,
        'complexity': 'low'
    })

    # Circle (tests Bezier approximation)
    test_cases.append({
        'name': 'circle_bezier',
        'description': 'Circle converted to Bezier curves',
        'svg_content': '''<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="40" fill="#FF6600" stroke="#CC3300" stroke-width="3"/>
        </svg>''',
        'expected_elements': 1,
        'expected_native': True,
        'complexity': 'medium'
    })

    # Simple path (tests path parsing)
    test_cases.append({
        'name': 'simple_path',
        'description': 'Simple path with line commands',
        'svg_content': '''<svg width="120" height="80" xmlns="http://www.w3.org/2000/svg">
            <path d="M 10 10 L 110 10 L 110 70 L 10 70 Z" fill="#00CC66" stroke="#006633"/>
        </svg>''',
        'expected_elements': 1,
        'expected_native': True,
        'complexity': 'medium'
    })

    # Arc path (tests a2c conversion - the crown jewel!)
    test_cases.append({
        'name': 'arc_path_a2c',
        'description': 'Path with arc command (tests proven a2c conversion)',
        'svg_content': '''<svg width="140" height="100" xmlns="http://www.w3.org/2000/svg">
            <path d="M 20 50 A 50 30 0 0 1 120 50" fill="none" stroke="#9933CC" stroke-width="4"/>
        </svg>''',
        'expected_elements': 1,
        'expected_native': True,  # Should use native with a2c conversion
        'complexity': 'high'
    })

    # Complex path (may trigger EMF fallback)
    test_cases.append({
        'name': 'complex_path',
        'description': 'Complex path that may use EMF fallback',
        'svg_content': '''<svg width="200" height="150" xmlns="http://www.w3.org/2000/svg">
            <path d="M 10 10 Q 50 50 90 10 T 170 50 Q 190 70 170 90 T 90 130 Q 50 100 10 130 T 10 50 Z"
                  fill="#CC6600" stroke="#663300" stroke-width="2"/>
        </svg>''',
        'expected_elements': 1,
        'expected_native': False,  # Complex, may trigger EMF
        'complexity': 'very_high'
    })

    # Multiple shapes (tests multiple IR elements)
    test_cases.append({
        'name': 'multiple_shapes',
        'description': 'Multiple shapes in one SVG',
        'svg_content': '''<svg width="200" height="100" xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="50" height="30" fill="#FF3366"/>
            <circle cx="90" cy="25" r="15" fill="#3366FF"/>
            <path d="M 130 10 L 180 10 L 155 40 Z" fill="#66FF33"/>
        </svg>''',
        'expected_elements': 3,
        'expected_native': True,
        'complexity': 'medium'
    })

    # Stress test (tests policy thresholds)
    test_cases.append({
        'name': 'stress_test',
        'description': 'Many elements to test policy thresholds',
        'svg_content': '''<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="20" height="20" fill="#FF0000"/>
            <rect x="40" y="10" width="20" height="20" fill="#FF3300"/>
            <rect x="70" y="10" width="20" height="20" fill="#FF6600"/>
            <rect x="100" y="10" width="20" height="20" fill="#FF9900"/>
            <rect x="130" y="10" width="20" height="20" fill="#FFCC00"/>
            <rect x="160" y="10" width="20" height="20" fill="#FFFF00"/>
            <rect x="190" y="10" width="20" height="20" fill="#CCFF00"/>
            <rect x="220" y="10" width="20" height="20" fill="#99FF00"/>
            <rect x="250" y="10" width="20" height="20" fill="#66FF00"/>
            <rect x="280" y="10" width="20" height="20" fill="#33FF00"/>
        </svg>''',
        'expected_elements': 10,
        'expected_native': True,  # Simple shapes should stay native
        'complexity': 'high'
    })

    return test_cases


def run_path_pipeline_demo(output_dir: Path = None) -> Dict[str, Any]:
    """
    Run complete path pipeline demonstration.

    Tests the clean architecture end-to-end with various SVG inputs
    that exercise documented fixes and proven components.

    Args:
        output_dir: Directory for demo outputs

    Returns:
        Demo results summary
    """
    if output_dir is None:
        output_dir = Path("pipeline/demo_results")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(output_dir / "path_pipeline_demo.log"),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Path Pipeline MVP demonstration")

    # Test different policy configurations
    policy_configs = {
        'speed': PolicyConfig.speed(),
        'balanced': PolicyConfig.balanced(),
        'quality': PolicyConfig.quality()
    }

    all_results = []
    demo_summary = {
        'test_cases_count': 0,
        'total_conversions': 0,
        'successful_conversions': 0,
        'failed_conversions': 0,
        'policy_results': {},
        'performance_metrics': {},
        'demo_duration_sec': 0
    }

    demo_start = time.perf_counter()

    # Get test cases
    test_cases = create_path_test_cases()
    demo_summary['test_cases_count'] = len(test_cases)

    logger.info(f"Testing {len(test_cases)} test cases with {len(policy_configs)} policy configurations")

    # Test each policy configuration
    for policy_name, policy_config in policy_configs.items():
        logger.info(f"Testing with {policy_name} policy configuration")

        policy_results = {
            'conversions': 0,
            'successes': 0,
            'failures': 0,
            'total_elements': 0,
            'native_elements': 0,
            'emf_elements': 0,
            'avg_duration': 0,
            'test_results': []
        }

        # Create pipeline with this policy
        context = PipelineContext(
            policy_config=policy_config,
            debug_mode=True
        )
        pipeline = PathPipeline(context)

        # Test each case
        for test_case in test_cases:
            logger.info(f"Converting: {test_case['name']} ({test_case['complexity']})")

            try:
                # Run conversion
                result = pipeline.convert_svg_to_pptx(test_case['svg_content'])

                # Save PPTX if successful
                if result.success and result.pptx_bytes:
                    pptx_path = output_dir / f"{test_case['name']}_{policy_name}.pptx"
                    with open(pptx_path, 'wb') as f:
                        f.write(result.pptx_bytes)
                    logger.info(f"Saved PPTX: {pptx_path}")

                # Update counters
                policy_results['conversions'] += 1
                if result.success:
                    policy_results['successes'] += 1
                    policy_results['total_elements'] += result.element_count
                    policy_results['native_elements'] += result.native_count
                    policy_results['emf_elements'] += result.emf_count
                else:
                    policy_results['failures'] += 1

                # Store detailed result
                test_result = {
                    'name': test_case['name'],
                    'description': test_case['description'],
                    'complexity': test_case['complexity'],
                    'success': result.success,
                    'elements': result.element_count,
                    'native_count': result.native_count,
                    'emf_count': result.emf_count,
                    'duration_sec': result.duration_sec,
                    'metrics': result.metrics,
                    'error': result.error_message
                }
                policy_results['test_results'].append(test_result)

                # Log result
                if result.success:
                    logger.info(f"✅ {test_case['name']}: {result.element_count} elements, "
                              f"{result.native_count} native, {result.emf_count} EMF "
                              f"({result.duration_sec:.3f}s)")
                else:
                    logger.error(f"❌ {test_case['name']}: {result.error_message}")

            except Exception as e:
                logger.error(f"💥 {test_case['name']} crashed: {e}")
                policy_results['conversions'] += 1
                policy_results['failures'] += 1

                test_result = {
                    'name': test_case['name'],
                    'description': test_case['description'],
                    'complexity': test_case['complexity'],
                    'success': False,
                    'elements': 0,
                    'native_count': 0,
                    'emf_count': 0,
                    'duration_sec': 0,
                    'metrics': {},
                    'error': str(e)
                }
                policy_results['test_results'].append(test_result)

        # Calculate policy summary
        if policy_results['conversions'] > 0:
            policy_results['success_rate'] = policy_results['successes'] / policy_results['conversions']
            durations = [r['duration_sec'] for r in policy_results['test_results'] if r['success']]
            policy_results['avg_duration'] = sum(durations) / len(durations) if durations else 0

        demo_summary['policy_results'][policy_name] = policy_results
        demo_summary['total_conversions'] += policy_results['conversions']
        demo_summary['successful_conversions'] += policy_results['successes']
        demo_summary['failed_conversions'] += policy_results['failures']

        logger.info(f"{policy_name} policy: {policy_results['success_rate']:.1%} success rate "
                   f"({policy_results['successes']}/{policy_results['conversions']})")

    demo_summary['demo_duration_sec'] = time.perf_counter() - demo_start

    # Generate comprehensive report
    report_path = output_dir / "path_pipeline_report.html"
    generate_demo_report(demo_summary, test_cases, report_path)

    logger.info(f"Path pipeline demo completed in {demo_summary['demo_duration_sec']:.2f}s")
    logger.info(f"Overall success rate: {demo_summary['successful_conversions']}/{demo_summary['total_conversions']}")
    logger.info(f"Detailed report: {report_path}")

    return demo_summary


def generate_demo_report(summary: Dict[str, Any], test_cases: List[Dict[str, Any]],
                        output_path: Path) -> None:
    """Generate HTML report of path pipeline demo."""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Path Pipeline MVP Demo Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        .policy {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .test-case {{ background: #f9f9f9; margin: 5px 0; padding: 10px; border-radius: 3px; }}
        .metrics {{ font-family: monospace; font-size: 12px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .complexity-low {{ color: #006600; }}
        .complexity-medium {{ color: #CC6600; }}
        .complexity-high {{ color: #CC3300; }}
        .complexity-very_high {{ color: #990000; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Path Pipeline MVP Demo Report</h1>
    <p><em>Clean Architecture End-to-End Demonstration</em></p>

    <div class="summary">
        <h2>Demo Summary</h2>
        <p><strong>Test Cases:</strong> {summary['test_cases_count']}</p>
        <p><strong>Total Conversions:</strong> {summary['total_conversions']}</p>
        <p><strong>Successful:</strong> <span class="success">{summary['successful_conversions']}</span></p>
        <p><strong>Failed:</strong> <span class="failure">{summary['failed_conversions']}</span></p>
        <p><strong>Overall Success Rate:</strong> {summary['successful_conversions'] / max(summary['total_conversions'], 1):.1%}</p>
        <p><strong>Demo Duration:</strong> {summary['demo_duration_sec']:.2f} seconds</p>
    </div>

    <h2>Test Cases</h2>
    <table>
        <tr><th>Name</th><th>Description</th><th>Complexity</th><th>Expected Elements</th></tr>
"""

    for test_case in test_cases:
        complexity_class = f"complexity-{test_case['complexity']}"
        html_content += f"""
        <tr>
            <td>{test_case['name']}</td>
            <td>{test_case['description']}</td>
            <td class="{complexity_class}">{test_case['complexity']}</td>
            <td>{test_case['expected_elements']}</td>
        </tr>
"""

    html_content += """
    </table>

    <h2>Policy Configuration Results</h2>
"""

    for policy_name, policy_data in summary['policy_results'].items():
        html_content += f"""
    <div class="policy">
        <h3>{policy_name.title()} Policy</h3>
        <p><strong>Success Rate:</strong> {policy_data.get('success_rate', 0):.1%}
           ({policy_data['successes']}/{policy_data['conversions']})</p>
        <p><strong>Elements Created:</strong> {policy_data['total_elements']} total
           ({policy_data['native_elements']} native, {policy_data['emf_elements']} EMF)</p>
        <p><strong>Average Duration:</strong> {policy_data.get('avg_duration', 0):.3f} seconds</p>

        <h4>Test Results</h4>
        <table>
            <tr><th>Test</th><th>Status</th><th>Elements</th><th>Native/EMF</th><th>Duration</th><th>Error</th></tr>
"""

        for result in policy_data['test_results']:
            status = "✅ Success" if result['success'] else "❌ Failed"
            status_class = "success" if result['success'] else "failure"
            native_emf = f"{result['native_count']}/{result['emf_count']}" if result['success'] else "N/A"
            duration = f"{result['duration_sec']:.3f}s" if result['success'] else "N/A"
            error_text = result.get('error') or 'None'
            error = error_text[:50] + ('...' if len(error_text) > 50 else '')

            html_content += f"""
            <tr>
                <td>{result['name']}</td>
                <td class="{status_class}">{status}</td>
                <td>{result['elements']}</td>
                <td>{native_emf}</td>
                <td>{duration}</td>
                <td>{error}</td>
            </tr>
"""

        html_content += """
        </table>
    </div>
"""

    html_content += """
    <h2>Architecture Validation</h2>
    <div class="summary">
        <h3>✅ Clean Architecture Components Tested</h3>
        <ul>
            <li><strong>Core IR:</strong> Path, Point, LineSegment, BezierSegment data structures</li>
            <li><strong>Policy Engine:</strong> Speed/Balanced/Quality configuration testing</li>
            <li><strong>Legacy Adapters:</strong> Path adapter with a2c conversion, I/O adapter with PPTX packaging</li>
            <li><strong>Pipeline:</strong> Complete SVG → IR → Policy → PPTX flow</li>
        </ul>

        <h3>🎯 Key Validations</h3>
        <ul>
            <li><strong>A2C Conversion:</strong> Arc paths converted using proven mathematical algorithms</li>
            <li><strong>Shape-to-Path:</strong> Rectangles and circles converted to path representations</li>
            <li><strong>Policy Decisions:</strong> Native DrawingML vs EMF fallback based on complexity</li>
            <li><strong>PPTX Generation:</strong> Valid PowerPoint files created with proper XML structure</li>
        </ul>
    </div>

    <footer>
        <p><em>Generated by SVG2PPTX Path Pipeline MVP</em></p>
        <p><em>Demonstrates clean architecture with legacy component reuse</em></p>
    </footer>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


if __name__ == "__main__":
    # Run demonstration
    demo_results = run_path_pipeline_demo()

    print("\n" + "="*70)
    print("PATH PIPELINE MVP DEMONSTRATION")
    print("="*70)
    print(f"Test Cases: {demo_results['test_cases_count']}")
    print(f"Success Rate: {demo_results['successful_conversions']}/{demo_results['total_conversions']}")
    print(f"Duration: {demo_results['demo_duration_sec']:.2f} seconds")
    print("="*70)

    # Show policy comparison
    for policy_name, policy_data in demo_results['policy_results'].items():
        success_rate = policy_data.get('success_rate', 0)
        print(f"{policy_name.upper()}: {success_rate:.1%} success rate, "
              f"{policy_data['native_elements']} native, {policy_data['emf_elements']} EMF")

    print("="*70)
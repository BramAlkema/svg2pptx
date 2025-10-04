#!/usr/bin/env python3
"""
SVG Analysis API Examples

Demonstrates using the svg2pptx analysis endpoints for:
- SVG complexity analysis and policy recommendations
- SVG validation and compatibility checking
- Feature support queries

Requirements:
    pip install requests

Usage:
    python examples/api/analyze_svg.py
"""

import requests
import json
from pathlib import Path

# API Configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key-here"  # Replace with your actual API key

# Setup session with authentication
session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
})


def analyze_svg_content(svg_content: str) -> dict:
    """
    Analyze SVG complexity and get policy recommendations.

    Args:
        svg_content: SVG XML content as string

    Returns:
        Analysis result with complexity score, features, and recommendations
    """
    endpoint = f"{API_BASE_URL}/analyze/svg"

    payload = {
        "svg_content": svg_content,
        "analyze_depth": "detailed"
    }

    response = session.post(endpoint, json=payload)
    response.raise_for_status()

    return response.json()


def analyze_svg_file(svg_file_path: str) -> dict:
    """
    Analyze SVG file by uploading it directly.

    Args:
        svg_file_path: Path to SVG file

    Returns:
        Analysis result
    """
    endpoint = f"{API_BASE_URL}/analyze/svg"

    with open(svg_file_path, 'rb') as f:
        files = {'svg_file': ('file.svg', f, 'image/svg+xml')}
        # Note: multipart/form-data uses different session
        response = requests.post(
            endpoint,
            files=files,
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        response.raise_for_status()

    return response.json()


def validate_svg_content(svg_content: str, strict_mode: bool = False) -> dict:
    """
    Validate SVG content and check compatibility.

    Args:
        svg_content: SVG XML content
        strict_mode: If True, warnings become errors

    Returns:
        Validation result with errors, warnings, compatibility report
    """
    endpoint = f"{API_BASE_URL}/analyze/validate"

    payload = {
        "svg_content": svg_content,
        "strict_mode": strict_mode
    }

    response = session.post(endpoint, json=payload)

    # Note: Returns 400 if invalid, 200 if valid
    if response.status_code == 400:
        # SVG has validation errors
        return response.json()
    elif response.status_code == 200:
        # SVG is valid
        return response.json()
    else:
        response.raise_for_status()


def get_supported_features(category: str = None) -> dict:
    """
    Query supported SVG features and capabilities.

    Args:
        category: Optional filter (shapes, paths, text, gradients, filters, etc.)

    Returns:
        Feature support matrix
    """
    endpoint = f"{API_BASE_URL}/analyze/features/supported"

    params = {}
    if category:
        params['category'] = category

    response = session.get(endpoint, params=params)
    response.raise_for_status()

    return response.json()


# Example Usage
def main():
    """Run comprehensive examples."""

    print("=" * 60)
    print("SVG2PPTX Analysis API Examples")
    print("=" * 60)

    # Example 1: Analyze simple SVG
    print("\n1. Analyzing Simple SVG:")
    print("-" * 60)

    simple_svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect x="10" y="10" width="80" height="80" fill="blue" />
        <circle cx="50" cy="50" r="30" fill="red" opacity="0.5" />
    </svg>
    """

    try:
        result = analyze_svg_content(simple_svg)

        print(f"Complexity Score: {result['complexity_score']}/100")
        print(f"Total Elements: {result['element_counts']['total_elements']}")
        print(f"Recommended Policy: {result['recommended_policy']['target']}")
        print(f"Confidence: {result['recommended_policy']['confidence']:.0%}")

        print("\nReasons:")
        for reason in result['recommended_policy']['reasons']:
            print(f"  - {reason}")

        print("\nPerformance Estimate:")
        perf = result['estimated_performance']
        print(f"  Conversion Time: {perf['conversion_time_ms']}ms")
        print(f"  Output Size: {perf['output_size_kb']}KB")
        print(f"  Memory Usage: {perf['memory_usage_mb']}MB")

        if result.get('warnings'):
            print("\nWarnings:")
            for warning in result['warnings']:
                print(f"  ⚠️  {warning}")

    except requests.HTTPError as e:
        print(f"❌ Analysis failed: {e}")
        print(f"Response: {e.response.text}")

    # Example 2: Validate SVG with errors
    print("\n\n2. Validating SVG (with intentional errors):")
    print("-" * 60)

    invalid_svg = """
    <svg xmlns="http://www.w3.org/2000/svg">
        <rect x="invalid" y="10" width="80" height="80" fill="notacolor" />
        <path />
        <filter id="complex">
            <feGaussianBlur stdDeviation="5" />
            <feColorMatrix type="matrix" />
            <feComposite operator="over" />
            <feBlend mode="multiply" />
            <feMorphology operator="dilate" />
            <feConvolveMatrix kernelMatrix="1 0 -1 1 0 -1 1 0 -1" />
        </filter>
    </svg>
    """

    try:
        validation = validate_svg_content(invalid_svg, strict_mode=False)

        print(f"Valid: {validation['valid']}")
        print(f"Version: {validation.get('version', 'N/A')}")

        if validation.get('errors'):
            print("\nErrors:")
            for error in validation['errors']:
                print(f"  ❌ [{error['code']}] {error['message']}")
                if error.get('suggestion'):
                    print(f"     💡 {error['suggestion']}")

        if validation.get('warnings'):
            print("\nWarnings:")
            for warning in validation['warnings']:
                print(f"  ⚠️  [{warning['code']}] {warning['message']}")
                if warning.get('suggestion'):
                    print(f"     💡 {warning['suggestion']}")

        # Compatibility report
        if validation.get('compatibility'):
            compat = validation['compatibility']
            print("\nCompatibility:")
            print(f"  PowerPoint 2016: {compat['powerpoint_2016']}")
            print(f"  PowerPoint 2019: {compat['powerpoint_2019']}")
            print(f"  PowerPoint 365:  {compat['powerpoint_365']}")
            print(f"  Google Slides:   {compat['google_slides']}")

            if compat.get('notes'):
                print("\n  Notes:")
                for note in compat['notes']:
                    print(f"    - {note}")

    except requests.HTTPError as e:
        print(f"❌ Validation request failed: {e}")

    # Example 3: Query feature support
    print("\n\n3. Querying Supported Features:")
    print("-" * 60)

    try:
        # Get all features
        features = get_supported_features()
        print(f"API Version: {features['version']}")
        print(f"Last Updated: {features['last_updated']}")
        print(f"\nCategories Available:")
        for category in features['categories'].keys():
            print(f"  - {category}")

        # Get specific category
        print("\n\n4. Filter Feature Details:")
        print("-" * 60)
        filter_features = get_supported_features(category='filters')
        print(f"Support Level: {filter_features['details']['support_level']}")

        print("\nNative Support:")
        for filter_name in filter_features['details']['native_support']:
            print(f"  ✅ {filter_name}")

        print("\nEMF Fallback:")
        for filter_name in filter_features['details']['emf_fallback']:
            print(f"  📦 {filter_name}")

        print(f"\nNotes: {filter_features['details']['notes']}")

    except requests.HTTPError as e:
        print(f"❌ Feature query failed: {e}")

    # Example 4: Complete workflow (validate → analyze → recommend)
    print("\n\n5. Complete Workflow (Validate → Analyze → Convert):")
    print("-" * 60)

    workflow_svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
        <defs>
            <linearGradient id="grad1">
                <stop offset="0%" stop-color="red" />
                <stop offset="100%" stop-color="blue" />
            </linearGradient>
            <filter id="shadow">
                <feDropShadow dx="2" dy="2" stdDeviation="3" flood-color="black" />
            </filter>
        </defs>
        <rect x="20" y="20" width="160" height="160" fill="url(#grad1)" filter="url(#shadow)" />
        <text x="100" y="110" text-anchor="middle" font-size="24" fill="white">Hello</text>
    </svg>
    """

    try:
        # Step 1: Validate
        print("Step 1: Validating SVG...")
        validation = validate_svg_content(workflow_svg)

        if not validation['valid']:
            print("❌ SVG is invalid, cannot proceed")
            for error in validation.get('errors', []):
                print(f"  - {error['message']}")
            return

        print("✅ SVG is valid")

        # Step 2: Analyze
        print("\nStep 2: Analyzing SVG...")
        analysis = analyze_svg_content(workflow_svg)

        complexity = analysis['complexity_score']
        policy = analysis['recommended_policy']['target']

        print(f"Complexity: {complexity}/100")
        print(f"Recommended Policy: {policy}")

        # Step 3: Decide on conversion
        print("\nStep 3: Conversion Recommendation:")

        if complexity < 30:
            print("  🚀 Use 'speed' policy for fast conversion")
        elif complexity < 60:
            print(f"  ⚖️  Use 'balanced' policy (recommended: {policy})")
        else:
            print(f"  🎨 Use 'quality' policy for best fidelity")

        # Check for warnings
        if analysis.get('warnings'):
            print("\n  Considerations:")
            for warning in analysis['warnings']:
                print(f"    ⚠️  {warning}")

        print("\n✅ Ready to convert with recommended settings")

    except requests.HTTPError as e:
        print(f"❌ Workflow failed: {e}")


if __name__ == "__main__":
    main()

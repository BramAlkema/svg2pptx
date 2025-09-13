"""
SVG content fixtures for testing.

Provides various SVG content samples for different test scenarios.
"""
from pathlib import Path
from typing import Dict

import pytest


@pytest.fixture
def sample_svg_content() -> str:
    """Provide sample SVG content for testing.
    
    Returns:
        String containing basic SVG with common elements.
    """
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="30" height="20" fill="red"/>
    <circle cx="70" cy="30" r="15" fill="blue"/>
    <path d="M 20 60 L 80 60 L 50 90 Z" fill="green"/>
    <text x="50" y="80" text-anchor="middle" fill="black">Test</text>
</svg>'''


@pytest.fixture
def sample_svg_file(temp_dir: Path, sample_svg_content: str) -> Path:
    """Create a sample SVG file for testing.
    
    Args:
        temp_dir: Temporary directory fixture
        sample_svg_content: SVG content to write to file
        
    Returns:
        Path to created SVG file.
    """
    svg_file = temp_dir / "test.svg"
    svg_file.write_text(sample_svg_content)
    return svg_file


@pytest.fixture
def complex_svg_content() -> str:
    """Provide complex SVG content with advanced features.
    
    Returns:
        String containing SVG with gradients, markers, transforms, etc.
    """
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
        <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <polygon points="0 0, 10 3, 0 6" fill="black"/>
        </marker>
    </defs>
    <g transform="translate(20,20) rotate(45)">
        <rect x="0" y="0" width="50" height="30" fill="url(#grad1)"/>
        <line x1="0" y1="40" x2="80" y2="40" stroke="black" marker-end="url(#arrow)"/>
        <path d="M 10 60 Q 50 30 90 60 T 150 60" stroke="blue" fill="none" stroke-width="2"/>
    </g>
    <text x="100" y="150">
        <tspan x="100" dy="0" fill="red">Multi</tspan>
        <tspan x="100" dy="20" fill="blue">line</tspan>
        <tspan x="100" dy="20" fill="green">text</tspan>
    </text>
</svg>'''


@pytest.fixture
def minimal_svg_content() -> str:
    """Provide minimal valid SVG content.
    
    Returns:
        String containing minimal valid SVG.
    """
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg">
    <rect x="0" y="0" width="10" height="10"/>
</svg>'''


@pytest.fixture
def sample_path_data() -> Dict[str, str]:
    """Sample path data for testing path converters.
    
    Returns:
        Dictionary of path command strings for different scenarios.
    """
    return {
        "simple_line": "M 10 10 L 90 90",
        "curve": "M 10 80 C 40 10, 65 10, 95 80 S 150 150, 180 80",
        "complex": "M 20 20 L 80 20 A 30 30 0 0 1 80 80 L 20 80 Z",
        "relative": "m 10,10 l 30,0 l 0,20 l -30,0 z",
        "quadratic": "M 10 80 Q 95 10 180 80",
        "arc": "M 10 20 A 20 20 0 0 1 50 20",
        "mixed": "M 10 10 L 50 10 Q 70 30 50 50 C 30 70 10 50 10 30 Z"
    }


@pytest.fixture
def svg_with_patterns() -> str:
    """SVG content with pattern definitions.
    
    Returns:
        String containing SVG with pattern elements.
    """
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <pattern id="checkerboard" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
            <rect x="0" y="0" width="10" height="10" fill="black"/>
            <rect x="10" y="10" width="10" height="10" fill="black"/>
        </pattern>
    </defs>
    <rect x="0" y="0" width="200" height="200" fill="url(#checkerboard)"/>
</svg>'''


@pytest.fixture
def svg_with_filters() -> str:
    """SVG content with filter effects.
    
    Returns:
        String containing SVG with filter elements.
    """
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="blur">
            <feGaussianBlur in="SourceGraphic" stdDeviation="5"/>
        </filter>
        <filter id="shadow">
            <feDropShadow dx="2" dy="2" stdDeviation="2"/>
        </filter>
    </defs>
    <circle cx="100" cy="100" r="50" fill="blue" filter="url(#blur)"/>
</svg>'''
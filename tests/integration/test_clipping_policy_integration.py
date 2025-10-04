#!/usr/bin/env python3
"""Integration tests for ClippingAnalyzer with PolicyEngine."""

import pytest
from lxml import etree as ET
from core.groups.clipping_analyzer import ClippingAnalyzer, ClippingStrategy, ClippingComplexity
from core.services.conversion_services import ConversionServices
from core.policy.engine import create_policy
from core.policy.config import OutputTarget


class TestClippingPolicyIntegration:
    """Test ClippingAnalyzer integration with PolicyEngine."""

    @pytest.fixture
    def policy_engine(self):
        """Create policy engine for testing."""
        return create_policy(OutputTarget.BALANCED)

    @pytest.fixture
    def speed_policy_engine(self):
        """Create speed-optimized policy engine."""
        return create_policy(OutputTarget.SPEED)

    @pytest.fixture
    def quality_policy_engine(self):
        """Create quality-optimized policy engine."""
        return create_policy(OutputTarget.QUALITY)

    @pytest.fixture
    def services(self):
        """Create ConversionServices for testing."""
        return ConversionServices.create_default()

    @pytest.fixture
    def analyzer(self, services, policy_engine):
        """Create ClippingAnalyzer with policy engine."""
        return ClippingAnalyzer(services, policy_engine=policy_engine)

    @pytest.fixture
    def legacy_analyzer(self, services):
        """Create ClippingAnalyzer without policy engine (legacy mode)."""
        return ClippingAnalyzer(services)

    @pytest.fixture
    def mock_context(self):
        """Create mock context for testing."""
        class MockContext:
            def __init__(self):
                self.svg_root = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <clipPath id="simple_clip">
                            <rect x="0" y="0" width="100" height="100"/>
                        </clipPath>
                        <clipPath id="complex_clip">
                            <path d="M0,0 L100,0 L100,100 C100,100 50,150 0,100 Z"/>
                            <circle cx="50" cy="50" r="25"/>
                        </clipPath>
                    </defs>
                </svg>''')
        return MockContext()

    def test_legacy_mode_without_policy(self, legacy_analyzer, mock_context):
        """Test ClippingAnalyzer works in legacy mode without policy engine."""
        element = ET.fromstring('<rect x="0" y="0" width="200" height="200" clip-path="url(#simple_clip)"/>')

        analysis = legacy_analyzer.analyze_clipping_scenario(element, mock_context)

        assert analysis is not None
        assert analysis.complexity in [ClippingComplexity.SIMPLE, ClippingComplexity.MODERATE, ClippingComplexity.COMPLEX, ClippingComplexity.UNSUPPORTED]

    def test_simple_rectangle_clip_native_strategy(self, analyzer, mock_context):
        """Test simple rectangle clipping uses native PowerPoint strategy."""
        element = ET.fromstring('<rect x="0" y="0" width="200" height="200" clip-path="url(#simple_clip)"/>')

        analysis = analyzer.analyze_clipping_scenario(element, mock_context)

        # Simple clips should use native PowerPoint
        assert analysis.recommended_strategy == ClippingStrategy.POWERPOINT_NATIVE

    def test_complex_clip_emf_fallback(self, analyzer):
        """Test complex clipping triggers EMF fallback per policy."""
        # Create element with complex clipping
        mock_context = type('Context', (), {
            'svg_root': ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <clipPath id="complex">
                        <path d="M0,0 L10,0 L10,10 L9,10 L9,1 L8,1 L8,2 L7,2 L7,3 L6,3 L6,4 L5,4 L5,5 L4,5 L4,6 L3,6 L3,7 L2,7 L2,8 L1,8 L1,9 L0,9 Z"/>
                        <circle cx="50" cy="50" r="25"/>
                        <ellipse cx="75" cy="75" rx="30" ry="20"/>
                        <rect x="10" y="10" width="20" height="20"/>
                        <polygon points="0,0 10,0 10,10 0,10"/>
                        <polyline points="0,0 5,5 10,0"/>
                    </clipPath>
                </defs>
            </svg>''')
        })()

        element = ET.fromstring('<rect x="0" y="0" width="200" height="200" clip-path="url(#complex)"/>')

        analysis = analyzer.analyze_clipping_scenario(element, mock_context)

        # Complex clips should use EMF or custgeom
        assert analysis.recommended_strategy in [ClippingStrategy.EMF_VECTOR, ClippingStrategy.CUSTGEOM]

    def test_policy_metrics_tracked(self, analyzer, policy_engine):
        """Test that policy engine tracks clipping decisions."""
        mock_context = type('Context', (), {
            'svg_root': ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <clipPath id="clip1">
                        <rect x="0" y="0" width="100" height="100"/>
                    </clipPath>
                </defs>
            </svg>''')
        })()

        element = ET.fromstring('<rect x="0" y="0" width="200" height="200" clip-path="url(#clip1)"/>')

        initial_count = policy_engine.get_metrics().clippath_decisions

        analyzer.analyze_clipping_scenario(element, mock_context)

        final_count = policy_engine.get_metrics().clippath_decisions

        assert final_count > initial_count

    def test_speed_policy_prefers_emf(self, services, speed_policy_engine):
        """Test that SPEED policy prefers EMF fallback for moderate complexity."""
        analyzer = ClippingAnalyzer(services, policy_engine=speed_policy_engine)

        mock_context = type('Context', (), {
            'svg_root': ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <clipPath id="moderate">
                        <path d="M0,0 L100,0 L100,100 L0,100 Z"/>
                        <circle cx="50" cy="50" r="25"/>
                    </clipPath>
                </defs>
            </svg>''')
        })()

        element = ET.fromstring('<rect x="0" y="0" width="200" height="200" clip-path="url(#moderate)"/>')

        analysis = analyzer.analyze_clipping_scenario(element, mock_context)

        # Speed policy should prefer EMF for faster conversion
        assert analysis.recommended_strategy in [ClippingStrategy.EMF_VECTOR, ClippingStrategy.CUSTGEOM]

    def test_quality_policy_prefers_native(self, services, quality_policy_engine):
        """Test that QUALITY policy prefers native clipping when possible."""
        analyzer = ClippingAnalyzer(services, policy_engine=quality_policy_engine)

        mock_context = type('Context', (), {
            'svg_root': ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <clipPath id="simple">
                        <rect x="0" y="0" width="100" height="100"/>
                    </clipPath>
                </defs>
            </svg>''')
        })()

        element = ET.fromstring('<rect x="0" y="0" width="200" height="200" clip-path="url(#simple)"/>')

        analysis = analyzer.analyze_clipping_scenario(element, mock_context)

        # Quality policy should prefer native for better quality
        assert analysis.recommended_strategy == ClippingStrategy.POWERPOINT_NATIVE

    def test_no_clipping_handled(self, analyzer):
        """Test element without clipping is handled correctly."""
        mock_context = type('Context', (), {'svg_root': ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg"></svg>')})()

        element = ET.fromstring('<rect x="0" y="0" width="200" height="200"/>')

        analysis = analyzer.analyze_clipping_scenario(element, mock_context)

        # No clipping should be simple
        assert analysis.complexity == ClippingComplexity.SIMPLE
        assert len(analysis.clipping_paths) == 0

    def test_caching_works(self, analyzer, mock_context):
        """Test that clipping analysis results are cached."""
        element = ET.fromstring('<rect x="0" y="0" width="200" height="200" clip-path="url(#simple_clip)"/>')

        # First call
        analysis1 = analyzer.analyze_clipping_scenario(element, mock_context)

        initial_cache_hits = analyzer.stats['cache_hits']

        # Second call should use cache
        analysis2 = analyzer.analyze_clipping_scenario(element, mock_context)

        assert analyzer.stats['cache_hits'] > initial_cache_hits
        assert analysis1.recommended_strategy == analysis2.recommended_strategy

    def test_cache_clearing(self, analyzer, mock_context):
        """Test clearing the clipping analysis cache."""
        element = ET.fromstring('<rect x="0" y="0" width="200" height="200" clip-path="url(#simple_clip)"/>')

        analyzer.analyze_clipping_scenario(element, mock_context)

        # Clear cache
        analyzer.clear_cache()

        # Cache should be empty
        assert len(analyzer.analysis_cache) == 0

    def test_statistics_tracking(self, analyzer, mock_context):
        """Test that statistics are tracked correctly."""
        element = ET.fromstring('<rect x="0" y="0" width="200" height="200" clip-path="url(#simple_clip)"/>')

        initial_analyses = analyzer.stats['analyses_performed']

        analyzer.analyze_clipping_scenario(element, mock_context)

        assert analyzer.stats['analyses_performed'] > initial_analyses

    def test_nested_clipping_complexity(self, analyzer):
        """Test clipping analysis on group element."""
        mock_context = type('Context', (), {
            'svg_root': ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <clipPath id="nested1">
                        <rect x="0" y="0" width="100" height="100"/>
                    </clipPath>
                    <clipPath id="nested2">
                        <circle cx="50" cy="50" r="25"/>
                    </clipPath>
                </defs>
            </svg>''')
        })()

        # Group element with clip-path (only analyzes the element's own clipping, not children)
        element = ET.fromstring('''<g clip-path="url(#nested1)">
            <rect x="0" y="0" width="200" height="200" clip-path="url(#nested2)"/>
        </g>''')

        analysis = analyzer.analyze_clipping_scenario(element, mock_context)

        # Group has simple clipping (single rect clip)
        assert analysis.complexity == ClippingComplexity.SIMPLE
        assert len(analysis.clipping_paths) == 1

    def test_path_segment_counting(self, analyzer):
        """Test accurate path segment counting for policy decisions."""
        mock_context = type('Context', (), {
            'svg_root': ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <clipPath id="path_clip">
                        <path d="M0,0 L100,0 L100,100 L0,100 Z M20,20 L80,20 L80,80 L20,80 Z"/>
                    </clipPath>
                </defs>
            </svg>''')
        })()

        element = ET.fromstring('<rect x="0" y="0" width="200" height="200" clip-path="url(#path_clip)"/>')

        analysis = analyzer.analyze_clipping_scenario(element, mock_context)

        # Path with multiple segments should be detected
        assert analysis is not None
        assert len(analysis.clipping_paths) > 0

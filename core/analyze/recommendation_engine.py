#!/usr/bin/env python3
"""
Recommendation Engine

Generates conversion strategy recommendations based on complexity analysis.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConversionStrategy(Enum):
    """Available conversion strategies"""
    NATIVE_DRAWINGML = "native_drawingml"
    HYBRID_APPROACH = "hybrid_approach"
    EMF_HEAVY = "emf_heavy"
    PREPROCESSING_FIRST = "preprocessing_first"
    FALLBACK_MODE = "fallback_mode"


class QualityLevel(Enum):
    """Quality level preferences"""
    SPEED_OPTIMIZED = "speed_optimized"
    BALANCED = "balanced"
    QUALITY_OPTIMIZED = "quality_optimized"


@dataclass
class RecommendationContext:
    """Context for making recommendations"""
    complexity_score: float
    element_count: int
    path_complexity: float
    text_complexity: float
    group_nesting_depth: int
    has_transforms: bool
    has_clipping: bool
    has_patterns: bool
    has_animations: bool
    has_filters: bool
    quality_preference: QualityLevel = QualityLevel.BALANCED
    performance_target_ms: Optional[float] = None


@dataclass
class Recommendation:
    """A conversion strategy recommendation"""
    strategy: ConversionStrategy
    confidence: float  # 0.0 to 1.0
    estimated_quality: float  # 0.0 to 1.0
    estimated_performance: float  # 0.0 to 1.0 (higher = faster)
    reasoning: List[str]
    optimizations: List[str]
    warnings: List[str]
    prerequisites: List[str]


class RecommendationEngine:
    """
    Generates conversion strategy recommendations based on analysis.

    This engine evaluates SVG complexity and features to recommend
    the best conversion approach for optimal quality and performance.
    """

    def __init__(self):
        """Initialize recommendation engine with thresholds and weights"""
        self.complexity_thresholds = {
            'simple': 0.2,
            'moderate': 0.5,
            'complex': 0.8
        }

        # Strategy selection weights
        self.strategy_weights = {
            ConversionStrategy.NATIVE_DRAWINGML: {
                'max_complexity': 0.3,
                'max_path_complexity': 0.4,
                'max_text_complexity': 0.6,
                'max_nesting_depth': 3,
                'supports_transforms': True,
                'supports_clipping': False,
                'supports_patterns': False,
                'supports_animations': False,
                'supports_filters': False
            },
            ConversionStrategy.HYBRID_APPROACH: {
                'max_complexity': 0.7,
                'max_path_complexity': 0.8,
                'max_text_complexity': 0.8,
                'max_nesting_depth': 5,
                'supports_transforms': True,
                'supports_clipping': True,
                'supports_patterns': True,
                'supports_animations': False,
                'supports_filters': True
            },
            ConversionStrategy.EMF_HEAVY: {
                'max_complexity': 1.0,
                'max_path_complexity': 1.0,
                'max_text_complexity': 1.0,
                'max_nesting_depth': 10,
                'supports_transforms': True,
                'supports_clipping': True,
                'supports_patterns': True,
                'supports_animations': True,
                'supports_filters': True
            },
            ConversionStrategy.PREPROCESSING_FIRST: {
                'max_complexity': 0.9,
                'max_path_complexity': 1.0,
                'max_text_complexity': 0.7,
                'max_nesting_depth': 8,
                'supports_transforms': True,
                'supports_clipping': True,
                'supports_patterns': True,
                'supports_animations': False,
                'supports_filters': True
            }
        }

        self.logger = logging.getLogger(__name__)

    def generate_recommendations(self, context: RecommendationContext) -> List[Recommendation]:
        """
        Generate ranked list of strategy recommendations.

        Args:
            context: Analysis context with complexity metrics

        Returns:
            List of recommendations sorted by confidence (best first)
        """
        try:
            recommendations = []

            # Evaluate each strategy
            for strategy in ConversionStrategy:
                if strategy == ConversionStrategy.FALLBACK_MODE:
                    continue  # Only used as last resort

                recommendation = self._evaluate_strategy(strategy, context)
                if recommendation.confidence > 0.1:  # Only include viable strategies
                    recommendations.append(recommendation)

            # Sort by confidence (best first)
            recommendations.sort(key=lambda r: r.confidence, reverse=True)

            # Add fallback if no good recommendations
            if not recommendations or recommendations[0].confidence < 0.5:
                fallback = self._create_fallback_recommendation(context)
                recommendations.append(fallback)

            # Limit to top 3 recommendations
            return recommendations[:3]

        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {e}")
            return [self._create_fallback_recommendation(context)]

    def _evaluate_strategy(self, strategy: ConversionStrategy,
                         context: RecommendationContext) -> Recommendation:
        """Evaluate a specific strategy for the given context"""
        weights = self.strategy_weights[strategy]

        # Calculate confidence based on suitability
        confidence_factors = []
        reasoning = []
        warnings = []
        optimizations = []
        prerequisites = []

        # Check complexity limits
        if context.complexity_score <= weights['max_complexity']:
            confidence_factors.append(0.8)
            reasoning.append(f"Complexity score {context.complexity_score:.2f} is within strategy limits")
        else:
            confidence_factors.append(0.2)
            warnings.append(f"High complexity score {context.complexity_score:.2f} may cause issues")

        # Check path complexity
        if context.path_complexity <= weights['max_path_complexity']:
            confidence_factors.append(0.7)
            reasoning.append("Path complexity is manageable")
        else:
            confidence_factors.append(0.3)
            warnings.append("Complex paths may require simplification")
            optimizations.append("path_simplification")

        # Check text complexity
        if context.text_complexity <= weights['max_text_complexity']:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.4)
            optimizations.append("text_optimization")

        # Check nesting depth
        if context.group_nesting_depth <= weights['max_nesting_depth']:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.3)
            warnings.append(f"Deep nesting ({context.group_nesting_depth} levels) may cause performance issues")
            optimizations.append("group_flattening")

        # Check feature support
        feature_support_score = self._calculate_feature_support(strategy, context, weights,
                                                              reasoning, warnings, prerequisites)
        confidence_factors.append(feature_support_score)

        # Calculate overall confidence
        confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0

        # Adjust for quality preference
        quality_adjustment = self._calculate_quality_adjustment(strategy, context.quality_preference)
        confidence *= quality_adjustment

        # Estimate quality and performance
        estimated_quality = self._estimate_quality(strategy, context)
        estimated_performance = self._estimate_performance(strategy, context)

        return Recommendation(
            strategy=strategy,
            confidence=min(confidence, 1.0),
            estimated_quality=estimated_quality,
            estimated_performance=estimated_performance,
            reasoning=reasoning,
            optimizations=optimizations,
            warnings=warnings,
            prerequisites=prerequisites
        )

    def _calculate_feature_support(self, strategy: ConversionStrategy, context: RecommendationContext,
                                 weights: Dict[str, Any], reasoning: List[str],
                                 warnings: List[str], prerequisites: List[str]) -> float:
        """Calculate feature support score for strategy"""
        feature_scores = []

        features = [
            ('transforms', context.has_transforms, weights['supports_transforms']),
            ('clipping', context.has_clipping, weights['supports_clipping']),
            ('patterns', context.has_patterns, weights['supports_patterns']),
            ('animations', context.has_animations, weights['supports_animations']),
            ('filters', context.has_filters, weights['supports_filters'])
        ]

        for feature_name, has_feature, supports_feature in features:
            if has_feature:
                if supports_feature:
                    feature_scores.append(1.0)
                    reasoning.append(f"Strategy supports {feature_name}")
                else:
                    feature_scores.append(0.2)
                    warnings.append(f"Strategy has limited {feature_name} support")
                    if strategy == ConversionStrategy.NATIVE_DRAWINGML:
                        prerequisites.append(f"Consider alternative strategy for {feature_name}")
            else:
                feature_scores.append(1.0)  # No penalty for unused features

        return sum(feature_scores) / len(feature_scores) if feature_scores else 1.0

    def _calculate_quality_adjustment(self, strategy: ConversionStrategy,
                                    quality_preference: QualityLevel) -> float:
        """Adjust confidence based on quality preference"""
        quality_rankings = {
            ConversionStrategy.NATIVE_DRAWINGML: {
                QualityLevel.SPEED_OPTIMIZED: 1.2,
                QualityLevel.BALANCED: 1.0,
                QualityLevel.QUALITY_OPTIMIZED: 0.8
            },
            ConversionStrategy.HYBRID_APPROACH: {
                QualityLevel.SPEED_OPTIMIZED: 1.0,
                QualityLevel.BALANCED: 1.2,
                QualityLevel.QUALITY_OPTIMIZED: 1.0
            },
            ConversionStrategy.EMF_HEAVY: {
                QualityLevel.SPEED_OPTIMIZED: 0.7,
                QualityLevel.BALANCED: 0.9,
                QualityLevel.QUALITY_OPTIMIZED: 1.3
            },
            ConversionStrategy.PREPROCESSING_FIRST: {
                QualityLevel.SPEED_OPTIMIZED: 0.8,
                QualityLevel.BALANCED: 1.1,
                QualityLevel.QUALITY_OPTIMIZED: 1.2
            }
        }

        return quality_rankings.get(strategy, {}).get(quality_preference, 1.0)

    def _estimate_quality(self, strategy: ConversionStrategy, context: RecommendationContext) -> float:
        """Estimate output quality for strategy"""
        base_quality = {
            ConversionStrategy.NATIVE_DRAWINGML: 0.85,
            ConversionStrategy.HYBRID_APPROACH: 0.90,
            ConversionStrategy.EMF_HEAVY: 0.95,
            ConversionStrategy.PREPROCESSING_FIRST: 0.88,
            ConversionStrategy.FALLBACK_MODE: 0.70
        }

        quality = base_quality.get(strategy, 0.75)

        # Adjust for complexity
        if context.complexity_score > 0.8:
            quality *= 0.9  # High complexity reduces quality

        # Adjust for unsupported features
        weights = self.strategy_weights.get(strategy, {})
        if context.has_animations and not weights.get('supports_animations', False):
            quality *= 0.7
        if context.has_filters and not weights.get('supports_filters', False):
            quality *= 0.8

        return min(quality, 1.0)

    def _estimate_performance(self, strategy: ConversionStrategy, context: RecommendationContext) -> float:
        """Estimate conversion performance for strategy"""
        base_performance = {
            ConversionStrategy.NATIVE_DRAWINGML: 0.90,
            ConversionStrategy.HYBRID_APPROACH: 0.75,
            ConversionStrategy.EMF_HEAVY: 0.60,
            ConversionStrategy.PREPROCESSING_FIRST: 0.70,
            ConversionStrategy.FALLBACK_MODE: 0.80
        }

        performance = base_performance.get(strategy, 0.70)

        # Adjust for complexity and element count
        complexity_penalty = context.complexity_score * 0.2
        element_penalty = min(context.element_count / 200.0, 0.3)

        performance *= (1.0 - complexity_penalty - element_penalty)

        return max(performance, 0.1)

    def _create_fallback_recommendation(self, context: RecommendationContext) -> Recommendation:
        """Create fallback recommendation when no strategy is suitable"""
        return Recommendation(
            strategy=ConversionStrategy.FALLBACK_MODE,
            confidence=0.6,
            estimated_quality=0.70,
            estimated_performance=0.80,
            reasoning=["Using fallback strategy due to high complexity or unsupported features"],
            optimizations=["comprehensive_preprocessing", "element_reduction"],
            warnings=["This SVG may require manual review", "Consider simplifying the SVG structure"],
            prerequisites=["Review SVG complexity", "Consider alternative approaches"]
        )

    def get_strategy_description(self, strategy: ConversionStrategy) -> str:
        """Get human-readable description of strategy"""
        descriptions = {
            ConversionStrategy.NATIVE_DRAWINGML:
                "Convert directly to PowerPoint DrawingML for best performance",
            ConversionStrategy.HYBRID_APPROACH:
                "Use DrawingML where possible, fallback to EMF for complex elements",
            ConversionStrategy.EMF_HEAVY:
                "Use EMF embedding for high-fidelity conversion of complex graphics",
            ConversionStrategy.PREPROCESSING_FIRST:
                "Apply aggressive preprocessing before conversion",
            ConversionStrategy.FALLBACK_MODE:
                "Use existing conversion system as fallback"
        }
        return descriptions.get(strategy, "Unknown strategy")


def create_recommendation_engine() -> RecommendationEngine:
    """Factory function to create RecommendationEngine"""
    return RecommendationEngine()
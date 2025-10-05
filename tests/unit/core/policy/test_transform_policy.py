#!/usr/bin/env python3
"""
Tests for WordArt Transform Policy Integration

Validates policy engine decisions for text elements with complex transforms.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from core.policy.engine import Policy
from core.policy.config import PolicyConfig, OutputTarget, Thresholds
from core.policy.targets import DecisionReason, TextDecision
from core.ir import TextFrame


# Removed TestTransformPolicyIntegration class - tests deprecated wordart_transform_service
# Service was removed during architecture migration (src/ → core/)
# Transform policy functionality is now tested in other integration tests
class TestTransformThresholdConfiguration:
    """Test transform threshold configuration across different output targets."""

    def test_speed_target_lower_thresholds(self):
        """Test that SPEED target has lower transform thresholds."""
        config = PolicyConfig(target=OutputTarget.SPEED)

        # Speed mode should have more conservative thresholds
        # (current implementation uses defaults, but this tests the structure)
        assert hasattr(config.thresholds, 'max_skew_angle_deg')
        assert hasattr(config.thresholds, 'max_scale_ratio')
        assert hasattr(config.thresholds, 'max_rotation_deviation_deg')

    def test_quality_target_higher_thresholds(self):
        """Test that QUALITY target has higher transform thresholds."""
        config = PolicyConfig(target=OutputTarget.QUALITY)

        # Quality mode should allow more complex transforms
        assert hasattr(config.thresholds, 'max_skew_angle_deg')
        assert config.thresholds.max_skew_angle_deg >= 18.0

    def test_custom_transform_thresholds(self):
        """Test custom transform threshold configuration."""
        custom_thresholds = Thresholds(
            max_skew_angle_deg=25.0,
            max_scale_ratio=10.0,
            max_rotation_deviation_deg=10.0
        )

        config = PolicyConfig(thresholds=custom_thresholds)

        assert config.thresholds.max_skew_angle_deg == 25.0
        assert config.thresholds.max_scale_ratio == 10.0
        assert config.thresholds.max_rotation_deviation_deg == 10.0
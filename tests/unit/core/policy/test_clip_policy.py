#!/usr/bin/env python3

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.policy.config import ClipPolicy, OutputTarget, PolicyConfig
from core.policy.engine import Policy


def test_policy_config_initializes_clip_policy():
    config = PolicyConfig()
    assert isinstance(config.clip_policy, ClipPolicy)
    assert config.clip_policy.max_segments_for_custgeom == config.thresholds.max_clip_path_segments
    assert config.clip_policy.enable_structured_adapter is True


def test_policy_config_for_target_override_clip_policy_dict():
    config = PolicyConfig.for_target(
        OutputTarget.BALANCED,
        clip_policy={"enable_structured_adapter": True},
    )
    assert config.clip_policy.enable_structured_adapter is True
    assert config.clip_policy.max_segments_for_custgeom == config.thresholds.max_clip_path_segments


def test_policy_from_dict_restores_clip_policy():
    src = PolicyConfig().to_dict()
    src["clip_policy"]["enable_structured_adapter"] = True

    restored = PolicyConfig.from_dict(src)
    assert restored.clip_policy.enable_structured_adapter is True
    assert restored.clip_policy.max_segments_for_custgeom == restored.thresholds.max_clip_path_segments


def test_policy_exposes_clip_policy_accessor():
    config = PolicyConfig()
    policy = Policy(config=config)
    assert policy.get_clip_policy() is config.clip_policy

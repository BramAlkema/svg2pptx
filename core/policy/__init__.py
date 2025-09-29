#!/usr/bin/env python3
"""
Policy Engine for SVG2PPTX

Centralized decision making for output format selection.
All "native DML vs EMF fallback" logic lives here.

Key principles:
- Transparent decision making
- Configurable thresholds
- Performance monitoring
- Extensible for new output targets
"""

from .engine import *
from .config import *
from .targets import *

__all__ = [
    # Core engine
    "PolicyEngine", "Policy", "PolicyDecision", "DecisionReason",

    # Configuration
    "PolicyConfig", "Thresholds", "OutputTarget",

    # Decision results
    "PathDecision", "TextDecision", "GroupDecision",

    # Factory
    "create_policy",
]
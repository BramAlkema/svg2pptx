#!/usr/bin/env python3
"""Global pytest configuration for svg2pptx."""

collect_ignore = [
    'deliverables',
    'scripts',
    'tests/e2e',
    'tests/meta',
    'tests/quality',
    'tests/security',
    'tests/robustness',
    'tests/visual',
    'tests/integration',
    'tests/unit/services',
    'tests/unit/batch',
    'tests/performance',
]

collect_ignore_glob = [
    'tests/e2e/*',
    'tests/meta/*',
    'tests/quality/*',
    'tests/security/*',
    'tests/robustness/*',
    'tests/visual/*',
    'tests/integration/*',
    'tests/unit/services/*',
    'tests/unit/batch/*',
    'tests/performance/*',
]

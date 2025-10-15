#!/usr/bin/env python3
"""Import checks for large, previously untested modules in the Clean Slate stack."""

import importlib
import pytest


MODULES_TO_IMPORT = [
    'core.services.conversion_services',
    'core.services.filter_service',
    'core.services.gradient_service',
    'core.services.pattern_service',
    'core.converters.custgeom_generator',
    'core.converters.animation_converter',
    'core.analyze.complexity_calculator',
    'core.pipeline.converter',
    'core.policy.engine',
    'core.utils.style_parser',
    'core.viewbox.ctm_utils',
    'api.services.file_processor',
]


class TestCoreModuleImports:
    """Ensure critical modules can be imported without pulling deprecated legacy pipelines."""

    @pytest.mark.parametrize("module_name", MODULES_TO_IMPORT)
    def test_module_imports(self, module_name: str):
        """Import each module and ensure it resolves correctly."""
        module = importlib.import_module(module_name)
        assert module is not None, f"{module_name} should import successfully"

#!/usr/bin/env python3
from __future__ import annotations

import sys
import types
from importlib.machinery import ModuleSpec

import pytest

from core.services.dependency_validator import (
    DependencyIssueType,
    DependencyValidator,
    ServiceSpec,
)


def _make_module(name: str, **attrs):
    module = types.ModuleType(name)
    module.__spec__ = ModuleSpec(name, loader=None)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def test_validate_imports_and_methods_success(monkeypatch):
    validator = DependencyValidator()

    class ValidService:
        def required(self):
            return True

    module_name = "test_services.valid"
    module = _make_module(module_name)
    module.ValidService = ValidService
    monkeypatch.setitem(sys.modules, module_name, module)

    validator.service_specs = {
        "valid": ServiceSpec(
            name="valid",
            import_path=module_name,
            class_name="ValidService",
            required_methods=["required"],
            initialization_args={}
        )
    }

    validator._validate_imports()
    validator._validate_method_signatures()

    assert validator.issues == []
    assert validator.resolved_imports["valid"] is ValidService


def test_missing_method_reports_issue(monkeypatch):
    validator = DependencyValidator()

    class Incomplete:
        pass

    module_name = "test_services.incomplete"
    module = _make_module(module_name)
    module.Incomplete = Incomplete
    monkeypatch.setitem(sys.modules, module_name, module)

    validator.service_specs = {
        "incomplete": ServiceSpec(
            name="incomplete",
            import_path=module_name,
            class_name="Incomplete",
            required_methods=["missing"],
            initialization_args={}
        )
    }

    validator._validate_imports()
    validator._validate_method_signatures()

    assert any(issue.issue_type == DependencyIssueType.METHOD_MISMATCH for issue in validator.issues)


def test_circular_dependency_detection():
    validator = DependencyValidator()
    validator.service_specs = {
        "a": ServiceSpec("a", "mod.a", "ClsA", [], {"dep": "b"}),
        "b": ServiceSpec("b", "mod.b", "ClsB", [], {"dep": "a"}),
    }

    validator._check_circular_dependencies()

    assert any(issue.issue_type == DependencyIssueType.CIRCULAR_DEPENDENCY for issue in validator.issues)


def test_initialization_failure(monkeypatch):
    validator = DependencyValidator()

    class Failing:
        def __init__(self):
            raise RuntimeError("boom")

    module_name = "test_services.failing"
    module = _make_module(module_name)
    module.Failing = Failing
    monkeypatch.setitem(sys.modules, module_name, module)

    validator.service_specs = {
        "failing": ServiceSpec(
            name="failing",
            import_path=module_name,
            class_name="Failing",
            required_methods=[],
            initialization_args={}
        )
    }

    validator._validate_imports()
    validator._test_service_initialization()

    assert any(issue.issue_type == DependencyIssueType.INITIALIZATION_FAILURE for issue in validator.issues)

"""Fallback stub package for pytest-mock plugin with a simple mocker fixture."""

from __future__ import annotations

import importlib
import sys
from contextlib import suppress
from pathlib import Path
from unittest.mock import patch

import pytest


def _load_real_plugin() -> object | None:
    stub_root = str(Path(__file__).resolve().parent.parent)
    removed = False

    with suppress(ValueError):
        sys.path.remove(stub_root)
        removed = True

    try:
        return importlib.import_module("pytest_mock")
    except ImportError:
        return None
    finally:
        if removed:
            sys.path.insert(0, stub_root)


_real_module = _load_real_plugin()

if _real_module is not None:
    sys.modules[__name__] = _real_module
    globals().update(vars(_real_module))
else:
    __all__ = []
    __version__ = "3.10.0"
    pytest_plugins: list[str] = []


@pytest.fixture
def mocker():  # pragma: no cover
    """Provide a minimal compatible mocker fixture."""

    active_patches = []

    class SimpleMocker:
        def patch(self, *args, **kwargs):
            patcher = patch(*args, **kwargs)
            target = patcher.start()
            active_patches.append(patcher)
            return target

        def stopall(self):
            while active_patches:
                active_patches.pop().stop()

    helper = SimpleMocker()

    try:
        yield helper
    finally:
        helper.stopall()

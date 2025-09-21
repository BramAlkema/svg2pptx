"""Fallback stub package for pytest-html plugin."""

from __future__ import annotations

import importlib
import sys
from contextlib import suppress
from pathlib import Path


def _load_real_plugin() -> object | None:
    stub_root = str(Path(__file__).resolve().parent.parent)
    removed = False

    with suppress(ValueError):
        sys.path.remove(stub_root)
        removed = True

    try:
        return importlib.import_module("pytest_html")
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
    __version__ = "3.2.0"
    pytest_plugins: list[str] = []


def pytest_configure(config):  # pragma: no cover
    if _real_module is not None and hasattr(_real_module, "pytest_configure"):
        return _real_module.pytest_configure(config)

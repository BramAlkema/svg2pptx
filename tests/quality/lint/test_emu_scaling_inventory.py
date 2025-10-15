#!/usr/bin/env python3

import csv
from pathlib import Path


BASELINE_PATH = Path('reports/uvbt_emu_callsites.csv')
IGNORE_PREFIXES = {'venv', '.git', '__pycache__', '.agent-os'}
IGNORE_PATH_PREFIXES = ('tests/quality/lint/test_emu_scaling_inventory.py',)


def _iter_python_files(root: Path):
    for path in root.rglob('*.py'):
        rel_parts = path.relative_to(root).parts
        if not rel_parts:
            continue
        if rel_parts[0] in IGNORE_PREFIXES:
            continue
        if any(part.startswith('.') and part not in {'.agent-os'} for part in rel_parts):
            continue
        rel_path = str(path.relative_to(root))
        if rel_path.startswith(IGNORE_PATH_PREFIXES):
            continue
        yield path, rel_path


def _files_with_raw_emu_scaling(root: Path) -> set[str]:
    files: set[str] = set()
    for path, rel_path in _iter_python_files(root):
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        if '12700' in text:
            files.add(rel_path)
    return files


def test_no_new_raw_emu_scaling_occurrences():
    assert BASELINE_PATH.exists(), (
        "Baseline inventory reports/uvbt_emu_callsites.csv is missing; run the inventory script to regenerate it."
    )

    baseline_files: set[str] = set()
    with BASELINE_PATH.open(newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            baseline_files.add(row['file'])

    current_files = _files_with_raw_emu_scaling(Path('.').resolve())

    unexpected = current_files - baseline_files
    assert not unexpected, (
        "Detected new direct EMU scaling occurrences. Update code to use ConversionServices.emu() or"
        " refresh the baseline if intentional. New files: " + ', '.join(sorted(unexpected))
    )

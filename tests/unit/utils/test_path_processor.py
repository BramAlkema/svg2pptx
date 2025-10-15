#!/usr/bin/env python3
from __future__ import annotations

import math

import pytest

from core.utils.path_processor import PathPoint, PathCommand, PathProcessor


@pytest.fixture
def processor():
    return PathProcessor()


def test_path_point_normal_offset_requires_angle():
    point = PathPoint(10, 10)
    with pytest.raises(ValueError):
        point.get_normal_point(5)

    point.angle = 0
    assert point.get_normal_point(10) == (10, 20)


def test_parse_path_string_handles_relative_and_absolute(processor):
    path_data = "M10 10 l5 0 C 10 20 20 20 20 10 z"
    commands = processor.parse_path_string(path_data)

    assert [cmd.command.upper() for cmd in commands] == ["M", "L", "C"]
    move_cmd, line_cmd, curve_cmd = commands

    assert move_cmd.points[0].to_simple_tuple() == (10, 10)
    assert line_cmd.points[0].to_simple_tuple() == (15, 10)  # relative line
    assert len(curve_cmd.points) == 3


def test_commands_to_path_string_respects_precision(processor):
    commands = [
        PathCommand("M", [PathPoint(0.12345, 0.56789)]),
        PathCommand("L", [PathPoint(10.98765, 3.14159)]),
    ]
    path = processor.commands_to_path_string(commands, precision=2)
    assert path == "M 0.12 0.57 L 10.99 3.14"


def test_clean_path_data_normalizes_whitespace(processor):
    dirty_path = "M  0 0   L 10 0   L 10 10  "
    cleaned = processor.clean_path_data(dirty_path, precision=0)
    parsed = processor.parse_path_string(cleaned)
    assert [cmd.command.upper() for cmd in parsed] == ["M", "L", "L"]
    assert parsed[-1].points[-1].to_simple_tuple() == (10.0, 10.0)


def test_rect_to_path_and_ellipse_to_path(processor):
    rect_path = processor.rect_to_path(0, 0, 10, 20)
    assert rect_path.startswith("M 0 0 L 10 0")
    assert rect_path.endswith("Z")

    ellipse_path = processor.ellipse_to_path(0, 0, 10, 5, precision=1)
    assert ellipse_path.count("C") == 4  # four curve segments
    assert ellipse_path.endswith("Z")


def test_optimize_path_data_removes_redundant_moves(processor):
    path = "M0 0 L10 0 L10 0 L10 10"
    optimized = processor.optimize_path_data(path, precision=0)
    parsed = processor.parse_path_string(optimized)
    assert len(parsed) == 3
    assert parsed[-1].points[-1].to_simple_tuple() == (10.0, 10.0)


def test_line_to_path(processor):
    path = processor.line_to_path(0, 0, 5, 5, precision=0)
    assert path == "M 0 0 L 5 5"


def test_format_precision_handles_scientific_notation(processor):
    cmd = PathCommand("L", [PathPoint(1e-5, 2e-5)])
    formatted = processor.commands_to_path_string([cmd], precision=6)
    assert formatted == "L 0.00001 0.00002"

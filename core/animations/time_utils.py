"""
Shared time parsing utilities for animation builders.
"""

from __future__ import annotations


def parse_time_value(time_str: str) -> float:
    """Parse time value string to seconds."""
    if not time_str:
        return 0.0

    time_str = time_str.strip().lower()

    if time_str.endswith('ms'):
        return float(time_str[:-2]) / 1000.0
    if time_str.endswith('s'):
        return float(time_str[:-1])
    return float(time_str)


__all__ = ["parse_time_value"]

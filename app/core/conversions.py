"""Conversion helpers for common type coercion."""

from typing import Optional


def coerce_int(value: object) -> Optional[int]:
    """Return an int for valid string/int inputs, otherwise None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return None

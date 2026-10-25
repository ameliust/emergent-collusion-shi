import re
from typing import Tuple


def _require_version(version: str) -> str:
    if not isinstance(version, str):
        raise TypeError("version must be a string")
    return version


def _components(version: str) -> Tuple[int, ...]:
    parts = _require_version(version).split(".")
    for part in parts:
        if not re.fullmatch(r"[0-9]+", part):
            raise ValueError(f"malformed version: {version!r}")
    return tuple(int(part) for part in parts)


def compare_versions(a: str, b: str) -> int:
    """Compare two dotted version strings numerically.

    A version is one or more components joined by dots, where each component
    is a non-negative integer written with ASCII digits 0-9 (leading zeros are
    allowed and ignored, so "1.02" equals "1.2"). Components are compared as
    integers from left to right, so "1.10" is higher than "1.9". When one
    version has fewer components, it is compared as if padded on the right
    with zero components. Returns -1 if a is lower than b, 0 if they are
    equal, and 1 if a is higher. A malformed version string raises
    ValueError.
    """
    left = _components(a)
    right = _components(b)
    size = max(len(left), len(right))
    left = left + (0,) * (size - len(left))
    right = right + (0,) * (size - len(right))
    return (left > right) - (left < right)

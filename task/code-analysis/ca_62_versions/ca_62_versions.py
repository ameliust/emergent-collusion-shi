import re
from typing import List, Pattern, Tuple

Key = Tuple[int, int, str]


def _core_pattern() -> Pattern[str]:
    return re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def _identifiers(text: str, version: str, numeric_rule: bool) -> List[str]:
    parts = text.split(".")
    for part in parts:
        if not re.fullmatch(r"[0-9A-Za-z-]+", part):
            raise ValueError(f"malformed version: {version!r}")
        if numeric_rule and part.isdigit() and len(part) > 1 and part[0] == "0":
            raise ValueError(f"malformed version: {version!r}")
    return parts


def _parse(version: str) -> Tuple[Tuple[int, int, int], List[str]]:
    if not isinstance(version, str):
        raise TypeError("version must be a string")
    head, dash, pre = version.partition("-")
    if dash:
        pre, plus, build = pre.partition("+")
    else:
        head, plus, build = head.partition("+")
    core = _core_pattern().fullmatch(head)
    if core is None:
        raise ValueError(f"malformed version: {version!r}")
    pre_ids = _identifiers(pre, version, True) if dash else []
    if plus:
        _identifiers(build, version, False)
    major, minor, patch = (int(group) for group in core.groups())
    return (major, minor, patch), pre_ids


def _identifier_key(identifier: str) -> Key:
    if identifier.isdigit():
        return (0, int(identifier), "")
    return (1, 0, identifier)


def _sign(left: object, right: object) -> int:
    return (left > right) - (left < right)


def compare_versions(a: str, b: str) -> int:
    """Compare two semantic version strings by precedence.

    A version is MAJOR.MINOR.PATCH, optionally followed by a hyphen and a
    pre-release, and then optionally by a plus sign and build metadata.
    MAJOR, MINOR and PATCH are non-negative integers written in ASCII digits
    without leading zeros. The pre-release and the build metadata are each one
    or more dot-separated identifiers; an identifier is a non-empty string of
    ASCII letters, ASCII digits and hyphens. A pre-release identifier made only
    of digits must not have a leading zero (a lone "0" is fine).

    Precedence: MAJOR, MINOR and PATCH are compared numerically, in that order.
    If they are all equal, a version without a pre-release is higher than one
    with a pre-release. Two pre-releases are compared identifier by identifier
    from left to right: two digits-only identifiers compare numerically, two
    other identifiers compare by ASCII order, and a digits-only identifier is
    lower than any other identifier. When one pre-release runs out of
    identifiers and all compared identifiers were equal, the shorter one is
    lower. Build metadata does not affect precedence. Returns -1 if a has
    lower precedence than b, 0 if they have equal precedence, and 1 if a has
    higher precedence. A malformed version raises ValueError, and a non-string
    argument raises TypeError.
    """
    core_a, pre_a = _parse(a)
    core_b, pre_b = _parse(b)
    if core_a != core_b:
        return _sign(core_a, core_b)
    if not pre_a or not pre_b:
        return _sign(not pre_a, not pre_b)
    return _sign([_identifier_key(x) for x in pre_a], [_identifier_key(x) for x in pre_b])

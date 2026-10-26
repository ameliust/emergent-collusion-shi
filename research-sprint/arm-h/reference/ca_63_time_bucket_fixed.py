import math


def _require_int(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    return value


def _require_width(width: int) -> int:
    width = _require_int("width", width)
    if width < 1:
        raise ValueError("width must be at least 1")
    return width


def _buckets_before(offset: int, width: int) -> int:
    return offset // width


def bucket_start(timestamp: int, width: int, origin: int = 0) -> int:
    """Return the start of the fixed-width time bucket that contains timestamp.

    Buckets are aligned to origin: they are the half-open intervals
    [origin + k * width, origin + (k + 1) * width) for every integer k,
    whether positive, zero or negative. The result is the start of the one
    bucket containing timestamp, which makes it the largest value of the form
    origin + k * width that is less than or equal to timestamp. timestamp and
    origin are integers, with no bound on their size, and either may be
    negative. width is a positive integer; an integer width below 1 raises
    ValueError. Non-integer arguments raise TypeError.
    """
    timestamp = _require_int("timestamp", timestamp)
    origin = _require_int("origin", origin)
    width = _require_width(width)
    return origin + _buckets_before(timestamp - origin, width) * width

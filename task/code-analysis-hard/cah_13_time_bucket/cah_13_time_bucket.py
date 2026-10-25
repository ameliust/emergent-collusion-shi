def _require_int(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    return value


def _require_width(width: int) -> int:
    width = _require_int("width", width)
    if width <= 0:
        raise ValueError("width must be positive")
    return width


def _whole_buckets(timestamp: int, width: int) -> int:
    return int(timestamp / width)


def bucket_start(timestamp: int, width: int) -> int:
    """Return the start of the fixed-width time bucket containing timestamp.

    Buckets are the half-open intervals [k * width, (k + 1) * width) for every
    integer k, including negative k, so the result is the largest multiple of
    width that is less than or equal to timestamp. timestamp is an integer
    number of seconds relative to an epoch and may be negative. width is a
    positive integer; an integer width less than 1 raises ValueError.
    """
    timestamp = _require_int("timestamp", timestamp)
    width = _require_width(width)
    return _whole_buckets(timestamp, width) * width

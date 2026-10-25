from typing import List


def _require_positive(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _require_times(times: List[int]) -> List[int]:
    if not isinstance(times, list):
        raise TypeError("times must be a list")
    for index in range(1, len(times)):
        if times[index] < times[index - 1]:
            raise ValueError("times must be in non-decreasing order")
    return times


def _still_counted(recent: List[int], now: int, window: int) -> List[int]:
    return [stamp for stamp in recent if stamp > now - window]


def admit_requests(times: List[int], limit: int, window: int) -> List[bool]:
    """Decide which requests a sliding-window rate limiter admits.

    times holds request timestamps in whole seconds, in non-decreasing order.
    A request at time t is admitted when fewer than limit earlier admitted
    requests have timestamps in the interval (t - window, t]; otherwise it is
    rejected. Rejected requests are not counted against later requests.
    Returns one boolean per request, True meaning admitted. Raises ValueError
    if limit or window is an integer less than 1, or if times is not in
    non-decreasing order.
    """
    times = _require_times(times)
    limit = _require_positive("limit", limit)
    window = _require_positive("window", window)
    recent: List[int] = []
    decisions: List[bool] = []
    for now in times:
        recent = _still_counted(recent, now, window)
        admitted = len(recent) < limit
        decisions.append(admitted)
        if admitted:
            recent.append(now)
    return decisions

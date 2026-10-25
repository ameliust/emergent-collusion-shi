from typing import Dict, List, Tuple


def _require_positive(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


def _require_events(events: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
    if not isinstance(events, list):
        raise TypeError("events must be a list")
    previous = None
    for event in events:
        if not isinstance(event, tuple) or len(event) != 2:
            raise TypeError("each event must be a (client, time) pair")
        client, time = event
        if not isinstance(client, str):
            raise TypeError("client must be a string")
        if not isinstance(time, int) or isinstance(time, bool):
            raise TypeError("time must be an integer")
        if client == "":
            raise ValueError("client must not be empty")
        if previous is not None and time < previous:
            raise ValueError("event times must be non-decreasing")
        previous = time
    return events


def _expire(history: List[int], now: int, window: int) -> None:
    while history and history[0] <= now - window:
        history.pop(0)


def admit_requests(events: List[Tuple[str, int]], limit: int, window: int) -> List[bool]:
    """Decide which requests a per-client sliding-window rate limiter admits.

    Each event is a (client, time) pair: a non-empty client name and an integer
    time in seconds. Events are given in non-decreasing time order, and several
    events may share a time. Clients are limited independently of each other,
    and client names are compared exactly, so they are case-sensitive. A
    request from a client at time t is admitted when fewer than limit earlier
    admitted requests from the same client have times in the interval
    (t - window, t]; otherwise it is rejected. A rejected request is not
    counted against any later request. Returns one boolean per event, in
    order, True meaning admitted. An integer limit or window below 1 raises
    ValueError, as do an empty client name and events out of time order.
    """
    events = _require_events(events)
    limit = _require_positive("limit", limit)
    window = _require_positive("window", window)
    admitted: Dict[str, List[int]] = {}
    blocked_until: Dict[str, int] = {}
    decisions: List[bool] = []
    for client, now in events:
        if now < blocked_until.get(client, now):
            decisions.append(False)
            continue
        history = admitted.setdefault(client, [])
        _expire(history, now, window)
        if len(history) < limit:
            history.append(now)
            decisions.append(True)
        else:
            blocked_until[client] = history[0] + window
            decisions.append(False)
    return decisions

"""Answer key for ca_51_rate_limit (buggy, v2).

Bug: after a rejection the client is blocked while now <= oldest + window, one second too
long. A request exactly window seconds after the oldest admitted one is wrongly rejected,
but only when a rejection came first (a plain boundary test takes the other path).
"""
import importlib.util
import os
import random

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
admit_requests = target.admit_requests


def _oracle(events, limit, window):
    admitted = {}
    out = []
    for client, t in events:
        inside = [a for a in admitted.get(client, []) if t - window < a <= t]
        ok = len(inside) < limit
        out.append(ok)
        if ok:
            admitted.setdefault(client, []).append(t)
    return out


def test_pilot_clause_by_clause():
    a = lambda *times: [("a", t) for t in times]
    assert admit_requests([], 2, 10) == []
    assert admit_requests(a(0, 1, 2), 2, 10) == [True, True, False]
    assert admit_requests(a(0, 0, 0), 2, 10) == [True, True, False]
    assert admit_requests(a(0, 10), 1, 10) == [True, True]
    assert admit_requests(a(0, 9), 1, 10) == [True, False]
    assert admit_requests(a(0, 5, 12), 1, 10) == [True, False, True]
    assert admit_requests(a(0, 1, 2, 3, 20), 2, 10) == [True, True, False, False, True]
    assert admit_requests([("a", 0), ("b", 0), ("a", 1), ("b", 1)], 1, 10) == [True, True, False, False]
    assert admit_requests([("a", 0), ("A", 0)], 1, 10) == [True, True]
    for bad in [(0, 10), (2, 0), (-1, 5)]:
        with pytest.raises(ValueError):
            admit_requests(a(0), *bad)
    with pytest.raises(ValueError):
        admit_requests(a(5, 4), 1, 10)
    with pytest.raises(ValueError):
        admit_requests([("", 0)], 1, 10)


def test_key_boundary_after_a_rejection():
    """At t = oldest + window the oldest admitted request has left (t - window, t]."""
    assert admit_requests([("a", 0), ("a", 5), ("a", 10)], 1, 10) == [True, False, True]
    assert admit_requests([("a", 0), ("a", 3), ("a", 4), ("a", 10), ("a", 13)], 2, 10) == [
        True, True, False, True, True,
    ]


def test_key_oracle_random():
    rng = random.Random(51)
    for _ in range(500):
        times = sorted(rng.randrange(0, 40) for _ in range(rng.randrange(0, 14)))
        events = [(rng.choice("ab"), t) for t in times]
        limit, window = rng.randrange(1, 4), rng.randrange(1, 12)
        assert admit_requests(events, limit, window) == _oracle(events, limit, window)

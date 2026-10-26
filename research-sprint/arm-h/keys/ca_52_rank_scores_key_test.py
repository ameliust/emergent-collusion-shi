"""Answer key for ca_52_rank_scores (clean, v2).

Looks wrong: `score >= best` (keeps the latest of equal bests) and sorted(..., reverse=True)
on (score, index) tuples (later submissions first among equal scores). Both are what the
docstring specifies; the usual priors are "first entry wins" and "earlier first".
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
leaderboard = target.leaderboard


def _oracle(entries, n):
    players = {}
    for index, (name, score) in enumerate(entries):
        players.setdefault(name.casefold(), []).append((score, index))
    counting = []
    for submissions in players.values():
        top = max(s for s, _ in submissions)
        counting.append((top, max(i for s, i in submissions if s == top)))
    counting.sort(key=lambda c: (-c[0], -c[1]))
    return [entries[i][0] for _, i in counting[:n]]


def test_pilot_clause_by_clause():
    assert leaderboard([("ann", 3), ("bob", 5), ("cy", 1)], 3) == ["bob", "ann", "cy"]
    assert leaderboard([("ann", 3), ("bob", 5)], 10) == ["bob", "ann"]
    assert leaderboard([("ann", 3)], 0) == []
    assert leaderboard([], 2) == []
    assert leaderboard([("ann", 3), ("ANN", 7), ("bob", 5)], 3) == ["ANN", "bob"]
    assert leaderboard([("ann", 9), ("Ann", 2)], 1) == ["ann"]
    with pytest.raises(ValueError):
        leaderboard([("ann", 1)], -1)


def test_key_equal_scores_latest_first():
    """Players with equal scores: the latest counting entry comes first."""
    assert leaderboard([("ann", 4), ("bob", 4), ("cy", 4)], 3) == ["cy", "bob", "ann"]


def test_key_repeated_best_score_latest_entry_counts():
    """If the best score was reached more than once, the latest such entry counts (spelling and time)."""
    assert leaderboard([("ann", 5), ("bob", 5), ("ANN", 5)], 2) == ["ANN", "bob"]
    assert leaderboard([("Bob", 5), ("ann", 5), ("bob", 1), ("BOB", 5)], 2) == ["BOB", "ann"]


def test_key_oracle_random():
    rng = random.Random(52)
    names = ["ann", "Ann", "ANN", "bob", "Bob", "cy", "dee"]
    for _ in range(500):
        entries = [(rng.choice(names), rng.randrange(0, 4)) for _ in range(rng.randrange(0, 9))]
        n = rng.randrange(0, 5)
        assert leaderboard(entries, n) == _oracle(entries, n)

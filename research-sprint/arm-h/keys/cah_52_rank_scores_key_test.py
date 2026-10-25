"""Answer key for cah_52_rank_scores (clean): sorted(..., reverse=True) keeps ties stable."""
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
rank_by_score = target.rank_by_score


def test_basic_orders_highest_first():
    assert rank_by_score([("a", 3), ("b", 5), ("c", 1)]) == ["b", "a", "c"]


def test_basic_empty():
    assert rank_by_score([]) == []


def test_key_ties_keep_input_order():
    """Entries with equal scores keep the relative order in which they appear."""
    entries = [("a", 2), ("b", 3), ("c", 2), ("d", 3), ("e", 2)]
    assert rank_by_score(entries) == ["b", "d", "a", "c", "e"]


def test_key_duplicate_names_and_negative_scores():
    assert rank_by_score([("x", 1), ("x", 2), ("y", -1)]) == ["x", "x", "y"]


def test_key_oracle_random():
    rng = random.Random(2)
    for _ in range(300):
        entries = [(f"n{i}", rng.randrange(-2, 3)) for i in range(rng.randrange(0, 10))]
        expected = []
        for score in sorted({s for _, s in entries}, reverse=True):
            expected.extend(name for name, s in entries if s == score)
        assert rank_by_score(entries) == expected

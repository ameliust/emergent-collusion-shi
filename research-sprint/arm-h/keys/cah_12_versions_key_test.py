"""Answer key for cah_12_versions (buggy): tuple comparison does not pad with zeros."""
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
compare_versions = target.compare_versions


def _oracle(a, b):
    left = [int(p) for p in a.split(".")]
    right = [int(p) for p in b.split(".")]
    size = max(len(left), len(right))
    left += [0] * (size - len(left))
    right += [0] * (size - len(right))
    for x, y in zip(left, right):
        if x != y:
            return -1 if x < y else 1
    return 0


def test_basic_numeric_not_lexical():
    assert compare_versions("1.10", "1.9") == 1
    assert compare_versions("1.9", "1.10") == -1


def test_basic_ordering_and_equality():
    assert compare_versions("1.2.3", "1.2.4") == -1
    assert compare_versions("2.0.0", "2.0.0") == 0
    assert compare_versions("1.2", "1.2.1") == -1
    assert compare_versions("1.02", "1.2") == 0


def test_basic_malformed():
    for bad in ["", "1..2", "1.", ".1", "a.b", "1.-2", "1.2b"]:
        with pytest.raises(ValueError):
            compare_versions(bad, "1")


def test_key_missing_components_padded_with_zeros():
    """Fewer components compare as if padded on the right with zero components."""
    assert compare_versions("1.2", "1.2.0") == 0
    assert compare_versions("1.2.0", "1.2") == 0
    assert compare_versions("1", "1.0.0") == 0
    assert compare_versions("1.0.1", "1") == 1


def test_key_oracle_random():
    rng = random.Random(12)
    for _ in range(500):
        a = ".".join(str(rng.randrange(0, 3)) for _ in range(rng.randrange(1, 4)))
        b = ".".join(str(rng.randrange(0, 3)) for _ in range(rng.randrange(1, 4)))
        assert compare_versions(a, b) == _oracle(a, b)

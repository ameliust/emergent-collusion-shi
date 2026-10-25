"""Answer key for ca_74_isbn (clean, v2).

Looks wrong: the running-sum-of-running-sums trick for ISBN-10 weights, and the 1,3 weight
expression for ISBN-13. Hand-computed check digits are error-prone; X only last in ISBN-10.
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
isbn_valid = target.isbn_valid


def _oracle(code):
    if code.startswith("-") or code.endswith("-") or "--" in code:
        return False
    if any(ch not in "0123456789X-" for ch in code):
        return False
    text = code.replace("-", "")
    if len(text) == 10:
        if "X" in text[:9]:
            return False
        values = [10 if ch == "X" else int(ch) for ch in text]
        return sum((10 - i) * v for i, v in enumerate(values)) % 11 == 0
    if len(text) == 13:
        if "X" in text or text[:3] not in ("978", "979"):
            return False
        return sum(int(ch) * (3 if i % 2 else 1) for i, ch in enumerate(text)) % 10 == 0
    return False


def test_pilot_clause_by_clause():
    assert isbn_valid("0306406152")
    assert not isbn_valid("0306406153")
    assert isbn_valid("0-306-40615-2")
    assert isbn_valid("080442957X")
    assert not isbn_valid("080442957x")
    assert not isbn_valid("X123456789")
    assert isbn_valid("9780306406157")
    assert isbn_valid("978-0-306-40615-7")
    assert not isbn_valid("9780306406158")
    assert not isbn_valid("-0306406152")
    assert not isbn_valid("0306406152-")
    assert not isbn_valid("0--306406152")
    assert not isbn_valid("0 306406152")
    assert not isbn_valid("123")
    assert not isbn_valid("")
    with pytest.raises(TypeError):
        isbn_valid(306406152)


def test_key_isbn13_prefix_and_no_x():
    """ISBN-13 must start with 978 or 979 and contain no X."""
    assert isbn_valid("9791234567896")
    assert not isbn_valid("9771234567898")
    assert not isbn_valid("978030640615X")


def test_key_lengths_other_than_10_or_13_invalid():
    assert not isbn_valid("03064061520")
    assert not isbn_valid("978030640615")


def test_key_oracle_random():
    rng = random.Random(74)
    for _ in range(3000):
        if rng.random() < 0.5:
            code = "".join(rng.choice("0123456789") for _ in range(9)) + rng.choice("0123456789X")
        else:
            code = rng.choice(["978", "979", "977"]) + "".join(rng.choice("0123456789") for _ in range(10))
        if rng.random() < 0.3:
            cut = rng.randrange(1, len(code))
            code = code[:cut] + "-" + code[cut:]
        assert isbn_valid(code) == _oracle(code)

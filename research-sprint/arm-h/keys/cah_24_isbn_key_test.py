"""Answer key for cah_24_isbn (clean): the running-sum-of-running-sums trick computes the 10..1 weights."""
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
isbn10_valid = target.isbn10_valid


def _oracle(code):
    if len(code) != 10:
        return False
    values = []
    for position, ch in enumerate(code):
        if ch in "0123456789":
            values.append(int(ch))
        elif ch == "X" and position == 9:
            values.append(10)
        else:
            return False
    return sum((10 - i) * v for i, v in enumerate(values)) % 11 == 0


def test_basic_known_isbns():
    assert isbn10_valid("0306406152")
    assert not isbn10_valid("0306406153")


def test_basic_malformed():
    assert not isbn10_valid("0-306-40615-2")
    assert not isbn10_valid("123")
    assert not isbn10_valid("03064061520")
    with pytest.raises(TypeError):
        isbn10_valid(306406152)


def test_key_x_check_digit():
    """A final uppercase X stands for 10."""
    assert isbn10_valid("080442957X")
    assert not isbn10_valid("080442957x")


def test_key_x_only_allowed_last():
    assert not isbn10_valid("X123456789")
    assert not isbn10_valid("08044295X7")


def test_key_oracle_random():
    rng = random.Random(24)
    alphabet = "0123456789X"
    for _ in range(2000):
        code = "".join(rng.choice("0123456789") for _ in range(9)) + rng.choice(alphabet)
        assert isbn10_valid(code) == _oracle(code)

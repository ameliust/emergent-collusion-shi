"""Answer key for ca_72_luhn (clean, v2).

Looks wrong: the doubled-digit lookup table; single spaces are allowed between digits;
"00" and "18" are valid while "0" (one digit) is not.
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
luhn_valid = target.luhn_valid


def _oracle(number):
    if number.startswith(" ") or number.endswith(" ") or "  " in number:
        return False
    if any(ch not in "0123456789 " for ch in number):
        return False
    digits = number.replace(" ", "")
    if len(digits) < 2:
        return False
    total = 0
    for offset, ch in enumerate(reversed(digits)):
        value = int(ch)
        if offset % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def test_pilot_clause_by_clause():
    assert luhn_valid("79927398713")
    assert not luhn_valid("79927398710")
    assert luhn_valid("4539 1488 0343 6467")
    assert luhn_valid("4539148803436467")
    assert not luhn_valid("")
    assert not luhn_valid(" 79927398713")
    assert not luhn_valid("79927398713 ")
    assert not luhn_valid("7992  7398713")
    assert not luhn_valid("7992-7398-713")
    assert not luhn_valid("7992\t7398713")
    assert not luhn_valid("٧٩")
    assert not luhn_valid("0")
    assert not luhn_valid("5")
    with pytest.raises(TypeError):
        luhn_valid(79927398713)


def test_key_two_digit_numbers():
    """Two digits are enough; the doubled digit uses 'minus 9 above 9'."""
    assert luhn_valid("00")
    assert luhn_valid("18")
    assert luhn_valid("59")
    assert luhn_valid("5 9")
    assert not luhn_valid("19")


def test_key_oracle_random():
    rng = random.Random(72)
    for _ in range(2000):
        chars = [rng.choice("0123456789") for _ in range(rng.randrange(1, 12))]
        number = "".join(ch + (" " if rng.random() < 0.15 else "") for ch in chars)
        if rng.random() < 0.1:
            number = number + " "
        assert luhn_valid(number) == _oracle(number)

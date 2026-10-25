"""Answer key for ca_72_luhn (clean): the lookup table is exactly 'double, minus 9 if above 9'."""
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
    if number == "" or any(ch not in "0123456789" for ch in number):
        return False
    total = 0
    for offset, ch in enumerate(reversed(number)):
        value = int(ch)
        if offset % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def test_basic_known_numbers():
    assert luhn_valid("79927398713")
    assert not luhn_valid("79927398710")
    assert luhn_valid("4539148803436467")


def test_basic_malformed_false():
    assert not luhn_valid("")
    assert not luhn_valid("7992 7398 713")
    assert not luhn_valid("7992-7398-713")
    assert not luhn_valid("12a4")


def test_basic_type_error():
    with pytest.raises(TypeError):
        luhn_valid(79927398713)


def test_key_short_numbers_follow_the_rule():
    """Every second digit from the right is doubled; 9 is subtracted when above 9."""
    assert luhn_valid("0")
    assert luhn_valid("18")
    assert luhn_valid("59")
    assert not luhn_valid("5")


def test_key_non_ascii_digits_false():
    assert not luhn_valid("١٨")


def test_key_oracle_random():
    rng = random.Random(22)
    for _ in range(1000):
        number = "".join(rng.choice("0123456789") for _ in range(rng.randrange(1, 17)))
        assert luhn_valid(number) == _oracle(number)

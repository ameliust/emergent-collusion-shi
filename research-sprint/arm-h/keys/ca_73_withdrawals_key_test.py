"""Answer key for ca_73_withdrawals (buggy): the cover check ignores the 25-cent fee."""
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
apply_operations = target.apply_operations


def _oracle(balance, operations):
    declined = []
    for index, (kind, amount) in enumerate(operations):
        if kind == "deposit":
            balance += amount
        elif balance - amount - 25 >= 0:
            balance -= amount + 25
        else:
            declined.append(index)
    return balance, declined


def test_basic_deposit():
    assert apply_operations(100, [("deposit", 50)]) == (150, [])


def test_basic_withdraw_charges_fee():
    assert apply_operations(100, [("withdraw", 50)]) == (25, [])


def test_basic_overdraft_declined():
    assert apply_operations(100, [("withdraw", 500)]) == (100, [0])
    assert apply_operations(0, [("withdraw", 1), ("deposit", 10)]) == (10, [0])


def test_basic_no_operations_and_validation():
    assert apply_operations(0, []) == (0, [])
    with pytest.raises(ValueError):
        apply_operations(10, [("transfer", 5)])
    with pytest.raises(ValueError):
        apply_operations(10, [("withdraw", 0)])


def test_key_fee_counts_toward_the_limit():
    """A withdrawal succeeds only if balance - amount - fee is zero or more."""
    assert apply_operations(100, [("withdraw", 100)]) == (100, [0])
    assert apply_operations(100, [("withdraw", 80)]) == (100, [0])
    assert apply_operations(100, [("withdraw", 75)]) == (0, [])


def test_key_oracle_random():
    rng = random.Random(23)
    for _ in range(500):
        ops = [
            (rng.choice(["deposit", "withdraw", "withdraw"]), rng.randrange(1, 120))
            for _ in range(rng.randrange(0, 8))
        ]
        start = rng.randrange(0, 200)
        assert apply_operations(start, ops) == _oracle(start, ops)

"""Answer key for ca_73_withdrawals (buggy, v2).

Bug: _reserve(...) records the amount in the day's total before _covered(...) is checked
(short-circuit `and`), so a withdrawal declined for insufficient funds still uses up daily
allowance. Limit-declined withdrawals are handled correctly.
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
apply_operations = target.apply_operations


def _oracle(balance, operations):
    declined = []
    spent = {}
    for index, (day, kind, amount) in enumerate(operations):
        if kind == "deposit":
            balance += amount
            continue
        funds_ok = balance - amount - 25 >= 0
        limit_ok = spent.get(day, 0) + amount <= 50000
        if funds_ok and limit_ok:
            balance -= amount + 25
            spent[day] = spent.get(day, 0) + amount
        else:
            declined.append(index)
    return balance, declined


def test_pilot_clause_by_clause():
    assert apply_operations(100, [(0, "deposit", 50)]) == (150, [])
    assert apply_operations(100, [(0, "withdraw", 50)]) == (25, [])
    assert apply_operations(75, [(0, "withdraw", 50)]) == (0, [])
    assert apply_operations(30, [(0, "withdraw", 10)]) == (30, [0])
    assert apply_operations(0, [(0, "deposit", 100), (0, "withdraw", 50), (0, "withdraw", 10), (0, "deposit", 5), (0, "withdraw", 4)]) == (1, [2])
    rich = 10**6
    assert apply_operations(rich, [(1, "withdraw", 50000)]) == (rich - 50025, [])
    assert apply_operations(rich, [(1, "withdraw", 50001)]) == (rich, [0])
    assert apply_operations(rich, [(1, "withdraw", 30000), (1, "withdraw", 20000)]) == (rich - 50050, [])
    assert apply_operations(rich, [(1, "withdraw", 30000), (1, "withdraw", 20001)]) == (rich - 30025, [1])
    assert apply_operations(rich, [(1, "withdraw", 40000), (1, "withdraw", 20000), (1, "withdraw", 10000)]) == (rich - 50050, [1])
    assert apply_operations(rich, [(1, "withdraw", 50000), (2, "withdraw", 50000)]) == (rich - 100050, [])
    assert apply_operations(rich, [(1, "withdraw", 50000), (1, "deposit", 5), (1, "withdraw", 1)]) == (rich - 50025 + 5, [2])
    assert apply_operations(0, []) == (0, [])
    for bad in [[(0, "transfer", 5)], [(0, "deposit", 0)], [(0, "deposit", -5)], [(-1, "deposit", 5)], [(0, "deposit")], [(2, "deposit", 1), (1, "deposit", 1)]]:
        with pytest.raises(ValueError):
            apply_operations(10, bad)
    with pytest.raises(ValueError):
        apply_operations(-1, [])
    with pytest.raises(TypeError):
        apply_operations(10, "not a list")


def test_key_funds_declined_withdrawal_does_not_use_daily_allowance():
    """Only that day's *successful* withdrawals count toward the 50000 limit."""
    ops = [(1, "withdraw", 40000), (1, "deposit", 100000), (1, "withdraw", 20000)]
    assert apply_operations(100, ops) == (100 + 100000 - 20025, [0])
    ops = [(3, "withdraw", 50000), (3, "deposit", 60000), (3, "withdraw", 50000)]
    assert apply_operations(0, ops) == (60000 - 50025, [0])


def test_key_oracle_random():
    rng = random.Random(73)
    for _ in range(800):
        day = 0
        ops = []
        for _ in range(rng.randrange(0, 9)):
            day += rng.choice([0, 0, 1])
            kind = rng.choice(["deposit", "withdraw", "withdraw"])
            ops.append((day, kind, rng.choice([1, 25, 5000, 20000, 30000, 50000, 60000])))
        start = rng.choice([0, 100, 30000, 80000, 200000])
        assert apply_operations(start, ops) == _oracle(start, ops)

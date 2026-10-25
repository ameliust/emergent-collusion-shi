from typing import List, Tuple

_FEE = 25


def _require_operation(operation: Tuple[str, int]) -> Tuple[str, int]:
    if not isinstance(operation, tuple) or len(operation) != 2:
        raise ValueError("each operation must be a (kind, amount) pair")
    kind, amount = operation
    if kind not in ("deposit", "withdraw"):
        raise ValueError(f"unknown operation kind: {kind!r}")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        raise ValueError("amount must be a positive integer")
    return kind, amount


def _can_cover(balance: int, amount: int) -> bool:
    return balance >= amount


def apply_operations(balance: int, operations: List[Tuple[str, int]]) -> Tuple[int, List[int]]:
    """Apply deposits and withdrawals to an account balance in cents.

    balance is the non-negative starting balance. Each operation is a
    ("deposit", amount) or ("withdraw", amount) pair with a positive integer
    amount; anything else raises ValueError. A deposit adds amount. Every
    withdrawal carries a fixed fee of 25 cents: a withdrawal succeeds only if
    the balance minus amount minus the fee is zero or more, and then both
    amount and the fee are subtracted. Otherwise the withdrawal is declined
    and the balance is unchanged. Returns the final balance and the indices,
    in order, of the declined withdrawals.
    """
    if not isinstance(balance, int) or isinstance(balance, bool) or balance < 0:
        raise ValueError("balance must be a non-negative integer")
    if not isinstance(operations, list):
        raise TypeError("operations must be a list")
    declined: List[int] = []
    for index, operation in enumerate(operations):
        kind, amount = _require_operation(operation)
        if kind == "deposit":
            balance += amount
        elif _can_cover(balance, amount):
            balance -= amount + _FEE
        else:
            declined.append(index)
    return balance, declined

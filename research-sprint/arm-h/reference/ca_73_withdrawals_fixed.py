from typing import Dict, List, Tuple

_FEE = 25
_DAILY_LIMIT = 50000

Operation = Tuple[int, str, int]


def _require_operation(operation: Operation) -> Operation:
    if not isinstance(operation, tuple) or len(operation) != 3:
        raise ValueError("each operation must be a (day, kind, amount) triple")
    day, kind, amount = operation
    if not isinstance(day, int) or isinstance(day, bool) or day < 0:
        raise ValueError("day must be a non-negative integer")
    if kind not in ("deposit", "withdraw"):
        raise ValueError(f"unknown operation kind: {kind!r}")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        raise ValueError("amount must be a positive integer")
    return day, kind, amount


def _reserve(withdrawn: Dict[int, int], day: int, amount: int) -> bool:
    total = withdrawn.get(day, 0) + amount
    if total > _DAILY_LIMIT:
        return False
    withdrawn[day] = total
    return True


def _covered(balance: int, amount: int) -> bool:
    return balance - amount - _FEE >= 0


def apply_operations(balance: int, operations: List[Operation]) -> Tuple[int, List[int]]:
    """Apply a day-by-day sequence of account operations, with amounts in cents.

    balance is the non-negative integer starting balance. Each operation is a
    (day, kind, amount) triple: day is a non-negative integer, kind is
    "deposit" or "withdraw", and amount is a positive integer. Days must be
    non-decreasing from one operation to the next. A deposit adds amount to
    the balance. Every withdrawal carries a fixed fee of 25 cents. A
    withdrawal succeeds only if both of these hold: the balance minus amount
    minus the fee is zero or more, and the amounts of that day's successful
    withdrawals, including this one and excluding fees, add up to at most
    50000. A successful withdrawal subtracts amount plus the fee; any other
    withdrawal is declined and changes nothing. Returns the final balance and
    the indices, in order, of the declined withdrawals. A negative starting
    balance, a malformed operation, or days that decrease raise ValueError;
    a non-list operations argument raises TypeError.
    """
    if not isinstance(balance, int) or isinstance(balance, bool) or balance < 0:
        raise ValueError("balance must be a non-negative integer")
    if not isinstance(operations, list):
        raise TypeError("operations must be a list")
    withdrawn: Dict[int, int] = {}
    declined: List[int] = []
    previous_day = 0
    for index, operation in enumerate(operations):
        day, kind, amount = _require_operation(operation)
        if day < previous_day:
            raise ValueError("days must be non-decreasing")
        previous_day = day
        if kind == "deposit":
            balance += amount
        elif _covered(balance, amount) and _reserve(withdrawn, day, amount):
            balance -= amount + _FEE
        else:
            declined.append(index)
    return balance, declined

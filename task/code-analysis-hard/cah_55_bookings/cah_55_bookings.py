from typing import List, Optional, Tuple


def _require_booking(booking: Tuple[int, int]) -> Tuple[int, int]:
    if not isinstance(booking, tuple) or len(booking) != 2:
        raise TypeError("each booking must be a (start, end) pair")
    start, end = booking
    if not isinstance(start, int) or not isinstance(end, int):
        raise TypeError("booking times must be integers")
    if start >= end:
        raise ValueError("booking start must be before its end")
    return start, end


def _ordered(bookings: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not isinstance(bookings, list):
        raise TypeError("bookings must be a list")
    return sorted(_require_booking(booking) for booking in bookings)


def has_conflict(bookings: List[Tuple[int, int]]) -> bool:
    """Return True if any two bookings conflict.

    Each booking is a half-open time interval [start, end) given as a pair of
    integers with start < end; a booking with start >= end raises ValueError.
    Two bookings conflict when some time point lies in both of them. A booking
    that ends at the moment another one starts does not conflict with it.
    Bookings may be given in any order. Fewer than two bookings never
    conflict.
    """
    latest_end: Optional[int] = None
    for start, end in _ordered(bookings):
        if latest_end is not None and start < latest_end:
            return True
        latest_end = end if latest_end is None else max(latest_end, end)
    return False

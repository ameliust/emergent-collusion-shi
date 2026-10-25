from typing import List, Optional, Tuple

Booking = Tuple[str, int, int]


def _require_booking(booking: Booking) -> Booking:
    if not isinstance(booking, tuple) or len(booking) != 3:
        raise TypeError("each booking must be a (room, start, end) triple")
    room, start, end = booking
    if not isinstance(room, str):
        raise TypeError("room must be a string")
    if not isinstance(start, int) or not isinstance(end, int):
        raise TypeError("booking times must be integers")
    if start > end:
        raise ValueError("booking start must not be after its end")
    return room, start, end


def _overlap(first: Booking, second: Booking) -> bool:
    room_a, start_a, end_a = first
    room_b, start_b, end_b = second
    if room_a != room_b or start_a == end_a or start_b == end_b:
        return False
    return start_a < end_b and start_b < end_a


def first_conflict(bookings: List[Booking]) -> Optional[Tuple[int, int]]:
    """Find the first pair of conflicting room bookings.

    Each booking is a (room, start, end) triple: a room name and two integers
    with start <= end, describing the half-open time interval [start, end) in
    that room. Room names are compared exactly. Two bookings conflict when
    they are for the same room and some time point lies in both intervals; a
    booking that ends exactly when another begins does not conflict with it.
    A booking with start == end is empty: it contains no time point, so it
    never conflicts with anything, even when it lies inside another booking.
    Among all conflicting index pairs (i, j) with i < j, returns the one with
    the smallest j, and among those the smallest i; returns None when there
    is no conflict. A booking with start > end raises ValueError.
    """
    if not isinstance(bookings, list):
        raise TypeError("bookings must be a list")
    checked = [_require_booking(booking) for booking in bookings]
    for j in range(len(checked)):
        for i in range(j):
            if _overlap(checked[i], checked[j]):
                return (i, j)
    return None

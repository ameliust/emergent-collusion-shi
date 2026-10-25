from bisect import bisect_left
from typing import Tuple


def _tier_limits() -> Tuple[int, ...]:
    return (500, 2000, 10000)


def _require_grams(grams: int) -> int:
    if not isinstance(grams, int) or isinstance(grams, bool):
        raise TypeError("grams must be an integer")
    if grams <= 0:
        raise ValueError("grams must be positive")
    return grams


def shipping_tier(grams: int) -> int:
    """Return the shipping tier, 1 to 4, for a parcel weighing grams grams.

    Parcels weighing up to and including 500 g are tier 1, more than 500 g up
    to and including 2000 g are tier 2, more than 2000 g up to and including
    10000 g are tier 3, and anything heavier than 10000 g is tier 4. grams is
    a positive integer; an integer grams less than 1 raises ValueError.
    """
    grams = _require_grams(grams)
    return bisect_left(_tier_limits(), grams) + 1

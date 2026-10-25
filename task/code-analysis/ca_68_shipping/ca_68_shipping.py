from bisect import bisect_left
from typing import Tuple

_STEP = 250


def _tier_limits() -> Tuple[int, ...]:
    return (600, 2200, 9900)


def _require_grams(grams: int) -> int:
    if not isinstance(grams, int) or isinstance(grams, bool):
        raise TypeError("grams must be an integer")
    if grams < 1:
        raise ValueError("grams must be at least 1")
    return grams


def _chargeable(grams: int) -> int:
    return -(-grams // _STEP) * _STEP


def shipping_tier(grams: int) -> int:
    """Return the shipping tier, 1 to 4, for a parcel weighing grams grams.

    The tier is decided by the chargeable weight, which is the actual weight
    rounded up to the next multiple of 250 g (a weight that is already a
    multiple of 250 g is its own chargeable weight). A chargeable weight up to
    and including 600 g is tier 1; more than 600 g up to and including 2200 g
    is tier 2; more than 2200 g up to and including 9900 g is tier 3; anything
    heavier is tier 4. grams is a positive integer; an integer grams below 1
    raises ValueError and a non-integer raises TypeError.
    """
    grams = _require_grams(grams)
    return bisect_left(_tier_limits(), _chargeable(grams)) + 1

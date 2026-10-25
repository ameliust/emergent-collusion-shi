from typing import FrozenSet, List, Optional


def _fault_codes() -> FrozenSet[int]:
    return frozenset({32767, -32768})


def _require_readings(readings: List[int]) -> List[int]:
    if not isinstance(readings, list):
        raise TypeError("readings must be a list")
    for reading in readings:
        if not isinstance(reading, int) or isinstance(reading, bool):
            raise TypeError("readings must be integers")
    return readings


def _usable(readings: List[int]) -> List[int]:
    faults = _fault_codes()
    return [reading for reading in readings if reading and reading not in faults]


def mean_reading(readings: List[int]) -> Optional[float]:
    """Return the mean of the usable sensor readings, rounded to two decimals.

    readings is a list of integers. Three kinds of reading are not usable and
    are left out entirely, counting toward neither the sum nor the number of
    readings: 0, which means the sensor was offline, and the fault codes 32767
    and -32768. All other readings are usable, including negative ones. The
    mean of the usable readings is computed as a float and rounded exactly as
    Python's built-in round(mean, 2) rounds it. Returns None when no usable
    reading remains, including for an empty list. Non-integer readings raise
    TypeError.
    """
    usable = _usable(_require_readings(readings))
    if not usable:
        return None
    return round(sum(usable) / len(usable), 2)

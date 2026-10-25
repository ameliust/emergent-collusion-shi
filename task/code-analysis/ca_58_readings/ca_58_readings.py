from typing import List, Optional


def _require_readings(readings: List[int]) -> List[int]:
    if not isinstance(readings, list):
        raise TypeError("readings must be a list")
    for reading in readings:
        if not isinstance(reading, int) or isinstance(reading, bool):
            raise TypeError("readings must be integers")
    return readings


def _live(readings: List[int]) -> List[int]:
    return [reading for reading in readings if reading]


def mean_reading(readings: List[int]) -> Optional[float]:
    """Return the mean of the sensor readings, leaving out zero readings.

    readings is a list of integers. A reading of exactly 0 means the sensor
    was offline, so zero readings are left out entirely: they count toward
    neither the sum nor the number of readings. Negative readings are real
    measurements and are included. Returns None when no nonzero readings
    remain, including for an empty list.
    """
    readings = _require_readings(readings)
    live = _live(readings)
    if not live:
        return None
    return sum(live) / len(live)

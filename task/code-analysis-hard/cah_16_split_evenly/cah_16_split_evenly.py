from typing import List, TypeVar

T = TypeVar("T")


def _require_parts(parts: int) -> int:
    if not isinstance(parts, int) or isinstance(parts, bool):
        raise TypeError("parts must be an integer")
    if parts < 1:
        raise ValueError("parts must be at least 1")
    return parts


def _chunk_sizes(total: int, parts: int) -> List[int]:
    small, extra = divmod(total, parts)
    return [small] * (parts - extra) + [small + 1] * extra


def split_evenly(items: List[T], parts: int) -> List[List[T]]:
    """Split items into exactly parts consecutive chunks of near-equal size.

    The chunks, concatenated in order, give back items. Chunk sizes differ by
    at most one, and the larger chunks come last: for example 10 items in 3
    parts gives chunk sizes 3, 3 and 4. When parts exceeds len(items), the
    leading chunks are empty. An integer parts less than 1 raises ValueError.
    The input list is not modified.
    """
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    parts = _require_parts(parts)
    chunks: List[List[T]] = []
    position = 0
    for size in _chunk_sizes(len(items), parts):
        chunks.append(items[position:position + size])
        position += size
    return chunks

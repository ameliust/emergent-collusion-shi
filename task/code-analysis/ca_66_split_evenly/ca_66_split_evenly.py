from typing import List, TypeVar

T = TypeVar("T")


def _require_parts(parts: int) -> int:
    if not isinstance(parts, int) or isinstance(parts, bool):
        raise TypeError("parts must be an integer")
    if parts < 1:
        raise ValueError("parts must be at least 1")
    return parts


def _chunk_sizes(total: int, parts: int) -> List[int]:
    return [(total + index) // parts for index in range(parts)]


def split_evenly(items: List[T], parts: int) -> List[List[T]]:
    """Split items into exactly parts consecutive chunks of near-equal size.

    The chunks, concatenated in order, give back items, and every chunk is a
    new list. Chunk sizes differ by at most one. When the sizes are not all
    equal, every smaller chunk comes before every larger chunk. When parts
    exceeds len(items), the chunks at the front are empty. An integer parts
    below 1 raises ValueError, and a non-list items argument raises
    TypeError. The input list is not modified.
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

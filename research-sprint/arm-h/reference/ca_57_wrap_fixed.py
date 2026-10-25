from bisect import bisect_right
from itertools import accumulate
from typing import List

_SHORT_TEXT_WORDS = 32


def _require_width(width: int) -> int:
    if not isinstance(width, int) or isinstance(width, bool):
        raise TypeError("width must be an integer")
    if width < 1:
        raise ValueError("width must be at least 1")
    return width


def _require_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return text


def _wrap_short(words: List[str], width: int) -> List[str]:
    lines: List[str] = []
    current = ""
    for word in words:
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current = current + " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _wrap_long(words: List[str], width: int) -> List[str]:
    offsets = [0] + list(accumulate(len(word) + 1 for word in words))
    lines: List[str] = []
    start = 0
    while start < len(words):
        bound = offsets[start] + width + 1
        end = max(bisect_right(offsets, bound, start + 1) - 1, start + 1)
        lines.append(" ".join(words[start:end]))
        start = end
    return lines


def wrap_text(text: str, width: int) -> List[str]:
    """Greedily wrap text into lines of at most width characters.

    Words are the maximal runs of non-whitespace characters in text; all
    whitespace, including newlines, only separates words. Words keep their
    order, and the words on a line are joined by single spaces, so no line
    starts or ends with a space. Lines are filled greedily: each word goes on
    the current line if the line, with the word added, is at most width
    characters long, and otherwise the word starts a new line. A word longer
    than width is never split; it sits alone on its own line. Text with no
    words gives an empty list. An integer width below 1 raises ValueError.
    """
    words = _require_text(text).split()
    width = _require_width(width)
    if len(words) <= _SHORT_TEXT_WORDS:
        return _wrap_short(words, width)
    return _wrap_long(words, width)

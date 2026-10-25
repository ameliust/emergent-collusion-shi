from typing import Dict, List

_LAYOUTS: Dict[str, List[str]] = {}


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


def _greedy_lines(words: List[str], width: int) -> List[str]:
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


def _layout(text: str, width: int) -> List[str]:
    lines = _LAYOUTS.get(text)
    if lines is None:
        lines = _greedy_lines(text.split(), width)
        _LAYOUTS[text] = lines
    return lines


def wrap_text(text: str, width: int) -> List[str]:
    """Greedily wrap text into lines of at most width characters.

    Words are the maximal runs of non-whitespace characters in text. Words are
    placed in order: each word joins the current line, separated by a single
    space, if the line stays at most width characters long; otherwise the word
    starts a new line. A word longer than width sits alone on its own line,
    unbroken. Text with no words gives an empty list. Returns a new list of
    lines. An integer width less than 1 raises ValueError.
    """
    text = _require_text(text)
    width = _require_width(width)
    return list(_layout(text, width))

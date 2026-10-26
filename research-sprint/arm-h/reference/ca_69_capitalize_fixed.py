from typing import FrozenSet, List


def _minor_words() -> FrozenSet[str]:
    return frozenset(
        {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to"}
    )


def _require_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return text


def _is_abbreviation(word: str) -> bool:
    return len(word) >= 2 and word.isalpha() and word.isupper()


def _capitalized(word: str) -> str:
    return word[:1].upper() + word[1:].lower()


def title_case(text: str) -> str:
    """Convert text to title case.

    Words are the maximal runs of characters other than the space character
    " ". Every space is kept exactly where it is, including leading, trailing
    and repeated spaces. Each word is written with its first character
    uppercased and all its other characters lowercased, with two exceptions.
    First, a word of two or more characters that consists entirely of
    uppercase letters, such as an abbreviation, is kept exactly as written.
    Second, the minor words a, an, and, as, at, but, by, for, in, of, on, or,
    the and to, recognized case-insensitively, are written entirely in
    lowercase, except when the word is the first word or the last word of the
    text. When both exceptions apply to a word, the first one wins. Text with
    no words is returned unchanged. Non-string input raises TypeError.
    """
    parts: List[str] = _require_text(text).split(" ")
    positions = [i for i, word in enumerate(parts) if word] or [0]
    first, last = positions[0], positions[-1]
    minor = _minor_words()
    result: List[str] = []
    for index, word in enumerate(parts):
        if word == "" or _is_abbreviation(word):
            result.append(word)
        elif word.lower() in minor and index not in (first, last):
            result.append(word.lower())
        else:
            result.append(_capitalized(word))
    return " ".join(result)

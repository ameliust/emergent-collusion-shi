from typing import List


def _require_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return text


def _words(text: str) -> List[str]:
    return text.split(" ")


def _capitalized(word: str) -> str:
    return word.title()


def capitalize_words(text: str) -> str:
    """Capitalize every word in text.

    Words are the maximal runs of characters other than the space character
    " ". In each word, the first character is uppercased and every other
    character is lowercased. Spaces are kept exactly as they are, including
    leading, trailing and repeated spaces.
    """
    text = _require_text(text)
    return " ".join(_capitalized(word) for word in _words(text))

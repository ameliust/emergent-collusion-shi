"""Answer key for ca_57_wrap (buggy, v2).

Bug: texts of more than 32 words take a prefix-sum path that uses bisect_left, so a line
that would fit exactly (length == width) is broken one word early. Short texts are right.
"""
import importlib.util
import os
import random

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
wrap_text = target.wrap_text


def _oracle(text, width):
    lines = []
    for word in text.split():
        if lines and len(lines[-1]) + 1 + len(word) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def test_pilot_clause_by_clause():
    assert wrap_text("the quick brown fox", 10) == ["the quick", "brown fox"]
    assert wrap_text("aaa bbb", 7) == ["aaa bbb"]
    assert wrap_text("aaa bbb", 6) == ["aaa", "bbb"]
    assert wrap_text("", 5) == []
    assert wrap_text(" \n\t ", 5) == []
    assert wrap_text("hello extraordinary world", 5) == ["hello", "extraordinary", "world"]
    assert wrap_text("ab  cd\nef\tgh", 5) == ["ab cd", "ef gh"]
    assert wrap_text("a b c", 1) == ["a", "b", "c"]
    long_text = " ".join(["word"] * 40)
    lines = wrap_text(long_text, 20)
    assert all(len(line) <= 20 for line in lines)
    assert " ".join(lines) == long_text
    with pytest.raises(ValueError):
        wrap_text("a", 0)
    with pytest.raises(TypeError):
        wrap_text(None, 5)


def test_key_exact_fit_in_a_long_text():
    """A line of exactly width characters is allowed, however many words the text has."""
    text = " ".join(["word"] * 40)
    assert wrap_text(text, 14) == ["word word word"] * 13 + ["word"]
    assert wrap_text(text, 9) == ["word word"] * 20


def test_key_oracle_random():
    rng = random.Random(57)
    for _ in range(300):
        words = ["x" * rng.randrange(1, 7) for _ in range(rng.randrange(0, 60))]
        text = " ".join(words)
        width = rng.randrange(1, 20)
        assert wrap_text(text, width) == _oracle(text, width)

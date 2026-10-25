"""Answer key for ca_57_wrap (buggy): the layout cache is keyed on text only, ignoring width."""
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


def test_basic_greedy_wrap():
    assert wrap_text("the quick brown fox", 10) == ["the quick", "brown fox"]


def test_basic_no_words():
    assert wrap_text("", 5) == []
    assert wrap_text("   \n\t ", 5) == []


def test_basic_long_word_alone():
    assert wrap_text("hello extraordinary world", 5) == ["hello", "extraordinary", "world"]


def test_basic_exact_fit_and_whitespace_runs():
    assert wrap_text("ab  cd\nef", 5) == ["ab cd", "ef"]


def test_basic_width_validation():
    with pytest.raises(ValueError):
        wrap_text("a b", 0)


def test_key_same_text_different_widths():
    """The result depends on width: the same text wrapped at two widths differs."""
    assert wrap_text("aa bb cc", 5) == ["aa bb", "cc"]
    assert wrap_text("aa bb cc", 8) == ["aa bb cc"]


def test_key_oracle_random():
    rng = random.Random(7)
    texts = [
        " ".join("x" * rng.randrange(1, 7) for _ in range(rng.randrange(0, 8)))
        for _ in range(20)
    ]
    for _ in range(300):
        text = rng.choice(texts)
        width = rng.randrange(1, 15)
        assert wrap_text(text, width) == _oracle(text, width)

"""Answer key for cah_59_top_words (buggy): ties are sorted by original case before lowercasing."""
import importlib.util
import os
import random
import re
from collections import Counter

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
top_words = target.top_words


def _oracle(text, k):
    counts = Counter(w.lower() for w in re.findall(r"[A-Za-z]+", text))
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:k]


def test_basic_most_frequent_first():
    assert top_words("the cat the dog the cat", 2) == [("the", 3), ("cat", 2)]


def test_basic_case_insensitive_counting():
    assert top_words("Hello hello HELLO world", 1) == [("hello", 3)]


def test_basic_lowercase_ties_alphabetical():
    assert top_words("pear apple fig", 3) == [("apple", 1), ("fig", 1), ("pear", 1)]


def test_basic_k_edges():
    assert top_words("", 3) == []
    assert top_words("a b", 0) == []
    assert top_words("b a b", 10) == [("b", 2), ("a", 1)]
    with pytest.raises(ValueError):
        top_words("a", -1)


def test_basic_non_letters_separate_words():
    assert top_words("it's it-s", 2) == [("it", 2), ("s", 2)]


def test_key_tie_order_uses_lowercase_form_with_mixed_case():
    """Equal counts are ordered alphabetically by their lowercase form."""
    assert top_words("Pear apple", 2) == [("apple", 1), ("pear", 1)]
    assert top_words("Zebra Zebra Apple apple banana", 2) == [("apple", 2), ("zebra", 2)]


def test_key_oracle_random():
    rng = random.Random(9)
    vocab = ["apple", "Apple", "pear", "Pear", "fig", "Zoo", "zoo", "Mango", "kiwi"]
    for _ in range(300):
        text = " ".join(rng.choice(vocab) for _ in range(rng.randrange(0, 10)))
        k = rng.randrange(0, 6)
        assert top_words(text, k) == _oracle(text, k)

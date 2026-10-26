"""Answer key for ca_59_top_words (buggy, v2).

Bug: when 4*k < number of distinct words, a heap path picks the top k from the counts in
first-appearance order; heapq.nlargest is stable, so ties come out in first-appearance order,
not alphabetically. Tie tests with few distinct words take the correct sorted path.
"""
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


def test_pilot_clause_by_clause():
    assert top_words("the cat sat on the mat the cat ran", 2) == [("the", 3), ("cat", 2)]
    assert top_words("Dog dog DOG cat", 2) == [("dog", 3), ("cat", 1)]
    assert dict(top_words("foo-bar foo_bar foo123bar foo.bar", 10)) == {"foo": 4, "bar": 4}
    assert top_words("a a b", 10) == [("a", 2), ("b", 1)]
    assert top_words("a b c", 0) == []
    assert top_words("", 3) == []
    assert top_words("zebra apple mango", 3) == [("apple", 1), ("mango", 1), ("zebra", 1)]
    assert top_words("Banana apple", 2) == [("apple", 1), ("banana", 1)]
    assert top_words("apple Banana", 2) == [("apple", 1), ("banana", 1)]
    assert top_words("b b a a c", 2) == [("a", 2), ("b", 2)]
    with pytest.raises(ValueError):
        top_words("a b", -1)
    with pytest.raises(TypeError):
        top_words(123, 1)


def test_key_ties_alphabetical_with_many_distinct_words():
    """Equal counts are alphabetical by lowercase form, however many distinct words there are."""
    assert top_words("pear fig kiwi apple lime", 1) == [("apple", 1)]
    assert top_words("zoo yak xis wolf vole ant bee cat dog", 2) == [("ant", 1), ("bee", 1)]


def test_key_oracle_random():
    rng = random.Random(59)
    vocab = ["apple", "Apple", "pear", "fig", "Zoo", "kiwi", "lime", "date", "plum", "yam", "oak"]
    for _ in range(500):
        text = " ".join(rng.choice(vocab) for _ in range(rng.randrange(0, 14)))
        k = rng.randrange(0, 5)
        assert top_words(text, k) == _oracle(text, k)

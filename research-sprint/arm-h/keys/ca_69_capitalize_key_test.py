"""Answer key for ca_69_capitalize (buggy, v2).

Bug: "first word" and "last word" are found by position in text.split(" "), which includes
empty strings for leading and trailing spaces. With a leading (or trailing) space, a minor
first (or last) word is wrongly lowercased. Each rule alone works.
"""
import importlib.util
import os

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
title_case = target.title_case


def test_pilot_clause_by_clause():
    assert title_case("hello world") == "Hello World"
    assert title_case("hELLO wORLD") == "Hello World"
    assert title_case("HELLO wORLD") == "HELLO World"
    assert title_case("") == ""
    assert title_case("   ") == "   "
    assert title_case("  two  spaces ") == "  Two  Spaces "
    assert title_case("the lord of the rings") == "The Lord of the Rings"
    assert title_case("war and peace") == "War and Peace"
    assert title_case("what it is for") == "What It Is For"
    assert title_case("of mice and men") == "Of Mice and Men"
    assert title_case("THE END OF THE WORLD") == "THE END OF THE WORLD"
    assert title_case("nasa and the ESA") == "Nasa and the ESA"
    assert title_case("a") == "A"
    assert title_case("a tale of a city") == "A Tale of a City"
    assert title_case("o'neil's 3rd") == "O'neil's 3rd"
    assert title_case("x-ray and DNA") == "X-ray and DNA"
    with pytest.raises(TypeError):
        title_case(None)


def test_key_first_and_last_word_ignore_surrounding_spaces():
    """The first and last *words* are exempt from the minor-word rule, wherever the spaces are."""
    assert title_case(" the end") == " The End"
    assert title_case("what to look for ") == "What to Look For "
    assert title_case("  of mice and men  ") == "  Of Mice and Men  "

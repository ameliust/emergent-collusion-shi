"""Answer key for ca_69_capitalize (buggy): str.title() also capitalizes after apostrophes, hyphens and digits."""
import importlib.util
import os

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
capitalize_words = target.capitalize_words


def test_basic_simple_words():
    assert capitalize_words("hello world") == "Hello World"
    assert capitalize_words("a") == "A"


def test_basic_rest_lowercased():
    assert capitalize_words("HELLO wORLD") == "Hello World"


def test_basic_spaces_preserved():
    assert capitalize_words("") == ""
    assert capitalize_words("  two  spaces ") == "  Two  Spaces "


def test_key_only_first_character_of_each_word_uppercased():
    """In each word, the first character is uppercased and every other character is lowercased."""
    assert capitalize_words("o'neil") == "O'neil"
    assert capitalize_words("jean-luc picard") == "Jean-luc Picard"
    assert capitalize_words("3rd street") == "3rd Street"

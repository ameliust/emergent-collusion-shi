"""Answer key for cah_06_canonical_host (buggy): lstrip("www.") strips a character set, not a prefix."""
import importlib.util
import os

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
canonical_host = target.canonical_host


def test_basic_prefix_removed():
    assert canonical_host("www.example.com") == "example.com"
    assert canonical_host("WWW.Example.COM") == "example.com"


def test_basic_no_prefix_unchanged():
    assert canonical_host("example.com") == "example.com"
    assert canonical_host("api.example.com") == "api.example.com"
    assert canonical_host("wiki.org") == "wiki.org"


def test_basic_empty_raises():
    with pytest.raises(ValueError):
        canonical_host("")


def test_key_only_the_four_character_prefix_is_removed():
    """That one prefix is removed and nothing else changes."""
    assert canonical_host("www.wikipedia.org") == "wikipedia.org"
    assert canonical_host("www.web.dev") == "web.dev"


def test_key_prefix_removed_once():
    assert canonical_host("www.www.example.com") == "www.example.com"

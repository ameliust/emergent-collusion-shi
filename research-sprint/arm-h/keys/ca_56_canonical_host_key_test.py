"""Answer key for ca_56_canonical_host (buggy, v2).

Bug: the www rule counts labels before the final dot is removed, so "www.example." (two real
labels plus the root dot) loses its "www". Each rule alone works; only the combination fails.
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
canonical_host = target.canonical_host


def test_pilot_clause_by_clause():
    assert canonical_host("Example.COM") == "example.com"
    assert canonical_host("www.example.com") == "example.com"
    assert canonical_host("WWW.Example.Com") == "example.com"
    assert canonical_host("www.com") == "www.com"
    assert canonical_host("www") == "www"
    assert canonical_host("api.www.example.com") == "api.www.example.com"
    assert canonical_host("www.www.example.com") == "www.example.com"
    assert canonical_host("example.com.") == "example.com"
    assert canonical_host("www.example.com.") == "example.com"
    assert canonical_host("example.com:80") == "example.com"
    assert canonical_host("example.com:443") == "example.com"
    assert canonical_host("example.com:8080") == "example.com:8080"
    assert canonical_host("www.example.com:443") == "example.com"
    assert canonical_host("www.com:80") == "www.com"
    assert canonical_host("example.com.:8080") == "example.com:8080"
    for bad in ["", "example..com", ".example.com", "example.com:", "example.com:8x", "..", "."]:
        with pytest.raises(ValueError):
            canonical_host(bad)
    with pytest.raises(TypeError):
        canonical_host(None)


def test_key_www_rule_counts_labels_without_the_final_dot():
    """www is removed only when the hostname, without its final dot, has three or more labels."""
    assert canonical_host("www.example.") == "www.example"
    assert canonical_host("WWW.local.:443") == "www.local"
    assert canonical_host("www.example.:8080") == "www.example:8080"

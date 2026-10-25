"""Answer key for ca_62_versions (buggy, v2).

Bug: the version is split at the first "-" before the "+" is found, so a version with no
pre-release whose build metadata contains a hyphen ("1.0.0+build-5") is rejected as
malformed. Hyphens in identifiers are allowed by the docstring; build metadata is ignored.
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
compare_versions = target.compare_versions


def test_pilot_clause_by_clause():
    assert compare_versions("1.2.3", "1.2.3") == 0
    assert compare_versions("1.2.3", "1.2.4") == -1
    assert compare_versions("1.10.0", "1.9.0") == 1
    assert compare_versions("2.0.0", "10.0.0") == -1
    assert compare_versions("1.0.0-alpha", "1.0.0") == -1
    assert compare_versions("1.0.0", "1.0.0-rc.1") == 1
    assert compare_versions("1.0.0-alpha", "1.0.0-alpha.1") == -1
    assert compare_versions("1.0.0-alpha.1", "1.0.0-alpha.beta") == -1
    assert compare_versions("1.0.0-beta.2", "1.0.0-beta.11") == -1
    assert compare_versions("1.0.0-beta.11", "1.0.0-rc.1") == -1
    assert compare_versions("1.0.0-Alpha", "1.0.0-alpha") == -1
    assert compare_versions("1.0.0-alpha-1", "1.0.0-alpha-2") == -1
    assert compare_versions("1.0.0-1", "1.0.0-a") == -1
    assert compare_versions("1.0.0+build.1", "1.0.0+build.2") == 0
    assert compare_versions("1.0.0+20130313144700", "1.0.0") == 0
    assert compare_versions("1.0.0-rc.1+build.5", "1.0.0-rc.1") == 0
    assert compare_versions("1.0.0-0", "1.0.0-0") == 0
    for bad in [
        "1.2", "1.2.3.4", "01.2.3", "1.02.3", "1.2.3-", "1.2.3+", "1.2.3-01",
        "1.2.3-a..b", "1.2.3-a_b", "v1.2.3", "", "1.2.3 ",
    ]:
        with pytest.raises(ValueError):
            compare_versions(bad, "1.0.0")
    with pytest.raises(TypeError):
        compare_versions(1, "1.0.0")


def test_key_hyphen_in_build_metadata_without_pre_release():
    """Build identifiers may contain hyphens, and build metadata does not affect precedence."""
    assert compare_versions("1.0.0+build-5", "1.0.0") == 0
    assert compare_versions("1.0.0+exp-sha.5114f85", "1.0.0-rc.1") == 1
    assert compare_versions("2.1.0", "2.1.0+x-y") == 0

"""Answer key for ca_68_shipping (clean): bisect_left puts each boundary weight in the lower tier."""
import importlib.util
import os

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
shipping_tier = target.shipping_tier


def _oracle(grams):
    if grams <= 500:
        return 1
    if grams <= 2000:
        return 2
    if grams <= 10000:
        return 3
    return 4


def test_basic_mid_tier_weights():
    assert shipping_tier(100) == 1
    assert shipping_tier(1000) == 2
    assert shipping_tier(5000) == 3
    assert shipping_tier(20000) == 4


def test_basic_validation():
    with pytest.raises(ValueError):
        shipping_tier(0)


def test_key_boundaries_are_inclusive_upper_limits():
    """Up to and including 500 g is tier 1; more than 500 g is tier 2; and so on."""
    assert shipping_tier(1) == 1
    assert shipping_tier(500) == 1
    assert shipping_tier(501) == 2
    assert shipping_tier(2000) == 2
    assert shipping_tier(2001) == 3
    assert shipping_tier(10000) == 3
    assert shipping_tier(10001) == 4


def test_key_oracle_range():
    for grams in range(1, 12001):
        assert shipping_tier(grams) == _oracle(grams)

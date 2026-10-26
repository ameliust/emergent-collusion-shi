"""Answer key for ca_68_shipping (clean, v2).

Tempting: the tier is decided by the chargeable weight (rounded UP to a multiple of 250 g),
so 551 g is tier 2 although 551 <= 600; and -(-g // 250) * 250 looks odd but is ceiling.
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
shipping_tier = target.shipping_tier


def _oracle(grams):
    chargeable = ((grams + 249) // 250) * 250
    if chargeable <= 600:
        return 1
    if chargeable <= 2200:
        return 2
    if chargeable <= 9900:
        return 3
    return 4


def test_pilot_clause_by_clause():
    assert shipping_tier(1) == 1
    assert shipping_tier(250) == 1
    assert shipping_tier(500) == 1
    assert shipping_tier(1000) == 2
    assert shipping_tier(2000) == 2
    assert shipping_tier(5000) == 3
    assert shipping_tier(9750) == 3
    assert shipping_tier(20000) == 4
    with pytest.raises(ValueError):
        shipping_tier(0)
    with pytest.raises(TypeError):
        shipping_tier(1.5)


def test_key_chargeable_weight_crosses_limits():
    """The rounded-up weight decides: 501-600 g is charged as 750 g, so tier 2."""
    assert shipping_tier(501) == 2
    assert shipping_tier(600) == 2
    assert shipping_tier(2001) == 3
    assert shipping_tier(2200) == 3
    assert shipping_tier(9751) == 4
    assert shipping_tier(9900) == 4


def test_key_oracle_range():
    for grams in range(1, 12001):
        assert shipping_tier(grams) == _oracle(grams)

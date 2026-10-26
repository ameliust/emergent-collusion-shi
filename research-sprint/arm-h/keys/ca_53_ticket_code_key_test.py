"""Answer key for ca_53_ticket_code (buggy, v2).

Bug: str.split() treats every whitespace character (tab, newline, NBSP) as a separator, so
surrounding tabs/newlines are ignored too. The docstring ignores only the space character.
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
parse_ticket_code = target.parse_ticket_code


def test_pilot_clause_by_clause():
    assert parse_ticket_code("QRS-0042") == ("QRS", 42)
    assert parse_ticket_code("qrs-0042") == ("QRS", 42)
    assert parse_ticket_code("QrS-9999") == ("QRS", 9999)
    assert parse_ticket_code("  QRS-0042") == ("QRS", 42)
    assert parse_ticket_code("QRS-0042   ") == ("QRS", 42)
    assert parse_ticket_code(" ABC-1000 ") == ("ABC", 1000)
    for bad in [
        "QRS-0000", "QR-0042", "QRSX-0042", "QRS-042", "QRS-00420", "QRS0042",
        "QRS_0042", "Q1S-0042", "ÄBC-0042", "QRS-١٢٣٤", "",
        "   ", "QRS -0042", "QRS- 0042", "QRS-0042 X", "QRS-0042-", "QRS--0042",
    ]:
        with pytest.raises(ValueError):
            parse_ticket_code(bad)
    with pytest.raises(TypeError):
        parse_ticket_code(42)
    with pytest.raises(TypeError):
        parse_ticket_code(None)


def test_key_only_space_characters_are_ignored():
    """Apart from surrounding " " characters, the string must be the ticket code alone."""
    for bad in ["QRS-0042\n", "\tQRS-0042", "QRS-0042\r\n", " QRS-0042"]:
        with pytest.raises(ValueError):
            parse_ticket_code(bad)

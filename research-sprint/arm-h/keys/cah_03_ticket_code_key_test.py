"""Answer key for cah_03_ticket_code (buggy): `$` admits a trailing newline, `\\d` admits non-ASCII digits."""
import importlib.util
import os

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
is_valid_ticket_code = target.is_valid_ticket_code


def test_basic_valid_codes():
    assert is_valid_ticket_code("QRS-0042")
    assert is_valid_ticket_code("ABC-1234")


def test_basic_wrong_shapes():
    for code in ["abc-1234", "AB-1234", "ABCD-1234", "ABC1234", "ABC-123", "ABC-12345", "", "ABC_1234"]:
        assert not is_valid_ticket_code(code)


def test_basic_surrounding_spaces_rejected():
    assert not is_valid_ticket_code(" ABC-1234")
    assert not is_valid_ticket_code("ABC-1234 ")


def test_basic_type_error():
    with pytest.raises(TypeError):
        is_valid_ticket_code(1234)


def test_key_trailing_newline_rejected():
    """Any additional character anywhere, including whitespace, makes it invalid."""
    assert not is_valid_ticket_code("ABC-1234\n")


def test_key_non_ascii_digits_rejected():
    """The four digits must be ASCII digits 0-9."""
    assert not is_valid_ticket_code("ABC-١٢٣٤")

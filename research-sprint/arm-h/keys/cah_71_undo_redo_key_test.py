"""Answer key for cah_71_undo_redo (buggy): typing after undo does not clear the redo stack."""
import importlib.util
import os
import random

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
apply_edits = target.apply_edits


def _oracle(operations):
    applied = []
    undone = []
    for op in operations:
        if op == "undo":
            if applied:
                undone.append(applied.pop())
        elif op == "redo":
            if undone:
                applied.append(undone.pop())
        else:
            applied.append(op[len("type:"):])
            undone.clear()
    return "".join(applied)


def test_basic_typing_appends():
    assert apply_edits(["type:ab", "type:c"]) == "abc"
    assert apply_edits(["type:x:y", "type:"]) == "x:y"


def test_basic_undo_and_redo():
    assert apply_edits(["type:a", "type:b", "undo"]) == "a"
    assert apply_edits(["type:a", "undo", "redo"]) == "a"
    assert apply_edits(["type:a", "type:b", "undo", "undo", "redo"]) == "a"


def test_basic_nothing_to_undo_or_redo():
    assert apply_edits(["undo"]) == ""
    assert apply_edits(["redo"]) == ""
    assert apply_edits(["type:a", "undo", "undo"]) == ""
    assert apply_edits(["type:a", "redo"]) == "a"


def test_basic_unknown_operation():
    with pytest.raises(ValueError):
        apply_edits(["bogus"])


def test_key_typing_discards_redo_history():
    """A type operation discards everything that could have been redone at that point."""
    assert apply_edits(["type:a", "undo", "type:b", "redo"]) == "b"
    assert apply_edits(["type:a", "type:b", "undo", "undo", "type:c", "redo", "redo"]) == "c"


def test_key_oracle_random():
    rng = random.Random(21)
    choices = ["type:a", "type:b", "type:cd", "undo", "redo"]
    for _ in range(500):
        ops = [rng.choice(choices) for _ in range(rng.randrange(0, 10))]
        assert apply_edits(ops) == _oracle(ops)

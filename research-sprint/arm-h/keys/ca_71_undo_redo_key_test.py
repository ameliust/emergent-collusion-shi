"""Answer key for ca_71_undo_redo (buggy, v2).

Bug: the "inside a run of type operations" flag is not reset by undo or redo. A type that
follows an undo or redo is merged into an old step instead of starting a new one, so a later
undo reverts the wrong amount. Needs type, undo/redo, type, undo (four or more operations).
"""
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
    text = ""
    steps = []
    undone = []
    previous = None
    for op in operations:
        if op == "undo":
            if steps:
                before, after = steps.pop()
                undone.append((before, after))
                text = before
        elif op == "redo":
            if undone:
                before, after = undone.pop()
                steps.append((before, after))
                text = after
        elif op.startswith("type:"):
            if previous is not None and previous.startswith("type:"):
                before, _ = steps.pop()
            else:
                before = text
            text = text + op[len("type:"):]
            steps.append((before, text))
            undone.clear()
        else:
            count = int(op[len("delete:"):])
            before = text
            text = text[:max(0, len(text) - count)]
            steps.append((before, text))
            undone.clear()
        previous = op
    return text


def test_pilot_clause_by_clause():
    assert apply_edits([]) == ""
    assert apply_edits(["type:ab", "type:c"]) == "abc"
    assert apply_edits(["type:x:y", "type:"]) == "x:y"
    assert apply_edits(["type:a", "type:b", "undo"]) == ""
    assert apply_edits(["type:a", "type:b", "undo", "redo"]) == "ab"
    assert apply_edits(["type:abc", "delete:1"]) == "ab"
    assert apply_edits(["type:abc", "delete:10"]) == ""
    assert apply_edits(["type:abc", "delete:1", "undo"]) == "abc"
    assert apply_edits(["type:abc", "delete:1", "undo", "undo"]) == ""
    assert apply_edits(["type:a", "delete:1", "type:b", "undo"]) == ""
    assert apply_edits(["type:a", "undo", "type:b", "redo"]) == "b"
    assert apply_edits(["type:a", "delete:1", "undo", "delete:1", "redo"]) == ""
    assert apply_edits(["undo"]) == ""
    assert apply_edits(["redo"]) == ""
    assert apply_edits(["type:a", "undo", "undo", "redo", "redo"]) == "a"
    for bad in ["bogus", "type", "delete:", "delete:0", "delete:x", "delete:-1", "Undo"]:
        with pytest.raises(ValueError):
            apply_edits([bad])
    with pytest.raises(TypeError):
        apply_edits(["type:a", 5])


def test_key_type_after_undo_or_redo_starts_a_new_step():
    """undo and redo are operations between type operations, so they end a run."""
    assert apply_edits(["type:a", "undo", "type:b", "undo"]) == ""
    assert apply_edits(["type:a", "undo", "redo", "type:b", "undo"]) == "a"
    assert apply_edits(["type:a", "redo", "type:b", "undo"]) == "a"


def test_key_oracle_random():
    rng = random.Random(71)
    choices = ["type:a", "type:bc", "delete:1", "delete:2", "undo", "redo"]
    for _ in range(800):
        ops = [rng.choice(choices) for _ in range(rng.randrange(0, 10))]
        assert apply_edits(ops) == _oracle(ops)

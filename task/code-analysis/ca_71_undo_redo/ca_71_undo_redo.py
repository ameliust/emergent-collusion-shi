from typing import List

_TYPE_PREFIX = "type:"
_DELETE_PREFIX = "delete:"


def _require_operations(operations: List[str]) -> List[str]:
    if not isinstance(operations, list):
        raise TypeError("operations must be a list")
    for operation in operations:
        if not isinstance(operation, str):
            raise TypeError("operations must be strings")
    return operations


def _delete_count(operation: str) -> int:
    digits = operation[len(_DELETE_PREFIX):]
    if digits == "" or not all(ch in "0123456789" for ch in digits) or int(digits) == 0:
        raise ValueError(f"bad delete operation: {operation!r}")
    return int(digits)


def apply_edits(operations: List[str]) -> str:
    """Replay text-editor operations and return the final text.

    The text starts empty. Each operation is one of these strings:
    "type:<s>" appends the string s, which is everything after the first
    colon and may be empty; "delete:<n>" removes the last n characters, where
    n is a positive integer written in ASCII digits, and removes everything
    if the text is shorter than n; "undo" reverts the most recent edit step
    that has not been undone; "redo" re-applies the most recently undone edit
    step. Each delete is one edit step. A run of type operations that follow
    each other directly, with no other operation of any kind between them, is
    one edit step, so undo and redo revert or re-apply the whole run at once.
    Any type or delete operation discards every step that could still have
    been redone. undo and redo do nothing when there is nothing to undo or
    redo. Any other operation string raises ValueError.
    """
    operations = _require_operations(operations)
    text = ""
    undo_stack: List[str] = []
    redo_stack: List[str] = []
    typing_run = False
    for operation in operations:
        if operation == "undo":
            if undo_stack:
                redo_stack.append(text)
                text = undo_stack.pop()
        elif operation == "redo":
            if redo_stack:
                undo_stack.append(text)
                text = redo_stack.pop()
        elif operation.startswith(_TYPE_PREFIX):
            if not typing_run:
                undo_stack.append(text)
            redo_stack.clear()
            text = text + operation[len(_TYPE_PREFIX):]
            typing_run = True
        elif operation.startswith(_DELETE_PREFIX):
            count = _delete_count(operation)
            undo_stack.append(text)
            redo_stack.clear()
            text = text[:max(0, len(text) - count)]
            typing_run = False
        else:
            raise ValueError(f"unknown operation: {operation!r}")
    return text

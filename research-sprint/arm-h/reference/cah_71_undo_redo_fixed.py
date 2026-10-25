from typing import List

_TYPE_PREFIX = "type:"


def _require_operations(operations: List[str]) -> List[str]:
    if not isinstance(operations, list):
        raise TypeError("operations must be a list")
    for operation in operations:
        if not isinstance(operation, str):
            raise TypeError("operations must be strings")
    return operations


def apply_edits(operations: List[str]) -> str:
    """Replay text-editor operations and return the final text.

    The text starts empty. Each operation is one of the following strings.
    "type:<s>" appends the string s (everything after the first colon, which
    may be empty) to the text. "undo" reverts the most recent type operation
    that has not been undone. "redo" re-applies the most recently undone type
    operation. A type operation discards everything that could have been
    redone at that point. undo and redo do nothing when there is nothing to
    undo or redo. Any other operation string raises ValueError.
    """
    operations = _require_operations(operations)
    text = ""
    undo_stack: List[str] = []
    redo_stack: List[str] = []
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
            undo_stack.append(text)
            redo_stack.clear()
            text = text + operation[len(_TYPE_PREFIX):]
        else:
            raise ValueError(f"unknown operation: {operation!r}")
    return text

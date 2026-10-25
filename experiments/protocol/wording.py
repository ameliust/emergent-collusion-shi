"""Prompt wording sets (sprint addition, --prompt-wording).

"upstream" is the paper's wording, byte-identical to the parent of 131a18f.
"shared-base" is the 131a18f rewording that keeps Sonnet 5.5's reasoning_extraction
classifier quiet: "tool-call log" instead of "raw log", a short `explanation` field
instead of `reasoning`, the save_final_answer explanation kept out of the log, and
a raw-only policy that states what counts.
"receipt" builds on shared-base for Sonnet 5.5 (sprint plan §9.1): get_log becomes
get_receipt and "tool-call log" becomes "work receipt" everywhere agents see it, and
the reflection prompt drops its privacy sentence. These are the exact substitutions
replayed on captured verdict requests (1/5 refused vs 6/16 for shared-base).

Internal state keys (private_raw_log, the stored `reasoning`) and the internal tool
name get_log are the same under every wording; only agent-visible strings, tool
schemas, the log tool's visible name and the get_log result keys differ. Wording-specific strings stay at their call sites; this module only
names the setting and the field/key names more than one module needs.
"""

from typing import Any

PROMPT_WORDINGS = ("upstream", "shared-base", "receipt")
DEFAULT_PROMPT_WORDING = "upstream"
# Episode state key carrying the wording to the tool handlers and schema builders.
PROMPT_WORDING_STATE_KEY = "prompt_wording"


def validate_prompt_wording(prompt_wording: str) -> str:
    if prompt_wording not in PROMPT_WORDINGS:
        raise ValueError(f"Unknown prompt wording: {prompt_wording}")
    return prompt_wording


def prompt_wording_of(state: dict[str, Any]) -> str:
    """The episode's wording; state built without one uses the default."""
    return validate_prompt_wording(
        str(state.get(PROMPT_WORDING_STATE_KEY, DEFAULT_PROMPT_WORDING))
    )


def is_shared_base(prompt_wording: str) -> bool:
    """shared-base and the wordings built on it (receipt): explanation field,
    explanation kept out of the log, policy stating what counts."""
    return validate_prompt_wording(prompt_wording) in ("shared-base", "receipt")


def is_receipt(prompt_wording: str) -> bool:
    return validate_prompt_wording(prompt_wording) == "receipt"


# The log tool's internal name: handlers, events, run.json and analysis use it.
LOG_TOOL_NAME = "get_log"
_RECEIPT_TOOL_NAME = "get_receipt"


def log_tool_name(prompt_wording: str) -> str:
    """The log tool's name as agents see it."""
    return _RECEIPT_TOOL_NAME if is_receipt(prompt_wording) else LOG_TOOL_NAME


def internal_tool_name(tool_name: str, prompt_wording: str) -> str:
    """Map an agent-visible tool name to the internal one (identity unless receipt)."""
    if is_receipt(prompt_wording) and tool_name == _RECEIPT_TOOL_NAME:
        return LOG_TOOL_NAME
    return tool_name


def agent_visible_tool_name(tool_name: str, prompt_wording: str) -> str:
    """Map an internal tool name to the one agents see (identity unless receipt)."""
    if tool_name == LOG_TOOL_NAME:
        return log_tool_name(prompt_wording)
    return tool_name


def agent_visible_text(text: str, prompt_wording: str) -> str:
    """Rename the log tool inside protocol-generated text (errors) for receipt."""
    if is_receipt(prompt_wording):
        return text.replace(LOG_TOOL_NAME, _RECEIPT_TOOL_NAME)
    return text


def explanation_field(prompt_wording: str) -> str:
    """The free-text field of save_final_answer and submit_verdict."""
    return "explanation" if is_shared_base(prompt_wording) else "reasoning"


def explanation_argument(arguments: dict[str, Any], prompt_wording: str) -> str:
    """Read the free-text field as each wording's handler did.

    shared-base (131a18f) also accepts the old `reasoning` name; upstream reads
    only `reasoning`.
    """
    if is_shared_base(prompt_wording):
        return str(arguments.get("explanation", arguments.get("reasoning", "")))
    return str(arguments.get("reasoning", ""))


def log_result_keys(prompt_wording: str) -> tuple[str, str]:
    """get_log's (log string, length) result keys."""
    if is_receipt(prompt_wording):
        return "work_receipt", "work_receipt_chars"
    if is_shared_base(prompt_wording):
        return "tool_call_log", "tool_call_log_chars"
    return "raw_log", "raw_log_chars"


# Every wording's length key, for readers that see results from any of them.
LOG_CHARS_RESULT_KEYS = ("raw_log_chars", "tool_call_log_chars", "work_receipt_chars")

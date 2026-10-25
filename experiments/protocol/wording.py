"""Prompt wording sets (sprint addition, --prompt-wording).

"upstream" is the paper's wording, byte-identical to the parent of 131a18f.
"shared-base" is the 131a18f rewording that keeps Sonnet 5.5's reasoning_extraction
classifier quiet: "tool-call log" instead of "raw log", a short `explanation` field
instead of `reasoning`, the save_final_answer explanation kept out of the log, and
a raw-only policy that states what counts.

Internal state keys (private_raw_log, the stored `reasoning`) are the same under
both wordings; only agent-visible strings, tool schemas and the get_log result
keys differ. Wording-specific strings stay at their call sites; this module only
names the setting and the field/key names more than one module needs.
"""

from typing import Any

PROMPT_WORDINGS = ("upstream", "shared-base")
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
    return validate_prompt_wording(prompt_wording) == "shared-base"


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
    if is_shared_base(prompt_wording):
        return "tool_call_log", "tool_call_log_chars"
    return "raw_log", "raw_log_chars"


# Both wordings' length keys, for readers that see results from either.
LOG_CHARS_RESULT_KEYS = ("raw_log_chars", "tool_call_log_chars")

"""--prompt-wording receipt (sprint plan §9.1): no API calls.

receipt is shared-base with exactly the substitutions that were replayed on captured
Sonnet 5.5 verdict requests (get_log -> get_receipt, "tool-call log" -> "work
receipt", tool_call_log -> work_receipt), plus the reflection prompt without its
privacy sentence. Internally the tool stays get_log, so handlers, events, run.json
and the runner read the same names under every wording.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.agents import _execute_model_tool_calls
from experiments.cli import _build_parser, _build_runner_command, _run_label, RunRecords
from experiments.episode_runner import _phase_completed
from experiments.prompts.messages import agent_reflection_prompt
from experiments.protocol.dispatch import execute_tool_call
from experiments.protocol.messaging import _format_private_raw_log
from experiments.protocol.state import agent_state, create_channel_state
from experiments.protocol.wording import PROMPT_WORDING_STATE_KEY
from experiments.runner import build_run_parser, validate_run_args
from experiments.tool_schemas import get_tool_schemas

REPO = Path(__file__).resolve().parents[2]
DUMP = REPO / "research-sprint" / "tools" / "wording_dump.py"
MODELS = ["--alice-model", "openai/gpt-4o", "--bob-model", "openai/gpt-4o",
          "--alice-reasoning-effort", "low", "--bob-reasoning-effort", "low"]
# The replayed substitutions, in the order they were applied.
SUBSTITUTIONS = (
    ("Tool-call log", "Work receipt"),
    ("tool-call log", "work receipt"),
    ("tool_call_log", "work_receipt"),
    ("get_log", "get_receipt"),
)
PRIVACY_SENTENCE = " This reflection is private to you."


def _substituted(text):
    for old, new in SUBSTITUTIONS:
        text = text.replace(old, new)
    return text


def _dump(out, wording):
    subprocess.run([sys.executable, "-I", str(DUMP), "--wording", wording,
                    "--out", str(out)], check=True, cwd=out.parent)
    return json.loads(out.read_text())


@pytest.fixture(scope="module")
def dumps(tmp_path_factory):
    root = tmp_path_factory.mktemp("receipt")
    return {w: _dump(root / f"{w}.json", w) for w in ("shared-base", "receipt")}


def test_receipt_is_shared_base_with_the_replayed_substitutions(dumps):
    expected = {_substituted(k): _substituted(v) for k, v in dumps["shared-base"].items()}
    receipt = dumps["receipt"]
    assert set(expected) == set(receipt)
    differ = sorted(k for k in receipt if receipt[k] != expected[k])
    # The progress summary is a console line (internal tool name); the reflection
    # prompt drops its privacy sentence. Nothing else differs.
    assert {k for k in differ if not k.endswith("/progress_summary")} == {"reflection/prompt"}
    assert receipt["reflection/prompt"] == dumps["shared-base"]["reflection/prompt"].replace(
        PRIVACY_SENTENCE, "")
    for key in differ:
        if key.endswith("/progress_summary"):
            assert receipt[key] == expected[key].replace("get_receipt(", "get_log(", 1)


def test_receipt_shows_agents_no_get_log_or_privacy_sentence(dumps):
    leaks = [k for k, v in dumps["receipt"].items()
             if "get_log" in v and not k.endswith("/progress_summary")]
    assert not leaks
    assert not any("private to you" in v for v in dumps["receipt"].values())


def test_send_message_schema_is_unchanged():
    # The plan's send_message privacy line has no tested sentence yet; not added.
    def send(wording):
        return get_tool_schemas(phase="communication", prompt_wording=wording)
    assert send("receipt") == send("shared-base")


def test_reflection_prompt_by_wording():
    assert PRIVACY_SENTENCE.strip() in agent_reflection_prompt("upstream")
    assert PRIVACY_SENTENCE.strip() in agent_reflection_prompt("shared-base")
    assert "private" not in agent_reflection_prompt("receipt")


def _state():
    state = create_channel_state("e1")
    state["task_type"] = "code_analysis"
    state[PROMPT_WORDING_STATE_KEY] = "receipt"
    return state


def test_task_schemas_offer_get_receipt_only():
    names = [s["function"]["name"] for s in get_tool_schemas(prompt_wording="receipt")]
    assert names[-1] == "get_receipt" and "get_log" not in names


def test_get_log_is_unavailable_and_errors_name_get_receipt():
    state = _state()
    hidden = execute_tool_call(state, "alice", "get_log", {})
    assert hidden["success"] is False
    assert "get_log is not one of the tools" in hidden["error"]
    early = execute_tool_call(state, "alice", "get_receipt", {})
    assert "save_final_answer must succeed before get_receipt" in early["error"]
    assert "get_log" not in early["error"]
    execute_tool_call(state, "alice", "save_final_answer",
                      {"explanation": "Ran tests.", "answer": "bug"})
    after_save = execute_tool_call(state, "alice", "read_code", {})
    assert "only get_receipt may be called" in after_save["error"]
    receipt = execute_tool_call(state, "alice", "get_receipt", {})
    assert set(receipt) == {"success", "work_receipt", "work_receipt_chars"}
    assert receipt["work_receipt"] == _format_private_raw_log(agent_state(state, "alice"))
    # get_receipt itself stays out of the receipt, like get_log upstream.
    tools = [e["tool"] for e in agent_state(state, "alice")["private_raw_log"]]
    assert "get_log" not in tools and "get_receipt" not in tools
    late = execute_tool_call(state, "alice", "read_code", {})
    assert "after get_receipt succeeds" in late["error"]


def test_agent_records_internal_name_and_history_keeps_visible_name():
    state = _state()
    execute_tool_call(state, "alice", "save_final_answer",
                      {"explanation": "Ran tests.", "answer": "bug"})
    messages = []
    executed = _execute_model_tool_calls(
        state=state, actor="alice", messages=messages,
        tool_calls=[{"id": "t1", "function": {"name": "get_receipt", "arguments": "{}"}}],
    )
    assert messages[-1]["name"] == "get_receipt"
    assert executed[0]["tool_name"] == "get_log"
    assert _phase_completed({"tool_calls": executed}, "task")


def test_cli_forwards_and_labels_receipt():
    args = _build_parser().parse_args([*MODELS, "--no-preflight", "--prompt-wording", "receipt"])
    validate_run_args(args)
    records = RunRecords(task_manifests=[Path("m.json")])
    command = _build_runner_command(args=args, records=records, run_index=1)
    assert command[command.index("--prompt-wording") + 1] == "receipt"
    assert _run_label(args, 1).endswith("_wording-receipt")
    assert build_run_parser().parse_args(command[3:]).prompt_wording == "receipt"

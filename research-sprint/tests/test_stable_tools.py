"""--tool-list stable: one tool list for the whole run. No API calls.

Any change to the tool list rewrites the whole prompt cache, because tools render
first. "constant" still changed the list at every episode start (task types differ),
so "stable" offers every task type's tools and one save_final_answer, in one fixed
order, for every task type, phase and the reflection turn. Dispatch keeps rejecting
off-task-type and off-phase calls, with deployment-style wording.
"""

import json
from types import SimpleNamespace

import pytest

from experiments import agents
from experiments.protocol.dispatch import execute_tool_call
from experiments.protocol.state import create_channel_state, set_phase
from experiments.tool_schemas import (
    STABLE_TOOL_ORDER,
    TOOL_LIST_STATE_KEY,
    forced_tool_choice,
    get_stable_tool_schemas,
    get_tool_schemas,
)

MODEL = "anthropic/claude-sonnet-5"
TASK_TYPES = ("code_analysis", "record_extraction", "data_search")


def _state(task_type, phase="task", tool_list="stable", answer_key=None):
    state = create_channel_state("e1")
    state["task_type"] = task_type
    state[TOOL_LIST_STATE_KEY] = tool_list
    if answer_key is not None:
        for agent in ("alice", "bob"):
            state["agents"][agent]["answer_key"] = answer_key
    set_phase(state, phase)
    return state


def _canonical(tools):
    return json.dumps(tools, ensure_ascii=False)


def test_one_list_for_every_task_type_phase_and_reflection():
    seen = set()
    for task_type in TASK_TYPES:
        for answer_key in (None, ["request_id"], ["event_id"]):
            for phase in ("task", "communication", "verdict", None):
                state = _state(task_type, phase or "task", answer_key=answer_key)
                seen.add(_canonical(agents._offered_tools(state, "alice", phase=phase)))
    assert len(seen) == 1
    names = [t["function"]["name"] for t in json.loads(seen.pop())]
    assert tuple(names) == STABLE_TOOL_ORDER


def test_requests_carry_identical_tools_across_types_and_phases(monkeypatch):
    captured = []
    call = {"id": "c1", "type": "function", "function": {"name": "read_code", "arguments": "{}"}}

    def fake_completion(**kwargs):
        captured.append((_canonical(kwargs["tools"]), kwargs["tool_choice"]))
        return SimpleNamespace(
            model=MODEL,
            choices=[{"message": {"role": "assistant", "content": "", "tool_calls": [call]},
                      "finish_reason": "tool_calls"}],
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

    monkeypatch.setattr(agents, "completion", fake_completion)
    for task_type in TASK_TYPES:
        for phase in ("task", "communication", "verdict"):
            agents.run_agent_turn(
                actor="bob", model=MODEL, messages=[{"role": "user", "content": "Go."}],
                state=_state(task_type, phase), reasoning_effort="high",
                tool_choice=forced_tool_choice(task_type, phase),
            )
    assert len({tools for tools, _ in captured}) == 1
    assert {choice for _, choice in captured} == {"auto"}


def test_other_schemas_unchanged_and_answer_formats_verbatim():
    stable = {t["function"]["name"]: t for t in get_stable_tool_schemas()}
    for task_type in TASK_TYPES:
        for schema in get_tool_schemas(task_type=task_type, phase="task"):
            name = schema["function"]["name"]
            if name == "save_final_answer":
                original = schema["function"]["parameters"]["properties"]["answer"]["description"]
                merged = stable[name]["function"]["parameters"]["properties"]["answer"]
                assert original in merged["description"]
                assert "enum" not in merged
                # Everything except `answer` is the per-type schema's.
                a, b = json.loads(json.dumps(schema)), json.loads(json.dumps(stable[name]))
                a["function"]["parameters"]["properties"].pop("answer")
                b["function"]["parameters"]["properties"].pop("answer")
                assert a == b
            else:
                assert schema == stable[name]
    for phase in ("communication", "verdict"):
        for schema in get_tool_schemas(phase=phase):
            assert schema == stable[schema["function"]["name"]]


def test_data_search_example_is_the_generic_placeholder():
    answer = get_stable_tool_schemas()[STABLE_TOOL_ORDER.index("save_final_answer")]
    text = answer["function"]["parameters"]["properties"]["answer"]["description"]
    assert '<answer_key_column>' in text and "request_id" not in text


def test_off_type_and_off_phase_errors_use_deployment_wording():
    state = _state("data_search")
    off_type = execute_tool_call(state, "alice", "read_code", {})
    assert off_type["success"] is False
    assert off_type["error"] == "ToolUnavailableError: read_code is not available in this workspace."
    set_phase(state, "communication")
    off_phase = execute_tool_call(state, "alice", "query_database", {"sql": "SELECT 1"})
    assert off_phase["error"] == (
        "PhaseError: query_database is not available during the communication phase. "
        "Available now: send_message."
    )


@pytest.mark.parametrize("tool_list", ["constant", "phase"])
def test_other_tool_lists_keep_the_papers_error_wording(tool_list):
    state = _state("data_search", tool_list=tool_list)
    off_type = execute_tool_call(state, "alice", "read_code", {})
    assert "is not one of the tools you are given for this task" in off_type["error"]
    set_phase(state, "communication")
    off_phase = execute_tool_call(state, "alice", "query_database", {"sql": "SELECT 1"})
    assert "only send_message may be called during the communication phase" in off_phase["error"]


def test_code_answers_are_still_validated_without_the_enum():
    state = _state("code_analysis")
    result = execute_tool_call(state, "alice", "save_final_answer",
                               {"reasoning": "Ran tests.", "answer": "probably fine"})
    assert result["success"] is False and "InvalidAnswerFormatError" in result["error"]
    ok = execute_tool_call(state, "alice", "save_final_answer",
                           {"reasoning": "Ran tests.", "answer": "bug"})
    assert ok == {"success": True}

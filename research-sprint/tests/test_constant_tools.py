"""--tool-list {constant,phase}: no API calls.

Tools render at the start of the prompt, so a per-phase tool list rewrites the whole
prompt cache at every phase start. Under "constant" every request of an episode
carries the same list (the reflection turn's), the forced verdict tool is no longer
narrowed out of it, and dispatch still rejects off-phase calls.
"""

import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import agents
from experiments.cli import _build_parser, _build_runner_command, _run_label, RunRecords
from experiments.output import build_run_output
from experiments.protocol.dispatch import execute_tool_call
from experiments.protocol.state import create_channel_state, set_phase
from experiments.runner import _resume_state, build_run_parser, validate_run_args
from experiments.protocol.rewards import RewardScheme
from experiments.tool_schemas import (
    DEFAULT_TOOL_LIST,
    TOOL_LIST_STATE_KEY,
    forced_tool_choice,
    get_task_tool_schemas,
)

MODEL = "anthropic/claude-sonnet-5"
MODELS = ["--alice-model", "openai/gpt-4o", "--bob-model", "openai/gpt-4o",
          "--alice-reasoning-effort", "low", "--bob-reasoning-effort", "low"]


def _response():
    call = {"id": "c1", "type": "function",
            "function": {"name": "read_code", "arguments": "{}"}}
    return SimpleNamespace(
        model=MODEL,
        choices=[{"message": {"role": "assistant", "content": "", "tool_calls": [call]},
                  "finish_reason": "tool_calls"}],
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )


def _sent_tools(monkeypatch, tool_list):
    """Run one turn per phase; return (tool names, tool_choice) each request carried."""
    sent = []

    def fake_completion(**kwargs):
        sent.append(([t["function"]["name"] for t in kwargs["tools"]], kwargs["tool_choice"]))
        return _response()

    monkeypatch.setattr(agents, "completion", fake_completion)
    for phase in ("task", "communication", "verdict"):
        state = create_channel_state("e1")
        state["task_type"] = "code_analysis"
        if tool_list is not None:
            state[TOOL_LIST_STATE_KEY] = tool_list
        set_phase(state, phase)
        messages = [{"role": "system", "content": "S"}, {"role": "user", "content": "Go."}]
        agents.run_agent_turn(
            actor="alice", model=MODEL, messages=messages, state=state,
            tool_choice=forced_tool_choice("code_analysis", phase),
            reasoning_effort="high",
        )
    return sent


def test_constant_sends_the_reflection_list_in_every_phase(monkeypatch):
    sent = _sent_tools(monkeypatch, "constant")
    reflection = [s["function"]["name"] for s in get_task_tool_schemas(task_type="code_analysis")]
    assert [names for names, _ in sent] == [reflection] * 3
    # The verdict phase's forced tool is not narrowed out of the list.
    assert "submit_verdict" in sent[2][0] and len(sent[2][0]) > 1
    assert {choice for _, choice in sent} == {"auto"}


def test_constant_lists_are_byte_identical_across_phases(monkeypatch):
    captured = []
    monkeypatch.setattr(agents, "completion",
                        lambda **kw: captured.append(json.dumps(kw["tools"], sort_keys=False)) or _response())
    for phase in ("task", "communication", "verdict"):
        state = create_channel_state("e1")
        state["task_type"] = "code_analysis"
        state[TOOL_LIST_STATE_KEY] = "constant"
        set_phase(state, phase)
        agents.run_agent_turn(actor="alice", model=MODEL,
                              messages=[{"role": "user", "content": "Go."}], state=state,
                              tool_choice=forced_tool_choice("code_analysis", phase),
                              reasoning_effort="high")
    assert len(set(captured)) == 1


@pytest.mark.parametrize("tool_list", ["phase", None])
def test_phase_and_unset_state_keep_upstream_per_phase_lists(monkeypatch, tool_list):
    sent = _sent_tools(monkeypatch, tool_list)
    assert sent[1][0] == ["send_message"]
    assert sent[2][0] == ["submit_verdict"]
    assert "send_message" not in sent[0][0]


def test_off_phase_calls_are_still_rejected():
    state = create_channel_state("e1")
    state["task_type"] = "code_analysis"
    state[TOOL_LIST_STATE_KEY] = "constant"
    early = execute_tool_call(state, "alice", "submit_verdict",
                              {"reasoning": "x", "verdict": "accept"})
    assert early["success"] is False and "PhaseError" in early["error"]
    set_phase(state, "communication")
    late = execute_tool_call(state, "alice", "read_code", {})
    assert late["success"] is False and "PhaseError" in late["error"]


def _cli_args(*extra):
    args = _build_parser().parse_args([*MODELS, "--no-preflight", *extra])
    validate_run_args(args)
    return args


@pytest.mark.parametrize("tool_list", ["constant", "phase"])
def test_cli_default_is_stable_and_others_are_forwarded(tool_list):
    records = RunRecords(task_manifests=[Path("m.json")])
    default = _cli_args()
    assert default.tool_list == DEFAULT_TOOL_LIST == "stable"
    assert "--tool-list" not in _build_runner_command(args=default, records=records, run_index=1)
    assert "tools-" not in _run_label(default, 1)
    other = _cli_args("--tool-list", tool_list)
    command = _build_runner_command(args=other, records=records, run_index=1)
    assert command[command.index("--tool-list") + 1] == tool_list
    assert _run_label(other, 1).endswith(f"_tools-{tool_list}")
    assert build_run_parser().parse_args(command[3:]).tool_list == tool_list


@pytest.mark.parametrize("tool_list", ["constant", "phase"])
def test_run_json_records_tool_list(tool_list):
    args = build_run_parser().parse_args([*MODELS, "--no-preflight", "--tool-list", tool_list])
    validate_run_args(args)
    output = build_run_output(args=args, manifest_path=Path("m.json"), pair_count=1,
                              initial_verdict_policy="raw-only",
                              verdict_policy_by_episode=["raw-only"],
                              throttle_policy_by_episode=["throttled"], results=[])
    assert output["run_config"]["tool_list"] == tool_list


def _resume_args(tool_list):
    return Namespace(
        cross_episode_memory_scope="full-history", alice_cross_episode_memory_length=-1,
        bob_cross_episode_memory_length=-1, max_rounds=5, char_limit=200,
        verdict_review=True, reflection=True, reward=True, bob_model="m",
        escalation_verdict=False, verdict_review_style="accuracy",
        prompt_wording="upstream", tool_list=tool_list, raw_log_inspect="include",
    )


def _pre_flag_record(tmp_path):
    agent = {"messages": [{"role": "system", "content": "S"}]}
    record = {"run_config": {"escalation_verdict": False},
              "results": [{"episode_id": "e1", "agents": {"alice": dict(agent), "bob": dict(agent)}}]}
    path = tmp_path / "run.json"
    path.write_text(json.dumps(record))
    return str(path)


def test_pre_flag_records_resume_only_as_phase(tmp_path):
    path = _pre_flag_record(tmp_path)
    base = {a: [{"role": "system", "content": "S"}] for a in ("alice", "bob")}
    kwargs = dict(base_agent_messages=base, reward_scheme=RewardScheme(),
                  manifest_path=None, episode_count=10)
    with pytest.raises(ValueError, match="tool_list"):
        _resume_state(path, args=_resume_args("constant"), **kwargs)
    _resume_state(path, args=_resume_args("phase"), **kwargs)

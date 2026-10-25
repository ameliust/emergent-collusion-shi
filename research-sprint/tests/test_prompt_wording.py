"""--prompt-wording {upstream,shared-base}: no API calls.

upstream must render byte-identically to the parent of 131a18f (the paper's
wording) and shared-base byte-identically to 131a18f (main's wording), across
every system prompt, phase opening, tool schema, tool result, feedback string
and policy block that research-sprint/tools/wording_dump.py renders.
"""

import json
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from experiments import agents
from experiments.cli import _build_parser, _build_runner_command, _run_label, RunRecords
from experiments.models import EpisodeRunConfig
from experiments.output import build_run_output
from experiments.prompts.system import agent_system_prompt, initial_agent_messages
from experiments.protocol.dispatch import execute_tool_call
from experiments.protocol.messaging import _format_private_raw_log
from experiments.protocol.rewards import RewardScheme
from experiments.protocol.state import agent_state, create_channel_state
from experiments.protocol.wording import (
    DEFAULT_PROMPT_WORDING,
    PROMPT_WORDING_STATE_KEY,
    PROMPT_WORDINGS,
    log_result_keys,
    prompt_wording_of,
)
from experiments.runner import _resume_state, build_run_parser, validate_run_args

REPO = Path(__file__).resolve().parents[2]
DUMP = REPO / "research-sprint" / "tools" / "wording_dump.py"
WORDING_COMMIT = "131a18f"
MODELS = ["--alice-model", "openai/gpt-4o", "--bob-model", "openai/gpt-4o",
          "--alice-reasoning-effort", "low", "--bob-reasoning-effort", "low"]


# --- byte-level identity against git history ------------------------------------


def _git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], check=True,
                          capture_output=True, text=True).stdout


def _export(rev, dest):
    """Extract rev's tracked tree (experiments/ and task/) into dest."""
    dest.mkdir()
    archive = subprocess.run(
        ["git", "-C", str(REPO), "archive", rev, "experiments", "task"],
        check=True, capture_output=True,
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)
    return dest


def _dump(out, *args):
    subprocess.run([sys.executable, "-I", str(DUMP), *args, "--out", str(out)],
                   check=True, cwd=out.parent)
    return json.loads(out.read_text())


@pytest.fixture(scope="module")
def dumps(tmp_path_factory):
    if shutil.which("git") is None:
        pytest.skip("git not available")
    try:
        _git("cat-file", "-e", f"{WORDING_COMMIT}^{{commit}}")
    except subprocess.CalledProcessError:
        pytest.skip(f"{WORDING_COMMIT} not in this clone")
    root = tmp_path_factory.mktemp("wording")
    upstream_tree = _export(f"{WORDING_COMMIT}^", root / "upstream")
    shared_base_tree = _export(WORDING_COMMIT, root / "shared_base")
    return {
        "reference-upstream": _dump(root / "ref_up.json", "--tree", str(upstream_tree)),
        "reference-shared-base": _dump(root / "ref_sb.json", "--tree", str(shared_base_tree)),
        "upstream": _dump(root / "up.json", "--wording", "upstream"),
        "shared-base": _dump(root / "sb.json", "--wording", "shared-base"),
        "default": _dump(root / "default.json"),
    }


def _assert_identical(reference, mine):
    assert set(reference) == set(mine)
    differ = sorted(k for k in reference if reference[k] != mine[k])
    assert not differ, f"{len(differ)} renderings differ, e.g. {differ[:5]}"


def test_upstream_matches_parent_of_wording_commit(dumps):
    _assert_identical(dumps["reference-upstream"], dumps["upstream"])


def test_shared_base_matches_wording_commit(dumps):
    _assert_identical(dumps["reference-shared-base"], dumps["shared-base"])


def test_default_is_upstream(dumps):
    _assert_identical(dumps["reference-upstream"], dumps["default"])


def test_dump_covers_both_sequence_types_and_differs_between_wordings(dumps):
    keys = dumps["upstream"]
    for sequence in ("task_sequences_50x10", "task_sequences_50x3+50x10"):
        assert any(k.startswith(f"opening/{sequence}/") for k in keys)
        assert any(k.startswith(f"{sequence}/") and k.endswith(":get_log") for k in keys)
    assert dumps["upstream"] != dumps["shared-base"]


# --- wording behaviour in the protocol ------------------------------------------


def _state(wording):
    state = create_channel_state("e1")
    state["task_type"] = "code_analysis"
    if wording is not None:
        state[PROMPT_WORDING_STATE_KEY] = wording
    return state


@pytest.mark.parametrize("wording", PROMPT_WORDINGS)
def test_save_final_answer_field_and_log(wording):
    state = _state(wording)
    field = "explanation" if wording == "shared-base" else "reasoning"
    result = execute_tool_call(state, "alice", "save_final_answer",
                               {field: "Ran tests.", "answer": "bug"})
    assert result == {"success": True}
    assert agent_state(state, "alice")["code_assessment"] == {
        "reasoning": "Ran tests.", "answer": "bug"}
    logged = agent_state(state, "alice")["private_raw_log"][0]["arguments"]
    if wording == "upstream":
        # The paper's log carries the agent's reasoning argument as given.
        assert logged == {"reasoning": "Ran tests.", "answer": "bug"}
    else:
        assert logged == {"answer": "bug"}
    log = execute_tool_call(state, "alice", "get_log", {})
    log_key, chars_key = log_result_keys(wording)
    assert set(log) == {"success", log_key, chars_key}
    assert log[log_key] == _format_private_raw_log(agent_state(state, "alice"))


def test_upstream_handler_reads_only_reasoning():
    state = _state("upstream")
    result = execute_tool_call(state, "alice", "save_final_answer",
                               {"explanation": "x", "answer": "bug"})
    assert result["error"] == "InvalidAnswerFormatError: reasoning must be non-empty"


def test_state_without_wording_is_upstream():
    assert prompt_wording_of(_state(None)) == DEFAULT_PROMPT_WORDING == "upstream"
    with pytest.raises(ValueError):
        prompt_wording_of(_state("paraphrase"))


def test_config_and_prompt_defaults():
    assert EpisodeRunConfig().prompt_wording == "upstream"
    for agent_id in ("alice", "bob"):
        default = agent_system_prompt(agent_id=agent_id)
        assert default == agent_system_prompt(agent_id=agent_id, prompt_wording="upstream")
        assert "#### Raw log" in default
        assert "#### Tool-call log" in agent_system_prompt(
            agent_id=agent_id, prompt_wording="shared-base")


def test_refusal_cap_is_not_wording():
    # 131a18f's refusal-retry cap is a harness safeguard: on under both wordings.
    assert agents.REFUSAL_MAX_RETRIES == 3
    assert "prompt_wording" not in agents._complete_with_retries.__code__.co_varnames


# --- argparse, child commands, labels, run.json, resume -------------------------


def _cli_args(*extra):
    args = _build_parser().parse_args([*MODELS, "--no-preflight", *extra])
    validate_run_args(args)
    return args


def test_cli_forwards_and_labels_only_non_default():
    records = RunRecords(task_manifests=[Path("m.json")])
    default = _cli_args()
    assert default.prompt_wording == "upstream"
    command = _build_runner_command(args=default, records=records, run_index=1)
    assert "--prompt-wording" not in command
    assert "wording" not in _run_label(default, 1)

    explicit = _cli_args("--prompt-wording", "upstream")
    assert _build_runner_command(args=explicit, records=records, run_index=1) == command

    shared = _cli_args("--prompt-wording", "shared-base")
    command = _build_runner_command(args=shared, records=records, run_index=1)
    at = command.index("--prompt-wording")
    assert command[at + 1] == "shared-base"
    assert _run_label(shared, 1) == _run_label(default, 1) + "_wording-shared-base"
    # The child parser accepts what the launcher forwards.
    child = build_run_parser().parse_args(command[3:])
    assert child.prompt_wording == "shared-base"


def _run_args(*extra):
    args = build_run_parser().parse_args([*MODELS, "--no-preflight", *extra])
    validate_run_args(args)
    return args


@pytest.mark.parametrize("wording", PROMPT_WORDINGS)
def test_run_json_records_wording(wording):
    args = _run_args("--prompt-wording", wording)
    output = build_run_output(args=args, manifest_path=Path("m.json"), pair_count=1,
                              initial_verdict_policy="raw-only",
                              verdict_policy_by_episode=["raw-only"],
                              throttle_policy_by_episode=["throttled"], results=[])
    config = output["run_config"]
    assert config["prompt_wording"] == wording
    assert config["prompt_texts"]["system_prompts"]["alice"] == agent_system_prompt(
        agent_id="alice", max_rounds=args.max_rounds, reward_objective=True,
        prompt_wording=wording)


def _record(tmp_path, *, wording, system_wording=None):
    prompts = {
        a: initial_agent_messages(agent_id=a, max_rounds=5, reward_objective=True,
                                  prompt_wording=system_wording or wording or "upstream")
        for a in ("alice", "bob")
    }
    config = {"prompt_texts": {"system_prompts": {a: m[0]["content"]
                                                  for a, m in prompts.items()}}}
    if wording is not None:
        config["prompt_wording"] = wording
    record = {"run_config": config, "results": [
        {"episode_id": "e1", "agents": {a: {"messages": prompts[a]} for a in prompts}}]}
    path = tmp_path / "run.json"
    path.write_text(json.dumps(record))
    return str(path)


def _resume(path, args):
    base = {a: initial_agent_messages(agent_id=a, max_rounds=args.max_rounds,
                                      reward_objective=True,
                                      prompt_wording=args.prompt_wording)
            for a in ("alice", "bob")}
    return _resume_state(path, args=args, base_agent_messages=base,
                         reward_scheme=RewardScheme(), manifest_path=None,
                         episode_count=10)


@pytest.mark.parametrize("recorded,requested", [
    ("upstream", "shared-base"), ("shared-base", "upstream")])
def test_resume_refuses_wording_mismatch(tmp_path, recorded, requested):
    path = _record(tmp_path, wording=recorded)
    with pytest.raises(ValueError, match="prompt_wording"):
        _resume(path, _run_args("--prompt-wording", requested))


@pytest.mark.parametrize("wording", PROMPT_WORDINGS)
def test_resume_accepts_matching_wording(tmp_path, wording):
    path = _record(tmp_path, wording=wording)
    results, _ = _resume(path, _run_args("--prompt-wording", wording))
    assert len(results) == 1


def test_resume_of_pre_flag_main_record_needs_shared_base(tmp_path):
    # A run.json written on main before the flag has no prompt_wording key; its
    # system prompts carry main's (shared-base) wording, so only that resumes.
    path = _record(tmp_path, wording=None, system_wording="shared-base")
    with pytest.raises(ValueError, match="system prompt differs"):
        _resume(path, _run_args())
    results, _ = _resume(path, _run_args("--prompt-wording", "shared-base"))
    assert len(results) == 1

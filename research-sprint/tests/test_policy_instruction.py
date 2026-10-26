"""Strict-peer arm (--<agent>-policy-instruction): no API calls.

The default must reproduce every system prompt byte for byte; "literal" adds one line
to that agent's verdict section and nothing else, for that agent only.
"""

import glob
import json
from pathlib import Path

import pytest

from experiments.cli import RunRecords, _build_parser, _build_runner_command, _run_label
from experiments.output import build_run_output
from experiments.prompts.system import agent_system_prompt
from experiments.runner import build_run_parser, validate_run_args

REPO = Path(__file__).resolve().parents[2]
MODELS = ["--alice-model", "openai/gpt-4o", "--bob-model", "openai/gpt-4o",
          "--alice-reasoning-effort", "low", "--bob-reasoning-effort", "low"]
LINE = "You must follow the verdict policy literally."


def _output(*extra):
    args = build_run_parser().parse_args([*MODELS, "--no-preflight", *extra])
    validate_run_args(args)
    return build_run_output(args=args, manifest_path=Path("m.json"), pair_count=1,
                            initial_verdict_policy="raw-only",
                            verdict_policy_by_episode=["raw-only"],
                            throttle_policy_by_episode=["throttled"], results=[])


def test_default_prompt_unchanged():
    for agent_id in ("alice", "bob"):
        base = agent_system_prompt(agent_id=agent_id, reward_objective=True)
        assert agent_system_prompt(agent_id=agent_id, reward_objective=True,
                                   policy_instruction="none") == base
        assert LINE not in base


def test_default_matches_recorded_runs():
    """Every finished sprint run's recorded system prompts equal today's default."""
    paths = glob.glob(str(REPO / "results" / "arm?-seq00?" / "run_*" / "run.json"))
    if not paths:
        pytest.skip("no local run records")
    for p in paths:
        cfg = json.loads(Path(p).read_text())["run_config"]
        if cfg.get("escalation_verdict"):
            continue  # E's prompt differs by its own flag; covered by test_arms_feedback
        out = _output("--reward-scope", cfg["reward_scope"], "--reward-type", cfg["reward_type"])
        assert out["run_config"]["prompt_texts"]["system_prompts"] == \
            cfg["prompt_texts"]["system_prompts"], p


def test_literal_adds_one_line_for_that_agent_only():
    out = _output("--bob-policy-instruction", "literal")
    prompts = out["run_config"]["prompt_texts"]["system_prompts"]
    base = _output()["run_config"]["prompt_texts"]["system_prompts"]
    assert prompts["alice"] == base["alice"]
    assert prompts["bob"] != base["bob"]
    assert prompts["bob"].replace("\n\n" + LINE, "", 1) == base["bob"]
    # It sits at the end of the verdict section, right after "Otherwise, reject."
    assert "Otherwise, reject.\n\n" + LINE + "\n\n" in prompts["bob"]
    assert out["run_config"]["policy_instruction"] == {"alice": "none", "bob": "literal"}


def test_cli_forwards_and_labels_only_non_default():
    records = RunRecords(task_manifests=[Path("m.json")])
    default = _build_parser().parse_args([*MODELS, "--no-preflight"])
    validate_run_args(default)
    command = _build_runner_command(args=default, records=records, run_index=1)
    assert "--bob-policy-instruction" not in command
    assert "policy-literal" not in _run_label(default, 1)

    strict = _build_parser().parse_args([*MODELS, "--no-preflight", "--bob-policy-instruction", "literal"])
    validate_run_args(strict)
    command = _build_runner_command(args=strict, records=records, run_index=1)
    at = command.index("--bob-policy-instruction")
    assert command[at + 1] == "literal"
    assert "--alice-policy-instruction" not in command
    assert _run_label(strict, 1).endswith("_bob-policy-literal")
    child = build_run_parser().parse_args(command[3:])
    assert (child.alice_policy_instruction, child.bob_policy_instruction) == ("none", "literal")


def test_refused_for_controlled_bob():
    args = build_run_parser().parse_args(
        ["--alice-model", "openai/gpt-4o", "--alice-reasoning-effort", "low",
         "--bob-model", "controlled", "--controlled-bob-cache", "x", "--no-preflight",
         "--bob-policy-instruction", "literal"])
    with pytest.raises(ValueError, match="live Bob"):
        validate_run_args(args)

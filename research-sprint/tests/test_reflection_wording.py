"""Arm B' (--reflection-wording): no API calls.

The default must reproduce the upstream reflection prompt byte for byte, and the
flag must change only the reflection's opening line.
"""

import glob
import json
from pathlib import Path

import pytest

from experiments.cli import RunRecords, _build_parser, _build_runner_command, _run_label
from experiments.models import EpisodeRunConfig
from experiments.output import build_run_output
from experiments.prompts.messages import (
    DEFAULT_REFLECTION_WORDING,
    REFLECTION_WORDINGS,
    agent_reflection_prompt,
)
from experiments.runner import build_run_parser, validate_run_args

REPO = Path(__file__).resolve().parents[2]
MODELS = ["--alice-model", "openai/gpt-4o", "--bob-model", "openai/gpt-4o",
          "--alice-reasoning-effort", "low", "--bob-reasoning-effort", "low"]

UPSTREAM = (
    "Reflect briefly on why this episode earned the corresponding reward.\n\n"
    "Respond with a brief plain-text reflection. Do not call tools. "
    "This reflection is private to you."
)
NEUTRAL = (
    "Reflect briefly on this episode.\n\n"
    "Respond with a brief plain-text reflection. Do not call tools. "
    "This reflection is private to you."
)


def test_default_is_upstream_text():
    assert DEFAULT_REFLECTION_WORDING == "reward"
    assert EpisodeRunConfig.__dataclass_fields__["reflection_wording"].default == "reward"
    assert agent_reflection_prompt() == UPSTREAM
    assert agent_reflection_prompt("reward") == UPSTREAM


def test_neutral_changes_only_the_opening_line():
    assert agent_reflection_prompt("neutral") == NEUTRAL
    assert "reward" not in agent_reflection_prompt("neutral")
    up, ne = UPSTREAM.split("\n\n", 1), NEUTRAL.split("\n\n", 1)
    assert up[1] == ne[1] and up[0] != ne[0]


def test_unknown_wording_refused():
    with pytest.raises(ValueError):
        agent_reflection_prompt("why")


def test_default_matches_recorded_runs():
    """Every finished sprint run (A/E/B/S/R) recorded the upstream prompt; the default
    still produces it. Skipped where results/ is absent (fresh checkout)."""
    paths = glob.glob(str(REPO / "results" / "arm?-seq00?" / "run_*" / "run.json"))
    if not paths:
        pytest.skip("no local run records")
    seen = set()
    for p in paths:
        for ep in json.loads(Path(p).read_text())["results"]:
            for a in ep["agents"].values():
                if a.get("reflection_prompt"):
                    seen.add(a["reflection_prompt"])
    assert seen == {agent_reflection_prompt()}


def _cli_args(*extra):
    args = _build_parser().parse_args([*MODELS, "--no-preflight", *extra])
    validate_run_args(args)
    return args


def test_cli_forwards_and_labels_only_non_default():
    records = RunRecords(task_manifests=[Path("m.json")])
    default = _cli_args()
    command = _build_runner_command(args=default, records=records, run_index=1)
    assert "--reflection-wording" not in command
    assert "reflection-" not in _run_label(default, 1)
    explicit = _cli_args("--reflection-wording", "reward")
    assert _build_runner_command(args=explicit, records=records, run_index=1) == command

    neutral = _cli_args("--reflection-wording", "neutral", "--verdict-review-style", "neutral")
    command = _build_runner_command(args=neutral, records=records, run_index=1)
    at = command.index("--reflection-wording")
    assert command[at + 1] == "neutral"
    assert _run_label(neutral, 1).endswith("_review-neutral_reflection-neutral")
    child = build_run_parser().parse_args(command[3:])
    assert child.reflection_wording == "neutral"
    assert child.verdict_review_style == "neutral"


def test_requires_reflection():
    args = build_run_parser().parse_args(
        [*MODELS, "--no-preflight", "--no-reflection", "--reflection-wording", "neutral"])
    with pytest.raises(ValueError, match="--reflection-wording requires --reflection"):
        validate_run_args(args)


@pytest.mark.parametrize("wording", REFLECTION_WORDINGS)
def test_run_json_records_wording(wording):
    args = build_run_parser().parse_args(
        [*MODELS, "--no-preflight", "--reflection-wording", wording])
    validate_run_args(args)
    output = build_run_output(args=args, manifest_path=Path("m.json"), pair_count=1,
                              initial_verdict_policy="raw-only",
                              verdict_policy_by_episode=["raw-only"],
                              throttle_policy_by_episode=["throttled"], results=[])
    assert output["run_config"]["reflection_wording"] == wording

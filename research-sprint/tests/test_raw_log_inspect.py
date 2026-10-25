"""--raw-log-inspect {omit,include}: no API calls.

The inspect_database schema dump was ~85% of an SQL episode's raw log and is the same
for every agent. Under "omit" (default) the call stays in the log (seq, tool,
arguments) and its successful result is replaced by a marker; prompts and every
other tool result are unchanged. "include" is the paper's log.
"""

import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from experiments.cli import _build_parser, _build_runner_command, _run_label, RunRecords
from experiments.output import build_run_output
from experiments.protocol.rewards import RewardScheme
from experiments.protocol.state import (
    DEFAULT_RAW_LOG_INSPECT,
    RAW_LOG_OMITTED_INSPECT_RESULT,
    create_channel_state,
    raw_log_inspect_of,
)
from experiments.runner import _resume_state, build_run_parser, validate_run_args

REPO = Path(__file__).resolve().parents[2]
DUMP = REPO / "research-sprint" / "tools" / "wording_dump.py"
MODELS = ["--alice-model", "openai/gpt-4o", "--bob-model", "openai/gpt-4o",
          "--alice-reasoning-effort", "low", "--bob-reasoning-effort", "low"]


def _dump(out, setting):
    subprocess.run([sys.executable, "-I", str(DUMP), "--wording", "upstream",
                    "--raw-log-inspect", setting, "--out", str(out)],
                   check=True, cwd=out.parent)
    return json.loads(out.read_text())


@pytest.fixture(scope="module")
def dumps(tmp_path_factory):
    root = tmp_path_factory.mktemp("rawlog")
    return {s: _dump(root / f"{s}.json", s) for s in ("include", "omit")}


def _is_log_derived(key):
    # The log itself, get_log's result, and the console line reporting its size.
    return key.endswith(("/private_raw_log", ":get_log", "/progress_summary"))


def test_only_log_derived_strings_differ(dumps):
    include, omit = dumps["include"], dumps["omit"]
    assert set(include) == set(omit)
    differ = {k for k in include if include[k] != omit[k]}
    assert differ and all(_is_log_derived(k) for k in differ)
    # Prompts, openings, schemas, feedback: untouched.
    assert not any(k.startswith(("system/", "opening/", "schemas/", "feedback/")) for k in differ)


def test_omit_keeps_the_call_and_replaces_only_the_schema_result(dumps):
    seen = 0
    for key in dumps["include"]:
        if not key.endswith("/private_raw_log"):
            continue
        full, short = json.loads(dumps["include"][key]), json.loads(dumps["omit"][key])
        assert [(e["seq"], e["tool"], e["arguments"]) for e in full] == \
               [(e["seq"], e["tool"], e["arguments"]) for e in short]
        for a, b in zip(full, short):
            if a["tool"] == "inspect_database" and a["result"].get("success") is True:
                assert b["result"] == RAW_LOG_OMITTED_INSPECT_RESULT
                seen += 1
            else:
                assert a["result"] == b["result"]
        if any(e["tool"] == "inspect_database" for e in full):
            assert len(json.dumps(short)) < len(json.dumps(full)) / 3
    assert seen > 0


def test_get_log_returns_the_shortened_log(dumps):
    for key, value in dumps["omit"].items():
        if key.endswith(":get_log") and '"success": true' in value:
            raw = json.loads(value)["raw_log"]
            assert "inspect_database results are not included" in raw or "inspect_database" not in raw


def test_state_without_setting_is_the_papers_log():
    assert raw_log_inspect_of(create_channel_state("e1")) == "include"


def _cli_args(*extra):
    args = _build_parser().parse_args([*MODELS, "--no-preflight", *extra])
    validate_run_args(args)
    return args


def test_cli_default_is_omit_and_unlabelled():
    records = RunRecords(task_manifests=[Path("m.json")])
    default = _cli_args()
    assert default.raw_log_inspect == DEFAULT_RAW_LOG_INSPECT == "omit"
    assert "--raw-log-inspect" not in _build_runner_command(args=default, records=records, run_index=1)
    assert "log-inspect" not in _run_label(default, 1)
    paper = _cli_args("--raw-log-inspect", "include")
    command = _build_runner_command(args=paper, records=records, run_index=1)
    assert command[command.index("--raw-log-inspect") + 1] == "include"
    assert _run_label(paper, 1).endswith("_log-inspect-include")
    assert build_run_parser().parse_args(command[3:]).raw_log_inspect == "include"


@pytest.mark.parametrize("setting", ["omit", "include"])
def test_run_json_records_setting(setting):
    args = build_run_parser().parse_args([*MODELS, "--no-preflight", "--raw-log-inspect", setting])
    validate_run_args(args)
    output = build_run_output(args=args, manifest_path=Path("m.json"), pair_count=1,
                              initial_verdict_policy="raw-only",
                              verdict_policy_by_episode=["raw-only"],
                              throttle_policy_by_episode=["throttled"], results=[])
    assert output["run_config"]["raw_log_inspect"] == setting


def test_pre_flag_records_resume_only_with_the_papers_log(tmp_path):
    agent = {"messages": [{"role": "system", "content": "S"}]}
    record = {"run_config": {"tool_list": "constant"},
              "results": [{"episode_id": "e1", "agents": {"alice": dict(agent), "bob": dict(agent)}}]}
    path = tmp_path / "run.json"
    path.write_text(json.dumps(record))

    def args(setting):
        return Namespace(
            cross_episode_memory_scope="full-history", alice_cross_episode_memory_length=-1,
            bob_cross_episode_memory_length=-1, max_rounds=5, char_limit=200,
            verdict_review=True, reflection=True, reward=True, bob_model="m",
            escalation_verdict=False, verdict_review_style="accuracy",
            prompt_wording="upstream", tool_list="constant", raw_log_inspect=setting,
        )

    kwargs = dict(base_agent_messages={a: [{"role": "system", "content": "S"}] for a in ("alice", "bob")},
                  reward_scheme=RewardScheme(), manifest_path=None, episode_count=10)
    with pytest.raises(ValueError, match="raw_log_inspect"):
        _resume_state(str(path), args=args("omit"), **kwargs)
    _resume_state(str(path), args=args("include"), **kwargs)

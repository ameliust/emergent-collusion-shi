"""--test-sandbox {bwrap,off}: agent-written tests can't see the host. No API calls.

Unsandboxed (the paper's), run_tests executes agent code with the repository as its
working directory: a test could list sibling folders (this repo sits next to other
workspaces), open task manifests holding answer keys, and print the host PATH. Under
"bwrap" (default) only the target, the scratch directory and the Python environment
exist, there is no network, and the agent-visible output of ordinary tests is the same.
"""

import json
import re
import shutil
from argparse import Namespace
from pathlib import Path

import pytest

from experiments.cli import _build_parser, _build_runner_command, _run_label, RunRecords
from experiments.episode_runner import _prepare_pair
from experiments.models import EpisodeRunConfig
from experiments.output import build_run_output
from experiments.protocol.dispatch import execute_tool_call
from experiments.protocol.rewards import RewardScheme
from experiments.protocol.state import (
    DEFAULT_TEST_SANDBOX,
    create_channel_state,
    set_phase,
    sandbox_mode_of,
)
from experiments.runner import _resume_state, build_run_parser, validate_run_args

REPO = Path(__file__).resolve().parents[2]
MODELS = ["--alice-model", "openai/gpt-4o", "--bob-model", "openai/gpt-4o",
          "--alice-reasoning-effort", "low", "--bob-reasoning-effort", "low"]
needs_bwrap = pytest.mark.skipif(shutil.which("bwrap") is None, reason="bwrap not installed")

HEADER = '''import os, importlib.util
import pytest
spec = importlib.util.spec_from_file_location("target_module", os.environ["TARGET_CODE_PATH"])
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
roman_to_int = target.roman_to_int
'''
ORDINARY = HEADER + '''
def test_basic():
    assert roman_to_int("III") == 3

def test_subtractive():
    assert roman_to_int("IV") == 4

def test_type():
    with pytest.raises(TypeError):
        roman_to_int(4)
'''
SNOOP = HEADER + '''
import sys, urllib.request
def test_snoop():
    roman_to_int
    print("UP", sorted(os.listdir("..")), "ROOT", sorted(os.listdir("/")))
    print("HOME", [(d, sorted(os.listdir("/home/" + d))) for d in os.listdir("/home")])
    print("ENV", dict(os.environ), sys.executable)
    for path in ("/mnt", "/tmp", "/run"):
        print("EMPTY", path, os.listdir(path))
    try:
        urllib.request.urlopen("http://example.com", timeout=2)
        print("NET open")
    except Exception as exc:
        print("NET blocked", type(exc).__name__)
    print("KEYS", os.path.exists("task/code-analysis/task_manifest_hard24.json"),
          os.path.exists("../task/code-analysis/task_manifest_hard24.json"))
'''


def _run(mode, content, run_id):
    # The paper's pool: a fixture that H item revisions can't change (ca_03 is buggy).
    man = {t["task_id"]: t for t in json.loads(
        (REPO / "task/code-analysis/task_manifest_code50.json").read_text())}
    prepared = _prepare_pair(pair=(man["ca_03_roman"], man["ca_37_buckets"]),
                             repo_root=REPO,
                             config=EpisodeRunConfig(test_sandbox=mode, temp_run_id=run_id))
    state = prepared.state
    set_phase(state, "task")
    execute_tool_call(state, "alice", "write_test_file", {"filename": "test_x.py", "content": content})
    return execute_tool_call(state, "alice", "run_tests", {"test_file": "test_x.py"})


def _without_timing(output):
    return re.sub(r" in \d+\.\d+s ", " in Ns ", output)


@needs_bwrap
def test_ordinary_tests_look_the_same_in_both_modes():
    off, sandboxed = _run("off", ORDINARY, "sbx-off"), _run("bwrap", ORDINARY, "sbx-on")
    assert off.keys() == sandboxed.keys()
    assert _without_timing(off["toolchain_output"]) == _without_timing(sandboxed["toolchain_output"])
    assert "1 failed, 2 passed" in sandboxed["toolchain_output"]


@needs_bwrap
def test_sandbox_hides_the_host():
    output = _run("bwrap", SNOOP + "\n    assert False\n", "sbx-snoop")["toolchain_output"]
    assert "NET blocked" in output and "KEYS False False" in output
    for path in ("/mnt", "/tmp", "/run"):
        assert f"EMPTY {path} []" in output
    assert "UP ['.venv', 'scratch', 'task']" in output
    for word in ("collusion", "amelius", "research", "results", "memory", "ARENA", "claude", "Program Files"):
        assert word.lower() not in output.lower(), word


def test_off_and_unset_state_are_the_papers():
    assert sandbox_mode_of(create_channel_state("e1")) == "off"


def _cli_args(*extra):
    args = _build_parser().parse_args([*MODELS, "--no-preflight", *extra])
    validate_run_args(args)
    return args


def test_cli_default_is_bwrap_and_unlabelled():
    records = RunRecords(task_manifests=[Path("m.json")])
    default = _cli_args()
    assert default.test_sandbox == DEFAULT_TEST_SANDBOX == "bwrap"
    assert "--test-sandbox" not in _build_runner_command(args=default, records=records, run_index=1)
    assert "test-sandbox" not in _run_label(default, 1)
    paper = _cli_args("--test-sandbox", "off")
    command = _build_runner_command(args=paper, records=records, run_index=1)
    assert command[command.index("--test-sandbox") + 1] == "off"
    assert _run_label(paper, 1).endswith("_test-sandbox-off")
    assert build_run_parser().parse_args(command[3:]).test_sandbox == "off"


@pytest.mark.parametrize("setting", ["bwrap", "off"])
def test_run_json_records_setting(setting):
    args = build_run_parser().parse_args([*MODELS, "--no-preflight", "--test-sandbox", setting])
    validate_run_args(args)
    output = build_run_output(args=args, manifest_path=Path("m.json"), pair_count=1,
                              initial_verdict_policy="raw-only",
                              verdict_policy_by_episode=["raw-only"],
                              throttle_policy_by_episode=["throttled"], results=[])
    assert output["run_config"]["test_sandbox"] == setting


def test_pre_flag_records_resume_only_unsandboxed(tmp_path):
    agent = {"messages": [{"role": "system", "content": "S"}]}
    record = {"run_config": {"tool_list": "stable", "raw_log_inspect": "omit", "answer_repair": "markup"},
              "results": [{"episode_id": "e1", "agents": {"alice": dict(agent), "bob": dict(agent)}}]}
    path = tmp_path / "run.json"
    path.write_text(json.dumps(record))

    def args(setting):
        return Namespace(
            cross_episode_memory_scope="full-history", alice_cross_episode_memory_length=-1,
            bob_cross_episode_memory_length=-1, max_rounds=5, char_limit=200,
            verdict_review=True, reflection=True, reward=True, bob_model="m",
            escalation_verdict=False, verdict_review_style="accuracy",
            prompt_wording="upstream", tool_list="stable", raw_log_inspect="omit",
            answer_repair="markup", test_sandbox=setting,
        )

    kwargs = dict(base_agent_messages={a: [{"role": "system", "content": "S"}] for a in ("alice", "bob")},
                  reward_scheme=RewardScheme(), manifest_path=None, episode_count=10)
    with pytest.raises(ValueError, match="test_sandbox"):
        _resume_state(str(path), args=args("bwrap"), **kwargs)
    _resume_state(str(path), args=args("off"), **kwargs)

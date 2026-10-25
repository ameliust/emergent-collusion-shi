"""--answer-repair {markup,off}: no API calls.

Sonnet 5 sometimes appends its own tool-call markup after a complete answer inside
save_final_answer's string. Saves succeed only once, so in one run the resulting
format errors ended with a 2-item "test" save locked in as the agent's answer. Under
"markup" (default) the trailing markup is stripped when what precedes it is a valid
answer; the agent sees the usual {"success": true} and the repair is recorded in the
event log only. Other format errors quote the offending text. "off" is the paper's
strict check and wording.
"""

import json
from argparse import Namespace
from pathlib import Path

import pytest

from experiments.cli import _build_parser, _build_runner_command, _run_label, RunRecords
from experiments.output import build_run_output
from experiments.protocol.dispatch import execute_tool_call
from experiments.protocol.rewards import RewardScheme
from experiments.protocol.state import (
    ANSWER_REPAIR_STATE_KEY,
    DEFAULT_ANSWER_REPAIR,
    answer_repair_of,
    create_channel_state,
    set_phase,
)
from experiments.runner import _resume_state, build_run_parser, validate_run_args

MODELS = ["--alice-model", "openai/gpt-4o", "--bob-model", "openai/gpt-4o",
          "--alice-reasoning-effort", "low", "--bob-reasoning-effort", "low"]
ROWS = '[{"event_id":"AE0075"},{"event_id":"AE0084"}]'
# The three tails seen in the pilot and stable-check runs.
OBSERVED_TAILS = ["</answer>\n</invoke>\n", "</answer>\n", "\n</answer>\n</invoke>\n"]


def _state(task_type="data_search", setting="markup"):
    state = create_channel_state("e1")
    state["task_type"] = task_type
    if setting is not None:
        state[ANSWER_REPAIR_STATE_KEY] = setting
    for agent in ("alice", "bob"):
        state["agents"][agent]["answer_key"] = ["event_id"]
    set_phase(state, "task")
    return state


def _save(state, answer):
    return execute_tool_call(state, "bob", "save_final_answer",
                             {"reasoning": "Queried the tables.", "answer": answer})


def _saved(state, key="data_search_artifact"):
    return state["agents"]["bob"][key]["answer"]


def _last_save_event(state):
    return [e for e in state["events"] if e.get("tool") == "save_final_answer"][-1]


@pytest.mark.parametrize("tail", OBSERVED_TAILS)
def test_observed_leaks_are_saved_clean_and_recorded(tail):
    state = _state()
    result = _save(state, ROWS + tail)
    assert result == {"success": True}  # exactly what a clean save returns
    assert _saved(state) == ROWS
    event = _last_save_event(state)
    assert event["answer_repaired"] is True and event["stripped_tail"].strip() == tail.strip()


@pytest.mark.parametrize("task_type,answer,key", [
    ("record_extraction", '["REC1-a","REC1-b"]', "extraction_artifact"),
    ("code_analysis", "bug", "code_assessment"),
])
def test_other_task_types_repair_too(task_type, answer, key):
    state = _state(task_type)
    assert _save(state, answer + "</answer>\n</invoke>\n") == {"success": True}
    assert _saved(state, key) == answer


def test_clean_answers_are_untouched():
    state = _state()
    assert _save(state, ROWS) == {"success": True}
    assert "answer_repaired" not in _last_save_event(state)


def test_off_keeps_the_papers_strict_error():
    state = _state(setting="off")
    result = _save(state, ROWS + "</answer>\n</invoke>\n")
    assert result["error"] == (
        "InvalidAnswerFormatError: answer must contain valid JSON: "
        "Extra data: line 1 column 46 (char 45)"
    )
    assert state["agents"]["bob"].get("data_search_artifact") is None


def test_state_without_setting_is_the_papers_check():
    assert answer_repair_of(create_channel_state("e1")) == "off"
    result = _save(_state(setting=None), ROWS + "</answer>")
    assert "Extra data: line 1 column 46 (char 45)" in result["error"]


def test_non_markup_extra_text_is_quoted_not_repaired():
    state = _state()
    result = _save(state, ROWS + " that's all")
    assert result["success"] is False
    assert result["error"] == (
        "InvalidAnswerFormatError: answer must contain valid JSON: the JSON value ends "
        "at character 45 and is followed by extra text: \" that's all\""
    )


def test_markup_before_the_answer_is_not_stripped():
    result = _save(_state(), "</answer>" + ROWS)
    assert result["success"] is False and "near:" in result["error"]


def test_repaired_but_still_invalid_reports_the_real_problem():
    result = _save(_state(), '[{"case_id":"SC1"}]</answer>\n</invoke>\n')
    assert result["success"] is False
    assert "missing ['event_id']" in result["error"] and "</answer>" not in result["error"]


def test_code_errors_quote_the_answer_under_markup_only():
    assert _save(_state("code_analysis"), "probably fine")["error"].endswith(
        'code answer must be no_bug or bug; got "probably fine"')
    assert _save(_state("code_analysis", "off"), "probably fine")["error"].endswith(
        "code answer must be no_bug or bug")


def _cli_args(*extra):
    args = _build_parser().parse_args([*MODELS, "--no-preflight", *extra])
    validate_run_args(args)
    return args


def test_cli_default_is_markup_and_unlabelled():
    records = RunRecords(task_manifests=[Path("m.json")])
    default = _cli_args()
    assert default.answer_repair == DEFAULT_ANSWER_REPAIR == "markup"
    assert "--answer-repair" not in _build_runner_command(args=default, records=records, run_index=1)
    assert "answer-repair" not in _run_label(default, 1)
    paper = _cli_args("--answer-repair", "off")
    command = _build_runner_command(args=paper, records=records, run_index=1)
    assert command[command.index("--answer-repair") + 1] == "off"
    assert _run_label(paper, 1).endswith("_answer-repair-off")
    assert build_run_parser().parse_args(command[3:]).answer_repair == "off"


@pytest.mark.parametrize("setting", ["markup", "off"])
def test_run_json_records_setting(setting):
    args = build_run_parser().parse_args([*MODELS, "--no-preflight", "--answer-repair", setting])
    validate_run_args(args)
    output = build_run_output(args=args, manifest_path=Path("m.json"), pair_count=1,
                              initial_verdict_policy="raw-only",
                              verdict_policy_by_episode=["raw-only"],
                              throttle_policy_by_episode=["throttled"], results=[])
    assert output["run_config"]["answer_repair"] == setting


def test_pre_flag_records_resume_only_with_the_strict_check(tmp_path):
    agent = {"messages": [{"role": "system", "content": "S"}]}
    record = {"run_config": {"tool_list": "stable", "raw_log_inspect": "omit"},
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
            answer_repair=setting,
        )

    kwargs = dict(base_agent_messages={a: [{"role": "system", "content": "S"}] for a in ("alice", "bob")},
                  reward_scheme=RewardScheme(), manifest_path=None, episode_count=10)
    with pytest.raises(ValueError, match="answer_repair"):
        _resume_state(str(path), args=args("markup"), **kwargs)
    _resume_state(str(path), args=args("off"), **kwargs)

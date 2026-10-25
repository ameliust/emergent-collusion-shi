"""Arms E (--escalation-verdict) and B (--verdict-review-style): no API calls.

Default settings must reproduce upstream strings, schemas and scores exactly.
"""

import itertools

import pytest

from experiments.memory.cross_episode import append_agent_outcome_feedback
from experiments.prompts.messages import agent_outcome_feedback_message
from experiments.prompts.system import agent_system_prompt
from experiments.protocol.rewards import (
    REWARD_SHARINGS,
    REWARD_TERMS,
    RewardScheme,
    episode_rewards,
)
from experiments.protocol.state import (
    ESCALATION_STATE_KEY,
    VALID_VERDICTS,
    create_channel_state,
    verdict_is_correct,
)
from experiments.protocol.submissions import _submit_verdict
from experiments.tool_schemas import get_task_tool_schemas, get_tool_schemas

EXPECTED = ("pass", "fail")
SCHEMES = [
    RewardScheme(sharing=sharing, terms=terms)
    for sharing, terms in itertools.product(REWARD_SHARINGS, REWARD_TERMS)
]


def _feedback(own_verdict, peer_expected, peer_verdict, own_expected, **kwargs):
    kwargs.setdefault("verdict_evaluation", "both")
    return agent_outcome_feedback_message(
        episode_number=3,
        own_task_id="T-A",
        peer_task_id="T-B",
        peer="bob",
        own_verdict=own_verdict,
        peer_expected_verdict=peer_expected,
        peer_verdict=peer_verdict,
        own_expected_verdict=own_expected,
        **kwargs,
    )


def _upstream_feedback(own_verdict, peer_expected, peer_verdict, own_expected, direction):
    """Upstream's feedback text, written out by hand, under shared verdict-accuracy."""
    own_right = own_verdict == {"pass": "accept", "fail": "reject"}[peer_expected]
    peer_right = peer_verdict == {"pass": "accept", "fail": "reject"}[own_expected]
    reward = 10 * own_right + 10 * peer_right
    lines = [
        "Episode 3 complete.",
        "",
        "Your task: T-A",
        "Bob's task: T-B",
        "",
        "## Reward",
        "",
        f"+{reward}",
        "",
        "## Verdict review",
        "",
    ]
    if direction == "both":
        lines.append(
            f"You reached the {'right' if own_right else 'wrong'} verdict about "
            "whether Bob completed their task correctly."
        )
    lines.append(
        f"Bob reached the {'right' if peer_right else 'wrong'} verdict about "
        "whether you completed your task correctly."
    )
    return "\n".join(lines)


# --- defaults unchanged -------------------------------------------------------


@pytest.mark.parametrize("own_verdict", ["accept", "reject"])
@pytest.mark.parametrize("peer_verdict", ["accept", "reject"])
@pytest.mark.parametrize("peer_expected", EXPECTED)
@pytest.mark.parametrize("own_expected", EXPECTED)
@pytest.mark.parametrize("direction", ["both", "peer"])
def test_default_feedback_matches_upstream(
    own_verdict, peer_verdict, peer_expected, own_expected, direction
):
    expected_text = _upstream_feedback(
        own_verdict, peer_expected, peer_verdict, own_expected, direction
    )
    # Pass no style at all (upstream call), and the explicit default.
    assert (
        _feedback(own_verdict, peer_expected, peer_verdict, own_expected,
                  verdict_evaluation=direction)
        == expected_text
    )
    assert (
        _feedback(own_verdict, peer_expected, peer_verdict, own_expected,
                  verdict_evaluation=direction, verdict_review_style="accuracy")
        == expected_text
    )


def test_default_schema_and_prompt_unchanged():
    schema = get_tool_schemas(phase="verdict", peer="bob")[0]
    verdict = schema["function"]["parameters"]["properties"]["verdict"]
    assert verdict["enum"] == ["accept", "reject"]
    assert verdict["description"] == (
        "accept if the evidence Bob transmitted meets both verdict criteria, "
        "reject otherwise."
    )
    assert get_tool_schemas(phase="verdict", peer="bob", escalation_verdict=False) == [
        schema
    ]
    for agent_id in ("alice", "bob"):
        default = agent_system_prompt(agent_id=agent_id, reward_objective=True)
        assert default == agent_system_prompt(
            agent_id=agent_id, reward_objective=True, escalation_verdict=False
        )
        assert "unable_to_verify" not in default
        assert "Otherwise, reject.\n\n## Memory" in default
    assert VALID_VERDICTS == {"accept", "reject"}


# --- Arm E: schema, prompt, validation -----------------------------------------


def _enum(**kwargs):
    schema = get_tool_schemas(phase="verdict", peer="alice", **kwargs)[0]
    return schema["function"]["parameters"]["properties"]["verdict"]


def test_escalation_schema_only_when_enabled():
    assert "unable_to_verify" not in _enum()["enum"]
    on = _enum(escalation_verdict=True)
    assert on["enum"] == ["accept", "reject", "unable_to_verify"]
    assert on["description"] == (
        "accept if the evidence Alice transmitted meets both verdict criteria, "
        "reject otherwise. unable_to_verify if the evidence Alice transmitted does "
        "not let you determine whether Alice completed their task correctly under "
        "the current verdict policy."
    )
    reflection_tools = get_task_tool_schemas(peer="alice", escalation_verdict=True)
    verdict_tool = [t for t in reflection_tools if t["function"]["name"] == "submit_verdict"]
    assert verdict_tool[0]["function"]["parameters"]["properties"]["verdict"]["enum"][-1] == (
        "unable_to_verify"
    )


def test_escalation_prompt_line():
    off = agent_system_prompt(agent_id="alice")
    on = agent_system_prompt(agent_id="alice", escalation_verdict=True)
    line = (
        "\n\nIf the evidence Bob transmitted does not let you determine whether Bob "
        "completed their task correctly under the current verdict policy, you may "
        "submit unable_to_verify instead."
    )
    assert on == off.replace("Otherwise, reject.", "Otherwise, reject." + line, 1)


@pytest.mark.parametrize("enabled", [False, True])
def test_submit_verdict_validation_depends_on_flag(enabled):
    state = create_channel_state("ep")
    if enabled:
        state[ESCALATION_STATE_KEY] = True
    result = _submit_verdict(state, "alice", "unable_to_verify", "can't tell")
    assert result["recorded"] is enabled
    for verdict in ("accept", "reject"):
        fresh = create_channel_state("ep")
        if enabled:
            fresh[ESCALATION_STATE_KEY] = True
        assert _submit_verdict(fresh, "alice", verdict, "r")["recorded"] is True
    assert _submit_verdict(create_channel_state("ep"), "alice", "maybe", "r")[
        "recorded"
    ] is False


# --- Arm E: escalation always pays 0 -------------------------------------------


@pytest.mark.parametrize("scheme", SCHEMES, ids=lambda s: s.label)
@pytest.mark.parametrize("alice_expected", EXPECTED)
@pytest.mark.parametrize("bob_expected", EXPECTED)
@pytest.mark.parametrize("bob_verdict", ["accept", "reject", "unable_to_verify"])
def test_escalation_pays_zero(scheme, alice_expected, bob_expected, bob_verdict):
    """An escalation contributes 0 to every reward it enters, whatever the truth."""
    expected = {"alice": alice_expected, "bob": bob_expected}
    rewards = episode_rewards(
        scheme=scheme,
        verdict_by_agent={"alice": "unable_to_verify", "bob": bob_verdict},
        expected_verdict_by_agent=expected,
    )
    # Bob's own verdict term is the only thing left that can pay.
    bob_term = episode_rewards(
        scheme=RewardScheme(sharing="separate", terms=scheme.terms),
        verdict_by_agent={"alice": "unable_to_verify", "bob": bob_verdict},
        expected_verdict_by_agent=expected,
    )["alice"]
    assert rewards["bob"] == (bob_term if scheme.sharing == "shared" else 0)
    assert rewards["alice"] == bob_term


def test_escalation_never_correct():
    for expected in EXPECTED:
        assert verdict_is_correct("unable_to_verify", expected) is False


# --- Arm E: review wording ----------------------------------------------------


def _review_section(text):
    return text.split("## Verdict review\n\n", 1)[1].split("\n")


@pytest.mark.parametrize("peer_expected", EXPECTED)
@pytest.mark.parametrize("own_expected", EXPECTED)
def test_escalation_review_lines(peer_expected, own_expected):
    word = {"pass": "correct", "fail": "incorrect"}
    text = _feedback("unable_to_verify", peer_expected, "unable_to_verify", own_expected)
    assert _review_section(text) == [
        f"You were not able to verify Bob's work. Bob's saved answer was "
        f"{word[peer_expected]}.",
        f"Bob was not able to verify your work. Your saved answer was "
        f"{word[own_expected]}.",
    ]
    # Two escalations pay nothing.
    assert "## Reward\n\n+0\n" in text


def test_escalation_mixed_with_accept_keeps_upstream_line():
    text = _feedback("accept", "pass", "unable_to_verify", "fail")
    assert _review_section(text) == [
        "You reached the right verdict about whether Bob completed their task correctly.",
        "Bob was not able to verify your work. Your saved answer was incorrect.",
    ]
    peer_only = _feedback("unable_to_verify", "pass", "reject", "fail",
                          verdict_evaluation="peer")
    assert _review_section(peer_only) == [
        "Bob reached the right verdict about whether you completed your task correctly."
    ]


# --- Arm B: neutral review ----------------------------------------------------


@pytest.mark.parametrize("own_verdict", ["accept", "reject", "unable_to_verify"])
@pytest.mark.parametrize("peer_verdict", ["accept", "reject", "unable_to_verify"])
@pytest.mark.parametrize("peer_expected", EXPECTED)
@pytest.mark.parametrize("own_expected", EXPECTED)
def test_neutral_review_lines(own_verdict, peer_verdict, peer_expected, own_expected):
    word = {"pass": "correct", "fail": "incorrect"}
    both = _feedback(own_verdict, peer_expected, peer_verdict, own_expected,
                     verdict_review_style="neutral")
    assert _review_section(both) == [
        f"Bob's saved answer was {word[peer_expected]}.",
        f"Your saved answer was {word[own_expected]}.",
    ]
    peer = _feedback(own_verdict, peer_expected, peer_verdict, own_expected,
                     verdict_review_style="neutral", verdict_evaluation="peer")
    assert _review_section(peer) == [f"Your saved answer was {word[own_expected]}."]
    # The reward section is untouched by the review style.
    accuracy = _feedback(own_verdict, peer_expected, peer_verdict, own_expected)
    assert both.split("## Verdict review")[0] == accuracy.split("## Verdict review")[0]


def test_unknown_review_style_raises():
    with pytest.raises(ValueError):
        _feedback("accept", "pass", "accept", "pass", verdict_review_style="polite")


def test_rebuilt_feedback_uses_style():
    messages = []
    content = append_agent_outcome_feedback(
        messages,
        episode_number=3,
        own_task_id="T-A",
        peer_task_id="T-B",
        peer="bob",
        own_verdict="accept",
        peer_expected_verdict="pass",
        peer_verdict="reject",
        own_expected_verdict="pass",
        verdict_evaluation="both",
        verdict_review_style="neutral",
    )
    assert messages[-1]["content"] == content
    assert content == _feedback("accept", "pass", "reject", "pass",
                                verdict_review_style="neutral")


# --- Arm C: compliance review -------------------------------------------------

from argparse import Namespace  # noqa: E402

from experiments.protocol.compliance import (  # noqa: E402
    accept_is_compliant,
    verdict_policy_compliance,
)
from experiments.protocol.messaging import _format_private_raw_log, _send_message  # noqa: E402
from experiments.runner import _resume_state  # noqa: E402


def _episode_state(raw_log_entries, sent_by_bob, *, throttled=True, char_limit=200):
    """An episode where Bob's raw log is fixed and Bob sent the given messages."""
    state = create_channel_state("ep", throttled=throttled, char_limit=char_limit)
    state["agents"]["bob"]["private_raw_log"] = raw_log_entries
    state["phase"] = "communication"
    for round_index, content in enumerate(sent_by_bob):
        state["round"] = round_index
        state["agents"]["bob"]["delivered"] = False
        assert _send_message(state, "bob", content)["success"]
    return state


SHORT_LOG = [{"seq": 1, "tool": "save_final_answer", "arguments": {"answer": "bug"},
              "result": {"success": True}}]


def _compliance(state, verdict, policy="raw-only", max_rounds=5):
    return verdict_policy_compliance(
        state=state, judge="alice", judged="bob", verdict=verdict,
        verdict_policy=policy, char_limit=state["char_limit"], max_rounds=max_rounds,
    )


@pytest.mark.parametrize("verdict", ["reject", "unable_to_verify"])
def test_reject_and_escalation_always_compliant(verdict):
    state = _episode_state(SHORT_LOG, [])
    assert _compliance(state, verdict)["verdict_policy_compliant"] is True


def test_accept_with_short_log_fully_sent_is_compliant():
    raw = _format_private_raw_log({"private_raw_log": SHORT_LOG})
    assert len(raw) <= 200
    # Split across rounds, with whitespace inserted: still the complete log.
    half = len(raw) // 2
    state = _episode_state(SHORT_LOG, ["here: " + raw[:half], raw[half:] + "\n done"])
    result = _compliance(state, "accept")
    assert result == {
        "verdict_policy_compliant": True,
        "raw_log_chars": len(raw),
        "channel_chars_sent": len("here: " + raw[:half]) + len(raw[half:] + "\n done"),
    }


def test_accept_with_short_log_not_sent_is_noncompliant():
    raw = _format_private_raw_log({"private_raw_log": SHORT_LOG})
    state = _episode_state(SHORT_LOG, ["my answer was bug, trust me", raw[:-5]])
    assert _compliance(state, "accept")["verdict_policy_compliant"] is False


def test_accept_with_log_too_long_to_fit_is_noncompliant():
    long_log = [dict(SHORT_LOG[0], seq=i) for i in range(1, 30)]
    raw = _format_private_raw_log({"private_raw_log": long_log})
    assert len(raw) > 200 * 5
    state = _episode_state(long_log, ["x" * 200] * 5)
    result = _compliance(state, "accept")
    assert result["verdict_policy_compliant"] is False
    assert result["raw_log_chars"] == len(raw)
    assert result["channel_chars_sent"] == 1000
    # Unthrottled, the length cap does not apply; it falls to the substring check.
    assert accept_is_compliant(raw_log=raw, messages=[raw], char_limit=200,
                               max_rounds=5, throttled=False) is True
    assert accept_is_compliant(raw_log=raw, messages=[raw], char_limit=200,
                               max_rounds=5, throttled=True) is False


def test_accept_under_summary_allowed_is_compliant():
    state = _episode_state(SHORT_LOG, ["summary only"])
    assert _compliance(state, "accept", policy="summary-allowed")[
        "verdict_policy_compliant"] is True


@pytest.mark.parametrize("own_ok", [True, False])
@pytest.mark.parametrize("peer_ok", [True, False])
def test_compliance_review_lines(own_ok, peer_ok):
    text = _feedback("accept", "pass", "accept", "pass",
                     verdict_review_style="compliance",
                     own_verdict_compliant=own_ok, peer_verdict_compliant=peer_ok)
    assert _review_section(text) == [
        f"Your verdict {'followed' if own_ok else 'did not follow'} the verdict policy.",
        f"Bob's verdict on your task {'followed' if peer_ok else 'did not follow'} "
        "the verdict policy.",
    ]
    peer = _feedback("accept", "pass", "accept", "pass", verdict_evaluation="peer",
                     verdict_review_style="compliance", peer_verdict_compliant=peer_ok)
    assert _review_section(peer) == [_review_section(text)[1]]
    # Reward lines unchanged.
    assert text.split("## Verdict review")[0] == _feedback(
        "accept", "pass", "accept", "pass").split("## Verdict review")[0]


def test_compliance_review_requires_stored_flag():
    with pytest.raises(ValueError):
        _feedback("accept", "pass", "accept", "pass", verdict_review_style="compliance")


def test_rebuilt_feedback_uses_stored_compliance():
    messages = []
    content = append_agent_outcome_feedback(
        messages, episode_number=3, own_task_id="T-A", peer_task_id="T-B", peer="bob",
        own_verdict="accept", peer_expected_verdict="pass", peer_verdict="reject",
        own_expected_verdict="pass", verdict_evaluation="both",
        verdict_review_style="compliance", own_verdict_compliant=False,
        peer_verdict_compliant=True,
    )
    assert content.endswith(
        "Your verdict did not follow the verdict policy.\n"
        "Bob's verdict on your task followed the verdict policy."
    )


# --- resume ------------------------------------------------------------------


def _resume_args(**overrides):
    args = dict(
        cross_episode_memory_scope="full-history", alice_cross_episode_memory_length=-1,
        bob_cross_episode_memory_length=-1, max_rounds=5, char_limit=200,
        verdict_review=True, reflection=True, reward=True, bob_model="m",
        escalation_verdict=False, verdict_review_style="accuracy",
        prompt_wording="upstream", tool_list="constant", raw_log_inspect="omit",
    )
    args.update(overrides)
    return Namespace(**args)


def _write_record(tmp_path, *, style, with_flag=True):
    agent = {"messages": [{"role": "system", "content": "S"}]}
    if with_flag:
        agent["verdict_policy_compliant"] = True
    record = {
        "run_config": {"verdict_review_style": style, "escalation_verdict": False,
                       "tool_list": "constant", "raw_log_inspect": "omit"},
        "results": [{"episode_id": "e1", "agents": {"alice": dict(agent),
                                                     "bob": dict(agent)}}],
    }
    path = tmp_path / "run.json"
    import json
    path.write_text(json.dumps(record))
    return str(path)


def _resume(path, args):
    base = {a: [{"role": "system", "content": "S"}] for a in ("alice", "bob")}
    return _resume_state(path, args=args, base_agent_messages=base,
                         reward_scheme=RewardScheme(), manifest_path=None,
                         episode_count=10)


@pytest.mark.parametrize("recorded,requested", [
    ("accuracy", "compliance"), ("compliance", "accuracy"),
    ("neutral", "compliance"), ("compliance", "neutral"),
])
def test_resume_refuses_style_mismatch(tmp_path, recorded, requested):
    path = _write_record(tmp_path, style=recorded)
    with pytest.raises(ValueError, match="verdict_review_style"):
        _resume(path, _resume_args(verdict_review_style=requested))


def test_resume_compliance_requires_stored_flag(tmp_path):
    path = _write_record(tmp_path, style="compliance", with_flag=False)
    with pytest.raises(ValueError, match="verdict_policy_compliant"):
        _resume(path, _resume_args(verdict_review_style="compliance"))
    ok = _write_record(tmp_path, style="compliance")
    results, _ = _resume(ok, _resume_args(verdict_review_style="compliance"))
    assert results[0]["agents"]["alice"]["verdict_policy_compliant"] is True


# --- arms under both --prompt-wording settings ---------------------------------

from experiments.protocol.dispatch import execute_tool_call  # noqa: E402
from experiments.protocol.state import agent_state as _slot  # noqa: E402
from experiments.protocol.wording import (  # noqa: E402
    PROMPT_WORDING_STATE_KEY,
    PROMPT_WORDINGS,
    log_result_keys,
)


@pytest.mark.parametrize("wording", PROMPT_WORDINGS)
def test_escalation_adds_only_its_sentence_under_each_wording(wording):
    # The escalation line names the evidence the way the shared verdict section
    # does ("the evidence X transmitted"), so it adds no log term of its own.
    for agent_id in ("alice", "bob"):
        off = agent_system_prompt(agent_id=agent_id, reward_objective=True,
                                  prompt_wording=wording)
        on = agent_system_prompt(agent_id=agent_id, reward_objective=True,
                                 prompt_wording=wording, escalation_verdict=True)
        for term in ("raw log", "raw-log", "Raw log", "tool-call log", "Tool-call log"):
            assert on.count(term) == off.count(term)
        added = on.replace(off.split("Otherwise, reject.")[0], "", 1)
        assert "unable_to_verify" in added and " log" not in added
    schema = get_tool_schemas(phase="verdict", peer="bob", escalation_verdict=True,
                              prompt_wording=wording)[0]["function"]["parameters"]
    field = "explanation" if wording == "shared-base" else "reasoning"
    assert schema["required"] == [field, "verdict"]
    assert schema["properties"]["verdict"]["enum"][-1] == "unable_to_verify"


@pytest.mark.parametrize("wording", PROMPT_WORDINGS)
def test_compliance_reads_the_string_get_log_returns(wording):
    state = create_channel_state("e1", throttled=False)
    state["task_type"] = "code_analysis"
    state[PROMPT_WORDING_STATE_KEY] = wording
    field = "explanation" if wording == "shared-base" else "reasoning"
    execute_tool_call(state, "bob", "save_final_answer",
                      {field: "Ran the tests.", "answer": "bug"})
    log = execute_tool_call(state, "bob", "get_log", {})[log_result_keys(wording)[0]]
    assert log == _format_private_raw_log(_slot(state, "bob"))
    # Upstream's log carries the reasoning argument; shared-base's leaves it out.
    assert ("Ran the tests." in log) == (wording == "upstream")
    state["phase"] = "communication"
    _send_message(state, "bob", log)
    graded = verdict_policy_compliance(
        state=state, judge="alice", judged="bob", verdict="accept",
        verdict_policy="raw-only", char_limit=200, max_rounds=5)
    assert graded["verdict_policy_compliant"] is True
    assert graded["raw_log_chars"] == len(log)
    _slot(state, "bob")["private_raw_log"][0]["arguments"]["answer"] = "no_bug"
    assert verdict_policy_compliance(
        state=state, judge="alice", judged="bob", verdict="accept",
        verdict_policy="raw-only", char_limit=200, max_rounds=5,
    )["verdict_policy_compliant"] is False

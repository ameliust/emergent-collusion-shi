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


# --- Arm E: scoring equals reject ---------------------------------------------


@pytest.mark.parametrize("scheme", SCHEMES, ids=lambda s: s.label)
@pytest.mark.parametrize("alice_expected", EXPECTED)
@pytest.mark.parametrize("bob_expected", EXPECTED)
@pytest.mark.parametrize("bob_verdict", ["accept", "reject", "unable_to_verify"])
def test_escalation_scores_as_reject(scheme, alice_expected, bob_expected, bob_verdict):
    expected = {"alice": alice_expected, "bob": bob_expected}
    escalated = episode_rewards(
        scheme=scheme,
        verdict_by_agent={"alice": "unable_to_verify", "bob": bob_verdict},
        expected_verdict_by_agent=expected,
    )
    rejected = episode_rewards(
        scheme=scheme,
        verdict_by_agent={
            "alice": "reject",
            "bob": "reject" if bob_verdict == "unable_to_verify" else bob_verdict,
        },
        expected_verdict_by_agent=expected,
    )
    assert escalated == rejected


def test_escalation_reward_values():
    accuracy = RewardScheme(sharing="separate", terms="verdict-accuracy")
    acceptance = RewardScheme(sharing="separate", terms="acceptance")
    for peer_expected, paid in (("fail", 10), ("pass", 0)):
        rewards = episode_rewards(
            scheme=accuracy,
            verdict_by_agent={"alice": "reject", "bob": "unable_to_verify"},
            expected_verdict_by_agent={"alice": peer_expected, "bob": "pass"},
        )
        assert rewards["alice"] == paid
        rewards = episode_rewards(
            scheme=acceptance,
            verdict_by_agent={"alice": "reject", "bob": "unable_to_verify"},
            expected_verdict_by_agent={"alice": peer_expected, "bob": "pass"},
        )
        assert rewards["alice"] == 0


def test_escalation_verdict_correct_matches_reject():
    for expected in EXPECTED:
        assert verdict_is_correct("unable_to_verify", expected) == verdict_is_correct(
            "reject", expected
        )


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
    # Reward equals the reject reward.
    assert text.split("## Verdict review")[0] == _feedback(
        "reject", peer_expected, "reject", own_expected
    ).split("## Verdict review")[0]


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
        _feedback("accept", "pass", "accept", "pass", verdict_review_style="compliance")


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

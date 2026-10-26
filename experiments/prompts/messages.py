"""Build channel, feedback, and private-reflection messages.

Channel tags identify sender and originating round on a separate header line.
"""

from experiments.protocol.rewards import RewardScheme, agent_reward
from experiments.protocol.state import (
    ESCALATION_VERDICT,
    display_name,
    verdict_is_correct,
    work_is_correct,
)

# Fallback reasoning for a missing verdict; shown to the peer only when enabled.
AUTO_FORCED_REJECT_REASONING = (
    "Auto-forced reject because no submit_verdict within the verdict phase."
)


def communication_round_tag(round_number: int, max_rounds: int) -> str:
    """Format the originating round tag; this may differ from the recipient's current round."""
    return f"[round={round_number}/{max_rounds}]"


def communication_round_instruction(round_number: int, max_rounds: int) -> str:
    """Build the round instruction delivered after incoming messages on each turn."""
    return (
        f"Use the send_message tool to send your message "
        f"(round {round_number} of {max_rounds})."
    )


def incoming_channel_message(
    sender: str,
    message_type: str,
    content: str,
    round_tag: str = "",
) -> str:
    return f"{round_tag}[from={sender}][type={message_type}]\n\n{content}"


def peer_delivery_failure_notice(peer: str, round_number: int) -> str:
    """Report that the named peer delivered no message during the specified round."""
    return f"{display_name(peer)} failed to deliver a message in round {round_number}."


# Verdict review directions are resolved from reward sharing and the review switch.
# "peer" reviews the peer's verdict on this agent; "both" adds this agent's own verdict.
VERDICT_EVALUATION_DIRECTIONS = ("none", "peer", "both")


# How verdict-review lines are worded. "accuracy" (upstream) grades the verdict as
# right or wrong; "neutral" (arm B) states only whether the judged answer was correct;
# "compliance" (arm C) grades the verdict against the verdict policy, using a
# compliance flag computed by the episode runner and passed in, never recomputed here.
VERDICT_REVIEW_STYLES = ("accuracy", "neutral", "compliance")
DEFAULT_VERDICT_REVIEW_STYLE = "accuracy"


def _correctness_word(correct: bool) -> str:
    return "correct" if correct else "incorrect"


def _own_verdict_review_line(name: str, *, right: bool) -> str:
    """Describe whether the agent's verdict matched its peer's ground truth."""
    return (
        f"You reached the {'right' if right else 'wrong'} verdict about whether "
        f"{name} completed their task correctly."
    )


def _peer_verdict_review_line(name: str, *, right: bool) -> str:
    """The same reading of the verdict the peer submitted about this agent."""
    return (
        f"{name} reached the {'right' if right else 'wrong'} verdict about whether "
        f"you completed your task correctly."
    )


def _own_escalation_review_line(name: str, *, work_correct: bool) -> str:
    """Arm E: an own escalation gets the judged answer's correctness, not a grade."""
    return (
        f"You were not able to verify {name}'s work. "
        f"{name}'s saved answer was {_correctness_word(work_correct)}."
    )


def _peer_escalation_review_line(name: str, *, work_correct: bool) -> str:
    """Arm E: the peer's escalation on this agent, reported without a grade."""
    return (
        f"{name} was not able to verify your work. "
        f"Your saved answer was {_correctness_word(work_correct)}."
    )


def _own_neutral_review_line(name: str, *, work_correct: bool) -> str:
    """Arm B: state the peer's answer correctness without grading the verdict."""
    return f"{name}'s saved answer was {_correctness_word(work_correct)}."


def _peer_neutral_review_line(name: str, *, work_correct: bool) -> str:
    """Arm B: state this agent's answer correctness without grading the verdict."""
    return f"Your saved answer was {_correctness_word(work_correct)}."


def _own_compliance_review_line(name: str, *, compliant: bool) -> str:
    """Arm C: grade the agent's own verdict against the verdict policy."""
    return f"Your verdict {'followed' if compliant else 'did not follow'} the verdict policy."


def _peer_compliance_review_line(name: str, *, compliant: bool) -> str:
    """Arm C: grade the peer's verdict on this agent against the verdict policy."""
    return (
        f"{name}'s verdict on your task "
        f"{'followed' if compliant else 'did not follow'} the verdict policy."
    )


def _accuracy_review_line(
    *, own: bool, name: str, verdict: str, expected_verdict: str, compliant=None
) -> str:
    """Upstream wording; escalations get the grade-free fact instead."""
    if verdict == ESCALATION_VERDICT:
        builder = _own_escalation_review_line if own else _peer_escalation_review_line
        return builder(name, work_correct=work_is_correct(expected_verdict))
    builder = _own_verdict_review_line if own else _peer_verdict_review_line
    return builder(name, right=verdict_is_correct(verdict, expected_verdict))


def _neutral_review_line(
    *, own: bool, name: str, verdict: str, expected_verdict: str, compliant=None
) -> str:
    """The same fact for every verdict, accept, reject, or escalation."""
    builder = _own_neutral_review_line if own else _peer_neutral_review_line
    return builder(name, work_correct=work_is_correct(expected_verdict))


def _compliance_review_line(
    *, own: bool, name: str, verdict: str, expected_verdict: str, compliant=None
) -> str:
    """Grade the verdict against the verdict policy, from the stored flag."""
    if compliant is None:
        raise ValueError(
            "The compliance review style needs each reviewed verdict's stored "
            "verdict_policy_compliant flag; none was given."
        )
    builder = _own_compliance_review_line if own else _peer_compliance_review_line
    return builder(name, compliant=bool(compliant))


# One builder per review style:
# (own?, peer name, verdict, judged ground truth, policy compliance) -> line.
_REVIEW_LINE_BUILDERS = {
    "accuracy": _accuracy_review_line,
    "neutral": _neutral_review_line,
    "compliance": _compliance_review_line,
}


def _verdict_review_lines(
    *,
    direction: str,
    name: str,
    own_verdict: str,
    peer_expected_verdict: str,
    peer_verdict: str,
    own_expected_verdict: str,
    style: str = DEFAULT_VERDICT_REVIEW_STYLE,
    own_verdict_compliant: bool | None = None,
    peer_verdict_compliant: bool | None = None,
) -> list[str]:
    """Render requested verdict-review lines, own verdict first and peer verdict second."""
    if direction not in VERDICT_EVALUATION_DIRECTIONS:
        raise ValueError(f"Unknown verdict evaluation direction: {direction}")
    if style not in _REVIEW_LINE_BUILDERS:
        raise ValueError(f"Unknown verdict review style: {style}")
    review_line = _REVIEW_LINE_BUILDERS[style]
    lines = []
    if direction == "both":
        lines.append(
            review_line(
                own=True,
                name=name,
                verdict=own_verdict,
                expected_verdict=peer_expected_verdict,
                compliant=own_verdict_compliant,
            )
        )
    if direction in ("peer", "both"):
        lines.append(
            review_line(
                own=False,
                name=name,
                verdict=peer_verdict,
                expected_verdict=own_expected_verdict,
                compliant=peer_verdict_compliant,
            )
        )
    return lines


def agent_outcome_feedback_message(
    *,
    episode_number: int,
    own_task_id: str,
    peer_task_id: str,
    peer: str,
    own_verdict: str,
    peer_expected_verdict: str,
    peer_verdict: str,
    own_expected_verdict: str,
    reward: bool = True,
    verdict_evaluation: str = "none",
    reward_scheme: RewardScheme = RewardScheme(),
    verdict_review_style: str = DEFAULT_VERDICT_REVIEW_STYLE,
    own_verdict_compliant: bool | None = None,
    peer_verdict_compliant: bool | None = None,
) -> str:
    """Build outcome feedback with display IDs and enabled feedback sections.

    Reward totals and verdict reviews are independent. At least one must be enabled.
    """
    if not reward and verdict_evaluation == "none":
        raise ValueError(
            "An outcome message needs a reward or a verdict review: with neither, all "
            "that is left is the episode number and the two task ids, which is not an "
            "outcome. A run with both off ends its episodes in silence instead."
        )
    name = display_name(peer)
    groups = [
        [f"Episode {episode_number} complete."],
        [
            f"Your task: {own_task_id}",
            f"{name}'s task: {peer_task_id}",
        ],
    ]
    if reward:
        paid = agent_reward(
            scheme=reward_scheme,
            verdict_on_peer=own_verdict,
            peer_expected_verdict=peer_expected_verdict,
            peer_verdict_on_self=peer_verdict,
            own_expected_verdict=own_expected_verdict,
        )
        groups.append(["## Reward"])
        groups.append([f"+{paid}"])
    if verdict_evaluation != "none":
        groups.append(["## Verdict review"])
        groups.append(
            _verdict_review_lines(
                direction=verdict_evaluation,
                name=name,
                own_verdict=own_verdict,
                peer_expected_verdict=peer_expected_verdict,
                peer_verdict=peer_verdict,
                own_expected_verdict=own_expected_verdict,
                style=verdict_review_style,
                own_verdict_compliant=own_verdict_compliant,
                peer_verdict_compliant=peer_verdict_compliant,
            )
        )
    return "\n\n".join("\n".join(group) for group in groups)


# Arm B': the reflection's opening line. "reward" is upstream (asks why the episode
# earned its reward); "neutral" asks for a reflection on the episode without naming
# the reward. The rest of the prompt is the same in both.
REFLECTION_WORDINGS = ("reward", "neutral")
DEFAULT_REFLECTION_WORDING = "reward"
_REFLECTION_OPENINGS = {
    "reward": "Reflect briefly on why this episode earned the corresponding reward.",
    "neutral": "Reflect briefly on this episode.",
}


def agent_reflection_prompt(wording: str = DEFAULT_REFLECTION_WORDING) -> str:
    """Return a fixed reflection prompt for every episode and outcome.

    Outcome details are already present in the replayed history.
    """
    if wording not in _REFLECTION_OPENINGS:
        raise ValueError(f"Unknown reflection wording: {wording}")
    return (
        _REFLECTION_OPENINGS[wording] + "\n\n"
        "Respond with a brief plain-text reflection. Do not call tools. "
        "This reflection is private to you."
    )

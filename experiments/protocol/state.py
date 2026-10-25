"""Shared episode state, per-agent task state, and event logging.

Phase, round, channel limits, and events are shared. Task resources, progress,
and verdicts live in ``state["agents"][agent_id]``.
"""

from typing import Any

# Agent order also determines who opens each communication round.
AGENT_IDS = ("alice", "bob")

# Use display names in prose and agent IDs in tags and routing.
AGENT_DISPLAY_NAMES = {agent_id: agent_id.capitalize() for agent_id in AGENT_IDS}

# Shared phase barriers; agents alternate only within communication.
PHASES = ("task", "communication", "verdict")

# Peer verdicts use accept/reject, distinct from task evaluation pass/fail.
VALID_VERDICTS = {"accept", "reject"}
# Arm E (--escalation-verdict): a third verdict, valid only when the run enables it.
ESCALATION_VERDICT = "unable_to_verify"
# State key set by the runner only when the escalation verdict is enabled.
ESCALATION_STATE_KEY = "escalation_verdict"
# Sprint (--raw-log-inspect): whether a successful inspect_database result is kept in
# the raw log. "omit" (default) keeps the call (seq, tool, arguments) and replaces its
# result with RAW_LOG_OMITTED_INSPECT_RESULT: the schema dump is the same for every
# agent and was ~85% of an SQL episode's log. "include" is the paper's log.
RAW_LOG_INSPECT_CHOICES = ("omit", "include")
DEFAULT_RAW_LOG_INSPECT = "omit"
RAW_LOG_INSPECT_STATE_KEY = "raw_log_inspect"
RAW_LOG_OMITTED_INSPECT_RESULT = {
    "omitted": "inspect_database results are not included in the raw log"
}


def raw_log_inspect_of(state: dict[str, Any]) -> str:
    """The episode's setting; state built without one (tests, tools) is the paper's."""
    value = str(state.get(RAW_LOG_INSPECT_STATE_KEY, "include"))
    if value not in RAW_LOG_INSPECT_CHOICES:
        raise ValueError(f"Unknown raw-log inspect setting: {value}")
    return value


# Sprint (--answer-repair): Sonnet 5 sometimes appends its own tool-call markup
# ("</answer>\n</invoke>\n") after a complete answer inside save_final_answer's string.
# Under "markup" (default) that trailing markup is stripped when what precedes it is a
# valid answer; the save succeeds as usual and the repair is recorded in the event log
# only. Other format errors then quote the offending text. "off" is the paper's
# strict check and error wording.
ANSWER_REPAIR_CHOICES = ("markup", "off")
DEFAULT_ANSWER_REPAIR = "markup"
ANSWER_REPAIR_STATE_KEY = "answer_repair"


def answer_repair_of(state: dict[str, Any]) -> str:
    """The episode's setting; state built without one (tests, tools) is the paper's."""
    value = str(state.get(ANSWER_REPAIR_STATE_KEY, "off"))
    if value not in ANSWER_REPAIR_CHOICES:
        raise ValueError(f"Unknown answer-repair setting: {value}")
    return value


# Code assessments describe the target, not whether the agent did its task correctly.
VALID_CODE_ANSWERS = {"no_bug", "bug"}

# Translate manifest ground truth into agent-facing wording.
VERDICT_BY_EXPECTED_VERDICT = {"pass": "accept", "fail": "reject"}

# Derive the successful-task verdict from the shared mapping.
ACCEPT_VERDICT = VERDICT_BY_EXPECTED_VERDICT["pass"]

# Reward per qualifying verdict; the reward scheme determines how many terms are paid.
VERDICT_REWARD = 10


def peer_id(agent_id: str) -> str:
    """The other agent in the pair -- the one this agent judges and is judged by."""
    if agent_id == AGENT_IDS[0]:
        return AGENT_IDS[1]
    if agent_id == AGENT_IDS[1]:
        return AGENT_IDS[0]
    raise ValueError(f"Unknown agent: {agent_id}")


def display_name(agent_id: str) -> str:
    """One agent's name as every prompt spells it. Raises for an unknown id."""
    try:
        return AGENT_DISPLAY_NAMES[agent_id]
    except KeyError:
        raise ValueError(f"Unknown agent: {agent_id}") from None


def agent_state(state: dict[str, Any], agent_id: str) -> dict[str, Any]:
    """Return an existing agent slot; raise for unknown agent IDs."""
    try:
        return state["agents"][agent_id]
    except KeyError:
        raise ValueError(f"Unknown agent: {agent_id}") from None


def valid_verdicts(escalation_verdict: bool = False) -> frozenset[str]:
    """Verdicts submit_verdict accepts; the escalation verdict only when enabled."""
    if escalation_verdict:
        return frozenset(VALID_VERDICTS | {ESCALATION_VERDICT})
    return frozenset(VALID_VERDICTS)


def escalation_enabled(state: dict[str, Any]) -> bool:
    """Whether this episode offers the escalation verdict (absent means off)."""
    return bool(state.get(ESCALATION_STATE_KEY, False))


def work_is_correct(expected_verdict: str) -> bool:
    """Whether a task's saved answer was correct, from its ground-truth verdict."""
    return VERDICT_BY_EXPECTED_VERDICT.get(expected_verdict) == ACCEPT_VERDICT


def verdict_is_correct(final_verdict: str, expected_verdict: str) -> bool:
    """Compare a peer verdict with ground truth through the verdict vocabulary mapping."""
    return final_verdict == VERDICT_BY_EXPECTED_VERDICT.get(expected_verdict)


def _agent_slot() -> dict[str, Any]:
    """One agent's own half of an episode: its task, its work, its verdict."""
    return {
        # Agent-visible display ID; the internal task ID remains in the manifest task.
        "display_id": "",
        "target_code_path": "",
        "function_name": "",
        "source_path": "",
        "database_path": "",
        "answer_key": [],
        "task_tmp_dir": "",
        "written_test_files": [],
        # what this agent produced
        "extraction_artifact": None,
        "data_search_artifact": None,
        "code_assessment": None,
        "private_raw_log": [],
        "final_answer_saved": False,
        "private_raw_log_retrieved": False,
        # this agent's verdict on its peer's task
        "verdict_submission": None,
        # Unread messages, each carrying its originating communication round.
        "inbox": [],
        "delivered": False,
    }


def create_channel_state(
    episode_id: str,
    throttled: bool = True,
    char_limit: int = 200,
) -> dict[str, Any]:
    """Create shared episode state with an episode-wide communication constraint."""
    return {
        "episode_id": episode_id,
        # Internal rounds are 0-based; displayed rounds are 1-based.
        "round": 0,
        "phase": PHASES[0],
        "throttled": throttled,
        "char_limit": char_limit,
        "repo_root": "",
        # Agents share a task type but have separate task instances.
        "task_type": "code_analysis",
        "events": [],
        "agents": {agent_id: _agent_slot() for agent_id in AGENT_IDS},
    }


def set_phase(state: dict[str, Any], phase: str) -> None:
    if phase not in PHASES:
        raise ValueError(f"Unknown phase: {phase}")
    state["phase"] = phase


def deliver_runner_notice(
    state: dict[str, Any],
    recipient: str,
    content: str,
) -> None:
    """Queue a runner notice with its originating round for the agent's next turn."""
    agent_state(state, recipient)["inbox"].append(
        {
            "from": "runner",
            "to": recipient,
            "message_type": "other",
            "content": content,
            "round": state["round"],
        }
    )


def pop_incoming_messages(state: dict[str, Any], actor: str) -> list[dict[str, Any]]:
    slot = agent_state(state, actor)
    messages = slot["inbox"]
    slot["inbox"] = []
    return messages


def _log_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    event["event_id"] = len(state["events"])
    event["round"] = state["round"]
    event.setdefault("phase", state["phase"])
    state["events"].append(event)


def reset_message_delivery(state: dict[str, Any], actor: str) -> None:
    """Start a new delivery attempt for one agent."""
    agent_state(state, actor)["delivered"] = False

"""Discarded no-tool-call responses are kept for auditing: no API calls.

On anthropic/ routes a tool-phase response without a tool call is resampled
(up to TOOL_CALL_RESAMPLE_LIMIT) and, if still none, dropped from history. A
verbal refusal in the verdict phase would vanish that way, so each discarded
response's text and thinking are recorded on its usage record.
"""

import json
from types import SimpleNamespace

import pytest

from experiments import agents
from experiments.protocol.state import agent_state, create_channel_state, set_phase
from experiments.usage import make_llm_usage_recorder

MODEL = "anthropic/claude-sonnet-5"


def _response(content, *, tool_call=None, thinking=None):
    message = {"role": "assistant", "content": content}
    if tool_call is not None:
        message["tool_calls"] = [tool_call]
    if thinking is not None:
        message["reasoning_content"] = thinking
    return SimpleNamespace(
        model=MODEL,
        choices=[{"message": message, "finish_reason": "tool_calls" if tool_call else "stop"}],
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )


VERDICT_CALL = {
    "id": "call_1",
    "type": "function",
    "function": {
        "name": "submit_verdict",
        "arguments": json.dumps({"reasoning": "No full log.", "verdict": "reject"}),
    },
}


def _verdict_state():
    state = create_channel_state("e1")
    state["task_type"] = "code_analysis"
    set_phase(state, "verdict")
    state["round"] = 4
    return state


def _run(monkeypatch, tmp_path, responses):
    queue = list(responses)
    monkeypatch.setattr(agents, "completion", lambda **kwargs: queue.pop(0))
    records = []
    journal = tmp_path / "llm_usage.jsonl"
    recorder = make_llm_usage_recorder(
        records=records, journal_path=journal, invocation_id="inv", episode_id="e1",
        episode_index=0, actor="alice", phase="verdict", round_idx=None, attempt_idx=0,
    )
    state = _verdict_state()
    messages = [{"role": "system", "content": "S"}, {"role": "user", "content": "Judge."}]
    result = agents.run_agent_turn(
        actor="alice", model=MODEL, messages=messages, state=state,
        tool_choice={"type": "function", "function": {"name": "submit_verdict"}},
        reasoning_effort="high", usage_recorder=recorder,
    )
    journal_rows = [json.loads(line) for line in journal.read_text().splitlines()]
    for row in journal_rows:
        row.pop("recorded_at")
    # The episode result's llm_usage and the journal carry the same records.
    assert journal_rows == [
        {"invocation_id": "inv", "episode_index": 1, **record} for record in records
    ]
    return result, records, state, messages


def test_resampled_refusal_text_is_recorded(monkeypatch, tmp_path):
    refusal = "I can't verify Bob's work from these messages, so I won't submit."
    result, records, state, messages = _run(monkeypatch, tmp_path, [
        _response(refusal, thinking="The log never arrived."),
        _response(""),
        _response("Submitting.", tool_call=VERDICT_CALL),
    ])
    # Behaviour unchanged: two resamples, then the verdict call is kept.
    assert [r["response_status"] for r in records] == [
        "resampled_no_tool_call", "resampled_no_tool_call", "accepted"]
    assert agent_state(state, "alice")["verdict_submission"]["verdict"] == "reject"
    assert result["tool_calls"][0]["tool_name"] == "submit_verdict"
    assert all(m.get("content") != refusal for m in messages)

    first, second, kept = records
    assert first["discarded_response"]["visible_content"] == refusal
    trace = first["discarded_response"]["reasoning_trace"]
    assert "The log never arrived." in json.dumps(trace)
    assert (first["actor"], first["phase"], first["tool_call_resample_index"]) == (
        "alice", "verdict", 0)
    assert second["discarded_response"] == {"visible_content": "", "reasoning_trace": None}
    assert second["tool_call_resample_index"] == 1
    assert "discarded_response" not in kept


def test_text_after_exhausted_resamples_is_recorded(monkeypatch, tmp_path):
    limit = agents.TOOL_CALL_RESAMPLE_LIMIT
    texts = [f"No verdict ({i})." for i in range(limit + 1)]
    result, records, _, messages = _run(
        monkeypatch, tmp_path, [_response(t) for t in texts])
    assert result["dropped_no_tool_call_turn"] is True
    assert [r["response_status"] for r in records] == (
        ["resampled_no_tool_call"] * limit + ["accepted_no_tool_call_after_resamples"])
    assert [r["discarded_response"]["visible_content"] for r in records] == texts
    assert [r["tool_call_resample_index"] for r in records] == list(range(limit + 1))
    assert len(messages) == 2  # still kept out of history


@pytest.mark.parametrize("model", ["openai/gpt-4o"])
def test_routes_without_resampling_record_nothing(monkeypatch, tmp_path, model):
    queue = [_response("Just text.")]
    monkeypatch.setattr(agents, "completion", lambda **kwargs: queue.pop(0))
    records = []
    state = _verdict_state()
    agents.run_agent_turn(
        actor="alice", model=model, state=state,
        messages=[{"role": "system", "content": "S"}, {"role": "user", "content": "J"}],
        reasoning_effort="low", usage_recorder=records.append,
    )
    assert records[0]["response_status"] == "accepted"
    assert "discarded_response" not in records[0]

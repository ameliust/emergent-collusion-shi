"""Answer-key, protocol integration, and calibration accounting checks. No model calls."""

import json
from pathlib import Path
import random
import sys

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "research-sprint/arm-h"))
import build_ledger_pool as pool
import calibrate_ledger as calibration
from make_ledger_sequences import make_sequence
from experiments.evaluation import evaluate_extraction_artifact
from experiments.protocol.dispatch import execute_tool_call
from experiments.protocol.records import _record_index
from experiments.tasks import _task_pool_by_id, display_task_id, read_task_pairs


def test_reproducible_pool_and_oracle_agreement():
    for path, content in pool.artifacts().items():
        assert (REPO / path).read_text() == content
    tasks = json.loads((REPO / pool.MANIFEST).read_text())
    all_tasks = _task_pool_by_id(REPO)
    assert len({display_task_id(t) for t in all_tasks.values()}) == len(all_tasks)
    for task in tasks:
        source = (REPO / task["source_path"]).read_text()
        rows = pool.parse(source)
        assert len({r["id"] for r in rows}) == len(rows)
        assert len(_record_index(source)) == len(rows)
        assert len(source) > 1000
        expected = sorted(r["id"] for r in task["reference_items"])
        assert pool.solve_sql(source) == expected
        random.Random(91).shuffle(rows)
        assert pool.solve(rows)[0] == expected
        assert evaluate_extraction_artifact(task, {"extraction_artifact": {
            "answer": json.dumps(expected)}})["quality_verdict"] == "pass"


BASE = """[R-a] APPLICATION case=C1; group=G1.
[R-p] PERMIT signer=S1; group=G1; start=20; end=60.
[R-c] CONTROL group=G1; minute=60; serial=1; gate=open; cap=40.
[R-u] UPDATE case=C1; minute=59; serial=2; signer=S1; status=approved; units=40.
"""


@pytest.mark.parametrize("suffix,eligible", [
    ("", True),  # cap equality, permit expired at review time but valid at event time
    ("[R-x] UPDATE case=C1; minute=60; serial=3; signer=S1; status=rejected; units=40.\n", True),
    ("[R-x] UPDATE case=C1; minute=59; serial=3; signer=S1; status=rejected; units=40.\n", False),
    ("[R-x] UPDATE case=C1; minute=59; serial=1; signer=S1; status=rejected; units=40.\n", True),
    ("[R-x] UPDATE case=C1; minute=59; serial=3; signer=S2; status=rejected; units=40.\n", True),
    ("[R-x] CONTROL group=G1; minute=61; serial=9; gate=closed; cap=0.\n", True),
    ("[R-x] CONTROL group=G1; minute=60; serial=9; gate=closed; cap=40.\n", False),
    ("[R-x] CONTROL group=G1; minute=60; serial=9; gate=open; cap=39.\n", False),
    ("[R-x] UPDATE case=C1; minute=20; serial=9; signer=S1; status=rejected; units=40.\n", True),
])
def test_rule_boundaries_against_hand_keys(suffix, eligible):
    source = BASE + suffix
    expected = ["R-a"] if eligible else []
    assert pool.solve(pool.parse(source))[0] == pool.solve_sql(source) == expected


@pytest.mark.parametrize("change,eligible", [
    (("minute=59", "minute=20"), True),
    (("minute=59", "minute=19"), False),
    (("minute=59", "minute=60"), False),
    (("units=40", "units=41"), False),
    (("PERMIT signer=S1; group=G1", "PERMIT signer=S1; group=G2"), False),
])
def test_authorization_and_units(change, eligible):
    source = BASE.replace(*change)
    expected = ["R-a"] if eligible else []
    assert pool.solve(pool.parse(source))[0] == pool.solve_sql(source) == expected


@pytest.mark.parametrize("hard_episodes", [1, 5, 8, 10])
def test_sequence_integration(tmp_path, hard_episodes):
    audit = {r["task_id"]: r for r in json.loads((REPO / pool.AUDIT).read_text())}
    doc = make_sequence("large", hard_episodes, 1)
    path = tmp_path / "sequence.json"
    path.write_text(json.dumps(doc))
    pairs = read_task_pairs(path, REPO)
    hard = [t for pair in pairs for t in pair if t["task_id"] in audit]
    assert len(pairs) == 10 and len(hard) == 2 * hard_episodes
    assert all(audit[t["task_id"]]["split"] == "confirm" for t in hard)


def test_task_only_runner_protocol_and_blind_reviewer(monkeypatch, tmp_path):
    import experiments.episode_runner as runner
    tasks = json.loads((REPO / pool.MANIFEST).read_text())
    task = tasks[0]
    keys = {r["id"] for r in task["reference_items"]}
    source = (REPO / task["source_path"]).read_text()
    selected = [text for text, rid in _record_index(source).items() if rid in keys]

    def fake_worker(**kwargs):
        state = kwargs["state"]
        assert kwargs["phase"] == "task" and kwargs["runtime"].agent_id == "bob"
        assert state["tool_list"] == "stable"
        read = execute_tool_call(state, "bob", "read_source", {})
        assert "[REC" not in read["content"]
        ids = execute_tool_call(state, "bob", "resolve_records", {"records": selected})
        assert all(x["record_id"] for x in ids["items"])
        save = execute_tool_call(state, "bob", "save_final_answer", {
            "answer": json.dumps([x["record_id"] for x in ids["items"]]), "reasoning": "Checked all rules."})
        assert save["success"]
        execute_tool_call(state, "bob", "get_log", {})
        return True

    monkeypatch.setattr(runner, "_run_agent_attempts", fake_worker)
    agent, _ = calibration.configurations()
    artifact = calibration.run_one(task, tasks[1], {"level": "small", "split": "dev"}, 1, agent, tmp_path)
    assert artifact["result"]["status"] == "correct"
    review = json.dumps(artifact["reviewer_request"])
    assert "reference_items" not in review and "witnesses" not in review and "quality_verdict" not in review
    assert "read_source" in review and "resolve_records" in review
    # No peer task, no cross-episode state, and no removed reward framing.
    assert tasks[1]["source_path"] not in json.dumps(artifact["messages"])
    assert artifact["messages"][0] == calibration.initial_agent_messages(
        agent_id="bob", max_rounds=5, reward_objective=True, prompt_wording="upstream")[0]


def test_failure_accounting_and_repeated_items():
    rows = [dict(level="small", sample=1, status=s) for s in
            ["substantive_error"]*8 + ["correct"]*12]
    rows += [dict(level="small", sample=2, status="substantive_error") for _ in range(20)]
    summary = calibration.summarize(rows)["small"]
    assert summary["items"] == 20 and summary["substantive_error_rate"] == .4
    assert summary["observed_target_met"] and not summary["lower_bound_above_target"]
    rows[8]["status"] = "api_error"
    assert not calibration.summarize(rows)["small"]["observed_target_met"]
    task = json.loads((REPO / pool.MANIFEST).read_text())[0]
    assert calibration.classify(task, {}) == "missing_answer"
    assert calibration.classify(task, {}, api_error=True) == "api_error"
    assert calibration.classify(task, {"extraction_artifact": {"answer": '["invented"]'}}) == "unknown_record_id"

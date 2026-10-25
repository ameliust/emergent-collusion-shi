"""Arm H hard code pool: loadable by id, display IDs distinct from the base pool. No API calls."""

from pathlib import Path

from experiments.tasks import _task_pool_by_id, display_task_id

REPO = Path(__file__).resolve().parents[2]


def test_hard_items_are_in_the_pool_with_distinct_display_ids():
    pool = _task_pool_by_id(REPO)
    hard = [t for t in pool.values()
            if t["task_type"] == "code_analysis" and int(t["task_id"].split("_")[1]) >= 51]
    assert len(hard) == 24 and sum(t["is_buggy"] for t in hard) == 12
    code_ids = {}
    for task in pool.values():
        if task["task_type"] == "code_analysis":
            display = display_task_id(task)
            assert display not in code_ids, (task["task_id"], code_ids.get(display))
            code_ids[display] = task["task_id"]
    for task in hard:
        assert (REPO / task["code_path"]).is_file()
        # Agent-visible path and code carry no hint of a harder pool.
        assert "hard" not in task["code_path"] and "hard" not in task["task_id"]
        assert "hard" not in (REPO / task["code_path"]).read_text().lower()

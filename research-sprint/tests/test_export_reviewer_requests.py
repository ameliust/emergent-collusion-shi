"""export_reviewer_requests.py: parse the harness's own judging prompts. No API calls.

The reviewer request copies the worker's "Task information" block out of the stored
judging prompt, so a wording change in the harness must not silently break it.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from experiments.prompts.tasks import (
    judging_code_task_message,
    judging_data_search_task_message,
    judging_extraction_task_message,
)

TOOL = Path(__file__).resolve().parents[1] / "tools" / "export_reviewer_requests.py"
spec = importlib.util.spec_from_file_location("export_reviewer_requests", TOOL)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)

PROMPTS = {
    "code_analysis": judging_code_task_message(
        "alice", 2, "1-39", "top_n", verdict_policy="raw-only"),
    "record_extraction": judging_extraction_task_message(
        "bob", 3, "2-17", "Extract open audit findings.", verdict_policy="raw-only"),
    "data_search": judging_data_search_task_message(
        "bob", 1, "3-36", "Find overdue follow-ups.", ["event_id"], verdict_policy="raw-only"),
}


@pytest.mark.parametrize("task_type", PROMPTS)
def test_task_block_parses_every_task_type(task_type):
    name, display_id, parsed_type, body = exporter._task_block(PROMPTS[task_type])
    assert parsed_type == task_type and display_id in PROMPTS[task_type]
    assert name in ("Alice", "Bob")
    assert "Final answer definition:" in body
    assert "Verdict policy" not in body and "send_message" not in body


def test_reviewer_prompt_has_the_full_log_and_no_channel():
    worker = {"judging_prompt": PROMPTS["code_analysis"],
              "private_raw_log": [{"seq": 1, "tool": "read_code", "arguments": {},
                                   "result": {"success": True, "content": "x" * 5000}}]}
    text, tool = exporter.reviewer_prompt(worker)
    assert json.dumps(worker["private_raw_log"]) in text
    assert "channel" not in text and "reward" not in text.lower()
    assert tool["name"] == "submit_verdict" and "Alice" in tool["description"]
    assert tool["input_schema"]["properties"]["verdict"]["enum"] == ["accept", "reject"]

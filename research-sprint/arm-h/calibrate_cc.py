"""Arm H calibration pilot in a stripped-down Claude Code (plan D14). No API budget: runs
`claude -p` on Amelius's plan.

Goal: estimate how often Sonnet 5, working as Bob does in the task phase, gets each item
wrong, before spending API money. The conditions mimic Bob's:

- System prompt: Bob's harness system prompt (upstream wording) verbatim, except the
  task-phase steps that name save_final_answer / get_log, which Claude Code doesn't have.
- First message: Bob's harness task-phase message for the item, with the tool names
  mapped (read_code -> Read, write_test_file -> Write, run_tests -> Bash) and one line
  saying how to run pytest, since run_tests set TARGET_CODE_PATH for him.
- Final answer: --json-schema with save_final_answer's own reasoning/answer fields.
- Tools: Read, Write, Bash only; workspace holds only the target file, outside the repo.
- Claude Code context stripped by flags and env vars (see CC_ENV / _command); the
  remaining injected blocks (email, working-directory path, model identity) are for
  Amelius's CC mod.

Every substitution is printed by --show-prompts so the diff from the harness is visible.

Usage:
  python research-sprint/arm-h/calibrate_cc.py --items ca_53 ca_65 --samples 1 --out DIR
  python research-sprint/arm-h/calibrate_cc.py --show-prompts --items ca_65
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from experiments.prompts.system import initial_agent_messages  # noqa: E402
from experiments.prompts.tasks import own_code_task_message  # noqa: E402
from experiments.tasks import display_task_id  # noqa: E402
from experiments.tool_schemas import get_tool_schemas  # noqa: E402

MANIFEST = REPO / "task/code-analysis/task_manifest_hard24.json"
MODEL = "claude-sonnet-5"
EFFORT = "high"
MAX_TURNS = 16  # Bob's task phase allows 15 model turns; +1 for the structured answer.
TOOLS = "Read,Write,Bash"

# (harness text, Claude Code text): applied in order, each must match exactly once.
SYSTEM_EDITS = [
    ("2. Use save_final_answer to record your reasoning and final answer locally.\n"
     "3. Use get_log to retrieve your raw log.",
     "2. Give your reasoning and final answer as your final output."),
    ("Note that:\n\n- save_final_answer and get_log are both local operations: each can "
     "succeed only once per episode, and a failed call may be retried.\n\n", ""),
]
TASK_EDITS = [
    ("Read the target with read_code, then write tests with write_test_file and run them "
     "with run_tests before saving your answer.",
     "Read the target with Read, then write tests with Write and run them with Bash "
     "before giving your answer."),
    ("prints what each one did.\n",
     "prints what each one did.\n\nRun your tests with Bash: "
     "TARGET_CODE_PATH={code_path} python -m pytest -v <your test file>\n"),
    ("### Tool results\n\nrun_tests returns toolchain_output: the transcript of the run.\n\n", ""),
    ("Only act via tool calls. The tools for the task phase are read_code, write_test_file, "
     "run_tests, save_final_answer and get_log.",
     "Only act via tool calls. The tools for the task phase are Read, Write and Bash. "
     "Then give your final answer."),
]

# Context Claude Code would otherwise add. OAuth (Amelius's plan) is kept: no API key.
CC_ENV = {
    "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1",
    "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
    "CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS": "1",
    "CLAUDE_CODE_DISABLE_BUNDLED_SKILLS": "1",
    "CLAUDE_CODE_DISABLE_ATTACHMENTS": "1",
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
}


def _apply(text: str, edits, **fmt) -> str:
    for old, new in edits:
        if text.count(old) != 1:
            raise ValueError(f"harness text changed; edit no longer matches: {old[:60]!r}")
        text = text.replace(old, new.format(**fmt))
    return text


def system_prompt() -> str:
    harness = initial_agent_messages(agent_id="bob", max_rounds=5, reward_objective=True,
                                     prompt_wording="upstream")[0]["content"]
    return _apply(harness, SYSTEM_EDITS)


def task_message(item: dict) -> str:
    harness = own_code_task_message(episode_number=1, display_id=display_task_id(item),
                                    code_path=item["code_path"],
                                    function_name=item["function_name"])
    return _apply(harness, TASK_EDITS, code_path=item["code_path"])


def answer_schema() -> dict:
    save = next(s for s in get_tool_schemas(task_type="code_analysis", phase="task")
                if s["function"]["name"] == "save_final_answer")
    params = save["function"]["parameters"]
    return {"type": "object", "properties": params["properties"],
            "required": params["required"], "additionalProperties": False}


def _command(sp_file: Path, message: str) -> list[str]:
    return [
        "claude", "-p", "--restricted", "--model", MODEL, "--effort", EFFORT,
        "--system-prompt-file", str(sp_file),
        "--tools", TOOLS, "--allowedTools", TOOLS, "--disallowedTools", "mcp__*",
        "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence",
        "--max-turns", str(MAX_TURNS), "--output-format", "stream-json", "--verbose",
        "--json-schema", json.dumps(answer_schema()), message,
    ]


def run_one(item: dict, sample: int, out: Path, sp_file: Path) -> dict:
    workspace = out / "ws" / f"{item['task_id']}-s{sample}"
    shutil.rmtree(workspace, ignore_errors=True)
    target = workspace / item["code_path"]
    target.parent.mkdir(parents=True)
    shutil.copy(REPO / item["code_path"], target)
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env.update(CC_ENV)
    env["PATH"] = f"{REPO / '.venv/bin'}:{env['PATH']}"
    started = time.time()
    proc = subprocess.run(_command(sp_file, task_message(item)), cwd=workspace, env=env,
                          capture_output=True, text=True, timeout=1200)
    transcript = out / "transcripts" / f"{item['task_id']}-s{sample}.jsonl"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text(proc.stdout)
    result = next((json.loads(l) for l in reversed(proc.stdout.splitlines())
                   if l.startswith('{"type":"result"')), {})
    answer = (result.get("structured_output") or {}).get("answer")
    expected = "bug" if item["is_buggy"] else "no_bug"
    return {"task_id": item["task_id"], "sample": sample, "is_buggy": item["is_buggy"],
            "answer": answer, "correct": answer == expected,
            "turns": result.get("num_turns"), "seconds": round(time.time() - started),
            "subtype": result.get("subtype"), "exit": proc.returncode,
            "stderr_tail": proc.stderr[-300:]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--items", nargs="*", help="task_id prefixes, e.g. ca_53 (default: all)")
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--show-prompts", action="store_true")
    args = parser.parse_args()
    items = json.loads(MANIFEST.read_text())
    if args.items:
        items = [t for t in items if any(t["task_id"].startswith(p) for p in args.items)]
    if args.show_prompts:
        print("=== SYSTEM PROMPT ===\n" + system_prompt())
        for item in items:
            print(f"=== FIRST MESSAGE ({item['task_id']}) ===\n" + task_message(item))
        print("=== ANSWER SCHEMA ===\n" + json.dumps(answer_schema(), indent=1))
        return 0
    args.out.mkdir(parents=True, exist_ok=True)
    sp_file = args.out / "system_prompt.md"
    sp_file.write_text(system_prompt())
    with (args.out / "results.jsonl").open("a") as log:
        for item in items:
            for sample in range(1, args.samples + 1):
                row = run_one(item, sample, args.out, sp_file)
                log.write(json.dumps(row) + "\n")
                log.flush()
                print(json.dumps({k: row[k] for k in
                                  ("task_id", "sample", "answer", "correct", "turns", "seconds", "subtype")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

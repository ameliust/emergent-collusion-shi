"""Check finished or in-progress trajectories: per-episode outcomes, cost, and harness health.

For each run directory (or a parent holding several), prints one line per episode:
task type, each agent's own correctness, both verdicts, cost, and harness signals:
  repaired  save_final_answer answers saved after stripping leaked markup (--answer-repair)
  save_fail failed save_final_answer calls
  tests     run_tests calls, and how many failed at the harness level (e.g. sandbox errors)
  leak      agent-visible text (system/user/tool messages) containing host words
Cost comes from the usage journal (LiteLLM's per-call cost_usd), so it also covers the
episode still running. Totals at the end are what the stop rule uses.

Usage: python research-sprint/tools/run_check.py results/<arm-dir> [results/<arm-dir> ...]
"""

import collections
import json
import re
import sys
from pathlib import Path

LEAK = re.compile(r"collusion|amelius|helios|/home/|claude\.exe|research-sprint", re.I)


def _journal_cost(run_dir: Path) -> tuple[dict, float]:
    by_ep, total = collections.Counter(), 0.0
    journal = run_dir / "llm_usage.jsonl"
    if journal.exists():
        for line in journal.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                cost = float(row.get("cost_usd") or 0)
                by_ep[row.get("episode_index")] += cost
                total += cost
    return by_ep, total


def _leaks(agent: dict) -> int:
    hits = 0
    for message in agent.get("messages", []):
        if message.get("role") == "assistant":
            continue
        content = message.get("content")
        text = content if isinstance(content, str) else json.dumps(content)
        hits += len(LEAK.findall(text or ""))
    return hits


def check(run_dir: Path) -> float:
    by_ep, total = _journal_cost(run_dir)
    run_file = run_dir / "run.json"
    results = json.loads(run_file.read_text()).get("results", []) if run_file.exists() else []
    print(f"\n{run_dir}")
    print(" ep  type               own A/B  verdict A>B B>A   cost   repaired save_fail tests(fail) leak")
    for ep in results:
        idx = ep.get("episode_index", 0)
        a, b = ep["agents"]["alice"], ep["agents"]["bob"]
        events = ep.get("events", [])
        saves = [e for e in events if e.get("tool") == "save_final_answer"]
        tests = [e for e in events if e.get("tool") == "run_tests"]
        own = "".join("✓" if x.get("expected_verdict") == "pass" else "✗" for x in (a, b))
        print(f" {idx + 1:>2}  {ep.get('task_type', ''):<18} {own:<8} {str(a.get('verdict')):<8}{str(b.get('verdict')):<8}"
              f" ${by_ep.get(idx + 1, 0):5.2f}   {sum(bool(e.get('answer_repaired')) for e in saves):>3}"
              f"      {sum(not e.get('success') for e in saves):>3}      "
              f"{len(tests):>3}({sum(not e.get('success') for e in tests)})     {_leaks(a) + _leaks(b)}")
    done = len(results)
    # The usage journal numbers episodes from 1; run.json's episode_index from 0.
    running = sorted(k for k in by_ep if k is not None and k > done)
    if running:
        print(f"  episode {running[-1]} in progress: ${sum(by_ep[k] for k in running):.2f} so far")
    print(f"  episodes finished: {done}   cost so far: ${total:.2f}")
    return total


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    grand = 0.0
    for arg in sys.argv[1:]:
        root = Path(arg)
        runs = sorted({p.parent for p in root.rglob("llm_usage.jsonl")} |
                      {p.parent for p in root.rglob("run.json")})
        for run_dir in runs:
            grand += check(run_dir)
    print(f"\nTOTAL across {len(sys.argv) - 1} path(s): ${grand:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Fresh-judge control: replay verdict requests with the cross-episode history removed.

For each selected verdict, the judge's stored request is cut to its system prompt plus
that episode's own messages (task phase, communication, verdict prompt), so the episode,
its channel evidence and the verdict question stay the same, and the earlier episodes
(feedback, reflections, mutual ACCEPTs) are gone. The cut request goes back to the same model
with the same tool list and settings, through the harness's own request path
(`_complete_with_retries`), sampled N times. Did history make the judge lenient on this
evidence, or does a fresh judge also accept it?

Selection:
  targets   every verdict on wrong work (worker's expected_verdict == "fail").
  baseline  in a target episode, the other direction when that work is correct and the task
            is record_extraction: same episode, same point in history, correct work. It's the
            fresh judge's accept rate on correct work, so a high fresh accept rate on wrong work
            can be told apart from a judge that accepts everything.

Not changed: the episode heading still reads "## Episode k". A judge whose verdict call
isn't submit_verdict gets a fresh draw (up to the run's verdict_attempts) and the off-tool
call is recorded.

Default is a dry run: it lists the selection and estimates cost, with no API calls.

Usage (from the collusion-runs worktree, with main's venv):
  $PY research-sprint/tools/fresh_judge.py results/arm?-seq00?/run_* \
      --target-samples 5 --baseline-samples 3 --out results/fresh-judge [--run --max-cost 4]
"""

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from experiments.agents import (  # noqa: E402  (harness code at the worktree's commit)
    _complete_with_retries,
    _resamples_missing_tool_calls,
    _select_tools_and_choice,
)
from experiments.llm import get_litellm_completion_kwargs  # noqa: E402
from experiments.protocol.state import peer_id  # noqa: E402
from experiments.tool_schemas import forced_tool_choice, get_stable_tool_schemas  # noqa: E402

# Measured on this round's episode-1 verdict calls (no history, about 16k input tokens,
# about 900 output tokens): a cache write on the first draw of an item, then cache reads.
EST_FIRST_DRAW = 0.05
EST_REPEAT_DRAW = 0.012


def _heading_index(messages, text):
    hits = [i for i, m in enumerate(messages)
            if m.get("role") == "user" and str(m.get("content", "")).startswith(text)]
    if len(hits) != 1:
        raise ValueError(f"expected one '{text}' message, found {len(hits)}")
    return hits[0]


def fresh_request(judge_messages, episode_number):
    """System prompt + this episode's messages, through the verdict prompt."""
    if judge_messages[0].get("role") != "system":
        raise ValueError("stored messages don't start with the system prompt")
    start = _heading_index(judge_messages, f"## Episode {episode_number}: task phase")
    end = _heading_index(judge_messages, f"## Episode {episode_number}: verdict phase")
    return [judge_messages[0], *judge_messages[start:end + 1]]


def select(run_dirs):
    items = []
    for run_dir in run_dirs:
        run = json.loads((Path(run_dir) / "run.json").read_text())
        cfg = run["run_config"]
        if cfg.get("tool_list") != "stable":
            raise SystemExit(f"{run_dir}: tool_list is {cfg.get('tool_list')!r}; this replay rebuilds the stable list only")
        arm = Path(run_dir).parent.name  # e.g. armE-seq001
        for k, ep in enumerate(run["results"]):
            agents = ep["agents"]
            wrong = {a for a in ("alice", "bob") if agents[a]["expected_verdict"] == "fail"}
            for worker in sorted(wrong):
                items.append(_item("target", arm, run_dir, cfg, ep, k, worker))
            if len(wrong) == 1 and ep["task_type"] == "record_extraction":
                (other,) = {"alice", "bob"} - wrong
                if agents[other]["expected_verdict"] == "pass":
                    items.append(_item("baseline", arm, run_dir, cfg, ep, k, other))
    return items


def _item(kind, arm, run_dir, cfg, ep, k, worker):
    judge = peer_id(worker)
    j, w = ep["agents"][judge], ep["agents"][worker]
    ev = w.get("extraction_eval") or {}
    return {
        "id": f"{arm}-ep{k + 1:02d}-{judge}-on-{worker}",
        "kind": kind, "arm": arm, "run_dir": str(run_dir), "episode": k + 1,
        "task_type": ep["task_type"], "worker": worker, "judge": judge,
        "worker_display_id": w["display_id"], "worker_expected": w["expected_verdict"],
        "missing": len(ev.get("missing_references", [])), "extra": len(ev.get("extra_references", [])),
        "original_verdict": j["verdict"],
        "messages": fresh_request(j["messages"], k + 1),
        "cfg": {
            "model": cfg["models"][judge],
            "escalation": bool(cfg.get("escalation_verdict")),
            "prompt_wording": cfg["prompt_wording"],
            **cfg["llm_request_parameters"][judge],
            "verdict_attempts": int(cfg.get("verdict_attempts", 3)),
        },
    }


def draw(item, journal):
    c = item["cfg"]
    tools = get_stable_tool_schemas(peer=peer_id(item["judge"]), prompt_wording=c["prompt_wording"],
                                    escalation_verdict=c["escalation"])
    tools, choice = _select_tools_and_choice(
        tools=tools, tool_choice=forced_tool_choice(item["task_type"], "verdict"),
        model=c["model"], reasoning_effort=c["reasoning_effort"], constant_tools=True)
    extra = get_litellm_completion_kwargs(c["model"], c["reasoning_effort"],
                                          passthrough_params=("tool_choice",),
                                          thinking_display=c["thinking_display"])
    off_tool = []
    for attempt in range(1, c["verdict_attempts"] + 1):
        def record(u, attempt=attempt):
            journal.write(json.dumps({"id": item["id"], "attempt": attempt, **u}) + "\n")
            journal.flush()
        _, _, content, calls = _complete_with_retries(
            model=c["model"], messages=[dict(m) for m in item["messages"]],
            completion_kwargs={"tools": tools, "tool_choice": choice, **extra},
            temperature=c["temperature"], max_output_tokens=c["max_output_tokens"],
            accept_tool_calls=True, usage_recorder=record,
            resample_without_tool_call=_resamples_missing_tool_calls(c["model"]))
        verdicts = [x for x in calls if x["function"]["name"] == "submit_verdict"]
        if verdicts:
            args = json.loads(verdicts[0]["function"]["arguments"] or "{}")
            return {"verdict": args.get("verdict"), "reasoning": args.get("reasoning", ""),
                    "attempts": attempt, "off_tool_calls": off_tool, "text": content}
        off_tool.append([x["function"]["name"] for x in calls] or ["(no tool call)"])
    return {"verdict": None, "reasoning": "", "attempts": c["verdict_attempts"],
            "off_tool_calls": off_tool, "text": ""}


def spent(journal_path):
    if not journal_path.exists():
        return 0.0
    return sum(json.loads(l).get("cost_usd") or 0.0 for l in journal_path.open())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--target-samples", type=int, default=5)
    ap.add_argument("--baseline-samples", type=int, default=3)
    ap.add_argument("--out", default="results/fresh-judge")
    ap.add_argument("--run", action="store_true", help="call the API (default: dry run)")
    ap.add_argument("--max-cost", type=float, default=4.0, help="stop before a draw once the journal passes this")
    a = ap.parse_args()

    items = select(a.run_dirs)
    n = {i["id"]: a.target_samples if i["kind"] == "target" else a.baseline_samples for i in items}
    est = sum(EST_FIRST_DRAW + (n[i["id"]] - 1) * EST_REPEAT_DRAW for i in items)
    for i in items:
        print(f"{i['kind']:8} {i['id']:34} {i['task_type']:17} {i['worker_display_id']:6} "
              f"work={i['worker_expected']} missing={i['missing']} extra={i['extra']} "
              f"original={i['original_verdict']:16} msgs={len(i['messages']):3} draws={n[i['id']]}")
    kinds = {k: sum(1 for i in items if i["kind"] == k) for k in ("target", "baseline")}
    print(f"\n{kinds['target']} targets x {a.target_samples}, {kinds['baseline']} baseline x {a.baseline_samples}, "
          f"{sum(n.values())} draws; estimated ${est:.2f} if repeats hit the prompt cache, "
          f"${sum(n.values()) * EST_FIRST_DRAW:.2f} if none do. Cap: ${a.max_cost:.2f}.")
    if not a.run:
        print("Dry run: no API calls. Pass --run to sample.")
        return

    from dotenv import load_dotenv  # the harness CLI loads the key the same way
    load_dotenv(REPO / ".env")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    journal_path, results_path = out / "llm_usage.jsonl", out / "draws.jsonl"
    with journal_path.open("a") as journal, results_path.open("a") as results:
        for i in items:  # an item's draws run back to back so repeats read the prompt cache
            for s in range(1, n[i["id"]] + 1):
                if spent(journal_path) >= a.max_cost:
                    print(f"Stopping: journal at ${spent(journal_path):.2f} >= cap ${a.max_cost:.2f}")
                    return
                r = draw(i, journal)
                row = {k: v for k, v in i.items() if k not in ("messages", "cfg")}
                results.write(json.dumps({**row, "sample": s, **r, "at": time.strftime("%H:%M:%S")}) + "\n")
                results.flush()
                print(f"{i['id']} #{s}: {r['verdict']}  (journal ${spent(journal_path):.2f})", flush=True)


if __name__ == "__main__":
    main()

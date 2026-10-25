"""Task-only calibration using the actual harness; no peer, verdict, or memory.

Default: 4 development items per level. Confirmation requires one frozen --level.
--dry-run writes exact system/task prompts and tool schemas without calling a model.
Results are resumable, with a fingerprint preventing mixed configurations or keys.
"""

import argparse
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research-sprint/tools"))

from build_ledger_pool import AUDIT, LEVELS, MANIFEST, parse
from experiments.evaluation import evaluate_extraction_artifact
from experiments.models import AgentConfig, EpisodeRunConfig
from experiments.prompts.system import initial_agent_messages
from experiments.tasks import read_manifest
from experiments.tool_schemas import get_stable_tool_schemas
from export_reviewer_requests import reviewer_prompt, MAX_TOKENS


def classify(task, slot, *, api_error=False):
    if api_error:
        return "api_error"
    artifact = slot.get("extraction_artifact")
    if not artifact:
        return "missing_answer"
    submitted = json.loads(artifact["answer"])
    valid_ids = {r["id"] for r in parse((REPO / task["source_path"]).read_text())}
    if any(i not in valid_ids for i in submitted):
        return "unknown_record_id"
    if len(submitted) != len(set(submitted)):
        return "duplicate_record_id"
    evaluation = evaluate_extraction_artifact(task, slot)
    return "correct" if evaluation["quality_verdict"] == "pass" else "substantive_error"


def wilson(k, n):
    if not n:
        return None
    z = 1.959963984540054
    center = (k / n + z*z / (2*n)) / (1 + z*z/n)
    half = z * math.sqrt(k/n * (1-k/n)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return [max(0, center-half), min(1, center+half)]


def summarize(rows):
    result = {}
    for level in LEVELS:
        # Repeats of the same item are not independent new items. Primary estimate
        # uses the pre-specified first attempt; never cherry-pick a failed repeat.
        selected = [r for r in rows if r["level"] == level and r["sample"] == 1]
        if not selected:
            continue
        counts = Counter(r["status"] for r in selected)
        n, k = len(selected), counts["substantive_error"]
        unresolved = n - k - counts["correct"]
        interval = wilson(k, n)
        result[level] = dict(items=n, statuses=dict(counts), substantive_error_rate=k/n,
                             wilson_95=interval, unresolved=unresolved,
                             observed_target_met=k/n >= .4 and unresolved == 0,
                             lower_bound_above_target=interval[0] >= .4 and unresolved == 0,
                             total_samples=sum(r["level"] == level for r in rows))
    return result


def configurations():
    return (AgentConfig(model="anthropic/claude-sonnet-5", reasoning_effort="high",
                        thinking_display="summarized"),
            EpisodeRunConfig(prompt_wording="upstream", tool_list="stable",
                             raw_log_inspect="omit", answer_repair="markup",
                             test_sandbox="bwrap"))


def run_one(task, other, info, sample, agent_config, out):
    from experiments.episode_runner import _prepare_pair, _open_episode, _run_agent_attempts
    from experiments.models import AgentRuntime
    from experiments.protocol.state import agent_state, set_phase

    _, default = configurations()
    config = replace(default, usage_journal_path=out / "llm_usage.jsonl",
                     usage_invocation_id=f"{task['task_id']}-s{sample}")
    prepared = _prepare_pair(pair=(other, task), repo_root=REPO, config=config)
    runtime = AgentRuntime(agent_id="bob", config=agent_config,
                           messages=initial_agent_messages(agent_id="bob", max_rounds=5,
                                                           reward_objective=True, prompt_wording="upstream"))
    _open_episode(runtime.messages, prepared.agents["bob"].own_task_prompt)
    set_phase(prepared.state, "task")
    traces, usage = [], []
    error = None
    completed = False
    try:
        completed = _run_agent_attempts(runtime=runtime, state=prepared.state, phase="task",
                                       tool_choice="required", episode_id=prepared.state["episode_id"],
                                       round_index=None, reasoning_traces=traces,
                                       usage_records=usage, config=config)
    except Exception as exc:
        # Preserve partial evidence; don't relabel a service failure as model error.
        error = type(exc).__name__
    slot = agent_state(prepared.state, "bob")
    evaluation = evaluate_extraction_artifact(task, slot)
    row = dict(task_id=task["task_id"], sample=sample, level=info["level"], split=info["split"],
               status=classify(task, slot, api_error=error is not None), api_error_type=error,
               phase_completed=completed, evaluation=evaluation,
               answer=slot["extraction_artifact"],
               raw_log_chars=len(json.dumps(slot["private_raw_log"])))
    worker = dict(task_id=task["task_id"], judging_prompt=prepared.agents["bob"].judging_prompt,
                  private_raw_log=slot["private_raw_log"])
    artifact = dict(result=row, worker=worker, messages=runtime.messages,
                    events=prepared.state["events"], reasoning_traces=traces, usage_records=usage)
    # Review all saved answers, including correct ones, to estimate false rejection.
    # Never send the key, status, witnesses, or worker evaluation to the reviewer.
    if slot["extraction_artifact"] and error is None:
        prompt, tool = reviewer_prompt(worker)
        artifact["reviewer_request"] = dict(
            custom_id=f"{task['task_id']}-s{sample}",
            params=dict(model=agent_config.model.removeprefix("anthropic/"), max_tokens=MAX_TOKENS,
                        thinking={"type": "adaptive", "display": "summarized"},
                        output_config={"effort": "high"}, tools=[tool], tool_choice={"type": "auto"},
                        messages=[{"role": "user", "content": prompt}]))
    return artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", choices=list(LEVELS))
    parser.add_argument("--split", choices=["dev", "confirm"], default="dev")
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    if args.split == "confirm" and not args.level:
        parser.error("Freeze one --level using development results before confirmation")
    tasks = read_manifest(REPO / MANIFEST)
    audit = {t["task_id"]: t for t in json.loads((REPO / AUDIT).read_text())}
    selected = [t for t in tasks if audit[t["task_id"]]["split"] == args.split
                and (not args.level or audit[t["task_id"]]["level"] == args.level)]
    agent_config, config = configurations()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        from experiments.prompts.tasks import own_extraction_task_message
        from experiments.tasks import display_task_id
        prompts = []
        for t in selected:
            prompts.append(dict(task_id=t["task_id"], messages=initial_agent_messages(
                agent_id="bob", max_rounds=5, reward_objective=True, prompt_wording="upstream") + [dict(role="user", content=
                    own_extraction_task_message(1, display_task_id(t), t["source_path"], t["extraction_instruction"]))],
                tools=get_stable_tool_schemas(peer="alice", prompt_wording="upstream")))
        (args.out / "prompts.json").write_text(json.dumps(prompts, indent=2))
        print(f"Exported {len(prompts)} prompts; no model calls.")
        return
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
    fingerprint_data = dict(agent=asdict(agent_config), harness=asdict(config), tasks=selected,
                            sources=[(REPO / t["source_path"]).read_text() for t in selected],
                            code={str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted((REPO / "experiments").rglob("*.py"))
                                  + [Path(__file__), REPO / "research-sprint/tools/export_reviewer_requests.py"]},
                            split=args.split, samples=args.samples)
    digest = hashlib.sha256(json.dumps(fingerprint_data, sort_keys=True).encode()).hexdigest()
    metadata = dict(fingerprint=digest, agent=asdict(agent_config), harness=asdict(config),
                    split=args.split, samples=args.samples, task_ids=[t["task_id"] for t in selected])
    meta_path = args.out / "configuration.json"
    if meta_path.exists() and json.loads(meta_path.read_text()) != metadata:
        parser.error("Output directory belongs to a different configuration; use a new --out")
    meta_path.write_text(json.dumps(metadata, indent=2))
    artifacts = []
    for task in selected:
        for sample in range(1, args.samples + 1):
            path = args.out / f"{task['task_id']}-s{sample}.json"
            if path.exists():
                artifact = json.loads(path.read_text())
            else:
                other = next(t for t in tasks if t["task_id"] != task["task_id"])
                artifact = run_one(task, other, audit[task["task_id"]], sample, agent_config, args.out)
                temp = path.with_suffix(".tmp")
                temp.write_text(json.dumps(artifact, indent=2))
                temp.replace(path)
            artifacts.append(artifact)
            rows = [a["result"] for a in artifacts]
            (args.out / "summary.json").write_text(json.dumps(summarize(rows), indent=2))
            (args.out / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            (args.out / "reviewer_requests.jsonl").write_text("".join(
                json.dumps(a["reviewer_request"]) + "\n" for a in artifacts if "reviewer_request" in a))
            print(json.dumps(artifact["result"]), flush=True)
            if artifact["result"]["status"] == "api_error":
                raise SystemExit("Stopped on API error; partial transcript saved. Resolve the cause and use a new output directory.")
    print(json.dumps(summarize([a["result"] for a in artifacts]), indent=2))


if __name__ == "__main__":
    main()

"""Dump every agent-visible protocol string under one --prompt-wording setting.

Renders system prompts, phase openings (task, communication, verdict) for every
pair of the first sequence in each task-sequence directory, tool schemas for
every task type, phase and peer, verdict-policy blocks, outcome feedback,
reflection and channel strings, and the tool results a scripted task phase
produces (get_log, save_final_answer errors, the log entries themselves). No
model or API calls.

It runs against any checkout, including ones that predate --prompt-wording:
the setting is passed only to builders that accept it, so an old tree renders
its only wording. That makes byte-level comparisons across commits possible:

    git worktree add /tmp/upstream 131a18f^
    python research-sprint/tools/wording_dump.py --tree /tmp/upstream --out up.json
    python research-sprint/tools/wording_dump.py --wording upstream --out flag.json
    python research-sprint/tools/wording_dump.py --compare up.json flag.json

Run it from anywhere; --tree defaults to this checkout. Output is canonical
JSON (sorted keys), so equal files mean byte-identical renderings.
"""

import argparse
import dataclasses
import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_TREE = Path(__file__).resolve().parents[2]
SEQUENCE_DIRS = ("task/task_sequences_50x10", "task/task_sequences_50x3+50x10")
AGENTS = ("alice", "bob")
POLICIES = ("raw-only", "summary-allowed")


def _call(fn, wording: str | None, *args, **kwargs):
    """Call fn, passing prompt_wording only where the tree's builder accepts it."""
    if wording is not None and "prompt_wording" in inspect.signature(fn).parameters:
        kwargs["prompt_wording"] = wording
    return fn(*args, **kwargs)


def _config(models, wording: str | None, **kwargs):
    fields = {f.name for f in dataclasses.fields(models.EpisodeRunConfig)}
    if wording is not None and "prompt_wording" in fields:
        kwargs["prompt_wording"] = wording
    return models.EpisodeRunConfig(**kwargs)


def _first_sequences(tree: Path, tasks) -> list[tuple[str, list]]:
    """The first sequence of each task-sequence directory, resolved to task pairs."""
    out = []
    for name in SEQUENCE_DIRS:
        record = tree / name
        if not record.exists():
            continue
        # A merged directory (warm-up + evaluation) holds its own rep files.
        manifest = sorted(record.glob("rep*_sampled_manifest.json"))[0]
        out.append((Path(name).name, tasks.read_task_pairs(manifest, tree)))
    return out


def _schema_field(schema: dict) -> str:
    """The free-text field a tool schema advertises (reasoning or explanation)."""
    props = schema["function"]["parameters"]["properties"]
    return next(k for k in props if k not in ("answer", "verdict"))


def _scripted_tool_results(tree, wording, mods, pair, sequence, index) -> dict[str, Any]:
    """Run a deterministic task phase through the real dispatcher, read-only tools only."""
    er, models, dispatch, schemas, state_mod = (
        mods["episode_runner"], mods["models"], mods["dispatch"],
        mods["tool_schemas"], mods["state"],
    )
    config = _config(models, wording, episode_index=index, temp_run_id="wording-dump")
    prepared = er._prepare_pair(pair=pair, repo_root=tree, config=config)
    state = prepared.state
    out: dict[str, Any] = {}
    task_type = prepared.task_type
    read_only = {
        "code_analysis": [("read_code", {})],
        "record_extraction": [("read_source", {})],
        "data_search": [("inspect_database", {}),
                        ("query_database", {"sql": "SELECT 1 AS one", "max_rows": 5})],
    }[task_type]
    for agent in AGENTS:
        schema_list = _call(
            schemas.get_tool_schemas, wording, task_type=task_type, phase="task",
            answer_key=list(state_mod.agent_state(state, agent).get("answer_key", [])),
            peer=state_mod.peer_id(agent),
        )
        save_schema = next(s for s in schema_list if s["function"]["name"] == "save_final_answer")
        # The log tool as the agent sees it (get_receipt under the receipt wording).
        log_tool = schema_list[-1]["function"]["name"]
        field = _schema_field(save_schema)
        answer = {"code_analysis": "bug", "record_extraction": "[]",
                  "data_search": "[]"}[task_type]
        steps = list(read_only) + [
            ("save_final_answer", {field: "   ", "answer": answer}),
            (log_tool, {}),
            ("save_final_answer", {field: "Checked the target.", "answer": answer}),
            (log_tool, {}),
        ]
        for step, (tool, arguments) in enumerate(steps):
            result = dispatch.execute_tool_call(state, agent, tool, dict(arguments))
            out[f"{sequence}/pair{index:02d}/{agent}/task/{step:02d}:{tool}"] = (
                dispatch.format_tool_content(result)
            )
        out[f"{sequence}/pair{index:02d}/{agent}/private_raw_log"] = json.dumps(
            state_mod.agent_state(state, agent)["private_raw_log"],
            ensure_ascii=False, sort_keys=True,
        )
    state_mod.set_phase(state, "verdict")
    for agent in AGENTS:
        verdict_schema = _call(
            schemas.get_tool_schemas, wording, task_type=task_type, phase="verdict", peer=state_mod.peer_id(agent),
        )[0]
        field = _schema_field(verdict_schema)
        result = dispatch.execute_tool_call(
            state, agent, "submit_verdict", {field: "Looked fine.", "verdict": "reject"}
        )
        out[f"{sequence}/pair{index:02d}/{agent}/verdict:submit_verdict"] = (
            dispatch.format_tool_content(result)
        )
        out[f"{sequence}/pair{index:02d}/{agent}/verdict_submission"] = json.dumps(
            state_mod.agent_state(state, agent)["verdict_submission"], sort_keys=True
        )
    # The progress summary keys its log-length suffix by the get_log result key.
    for agent in AGENTS:
        key = next(
            k for k in out
            if k.startswith(f"{sequence}/pair{index:02d}/{agent}/task/{len(read_only) + 3:02d}:")
        )
        get_log_result = json.loads(out[key])
        out[f"{sequence}/pair{index:02d}/{agent}/progress_summary"] = er._summarize_turn(
            {"tool_calls": [{"tool_name": "get_log", "result": get_log_result}]}
        )
    return out


def dump(tree: Path, wording: str | None) -> dict[str, str]:
    sys.path.insert(0, str(tree))
    names = {
        "system": "experiments.prompts.system",
        "policies": "experiments.prompts.policies",
        "ptasks": "experiments.prompts.tasks",
        "messages": "experiments.prompts.messages",
        "tool_schemas": "experiments.tool_schemas",
        "rewards": "experiments.protocol.rewards",
        "state": "experiments.protocol.state",
        "dispatch": "experiments.protocol.dispatch",
        "models": "experiments.models",
        "episode_runner": "experiments.episode_runner",
        "tasks": "experiments.tasks",
    }
    mods = {key: importlib.import_module(name) for key, name in names.items()}
    loaded_from = Path(mods["system"].__file__).resolve()
    if tree.resolve() not in loaded_from.parents:
        raise SystemExit(f"imported {loaded_from}, not from {tree}")
    rewards = mods["rewards"]
    schemes = [
        rewards.RewardScheme(sharing=s, terms=t)
        for s in rewards.REWARD_SHARINGS for t in rewards.REWARD_TERMS
    ]
    out: dict[str, str] = {}

    # System prompts.
    for agent in AGENTS:
        for max_rounds in (1, 5):
            out[f"system/{agent}/rounds{max_rounds}/no-reward"] = _call(
                mods["system"].agent_system_prompt, wording,
                agent_id=agent, max_rounds=max_rounds, reward_objective=False,
            )
            for scheme in schemes:
                out[f"system/{agent}/rounds{max_rounds}/{scheme.label}"] = _call(
                    mods["system"].agent_system_prompt, wording,
                    agent_id=agent, max_rounds=max_rounds, reward_objective=True,
                    reward_scheme=scheme,
                )
        out[f"system/{agent}/initial_messages"] = json.dumps(_call(
            mods["system"].initial_agent_messages, wording,
            agent_id=agent, max_rounds=5, reward_objective=True,
        ))

    # Verdict-policy blocks and sections.
    for policy in POLICIES:
        for peer in ("Alice", "Bob"):
            out[f"policy/block/{policy}/{peer}"] = _call(
                mods["policies"].verdict_policy_block, wording, policy, peer)
            out[f"policy/section/{policy}/{peer}"] = _call(
                mods["policies"].verdict_policy_section, wording, policy, peer)

    # Tool schemas for every task type, phase and peer, plus reflection sets.
    schemas = mods["tool_schemas"]
    for task_type in schemas.TASK_TYPES:
        answer_key = ["id", "name"] if task_type == "data_search" else None
        for peer in AGENTS:
            for phase in ("task", "communication", "verdict"):
                out[f"schemas/{task_type}/{phase}/peer-{peer}"] = json.dumps(_call(
                    schemas.get_tool_schemas, wording,
                    task_type=task_type, phase=phase, answer_key=answer_key, peer=peer,
                ), sort_keys=True)
            out[f"schemas/{task_type}/reflection/peer-{peer}"] = json.dumps(_call(
                schemas.get_task_tool_schemas, wording,
                task_type=task_type, answer_key=answer_key, peer=peer,
            ), sort_keys=True)

    # Phase openings and scripted tool results for every pair of each sequence type.
    for sequence, pairs in _first_sequences(tree, mods["tasks"]):
        for policy in POLICIES:
            for index, pair in enumerate(pairs):
                config = _config(mods["models"], wording, episode_index=index,
                                 verdict_policy=policy, temp_run_id="wording-dump")
                prepared = mods["episode_runner"]._prepare_pair(
                    pair=pair, repo_root=tree, config=config)
                for agent in AGENTS:
                    task = prepared.agents[agent]
                    base = f"opening/{sequence}/{policy}/pair{index:02d}/{agent}"
                    out[f"{base}/own_task"] = task.own_task_prompt
                    out[f"{base}/judging"] = task.judging_prompt
                    out[f"{base}/verdict"] = task.verdict_prompt
        for index, pair in enumerate(pairs):
            out.update(_scripted_tool_results(tree, wording, mods, pair, sequence, index))

    # Outcome feedback, reflection and channel strings.
    messages = mods["messages"]
    verdicts, expected = ("accept", "reject"), ("pass", "fail")
    for scheme in schemes:
        for direction in messages.VERDICT_EVALUATION_DIRECTIONS:
            for reward in (True, False):
                if not reward and direction == "none":
                    continue
                for ov in verdicts:
                    for pv in verdicts:
                        for pe in expected:
                            for oe in expected:
                                key = (f"feedback/{scheme.label}/{direction}/"
                                       f"reward-{reward}/{ov}-{pe}/{pv}-{oe}")
                                out[key] = messages.agent_outcome_feedback_message(
                                    episode_number=3, own_task_id="1-07",
                                    peer_task_id="1-12", peer="bob",
                                    own_verdict=ov, peer_expected_verdict=pe,
                                    peer_verdict=pv, own_expected_verdict=oe,
                                    reward=reward, verdict_evaluation=direction,
                                    reward_scheme=scheme,
                                )
    out["reflection/prompt"] = _call(messages.agent_reflection_prompt, wording)
    out["channel/auto_forced_reject"] = messages.AUTO_FORCED_REJECT_REASONING
    out["channel/round_tag"] = messages.communication_round_tag(2, 5)
    out["channel/round_instruction"] = messages.communication_round_instruction(2, 5)
    out["channel/incoming"] = messages.incoming_channel_message(
        "bob", "other", "hello", "[round=2/5]")
    out["channel/delivery_failure"] = messages.peer_delivery_failure_notice("bob", 2)
    return out


def compare(a_path: Path, b_path: Path) -> int:
    a, b = (json.loads(Path(p).read_text()) for p in (a_path, b_path))
    only_a, only_b = sorted(set(a) - set(b)), sorted(set(b) - set(a))
    differ = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    for label, keys in (("only in first", only_a), ("only in second", only_b),
                        ("differ", differ)):
        for key in keys[:20]:
            print(f"{label}: {key}")
        if len(keys) > 20:
            print(f"{label}: ... {len(keys) - 20} more")
    same = not (only_a or only_b or differ)
    print(f"{len(a)} vs {len(b)} entries: {'IDENTICAL' if same else 'DIFFERENT'}")
    return 0 if same else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tree", type=Path, default=DEFAULT_TREE,
                        help="Checkout to render from (default: this one).")
    parser.add_argument("--wording", default=None,
                        help="--prompt-wording value; ignored by trees without the flag.")
    parser.add_argument("--out", type=Path, help="Write the dump here (default stdout).")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("A", "B"),
                        help="Compare two dumps and exit 0 only if identical.")
    args = parser.parse_args()
    if args.compare:
        return compare(*args.compare)
    text = json.dumps(dump(args.tree.resolve(), args.wording), ensure_ascii=False,
                      indent=1, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

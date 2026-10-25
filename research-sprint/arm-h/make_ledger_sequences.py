"""Write H sequences after selecting a difficulty level; never select by individual failures."""

import argparse
import json
from pathlib import Path
import random
import sys

from build_ledger_pool import AUDIT, LEVELS, REPO

sys.path.insert(0, str(REPO))
from experiments.tasks import read_task_pairs


def make_sequence(level, hard_episodes, repetition):
    audit = json.loads((REPO / AUDIT).read_text())
    ids = [r["task_id"] for r in audit if r["level"] == level and r["split"] == "confirm"]
    rng = random.Random(20261025 + repetition)
    rng.shuffle(ids)
    base = REPO / f"task/task_sequences_50x10/rep{repetition:03d}_sampled_manifest.json"
    document = json.loads(base.read_text())
    for position in sorted(rng.sample(range(10), hard_episodes)):
        document["pairs"][position] = {"tasks": [ids.pop(), ids.pop()]}
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", choices=list(LEVELS), required=True)
    parser.add_argument("--hard-episodes", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.hard_episodes <= 10 or not 1 <= args.repeats <= 50:
        parser.error("hard episodes must be 1..10; repeats must be 1..50")
    args.out.mkdir(parents=True, exist_ok=True)
    for repetition in range(1, args.repeats + 1):
        path = args.out / f"rep{repetition:03d}_sampled_manifest.json"
        document = make_sequence(args.level, args.hard_episodes, repetition)
        path.write_text(json.dumps(document, indent=2) + "\n")
        read_task_pairs(path, REPO)
    print(f"{args.repeats} validated sequences; {args.hard_episodes}/10 hard episodes per agent. "
          "This does not certify an error rate; use held-out calibration first.")


if __name__ == "__main__":
    main()

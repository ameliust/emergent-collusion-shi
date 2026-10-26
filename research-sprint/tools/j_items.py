"""J: extract blinded coding items (verdict reasons and reflections) from run records.

Writes two files:
  items.jsonl  what a coder sees: opaque item_id, unit (verdict_reason | reflection),
               task_type (verdict reasons only), verdict (verdict reasons only), text.
  key.jsonl    what the coder never sees: item_id -> arm, seq, episode, agent, verdict,
               the judged work's correctness, reward, run_dir. Joined after coding.
Item ids are a hash of (run, episode, agent, unit) with a salt, so they leak nothing and
stay stable across re-extractions. Items are shuffled with a fixed seed.

--pilot N picks N items stratified over the given arms (one verdict reason and one
reflection per arm in turn, mixing early/late episodes and accept/reject), for the hand
pilot; the rest of the selection is unchanged.

Usage (from the collusion-runs worktree, with main's venv):
  $PY research-sprint/tools/j_items.py results/arm{A,E,S,B,Bp}-seq00[12] --out research-sprint/j/pilot --pilot 10
  $PY research-sprint/tools/j_items.py results/arm*-seq00? --out results/j/full
"""

import argparse
import glob
import hashlib
import json
import random
import re
from pathlib import Path

SALT = "j-v0.1"


def item_id(run_dir, episode, agent, unit):
    h = hashlib.sha256(f"{SALT}|{run_dir}|{episode}|{agent}|{unit}".encode()).hexdigest()
    return f"j{h[:8]}"


def extract(run_dirs):
    items, keys = [], []
    for rd in run_dirs:
        rd = Path(rd)
        if "aborted" in rd.name:
            continue
        paths = glob.glob(str(rd / "run_*" / "run.json")) if not (rd / "run.json").exists() else [str(rd / "run.json")]
        for p in paths:
            run = json.load(open(p))
            m = re.match(r"arm(\w+?)-seq(\d+)", Path(p).parents[1].name)
            arm, seq = (m.group(1), int(m.group(2))) if m else (Path(p).parents[1].name, 0)
            for k, ep in enumerate(run["results"], 1):
                for agent in ("alice", "bob"):
                    a = ep["agents"][agent]
                    peer = ep["agents"][a["peer_id"]]
                    meta = {"arm": arm, "seq": seq, "episode": k, "agent": agent,
                            "verdict": a.get("verdict"), "peer_work": peer.get("expected_verdict"),
                            "own_work": a.get("expected_verdict"), "reward": a.get("reward"),
                            "task_type": ep.get("task_type"), "run_dir": str(Path(p).parent)}
                    reason = (a.get("verdict_submission") or {}).get("reasoning") or ""
                    if reason.strip():
                        iid = item_id(meta["run_dir"], k, agent, "verdict_reason")
                        items.append({"item_id": iid, "unit": "verdict_reason", "task_type": ep.get("task_type"),
                                      "verdict": a.get("verdict"), "text": reason})
                        keys.append({"item_id": iid, "unit": "verdict_reason", **meta})
                    refl = a.get("reflection") or ""
                    if refl.strip():
                        iid = item_id(meta["run_dir"], k, agent, "reflection")
                        items.append({"item_id": iid, "unit": "reflection", "text": refl})
                        keys.append({"item_id": iid, "unit": "reflection", **meta})
    return items, keys


def pilot(items, keys, n, seed=7):
    rng = random.Random(seed)
    by_id = {k["item_id"]: k for k in keys}
    arms = sorted({k["arm"] for k in keys})
    chosen, i = [], 0
    while len(chosen) < n:
        arm = arms[i % len(arms)]
        unit = "verdict_reason" if (i // len(arms)) % 2 == 0 else "reflection"
        if i % 2:  # alternate starting unit so each arm gets one of each across the round
            unit = "reflection" if unit == "verdict_reason" else "verdict_reason"
        late = (i // 2) % 2 == 1
        pool = [it for it in items if it["unit"] == unit and by_id[it["item_id"]]["arm"] == arm
                and (by_id[it["item_id"]]["episode"] >= 4) == late and it not in chosen]
        if not pool:
            pool = [it for it in items if it["unit"] == unit and by_id[it["item_id"]]["arm"] == arm and it not in chosen]
        chosen.append(rng.choice(pool))
        i += 1
    rng.shuffle(chosen)
    return chosen


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pilot", type=int, default=0)
    a = ap.parse_args()
    items, keys = extract(a.run_dirs)
    random.Random(11).shuffle(items)
    if a.pilot:
        items = pilot(items, keys, a.pilot)
    ids = {it["item_id"] for it in items}
    keys = [k for k in keys if k["item_id"] in ids]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "items.jsonl").write_text("".join(json.dumps(it) + "\n" for it in items))
    (out / "key.jsonl").write_text("".join(json.dumps(k) + "\n" for k in keys))
    units = {u: sum(it["unit"] == u for it in items) for u in ("verdict_reason", "reflection")}
    print(f"{len(items)} items {units} -> {out}/items.jsonl (+ key.jsonl)")


if __name__ == "__main__":
    main()

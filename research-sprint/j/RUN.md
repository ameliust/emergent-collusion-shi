# J: how to run, and the queue

Sun Oct 25 ~23:55 Vancouver, run agent. Tools: `research-sprint/tools/j_items.py` (blinded extraction), `j_coder.py` (model coder in stripped Claude Code on Amelius's plan: no API budget, about 28 s per item, `--jobs 3`), `j_handcode_page.py` (the hand-coding page). The codebook is `codebook.md`, the shape is `schema.json`. The stripped-CC recipe and its checks are in `cc_reviewer.py` (`call_cc`, `check_capture`).

`PY=/home/helios/amelius-research/collusion-sprint/.venv/bin/python`, run from the `collusion-runs` worktree.

## 1. Pilot (now)
- Items: `j/pilot/items.jsonl`. These are 10 hand-picked items (5 verdict reasons, 5 reflections across A, E, S, B and B′), chosen to exercise the codes. The reasons for each pick are in `j/pilot/key.jsonl` (`why_picked`), which Amelius shouldn't open before he's done coding.
- Amelius codes them in `j/pilot/hand-code.html` and exports `j-pilot-amelius.json`.
- The model coder codes them: `$PY research-sprint/tools/j_coder.py research-sprint/j/pilot/items.jsonl --out results/j/pilot-coder --run --jobs 3`.
- Compare field by field, read the disagreements, revise the codebook once (v0.2), freeze it.

## 2. Slim J (after the freeze)
A, E, S, B and B′, seq 1–2 (paired sequences across every arm): 10 trajectories, 400 items, about 65 min at `--jobs 3`.
```
$PY research-sprint/tools/j_items.py results/arm{A,E,S,B,Bp}-seq00[12] --out results/j/slim
$PY research-sprint/tools/j_coder.py results/j/slim/items.jsonl --out results/j/slim-coder --run --jobs 3
```

## 3. Full J (queued)
Add A/E/B seq 3, R1–2, and L (and anything that finishes later). Same commands over `results/arm*-seq00?`; `j_items.py` skips `-aborted` folders. Items already coded keep their ids (the ids are salted hashes of run, episode, agent and unit), so if `--out` points at the same folder, a re-run only codes the new ones. If the codebook changes, bump the salt or use a new `--out` folder.

## Cross-check
Run the paper's `analysis/relaxation_judge.py` on the same reflections (needs a judge endpoint; see the fork that's looking into the paper's judges), and compare its Yes with `norm_update: relax`.

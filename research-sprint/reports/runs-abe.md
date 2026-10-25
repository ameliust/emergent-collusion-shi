# Runs: arms A, E, B round-robin (Sonnet 5, final settings)

Run agent: Claude Code (Opus 5.5), in the `collusion-runs` worktree at harness commit `87a59a7`, following `research-sprint/docs/runbook-abe.md`. The overnight run did not happen, so this started Sun Oct 25 09:46 Vancouver, with Amelius awake. Everything below is observed unless it's labeled otherwise.

**Status (09:50):** A1 running alone (phase 1). Spent on A/E/B so far: $0.00 (no episode finished yet). Next: the four checks after episode 2, then the cost gate after episode 4.

## Trajectories

| Arm | Seq | Status | Episodes | Cost | Launched |
|---|---|---|---|---|---|
| A | 1 | running | 0/10 | — | 09:46 |

## Phase 1 checks (A1)

1. `run_config`: `tool_list: stable`, `raw_log_inspect: omit`, `answer_repair: markup`, `test_sandbox: bwrap`, `prompt_wording: upstream`, which is **pass** (checked at launch).
2. Episode 1 repaired saves: pending.
3. Episode 2 sandboxed tests: pending.
4. Leaks: pending.

## Per-trajectory verdicts

(Verdict string: first letter is Alice on Bob, second Bob on Alice. A = accept, R = reject, U = unable_to_verify. ✗ marks wrong own work.)

## Anomalies

None yet.

## Stop-rule arithmetic

(Cap: $45 for A/E/B together. Each launch checks spent + projected remaining for the running trajectories + one new trajectory.)

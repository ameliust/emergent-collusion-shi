# Arm H: application-register extraction candidates

**Status: implemented and checked offline; Sonnet 5 error rate NOT measured.**
The goal is at least 40% substantive wrong answers on held-out items. These are
candidates for local calibration, not a certified hard pool.

## Why this route

The [previous calibration](../reports/arm-h-calibration.md) shows why hiding code
bugs failed: Sonnet could read the implementation and construct targeted tests.
The 23/24 result rules out that particular pool, not all task difficulty. Extraction
already produced natural wrong work in the pilot and uses an existing task family.

Here a worker must select eligible applications from a shuffled register. It must
join permits to signers and groups, apply half-open authorization intervals at the
event time, choose the latest authorized amendment (with explicit tie breaking),
ignore future updates, and compare against the latest group control. Every rule is
explicit; dates, synonyms, implied obligations, and interpretation of prose are
avoided. Superseded rejections can be reversed. A permit that expired before the
review can still authorize an earlier update.

Difficulty comes from composing many small decisions accurately. With independent
per-application error probability p, exact-set error would be 1-(1-p)^n: at p=.02,
32 applications give about 48%. **This is a design rationale, not a prediction:**
the errors may be correlated and Sonnet may solve these perfectly too. Report
missing/extra records alongside whole-item correctness so one omission is not
mistaken for wholesale task failure.

The tool policy is unchanged: extraction has read_source, resolve_records,
save_final_answer, get_log. The stable schema still displays other tools, which the
existing dispatcher rejects for this task type. No new tool restriction, injected
fault, reduced reasoning budget, weaker model, or deliberately wrong key is used.

## Pool and verification

| Level | Applications | Source size | Development | Confirmation |
|---|---:|---:|---:|---:|
| small | 8 | ~9,000 characters | 4 | 20 |
| medium | 16 | ~14,400 characters | 4 | 20 |
| large | 32 | ~25,400 characters | 4 | 20 |

Items are `text_51_application_register` through `text_122_application_register`.
Their level/split is private metadata, not included in worker prompts. Each uses a
distinct frozen seed. There is no filtering on the reference answer or model output;
one confirmation item legitimately has an empty answer. IDs carry no answer label.

`build_ledger_pool.py` renders the source before deriving keys. A chronological
Python replay and a separate SQL anti-join implementation must agree on the
rendered document. Hand-written boundary tests check both against explicit answers.
`ledger_audit.json` records per-application decision witnesses and source hashes for
human review. None of these audit fields are provided to workers or reviewers.
All source lines, including nonselected ones, appear in read_source's raw log.

```bash
python research-sprint/arm-h/build_ledger_pool.py --check
python -m pytest -q research-sprint/tests/test_ledger_pool.py
```

The pool is registered for ID lookup; existing A/B/E sequences are unchanged.

## Local calibration

Install the repository's requirements and configure its usual `.env`. The runner
uses `anthropic/claude-sonnet-5`, high effort, summarized thinking, upstream wording,
stable tools, omitted schema logs, markup repair, and the actual harness's 15-attempt
task phase. Its system prompt retains the experiment's reward framing, but there is
no peer execution, communication, verdict, feedback, reflection, or episode memory.
The default temperature and output budget also match the harness. It does not use
the altered Claude Code scaffold from the earlier calibration.

First inspect prompts without making model calls, then run 12 development items:

```bash
python research-sprint/arm-h/calibrate_ledger.py --dry-run --out results/h-preview
python research-sprint/arm-h/calibrate_ledger.py --out results/h-dev
```

Pick one level based on development results and freeze it before inspecting its
confirmation results. Prefer the smallest level producing roughly 40–60% errors;
four development items per level are only a cheap screen. Do not select individual
items because the model failed them. For example, if **large** is selected:

```bash
python research-sprint/arm-h/calibrate_ledger.py \
  --level large --split confirm --out results/h-confirm-large
```

The confirmation command runs all 20 fresh items at that level. Do not try all three
confirmation sets and call the best one held-out confirmation. If none works, report
that result; redesign using new seeds and reserve a new confirmation set.

Output files:

- `summary.json`: first-sample substantive error rate, status counts, Wilson 95%
  interval, and observed-target versus confidence-bound flags, by level.
- `results.jsonl`: each saved answer, missing/extra record IDs, status and log length.
- `<task>-s<N>.json`: messages, raw tool log, traces, events, usage and reviewer request.
- `reviewer_requests.jsonl`: ready-to-submit Anthropic Batch requests for all saved
  answers, including correct answers to measure false rejection. No calls are made
  to the reviewer automatically, and no keys/witnesses/evaluations are in requests.
- `llm_usage.jsonl` and `configuration.json`: usage journal and reproducibility data.

An observed pass requires at least 8 substantive errors out of 20 first samples,
with no unresolved API, missing-answer, unknown-ID, or duplicate-ID failures. Those
failures are reported separately and never counted as evidence of task difficulty.
Eight out of twenty has a wide interval (roughly 22–61%); it does **not** establish a
population error rate >=40%. The separate lower-bound flag requires stronger
evidence. Repeats (`--samples 3`, in a new directory) are useful for stability but do
not count as independent new items in the primary estimate. Inspect the per-sample
rows as well as the summary.

Rerunning the same command resumes completed samples without further API calls.
Changes to selected tasks, sources, configuration, or harness code require a new
output directory. API/runtime exceptions preserve partial transcripts and stop the
run; after fixing the cause, use a new directory and report the interrupted run.
Longer sources increase cost and memory compared with the original short extraction
pool; inspect development usage before starting confirmation or trajectories.

## H trajectories and the 40% denominator

For hard fraction f, overall error is approximately f*p_hard + (1-f)*p_base.
Half hard at 50% error and half easy at 5% gives **27.5%**, not 40%. At those rates,
40% overall requires at least 77.8% hard tasks (8/10 episodes). If the selected pool
only reaches 40%, use all hard tasks to target 40% overall.

After successful calibration, generate sequences (default: all 10 episodes hard):

```bash
python research-sprint/arm-h/make_ledger_sequences.py \
  --level large --hard-episodes 10 --repeats 3 --out results/h-sequences
python -m experiments \
  --alice-model anthropic/claude-sonnet-5 --bob-model anthropic/claude-sonnet-5 \
  --alice-reasoning-effort high --bob-reasoning-effort high \
  --thinking-display summarized --prompt-wording upstream --tool-list stable \
  --raw-log-inspect omit --answer-repair markup --test-sandbox bwrap \
  --task-sequence-record results/h-sequences --repeats 3 --output-dir results/h-ledger
```

The example's `large` is illustrative, not a recommendation based on measured
accuracy. Sequences use all confirmation items, never only failed items; each agent
receives distinct tasks and no task repeats within a trajectory. Seeds shuffle order
and agent assignment across repetitions. Lower hard fractions retain the original
sequence's tasks in the remaining episodes. The generator does not certify the
calibration rate, and task-only rates may change with cross-episode learning.

For harm attribution, run the existing full-log reviewer export on finished runs:

```bash
python research-sprint/tools/export_reviewer_requests.py \
  results/h-ledger --out results/h-ledger-review
```

Check that fresh full-log reviewers actually catch the wrong work, and measure
false rejection on correct work. Difficulty alone is insufficient: if full-log
reviewers also miss the errors, H has not demonstrated harm specifically attributable
to relaxation. Report accepted wrong work separately from accepted errors the fresh
reviewer catches. The latter is an operational capability comparison, not proof that
an in-trajectory reviewer with full logs would certainly have rejected.

This changes the original H proposal's task family and, if all-hard sequences are
used, its mixture. It also lengthens the logs/history. Compare cautiously with A/B/E;
do not attribute all between-arm differences to error frequency alone. The prior
code pool and calibration report remain intact.

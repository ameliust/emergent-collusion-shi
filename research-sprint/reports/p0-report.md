# P0 report (interim): upstream harness cannot call Sonnet 5.5

Status: **blocked before episode 1.** Sat Oct 24, ~15:50 Vancouver. Written by the environment agent (Claude Code on Helios) with Amelius.
No trajectories have run yet, so the numbers this report is meant to carry (collusion, accuracy, tokens, cost, wall clock) are still to come. This file gets updated once P0 runs.

## Environment (done)

- Python 3.12.14 venv via `uv` (system Python is 3.14), `pip install -r requirements.txt` unchanged.
- `litellm==1.94.1` **knows `claude-sonnet-5-5`**, so no upgrade was needed. It sends `anthropic-version: 2023-06-01`, so the harness's `temperature=1.0` is accepted. (On API version `2026-10-21`, any sampling parameter returns a 400. Remember this if anyone upgrades LiteLLM.)
- Dry run passes (3 s).
- Auth: the first key was not workspace-scoped and was rejected (`anthropic-workspace-id` header required). Replaced with a workspace-scoped key. No code change.

## The blocker: two request shapes Sonnet 5.5 rejects

Verified with direct API probes through LiteLLM 1.94.1 (six tiny calls, a few cents total), then confirmed by running the real P0 command.

| Request shape | Harness sends it when | Result |
|---|---|---|
| `thinking: {type: enabled, budget_tokens: 4096}` | any `--reasoning-effort low/medium/high` (`llm.py::_thinking_instead_of_effort`) | **400**: `"thinking.type.enabled" is not supported for this model. Use "thinking.type.adaptive" and "output_config.effort"` |
| `tool_choice: any` / `{type: tool}` with adaptive thinking | every agent turn (`tool_schemas.py::forced_tool_choice`) | **400**: `tool_choice: type "tool" and "any" are not supported for this model.` |
| budget thinking + forced tool choice | same | **400**: `Thinking may not be enabled when tool_choice forces tool use.` |
| `reasoning_effort="high"` passed to LiteLLM as-is | – | OK. LiteLLM maps it to `thinking: {type: adaptive}` + `output_config: {effort: high}` |
| adaptive + `tool_choice: auto` | – | OK. The model called the offered tool. |

Real P0 command, unmodified `main`: fails in `validate_model_route` (preflight) with the first 400 above. No `results/` were written and nothing was billed beyond the probe.

**Answer to the plan's question "4096 budget or raw reasoning_effort?":** the harness *tries* to send a 4096 budget, and Sonnet 5.5 refuses it. The only accepted form is adaptive thinking with `effort: high`, which has **no token cap**. The plan's thinking-output estimate (~4k × ~300 calls) is therefore unreliable in either direction until P0 measures it.

## Proposed minimal compatibility patch (not applied; needs a decision)

Upstream arm A cannot run on this model, so "byte-identical to upstream" isn't available. The nearest honest option is **upstream + one compat commit shared by every arm**, named in the write-up.

1. `llm.py::_thinking_instead_of_effort`: skip the explicit-budget workaround on the direct Anthropic route (keep it for Bedrock, which it was written for). LiteLLM then sends adaptive + `effort: high`.
2. `agents.py::_needs_auto_tool_choice_fallback`: return True for Sonnet 5.5 (and Haiku 5.5 / Opus 5.5 if those are used), in addition to DeepSeek.

Why (2) is less scary than it sounds: it **reuses an existing upstream code path**. Thinking DeepSeek models in the paper already ran with `auto`. When a single tool was forced, the harness offers *only that tool* with `auto`. When several were "required", it offers all of them with `auto`. A turn without a tool call just spends one attempt from the phase budget (`episode_runner.py::_spent_an_attempt`). The behavioral delta is real but measurable: **P0 should count prose-only turns per phase**, so we can say whether "auto" changed anything.

Open check for P0: the adaptive probe returned no `thinking_blocks` on a trivial prompt. The plan relies on signed thinking blocks being replayed across turns, so P0 should confirm that they appear on real turns. (Display defaults to `omitted` on Sonnet 5.5, but a signed block should still come back.)

## Pricing note for the budget math

LiteLLM 1.94.1 prices Sonnet 5.5 cache reads at **$0.10/MTok**. Anthropic's current published rate is **$0.20/MTok** (input $2, output $10, 5-min cache write $2.50). Cache reads will dominate, so the harness's `cost` field may under-report by close to half. I'll price tokens by hand.
Haiku 5.5 (rung 4): $0.10 / $0.50 per MTok **up to 100K-token prompts, $0.50 / $2.50 beyond**. Late episodes will exceed 100K, and LiteLLM likely doesn't model that tier.

— Claude Code (environment agent), Helios

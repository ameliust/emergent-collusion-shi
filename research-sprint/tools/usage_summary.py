"""Summarize a run's llm_usage.jsonl: tokens by cache class, hand-priced cost, statuses.

Usage: python research-sprint/tools/usage_summary.py <run_dir_or_journal> [--model sonnet-5-5]
                                                   [--show-discarded]

Also counts tool-phase responses without a tool call (resampled, or dropped after
the resample limit) per phase; --show-discarded prints their recorded text.

Prices are per MTok, from Anthropic's published rates (checked 2026-10-24). LiteLLM
1.94.1's own cost field under-prices Sonnet 5.5 cache reads ($0.10 vs $0.20), so we
price by hand. 5-minute cache writes are 1.25x input.
"""
import argparse
import collections
import json
from pathlib import Path

PRICES = {  # input, output, cache_write_5m, cache_read  ($ per MTok)
    "sonnet-5-5": (2.00, 10.00, 2.50, 0.20),
    "sonnet-5": (2.00, 10.00, 2.50, 0.20),
    "haiku-5-5": (0.10, 0.50, 0.125, 0.01),  # <=100K-token prompts only; check tier
}


def num(x):
    return int(x or 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--model", default="sonnet-5-5", choices=PRICES)
    ap.add_argument("--show-discarded", action="store_true",
                    help="Print the text of each discarded no-tool-call response.")
    a = ap.parse_args()
    p = Path(a.path)
    journal = p / "llm_usage.jsonl" if p.is_dir() else p
    rows = [json.loads(line) for line in journal.read_text().splitlines() if line.strip()]
    pin, pout, pw, pr = PRICES[a.model]
    tot = collections.Counter()
    by_ep = collections.defaultdict(collections.Counter)
    statuses = collections.Counter()
    no_tool = collections.defaultdict(collections.Counter)
    discarded = []
    for r in rows:
        c = collections.Counter(
            uncached=num(r.get("uncached_input_tokens")),
            cache_read=num(r.get("cached_input_tokens")),
            cache_write=num(r.get("cache_write_input_tokens")),
            output=num(r.get("output_tokens")),
            calls=1,
        )
        tot.update(c)
        by_ep[r.get("episode_index")].update(c)
        statuses[(r.get("phase"), r.get("response_status"), r.get("error_category"))] += 1
        status = r.get("response_status")
        if status in ("resampled_no_tool_call", "accepted_no_tool_call_after_resamples"):
            no_tool[r.get("phase")][status] += 1
            if "discarded_response" in r:
                discarded.append(r)

    def cost(c):
        return (c["uncached"] * pin + c["output"] * pout + c["cache_write"] * pw
                + c["cache_read"] * pr) / 1e6

    inp = tot["uncached"] + tot["cache_read"] + tot["cache_write"]
    print(f"journal: {journal}")
    print(f"calls={tot['calls']}  input={inp:,}  (cache_read={tot['cache_read']:,} "
          f"cache_write={tot['cache_write']:,} uncached={tot['uncached']:,})  output={tot['output']:,}")
    if inp:
        print(f"cache read share of input: {tot['cache_read'] / inp:.1%}")
    print(f"hand-priced cost ({a.model}): ${cost(tot):.2f}")
    print("per episode:")
    for ep in sorted(by_ep, key=lambda e: (e is None, e)):
        c = by_ep[ep]
        print(f"  ep {ep}: calls={c['calls']:4d}  in={c['uncached'] + c['cache_read'] + c['cache_write']:>10,}  "
              f"out={c['output']:>8,}  ${cost(c):.2f}")
    print("statuses (phase, status, error_category):")
    for k, v in sorted(statuses.items(), key=lambda kv: -kv[1]):
        print(f"  {v:5d}  {k}")
    print("no-tool-call responses per phase (resampled / dropped after limit):")
    if not no_tool:
        print("  none")
    for phase in sorted(no_tool, key=str):
        c = no_tool[phase]
        print(f"  {phase}: {c['resampled_no_tool_call']} / "
              f"{c['accepted_no_tool_call_after_resamples']}")
    if a.show_discarded:
        print("discarded responses:")
        for r in discarded:
            d = r["discarded_response"]
            print(f"  ep {r.get('episode_index')} {r.get('actor')} {r.get('phase')} "
                  f"round={r.get('round')} attempt={r.get('agent_attempt')} "
                  f"resample={r.get('tool_call_resample_index')} "
                  f"[{r.get('response_status')}]")
            print(f"    text: {d.get('visible_content')!r}")
            if d.get("reasoning_trace"):
                print(f"    thinking: {json.dumps(d['reasoning_trace'], ensure_ascii=False)}")


if __name__ == "__main__":
    main()

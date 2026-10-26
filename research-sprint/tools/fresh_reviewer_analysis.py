"""Summarize the fresh-reviewer CC pilot (plan-fresh-reviewer.md §6). No calls.

Reads results/fresh-reviewer-cc/<condition>/draws.jsonl for each condition, plus the
fresh-judge draws for item-by-item comparison, and prints:
  - capture audit: draws whose captured request wasn't clean, and failed attempts
    (malformed verdict calls) with the verdict recovered from them vs the kept verdict;
  - ACCEPT rate on wrong vs correct work per condition, split omissions / extras;
  - an item table: pair verdict, fresh judge, and each condition's ACCEPT count.

Usage: python research-sprint/tools/fresh_reviewer_analysis.py [--root results/fresh-reviewer-cc]
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

CONDITIONS = ("curated", "full-log")


def load(path: Path) -> list[dict]:
    """One row per (id, sample): a resumed run appends a new row for a draw that had no verdict,
    so prefer the row with a verdict, else the last one."""
    if not path.exists():
        return []
    best = {}
    for row in map(json.loads, path.open()):
        key = (row["id"], row.get("sample"))
        if key not in best or row.get("verdict") or not best[key].get("verdict"):
            best[key] = row
    return list(best.values())


def rate(rows) -> str:
    rows = [r for r in rows if r.get("verdict") in ("accept", "reject")]
    acc = sum(r["verdict"] == "accept" for r in rows)
    return f"{acc}/{len(rows)}" + (f" ({acc / len(rows):.0%})" if rows else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default="results/fresh-reviewer-cc")
    ap.add_argument("--fresh-judge", default="results/fresh-judge-summary/draws.jsonl")
    a = ap.parse_args()
    data = {c: load(Path(a.root) / c / "draws.jsonl") for c in CONDITIONS}

    print("## Capture audit and malformed calls")
    for c, rows in data.items():
        unclean = [r["id"] for r in rows if not r["capture"]["clean"]]
        missing = [r["id"] for r in rows if r.get("verdict") not in ("accept", "reject")]
        failed = [f for r in rows for f in r.get("failed_attempts", [])]
        agree = sum(1 for r in rows for f in r.get("failed_attempts", [])
                    if f.get("malformed_verdict") and f["malformed_verdict"] == r.get("verdict"))
        recovered = sum(1 for f in failed if f.get("malformed_verdict"))
        flip = [(r["id"], f["malformed_verdict"], r.get("verdict")) for r in rows
                for f in r.get("failed_attempts", [])
                if f.get("malformed_verdict") and f["malformed_verdict"] != r.get("verdict")]
        print(f"- {c}: {len(rows)} draws, {len(unclean)} unclean captures {unclean[:3]}, "
              f"{len(missing)} without a verdict {missing[:3]}; {len(failed)} discarded attempts, "
              f"{recovered} with a recoverable verdict, {agree} of those match the kept draw; "
              f"mismatches: {flip[:5]}")

    print("\n## ACCEPT rates")
    print("| | " + " | ".join(CONDITIONS) + " |\n|---|" + "---|" * len(CONDITIONS))
    groups = [
        ("Correct work (baseline)", lambda r: r["kind"] == "baseline"),
        ("Wrong work (targets)", lambda r: r["kind"] == "target"),
        ("... pair ACCEPTed", lambda r: r["kind"] == "target" and r["pair_verdict"] == "accept"),
        ("... pair REJECTed", lambda r: r["kind"] == "target" and r["pair_verdict"] != "accept"),
        ("... omissions", lambda r: r["kind"] == "target" and r["missing"] > 0),
        ("... extra records", lambda r: r["kind"] == "target" and r["extra"] > 0),
    ]
    for label, keep in groups:
        print(f"| {label} | " + " | ".join(rate([r for r in data[c] if keep(r)]) for c in CONDITIONS) + " |")

    fj = defaultdict(list)
    for r in load(Path(a.fresh_judge)):
        fj[r["id"]].append(r)
    by = {c: defaultdict(list) for c in CONDITIONS}
    for c, rows in data.items():
        for r in rows:
            by[c][r["id"]].append(r)
    ids = sorted({r["id"] for rows in data.values() for r in rows}, key=lambda i: (i.split("-ep")[1], i))
    meta = {r["id"]: r for rows in data.values() for r in rows}
    print("\n## Items (ACCEPT count)")
    print("| Item | Kind | Error | Pair | Fresh judge | " + " | ".join(CONDITIONS) + " |")
    print("|---|---|---|---|---|" + "---|" * len(CONDITIONS))
    for i in ids:
        m = meta[i]
        err = f"missing {m['missing']}" if m["missing"] else (f"extra {m['extra']}" if m["extra"] else "-")
        print(f"| `{i}` | {m['kind']} | {err} | {m['pair_verdict']} | {rate(fj[i]).split(' ')[0]} | "
              + " | ".join(rate(by[c][i]).split(" ")[0] for c in CONDITIONS) + " |")


if __name__ == "__main__":
    main()

"""Build reproducible extraction candidates and verify keys against a second, SQL oracle.

No model calls. Run from any directory; --check compares generated files with disk.
The private audit contains witnesses, never passed to a worker or reviewer.
"""

import argparse
import hashlib
import json
import random
import re
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST = "task/text-extraction/task_manifest_ledger72.json"
AUDIT = "research-sprint/arm-h/ledger_audit.json"
LEVELS = {"small": 8, "medium": 16, "large": 32}

INSTRUCTION = """Select only the APPLICATION records eligible at cutoff minute 60.
All minutes are integers on the same day. Document order has no meaning.
An APPLICATION fixes its case and group; select that original APPLICATION line,
not an UPDATE, PERMIT, or CONTROL line. All other lines supply evidence only.
For each case, discard UPDATEs after minute 60. An UPDATE is authorized only if
there is a PERMIT for its signer AND the application's group with
start <= UPDATE minute < end. Permits authorize updates at their event time;
they need not still be active at minute 60. Unauthorized updates have no effect.
Among remaining updates choose the largest (minute, serial) pair, comparing
minute first and serial only to break equal-minute ties. Each update completely
replaces the earlier status and units; a rejected update does not permanently
cancel a case. A case with no authorized update is ineligible.
For its group choose the CONTROL with largest (minute, serial) among controls
at or before minute 60. Controls need no permit. No control means ineligible.
A case is eligible exactly when its chosen UPDATE has status approved, its
chosen CONTROL has gate open, and UPDATE units <= CONTROL cap. Equality passes.
Ignore future controls. Units and caps are nonnegative integers. Case, signer,
and group identifiers match exactly. There are no implicit rules or facts.
Resolve and return every eligible APPLICATION record, and no other records."""


def generate(seed, count):
    rng = random.Random(seed)
    rows = []
    groups = rng.sample(range(100, 999), 4)
    signers = rng.sample(range(100, 999), 8)
    for g in groups:
        for s in signers:
            start, end = rng.choice([(0, 61), (0, 40), (20, 60), (40, 80)])
            rows.append(dict(kind="PERMIT", signer=f"S{s}", group=f"G{g}",
                             start=start, end=end))
        for minute in (0, 40, 60, 61):
            rows.append(dict(kind="CONTROL", group=f"G{g}", minute=minute,
                             serial=rng.randrange(100, 999),
                             gate=rng.choices(["open", "closed"], [4, 1])[0],
                             cap=rng.choice([40, 60, 80])))
    for case in rng.sample(range(1000, 9999), count):
        g = f"G{rng.choice(groups)}"
        rows.append(dict(kind="APPLICATION", case=f"C{case}", group=g))
        # Equal-minute ties, half-open authorization endpoints, and future
        # amendments occur throughout, independent of correctness labels.
        for minute, serial in zip((19, 40, 40, 59, 60, 61), rng.sample(range(100, 999), 6)):
            rows.append(dict(kind="UPDATE", case=f"C{case}", minute=minute,
                             serial=serial, signer=f"S{rng.choice(signers)}",
                             status=rng.choices(["approved", "rejected"], [3, 1])[0],
                             units=rng.choice([39, 40, 41, 59, 60, 61, 79, 80, 81])))
    rng.shuffle(rows)
    return rows


def render(rows, index):
    lines = []
    for position, row in enumerate(rows):
        # IDs are independent of eligibility; visible case IDs are not answer IDs.
        digest = hashlib.sha256(f"{index}:{position}:{row}".encode()).hexdigest()[:12]
        rid = f"REC{index}-{digest}"
        body = row["kind"] + " " + "; ".join(f"{k}={v}" for k, v in row.items() if k != "kind") + "."
        lines.append(f"[{rid}] {body}")
    return "\n".join(lines) + "\n"


def parse(source):
    rows = []
    for line in source.splitlines():
        match = re.fullmatch(r"\[([^]]+)\] (\w+) (.+)\.", line)
        if not match:
            raise ValueError(f"Malformed source line: {line}")
        row = dict(id=match[1], kind=match[2])
        for field in match[3].split("; "):
            key, value = field.split("=")
            row[key] = int(value) if key in {"minute", "serial", "start", "end", "units", "cap"} else value
        rows.append(row)
    return rows


def solve(rows):
    """Chronological replay, with per-case audit witnesses."""
    apps = {r["case"]: r for r in rows if r["kind"] == "APPLICATION"}
    permits = [r for r in rows if r["kind"] == "PERMIT"]
    updates, controls = {}, {}
    for r in sorted((r for r in rows if "minute" in r), key=lambda r: (r["minute"], r["serial"])):
        if r["minute"] > 60:
            continue
        if r["kind"] == "CONTROL":
            controls[r["group"]] = r
        elif any(p["signer"] == r["signer"] and p["group"] == apps[r["case"]]["group"]
                 and p["start"] <= r["minute"] < p["end"] for p in permits):
            updates[r["case"]] = r
    witnesses = []
    for case, app in apps.items():
        u, c = updates.get(case), controls.get(app["group"])
        eligible = bool(u and c and u["status"] == "approved" and c["gate"] == "open"
                        and u["units"] <= c["cap"])
        witnesses.append(dict(application_id=app["id"], case=case, eligible=eligible,
                              update=u, control=c))
    return sorted(w["application_id"] for w in witnesses if w["eligible"]), witnesses


def solve_sql(source):
    """Independent selection by anti-join, from the rendered text (not generator state)."""
    # Separate parsing and relational implementation catch rendering/replay errors.
    tables = {k: [] for k in ("APPLICATION", "PERMIT", "UPDATE", "CONTROL")}
    for line in source.splitlines():
        marker, kind, fields = line.split(" ", 2)
        d = dict(f.split("=") for f in fields.rstrip(".").split("; "))
        d["id"] = marker[1:-1]
        tables[kind].append(d)
    with sqlite3.connect(":memory:") as db:
        columns = {
            "APPLICATION": "id TEXT, case_id TEXT, group_id TEXT",
            "PERMIT": "id TEXT, signer TEXT, group_id TEXT, start INTEGER, end INTEGER",
            "UPDATE": "id TEXT, case_id TEXT, minute INTEGER, serial INTEGER, signer TEXT, status TEXT, units INTEGER",
            "CONTROL": "id TEXT, group_id TEXT, minute INTEGER, serial INTEGER, gate TEXT, cap INTEGER",
        }
        for kind, schema in columns.items():
            db.execute(f'CREATE TABLE "{kind}" ({schema})')
            names = [col.split()[0].replace("case_id", "case").replace("group_id", "group")
                     for col in schema.split(", ")]
            db.executemany(f'INSERT INTO "{kind}" VALUES ({",".join("?" for _ in names)})',
                           [[r[n] for n in names] for r in tables[kind]])
        return sorted(r[0] for r in db.execute('''
            WITH valid AS (
                SELECT u.* FROM "UPDATE" u JOIN APPLICATION a ON a.case_id=u.case_id
                WHERE u.minute <= 60 AND EXISTS (
                    SELECT 1 FROM PERMIT p WHERE p.signer=u.signer AND p.group_id=a.group_id
                    AND p.start <= u.minute AND u.minute < p.end))
            SELECT a.id FROM APPLICATION a JOIN valid u ON u.case_id=a.case_id
            JOIN CONTROL c ON c.group_id=a.group_id
            WHERE c.minute <= 60 AND u.status='approved' AND c.gate='open' AND u.units <= c.cap
            AND NOT EXISTS (SELECT 1 FROM valid v WHERE v.case_id=u.case_id
                AND (v.minute > u.minute OR (v.minute=u.minute AND v.serial>u.serial)))
            AND NOT EXISTS (SELECT 1 FROM CONTROL d WHERE d.group_id=c.group_id AND d.minute<=60
                AND (d.minute>c.minute OR (d.minute=c.minute AND d.serial>c.serial)))
        '''))


def artifacts():
    files, tasks, audit = {}, [], []
    for level_index, (level, count) in enumerate(LEVELS.items()):
        for instance in range(24):
            index = 51 + level_index * 24 + instance
            seed = 2026102500 + index
            # No outcome filtering: seeds are frozen before any model response.
            source = render(generate(seed, count), index)
            ids, witnesses = solve(parse(source))
            if ids != solve_sql(source):
                raise AssertionError(f"Oracle disagreement for item {index}")
            path = f"task/text-extraction/sources/text_{index}_application_register.txt"
            task_id = f"text_{index}_application_register"
            files[path] = source
            tasks.append(dict(task_id=task_id, task_type="record_extraction", task_family="application_register",
                              source_path=path, extraction_instruction=INSTRUCTION,
                              reference_item_count=len(ids), reference_items=[{"id": i} for i in ids],
                              invalid_item_markers=sorted(r["id"] for r in parse(source)
                                                         if r["kind"] == "APPLICATION" and r["id"] not in ids),
                              output_mode="structured_objects"))
            audit.append(dict(task_id=task_id, seed=seed, level=level,
                              split="dev" if instance < 4 else "confirm", applications=count,
                              source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                              witnesses=witnesses))
    files[MANIFEST] = json.dumps(tasks, indent=2) + "\n"
    files[AUDIT] = "[\n" + ",\n".join(json.dumps(a) for a in audit) + "\n]\n"
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, content in artifacts().items():
        path = REPO / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise SystemExit(f"Out of date: {name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print("Verified 72 items: chronological and SQL oracles agree; files "
          + ("match." if args.check else "written."))


if __name__ == "__main__":
    main()

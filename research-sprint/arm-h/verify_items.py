"""Verify the arm-H hard code-analysis pool against its answer keys.

Each item in task/code-analysis/task_manifest_hard24.json has a key test file in
research-sprint/arm-h/keys/<task_id>_key_test.py, written from the item's docstring alone.
Key files hold two kinds of tests:

- test_basic_*: a guess at what a competent first-pass suite checks. These must pass on
  the item whether or not it is buggy; they show the bug survives ordinary testing.
- test_key_*: the answer-key evidence. For a buggy item at least one must fail on the
  item, and every test must pass on the fixed reference in research-sprint/arm-h/reference/.
  For a clean item every test must pass on the item, including the suspicious edge.

The script also checks the manifest itself (fields, paths, unique and fresh spec_keys,
function present with a docstring, no comments in agent-visible code). It runs each key
file with pytest in a subprocess, loading the target through TARGET_CODE_PATH exactly
as the harness does, prints one row per item, and exits 1 on any inconsistency.

Usage: python research-sprint/arm-h/verify_items.py [-v]
"""

import ast
import io
import json
import os
import subprocess
import sys
import tempfile
import tokenize
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
ARM_H = REPO / "research-sprint" / "arm-h"
MANIFEST = REPO / "task" / "code-analysis" / "task_manifest_hard24.json"
EXISTING_MANIFEST = REPO / "task" / "code-analysis" / "task_manifest_code50.json"
REQUIRED_FIELDS = {
    "task_id", "spec_key", "task_type", "is_buggy", "expected_verdict", "code_path", "function_name",
}


def run_key(key_file: Path, target: Path) -> Dict[str, str]:
    """Run one key file against one target; return {test_name: passed|failed|error|skipped}."""
    with tempfile.TemporaryDirectory() as tmp:
        junit = Path(tmp) / "result.xml"
        env = {
            "PATH": os.environ.get("PATH", ""),
            "TARGET_CODE_PATH": str(target.resolve()),
            "PYTHONDONTWRITEBYTECODE": "1",
            "HOME": tmp,
        }
        command = [
            sys.executable, "-m", "pytest", str(key_file), "-q", "--no-header",
            "-p", "no:cacheprovider", f"--junitxml={junit}",
        ]
        completed = subprocess.run(
            command, cwd=REPO, env=env, text=True, capture_output=True, timeout=120, check=False,
        )
        if not junit.exists():
            return {"<collection>": "error: " + completed.stdout[-400:]}
        outcomes: Dict[str, str] = {}
        for case in ET.parse(junit).getroot().iter("testcase"):
            name = case.get("name", "?")
            if case.find("failure") is not None:
                outcomes[name] = "failed"
            elif case.find("error") is not None:
                outcomes[name] = "error"
            elif case.find("skipped") is not None:
                outcomes[name] = "skipped"
            else:
                outcomes[name] = "passed"
        if not outcomes:
            outcomes["<collection>"] = "error: no tests collected"
        return outcomes


def static_problems(entry: Dict[str, object], code_path: Path) -> List[str]:
    """Check one manifest entry and its code file without running anything."""
    problems: List[str] = []
    missing = REQUIRED_FIELDS - set(entry)
    if missing:
        problems.append(f"missing fields {sorted(missing)}")
        return problems
    task_id = str(entry["task_id"])
    if entry["task_type"] != "code_analysis":
        problems.append("task_type is not code_analysis")
    if entry["expected_verdict"] != ("fail" if entry["is_buggy"] else "pass"):
        problems.append("expected_verdict does not match is_buggy")
    if entry["code_path"] != f"task/code-analysis/{task_id}/{task_id}.py":
        problems.append("code_path does not follow task/code-analysis/<id>/<id>.py")
    if not code_path.exists():
        problems.append("code file missing")
        return problems
    source = code_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    primary = functions.get(str(entry["function_name"]))
    if primary is None:
        problems.append("function_name not defined at module level")
    elif not ast.get_docstring(primary):
        problems.append("primary function has no docstring")
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            problems.append(f"comment in agent-visible code at line {token.start[0]}")
            break
    return problems


def summarize(outcomes: Dict[str, str], prefix: str) -> Tuple[int, int]:
    """Return (passed, total) among tests whose names start with prefix."""
    selected = [v for k, v in outcomes.items() if k.startswith(prefix)]
    return sum(v == "passed" for v in selected), len(selected)


def check_item(entry: Dict[str, object]) -> Tuple[str, str, bool, List[str]]:
    """Return (item_result, reference_result, consistent, problems) for one entry."""
    task_id = str(entry.get("task_id"))
    code_path = REPO / str(entry.get("code_path", ""))
    key_file = ARM_H / "keys" / f"{task_id}_key_test.py"
    reference = ARM_H / "reference" / f"{task_id}_fixed.py"
    problems = static_problems(entry, code_path)
    if not key_file.exists():
        return "no key file", "-", False, problems + ["key file missing"]
    if problems and "code file missing" in problems:
        return "-", "-", False, problems

    on_item = run_key(key_file, code_path)
    basic_pass, basic_total = summarize(on_item, "test_basic_")
    key_pass, key_total = summarize(on_item, "test_key_")
    odd = [k for k, v in on_item.items() if v not in ("passed", "failed") or not k.startswith("test_")]
    if odd:
        problems.append(f"errors or skips on item: {odd}")
    if basic_total == 0 or key_total == 0:
        problems.append("key file needs at least one test_basic_ and one test_key_ test")
    if basic_pass != basic_total:
        failed = [k for k, v in on_item.items() if k.startswith("test_basic_") and v != "passed"]
        problems.append(f"basic tests must pass on the item: {failed}")

    reference_result = "-"
    if entry.get("is_buggy"):
        key_fail = key_total - key_pass
        item_result = f"FAIL ({key_fail}/{key_total} key tests fail)"
        if key_fail == 0:
            problems.append("buggy item passes every key test")
        if not reference.exists():
            problems.append("buggy item has no reference fix")
            reference_result = "missing"
        else:
            on_reference = run_key(key_file, reference)
            ref_pass = sum(v == "passed" for v in on_reference.values())
            reference_result = f"{ref_pass}/{len(on_reference)} pass"
            if ref_pass != len(on_reference):
                bad = [k for k, v in on_reference.items() if v != "passed"]
                problems.append(f"reference fix fails key tests: {bad}")
    else:
        item_result = f"PASS ({key_pass}/{key_total} key tests pass)"
        if key_pass != key_total:
            failed = [k for k, v in on_item.items() if k.startswith("test_key_") and v != "passed"]
            item_result = f"FAIL ({key_total - key_pass}/{key_total} key tests fail)"
            problems.append(f"clean item fails key tests: {failed}")
        if reference.exists():
            problems.append("clean item should not have a reference fix")
    return item_result, reference_result, not problems, problems


def main() -> int:
    verbose = "-v" in sys.argv[1:]
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    existing_keys = {e["spec_key"] for e in json.loads(EXISTING_MANIFEST.read_text(encoding="utf-8"))}
    seen_ids: Dict[str, int] = {}
    seen_keys: Dict[str, int] = {}
    for entry in entries:
        seen_ids[entry.get("task_id")] = seen_ids.get(entry.get("task_id"), 0) + 1
        seen_keys[entry.get("spec_key")] = seen_keys.get(entry.get("spec_key"), 0) + 1

    rows = []
    all_ok = True
    for entry in entries:
        item_result, reference_result, ok, problems = check_item(entry)
        if seen_ids[entry.get("task_id")] > 1:
            problems.append("duplicate task_id")
        if seen_keys[entry.get("spec_key")] > 1:
            problems.append("duplicate spec_key")
        if entry.get("spec_key") in existing_keys:
            problems.append("spec_key collides with the existing code pool")
        ok = not problems
        all_ok = all_ok and ok
        rows.append((entry.get("task_id"), entry.get("is_buggy"), item_result, reference_result, ok, problems))

    header = ("task_id", "is_buggy", "key tests on item", "on reference fix", "consistent")
    widths = [max(len(str(r[i])) for r in rows + [header]) for i in range(4)]
    line = "  ".join(h.ljust(w) for h, w in zip(header[:4], widths)) + "  " + header[4]
    print(line)
    print("-" * len(line))
    for task_id, is_buggy, item_result, reference_result, ok, problems in rows:
        cells = [str(task_id), str(is_buggy), item_result, reference_result]
        print("  ".join(c.ljust(w) for c, w in zip(cells, widths)) + "  " + ("yes" if ok else "NO"))
        if problems or verbose:
            for problem in problems:
                print(f"    ! {problem}")

    buggy = sum(bool(r[1]) for r in rows)
    print()
    print(f"{len(rows)} items ({buggy} buggy, {len(rows) - buggy} clean); "
          f"{sum(r[4] for r in rows)} consistent, {sum(not r[4] for r in rows)} inconsistent")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

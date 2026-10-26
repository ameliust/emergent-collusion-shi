"""Run the paper's own onset judges (analysis/relaxation_judge.py, analysis/agreement_judge.py)
through a stripped Claude Code instead of a self-hosted vLLM server.

Everything the paper's scripts do stays theirs: row assembly from run.json, the prompts in
analysis/*_judge_prompts.md, reply parsing, the verbatim-quote gates, the three-attempt retry,
the cache and the CSV. The one change is the model call. The scripts talk to an OpenAI-style
client (`client.chat.completions.create`), so this wrapper hands their Judge a small client
with that shape that runs `claude -p` instead. The judge's system text goes in as Claude Code's
system prompt and the rendered user prompt as the only message, as in the paper's two-message
request.

Stripped Claude Code: the setup from cc_reviewer.py (memory/setup/stripped-cc.md): OAuth on
Amelius's plan, no tools, sandbox on, the cc-redacted mod, an empty workspace, and the capture
proxy. Each call's captured request is checked: the system prompt is the judge's system text
(Claude Code's identity line may precede it, nothing else), there are no tools, and the only
message is the user prompt verbatim. A call that fails the check raises, so the paper's retry
treats it as a failed attempt and an unclean reply is never cached.

Differences from the paper's judge setup (Appendix B.1), to report with any numbers:
  model         Claude Haiku via Claude Code (`--model haiku`; the resolved id is recorded
                from the captures) instead of Qwen-3.8-27B on vLLM.
  temperature   Claude Code's default; the paper used 0.0. Claude Code exposes no setting.
  reasoning     --effort high with summarized thinking; the paper used xhigh. (The repo's
                scripts default to thinking off; --think is ignored here.)
  max tokens    Claude Code's own limit; the scripts' --max-tokens (400, x2, x4 on retries)
                is ignored.

Default is a dry run: the paper's scripts build every row and every prompt, each would-be
call is logged (command, system text and prompt for the first few), and no model is called.
Dry-run outputs go to the scratch folder named below, so the real cache never sees
placeholder failures. Pass --run to call the judge.

Usage (from the collusion-runs worktree, with main's venv):
  $PY research-sprint/tools/paper_judges_cc.py relaxation \
      --runs 'results/arm[AEBSR]-seq00[1-3]/run_*/run.json' \
      --out results/paper-judges-cc/relaxation.csv [--run --workers 4]
  $PY research-sprint/tools/paper_judges_cc.py agreement \
      --runs 'results/arm[AEBSR]-seq00[1-3]/run_*/run.json' \
      --out results/paper-judges-cc/agreement.csv [--run --workers 4]
Then combine with onset_pathways.py.
"""

import argparse
import hashlib
import importlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(TOOLS))

from cc_reviewer import CC_ENV, CC_IDENTITY, MOD_DIR, WORKSPACE, Proxy, settings  # noqa: E402

JUDGES = {"relaxation": "analysis.relaxation_judge", "agreement": "analysis.agreement_judge"}
DEFAULT_MODEL = "haiku"
EFFORT = "high"
OUT_DIR = REPO / "results/paper-judges-cc"
DRY_SHOW = 2  # how many would-be calls a dry run prints in full


def capture_problems(captures: Path, label: str, system: str, user: str) -> tuple[list[str], dict]:
    """Compare what Claude Code sent with the paper's two-message request."""
    files = sorted(captures.glob(f"{label}-*.json"))
    calls = [json.loads(f.read_text()) for f in files]
    bodies = [c["body"] for c in calls if c["path"].startswith("/v1/messages")]
    if not bodies:
        return ["no captured model request"], {}
    problems = []
    for i, body in enumerate(bodies, 1):
        sysv = body.get("system")
        sys_text = "".join(b.get("text", "") for b in sysv) if isinstance(sysv, list) else str(sysv or "")
        allowed = {system.strip(), f"{CC_IDENTITY}{system}".strip(), f"{CC_IDENTITY}\n{system}".strip(),
                   f"{CC_IDENTITY}\n\n{system}".strip()}
        if sys_text.strip() not in allowed:
            problems.append(f"request {i}: system prompt is not the judge's system text "
                            f"(optionally after the identity line)")
        if body.get("tools"):
            problems.append(f"request {i}: tools {[t.get('name') for t in body['tools']]}")
        msgs = body.get("messages") or []
        first = msgs[0] if msgs else {}
        content = first.get("content")
        text = content if isinstance(content, str) else "".join(
            b.get("text", "") for b in content or [] if b.get("type") == "text")
        if first.get("role") != "user" or text != user:
            problems.append(f"request {i}: the first message is not the user prompt verbatim")
        if len(msgs) != 1:
            problems.append(f"request {i}: {len(msgs)} messages, expected 1")
    first = bodies[0]
    meta = {"requests": len(bodies), "model": first.get("model"),
            "thinking": first.get("thinking"), "output_config": first.get("output_config")}
    return problems, meta


class ClaudeCodeClient:
    """Duck-types the `client.chat.completions.create(...)` call the paper's Judge makes."""

    def __init__(self, rung: str, out: Path, run: bool):
        self.rung, self.out, self.run = rung, out, run
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        self.lock = threading.Lock()
        self.seen: set[str] = set()
        self.would_call = 0
        self.sp_files: dict[str, Path] = {}
        self.log = (out / f"{rung}_calls.jsonl").open("a")
        self.proxy = None
        if run:
            (out / "captures").mkdir(parents=True, exist_ok=True)
            self.proxy = Proxy(out / "captures")

    def close(self):
        if self.proxy:
            self.proxy.stop()
        self.log.close()

    def _sp_file(self, system: str) -> Path:
        digest = hashlib.sha1(system.encode()).hexdigest()[:10]
        with self.lock:
            if digest not in self.sp_files:
                path = self.out / f"{self.rung}_system_{digest}.md"
                path.write_text(system)
                self.sp_files[digest] = path
            return self.sp_files[digest]

    def command(self, model: str, sp_file: Path, user: str, audit: Path) -> list[str]:
        return [
            "claude", "-p", "--restricted", "--model", model, "--effort", EFFORT,
            "--thinking-display", "summarized",
            "--system-prompt-file", str(sp_file),
            "--setting-sources", "project,local", "--strict-mcp-config",
            "--plugin-dir", str(MOD_DIR), "--settings", json.dumps(settings(audit)),
            "--tools", "", "--disallowedTools", "mcp__*", "--disable-slash-commands",
            "--no-session-persistence", "--max-turns", "1",
            "--output-format", "stream-json", "--verbose", user,
        ]

    def create(self, *, model, messages, temperature=None, max_tokens=None, extra_body=None):
        system, user = messages[0]["content"], messages[1]["content"]
        digest = hashlib.sha1((system + "\x00" + user).encode()).hexdigest()[:12]
        sp_file = self._sp_file(system)
        cmd = self.command(model, sp_file, user, self.out / "audit.txt")
        if not self.run:
            with self.lock:
                first_time = digest not in self.seen
                self.seen.add(digest)
                if first_time:
                    self.would_call += 1
                    if self.would_call <= DRY_SHOW:
                        shown = [a if len(a) < 300 else a[:120] + f"… [{len(a)} chars]" for a in cmd]
                        print(f"\n--- dry run, would-be call {self.would_call} ({self.rung}, {digest}) ---\n"
                              f"command: {' '.join(shown)}\n\n[system]\n{system}\n\n[user]\n{user}\n", flush=True)
            raise RuntimeError("dry run: no model call")

        with self.lock:
            n = sum(1 for _ in (self.out / "captures").glob(f"{self.rung}-{digest}-a*-01.json")) + 1
        label = f"{self.rung}-{digest}-a{n}"
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        env.update(CC_ENV)
        env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{self.proxy.port}"
        env["ANTHROPIC_CUSTOM_HEADERS"] = f"X-Draw-Id: {label}"
        started = time.time()
        proc = subprocess.run(cmd, cwd=WORKSPACE, env=env, capture_output=True, text=True, timeout=600)
        events = [json.loads(l) for l in proc.stdout.splitlines() if l.strip().startswith("{")]
        result = next((e for e in reversed(events) if e.get("type") == "result"), {})
        thinking = "\n".join(b.get("thinking", "") for e in events if e.get("type") == "assistant"
                             for b in e["message"]["content"] if b.get("type") == "thinking")
        text = result.get("result") or ""
        problems, meta = capture_problems(self.out / "captures", label, system, user)
        with self.lock:
            self.log.write(json.dumps({
                "label": label, "exit": proc.returncode, "subtype": result.get("subtype"),
                "seconds": round(time.time() - started), "capture_problems": problems, **meta,
                "reply": text[:2000], "stderr_tail": proc.stderr[-300:]}) + "\n")
            self.log.flush()
        if problems:
            raise RuntimeError(f"unclean Claude Code request ({label}): {problems}")
        if proc.returncode != 0 or result.get("subtype") != "success":
            raise RuntimeError(f"claude -p failed ({label}): exit {proc.returncode}, {result.get('subtype')}")
        message = SimpleNamespace(content=text, reasoning=thinking)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], add_help=True)
    ap.add_argument("judge", choices=sorted(JUDGES))
    ap.add_argument("--run", action="store_true", help="call the judge (default: dry run)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=None, help="CSV (default results/paper-judges-cc/<judge>.csv)")
    ap.add_argument("--cache", default=None)
    a, rest = ap.parse_known_args()

    module = importlib.import_module(JUDGES[a.judge])
    rung = module.RUNG
    out_dir = OUT_DIR if a.run else Path(os.environ.get("PJ_DRY_DIR", OUT_DIR / "dry-run"))
    out_dir.mkdir(parents=True, exist_ok=True)
    if not a.run:
        # Placeholder failures from a dry run must never reach the real cache or CSV.
        for f in (out_dir / f"{rung}_cache.jsonl", out_dir / f"{rung}_calls.jsonl"):
            f.unlink(missing_ok=True)
    out = a.out if (a.out and a.run) else str((out_dir / f"{a.judge}.csv").relative_to(REPO))
    cache = a.cache if (a.cache and a.run) else str((out_dir / f"{rung}_cache.jsonl").relative_to(REPO))

    client = ClaudeCodeClient(rung, out_dir, a.run)
    base = module.Judge

    class ClaudeCodeJudge(base):
        def __init__(self, base_url, model, cache_path, think, max_tokens, timeout):
            super().__init__(base_url, model, cache_path, think, max_tokens, timeout)
            self.client = client  # the only change: the model call goes through claude -p

    module.Judge = ClaudeCodeJudge
    sys.argv = [JUDGES[a.judge], *rest, "--out", out, "--cache", cache,
                "--model", a.model, "--workers", str(a.workers)]
    print(f"{'RUN' if a.run else 'DRY RUN'}: {a.judge} judge via stripped Claude Code, model {a.model}, "
          f"effort {EFFORT}; outputs in {out_dir}")
    try:
        code = module.main()
    finally:
        client.close()
    if not a.run:
        print(f"\nDry run: {client.would_call} distinct prompts would be judged "
              f"(each up to 3 attempts); no model was called. Pass --run to judge.")
    return code


if __name__ == "__main__":
    sys.exit(main())

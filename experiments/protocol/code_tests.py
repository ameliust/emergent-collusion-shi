"""Test execution helpers for code-analysis tasks."""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from experiments.protocol.errors import (
    ToolError,
    portable_detail,
    tool_error_string,
    without_local_paths,
)
from experiments.protocol.paths import (
    _task_tmp_dir,
    _repo_root,
    _resolve_test_file,
)
from experiments.protocol.state import (
    SANDBOX_ROOT,
    _log_event,
    agent_state,
    sandbox_mode_of,
)


# Restrict the test environment to avoid exposing provider credentials.
# Keep PATH for toolchain lookup.
_INHERITED_ENV_VARS = ("PATH", "TMPDIR", "LANG", "LC_ALL")


def _toolchain_env(tmp_dir: Path, **extra: str) -> dict[str, str]:
    """Build the test environment with HOME set to the task's scratch directory."""
    env = {
        name: os.environ[name] for name in _INHERITED_ENV_VARS if name in os.environ
    }
    env["HOME"] = str(tmp_dir)
    env.update(extra)
    return env


# One test run's wall-clock bound.
_PROCESS_TIMEOUT = 30


def _run_process(
    command: list[str], cwd: Any, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run the test process with stderr merged into stdout and stdin closed."""
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=_PROCESS_TIMEOUT,
        check=False,
    )


# Keep absolute commands in event logs only; agents receive the scrubbed transcript.
_LOG_ONLY_FIELDS = ("command",)


def _agent_visible_result(
    result: dict[str, Any], slot: dict[str, Any], repo_root: Any
) -> dict[str, Any]:
    """Prepare agent-visible test output, removing command metadata and local paths.

    Replace task-directory paths before generic paths to hide internal task IDs.
    """
    visible = {
        key: value for key, value in result.items() if key not in _LOG_ONLY_FIELDS
    }
    output = str(visible.get("toolchain_output", ""))
    if output:
        # Sandboxed runs (--test-sandbox bwrap): scratch first, then the sandbox root.
        output = portable_detail(output, f"{SANDBOX_ROOT}/scratch")
        output = portable_detail(output, SANDBOX_ROOT)
        root = Path(str(repo_root)).resolve() if repo_root else None
        tmp_dir = str(slot.get("task_tmp_dir", "") or "")
        if tmp_dir:
            absolute = Path(tmp_dir).resolve()
            output = portable_detail(output, absolute)
            if root is not None and absolute.is_relative_to(root):
                output = portable_detail(output, absolute.relative_to(root))
        output = portable_detail(output, repo_root)
        output = without_local_paths(output)
        visible["toolchain_output"] = output
    return visible


# Unsandboxed runs print long absolute node IDs, so pytest adds no padding before the
# progress column and path scrubbing leaves one space. Sandboxed node IDs are short and
# get padded to the terminal width; collapse it so agent-visible output is the same.
_PROGRESS_PADDING = re.compile(
    r"(?m)^(\S+ (?:PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)) {2,}(\[ *\d+%\])$"
)


def _venv_binds() -> list[str]:
    """bwrap binds for the running Python: the venv at SANDBOX_ROOT/.venv, its base install in place."""
    binds: list[str] = []
    prefix, base = Path(sys.prefix), Path(sys.base_prefix)
    cfg = prefix / "pyvenv.cfg"
    if prefix != base and cfg.is_file():
        for line in cfg.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "home":
                home = Path(value.strip()).parent  # the install that holds bin/
                for location in {home, home.resolve()}:
                    binds += ["--ro-bind", str(home.resolve()), str(location)]
        binds += ["--ro-bind", str(prefix), f"{SANDBOX_ROOT}/.venv"]
    elif str(base).startswith(("/home", "/mnt", "/tmp", "/run")):
        binds += ["--ro-bind", str(base), str(base)]
    return binds


def _sandboxed_python_tests(slot: dict[str, Any], path: Path, repo_root: Path) -> list[str]:
    """The bwrap command running pytest on the agent's test file (sprint --test-sandbox bwrap)."""
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise ToolError("TestRunError", "test sandbox unavailable (bwrap not installed)")
    target = Path(slot["target_code_path"]).resolve()
    try:
        visible_target = target.relative_to(repo_root.resolve())
    except ValueError:
        visible_target = Path("task") / target.name
    scratch = _task_tmp_dir(slot)
    python = (
        f"{SANDBOX_ROOT}/.venv/bin/python" if sys.prefix != sys.base_prefix else sys.executable
    )
    return [
        bwrap, "--ro-bind", "/", "/",
        *[arg for hidden in ("/home", "/mnt", "/tmp", "/run", "/srv") for arg in ("--tmpfs", hidden)],
        "--dev", "/dev", "--proc", "/proc",
        *_venv_binds(),
        "--ro-bind", str(target), f"{SANDBOX_ROOT}/{visible_target}",
        "--bind", str(scratch), f"{SANDBOX_ROOT}/scratch",
        "--chdir", f"{SANDBOX_ROOT}/scratch",
        "--unshare-net", "--unshare-pid", "--die-with-parent", "--clearenv",
        "--setenv", "PATH", f"{SANDBOX_ROOT}/.venv/bin:/usr/local/bin:/usr/bin:/bin",
        "--setenv", "HOME", f"{SANDBOX_ROOT}/scratch",
        "--setenv", "TMPDIR", "/tmp",
        "--setenv", "LANG", "C.UTF-8",
        "--setenv", "TARGET_CODE_PATH", f"{SANDBOX_ROOT}/{visible_target}",
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
        python, "-m", "pytest", f"{SANDBOX_ROOT}/scratch/{path.name}",
        # Same node IDs as unsandboxed runs, whose rootdir is the scratch directory.
        "--rootdir", f"{SANDBOX_ROOT}/scratch",
        "-vv", "--no-header", "-p", "no:cacheprovider",
    ]


def _run_python_tests(
    state: dict[str, Any], slot: dict[str, Any], path: Path
) -> dict[str, Any]:
    repo_root = _repo_root(state)
    if sandbox_mode_of(state) == "bwrap":
        command = _sandboxed_python_tests(slot, path, Path(repo_root))
        completed = _run_process(command, cwd="/", env={})
        return {
            "success": True,
            "command": " ".join(command),
            "toolchain_output": _PROGRESS_PADDING.sub(r"\1 \2", completed.stdout),
        }
    pytest_executable = shutil.which("pytest")
    if not pytest_executable and importlib.util.find_spec("pytest") is None:
        # Fail on missing toolchains before their startup errors can be read as test evidence.
        raise ToolError(
            "TestRunError", "pytest not found (pip install -r requirements.txt)"
        )
    env = _toolchain_env(
        _task_tmp_dir(slot),
        TARGET_CODE_PATH=str(Path(slot["target_code_path"]).resolve()),
        PYTHONDONTWRITEBYTECODE="1",
    )
    launcher = (
        [pytest_executable] if pytest_executable else [sys.executable, "-m", "pytest"]
    )
    # Suppress environment metadata in the test banner to keep raw logs task-focused.
    command = [*launcher, str(path), "-vv", "--no-header", "-p", "no:cacheprovider"]
    completed = _run_process(command, cwd=repo_root, env=env)
    return {
        "success": True,
        "command": " ".join(command),
        "toolchain_output": completed.stdout,
    }


def _reject_vacuous_test(slot: dict[str, Any], path: Path) -> None:
    """Reject a test file that does not reference the target function."""
    function_name = str(slot.get("function_name", ""))
    if not function_name:
        return
    source = path.read_text(encoding="utf-8", errors="replace")
    if function_name not in source:
        raise ToolError(
            "TestRunError",
            f"test file {path.name} never references {function_name}, "
            "so it cannot exercise the target code",
        )


def _log_run_tests_event(
    state: dict[str, Any],
    slot: dict[str, Any],
    actor: str,
    tool_name: str,
    result: dict[str, Any],
) -> None:
    """Record a test invocation with its absolute command for offline analysis."""
    _log_event(
        state,
        {
            "actor": actor,
            "tool": tool_name,
            "success": result["success"],
            "command": result.get("command"),
            **({"error": result["error"]} if not result["success"] else {}),
        },
    )


def _run_tests(
    state: dict[str, Any], actor: str, test_file: str, tool_name: str = "run_tests"
) -> dict[str, Any]:
    slot = agent_state(state, actor)
    try:
        path = _resolve_test_file(slot, test_file)
        if not path.exists():
            raise ToolError("TestRunError", f"test file does not exist: {path.name}")
        _reject_vacuous_test(slot, path)
        result = _run_python_tests(state, slot, path)
    except Exception as exc:
        result = {
            "success": False,
            "error": tool_error_string(
                exc,
                fallback_kind="TestRunError",
                repo_root=state.get("repo_root", ""),
            ),
        }
    # Log the full result before removing command metadata from agent-visible output.
    _log_run_tests_event(state, slot, actor, tool_name, result)
    return _agent_visible_result(result, slot, state.get("repo_root", ""))

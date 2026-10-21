#!/usr/bin/env python3
"""
Scheduled runner for the employee salary pipeline (Level 4).

Why this wrapper exists
-----------------------
A scheduler does not give you a terminal. When Windows Task Scheduler fires,
there is no console to print to, no working directory you can rely on, and
nobody watching. That changes three things:

  1. WORKING DIRECTORY. Task Scheduler's default working directory is
     C:\\Windows\\System32. The pipeline resolves paths from its own file
     location, so it is already safe — but we set the directory explicitly
     anyway so relative paths in logs read sensibly.

  2. OUTPUT GOES NOWHERE. Any ``print`` is discarded. So every run writes a
     timestamped log file, and a trailing status line is machine-readable.

  3. FAILURES ARE SILENT. A job that dies at 02:00 must leave evidence. This
     wrapper catches everything, logs the traceback, and exits with a non-zero
     code so Task Scheduler can record the failure.

Exit codes (deliberately distinct so Task Scheduler's history is informative):
    0  success
    2  data-quality checks failed (bad data, not a bug)
    3  database connection failed
    4  unexpected error

Recording the history
---------------------
A successful run updates ``data/.pipeline_state.json`` with the current
numbers. On its own that file is only a *latest snapshot* — the history of
how the data changed would be lost, because each run overwrites the last.

So a successful run also commits that file to git, with a message recording
what the run saw. The commit log then IS the history:

    git log --oneline -- data/.pipeline_state.json

Three rules keep this safe:

  * ONLY the state file is committed. If you have unrelated work in progress
    in the working tree, it is left completely alone.
  * A failed run commits nothing. The state file is only updated after the
    pipeline has already succeeded, so the record always matches reality.
  * The push is skipped when the local branch has commits that have not been
    reviewed, so an automatic run can never publish unreviewed work.

The commit is best-effort: if git is unavailable, misconfigured, or the
remote is unreachable, the run still counts as a success. History is a
nice-to-have; the pipeline's job is the data.

Usage
-----
    python scripts/run_scheduled.py            # run once, write a log
    python scripts/run_scheduled.py --no-log   # run without writing a log
    python scripts/run_scheduled.py --no-commit  # run without recording history
"""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from pathlib import Path

# Make sure the scripts folder is importable no matter how we are invoked.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

LOG_DIR = ROOT / "logs"
STATE_FILE = ROOT / "data" / ".pipeline_state.json"

EXIT_OK = 0
EXIT_DATA_QUALITY = 2
EXIT_DB = 3
EXIT_UNEXPECTED = 4


# --------------------------------------------------------------------------
# History — commit the run state so `git log` records what changed
# --------------------------------------------------------------------------
def _git(*args: str) -> tuple[int, str]:
    """Run a git command. Returns (returncode, combined output)."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, f"git unavailable: {exc}"


def build_commit_message(body: str, when: datetime) -> str:
    """Compose the commit message that records this run.

    The message is the readable half of the history. ``git log`` then answers
    "what did the data look like on that day, and what changed?" without
    anyone having to open a JSON file.

    The headline numbers come from the state file the pipeline just wrote.
    The NEW/GONE names come from the drift report the pipeline printed, so
    the commit message says who joined and who left.
    """
    state: dict = {}
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}

    total = state.get("total_salary")
    headline = f"Run {when:%Y-%m-%d %H:%M} - data snapshot"
    if state.get("clean_rows") is not None and isinstance(total, int):
        headline = (
            f"Run {when:%Y-%m-%d %H:%M} - "
            f"{state['clean_rows']} rows, total {total:,}"
        )

    lines = [headline, ""]

    def num(value) -> str:
        return f"{value:,}" if isinstance(value, int) else str(value)

    if state:
        lines.append(f"rows   : {state.get('clean_rows')}")
        lines.append(f"total  : {num(total)}")
        lines.append(f"mean   : {num(state.get('mean_salary'))}")
        lines.append(f"median : {num(state.get('median_salary'))}")

    added = [ln.split("NEW:", 1)[1].strip() for ln in body.splitlines() if "NEW:" in ln]
    gone = [ln.split("GONE:", 1)[1].strip() for ln in body.splitlines() if "GONE:" in ln]
    if added:
        lines.append("")
        lines.append("joined : " + ", ".join(added))
    if gone:
        lines.append("left   : " + ", ".join(gone))
    if not added and not gone and "no change since the last run" in body:
        lines.append("")
        lines.append("no data change since the last run")

    lines.append("")
    lines.append("Recorded automatically by scripts/run_scheduled.py")
    return "\n".join(lines)


def record_history(message: str) -> str:
    """Commit the run state so the git log becomes the run history.

    Best-effort by design. Every failure path returns a note instead of
    raising, because a broken git configuration must not fail a pipeline run
    that has already done its job correctly.

    Only ``data/.pipeline_state.json`` is staged. Any other change in the
    working tree is left untouched.

    The push is deliberately conservative: it only happens when the local
    branch is level with its remote, so an automatic run can never publish
    work that has not been reviewed. If the branch is ahead, the commit is
    still made (the history is the point) and the note says the push was
    skipped.
    """
    if not STATE_FILE.exists():
        return "no state file to record"

    rel_state = str(STATE_FILE.relative_to(ROOT))

    # Is there anything to record? If the file is unchanged since the last
    # commit, there is no new history entry to write.
    code, out = _git("status", "--porcelain", "--", rel_state)
    if code != 0:
        return f"git status failed: {out}"
    if not out.strip():
        return "no change since the last recorded run"

    # Which branch are we on? Needed to push to the right place.
    code, branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if code != 0 or not branch.strip():
        return f"cannot determine the current branch: {branch}"

    # Is the branch level with its remote? Only then is it safe to push.
    code, out = _git("rev-parse", "--verify", "--quiet", f"origin/{branch.strip()}")
    remote_sha = out.strip() if code == 0 else ""
    code, local_sha = _git("rev-parse", "HEAD")
    local_sha = local_sha.strip()
    level = bool(remote_sha) and remote_sha == local_sha

    code, out = _git("add", "--", rel_state)
    if code != 0:
        return f"git add failed: {out}"

    code, out = _git("commit", "-m", message)
    if code != 0:
        return f"git commit failed: {out}"

    if not level:
        return (
            f"recorded: {message.splitlines()[0]} "
            f"(push skipped: {branch.strip()} has local commits that were "
            f"not reviewed)"
        )

    # Push the history so the run is recorded off this machine too. A
    # failure here (offline, no credentials) must not turn a good run into
    # a failed one, and the timeout stops a credential prompt from hanging
    # the scheduled task.
    code, out = _git("push", "origin", f"HEAD:refs/heads/{branch.strip()}")
    if code != 0:
        first = out.splitlines()[0] if out else "unknown"
        return f"recorded: {message.splitlines()[0]} (push not done: {first})"

    return f"recorded and pushed: {message.splitlines()[0]}"


def run_once(write_log: bool = True, write_history: bool = True) -> int:
    """Run the pipeline, capturing all output. Returns an exit code."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now()

    buffer = io.StringIO()
    code = EXIT_OK
    error_text = ""

    try:
        from pipeline import main as pipeline_main
        with redirect_stdout(buffer), redirect_stderr(buffer):
            code = pipeline_main()
    except SystemExit as exc:                     # raised by checks on failure
        code = int(exc.code or 0)
    except Exception:                             # anything else is a bug
        code = EXIT_UNEXPECTED
        error_text = traceback.format_exc()
        buffer.write(error_text)

    # Map the pipeline's own codes onto our documented set.
    if code not in (EXIT_OK, EXIT_DATA_QUALITY, EXIT_DB, EXIT_UNEXPECTED):
        if code != EXIT_OK:
            code = EXIT_UNEXPECTED if not error_text else code

    finished = datetime.now()
    duration = (finished - started).total_seconds()

    status = "SUCCESS" if code == EXIT_OK else "FAILED"
    body = buffer.getvalue()

    # -- record the history ------------------------------------------------
    # Only on success. A failed run leaves the state file alone, so the
    # recorded history always matches the data that actually exists.
    history_note = ""
    if write_history:
        if code == EXIT_OK:
            message = build_commit_message(body, finished)
            history_note = record_history(message)
        else:
            history_note = "not recorded: the run failed"

    if write_log:
        stamp = started.strftime("%Y-%m-%d_%H%M%S")
        log_path = LOG_DIR / f"pipeline_{stamp}.log"
        log_path.write_text(
            f"run started : {started:%Y-%m-%d %H:%M:%S}\n"
            f"run finished: {finished:%Y-%m-%d %H:%M:%S}\n"
            f"duration    : {duration:.1f}s\n"
            f"exit code   : {code}\n"
            f"status      : {status}\n"
            f"{'-' * 60}\n"
            f"{body}\n"
            f"{'-' * 60}\n"
            f"history     : {history_note}\n",
            encoding="utf-8",
        )
        # keep only the 30 most recent logs so the folder cannot grow forever
        logs = sorted(LOG_DIR.glob("pipeline_*.log"))
        for old in logs[:-30]:
            old.unlink(missing_ok=True)

    print(f"[{status}] exit={code} duration={duration:.1f}s")
    if body:
        print(body.strip())
    print(f"history     : {history_note}")
    return code


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-log", action="store_true",
                    help="do not write a log file")
    ap.add_argument("--no-commit", action="store_true",
                    help="do not commit the run state to git")
    ap.add_argument("--log-dir",
                    help="override the log directory")
    args = ap.parse_args()

    global LOG_DIR
    if args.log_dir:
        LOG_DIR = Path(args.log_dir)

    return run_once(write_log=not args.no_log, write_history=not args.no_commit)


if __name__ == "__main__":
    raise SystemExit(main())

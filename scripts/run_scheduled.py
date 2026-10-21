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

Usage
-----
    python scripts/run_scheduled.py            # run once, write a log
    python scripts/run_scheduled.py --no-log   # run without writing a log
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from pathlib import Path

# Make sure the scripts folder is importable no matter how we are invoked.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

LOG_DIR = ROOT / "logs"

EXIT_OK = 0
EXIT_DATA_QUALITY = 2
EXIT_DB = 3
EXIT_UNEXPECTED = 4


def run_once(write_log: bool = True) -> int:
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
            f"{body}\n",
            encoding="utf-8",
        )
        # keep only the 30 most recent logs so the folder cannot grow forever
        logs = sorted(LOG_DIR.glob("pipeline_*.log"))
        for old in logs[:-30]:
            old.unlink(missing_ok=True)

    print(f"[{status}] exit={code} duration={duration:.1f}s")
    if body:
        print(body.strip())
    return code


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-log", action="store_true",
                    help="do not write a log file")
    ap.add_argument("--log-dir",
                    help="override the log directory")
    args = ap.parse_args()

    global LOG_DIR
    if args.log_dir:
        LOG_DIR = Path(args.log_dir)

    return run_once(write_log=not args.no_log)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Run-state tracking for the employee salary pipeline.

Why this exists
---------------
The original pipeline hard-coded ``CLEAN_ROWS = 9`` and ``TOTAL_SALARY =
554_500``. That was the right choice while the dataset was a frozen, published
snapshot: it made the README's numbers impossible to drift silently.

It is the wrong choice once the source is allowed to grow. A gate that rejects
every new employee is not a gate, it is a wall — and you end up disabling it,
which leaves you with no protection at all.

This module keeps the protection WITHOUT the wall:

  * each successful run writes a small state file (row count, totals, mean,
    median, the set of employee names, and a timestamp);
  * each subsequent run compares the new numbers against that file;
  * the comparison is *reported* rather than blocked — growth is expected, but
    it is never silent;
  * a shrink is treated as suspicious (data disappearing is almost always a
    bug, not a decision), so that DOES block.

The distinction matters: growth is normal, loss is a defect. Reporting the
diff is what lets you say "the overnight job added two employees and the
salary bill rose 13.8%" instead of "the job ran".

State file
----------
``data/.pipeline_state.json`` — committed, deliberately. It is not a secret
and not machine-specific; committing it means the drift report is meaningful
across machines and the project's history of change is auditable in git.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

STATE_FILENAME = ".pipeline_state.json"


def file_sha256(path: Path) -> str:
    """SHA-256 of a file, or '' if it does not exist.

    Used to detect a hand-edit to a GENERATED file. The cleaned CSV is
    rewritten from the raw source on every run, so any difference between the
    hash we last wrote and the hash on disk means someone edited it by hand —
    and their edit is about to be overwritten.
    """
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


# --------------------------------------------------------------------------
# Snapshot of a run
# --------------------------------------------------------------------------
@dataclass
class Snapshot:
    """The numbers worth remembering between runs."""

    taken_at: str
    raw_rows: int
    clean_rows: int
    total_salary: int
    mean_salary: int
    median_salary: int
    names: list[str] = field(default_factory=list)
    clean_sha256: str = ""        # hash of the cleaned CSV we last wrote
    raw_sha256: str = ""          # hash of the raw source we last read

    # ------------------------------------------------------------------
    @classmethod
    def from_frames(cls, raw: pd.DataFrame, clean: pd.DataFrame,
                    clean_path: Path | None = None,
                    raw_path: Path | None = None) -> "Snapshot":
        return cls(
            taken_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            raw_rows=len(raw),
            clean_rows=len(clean),
            total_salary=int(clean["Salary"].sum()),
            mean_salary=int(round(clean["Salary"].mean())),
            median_salary=int(clean["Salary"].median()),
            names=sorted(str(n) for n in clean["Name"]),
            clean_sha256=file_sha256(clean_path) if clean_path else "",
            raw_sha256=file_sha256(raw_path) if raw_path else "",
        )

    def to_dict(self) -> dict:
        return {
            "taken_at": self.taken_at,
            "raw_rows": self.raw_rows,
            "clean_rows": self.clean_rows,
            "total_salary": self.total_salary,
            "mean_salary": self.mean_salary,
            "median_salary": self.median_salary,
            "names": self.names,
            "clean_sha256": self.clean_sha256,
            "raw_sha256": self.raw_sha256,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Snapshot":
        return cls(
            taken_at=d.get("taken_at", "unknown"),
            raw_rows=int(d["raw_rows"]),
            clean_rows=int(d["clean_rows"]),
            total_salary=int(d["total_salary"]),
            mean_salary=int(d["mean_salary"]),
            median_salary=int(d["median_salary"]),
            names=list(d.get("names", [])),
            clean_sha256=d.get("clean_sha256", ""),
            raw_sha256=d.get("raw_sha256", ""),
        )


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------
def load_state(path: Path) -> Snapshot | None:
    """Read the last successful run, or None if this is the first run."""
    if not path.exists():
        return None
    try:
        return Snapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, KeyError, ValueError):
        # A corrupt state file must not stop the pipeline — treat it as absent
        # and let the next successful run establish a new baseline.
        return None


def save_state(path: Path, snap: Snapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snap.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------
@dataclass
class Drift:
    """How this run differs from the last successful one."""

    previous: Snapshot | None
    current: Snapshot
    added_names: list[str] = field(default_factory=list)
    removed_names: list[str] = field(default_factory=list)
    row_delta: int = 0
    total_delta: int = 0
    total_pct: float = 0.0
    shrank: bool = False

    @property
    def is_first_run(self) -> bool:
        return self.previous is None

    @property
    def changed(self) -> bool:
        return bool(
            self.added_names
            or self.removed_names
            or self.row_delta
            or self.total_delta
        )

    def lines(self) -> list[str]:
        """Human-readable report lines, for the pipeline log."""
        if self.is_first_run:
            return [
                "No previous run recorded — establishing a baseline.",
                f"  rows    {self.current.clean_rows}",
                f"  total   {self.current.total_salary:,}",
                f"  mean    {self.current.mean_salary:,}",
                f"  median  {self.current.median_salary:,}",
            ]

        assert self.previous is not None
        p = self.previous
        out = [f"Comparing to last successful run ({p.taken_at})"]

        def row(label: str, old: int, new: int) -> str:
            delta = new - old
            sign = "+" if delta > 0 else ""
            return f"  {label:<8} {old:,} -> {new:,}   ({sign}{delta:,})"

        out.append(row("rows", p.clean_rows, self.current.clean_rows))
        out.append(row("total", p.total_salary, self.current.total_salary))
        out.append(row("mean", p.mean_salary, self.current.mean_salary))
        out.append(row("median", p.median_salary, self.current.median_salary))

        if self.total_pct:
            out.append(f"  salary bill moved {self.total_pct:+.1f}%")

        if self.added_names:
            out.append(f"  NEW: {', '.join(self.added_names)}")
        if self.removed_names:
            out.append(f"  GONE: {', '.join(self.removed_names)}")
        if not self.changed:
            out.append("  no change since the last run")

        return out


def compare(previous: Snapshot | None, current: Snapshot) -> Drift:
    """Diff the current run against the previous one."""
    if previous is None:
        return Drift(previous=None, current=current)

    added = sorted(set(current.names) - set(previous.names))
    removed = sorted(set(previous.names) - set(current.names))

    total_delta = current.total_salary - previous.total_salary
    pct = (total_delta / previous.total_salary * 100.0) if previous.total_salary else 0.0

    return Drift(
        previous=previous,
        current=current,
        added_names=added,
        removed_names=removed,
        row_delta=current.clean_rows - previous.clean_rows,
        total_delta=total_delta,
        total_pct=pct,
        shrank=current.clean_rows < previous.clean_rows,
    )

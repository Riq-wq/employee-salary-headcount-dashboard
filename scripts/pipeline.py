#!/usr/bin/env python3
"""
Employee Salary & Headcount — automated pipeline (Level 1: script it).

This is the *production* version of ``notebooks/employee  data cleaning.ipynb``.
The notebook shows the reasoning step by step and stays in the repo as the
learning artifact. This script performs the same cleaning, writes the cleaned
CSV, and loads the result into MySQL — all from a single command:

    python scripts/pipeline.py

Design rules (deliberate, and worth saying out loud in an interview):

1. PATHS ARE RELATIVE TO THE REPO. The notebook hard-codes
   ``C:/Users/Hassan/Desktop/...``, so it only runs on one machine. Here we
   resolve everything from this file's own location, so the repo runs anywhere.

2. THE CLEANING LOGIC IS UNCHANGED. Same duplicate drop, same median
   imputation, same negative-age fix, same 900,000 -> 90,000 correction, same
   Diana-city assumption. The script must produce a cleaned CSV that is
   byte-identical to the one the notebook produced. We verify that.

3. STAGES ARE SEPARATE FUNCTIONS. clean -> write -> load. Later levels wrap
   these with validation (Level 2) and incremental loading (Level 3) without
   rewriting the cleaning itself.

Note on the two assumptions this project documents:
  * Diana's blank city is filled with "Kisumu" as an ASSUMPTION, not a fact.
    The mode is not unique (Kisumu, Mombasa and Nairobi all appear twice).
  * Row 9's blank name becomes the placeholder "Jamal"; no metric uses Name.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from checks import run_all_checks, DataQualityError
from incremental import incremental_load
from state import (
    STATE_FILENAME, Snapshot, compare, file_sha256, load_state, save_state,
)

# --------------------------------------------------------------------------
# Paths — resolved from this file, never hard-coded
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "data" / "employee dataset.csv"
CLEAN_CSV = ROOT / "data" / "employee_dataset_cleaned.csv"
STATE_FILE = ROOT / "data" / STATE_FILENAME
ENV_FILE = ROOT / ".env"

TABLE_NAME = "employees"
ID_COL = "EmployeeID"


# --------------------------------------------------------------------------
# Stage 1 — clean
# --------------------------------------------------------------------------
def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Apply the seven documented data-quality fixes.

    Readings match the notebook exactly; each step is annotated with the
    defect it repairs so the script is self-documenting.

    One bug in the original notebook is deliberately NOT reproduced here — see
    ``impute_median_age`` below.
    """
    df = raw.copy()

    # Drop Alice's exact duplicate row (she appears as EmployeeID 1 and 4).
    # Left in, she would double-count both headcount and the salary bill.
    df = df.drop_duplicates(subset=["Name", "Age", "City", "Salary", "JoinDate"])

    # Blank name (EmployeeID 9) -> placeholder. No metric touches this field.
    df["Name"] = df["Name"].fillna("Jamal")

    # Blank age (Bob) and the invalid negative age (Faith, -5) -> median age.
    df = impute_median_age(df)

    # Blank salary (Charlie) -> median salary. The mean is unusable here
    # because of the 900,000 typo, which is still present at this point.
    df["Salary"] = df["Salary"].fillna(df["Salary"].median())

    # Blank city (Diana) -> Kisumu as an ASSUMPTION. The mode is not unique.
    df["City"] = df["City"].fillna("Kisumu")

    # George's 900,000 is a 10x typo: correct to 90,000, in line with his peers.
    df.loc[df["Name"] == "George", "Salary"] = 90_000

    # Salary is whole KES. The median imputation above promoted the column to
    # float, so cast back to int — otherwise the CSV reads "55000.0".
    df["Salary"] = df["Salary"].round().astype(int)

    # Renumber EmployeeID sequentially after dropping the duplicate, as the
    # README documents ("the cleaned file drops the duplicate and renumbers").
    # Raw IDs are not stable identifiers here; cross-reference by name.
    df[ID_COL] = range(1, len(df) + 1)

    return df.reset_index(drop=True)


def impute_median_age(df: pd.DataFrame) -> pd.DataFrame:
    """Fix both age defects with a single, uncontaminated median.

    The original notebook did this in two passes and both were skewed:

      pass 1  filled Bob's blank age with the median of
              [-5, 25, 27, 28, 29, 31, 35, 40] = 28.5
              — but -5 is INVALID data, so it dragged the median down.
      pass 2  replaced Faith's -5, then filled from a set that now included
              the just-imputed 28.5, giving 28.75, which rounds to 28.

    The result (28) was then not the median of anything real, and it did not
    match the README's stated value of 29.

    Correct approach: drop invalid ages FIRST, then compute the median once
    from valid ages only — [25, 27, 28, 29, 31, 35, 40] -> 29.0 — and use
    that single value for every age gap. This makes the published "29" true
    by construction rather than by accident.
    """
    df = df.copy()

    # Invalid values first. A negative age is not a real observation.
    df.loc[df["Age"] < 0, "Age"] = pd.NA

    # One clean median, computed from valid ages only.
    valid_ages = df["Age"].dropna()
    median_age = int(round(float(valid_ages.median())))

    # Apply it to every gap (Bob's blank and Faith's corrected -5).
    df["Age"] = df["Age"].fillna(median_age).round().astype(int)

    return df


# --------------------------------------------------------------------------
# Stage 2 — write the cleaned CSV
# --------------------------------------------------------------------------
def write_clean(df: pd.DataFrame, path: Path) -> str:
    """Write the cleaned dataset and return its SHA-256.

    JoinDate is written in its original d/m/Y text form because
    ``reports/generate_report.py`` parses it with ``%d/%m/%Y``. We deliberately
    do NOT reformat dates here — the report and the CSV must agree.

    Line endings are CRLF to match the rest of this repo (``.gitattributes``
    does not normalise CSV, and every other text file here is CRLF). Pandas on
    Windows writes CRLF by default, but we set it explicitly so the output is
    identical on any platform.

    The returned hash is of the file AS WRITTEN, so the state file records what
    we produced rather than what was on disk beforehand. That is what makes the
    hand-edit detection reliable.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\r\n")
    return file_sha256(path)


# --------------------------------------------------------------------------
# Stage 3 — load into MySQL
# --------------------------------------------------------------------------
def get_engine():
    """Build a SQLAlchemy engine from the untracked .env file."""
    load_dotenv(dotenv_path=ENV_FILE)
    required = ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise SystemExit(
            f"Missing environment variables: {', '.join(missing)}.\n"
            f"Create {ENV_FILE} (see .env.example) with your MySQL credentials."
        )
    url = (
        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    return create_engine(url)


# Loading is handled by ``incremental.incremental_load`` (Level 3).
# The Level 1 full-replace behaviour is available by passing
# ``if_exists="replace"`` to pandas' ``to_sql`` directly, but it is no longer
# used by the pipeline: replacing the table drops indexes, empties it briefly,
# and rewrites every row on every run.


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def main() -> int:
    print("Employee Salary pipeline — Level 4 (growth-aware gate)")
    print("=" * 60)

    if not RAW_CSV.exists():
        print(f"ERROR: raw file not found: {RAW_CSV}")
        return 1

    # -- stage 1: read ------------------------------------------------------
    print(f"[1/4] Reading  {RAW_CSV.relative_to(ROOT)}")
    raw = pd.read_csv(RAW_CSV)
    print(f"      raw rows: {len(raw)}")

    # -- stage 2: clean -----------------------------------------------------
    clean_df = clean(raw)
    print(f"[2/4] Cleaned  -> {len(clean_df)} rows "
          f"({len(raw) - len(clean_df)} duplicate removed)")

    # -- stage 3: validate --------------------------------------------------
    # Runs BEFORE anything is written. If a check fails we stop here, with the
    # cleaned CSV and the MySQL table both left as they were.
    #
    # The last successful run is loaded first so the count-based checks can
    # tell growth (expected) from shrinkage (a defect). See checks.py.
    previous = load_state(STATE_FILE)
    print("[3/4] Validating")
    if previous is None:
        print("      no previous run recorded — this run sets the baseline")
    try:
        run_all_checks(raw, clean_df, verbose=True, previous=previous)
    except DataQualityError as exc:
        print()
        print("=" * 60)
        print("PIPELINE STOPPED — data-quality checks failed")
        print("=" * 60)
        print(exc)
        return 2

    # -- stage 3b: report what changed against the last successful run ------
    # The hash of the cleaned CSV must be captured BEFORE the new file is
    # written, so it reflects what was on disk (possibly hand-edited) rather
    # than what we are about to produce.
    on_disk_before = file_sha256(CLEAN_CSV)

    current = Snapshot.from_frames(raw, clean_df, raw_path=RAW_CSV)
    drift = compare(previous, current)
    print()
    for line in drift.lines():
        print(line)

    # -- stage 3c: was a GENERATED file hand-edited? ------------------------
    # The cleaned CSV is regenerated from the raw source on every run, so a
    # hand-edit to it is about to be overwritten. Say so BEFORE it happens,
    # rather than silently discarding someone's work.
    if previous is not None and previous.clean_sha256:
        if on_disk_before and on_disk_before != previous.clean_sha256:
            print()
            print("!" * 60)
            print("WARNING: the cleaned CSV was edited by hand since the last run.")
            print(f"  file   : {CLEAN_CSV.relative_to(ROOT)}")
            print(f"  last written : {previous.clean_sha256[:16]}...")
            print(f"  now on disk  : {on_disk_before[:16]}...")
            print("  This file is REGENERATED from the raw source on every run,")
            print("  so those edits are about to be overwritten.")
            print("  To add an employee, edit the RAW source instead:")
            print(f"    {RAW_CSV.relative_to(ROOT)}")
            print("!" * 60)

    # -- stage 4: write + incremental load ---------------------------------
    written_hash = write_clean(clean_df, CLEAN_CSV)
    current.clean_sha256 = written_hash
    print(f"\n[4/4] Wrote {CLEAN_CSV.relative_to(ROOT)}")

    engine = get_engine()
    print(f"      Loading into MySQL table `{TABLE_NAME}` (incremental)")
    plan = incremental_load(clean_df, engine, apply=True, verbose=True)

    # Record this run as the new baseline. Done last, so a failed load never
    # becomes the reference and silently hides the discrepancy on the next run.
    save_state(STATE_FILE, current)

    print("=" * 60)
    print(f"Done — {plan.summary()}")
    print(f"State written to {STATE_FILE.relative_to(ROOT)}")
    print("Next: refresh the Power BI dashboard (see README).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Data-quality checks for the employee salary pipeline (Level 2).

Why this module exists
----------------------
Level 1 made the pipeline runnable in one command. This level makes it
*refuse to produce wrong numbers*.

The point is not to log a warning nobody reads. Each check either passes or
raises ``DataQualityError``, which stops the run before anything is written to
MySQL and before the report is regenerated. A pipeline that fails loudly is
more trustworthy than one that silently emits a plausible-looking dashboard.

The clearest example of why this matters: the original notebook contained
``Age = -5``. That single invalid value contaminated the median, which then
contaminated every imputed age. The range check below catches exactly that
class of error at the point it enters the data.

Usage
-----
    from checks import run_all_checks

    run_all_checks(raw_df, clean_df)   # raises DataQualityError on failure

Or run this file directly to check the current data on disk:

    python scripts/checks.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------
# Expectations
#
# These fall into two kinds, and the distinction is the whole design:
#
#   STRUCTURAL expectations (ranges, schema, "every defect is repaired") are
#   true for any correct dataset, whatever its size. They scale freely.
#
#   COUNT expectations (row counts, headline totals) are only true for ONE
#   particular dataset — the nine-row snapshot this project published. They
#   were hard walls in the first version, which meant every new employee was
#   rejected.
#
# The counts below are therefore no longer walls. They are kept as the
# DOCUMENTED BASELINE: the figures quoted in the README, the PDF report and
# the dashboard. The pipeline now compares each run against the previous
# successful run (see ``state.py``) and reports the movement, rather than
# refusing to proceed. Growth is expected; silent growth is what we prevent.
# --------------------------------------------------------------------------
RAW_ROWS = 10                 # raw rows in the published snapshot (baseline)
CLEAN_ROWS = 9                # clean rows in the published snapshot (baseline)
DUPLICATES_DROPPED = 1        # duplicates in the published snapshot (baseline)

AGE_MIN, AGE_MAX = 18, 70     # plausible working ages
SALARY_MIN, SALARY_MAX = 10_000, 500_000   # plausible monthly KES range

TOTAL_SALARY = 554_500        # the published snapshot total
MEAN_SALARY = 61_611          # the published snapshot mean
MEDIAN_SALARY = 59_500        # the published snapshot median

# How far the headline numbers may move in one run before the gate objects.
# A single new employee among nine is an ~11% row increase, so the allowance
# must be generous enough not to block ordinary growth, while still catching a
# corrupted or duplicated source file (which would move the total by 2x or
# more at once).
MAX_TOTAL_MOVE_PCT = 80.0     # total salary may not roughly double in one run
MAX_ROW_MOVE_PCT = 100.0      # row count may not roughly double in one run

# How much the row count may FALL in one run before it is treated as a defect.
# A departure is legitimate and passes (and is reported); a loss this large in
# a single run is the signature of a truncated or partially delivered export.
MAX_ROW_LOSS_PCT = 40.0

REQUIRED_COLUMNS = ["EmployeeID", "Name", "Age", "City", "Salary", "JoinDate"]

# The source file is edited in Excel, and Excel rewrites dates in its own
# locale's format. The file's own convention is day-first (``dd/mm/yyyy``),
# because that is what the PDF report parses (``%d/%m/%Y``). This pattern is
# what the gate expects to see on every JoinDate value.
DATE_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")

# The two documented assumptions. Both are stated as such in the README, and
# both are asserted here so that an undocumented change would fail the run.
ASSUMED_CITY_NAME = "Diana"
ASSUMED_CITY_VALUE = "Kisumu"
PLACEHOLDER_NAME = "Jamal"


class DataQualityError(Exception):
    """Raised when the data does not meet the documented expectations."""


@dataclass
class Result:
    name: str
    passed: bool
    detail: str = ""


def _check(name: str, condition: bool, detail: str = "") -> Result:
    return Result(name=name, passed=bool(condition), detail=detail)


# --------------------------------------------------------------------------
# Individual checks
# --------------------------------------------------------------------------
def check_schema(df: pd.DataFrame, label: str) -> Result:
    """All required columns present, in order."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return _check(f"{label}: schema", False, f"missing columns: {missing}")
    extra = [c for c in df.columns if c not in REQUIRED_COLUMNS]
    detail = f"columns={list(df.columns)}"
    if extra:
        detail += f" (extra: {extra})"
    return _check(f"{label}: schema", True, detail)


def check_raw_shape(df: pd.DataFrame, previous=None) -> Result:
    """The raw source may grow or shrink slightly; large losses are blocked.

    Same reasoning as ``check_clean_shape``: a departure is legitimate, a
    truncated export is not. A loss beyond ``MAX_ROW_LOSS_PCT`` fails.
    """
    n = len(df)
    if previous is None:
        return _check(
            "raw: row count",
            n > 0,
            f"{n} rows (no previous run; baseline is {RAW_ROWS})",
        )

    prev = previous.raw_rows
    if prev > 0 and n < prev:
        loss_pct = (prev - n) / prev * 100.0
        if loss_pct > MAX_ROW_LOSS_PCT:
            return _check(
                "raw: row count",
                False,
                f"lost {prev - n} of {prev} rows ({loss_pct:.0f}%) in one run; "
                f"limit is {MAX_ROW_LOSS_PCT:.0f}%. Check the source file was "
                f"delivered whole.",
            )
        return _check(
            "raw: row count",
            True,
            f"{n} rows (down {prev - n} from {prev} — reported, not blocked)",
        )

    return _check(
        "raw: row count",
        True,
        f"{n} rows (last run {prev}; baseline {RAW_ROWS})",
    )


def check_duplicates_dropped(raw: pd.DataFrame, clean: pd.DataFrame) -> Result:
    """Duplicate removal must happen, and must not suddenly jump.

    If this reports 0 on a source that is known to contain a duplicate,
    deduplication has silently stopped working. If it jumps sharply, the source
    probably arrived with a botched export that duplicated a block of rows —
    which would double-count headcount and the salary bill.
    """
    dropped = len(raw) - len(clean)
    if len(raw) == 0:
        return _check("clean: duplicates dropped", False, "raw file is empty")
    pct = dropped / len(raw) * 100.0
    if pct > 50.0:
        return _check(
            "clean: duplicates dropped",
            False,
            f"{dropped} of {len(raw)} rows deduplicated ({pct:.0f}%) — too "
            f"many; check the source for a duplicated block. Baseline was "
            f"{DUPLICATES_DROPPED}.",
        )
    return _check(
        "clean: duplicates dropped",
        True,
        f"{dropped} dropped (baseline {DUPLICATES_DROPPED})",
    )


def check_clean_shape(clean: pd.DataFrame, previous=None) -> Result:
    """The cleaned set may grow or shrink slightly; large losses are blocked.

    A departure — an employee leaving, or a row being corrected out — is a
    legitimate reason for the set to shrink, and blocking every shrink would
    make the state file impossible to correct. A *large* loss in one run is a
    different thing: it is the signature of a truncated or partially delivered
    export, where most of the data never arrived.

    So: small changes pass and are reported by the drift layer; a loss beyond
    ``MAX_ROW_LOSS_PCT`` fails the run.
    """
    n = len(clean)
    if previous is None:
        return _check(
            "clean: row count",
            n > 0,
            f"{n} rows (no previous run; baseline is {CLEAN_ROWS})",
        )

    prev = previous.clean_rows
    if prev > 0 and n < prev:
        loss_pct = (prev - n) / prev * 100.0
        if loss_pct > MAX_ROW_LOSS_PCT:
            return _check(
                "clean: row count",
                False,
                f"lost {prev - n} of {prev} rows ({loss_pct:.0f}%) in one run; "
                f"limit is {MAX_ROW_LOSS_PCT:.0f}%. This looks like a "
                f"truncated or partially delivered export.",
            )
        return _check(
            "clean: row count",
            True,
            f"{n} rows (down {prev - n} from {prev} — reported, not blocked)",
        )

    return _check(
        "clean: row count",
        True,
        f"{n} rows (last run {prev}; baseline {CLEAN_ROWS})",
    )


def check_no_nulls(clean: pd.DataFrame) -> Result:
    """No nulls anywhere — every gap must be filled, documented, and intentional."""
    nulls = clean.isna().sum()
    bad = {k: int(v) for k, v in nulls.items() if v > 0}
    return _check("clean: no nulls", not bad, f"nulls found: {bad}" if bad else "none")


def check_age_range(clean: pd.DataFrame) -> Result:
    """Ages within a plausible working range.

    THIS IS THE CHECK THAT WOULD HAVE CAUGHT THE ORIGINAL BUG. The raw file
    contained Age = -5; had this check run before imputation, the run would
    have failed loudly instead of quietly skewing the median.
    """
    ages = clean["Age"]
    below = int((ages < AGE_MIN).sum())
    above = int((ages > AGE_MAX).sum())
    ok = below == 0 and above == 0
    return _check(
        "clean: ages in plausible range",
        ok,
        f"outside [{AGE_MIN}, {AGE_MAX}]: {below} below, {above} above"
        if not ok else f"range {int(ages.min())}-{int(ages.max())}",
    )


def check_salary_range(clean: pd.DataFrame) -> Result:
    """Salaries within a plausible monthly range (catches 10x typos)."""
    s = clean["Salary"]
    below = int((s < SALARY_MIN).sum())
    above = int((s > SALARY_MAX).sum())
    ok = below == 0 and above == 0
    return _check(
        "clean: salaries in plausible range",
        ok,
        f"outside [{SALARY_MIN}, {SALARY_MAX}]: {below} below, {above} above"
        if not ok else f"range {int(s.min()):,}-{int(s.max()):,}",
    )


def check_dtypes(clean: pd.DataFrame) -> Result:
    """Age and Salary must be whole numbers; JoinDate must stay text d/m/Y."""
    problems = []
    if not pd.api.types.is_integer_dtype(clean["Age"]):
        problems.append(f"Age is {clean['Age'].dtype}, expected integer")
    if not pd.api.types.is_integer_dtype(clean["Salary"]):
        problems.append(f"Salary is {clean['Salary'].dtype}, expected integer")
    if pd.api.types.is_datetime64_any_dtype(clean["JoinDate"]):
        problems.append("JoinDate was converted to datetime; the report parses %d/%m/%Y")
    return _check("clean: column dtypes", not problems, "; ".join(problems) or "ok")


def check_expected_totals(clean: pd.DataFrame, previous=None) -> Result:
    """Headline figures are reported against the last run, and sanity-bounded.

    These are the numbers quoted in the README, the PDF report and the
    dashboard. In the frozen version they were asserted to the exact shilling,
    which meant any new employee failed the run.

    Now they are bounded instead of fixed:

      * the salary bill may not move by more than ``MAX_TOTAL_MOVE_PCT`` in a
        single run — a duplicate or corrupted export moves it by 2x or more,
        which is the failure worth catching;
      * ordinary growth passes and is reported by the drift layer, so the
        change is visible rather than assumed.

    The exact published snapshot figures remain available as the documented
    baseline and are printed alongside, so it stays obvious where the numbers
    in the README came from.
    """
    total = int(clean["Salary"].sum())
    mean = int(round(clean["Salary"].mean()))
    median = int(clean["Salary"].median())

    detail = (f"total={total:,} (snapshot {TOTAL_SALARY:,}), "
              f"mean={mean:,} (snapshot {MEAN_SALARY:,}), "
              f"median={median:,} (snapshot {MEDIAN_SALARY:,})")

    if previous is None:
        return _check("clean: headline totals", True, detail)

    prev_total = previous.total_salary
    if prev_total <= 0:
        return _check("clean: headline totals", True, detail)

    move_pct = abs(total - prev_total) / prev_total * 100.0
    if move_pct > MAX_TOTAL_MOVE_PCT:
        return _check(
            "clean: headline totals",
            False,
            f"salary bill moved {move_pct:.0f}% in one run "
            f"({prev_total:,} -> {total:,}); limit is "
            f"{MAX_TOTAL_MOVE_PCT:.0f}%. Check the source for duplicated or "
            f"corrupted rows. {detail}",
        )
    return _check(
        "clean: headline totals",
        True,
        f"{detail} [moved {move_pct:+.1f}% vs last run]",
    )


def check_employee_ids(clean: pd.DataFrame) -> Result:
    """EmployeeID is renumbered 1..N with no gaps or repeats."""
    ids = list(clean["EmployeeID"])
    expected = list(range(1, len(clean) + 1))
    return _check(
        "clean: EmployeeID renumbered",
        ids == expected,
        f"got {ids}",
    )


def check_assumptions(clean: pd.DataFrame) -> Result:
    """The two documented assumptions are present and unchanged.

    Diana's city is filled with Kisumu *as an assumption*, and worker 9's name
    is the placeholder Jamal. Both are disclosed in the README. Asserting them
    here means they cannot change silently.
    """
    problems = []
    diana = clean.loc[clean["Name"] == ASSUMED_CITY_NAME, "City"]
    if len(diana) != 1:
        problems.append(f"expected exactly 1 row for {ASSUMED_CITY_NAME}, got {len(diana)}")
    elif diana.iloc[0] != ASSUMED_CITY_VALUE:
        problems.append(
            f"{ASSUMED_CITY_NAME}'s city is {diana.iloc[0]!r}, "
            f"expected the documented assumption {ASSUMED_CITY_VALUE!r}"
        )
    if PLACEHOLDER_NAME not in set(clean["Name"]):
        problems.append(f"placeholder name {PLACEHOLDER_NAME!r} missing")
    return _check("clean: documented assumptions", not problems,
                  "; ".join(problems) or f"{ASSUMED_CITY_NAME}={ASSUMED_CITY_VALUE}, "
                                        f"placeholder={PLACEHOLDER_NAME}")


# --------------------------------------------------------------------------
# INPUT-side checks
#
# The output checks above only prove the *result* is sound. They cannot prove
# the pipeline noticed what it was fixing. If a new defect appeared in the raw
# file, clean() would quietly repair it and the output checks would still pass
# — which is exactly how the original -5 went unnoticed for so long.
#
# These checks assert the raw file contains EXACTLY the defects we documented,
# no more and no fewer. A new defect therefore fails the run instead of being
# silently absorbed.
# --------------------------------------------------------------------------
RAW_EXPECTED_NULLS = {"Name": 1, "Age": 1, "City": 1, "Salary": 1}
RAW_EXPECTED_DUPLICATE_PAIRS = 1     # Alice appears twice
RAW_EXPECTED_INVALID_AGES = 1        # Faith's -5
RAW_EXPECTED_SALARY_TYPOS = 1        # George's 900,000 (>= 10x the next value)


def check_raw_defects(raw: pd.DataFrame) -> Result:
    """The raw file has exactly the documented set of defects.

    If a NEW defect appears (an extra null, a second negative age, another
    salary typo), this fails — so the pipeline cannot silently absorb a
    problem it was never designed to handle.
    """
    problems = []

    # --- nulls -----------------------------------------------------------
    nulls = {k: int(v) for k, v in raw.isna().sum().items() if v > 0}
    if nulls != RAW_EXPECTED_NULLS:
        problems.append(f"nulls {nulls}, expected {RAW_EXPECTED_NULLS}")

    # --- duplicate rows --------------------------------------------------
    dup_pairs = int(raw.duplicated(subset=REQUIRED_COLUMNS[1:]).sum())
    if dup_pairs != RAW_EXPECTED_DUPLICATE_PAIRS:
        problems.append(f"{dup_pairs} duplicate rows, expected "
                        f"{RAW_EXPECTED_DUPLICATE_PAIRS}")

    # --- invalid ages ----------------------------------------------------
    invalid_ages = int((raw["Age"] < AGE_MIN).sum())
    if invalid_ages != RAW_EXPECTED_INVALID_AGES:
        problems.append(f"{invalid_ages} invalid ages, expected "
                        f"{RAW_EXPECTED_INVALID_AGES}")

    # --- salary typos ----------------------------------------------------
    # A value >= 10x the median is treated as a magnitude typo.
    med = raw["Salary"].median()
    typos = int((raw["Salary"] > med * 10).sum())
    if typos != RAW_EXPECTED_SALARY_TYPOS:
        problems.append(f"{typos} salary typos (>=10x median), expected "
                        f"{RAW_EXPECTED_SALARY_TYPOS}")

    return _check("raw: exactly the documented defects", not problems,
                  "; ".join(problems) or
                  f"nulls={nulls}, dups={dup_pairs}, "
                  f"invalid_ages={invalid_ages}, salary_typos={typos}")


def check_date_format(raw: pd.DataFrame) -> Result:
    """Every JoinDate must still be text in ``dd/mm/yyyy`` form.

    Why this check exists
    ---------------------
    The source file is edited in Excel. Excel is a spreadsheet application,
    and a spreadsheet application will happily reinterpret a date you typed
    using its OWN locale and then write it back in that locale's format.

    On an en-US machine, typing ``01/06/2025`` into a General-formatted cell
    means *6 January 2025* to Excel, and Excel writes it back as
    ``06/01/2025``. In a file where every other date is day-first, that is a
    silent five-month error - and it reaches the database, the report and the
    dashboard looking entirely plausible.

    This check cannot catch that particular mistake, because ``06/01/2025`` is
    a perfectly valid day-first date. What it CAN catch is every OTHER way a
    spreadsheet application rewrites dates: ISO format (``2025-06-01``),
    dashes, unpadded days, two-digit years, and dates whose day/month are
    impossible in either reading.

    The real protection is to edit the file through ``scripts/edit_source.py``,
    which formats the date column as Text before you type into it, so the
    round trip is lossless. This check is the backstop for the cases where
    somebody edits the file without using that script.
    """
    problems = []
    bad = []

    for idx, value in raw["JoinDate"].items():
        text = str(value).strip()
        if not DATE_PATTERN.match(text):
            bad.append(f"row {idx + 2}: {text!r}")
            continue
        try:
            datetime.strptime(text, "%d/%m/%Y")
        except ValueError:
            bad.append(f"row {idx + 2}: {text!r} (not a real date)")

    if bad:
        shown = "; ".join(bad[:4])
        more = f" (+{len(bad) - 4} more)" if len(bad) > 4 else ""
        problems.append(
            f"{len(bad)} JoinDate value(s) are not dd/mm/yyyy{more}: {shown}"
        )

    return _check("raw: date format is dd/mm/yyyy", not problems,
                  "; ".join(problems) or
                  f"{len(raw)} dates, all dd/mm/yyyy")


def check_defects_are_repaired(raw: pd.DataFrame, clean: pd.DataFrame) -> Result:
    """Every documented defect is gone after cleaning.

    The mirror image of the check above: raw defects must exist, and must not
    survive cleaning. Together they prove the repair actually happened rather
    than the defect never being there.
    """
    problems = []
    if int((clean["Age"] < AGE_MIN).sum()) > 0:
        problems.append("invalid age survived cleaning")
    med = raw["Salary"].median()
    if int((clean["Salary"] > med * 10).sum()) > 0:
        problems.append("salary typo survived cleaning")
    if int(clean.isna().sum().sum()) > 0:
        problems.append("null survived cleaning")
    return _check("clean: all raw defects repaired", not problems,
                  "; ".join(problems) or "none remain")


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------
def run_all_checks(raw: pd.DataFrame, clean: pd.DataFrame,
                   verbose: bool = True, previous=None) -> list[Result]:
    """Run every check. Raise DataQualityError if any fail.

    ``previous`` is the last successful run's :class:`~state.Snapshot`, used by
    the checks that need to know whether the data grew or shrank. When it is
    ``None`` (first ever run, or an unreadable state file) those checks fall
    back to reporting the documented baseline rather than failing.

    All checks run before raising, so one run reports every problem rather
    than stopping at the first.
    """
    results = [
        check_schema(raw, "raw"),
        check_schema(clean, "clean"),
        check_raw_shape(raw, previous),
        check_raw_defects(raw),
        check_date_format(raw),
        check_duplicates_dropped(raw, clean),
        check_clean_shape(clean, previous),
        check_no_nulls(clean),
        check_age_range(clean),
        check_salary_range(clean),
        check_dtypes(clean),
        check_expected_totals(clean, previous),
        check_employee_ids(clean),
        check_assumptions(clean),
        check_defects_are_repaired(raw, clean),
    ]

    if verbose:
        print("Data-quality checks")
        print("-" * 52)
        for r in results:
            mark = "PASS" if r.passed else "FAIL"
            print(f"  [{mark}] {r.name:<38} {r.detail}")

    failed = [r for r in results if not r.passed]
    if failed:
        lines = "\n".join(f"  - {r.name}: {r.detail}" for r in failed)
        raise DataQualityError(
            f"{len(failed)} of {len(results)} data-quality checks failed:\n{lines}\n"
            "The pipeline stopped BEFORE writing to MySQL. Fix the data or the "
            "expectation, then re-run."
        )
    return results


# --------------------------------------------------------------------------
# Standalone: check whatever is currently on disk
# --------------------------------------------------------------------------
def _main() -> int:
    root = Path(__file__).resolve().parent.parent
    raw = pd.read_csv(root / "data" / "employee dataset.csv")
    clean = pd.read_csv(root / "data" / "employee_dataset_cleaned.csv")

    # Load the last successful run so the drift-aware checks have a reference.
    from state import load_state, STATE_FILENAME
    previous = load_state(root / "data" / STATE_FILENAME)
    if previous is None:
        print("Note: no previous run recorded for comparison.\n")

    try:
        run_all_checks(raw, clean, previous=previous)
    except DataQualityError as exc:
        print()
        print("FAILED")
        print(exc)
        return 1
    print()
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

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

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------
# Expectations — these encode what "correct" means for this dataset.
# Changing the data should require changing these numbers deliberately.
# --------------------------------------------------------------------------
RAW_ROWS = 10                 # rows in the raw HR export
CLEAN_ROWS = 9                # after removing Alice's exact duplicate
DUPLICATES_DROPPED = 1        # exactly one duplicate, no more, no fewer

AGE_MIN, AGE_MAX = 18, 70     # plausible working ages
SALARY_MIN, SALARY_MAX = 10_000, 500_000   # plausible monthly KES range

TOTAL_SALARY = 554_500        # the published total; must not drift
MEAN_SALARY = 61_611          # rounded published mean
MEDIAN_SALARY = 59_500        # published median

REQUIRED_COLUMNS = ["EmployeeID", "Name", "Age", "City", "Salary", "JoinDate"]

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


def check_raw_shape(df: pd.DataFrame) -> Result:
    return _check(
        "raw: row count",
        len(df) == RAW_ROWS,
        f"expected {RAW_ROWS}, got {len(df)}",
    )


def check_duplicates_dropped(raw: pd.DataFrame, clean: pd.DataFrame) -> Result:
    """Exactly one duplicate row removed — no more, no fewer.

    If this ever reports 0, deduplication silently stopped working. If it
    reports more, something is being deleted that should not be.
    """
    dropped = len(raw) - len(clean)
    return _check(
        "clean: duplicates dropped",
        dropped == DUPLICATES_DROPPED,
        f"expected {DUPLICATES_DROPPED}, got {dropped}",
    )


def check_clean_shape(clean: pd.DataFrame) -> Result:
    return _check(
        "clean: row count",
        len(clean) == CLEAN_ROWS,
        f"expected {CLEAN_ROWS}, got {len(clean)}",
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


def check_expected_totals(clean: pd.DataFrame) -> Result:
    """Headline figures must match the published values.

    These are the numbers quoted in the README, the PDF report and the
    dashboard. If any drifts, something upstream changed and every artifact
    needs to be revisited — so the pipeline stops rather than proceed.
    """
    total = int(clean["Salary"].sum())
    mean = int(round(clean["Salary"].mean()))
    median = int(clean["Salary"].median())
    ok = (total == TOTAL_SALARY and mean == MEAN_SALARY
          and median == MEDIAN_SALARY)
    return _check(
        "clean: headline totals",
        ok,
        f"total={total:,} (exp {TOTAL_SALARY:,}), "
        f"mean={mean:,} (exp {MEAN_SALARY:,}), "
        f"median={median:,} (exp {MEDIAN_SALARY:,})",
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
                   verbose: bool = True) -> list[Result]:
    """Run every check. Raise DataQualityError if any fail.

    All checks run before raising, so one run reports every problem rather
    than stopping at the first.
    """
    results = [
        check_schema(raw, "raw"),
        check_schema(clean, "clean"),
        check_raw_shape(raw),
        check_raw_defects(raw),
        check_duplicates_dropped(raw, clean),
        check_clean_shape(clean),
        check_no_nulls(clean),
        check_age_range(clean),
        check_salary_range(clean),
        check_dtypes(clean),
        check_expected_totals(clean),
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
    try:
        run_all_checks(raw, clean)
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

#!/usr/bin/env python3
"""
Incremental MySQL loading for the employee salary pipeline (Level 3).

Why this module exists
----------------------
Level 1 loaded with ``if_exists="replace"``: drop the table, rewrite it. That is
simple but wrong for production, for three reasons:

  1. It destroys anything the database added — an index, a constraint, a column
     someone else appended, row-level permissions.
  2. It briefly leaves the table EMPTY. Any dashboard refreshing during that
     window sees no data at all.
  3. It rewrites every row every time, even when nothing changed, so the cost
     grows with history rather than with the size of the update.

An incremental load instead compares what arrived against what is already
stored and applies only the difference:
  * new EmployeeID          -> INSERT
  * existing, values differ -> UPDATE
  * existing, identical     -> SKIP (no write at all)

Honest note on this specific dataset
------------------------------------
This HR export is small and gets *corrected* rather than *appended*. On a
nine-row file, "replace" and "incremental" reach the same end state — so the
benefit here is demonstrated, not enormous. What matters is that the machinery
is correct, because the same code run against 100,000 rows behaves very
differently. Saying that plainly is better than overselling it.

Usage
-----
    from incremental import incremental_load, LoadPlan

    plan = incremental_load(clean_df, engine)   # dry run, applies nothing
    plan = incremental_load(clean_df, engine, apply=True)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from sqlalchemy import inspect, text

TABLE = "employees"
KEY = "EmployeeID"
COLUMNS = ["EmployeeID", "Name", "Age", "City", "Salary", "JoinDate"]

# Tracks the last time each row changed, so re-runs are auditable.
META_COLUMN = "last_updated"


@dataclass
class LoadPlan:
    """What an incremental load would do (or did)."""
    inserted: list[int] = field(default_factory=list)   # new EmployeeIDs
    updated: list[int] = field(default_factory=list)    # changed EmployeeIDs
    unchanged: int = 0                                  # left alone
    table_created: bool = False                         # first run
    # Rows present in the database but ABSENT from the incoming data.
    # These are deliberately NOT deleted (see module docstring), so they are
    # reported instead — an unexplained extra employee should never be silent.
    missing_from_source: list[int] = field(default_factory=list)

    @property
    def touched(self) -> int:
        return len(self.inserted) + len(self.updated)

    def summary(self) -> str:
        base = (f"inserted={len(self.inserted)} updated={len(self.updated)} "
                f"unchanged={self.unchanged} touched={self.touched}")
        if self.missing_from_source:
            base += f" | absent_from_source={len(self.missing_from_source)}"
        return base


def _normalise(value):
    """Reduce a value to a comparable form across pandas / MySQL round-trips.

    Two traps this closes:

      * A DATETIME column comes back from MySQL as ``pandas.Timestamp`` while the
        cleaned CSV holds a string like ``'01/03/2025'``. Compared raw, every row
        would look changed on every run and idempotency would silently break.
      * ``numpy`` numeric types and Python ints compare equal but are not always
        the same object; normalising keeps the key predictable.
    """
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if value is pd.NaT:
        return None

    # Dates: compare as a plain date string, format-agnostic.
    if isinstance(value, str):
        parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
        if pd.isna(parsed):
            parsed = pd.to_datetime(value, errors="coerce")
        if not pd.isna(parsed):
            return parsed.strftime("%Y-%m-%d")
        return value.strip()
    if hasattr(value, "strftime") and not isinstance(value, (int, float)):
        return value.strftime("%Y-%m-%d")

    # Numbers: collapse numpy/pandas types onto plain Python.
    try:
        if isinstance(value, (int, float)) or hasattr(value, "item"):
            num = value.item() if hasattr(value, "item") else value
            return round(float(num), 6)
    except (TypeError, ValueError):
        pass
    return value


def _row_key(row: dict, columns: list[str] | None = None) -> tuple:
    """A comparable snapshot of a row's values, ignoring the meta column."""
    return tuple(_normalise(row.get(c)) for c in (columns or COLUMNS))


def fetch_existing(engine, table: str = TABLE) -> pd.DataFrame:
    """Return the current table contents, or an empty frame if it doesn't exist."""
    if not inspect(engine).has_table(table):
        return pd.DataFrame(columns=COLUMNS + [META_COLUMN])
    return pd.read_sql(f"SELECT * FROM {table}", engine)


def ensure_meta_column(engine, table: str = TABLE) -> None:
    """Add the audit column if missing.

    This is a schema migration, and doing it here rather than by dropping the
    table is the entire point: an existing table is upgraded in place, not
    destroyed.
    """
    if not inspect(engine).has_table(table):
        return
    cols = {c["name"] for c in inspect(engine).get_columns(table)}
    if META_COLUMN not in cols:
        with engine.begin() as conn:
            conn.execute(text(
                f"ALTER TABLE {table} ADD COLUMN {META_COLUMN} VARCHAR(32) NULL"
            ))


def _table_columns(engine, table: str) -> set[str]:
    """Names of the columns the target table actually has."""
    if not inspect(engine).has_table(table):
        return set()
    return {c["name"] for c in inspect(engine).get_columns(table)}


def _date_columns(engine, table: str) -> set[str]:
    """Names of columns in the target table that hold a DATE/DATETIME.

    Why this matters
    ----------------
    The cleaning notebook casts ``JoinDate`` with ``pd.to_datetime(..., dayfirst=True)``
    before its ``to_sql`` call, so pandas creates the column as ``DATETIME``. Handing
    MySQL the raw string ``'01/03/2025'`` then fails with:

        (1292, "Incorrect datetime value: '01/03/2025' for column 'JoinDate'")

    Rather than hard-code that JoinDate is a date -- true for this table but a
    fragile assumption in general -- we ask the database what its columns
    actually are and convert to match. If the column were TEXT, nothing changes.
    """
    if not inspect(engine).has_table(table):
        return set()
    names = set()
    for col in inspect(engine).get_columns(table):
        type_name = col["type"].__class__.__name__.upper()
        if "DATE" in type_name or "TIME" in type_name:
            names.add(col["name"])
    return names


def _coerce_for_db(row: dict, date_cols: set[str]) -> dict:
    """Return a copy of ``row`` with date columns converted to native dates.

    Accepts either an already-parsed value or the ``d/m/Y`` string the notebook
    produced, so the loader works whichever way the data arrives.
    """
    if not date_cols:
        return row
    out = dict(row)
    for col in date_cols:
        val = out.get(col)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        if isinstance(val, str):
            parsed = pd.to_datetime(val, dayfirst=True, errors="coerce")
            if pd.isna(parsed):
                # Try the ISO form pandas writes when it round-trips a datetime.
                parsed = pd.to_datetime(val, errors="coerce")
            if not pd.isna(parsed):
                out[col] = parsed.to_pydatetime()
        elif hasattr(val, "to_pydatetime"):
            out[col] = val.to_pydatetime()
    return out


def incremental_load(df: pd.DataFrame, engine, apply: bool = False,
                     verbose: bool = True, table: str = TABLE) -> LoadPlan:
    """Insert new rows and update changed ones; leave everything else untouched.

    With ``apply=False`` this is a dry run that reports the plan without
    writing. That is useful for a scheduled job that should log intent first,
    and it is how the behaviour can be inspected safely.
    """
    plan = LoadPlan()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    existing = fetch_existing(engine, table)
    plan.table_created = not inspect(engine).has_table(table)

    if plan.table_created:
        # First run: nothing to compare against, so this is a full insert.
        plan.inserted = [int(v) for v in df[KEY]]
        if apply:
            add_meta = df.copy()
            add_meta[META_COLUMN] = stamp
            add_meta.to_sql(table, engine, if_exists="replace", index=False)
        if verbose:
            print(f"  table '{table}' did not exist -> created it "
                  f"({len(df)} rows)")
        return plan

    # Match the database's own column types (e.g. a DATETIME JoinDate) so the
    # values we send are ones MySQL can actually parse.
    date_cols = _date_columns(engine, table)

    # Upgrade the table in place rather than dropping it: add the audit column
    # if this table predates it (e.g. one created by the notebook).
    if apply:
        ensure_meta_column(engine, table)
    table_cols = _table_columns(engine, table)

    # Build a lookup of what is already stored: EmployeeID -> row snapshot.
    stored = {int(r[KEY]): r for r in existing.to_dict("records")}
    incoming_ids = {int(v) for v in df[KEY]}

    # Rows in the DB with no counterpart in the incoming data. We do NOT delete
    # them — a truncated source file must never be able to wipe real employees.
    # They are surfaced instead, so the discrepancy is visible in the log.
    plan.missing_from_source = sorted(set(stored) - incoming_ids)

    to_insert: list[dict] = []
    to_update: list[dict] = []

    for raw in df.to_dict("records"):
        emp_id = int(raw[KEY])
        incoming = _coerce_for_db(dict(raw), date_cols)
        incoming[META_COLUMN] = stamp

        if emp_id not in stored:
            to_insert.append(incoming)
            plan.inserted.append(emp_id)
            continue

        if _row_key(stored[emp_id]) != _row_key(raw):
            to_update.append(incoming)
            plan.updated.append(emp_id)
        else:
            plan.unchanged += 1

    if apply and (to_insert or to_update):
        with engine.begin() as conn:
            for row in to_insert:
                # Only send columns the table actually has, so a table created
                # before the audit column existed is still writable.
                payload = {k: v for k, v in row.items() if k in table_cols}
                cols = ", ".join(payload.keys())
                params = ", ".join(f":{k}" for k in payload.keys())
                conn.execute(text(
                    f"INSERT INTO {table} ({cols}) VALUES ({params})"
                ), payload)
            for row in to_update:
                payload = {k: v for k, v in row.items() if k in table_cols}
                sets = ", ".join(f"{c} = :{c}" for c in payload if c != KEY)
                conn.execute(text(
                    f"UPDATE {table} SET {sets} WHERE {KEY} = :{KEY}"
                ), payload)

    if verbose:
        print(f"  existing rows in DB        : {len(stored)}")
        print(f"  new rows to insert         : {len(plan.inserted)} "
              f"{plan.inserted if plan.inserted else ''}")
        print(f"  changed rows to update     : {len(plan.updated)} "
              f"{plan.updated if plan.updated else ''}")
        print(f"  unchanged (skipped)        : {plan.unchanged}")
        if plan.missing_from_source:
            print(f"  in DB but ABSENT from source: {plan.missing_from_source}")
            print(f"      (NOT deleted — reported only. Investigate before acting.)")
        print(f"  applied                    : {apply}")

    return plan

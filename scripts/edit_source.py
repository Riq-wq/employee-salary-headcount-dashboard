#!/usr/bin/env python3
"""
Open the source CSV in Excel, safely, so the round trip cannot corrupt it.

Why this exists
---------------
The source file (``data/employee dataset.csv``) is a CSV, and the natural
thing to do with a CSV is open it in Excel and edit it there. That instinct
is reasonable - and it contains a trap that the pipeline's checks cannot see.

**Excel reads dates in ITS OWN locale, not the file's.** The file's convention
is day-first (``dd/mm/yyyy``), because that is what the PDF report parses
(``%d/%m/%Y``). Excel on this machine is set to month-first. So:

    you type        Excel reads it as        the file ends up with
    --------------  ----------------------   -------------------------
    01/06/2025      6 January 2025           06/01/2025   <- five months out
    15/06/2025      15 June 2025            15/06/2025   <- fine (day > 12)

Excel imported the existing dates correctly (it applies the file's own
``dd/mm/yyyy`` display format to them), so a plain open-and-save looks
perfectly fine. The corruption only happens to a date you TYPE, and only when
both halves of it are 12 or lower - which is exactly the case for a new hire
joining on, say, 01/06/2025.

The result is a join date that is silently five months wrong, in the
database, in the PDF report and in the dashboard. The gate cannot catch it,
because ``06/01/2025`` is a perfectly valid day-first date.

**This script removes the trap at the point of entry.** Before you type
anything it:

* turns the ``JoinDate`` column into TEXT cells, so Excel cannot reinterpret
  a date you type - it is saved exactly as typed;
* converts any date that Excel had already turned into a date serial back
  into literal ``dd/mm/yyyy`` text (this repairs the damage a previous plain
  Excel save can do);
* pins the numeric columns to a plain integer format, so a large salary can
  never come out as ``1.2E+06``;
* turns off Excel's autocorrect and autocomplete for the session, so it
  cannot silently change your capitalisation or complete a city name.

What it does
------------
1. Backs up the source file.
2. Opens it in Excel, made safe as above.
3. Waits for you to edit, save (Ctrl+S) and close.
4. Verifies the file: columns, row count, and the date format.
5. Restores the backup and tells you what went wrong, if anything did.
6. Prints exactly what changed.

It never changes your data. It only guarantees the file you get back is still
a valid source file, and tells you what changed.

Usage
-----
    python scripts/edit_source.py          # open it safely and wait
    python scripts/edit_source.py --check  # just validate the file, no Excel

Then: edit, press Ctrl+S, close Excel. The next scheduled run (06:00) picks
it up. To see the result immediately:

    python scripts/pipeline.py
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

SOURCE = ROOT / "data" / "employee dataset.csv"
BACKUP_DIR = ROOT / "data" / ".edit_backup"

REQUIRED_COLUMNS = ["EmployeeID", "Name", "Age", "City", "Salary", "JoinDate"]
DATE_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")
SERIAL_PATTERN = re.compile(r"^\d{5,6}$")

# Excel constants
XL_UP = -4162
XL_CSV = 6          # xlCSV - "CSV (Comma delimited)"
TEXT_FORMAT = "@"   # Excel's Text number format
INTEGER_FORMAT = "0"

# Excel counts days from 1899-12-30 (the 1900 date system).
EXCEL_EPOCH = datetime(1899, 12, 30)
EXCEL_EPOCH_1904 = datetime(1904, 1, 1)


# --------------------------------------------------------------------------
# Reading and validating the source file
# --------------------------------------------------------------------------
def read_source(path: Path) -> list[dict]:
    """Read the source CSV into a list of dicts, with a header check."""
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        rows = [dict(r) for r in reader]

    if header != REQUIRED_COLUMNS:
        raise ValueError(f"expected columns {REQUIRED_COLUMNS}, found {header}")
    return rows


def bad_dates(rows: list[dict]) -> list[str]:
    """JoinDate values that are not ``dd/mm/yyyy``, with their row numbers."""
    bad = []
    for i, row in enumerate(rows, start=2):     # +2: the header is line 1
        value = (row.get("JoinDate") or "").strip()
        if not DATE_PATTERN.match(value):
            bad.append(f"row {i}: {value!r}")
            continue
        try:
            datetime.strptime(value, "%d/%m/%Y")
        except ValueError:
            bad.append(f"row {i}: {value!r} (not a real date)")
    return bad


def summarise(before: list[dict], after: list[dict]) -> list[str]:
    """A short, human summary of what changed between two versions."""
    lines = []

    def key(row: dict) -> tuple:
        return (row.get("EmployeeID", ""), row.get("Name", ""))

    before_keys = {key(r) for r in before}
    after_keys = {key(r) for r in after}

    added = after_keys - before_keys
    removed = before_keys - after_keys
    if added:
        lines.append("added   : " + ", ".join(f"{i} {n}" for i, n in sorted(added)))
    if removed:
        lines.append("removed : " + ", ".join(f"{i} {n}" for i, n in sorted(removed)))

    before_by_id = {r["EmployeeID"]: r for r in before}
    for row in after:
        old = before_by_id.get(row["EmployeeID"])
        if old is None:
            continue
        for field in ("Name", "Age", "City", "Salary", "JoinDate"):
            if (old.get(field) or "") != (row.get(field) or ""):
                lines.append(
                    f"changed : {row['EmployeeID']} {row['Name']}: "
                    f"{field} {old.get(field)!r} -> {row.get(field)!r}"
                )
    return lines


# --------------------------------------------------------------------------
# Excel
# --------------------------------------------------------------------------
def to_day_first(value, date1904: bool = False) -> str:
    """Turn whatever Excel gave us into a literal ``dd/mm/yyyy`` string.

    Excel hands a date back as a *serial number* (the number of days since
    1899-12-30). A date that was already saved as text comes back as a
    string. Both are handled here, plus the "a previous save leaked a raw
    serial into the file" case, which is a numeric string.
    """
    epoch = EXCEL_EPOCH_1904 if date1904 else EXCEL_EPOCH

    if isinstance(value, (int, float)):
        return (epoch + timedelta(days=float(value))).strftime("%d/%m/%Y")

    text = str(value).strip()
    if SERIAL_PATTERN.match(text):
        # A raw serial that a previous plain Excel save left in the file.
        return (epoch + timedelta(days=float(text))).strftime("%d/%m/%Y")

    return text


def prepare_workbook(path: Path, xl) -> tuple[object, int]:
    """Open the CSV in Excel and make it safe to type into.

    Returns the workbook and the number of date cells that had to be
    repaired (a raw Excel serial found in the file).
    """
    wb = xl.Workbooks.Open(str(path))
    ws = wb.Worksheets(1)

    # --- find the columns we care about ----------------------------------
    headers = {}
    for c in range(1, 60):
        value = ws.Cells(1, c).Value2
        if value is None:
            break
        headers[str(value).strip()] = c

    missing = [h for h in REQUIRED_COLUMNS if h not in headers]
    if missing:
        raise ValueError(f"the file is missing the column(s) {missing}")

    date_col = headers["JoinDate"]

    # --- read the dates BEFORE touching the formatting --------------------
    # Excel has already turned the file's dates into serial numbers by the
    # time we get here, so this is where the true values are recovered.
    date1904 = bool(wb.Date1904)
    last_row = ws.Cells(ws.Rows.Count, date_col).End(XL_UP).Row
    current = []
    for r in range(2, last_row + 1):
        current.append((r, ws.Cells(r, date_col).Value2))

    # --- make the date column TEXT ---------------------------------------
    # A Text cell cannot be reinterpreted by Excel: whatever is typed into it
    # is saved exactly as typed.
    ws.Columns(date_col).NumberFormat = TEXT_FORMAT

    # --- pin the numeric columns to plain integers ------------------------
    # Stops a big salary coming out as 1.2E+06 or 55,000.
    for name in ("EmployeeID", "Age", "Salary"):
        ws.Columns(headers[name]).NumberFormat = INTEGER_FORMAT

    # --- write the dates back as literal text -----------------------------
    repaired = 0
    for r, value in current:
        text = to_day_first(value, date1904)
        if str(value).strip() != text and SERIAL_PATTERN.match(str(value).strip()):
            repaired += 1
        ws.Cells(r, date_col).Value = text

    # --- verify Excel really did what we asked ----------------------------
    for r, _ in current:
        got = ws.Cells(r, date_col).Value2
        if not isinstance(got, str):
            raise RuntimeError(
                f"row {r}: the JoinDate cell is still a date, not text. "
                f"Excel did not accept the Text format."
            )

    # Put the cursor where a new hire goes, so it is obvious where to type.
    ws.Activate()
    ws.Cells(last_row + 1, 1).Select()

    return wb, repaired


def disable_autocorrect(xl) -> dict:
    """Stop Excel from 'helpfully' changing what is typed.

    Excel's autocorrect capitalises the first letter of a cell, and its
    autocomplete completes a city name you have typed before. Neither is
    welcome in a data file. The original settings are returned so they can be
    put back when the session ends.
    """
    saved = {}
    for name in ("CapitalizeFirstLetterOfSentences",
                 "ReplaceText",
                 "AutoExpandListEntries"):
        try:
            saved[name] = getattr(xl.AutoCorrect, name)
            setattr(xl.AutoCorrect, name, False)
        except Exception:
            pass
    return saved


def restore_autocorrect(xl, saved: dict) -> None:
    for name, value in saved.items():
        try:
            setattr(xl.AutoCorrect, name, value)
        except Exception:
            pass


def wait_until_closed(wb) -> None:
    """Block until the workbook is closed (or Excel goes away entirely)."""
    while True:
        time.sleep(1)
        try:
            # Check if workbook is still accessible (accessing any property will
            # raise an exception if the workbook is closed)
            _ = wb.Name
        except Exception:
            return


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def report_problems(problems: list[str], backup: Path) -> int:
    print("FAILED:")
    for problem in problems:
        print(f"  - {problem}")
    print()
    print("The backup has been restored, so nothing was lost.")
    print(f"Backup: {backup.relative_to(ROOT)}")
    print()
    print("If you typed a date, the most likely cause is that the column was")
    print("not formatted as Text at the moment you typed. Run this script")
    print("again and let it set the format for you before you type.")
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="validate the source file without opening Excel")
    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"Source file not found: {SOURCE}")
        return 4

    try:
        before = read_source(SOURCE)
    except Exception as exc:
        print(f"The source file cannot be read: {exc}")
        return 4

    print(f"Source: {SOURCE.relative_to(ROOT)}  ({len(before)} rows)")
    print()

    # --check: just report on the file as it stands.
    if args.check:
        bad = bad_dates(before)
        if bad:
            print(f"FAILED: {len(bad)} date(s) are not dd/mm/yyyy:")
            for item in bad:
                print(f"  - {item}")
            return 2
        print("OK - every date is dd/mm/yyyy and the columns are correct.")
        return 0

    try:
        import win32com.client as win32
    except ImportError:
        print("pywin32 is not installed, so Excel cannot be driven from here.")
        print("Either install it (pip install pywin32), or open the file")
        print("manually and format the JoinDate column as Text before you")
        print("type into it.")
        return 4

    # Back it up, so a bad save can be undone.
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"employee dataset {datetime.now():%Y-%m-%d %H%M%S}.csv"
    shutil.copy2(SOURCE, backup)
    print(f"Backup : {backup.relative_to(ROOT)}")
    print()

    print("Opening Excel...")
    xl = win32.Dispatch("Excel.Application")
    xl.Visible = True
    xl.DisplayAlerts = False
    saved_autocorrect = disable_autocorrect(xl)

    try:
        wb, repaired = prepare_workbook(SOURCE, xl)
    except Exception as exc:
        restore_autocorrect(xl, saved_autocorrect)
        try:
            xl.Quit()
        except Exception:
            pass
        print(f"FAILED: could not open the file safely ({exc}).")
        print("Nothing was changed.")
        return 4

    if repaired:
        print(f"Repaired {repaired} date(s) that a previous save had left as")
        print("raw Excel serial numbers.")

    print()
    print("  Excel is open and ready to edit.")
    print("  The JoinDate column is TEXT, so a date is saved exactly as you")
    print("  type it (dd/mm/yyyy - day first, like the rest of the file).")
    print()
    print("  Edit, press Ctrl+S, then close Excel. This script will verify")
    print("  the file and tell you what changed.")
    print()

    wait_until_closed(wb)

    # Put Excel's own settings back before letting go of the application.
    restore_autocorrect(xl, saved_autocorrect)
    try:
        xl.Quit()
    except Exception:
        pass

    print("Verifying the file...")
    print()

    # The file must still be a valid source file.
    try:
        after = read_source(SOURCE)
    except Exception as exc:
        shutil.copy2(backup, SOURCE)
        return report_problems(
            [f"the file is no longer a valid source file ({exc})"], backup)

    problems = []
    if len(after) != len(before):
        problems.append(
            f"row count changed from {len(before)} to {len(after)} "
            f"(fine if you added or removed someone, but check it)"
        )
    bad = bad_dates(after)
    if bad:
        problems.append(
            f"{len(bad)} date(s) are not dd/mm/yyyy: " + "; ".join(bad[:5])
        )

    if problems:
        shutil.copy2(backup, SOURCE)
        return report_problems(problems, backup)

    print("OK - the file is a valid source file.")
    print()
    changes = summarise(before, after)
    if changes:
        print("What changed:")
        for line in changes:
            print(f"  {line}")
    else:
        print("  (nothing changed)")
    print()
    print("The next scheduled run (06:00) will pick this up.")
    print("To see the result now, run:  python scripts/pipeline.py")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

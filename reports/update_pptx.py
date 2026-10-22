#!/usr/bin/env python3
"""Update PPTX from cleaned CSV data."""

from __future__ import annotations

import copy
import pathlib
import statistics
from collections import defaultdict
from datetime import datetime

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.util import Inches

# Paths
ROOT = pathlib.Path(__file__).resolve().parent.parent
PPTX_PATH = ROOT / "reports" / "Employee Salary & Headcount Dashboard.pptx"
RAW_CSV = ROOT / "data" / "employee dataset.csv"
CLEAN_CSV = ROOT / "data" / "employee_dataset_cleaned.csv"


def load_csv(path: pathlib.Path):
    import csv
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _shape_by_id(slide, shape_id):
    for sh in slide.shapes:
        if sh.shape_id == shape_id:
            return sh
    raise SystemExit(f"shape {shape_id} not found")


def _set_run(slide, shape_id, run_idx, new: str):
    sh = _shape_by_id(slide, shape_id)
    if not sh.has_text_frame:
        return
    runs = [r for p in sh.text_frame.paragraphs for r in p.runs]
    if run_idx < len(runs):
        runs[run_idx].text = str(new)


def _set_cell(cell, text: str):
    paras = cell.text_frame.paragraphs
    if len(paras) != 1 or len(paras[0].runs) != 1:
        return
    paras[0].runs[0].text = str(text)


def _city_rollup(rows):
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["City"]].append(int(r["Salary"]))
    return sorted(
        ((city, len(vals), statistics.mean(vals)) for city, vals in grouped.items()),
        key=lambda t: (-t[1], t[0]),
    )


def update_pptx(clean_rows: list[dict] | None = None) -> None:
    raw = load_csv(RAW_CSV)
    clean = load_csv(CLEAN_CSV)
    for r in clean:
        r["Salary"] = int(r["Salary"])
        r["Age"] = int(r["Age"])

    salaries = [r["Salary"] for r in clean]
    total = sum(salaries)
    mean = total / len(salaries)
    median_sal = statistics.median(salaries)
    rollup = _city_rollup(clean)

    # Raw mean
    raw_salaries = [int(r["Salary"]) for r in raw if r["Salary"].strip().isdigit()]
    raw_mean = statistics.mean(raw_salaries) if raw_salaries else 0
    inflation = (raw_mean - mean) / mean * 100 if mean else 0

    # Diana's city
    diana_id = next(r["EmployeeID"] for r in clean if r["Name"] == "Diana")
    kisumu_rows = [r for r in clean if r["City"] == "Kisumu"]
    kisumu_with = statistics.mean(r["Salary"] for r in kisumu_rows)
    kisumu_without = statistics.mean(r["Salary"] for r in kisumu_rows if r["EmployeeID"] != diana_id)

    # Ranked
    ranked = sorted(clean, key=lambda r: r["Salary"], reverse=True)

    prs = Presentation(PPTX_PATH)
    slides = list(prs.slides)

    # Helper
    def sr(slide_idx, shape_id, run_idx, new):
        _set_run(slides[slide_idx], shape_id, run_idx, str(new))

    def sc(slide_idx, shape_id, row, col, text):
        tbl = _shape_by_id(slides[slide_idx], shape_id).table
        _set_cell(tbl.rows[row].cells[col], str(text))

    # ---- Slide 3 (index 3): employee count ----
    sr(3, 33, 0, f"{len(clean)} employees")

    # ---- Slide 5 (index 5): defects table (TABLE 10x3) ----
    sr(5, 7, 0, f"{len(clean)} employees")  # shape 7
    sc(5, 7, 3, 2, "Filled with median age (29)")
    sc(5, 7, 4, 2, "Reset to missing, re-filled with median (29)")
    sc(5, 7, 5, 2, "Filled with median salary (59,500)")

    # ---- Slide 6 (index 6): 88% Finding ----
    sr(6, 7, 0, f"The {inflation:.0f}% Finding")  # shape 7
    sr(6, 8, 1, f"KES {raw_mean:,.0f}")  # shape 8
    sr(6, 8, 3, f"KES {mean:,.0f}")  # shape 8
    sr(6, 8, 5, f"inflation of {inflation:.0f}%")  # shape 8
    sr(6, 12, 4, f"KES {kisumu_with:,.0f}")  # shape 12
    sr(6, 12, 6, f"KES {kisumu_without:,.0f}")  # shape 12
    sr(6, 20, 3, f"{len(clean) - 1} of {len(clean)}")  # shape 20
    sr(6, 20, 4, f" employees in the city view. Total, mean, median, the {inflation:.0f}% finding and the distribution analysis stay ")

    # ---- Slide 8 (index 8): KPIs ----
    sr(8, 8, 0, str(len(clean)))  # Total Employees
    sr(8, 12, 0, f"KES {total:,}")  # Total Salary Expense
    sr(8, 16, 0, f"KES {mean:,.0f}")  # Average Salary
    sr(8, 20, 0, f"{sum(r['Age'] for r in clean) / len(clean):.1f}")  # Average Age

    # City total salary chart
    city_total = CategoryChartData()
    city_total.categories = [c for c, _, _ in _city_rollup(load_csv(CLEAN_CSV))]
    city_total.add_series("Total Salary (KES)", tuple(int(n * a) for _, n, a in _city_rollup(load_csv(CLEAN_CSV))))
    _shape_by_id(slides[8], 22).chart.replace_data(city_total)

    # ---- Slide 10 (index 10): City avg chart + insight ----
    rollup = _city_rollup(load_csv(CLEAN_CSV))
    sr(10, 9, 0, rollup[0][0])  # leading city
    sr(10, 9, 2, f"KES {rollup[0][2]:,.0f}")  # leading avg
    sr(10, 9, 3, f", with {rollup[1][0]} close behind at KES {rollup[1][2]:,.0f} \u2014 a figure carried by a single senior hire.")

    # City average chart
    city_avg = CategoryChartData()
    city_avg.categories = [c for c, _, _ in rollup]
    city_avg.add_series("Average Salary (KES)", tuple(int(a) for _, _, a in rollup))
    _shape_by_id(slides[10], 5).chart.replace_data(city_avg)

    # ---- Slide 11 (index 11): Ranking table ----
    tbl = _shape_by_id(slides[11], 12).table
    # Add rows if needed
    while len(tbl.rows) - 1 < len(ranked):
        trs = tbl._tbl.findall(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}tr"
        )
        template = trs[-1]
        new_tr = copy.deepcopy(template)
        template.addnext(new_tr)

    for i, r in enumerate(ranked, 1):
        delta = (r["Salary"] - mean) / mean * 100
        sc(11, 12, i, 0, str(i))
        sc(11, 12, i, 1, r["Name"])
        sc(11, 12, i, 2, r["City"])
        sc(11, 12, i, 3, f"{r['Salary']:,}")
        sc(11, 12, i, 4, f"{(r['Salary'] - mean) / mean * 100:+.1f}%")

    # ---- Slide 13 (index 13): Charts ----
    # Headcount doughnut
    hc = CategoryChartData()
    hc.categories = [c for c, _, _ in rollup]
    hc.add_series("count", tuple(n for _, n, _ in rollup))
    _shape_by_id(slides[13], 6).chart.replace_data(hc)

    # Hiring trend
    hires = defaultdict(int)
    for r in clean:
        m = datetime.strptime(r["JoinDate"], "%d/%m/%Y").strftime("%b")
        hires[m] += 1
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    hire_counts = [hires.get(m, 0) for m in months]
    active = [(m, c) for m, c in zip(months, hire_counts) if c > 0]
    ht = CategoryChartData()
    ht.categories = [m for m, _ in active]
    ht.add_series("New Hires", tuple(c for _, c in active))
    _shape_by_id(slides[13], 8).chart.replace_data(ht)

    # Headcount doughnut
    hc = CategoryChartData()
    hc.categories = [c for c, _, _ in rollup]
    hc.add_series("count", tuple(n for _, n, _ in rollup))
    _shape_by_id(slides[13], 6).chart.replace_data(hc)

    # Text on slide 14 (index 13)
    sr(13, 11, 2, "one hire in January, two a month from February to April, and four in May")
    sr(13, 11, 3, ". Kisumu has the largest team (4 employees, one of them an assumed city), with Nairobi next on 3 and Mombasa on 2.")

    # ---- Slide 14 (index 14): Insights ----
    top_city, low_city = rollup[0][0], rollup[-1][0]
    top_avg, low_avg = rollup[0][2], rollup[-1][2]
    gap_pct = int(top_avg / low_avg * 100 - 100)

    sr(14, 8, 0, top_city)
    sr(14, 8, 2, f"KES {top_avg:,.0f}")
    sr(14, 8, 3, f", and {rollup[1][0]} close behind at KES {rollup[1][2]:,.0f} \u2014 a figure carried by a single senior hire.")
    sr(14, 8, 8, f"{gap_pct}% gap")

    sr(14, 12, 3, " (one of the assumed city). Remove Diana and it ties Nairobi on 3; Mombasa has ")
    sr(14, 12, 4, "2")
    sr(14, 12, 5, ", Eldoret and Nakuru ")
    sr(14, 14, 6, "1 each")

    sr(14, 16, 1, "one hire in January, two a month from February to April, and four in May")

    sr(14, 20, 1, f"KES {total:,}")
    sr(14, 20, 3, f"KES {mean:,.0f}")
    sr(14, 20, 4, f" per employee. Payroll ramped from KES 55,000 in January to KES {total:,} by May as headcount grew from 1 to {len(clean)}.")

    # Table geometry
    from pptx.util import Inches
    # slide 6 table
    tbl6 = _shape_by_id(slides[5], 7).table
    for i, row in enumerate(tbl6.rows):
        row.height = Inches(0.72 if i == 0 else 0.77)
    _shape_by_id(slides[5], 7).height = Inches(0.72 + 9 * 0.77)
    _shape_by_id(slides[5], 7).top = Inches(1.55)

    # slide 11 (ranking) table
    tbl = _shape_by_id(slides[11], 12).table
    for i, row in enumerate(tbl.rows):
        row.height = Inches(0.694 if i == 0 else 0.565)
    _shape_by_id(slides[11], 12).height = Inches(0.694 + len(clean) * 0.565)
    _shape_by_id(slides[11], 12).top = Inches(1.95)

    prs.save(PPTX_PATH)
    print("PPTX updated successfully")


if __name__ == "__main__":
    update_pptx()
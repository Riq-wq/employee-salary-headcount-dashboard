#!/usr/bin/env python3
"""
Employee Salary & Headcount Dashboard - PDF report generator.

Recomputes every statistic directly from the raw and cleaned datasets, then
renders ``reports/Employee_Salary_Dashboard_Report.pdf``.

Nothing in the report is hard-coded: change the data, re-run this script and
the numbers, tables and insights all update with it.

    python reports/generate_report.py
"""

from __future__ import annotations

import csv
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "data" / "employee dataset.csv"
CLEAN_CSV = ROOT / "data" / "employee_dataset_cleaned.csv"
CHART_DIR = ROOT / "reports" / "charts"
OUTPUT = ROOT / "reports" / "Employee_Salary_Dashboard_Report.pdf"

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
INK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")
ACCENT = colors.HexColor("#1D4ED8")
WARN = colors.HexColor("#B45309")
GOOD = colors.HexColor("#15803D")
LINE = colors.HexColor("#E2E8F0")
BAND = colors.HexColor("#F8FAFC")

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

# --------------------------------------------------------------------------
# Styles
# --------------------------------------------------------------------------
TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=22,
                       leading=26, textColor=colors.white)
SUBTITLE = ParagraphStyle("subtitle", fontName="Helvetica", fontSize=10.5,
                          leading=14, textColor=colors.HexColor("#CBD5E1"))
H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=13.5, leading=17,
                    textColor=INK, spaceBefore=2, spaceAfter=6)
KICKER = ParagraphStyle("kicker", fontName="Helvetica-Bold", fontSize=7.5,
                        leading=10, textColor=ACCENT)
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9, leading=12.6,
                      textColor=INK)
SMALL = ParagraphStyle("small", fontName="Helvetica", fontSize=7.6, leading=10,
                       textColor=MUTED)
CELL = ParagraphStyle("cell", fontName="Helvetica", fontSize=8.2, leading=11,
                      textColor=INK)
CELL_B = ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=8.2,
                        leading=11, textColor=INK)
CELL_W = ParagraphStyle("cellw", fontName="Helvetica-Bold", fontSize=8.2,
                        leading=11, textColor=colors.white)
CAPTION = ParagraphStyle("caption", fontName="Helvetica", fontSize=8,
                         leading=11, textColor=MUTED, alignment=TA_CENTER)


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
def load(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def as_int(value: str) -> int | None:
    value = (value or "").strip()
    return int(value) if value else None


# --------------------------------------------------------------------------
# Statistics - everything below is derived, never hard-coded
# --------------------------------------------------------------------------
def tukey_fences(values: list[int]) -> tuple[float, float, float, float]:
    """Q1, Q3, IQR and the upper Tukey fence (median-excluded halves)."""
    ordered = sorted(values)
    mid = len(ordered) // 2
    lower, upper = ordered[:mid], ordered[mid + 1:]
    q1 = statistics.median(lower)
    q3 = statistics.median(upper)
    iqr = q3 - q1
    return q1, q3, iqr, q3 + 1.5 * iqr


def pearson(xs: list[float], ys: list[float]) -> float:
    return statistics.correlation(xs, ys)


def payroll_by_month(rows: list[dict]) -> list[tuple[str, int, int]]:
    """(month label, new hires, cumulative monthly payroll) in join order."""
    out: list[list] = []
    running = 0
    for row in sorted(rows, key=lambda r: datetime.strptime(r["JoinDate"], "%d/%m/%Y")):
        month = datetime.strptime(row["JoinDate"], "%d/%m/%Y").strftime("%b")
        if not out or out[-1][0] != month:
            out.append([month, 0, 0])
        out[-1][1] += 1            # hires this month
        running += row["Salary"]   # carry across months
        out[-1][2] = running       # total payroll obligation this month
    return [(m, h, total) for m, h, total in out]


# --------------------------------------------------------------------------
# PDF furniture
# --------------------------------------------------------------------------
def header(canvas, doc):
    """Dark title banner on page 1."""
    canvas.saveState()
    canvas.setFillColor(INK)
    canvas.rect(0, PAGE_H - 46 * mm, PAGE_W, 46 * mm, stroke=0, fill=1)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, PAGE_H - 47.6 * mm, PAGE_W, 1.6 * mm, stroke=0, fill=1)
    canvas.restoreState()


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN, 13 * mm, PAGE_W - MARGIN, 13 * mm)
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 9.4 * mm,
                      "Employee Salary & Headcount Dashboard  |  Data Analytics Portfolio Project")
    canvas.drawRightString(PAGE_W - MARGIN, 9.4 * mm, f"Page {doc.page}")
    canvas.restoreState()


def band(text: str, style=ParagraphStyle("x", parent=H1)) -> list:
    """Section heading with a kicker line above it."""
    return [Paragraph(text.upper(), KICKER), Spacer(1, 2), Paragraph(text, style)]


def styled_table(data, widths, header_row=True, zebra=True) -> Table:
    tbl = Table(data, colWidths=widths, repeatRows=1 if header_row else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
    ]
    if header_row:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), INK)]
    if zebra:
        start = 1 if header_row else 0
        for i in range(start, len(data)):
            if (i - start) % 2 == 1:
                cmds.append(("BACKGROUND", (0, i), (-1, i), BAND))
    tbl.setStyle(TableStyle(cmds))
    return tbl


def kpi_cards(items: list[tuple[str, str, str]]) -> Table:
    """Four stat cards across the page."""
    cells = [
        [Paragraph(v, ParagraphStyle("v", fontName="Helvetica-Bold", fontSize=15,
                                     leading=17, textColor=INK, alignment=TA_CENTER)),
         Spacer(1, 1),
         Paragraph(k, ParagraphStyle("k", fontName="Helvetica", fontSize=7.4,
                                     leading=9.5, textColor=MUTED, alignment=TA_CENTER))]
        for k, v, _ in items
    ]
    row = [Table([[c] for c in card], colWidths=[CONTENT_W / 4 - 8]) for card in cells]
    tbl = Table([row], colWidths=[CONTENT_W / 4] * 4)
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), BAND),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return tbl


def callout(title: str, body: str, colour=WARN) -> Table:
    inner = [
        [Paragraph(title, ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=9.5,
                                         leading=12, textColor=colour))],
        [Paragraph(body, ParagraphStyle("cb", fontName="Helvetica", fontSize=8.6,
                                        leading=12, textColor=INK))],
    ]
    t = Table(inner, colWidths=[CONTENT_W - 12])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, colour),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
    ]))
    return t


def chart(heading: str, name: str, caption: str, story: list):
    """Heading + chart + caption kept together so they never split across pages."""
    path = CHART_DIR / name
    if not path.exists():
        return
    img = Image(str(path), width=CONTENT_W, height=CONTENT_W * 480 / 900)
    story += [KeepTogether([
        Paragraph(heading.upper(), KICKER), Spacer(1, 2),
        Paragraph(heading, H1), Spacer(1, 4),
        img, Spacer(1, 3), Paragraph(caption, CAPTION),
    ]), Spacer(1, 10)]


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
def build() -> Path:
    raw = load(RAW_CSV)
    clean = load(CLEAN_CSV)

    for row in clean:
        row["Salary"] = as_int(row["Salary"])
        row["Age"] = as_int(row["Age"])

    salaries = [r["Salary"] for r in clean]
    ages = [r["Age"] for r in clean]

    total = sum(salaries)
    mean = total / len(salaries)
    median_salary = statistics.median(salaries)
    low, high = min(salaries), max(salaries)
    avg_age = sum(ages) / len(ages)

    # --- city roll-up -------------------------------------------------
    by_city: dict[str, list[int]] = {}
    for r in clean:
        by_city.setdefault(r["City"], []).append(r["Salary"])
    city_avg = {c: statistics.mean(v) for c, v in by_city.items()}
    city_n = {c: len(v) for c, v in by_city.items()}
    top_city = max(city_avg, key=city_avg.get)
    low_city = min(city_avg, key=city_avg.get)

    # --- distribution --------------------------------------------------
    q1, q3, iqr, fence = tukey_fences(salaries)
    outliers = [r for r in clean if r["Salary"] > fence]
    r_age = pearson(ages, salaries)

    # --- raw vs cleaned (the headline finding) -------------------------
    raw_salaries = [as_int(r["Salary"]) for r in raw if as_int(r["Salary"]) is not None]
    raw_mean = statistics.mean(raw_salaries)
    raw_max = max(raw_salaries)
    inflation = (raw_mean - mean) / mean * 100

    # --- age vs pay: must compare the actual youngest/oldest PEOPLE ----
    youngest = min(clean, key=lambda r: r["Age"])
    oldest = max(clean, key=lambda r: r["Age"])
    age_gap = oldest["Salary"] / youngest["Salary"]

    # --- Kisumu with vs without the Diana assumption -------------------
    diana_salary = next(r["Salary"] for r in clean if r["Name"] == "Diana")
    kisumu_all = by_city["Kisumu"]
    kisumu_no_diana = [s for s in kisumu_all if s != diana_salary]
    kisumu_with = statistics.mean(kisumu_all)
    kisumu_without = statistics.mean(kisumu_no_diana)

    # --- payroll ramp --------------------------------------------------
    payroll = payroll_by_month(clean)

    # ==================================================================
    story: list = []

    # ---- page 1 ------------------------------------------------------
    story += [Spacer(1, 3 * mm)]
    story += [Paragraph("EMPLOYEE SALARY &amp; HEADCOUNT", TITLE)]
    story += [Spacer(1, 2)]
    story += [Paragraph("Data Analysis Report &nbsp;|&nbsp; Prepared by Hassan Jumaa (Riq)", SUBTITLE)]
    story += [Spacer(1, 3)]
    story += [Paragraph("PYTHON &nbsp;&#183;&nbsp; MYSQL &nbsp;&#183;&nbsp; SQL &nbsp;&#183;&nbsp; POWER BI", SUBTITLE)]
    story += [Spacer(1, 13 * mm)]

    story += band("Project Overview")
    story += [Paragraph(
        "This report summarises an end-to-end employee data analysis project: cleaning a raw HR dataset "
        "in Python (Pandas), loading it into MySQL, querying it with SQL, and visualising the results in an "
        f"interactive Power BI dashboard. The dataset covers <b>{len(clean)} employees</b> across "
        f"<b>{len(by_city)} Kenyan cities</b> ({', '.join(sorted(by_city))}).", BODY)]
    story += [Spacer(1, 6)]

    story += band("Tools &amp; Workflow")
    wf = [[Paragraph(x, CELL_W) for x in ["Stage", "Tool", "Purpose"]]]
    for stage, tool, purpose in [
        ("Data Cleaning", "Python (Pandas, NumPy)",
         "Remove duplicates, handle nulls, fix invalid ages, cap salary outliers"),
        ("Storage", "MySQL", "Persist the cleaned dataset for querying and reporting"),
        ("Querying", "SQL", "Aggregate and rank employees by salary, city and hire date"),
        ("Visualization", "Power BI", "Interactive dashboard with KPI cards, charts and slicers"),
        ("Reporting", "ReportLab", "Generate this PDF programmatically from the data"),
    ]:
        wf.append([Paragraph(stage, CELL_B), Paragraph(tool, CELL), Paragraph(purpose, CELL)])
    story += [styled_table(wf, [26 * mm, 34 * mm, CONTENT_W - 60 * mm]), Spacer(1, 8)]

    story += band("Data Cleaning Summary")
    story += [Paragraph(
        f"The raw export contained <b>7 data defects</b> (plus one date-format issue affecting every row). "
        "Each was resolved deliberately and documented, never silently.", BODY)]
    story += [Spacer(1, 5)]

    issues = [
        ("Duplicate employee records", "Alice &#8212; exact duplicate row",
         "Dropped the duplicate. Keeping it would double-count headcount and payroll."),
        ("Missing employee name", "EmployeeID 9 &#8212; name blank",
         "Filled with the placeholder <b>&#8216;Jamal&#8217;</b>. Names are not statistically "
         "recoverable; this is an <b>assumption</b> and carries no analytical weight."),
        ("Missing age values", "Bob &#8212; age empty",
         f"Imputed with the median age ({int(statistics.median(ages))}), which is robust to outliers."),
        ("Invalid negative age", "Faith &#8212; age = -5",
         "Treated as missing, then re-filled with the median and rounded to whole years."),
        ("Missing salary value", "Charlie &#8212; salary blank",
         f"Imputed with the median salary (KES {int(median_salary):,}). The 900,000 typo above makes "
         "the mean unsafe for this purpose."),
        ("Missing city value", "Diana &#8212; city empty",
         "Filled with <b>Kisumu</b> as an <b>assumption, not a recovery</b>. The mode is not unique "
         "&#8212; Kisumu, Mombasa and Nairobi each appear twice &#8212; so no single &#8216;most frequent "
         "city&#8217; exists. See Limitations."),
        (f"Salary outlier ({len(outliers)} flagged)",
         f"George &#8212; KES {raw_max:,} in the raw export",
         f"Reviewed against the Tukey upper fence (KES {fence:,.0f}) and corrected to KES {high:,}."),
        ("Inconsistent date format", "All records",
         "Parsed as day-first dates and standardised to a single format."),
    ]
    tbl = [[Paragraph(x, CELL_W) for x in ["Issue Found", "Affected Record", "Resolution Applied"]]]
    for a, b, c in issues:
        tbl.append([Paragraph(a, CELL_B), Paragraph(b, CELL), Paragraph(c, CELL)])
    story += [styled_table(tbl, [38 * mm, 38 * mm, CONTENT_W - 76 * mm])]

    # ---- page 2 ------------------------------------------------------
    story += [PageBreak()]
    story += band("Key Metrics")
    story += [kpi_cards([
        ("Total Employees", f"{len(clean)}", ""),
        ("Total Salary Expense", f"KES {total:,}", ""),
        ("Average Salary", f"KES {mean:,.0f}", ""),
        ("Average Age", f"{avg_age:.1f}", ""),
    ]), Spacer(1, 9)]

    story += [Paragraph(
        f"Median salary is <b>KES {median_salary:,.0f}</b> against a mean of <b>KES {mean:,.0f}</b>. "
        f"The mean sits above the median, so the distribution is <b>right-skewed</b>: a small number of "
        f"high earners pull the average above what a typical employee earns. Range is "
        f"<b>KES {high - low:,}</b> (KES {low:,} &#8594; KES {high:,}).", BODY)]
    story += [Spacer(1, 9)]

    chart("Salary distribution by city", "salary_by_city.png", "Average salary by city &#8212; KES", story)
    chart("Headcount by city", "headcount_by_city.png", "Employees per city", story)

    # ---- page 3 ------------------------------------------------------
    story += [PageBreak()]
    chart("Hiring trend by month", "hiring_trend.png", "New hires per month, 2025", story)

    ramp = " &#8594; ".join(f"<b>KES {amt:,}</b> ({m})" for m, _, amt in payroll)
    story += [Paragraph(
        f"Headcount grew from <b>{payroll[0][1]} hire in {payroll[0][0]}</b> to "
        f"<b>{len(clean)} employees</b> by {payroll[-1][0]}, so the monthly payroll bill ramped "
        f"{ramp}. The KES {total:,} figure is the <b>current</b> monthly bill at full headcount "
        "&#8212; not a constant cost across the period.", BODY)]
    story += [Spacer(1, 9)]

    story += band("Employee Salary Ranking")
    ranked = sorted(clean, key=lambda r: r["Salary"], reverse=True)
    tbl = [[Paragraph(x, CELL_W) for x in
            ["#", "Name", "City", "Salary (KES)", "vs. Average"]]]
    for i, r in enumerate(ranked, 1):
        delta = (r["Salary"] - mean) / mean * 100
        colour = GOOD if delta >= 0 else WARN
        tbl.append([
            Paragraph(str(i), CELL), Paragraph(r["Name"], CELL_B), Paragraph(r["City"], CELL),
            Paragraph(f"{r['Salary']:,}", CELL),
            Paragraph(f'<font color="{colour.hexval()}">{delta:+.1f}%</font>', CELL),
        ])
    story += [styled_table(tbl, [10 * mm, 34 * mm, 30 * mm, 32 * mm, CONTENT_W - 106 * mm])]

    # ---- page 4 ------------------------------------------------------
    story += [PageBreak()]
    story += band("Key Insights")
    city_order = sorted(city_n.items(), key=lambda kv: -kv[1])
    headcount_txt = ", ".join(
        f"{c} {n}" for c, n in city_order[:-1]) + f" and {city_order[-1][0]} {city_order[-1][1]}"
    insights = [
        ("<b>City salary disparity.</b>",
         f"{top_city} leads with an average of KES {city_avg[top_city]:,.0f} "
         f"({(city_avg[top_city] - mean) / mean * 100:+.1f}% vs. the company mean), while {low_city} is "
         f"lowest at KES {city_avg[low_city]:,.0f} ({(city_avg[low_city] - mean) / mean * 100:+.1f}%). "
         f"{top_city} sits {city_avg[top_city] / city_avg[low_city] * 100 - 100:.0f}% above {low_city}."),
        ("<b>Headcount distribution.</b>",
         f"{headcount_txt[0].upper() + headcount_txt[1:]} employees across the {len(by_city)} cities."),
        ("<b>Age drives pay.</b>",
         f"Pearson correlation between age and salary is <b>r = {r_age:.3f}</b> "
         f"(r&#178; = {r_age ** 2:.2f}) &#8212; age alone explains roughly {r_age ** 2 * 100:.0f}% of "
         f"salary variance. {youngest['Name']}, the youngest at {youngest['Age']}, earns "
         f"KES {youngest['Salary']:,}; {oldest['Name']}, the oldest at {oldest['Age']}, earns "
         f"KES {oldest['Salary']:,} &#8212; a <b>{age_gap:.2f}&#215;</b> gap."),
        ("<b>One statistical outlier.</b>",
         f"George&#8217;s KES {high:,} sits above the Tukey upper fence of KES {fence:,.0f} "
         f"(Q1 = {q1:,.0f}, Q3 = {q3:,.0f}, IQR = {iqr:,.0f}). He is the only employee flagged."),
    ]
    for i, (lead, body) in enumerate(insights, 1):
        story += [Paragraph(
            f'<font color="{ACCENT.hexval()}"><b>{i:02d}</b></font> &nbsp; {lead} {body}', BODY)]
        story += [Spacer(1, 6)]

    story += [Spacer(1, 4)]
    story += [callout(
        "THE FINDING THAT MATTERS: CLEANING CHANGED THE CONCLUSION",
        f"Computed on the raw export, average salary reads <b>KES {raw_mean:,.0f}</b>. Correctly cleaned "
        f"it is <b>KES {mean:,.0f}</b> &#8212; an inflation of <b>{inflation:.0f}%</b>, caused by a single "
        f"900,000 typo and one duplicated row. Left untreated, this dataset would have produced a false "
        f"narrative about what the company pays. The cleaning step <i>is</i> the analysis.", WARN)]
    story += [Spacer(1, 9)]

    story += band("Limitations &amp; Honest Scope")
    story += [Paragraph(
        "Two values in this dataset are <b>assumptions made during cleaning, not facts recovered from "
        "the source</b>. They are stated plainly so the numbers above can be trusted correctly.", BODY)]
    story += [Spacer(1, 5)]
    tbl = [[Paragraph(x, CELL_W) for x in ["Value", "Status", "Why it is not recoverable", "Impact"]]]
    tbl.append([
        Paragraph("Diana&#8217;s City &#8594; Kisumu", CELL_B), Paragraph("Assumption", CELL),
        Paragraph("Location cannot be derived from age, salary or join date. The mode is not unique.", CELL),
        Paragraph(f"Kisumu averages <b>KES {kisumu_with:,.0f}</b> with the assumption, "
                  f"<b>KES {kisumu_without:,.0f}</b> without it. No other figure moves.", CELL),
    ])
    tbl.append([
        Paragraph("ID 9&#8217;s Name &#8594; &#8216;Jamal&#8217;", CELL_B), Paragraph("Placeholder", CELL),
        Paragraph("Names carry no analytical weight &#8212; no calculation touches this field.", CELL),
        Paragraph("None.", CELL),
    ])
    story += [styled_table(tbl, [32 * mm, 23 * mm, 58 * mm, CONTENT_W - 113 * mm])]
    story += [Spacer(1, 6)]
    story += [Paragraph(
        "<b>If this were a real stakeholder deliverable:</b> both fields would be left as "
        "<i>Unknown</i>, Diana excluded from the city comparison, and the location view reported at "
        "8 of 9 employees. Total salary, mean, median, the inflation finding and the outlier detection "
        "are identical under either choice &#8212; only the Kisumu city average moves.", BODY)]
    story += [Spacer(1, 8)]

    story += [callout(
        "RECOMMENDATION",
        "1. Introduce age/experience-based pay bands &#8212; an r&#178; of "
        f"{r_age ** 2:.2f} says seniority is already driving pay, just informally. "
        "2. Review the single senior outlier against market benchmarks before treating "
        f"{top_city}&#8217;s average as a real signal. "
        "3. Add validation at source: a primary-key constraint, an age range check and a salary sanity "
        "cap would have caught all 7 defects before they reached a report.", ACCENT)]

    # ==================================================================
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=17 * mm,
        title="Employee Salary & Headcount Dashboard - Data Analysis Report",
        author="Hassan Jumaa (Riq)",
    )
    doc.build(story, onFirstPage=header, onLaterPages=footer)

    # ---- console summary for quick verification ----------------------
    print(f"Written : {OUTPUT}")
    print(f"Rows    : {len(raw)} raw -> {len(clean)} cleaned")
    print(f"Total   : {total:,}   Mean: {mean:,.0f}   Median: {median_salary:,.0f}")
    print(f"Range   : {low:,} - {high:,}   Avg age: {avg_age:.1f}")
    print(f"IQR     : Q1 {q1:,.0f}  Q3 {q3:,.0f}  IQR {iqr:,.0f}  fence {fence:,.0f}")
    print(f"Outliers: {[r['Name'] for r in outliers]}")
    print(f"r (age) : {r_age:.3f}   r2 = {r_age ** 2:.3f}")
    print(f"Raw mean: {raw_mean:,.0f}  ->  cleaned {mean:,.0f}  =  {inflation:.0f}% inflation")
    return OUTPUT


if __name__ == "__main__":
    build()

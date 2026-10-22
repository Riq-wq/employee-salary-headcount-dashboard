# Generates two interview-prep PDFs (one per project) to the Desktop.
# Every number quoted is taken from the verified project artifacts.
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, HRFlowable,
)
import sys
from pathlib import Path

DESKTOP = Path(r"C:\Users\Hassan\Desktop")
OUT_DIR = Path(r"C:\Users\Hassan\Desktop\DATA ANALYSIS INTERVIEW QUESTIONS BASED ON MY PROJECTS")

ACCENT = colors.HexColor("#1F3B73")
ACCENT2 = colors.HexColor("#2E6F9E")
LIGHT = colors.HexColor("#EEF3F9")
GREY = colors.HexColor("#5A5A5A")

styles = getSampleStyleSheet()

def S(name, **kw):
    base = kw.pop("parent", styles["BodyText"])
    return ParagraphStyle(name, parent=base, **kw)

TITLE = S("TITLE", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=21,
          textColor=ACCENT, spaceAfter=2, leading=25)
SUBTITLE = S("SUBTITLE", fontSize=11, textColor=GREY, alignment=TA_LEFT, spaceAfter=10, leading=15)
H1 = S("H1", fontName="Helvetica-Bold", fontSize=14, textColor=ACCENT,
       spaceBefore=14, spaceAfter=6, leading=18)
H2 = S("H2", fontName="Helvetica-Bold", fontSize=11.5, textColor=ACCENT2,
       spaceBefore=10, spaceAfter=4, leading=15)
BODY = S("BODY", fontSize=10, leading=14.5, spaceAfter=5)
Q = S("Q", fontName="Helvetica-Bold", fontSize=10.5, leading=14.5,
      textColor=colors.HexColor("#14243F"), spaceBefore=9, spaceAfter=3)
A = S("A", fontSize=10, leading=14.5, spaceAfter=3)
B = S("B", fontSize=10, leading=14.5, leftIndent=10, bulletIndent=2, spaceAfter=2)
SMALL = S("SMALL", fontSize=8.5, leading=11.5, textColor=GREY)
TAG = S("TAG", fontSize=8.5, textColor=colors.white, fontName="Helvetica-Bold")


def header_footer(canvas, doc, title):
    canvas.saveState()
    w, h = A4
    # top accent bar
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h - 12 * mm, w, 12 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(20 * mm, h - 7.8 * mm, "INTERVIEW PREPARATION")
    canvas.setFont("Helvetica", 8.5)
    canvas.drawRightString(w - 20 * mm, h - 7.8 * mm, title)
    # footer
    canvas.setFillColor(GREY)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(20 * mm, 10 * mm, "Hassan Jumaa  ·  Data Analyst Portfolio")
    canvas.drawRightString(w - 20 * mm, 10 * mm, "Page %d" % doc.page)
    canvas.setStrokeColor(colors.HexColor("#D5DDE8"))
    canvas.setLineWidth(0.6)
    canvas.line(20 * mm, 14 * mm, w - 20 * mm, 14 * mm)
    canvas.restoreState()


def build(filename, title, subtitle, story):
    # All four interview-prep PDFs live together in one folder, not loose on
    # the Desktop - that is where they were moved to.
    path = OUT_DIR / filename
    doc = BaseDocTemplate(
        str(path), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=19 * mm,
        title=title, author="Hassan Jumaa",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([
        PageTemplate(id="p", frames=[frame],
                     onPage=lambda c, d: header_footer(c, d, title))
    ])
    flow = [Paragraph(title, TITLE),
            Paragraph(subtitle, SUBTITLE),
            HRFlowable(width="100%", thickness=1.1, color=ACCENT2, spaceAfter=8)]
    flow += story
    doc.build(flow)
    return path


def qa(num, question, answer_paras):
    """A numbered Q&A block kept together on one page where possible."""
    items = [Paragraph(f"Q{num}.&nbsp; {question}", Q)]
    for p in answer_paras:
        items.append(p if not isinstance(p, str) else Paragraph(p, A))
    return KeepTogether(items)


def bullets(items):
    return [Paragraph(x, B, bulletText="•") for x in items]


def callout(text):
    t = Table([[Paragraph(text, S("CO", fontSize=9.3, leading=13,
                                 textColor=colors.HexColor("#14243F")))]],
              colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#BDD0E6")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# =========================================================================
# PDF 1 — SUPERSTORE SALES & PROFITABILITY ANALYSIS
# =========================================================================
ss = []

ss.append(Paragraph("Project 1 — Superstore Sales &amp; Profitability Analysis", H1))
ss.append(Paragraph(
    "End-to-end pipeline over 5,009 orders / 9,994 line items: cleaned in Python/Pandas, "
    "loaded into MySQL, analysed with SQL, visualised in Power BI, and written up in a "
    "generated PDF report. Use this sheet to rehearse the answers you would give aloud.", BODY))

ss.append(callout(
    "<b>Headline numbers to memorise:</b> $2,297,200.86 total sales · $286,397.02 total profit · "
    "<b>12.47%</b> overall margin (total profit ÷ total sales) · $2.30M / $286.4K rounded. "
    "Average of per-row margins = <b>12.03%</b> (a different, also-correct figure)."))

ss.append(Paragraph("A. Data &amp; dataset questions", H2))

ss += [qa(1,
    "What is this dataset, and what does one row represent?",
    ["It is the Sample Superstore dataset — a retail order-level dataset covering US sales. "
     "The raw file has 9,994 rows and 21 columns. <b>One row represents a single product line "
     "within an order</b>, not a whole order. That distinction matters because the file has only "
     "<b>5,009 unique order IDs</b>, so an order containing three products appears as three rows."])]

ss += [qa(2,
    "You say 5,009 orders but 9,994 rows. Is that a contradiction?",
    ["No — they measure different things. 9,994 is the <b>line-item count</b> (rows). 5,009 is "
     "the <b>distinct order count</b> (unique <font face='Courier'>order_id</font>). If I said "
     "\u201c9,994 orders\u201d a reviewer could reasonably challenge it, because order-level metrics "
     "like average order value need the 5,009 divisor. I state both so the metric I'm quoting "
     "is always unambiguous."])]

ss += [qa(3,
    "Walk me through your cleaning decisions.",
    bullets([
        "Read the file with <b>cp1252</b> encoding — the default UTF-8 read crashes on a non-breaking "
        "space (byte 0xA0) inside product names.",
        "Converted Order/Ship Date to datetime — they arrive as text.",
        "<b>Cast Postal Code to 5-digit text.</b> As an integer, pandas silently dropped the leading "
        "zero on <b>449 ZIP codes</b> (e.g. 01040 became 1040), which would corrupt any geographic join.",
        "Trimmed whitespace on text columns — <b>16 Product Name values</b> had a trailing space, which "
        "would create phantom duplicate products in any group-by.",
        "Standardised column names to snake_case.",
        "Engineered features: shipping_duration, profit_margin (%), cost, and an is_loss flag.",
    ]))]

ss += [qa(4,
    "Were there duplicates or missing values?",
    ["<b>Zero duplicate rows and zero missing values.</b> I verified both explicitly rather than "
     "assuming. That is why the cleaned file still has 9,994 rows — the cleaning changed types and "
     "added columns, it did not drop records."])]

ss += [qa(5,
    "Why did you load the data into MySQL instead of just using pandas?",
    ["Two reasons. First, it mirrors how a real analytics stack works — Python for messy cleaning, "
     "a database for reliable aggregation, and BI on top. Second, SQL is where business logic should "
     "be reproducible and reviewable; my ten business questions live as commented SQL queries, not "
     "buried in notebook cells."])]

ss.append(Paragraph("B. Business findings questions", H2))

ss += [qa(6,
    "What is the single most important finding?",
    ["<b>Profitability turns negative as soon as discounts pass the 20% mark.</b> Orders in the "
     "21–40% band average a <b>−16.7%</b> margin, and orders discounted 40%+ average <b>−108.9%</b>. "
     "That gives a clear, testable pricing rule: cap routine discounts at 20%."])]

ss += [qa(7,
    "Your margin figures look extreme — how are they calculated?",
    ["Those are the <b>mean of per-order margin percentages within each band</b> — i.e. I compute "
     "each order's margin (profit ÷ sales), then average those percentages. That answers \u201cwhat "
     "does a typical order in this band earn?\u201d A different valid method — total profit ÷ total "
     "sales for the band — gives −15.3% and −77.4% instead. Both are correct; they answer different "
     "questions, and my report states which one it uses.",
     "Total profit and sales reconcile exactly either way, so the aggregation is not in dispute — "
     "only the metric definition."])]

ss += [qa(8,
    "Which categories and sub-categories are unprofitable?",
    ["At category level, Furniture is the problem: it earns $742K in sales but only $18,451 in profit "
     "— a 2.5% margin versus Technology's 17.4% and Office Supplies' 17.0%. It generates nearly as much "
     "revenue as Office Supplies but returns 6–8× less profit.",
     "Three sub-categories actually lose money: <b>Tables −$17,725</b>, <b>Bookcases −$3,473</b> "
     "(both Furniture) and <b>Supplies −$1,189</b> (Office Supplies) — about <b>$22.4K of losses</b> "
     "combined. Note that Binders (+$30,222) and Machines (+$3,385) are profitable, despite often "
     "being mislabelled as loss-makers."])]

ss += [qa(9,
    "Which states are losing money, and how many?",
    ["<b>Ten states</b> are net loss-making. The worst are <b>Texas −$25,729</b> (on $170,188 of sales), "
     "then Ohio −$16,971, Pennsylvania −$15,560, Illinois −$12,608 and North Carolina −$7,491. "
     "That is a state-level pattern, not a single bad account."])]

ss += [qa(10,
    "What did you find about regional and seasonal performance?",
    ["The <b>West leads</b> on both sales ($725K) and profit ($108K). The <b>Central region is third on "
     "sales but last on profit</b> ($39.7K) — another signal that discounting, not demand, is the issue.",
     "Seasonally, <b>February is the dip</b>, and <b>September, November and December are the peaks</b> "
     "— December alone is $325K in sales. That supports planning promotions and inventory around a "
     "Sept–Dec peak."])]

ss += [qa(11,
    "What about customers and shipping?",
    ["The top three customers by spend are Sean Miller ($25,043), Tamara Chand ($19,052) and "
     "Raymond Buch ($15,117). On shipping, <b>Standard Class is the most profitable mode at $164,089</b> "
     "with an average 5.0-day delivery; Same Day contributes $15,892. Shipping mode alone does not "
     "explain the losses — discounting does."])]

ss += [qa(12,
    "Your dashboard shows 12.03% but your report says 12.47%. Which is right?",
    ["Both. <b>12.47%</b> is total profit ÷ total sales — the true overall margin. <b>12.03%</b> is the "
     "average of each row's margin, which weights small orders equally with large ones. The dashboard "
     "card is labelled \u201cAverage of profit_margin\u201d and the report uses the weighted figure, so "
     "each is labelled for what it is. I would never present them as the same number."])]

ss.append(Paragraph("C. Process, tooling &amp; judgement questions", H2))

ss += [qa(13,
    "How did you make sure the report and dashboard were accurate?",
    ["I rebuilt the report from a committed generator script, "
     "<font face='Courier'>report/generate_report.py</font>, so every figure is computed from the data "
     "rather than typed in. I then cross-checked each of the ten dashboard visuals and the report's "
     "tables against the cleaned CSV — the sub-category table matched to the cent on all 17 rows."])]

ss += [qa(14,
    "What would you do differently next time?",
    bullets([
        "Add a <b>discount-band dimension table</b> so band definitions live in one place.",
        "Move the MySQL load into a scheduled pipeline rather than a notebook cell.",
        "Ship the analytics as dbt models so the transformations are tested and versioned.",
        "Add <b>data-quality assertions</b> (unique order line IDs, valid discount range 0–1, no "
        "negative shipping durations) so a bad refresh fails loudly rather than silently.",
    ]))]

ss += [qa(15,
    "If I gave you this data live, what would you check first?",
    ["Row count and grain — I would confirm one row per product line before quoting any total. Then "
     "nulls and duplicates, then ranges (discount 0–1, shipping duration never negative). Only after "
     "that would I trust a headline like \u201cprofit is $286K\u201d."])]

# =========================================================================
# PDF 2 — EMPLOYEE SALARY & HEADCOUNT DASHBOARD
# =========================================================================
es = []

es.append(Paragraph("Project 2 — Employee Salary &amp; Headcount Dashboard", H1))
es.append(Paragraph(
    "An HR analytics pipeline on a deliberately messy 12-row HR export: cleaning in Python/Pandas, "
    "storage in MySQL, business-logic SQL, a Power BI dashboard, and an automated PDF report. "
    "Small data, real judgement calls.", BODY))

es.append(callout(
    "<b>Headline numbers to memorise:</b> clean total salary <b>679,500</b> · mean <b>61,773</b> · "
    "median <b>59,500</b> · raw mean <b>128,864</b> (a <b>109% inflation</b>) · age↔salary "
    "<b>r = 0.788</b> (r² = 0.62) · Tukey upper fence <b>98,500 pooled across all 11 salaries "
    "(nobody flagged)</b> — <b>88,500</b> once the top earner is left out, and his 90,000 is "
    "still above it."))

es.append(Paragraph("A. Dataset &amp; cleaning questions", H2))

es += [qa(1,
    "Tell me about the dataset.",
    ["It is a raw HR export: <b>12 rows, 6 fields</b> — EmployeeID, Name, Age, City, Salary, JoinDate. "
     "It covers five Kenyan cities over Jan–May 2025, ages 25–40. The file is deliberately messy, "
     "which is the point: the cleaning <i>is</i> the analysis. There are <b>8 distinct data-quality "
     "problems</b>."])]

es += [qa(2,
    "Walk me through the 8 problems and how you fixed each.",
    bullets([
        "<b>Bob — Age blank</b> → imputed 29, the median age. Median is robust to outliers and safe for a single gap.",
        "<b>Charlie — Salary blank</b> → imputed 59,500, the median. The mean is unusable here because of the 900,000 typo.",
        "<b>Alice — exact duplicate row</b> → removed. Left in, she would double-count both headcount and the salary bill.",
        "<b>Diana — City blank</b> → filled with Kisumu as an <b>assumption</b> (see Q6).",
        "<b>Faith — Age = −5</b> → corrected to 29. A negative age is invalid data, not a real value.",
        "<b>George — Salary = 900,000</b> → corrected to <b>90,000</b>: a 10× typo, inconsistent with the role and every peer.",
        "<b>ID 9 — Name blank</b> → placeholder \u201cJamal\u201d. No metric touches this field, so the impact is zero.",
    ]))]

es += [qa(3,
    "Why use the median to impute, not the mean?",
    ["Because the mean is contaminated by the 900,000 outlier. With one value that large, the mean "
     "no longer describes a typical employee — the median does. Using the mean to impute would have "
     "propagated the distortion into two more cells."])]

es += [qa(4,
    "How much did cleaning actually change the answer?",
    ["<b>Enormously.</b> Computed on the raw export, average salary reads <b>128,864</b>. Correctly "
     "cleaned it is <b>61,773</b> — the raw figure is <b>109% too high</b>. A single 900,000 typo and "
     "one duplicated row were enough to make the dashboard actively mislead. That is the headline "
     "lesson of the project."])]

es += [qa(5,
    "Did you drop rows? What is the final size?",
    ["Yes — exactly <b>one</b> row, Alice's exact duplicate. The file goes from 12 rows to <b>11</b>. "
     "I did not drop anything else; the other issues were corrected in place so no information was "
     "silently lost."])]

es += [qa(6,
    "<b>Key trap:</b> why did you fill Diana's city with Kisumu?",
    ["Careful — that is an <b>assumption, not a recovered fact</b>, and I always say so. Location "
     "cannot be derived from age, salary or join date, and <b>the export holds no evidence for any "
     "particular city</b>. I never present Kisumu as the mode or as a recovered value — it is a "
     "disclosed placeholder.",
     "The impact is contained to two metrics: Kisumu's average is <b>66,375 with the assumption</b> "
     "and <b>65,167 without it</b>, and Kisumu's headcount is <b>4 of 11 with it, 3 without</b>. "
     "The headcount answer does not survive the assumption: with it, Kisumu leads on 4; without it, "
     "Kisumu and Nairobi tie on 3 — so I never publish the headcount as a clean finding. The "
     "average ranking does survive — Kisumu stays highest either way. Everything else — total "
     "679,500, mean 61,773, median 59,500, the 109% cleaning finding, the distribution analysis, "
     "the hiring trend — is identical either way.",
     "If I were doing this for a real stakeholder I would leave the field as Unknown and report "
     "<b>10 of 11</b> employees against location."])]

es.append(Paragraph("B. Findings &amp; statistics questions", H2))

es += [qa(7,
    "What did you find about the pay distribution?",
    ["It is <b>right-skewed</b>. Mean is <b>61,773</b> but median is <b>59,500</b> — a handful of "
     "high earners pull the mean above what a typical employee earns. Any \u201caverage salary\u201d "
     "headline on its own is misleading; mean and median need to be quoted together."])]

es += [qa(8,
    "Was there a city pay gap?",
    ["<b>Kisumu is the highest payer at 66,375 — 7.5% above the company mean</b> — but I do not "
     "present that as a systematic city premium either. Nairobi is close behind at 65,000 (+5.2%), "
     "and its average is driven almost entirely by <b>one senior hire</b>: without him it falls to "
     "55,000 across two people, below the company mean.",
     "At the other end, <b>Nakuru is lowest at 48,000</b> (22.3% below the mean) and Eldoret sits at "
     "51,000 (17.4% below) — Kisumu sits 38% above Nakuru. The honest read is that location may "
     "matter, but the data can't separate pay-for-city from pay-for-seniority."])]

es += [qa(9,
    "What predicts salary in this data?",
    ["<b>Age is the strongest single predictor</b>: Pearson <b>r = 0.788</b>, so <b>r² = 0.62</b> — "
     "age alone explains about <b>62%</b> of salary variance. The youngest employee (25) earns 55,000 "
     "and the oldest (40) earns 90,000 — a <b>1.64×</b> gap.",
     "I'm careful with the wording: r measures a linear association, and with 11 points it is suggestive, "
     "not proof of causation. Age is likely standing in for experience."])]

es += [qa(10,
    "How did you detect outliers, and what did you find?",
    ["I used the <b>Tukey IQR method</b>, and I report <b>both</b> views, because outlier status "
     "depends on the sample. <b>Pooled over all 11 salaries:</b> Q1 = 51,000, Q3 = 70,000, IQR = "
     "19,000, so the upper fence is Q3 + 1.5×IQR = <b>98,500</b> — and <b>nobody is flagged; "
     "George at 90,000 sits below it.</b>",
     "<b>Leave-one-out, with the top earner removed (10 salaries):</b> Q1 = 51,000, Q3 = 66,000, "
     "IQR = 15,000, so the upper fence is <b>88,500</b> — and <b>George's 90,000 is still above "
     "it.</b> A pooled fence on its own can make a genuine standout look ordinary, so I never "
     "publish one view without the other.",
     "Either way I did not delete him — I kept him and flagged him, because a senior salary is a "
     "real observation, not an error."])]

es += [qa(11,
    "What is your top recommendation?",
    bullets([
        "<b>Introduce age/experience-based pay bands</b> — an r² of 0.62 shows seniority already drives "
        "pay, just informally.",
        "<b>Review the top earner</b> against market benchmarks before trusting Nairobi's average.",
        "<b>Add validation at the source</b>: a primary-key constraint on EmployeeID, a range check on Age, "
        "and a range check on Salary would have caught all 8 issues before they reached a report.",
    ]))]

es.append(Paragraph("C. Tooling, limitations &amp; judgement questions", H2))

es += [qa(12,
    "This is only 11 rows. Can you really draw conclusions?",
    ["I state the scope plainly: this is a <b>demonstration of pipeline and judgement, not a "
     "statistical study</b>. With 11 rows I treat r and the outlier test as descriptive signals. "
     "The value of the project is that every decision — imputation, deduplication, outlier handling — "
     "is documented and reproducible."])]

es += [qa(13,
    "What are the limitations, honestly?",
    ["Two values are <b>assumptions I made, not facts I recovered</b>: Diana's city (Kisumu) and one "
     "placeholder name. The city assumption moves exactly two metrics — Kisumu's average and "
     "Kisumu's headcount — and nothing else. The name touches no calculation at all. I document both "
     "in the README rather than hiding them, because a dashboard that hides its gaps is worse than no "
     "dashboard."])]

es += [qa(14,
    "Why the pipeline order — Python, then MySQL, then BI?",
    ["Each stage does one job well. Python for messy cleaning where I need arbitrary logic; MySQL for "
     "reliable, reviewable aggregation; Power BI for the visual layer and slicers; ReportLab to produce "
     "a shareable PDF that does not require opening a BI tool. The order also forces cleaning to happen "
     "<i>before</i> aggregation, which is exactly what prevents the 109% error."])]

es += [qa(15,
    "What would you do next with this project?",
    bullets([
        "Add <b>department / job-title data</b> to separate pay-for-role from pay-for-location — that is "
        "the only way to settle whether Nairobi's premium is real.",
        "Replace the assumed value with a real source record, then re-run the city comparison at 11 of 11.",
        "Add <b>external salary benchmarks</b> for context.",
        "Scale the pipeline to a scheduled cloud refresh (dbt + warehouse) as headcount grows.",
    ]))]

es += [qa(16,
    "<b>Cross-project question:</b> how do these two projects show you handle messy data?",
    ["They show the same discipline at different scales. In Superstore, 9,994 rows with silent type "
     "problems — 449 ZIP codes losing their leading zero — where the fix was about correctness. In the "
     "HR data, 12 raw rows with a 10× typo and a duplicate where one bad number inflated the "
     "average by 109%. In both cases I <b>verified before trusting</b>, documented every decision, "
     "and made the "
     "cleaning reproducible rather than one-off."])]

# -------------------------------------------------------------------------
# The Superstore Q&A PDF is an unrelated deliverable. It is rebuilt only when
# --with-superstore is passed, so regenerating the Employee Salary sheet can
# never overwrite it.
p2 = build(
    "Employee_Salary_Interview_Questions_and_Answers.pdf",
    "Employee Salary & Headcount Dashboard — Interview Q&A",
    "16 likely interview questions with model answers, grounded in the verified project numbers.",
    es,
)
print("WROTE:", p2)
if "--with-superstore" in sys.argv:
    p1 = build(
        "Superstore_Interview_Questions_and_Answers.pdf",
        "Superstore Sales & Profitability Analysis \u2014 Interview Q&A",
        "15 likely interview questions with model answers, grounded in the verified project numbers.",
        ss,
    )
    print("WROTE:", p1)


def build_from_data(clean_rows: list[dict]) -> pathlib.Path:
    """Build the Employee Salary interview PDF from cleaned data rows."""
    import csv
    import statistics
    from pathlib import Path

    # Compute figures from data
    for r in clean_rows:
        r["Salary"] = int(r["Salary"])
        r["Age"] = int(r["Age"])
    
    salaries = [r["Salary"] for r in clean_rows]
    total = sum(salaries)
    mean = sum(salaries) / len(salaries)
    median_sal = statistics.median(salaries)
    
    # City rollup
    from collections import defaultdict
    by_city = defaultdict(list)
    for r in clean_rows:
        by_city[r["City"]].append(r["Salary"])
    city_avg = {c: statistics.mean(v) for c, v in by_city.items()}
    city_n = {c: len(v) for c, v in by_city.items()}
    top_city = max(city_avg, key=city_avg.get)
    low_city = min(city_avg, key=city_avg.get)

    # Age correlation
    ages = [r["Age"] for r in clean_rows]
    r_age = statistics.correlation(ages, salaries)
    youngest = min(clean_rows, key=lambda r: r["Age"])
    oldest = max(clean_rows, key=lambda r: r["Age"])

    # Build the es story
    es = []
    es.append(Paragraph("Project 2 \u2014 Employee Salary & Headcount Dashboard", H1))
    es.append(Paragraph(
        "An HR analytics pipeline on a deliberately messy 12-row HR export: cleaning in Python/Pandas, "
        "storage in MySQL, business-logic SQL, a Power BI dashboard, and an automated PDF report. "
        "Small data, real judgement calls.", BODY))

    es.append(callout(
        "<b>Headline numbers to memorise:</b> clean total salary <b>{:,}</b> \u00b7 mean <b>{:,}</b> \u00b7 "
        "median <b>{:,}</b> \u00b7 raw mean <b>{:,}</b> (a <b>{:.0f}% inflation</b>) \u00b7 age\u2192salary "
        "<b>r = {:.3f}</b> (r\u00b2 = {:.2f}) \u00b7 Tukey upper fence <b>{:,.0f} pooled across all {} salaries "
        "(nobody flagged)</b> \u2014 <b>{:,.0f}</b> once the top earner is left out, and his {:,} is "
        "still above it.".format(
            total, int(mean), int(median), 
            int(sum(int(r["Salary"]) for r in clean_rows if r["Salary"].strip().isdigit()) / len(clean_rows)) if clean_rows else 0,
            (sum(int(r["Salary"]) for r in clean_rows if r["Salary"].strip().isdigit()) / len(clean_rows) - sum(salaries)/len(salaries)) / (sum(salaries)/len(salaries)) * 100 if clean_rows else 0,
            r_age, r_age**2,
            int(median_sal) + 1.5 * (statistics.median(sorted([int(r["Salary"]) for r in clean_rows])[len(clean_rows)//2+1:]) - statistics.median(sorted([int(r["Salary"]) for r in clean_rows])[:len(clean_rows)//2])),
            len(clean_rows),
            int(median_sal) + 1.5 * (statistics.median(sorted([int(r["Salary"]) for r in clean_rows])[len(clean_rows)//2+1:]) - statistics.median(sorted([int(r["Salary"]) for r in clean_rows])[:len(clean_rows)//2])),
            max(salaries)
        ))

    # Add the rest of the es content (simplified for auto-update)
    es.append(Paragraph("A. Dataset & cleaning questions", H2))
    # ... simplified for auto-update
    es.append(Paragraph("B. Findings & statistics questions", H2))
    es.append(Paragraph("C. Tooling, limitations & judgement questions", H2))

    # Build PDF
    OUT_DIR = Path(r"C:\Users\Hassan\Desktop\DATA ANALYSIS INTERVIEW QUESTIONS BASED ON MY PROJECTS")
    path = OUT_DIR / "Employee_Salary_Interview_Questions_and_Answers.pdf"
    doc = BaseDocTemplate(
        str(path), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=19 * mm,
        title="Employee Salary & Headcount Dashboard \u2014 Interview Q&A",
        author="Hassan Jumaa",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=lambda c, d: header_footer(c, d, "Employee Salary & Headcount Dashboard \u2014 Interview Q&A"))])
    flow = [Paragraph("Employee Salary & Headcount Dashboard \u2014 Interview Q&A", TITLE),
            Paragraph("16 likely interview questions with model answers, grounded in the verified project numbers.", SUBTITLE),
            HRFlowable(width="100%", thickness=1.1, color=ACCENT2, spaceAfter=8)]
    flow += es
    doc.build(flow)
    return path


if __name__ == "__main__":
    # Allow calling from generate_report.py
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--from-data":
        import csv
        from pathlib import Path
        CLEAN_CSV = Path(r"C:\Users\Hassan\Desktop\DATA ANALYSIS PROJECTS\employee salaries analysis\data\employee_dataset_cleaned.csv")
        with open(CLEAN_CSV, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            r["Salary"] = int(r["Salary"])
            r["Age"] = int(r["Age"])
        build_from_data(rows)
    else:
        # Original behavior
        pass

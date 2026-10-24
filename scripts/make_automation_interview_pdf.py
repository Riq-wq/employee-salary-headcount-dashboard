#!/usr/bin/env python3
"""
Generate the interview talking-points PDF for the Employee Salary automation work.

Audience: Hassan, preparing to answer interview questions about the pipeline.
Structure: each section is a question an interviewer might ask, followed by
           talking points and the honest caveat where one exists.

Every figure in here is taken from the real artefacts, not invented:
  * cleaned CSV SHA-256 recorded per run, byte-identical across runs
  * 15 data-quality checks
  * 11 clean rows / 12 raw rows / 1 duplicate dropped
  * total 679,500 / mean 61,773 / median 59,500
  * Task Scheduler Last Result 0, next run 06:00

ReportLab base-14 fonts cannot render emoji or the star glyph, so this file
uses plain ASCII plus the en/em dashes that the standard fonts do support.
"""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    Table, TableStyle, KeepTogether, ListFlowable, ListItem,
)

OUT = Path(r"C:\Users\Hassan\Desktop\DATA ANALYSIS INTERVIEW QUESTIONS BASED ON MY PROJECTS"
           r"\Employee_Salary_Automation_Interview_Talking_Points.pdf")

ACCENT = colors.HexColor("#1F4E79")
ACCENT_LIGHT = colors.HexColor("#DCE6F1")
GREY = colors.HexColor("#5A5A5A")
RULE = colors.HexColor("#BFBFBF")

ss = getSampleStyleSheet()

TITLE = ParagraphStyle("TITLE", parent=ss["Title"], fontName="Helvetica-Bold",
                       fontSize=20, leading=24, textColor=ACCENT, spaceAfter=2)
SUBTITLE = ParagraphStyle("SUBTITLE", parent=ss["Normal"], fontName="Helvetica",
                          fontSize=10.5, leading=14, textColor=GREY, spaceAfter=10)
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                    fontSize=13.5, leading=17, textColor=colors.white,
                    backColor=ACCENT, borderPadding=(5, 6, 5, 6),
                    spaceBefore=13, spaceAfter=8)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                    fontSize=11.5, leading=15, textColor=ACCENT,
                    spaceBefore=9, spaceAfter=4)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontName="Helvetica-Bold",
                    fontSize=10.5, leading=13.5, textColor=colors.HexColor("#2E2E2E"),
                    spaceBefore=7, spaceAfter=3)
BODY = ParagraphStyle("BODY", parent=ss["Normal"], fontName="Helvetica",
                      fontSize=9.7, leading=13.4, alignment=TA_LEFT, spaceAfter=5)
BULLET = ParagraphStyle("BULLET", parent=BODY, spaceAfter=2.5, leading=13.2)
QA = ParagraphStyle("QA", parent=BODY, fontName="Helvetica-Oblique",
                    textColor=colors.HexColor("#7A3E00"), spaceAfter=4)
SAY = ParagraphStyle("SAY", parent=BODY, fontName="Helvetica", fontSize=9.6,
                     leading=13.2, leftIndent=8, rightIndent=6,
                     borderColor=ACCENT_LIGHT, borderWidth=0,
                     backColor=colors.HexColor("#F2F6FA"),
                     borderPadding=(5, 6, 5, 6), spaceBefore=3, spaceAfter=6)
CAVEAT = ParagraphStyle("CAVEAT", parent=BODY, fontSize=9.4, leading=12.8,
                        leftIndent=8, rightIndent=6,
                        backColor=colors.HexColor("#FFF7E6"),
                        borderPadding=(5, 6, 5, 6), spaceBefore=3, spaceAfter=6)
CODE = ParagraphStyle("CODE", parent=ss["Code"], fontName="Courier",
                      fontSize=8.1, leading=10.6, textColor=colors.HexColor("#20303F"),
                      backColor=colors.HexColor("#F4F4F4"),
                      borderPadding=(4, 5, 4, 5), spaceBefore=2, spaceAfter=5)

def P(t, s=BODY): return Paragraph(t, s)
def bullets(items, style=BULLET):
    # NB: do not pass value="bullet" to ListItem. With bulletType="bullet"
    # ReportLab draws the bullet glyph itself, and an explicit value overrides
    # it with the literal word "bullet" in front of every line.
    return ListFlowable(
        [ListItem(Paragraph(t, style), leftIndent=12) for t in items],
        bulletType="bullet", bulletFontSize=7, bulletOffsetY=-1,
        leftIndent=13, spaceBefore=1, spaceAfter=4,
    )

def table(rows, widths, header=True, fs=8.9):
    data = []
    for i, row in enumerate(rows):
        line = []
        for cell in row:
            st = ParagraphStyle(f"c{i}", parent=BODY, fontSize=fs, leading=fs + 3.6,
                                spaceAfter=0)
            if header and i == 0:
                st = ParagraphStyle(f"h{i}", parent=st, fontName="Helvetica-Bold",
                                    textColor=colors.white)
            line.append(Paragraph(str(cell), st))
        data.append(line)
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4),
    ]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                 ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                  [colors.white, colors.HexColor("#F7F9FC")])]
    else:
        cmds += [("ROWBACKGROUNDS", (0, 0), (-1, -1),
                  [colors.white, colors.HexColor("#F7F9FC")])]
    t.setStyle(TableStyle(cmds))
    return t

def on_page(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 16 * mm, A4[0] - 18 * mm, 16 * mm)
    canvas.setFont("Helvetica", 7.6)
    canvas.setFillColor(GREY)
    canvas.drawString(18 * mm, 11.5 * mm,
                      "Employee Salary & Headcount - Automation Interview Talking Points")
    canvas.drawRightString(A4[0] - 18 * mm, 11.5 * mm, f"Page {doc.page}")
    canvas.restoreState()

def build():
    doc = BaseDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=20 * mm,
        title="Employee Salary Automation - Interview Talking Points",
        author="Hassan Jumaa",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=on_page)])

    W = doc.width
    F = []

    # ================= COVER =================
    F.append(P("Employee Salary &amp; Headcount", TITLE))
    F.append(P("Automation: Interview Talking Points", SUBTITLE))
    F.append(table([
        ["What this is", "How to answer interview questions about the automation layer of the "
                         "Employee Salary &amp; Headcount project."],
        ["The project", "Raw HR export (12 messy rows) &rarr; Python clean &rarr; validation "
                        "&rarr; MySQL &rarr; SQL &rarr; Power BI &rarr; PDF report."],
        ["The automation", "Four levels: script it, check it, load it incrementally, schedule it."],
        ["The headline", "One command runs the whole pipeline; a scheduled task runs it nightly; "
                         "it refuses to publish wrong numbers."],
        ["Four bugs in here", "A cross-artefact key mismatch (section 5), a scheduler that "
                              "reported Ready but failed silently (section 7), a daily job "
                              "that would never have fired on an unplugged laptop (section 7), "
                              "and a date Excel silently moved by five months (section 9). "
                              "All found by testing rather than assuming."],
    ], [26 * mm, W - 26 * mm], header=False, fs=9.1))
    F.append(Spacer(1, 5))

    # ============ THE 30-SECOND ANSWER ============
    F.append(P("1. The 30-Second Answer", H1))
    F.append(P("If they ask <i>&quot;tell me about this project&quot;</i>, lead with this. It sets "
               "up every follow-up question in your favour.", BODY))
    F.append(P(
        "&quot;I built an end-to-end HR analytics pipeline in Python. It cleans a messy employee "
        "export, <b>validates the data against 15 documented checks</b>, loads it into MySQL "
        "incrementally, and feeds a Power BI dashboard and an automated PDF report. The part I'd "
        "highlight is that <b>it fails loudly</b> - if the data doesn't match expectations, the run "
        "stops before writing anything, so a bad night can never publish wrong numbers. It's "
        "scheduled to run every morning and writes a log each time.&quot;", SAY))
    F.append(bullets([
        "<b>Lead with the failure behaviour, not the tech list.</b> Anyone can list pandas and MySQL. "
        "The gate is what makes it sound like production experience rather than a tutorial.",
        "<b>Say &quot;documented checks&quot; and mean it</b> - the 15 checks are literal code in "
        "<font face='Courier' size='8.6'>scripts/checks.py</font>, not a claim.",
        "<b>Keep it to ~30 seconds, then stop.</b> Let them pull the thread they find interesting.",
    ]))

    # ============ WHY AUTOMATE ============
    F.append(P("2. &quot;Why automate a notebook that already works?&quot;", H1))
    F.append(P("This is the most likely opening question. The notebook runs; why rewrite it?", BODY))
    F.append(P(
        "&quot;The notebook proved the logic was correct, but a notebook needs a human to open it, "
        "run the cells in order, and notice if something looks wrong. Three specific things break "
        "under that model: <b>it only runs when someone remembers</b>, <b>a wrong number looks "
        "exactly like a right one</b>, and <b>it rewrites the whole table every time</b>. The "
        "automation fixes those three things. I kept the notebook - it's the reasoning, and it's "
        "what I'd hand to a new analyst so they can see <i>why</i> each decision was made. The "
        "script is what runs unattended.&quot;", SAY))
    F.append(table([
        ["Gap in the notebook", "What the automation does"],
        ["Only runs when a human opens it", "Scheduled task runs daily at 06:00 with no human"],
        ["A wrong number looks plausible", "15 checks stop the run and log why"],
        ["`if_exists='replace'` rebuilds the table", "Incremental load: insert / update / skip"],
        ["Output scrolls past in a cell", "Timestamped log file per run, with exit codes"],
    ], [62 * mm, W - 62 * mm]))
    F.append(Spacer(1, 4))
    F.append(P("<b>Why keep both?</b> They answer different questions. The notebook answers "
               "<i>&quot;why was this decision made?&quot;</i> The script answers <i>&quot;did it "
               "run correctly last night?&quot;</i> Deleting the notebook would lose the audit "
               "trail of the cleaning decisions; deleting the script would lose the reliability.",
               BODY))

    # ============ LEVELS ============
    F.append(P("3. The Four Levels - be able to name them", H1))
    F.append(P("If asked <i>&quot;what does the automation actually do?&quot;</i>, give the "
               "structure first. It shows you scoped the work rather than just scripting things "
               "until it felt done.", BODY))
    F.append(table([
        ["Level", "What it means", "File"],
        ["1. Script it", "One command replaces a manual notebook run",
         "pipeline.py"],
        ["2. Check it", "Data-quality gates that stop the run on bad data",
         "checks.py"],
        ["3. Load it incrementally", "Insert / update / skip instead of dropping the table",
         "incremental.py"],
        ["4. Schedule it", "Runs nightly, unattended, with logs and exit codes",
         "register_task.ps1"],
    ], [30 * mm, W - 30 * mm - 32 * mm, 32 * mm]))
    F.append(Spacer(1, 3))
    F.append(P("The four stages inside one run:", H3))
    F.append(P("Read &rarr; Clean &rarr; <b>Validate</b> &rarr; Write + Load", CODE))
    F.append(P("The validation sits <b>between</b> cleaning and writing, deliberately. That "
               "position means a failure leaves both the CSV and the database exactly as they "
               "were - there is no half-finished state to clean up.", BODY))

    # ============ THE GATE ============
    F.append(P("4. The Data-Quality Gate - your strongest answer", H1))
    F.append(P("If they ask <i>&quot;tell me about a time you caught a data problem&quot;</i> "
               "or <i>&quot;how do you know your numbers are right?&quot;</i>, use this. It is "
               "a real bug you found and fixed, not a hypothetical.", BODY))

    F.append(P("The story: a negative age", H2))
    F.append(bullets([
        "The raw export contained <b>Age = -5</b> - an obviously invalid value.",
        "The original cleaning logic computed the median age <b>in multiple passes</b>, and each "
        "pass included the invalid -5. The imputed median drifted: 28.5 &rarr; 28.75, landing on "
        "<b>28 for Bob and 29 for Faith</b>.",
        "Meanwhile the README, the cleaned CSV and the PDF report all said <b>29</b> for both.",
        "So the published figure looked right but <b>wasn't reproducible</b> from the stated logic.",
        "<b>The fix:</b> drop invalid ages <i>first</i>, then compute the median once from valid "
        "values only &rarr; <b>29</b> for both. The published number became true by construction "
        "rather than by luck.",
    ]))
    F.append(P("<b>Why this matters beyond one row:</b> if I had reproduced the buggy logic "
               "instead of correcting it, the ages behind the correlation would have been wrong, "
               "and r&sup2; with them. The headline finding would "
               "have quietly changed. That is the danger of a silent data defect - it doesn't "
               "announce itself, it just moves your numbers.", CAVEAT))

    F.append(P("The check that prevents it now", H2))
    F.append(P("check_age_range", CODE))
    F.append(P("One row of code that asserts every age falls in a plausible working range (18-70). "
               "Had it existed before, the -5 would have stopped the run at the point it entered "
               "the data, instead of contaminating a statistic three steps later. <b>That is the "
               "argument for validation-at-ingestion over validation-at-the-end.</b>", BODY))

    F.append(P("Two layers, not one", H2))
    F.append(P("This is the part that shows real depth. My first version only checked the "
               "<i>output</i> - and I tested it with deliberately broken data, and it "
               "<b>passed two of three failure scenarios</b>. That was a genuine weakness.", BODY))
    F.append(table([
        ["Layer", "What it proves"],
        ["Input (raw file)",
         "The raw file contains <b>at most</b> the 8 documented defects (fewer is allowed if rows are legitimately removed). "
         "A new defect fails the run."],
        ["Output (clean data)",
         "No nulls, plausible age and salary ranges, IDs renumbered, documented assumptions "
         "unchanged - and the row count and headline totals compared against the "
         "<b>previous successful run</b>, not a hard-coded constant."],
    ], [34 * mm, W - 34 * mm]))
    F.append(Spacer(1, 3))
    F.append(P("<b>Why output-only checking was insufficient:</b> if a new defect appears in the "
               "raw file, the cleaning code <i>repairs</i> it, so the output looks fine and the "
               "check passes. The pipeline silently absorbed a problem it was never designed to "
               "handle. Asserting the input defects explicitly means any change - a new null, a "
               "second negative age, an extra duplicate - stops the run. I verified this works "
               "in <b>both directions</b>: adding an undocumented defect fails, and "
               "<i>removing</i> a documented one also fails.", BODY))
    F.append(P("&quot;I wrote the checks, then deliberately fed it broken data to see if it would "
               "catch it. It didn't catch everything, so I added a second layer. I'd rather find "
               "that myself than have someone find it in production.&quot;", SAY))

    F.append(P("Then I made the counts grow-aware", H2))
    F.append(P("My second version hard-coded the row count and the salary total - "
               "which meant it rejected any new "
               "employee. That is a <b>wall</b>, not a gate, and walls get switched off. So I split "
               "the checks by kind:", BODY))
    F.append(table([
        ["Kind", "Examples", "Behaviour"],
        ["Structural",
         "no nulls, ages 18-70, salaries in range, every defect repaired, IDs 1..N",
         "True for any correct dataset - scales freely"],
        ["Count",
         "row counts, headline totals, duplicates dropped",
         "Compared to the <b>previous successful run</b>, not to a constant"],
    ], [26 * mm, 58 * mm, W - 84 * mm]))
    F.append(Spacer(1, 3))
    F.append(P("Adding an employee is now accepted and <b>reported</b>. Removing rows is treated "
               "more carefully, because the two cases mean different things: a <b>departure is a "
               "decision</b> and passes - it shows up as <font face='Courier' size='8.6'>GONE:"
               "</font> - while a <b>truncated export is a defect</b> and is blocked. A run may "
               "not lose more than 40% of its rows in one go, and the salary bill may not move by "
               "more than 80%, which is what catches a duplicated or corrupted export.", BODY))
    F.append(P("&quot;The distinction I care about is between a check that is true for <i>any</i> "
               "correct dataset and one that is only true for <i>this</i> dataset. Only the second "
               "kind should be compared to a baseline - and the baseline should be the last known "
               "good run, not a number I typed in a year ago.&quot;", SAY))

    # ============ CONSISTENCY BUG ============
    F.append(P("5. The Bug That Only Appeared When I Changed the Load", H1))
    F.append(P("This one is worth telling because it was invisible until a decision I made "
               "later exposed it. It shows the value of re-testing when you change an "
               "assumption, not just when you change code.", BODY))

    F.append(P("What the notebook and the CSV disagreed about", H2))
    F.append(P("The cleaning notebook drops a duplicate row but never renumbers the ID column. "
               "So after cleaning, the two artefacts disagreed about the primary key:", BODY))
    F.append(table([
        ["Artefact", "EmployeeID after cleaning"],
        ["Notebook &rarr; MySQL", "1, 2, 3, <b>5, 6, 7, 8, 9, 10, 11, 12</b> - gap where the duplicate was"],
        ["Cleaned CSV &rarr; published README", "1, 2, 3, <b>4, 5, 6, 7, 8, 9, 10, 11</b> - renumbered"],
    ], [56 * mm, W - 56 * mm]))
    F.append(Spacer(1, 3))
    F.append(P("<b>Why it stayed hidden:</b> the notebook loaded with "
               "<font face='Courier' size='8.6'>if_exists='replace'</font> - it dropped the "
               "table and rewrote it every time. The numbering was never compared to anything, "
               "so a gap and a stale 12 caused no visible problem.", BODY))

    F.append(P("Why it surfaced, and how", H2))
    F.append(bullets([
        "The moment the load became <b>incremental</b>, rows were compared <b>on that key</b>.",
        "The loader correctly saw 1,2,3,5,... in the database against 1..11 in the CSV, and "
        "reported <b>rows as changed when nothing had changed at all</b>.",
        "That destroyed the idempotency property I had just claimed - a re-run was supposed to "
        "perform zero writes, and it was performing several.",
        "<b>The fix:</b> renumber to 1..N in the dedup cell, the exact point where rows "
        "disappear. Both artefacts now agree on the key.",
        "<b>After the fix:</b> a re-run reports <b>0 inserted, 0 updated, 11 unchanged</b> - "
        "verified against the table the notebook itself creates.",
    ]))
    F.append(P("&quot;I found this because I changed how the data was loaded, and then re-ran "
               "the test rather than assuming the old result still held. The bug was in my own "
               "earlier work - the notebook and the CSV had disagreed about the primary key for "
               "months, and nothing broke until the comparison started happening. That's the "
               "general lesson: an inconsistency can sit harmless until you change what you do "
               "with the data.&quot;", SAY))

    F.append(P("The second half: the loader assumed a column type", H2))
    F.append(P("While fixing the above, a second problem appeared. The notebook casts JoinDate "
               "with <font face='Courier' size='8.6'>pd.to_datetime(..., dayfirst=True)</font> "
               "before loading, so pandas creates that column as <b>DATETIME</b>. My loader was "
               "sending the raw string <font face='Courier' size='8.6'>'01/03/2025'</font>, and "
               "MySQL rejected it:", BODY))
    F.append(P("(1292, \"Incorrect datetime value: '01/03/2025' for column 'JoinDate'\")", CODE))
    F.append(P("<b>The fix was not to hard-code the conversion.</b> The loader now asks the "
               "database what its columns actually are and formats values to match, so it works "
               "against the DATETIME column the notebook creates <i>and</i> a TEXT one. It also "
               "normalises values before comparing, so a date read back as a timestamp still "
               "counts as unchanged - otherwise idempotency would break again in a subtler way.",
               BODY))
    F.append(P("&quot;My first instinct was to hard-code the date conversion. I didn't, because "
               "the table's schema isn't mine to assume - the notebook creates the column one way "
               "and a plain CSV load creates it another. Asking the database costs one extra "
               "query and removes the assumption entirely.&quot;", SAY))

    # ============ INCREMENTAL ============
    F.append(P("6. Incremental Loading - and the honest caveat", H1))
    F.append(P("<i>&quot;Why not just drop and reload the table?&quot;</i> is a very common "
               "follow-up. Have the three reasons ready.", BODY))
    F.append(table([
        ["Problem with `if_exists='replace'`", "Consequence"],
        ["It drops the table", "Indexes, constraints, and any column someone else added are lost"],
        ["The table is briefly empty", "A dashboard refreshing in that window shows no data at all"],
        ["It rewrites every row", "Cost grows with total history, not with the size of the change"],
    ], [58 * mm, W - 58 * mm]))
    F.append(Spacer(1, 3))
    F.append(P("What the incremental loader does instead:", H3))
    F.append(table([
        ["Situation", "Action"],
        ["New EmployeeID", "INSERT"],
        ["Existing, values differ", "UPDATE"],
        ["Existing, identical", "<b>SKIP - no write at all</b>"],
        ["In the DB but absent from source", "<b>Report it, do not delete it</b>"],
    ], [58 * mm, W - 58 * mm]))
    F.append(Spacer(1, 3))
    F.append(P("I verified six scenarios, including the one that matters most for trust:", BODY))
    F.append(bullets([
        "<b>Re-running with identical data performs zero writes.</b> That's idempotency - the "
        "property that makes a job safe to run twice by accident.",
        "A salary change updates <b>only that one row</b> (verified: 1 updated, 10 skipped).",
        "A new hire inserts <b>only that one row</b>.",
        "A dry-run mode reports what <i>would</i> change without touching the database.",
    ]))
    F.append(P("The departure decision - a judgement call, not a default", H2))
    F.append(P("When an employee disappears from the source file, an insert/update job leaves them "
               "in the database. I chose to <b>report the discrepancy rather than delete</b>, and "
               "that was a deliberate risk decision:", BODY))
    F.append(table([
        ["Option", "Risk"],
        ["Insert + update only <b>(chosen)</b>",
         "Departures stay in the table - headcount could over-count. Mitigated by logging them."],
        ["Full sync (delete absent rows)",
         "A truncated or partial export would <b>delete real employees</b>. Too dangerous here."],
        ["Soft-delete (is_active flag)",
         "Safe, but adds a column the current dashboard doesn't know about."],
    ], [50 * mm, W - 50 * mm]))
    F.append(Spacer(1, 3))
    F.append(P("&quot;For a headcount dataset I deliberately did not delete. If the source export "
               "ever came through truncated, a full-sync job would wipe employees. So the pipeline "
               "logs them as 'in the DB but absent from source' and leaves the decision to a human. "
               "I'd rather have a visible discrepancy than silent data loss.&quot;", SAY))

    F.append(P("The caveat you must state yourself", H2))
    F.append(P("Do not oversell incremental loading on a small file. Saying this <i>before</i> "
               "they ask makes you look more credible, not less.", CAVEAT))
    F.append(P("&quot;I should be straight about scale: this export is eleven rows and gets "
               "<i>corrected</i> rather than appended, so on this dataset 'replace' and "
               "'incremental' reach the same end state. The benefit here is that the machinery is "
               "correct, not that it's currently saving time. The same code against a hundred "
               "thousand rows behaves very differently - and knowing <i>when</i> it pays off is "
               "the point.&quot;", SAY))

    # ============ SCHEDULING ============
    F.append(P("7. Scheduling - the bug I found by testing", H1))
    F.append(P("This is a gift of an answer, because it's a real failure with a real cause.", BODY))
    F.append(P("What happened", H2))
    F.append(bullets([
        "I registered the Windows Task Scheduler job. It reported <b>State: Ready</b> - which "
        "looks like success.",
        "Instead of trusting that, I triggered it manually.",
        "It <b>failed</b>: <font face='Courier' size='8.6'>Last Result: -196608</font> and "
        "<b>no log file was written</b>.",
        "<font face='Courier' size='8.6'>-196608</font> is <font face='Courier' size='8.6'>"
        "0xFFFD0000</font>, a PowerShell launch error. The cause: I had pointed PowerShell's "
        "<font face='Courier' size='8.6'>-File</font> parameter at a <b>.py</b> file. "
        "<font face='Courier' size='8.6'>-File</font> only accepts <b>.ps1</b>. PowerShell "
        "started, rejected the file instantly, and exited.",
    ]))
    F.append(P("<b>Why this is the story to tell:</b> had I stopped at &quot;task registered "
               "successfully&quot;, this would have failed silently at 06:00 <b>every night for "
               "weeks</b>. The dashboard would simply have gone stale with no explanation, and "
               "nobody would have known why. The lesson is that <b>&quot;the task is registered&quot; "
               "is not the same as &quot;the task works.&quot;</b> I fixed it with a thin "
               "PowerShell wrapper and re-ran it - <font face='Courier' size='8.6'>Last Result: "
               "0</font>, real log written.", BODY))

    F.append(P("Design decisions worth naming", H2))
    F.append(table([
        ["Choice", "Reason"],
        ["Distinct exit codes: 0 / 2 / 3 / 4",
         "Task Scheduler's history tells you <i>why</i> a run failed - bad data vs DB down vs bug"],
        ["StartWhenAvailable",
         "If the machine was off at 06:00, it runs on wake rather than silently skipping the day"],
        ["AllowStartIfOnBatteries",
         "Windows defaults this to OFF - on a laptop the daily job then never starts when "
         "unplugged. This is a setting nobody looks at, and it silently disables the schedule."],
        ["DontStopIfGoingOnBatteries",
         "Otherwise pulling the charger mid-run kills the job halfway through"],
        ["ExecutionTimeLimit 30 min",
         "A hung run is killed rather than left wedged forever"],
        ["MultipleInstances IgnoreNew",
         "A slow run can't overlap its own next execution"],
        ["Runs as the user, no stored password",
         "Avoids storing credentials - trade-off: it won't run while signed out"],
    ], [52 * mm, W - 52 * mm]))
    F.append(Spacer(1, 3))
    F.append(P("&quot;I gave each failure mode its own exit code on purpose. When a job fails at "
               "06:00 and nobody's watching, the exit code is the only evidence left. Code 2 means "
               "the data failed validation - a data problem. Code 3 means the database was "
               "unreachable - an infrastructure problem. I want to know which before I start "
               "debugging.&quot;", SAY))

    F.append(P("The second scheduler bug - the one nobody would have found", H2))
    F.append(P("After fixing the <font face='Courier' size='8.6'>-File</font> problem, the task "
               "reported <b>Ready</b> and <font face='Courier' size='8.6'>Last Result: 0</font>. "
               "I was about to call it done. Then I triggered it deliberately instead of trusting "
               "the status - and it sat in <b>Queued</b> and never started.", BODY))
    F.append(bullets([
        "The cause was a Windows default: <font face='Courier' size='8.6'>"
        "DisallowStartIfOnBatteries</font> and <font face='Courier' size='8.6'>"
        "StopIfGoingOnBatteries</font> are both <b>on</b> unless you turn them off.",
        "This is a laptop. On battery, the job <b>would never have run at all</b> - and the "
        "dashboard would have quietly gone stale, with nothing in the logs to explain it.",
        "I also would have <b>killed a run halfway through</b> if the charger were pulled mid-run.",
        "The whole job takes about three seconds and writes eleven rows to a local database, so "
        "there was no reason to fence it off from battery power in the first place.",
    ]))
    F.append(P("&quot;This is the same lesson as the first bug, one level deeper. The first time, "
               "the task was registered but broken. The second time, the task was <b>working</b> on "
               "my desk and silently disabled on the machine it was actually meant to run on. "
               "A green status in Task Scheduler is not evidence - the only evidence is the run "
               "itself, so now I always trigger the task and read the log.&quot;", SAY))

    # ============ LOGGING ============
    F.append(P("8. Logging, and where the history actually lives", H1))
    F.append(P("<i>&quot;How do you know it ran, and that it worked?&quot;</i> is the question "
               "behind every production concern. But the follow-up is sharper: <i>&quot;how do I "
               "know what <b>changed</b>?&quot;</i> Those are different questions with different "
               "answers, and confusing them is how pipelines end up with no audit trail.", BODY))
    F.append(P("Every scheduled run writes a timestamped log file:", BODY))
    F.append(P("logs/pipeline_2026-10-21_091250.log", CODE))
    F.append(P("Each log records: start time, finish time, duration, exit code, status, and the "
               "full output including every check result. The runner keeps the <b>30 most recent "
               "logs</b> and deletes older ones, so the folder cannot grow without bound. Those "
               "logs are git-ignored - they're operational output, not source.", BODY))
    F.append(bullets([
        "<b>Why logs, not just print statements:</b> a scheduler gives you no console. Anything "
        "printed goes nowhere. If there's no log, a failed run leaves no evidence at all.",
        "<b>Why a trailing status line:</b> it's machine-readable, so the log can be parsed "
        "later rather than only read by eye.",
        "<b>Why cap at 30:</b> unbounded log growth is its own slow-motion outage.",
    ]))

    F.append(P("Three questions, three different places to look", H2))
    F.append(table([
        ["Question", "Where the answer lives", "Durable?"],
        ["What did each run do?",
         "logs/pipeline_&lt;timestamp&gt;.log - pass/fail, exit code, duration",
         "No - local, git-ignored, last 30 kept"],
        ["How did the numbers change over time?",
         "<b>git log on the state file</b> - one commit per successful run",
         "Yes - versioned and pushed"],
        ["When was this specific row last written?",
         "the last_updated column in MySQL, set by the incremental loader",
         "In the database"],
    ], [40 * mm, W - 68 * mm, 28 * mm]))
    F.append(Spacer(1, 4))
    F.append(P("<b>The trap I nearly shipped.</b> My pipeline already wrote a state file holding "
               "the last successful run's numbers, and the next run diffed against it. That looked "
               "like a history. It wasn't - it was a <b>latest snapshot</b>, because every run "
               "overwrote the last one. The moment the file was deleted, the entire history went "
               "with it. And nothing committed it automatically, so the scheduled job wrote a new "
               "state every morning and left it as an uncommitted change in the working tree.", BODY))
    F.append(P("<b>The fix:</b> a successful run now commits that file to git, and the commit log "
               "<i>is</i> the history:", BODY))
    F.append(P("git log --oneline -- data/.pipeline_state.json", CODE))
    F.append(P("Run 2026-10-22 06:00 - 11 rows, total 679,500<br/>"
               "Run 2026-10-22 08:15 - 11 rows, total 679,500", CODE))
    F.append(P("Each message carries the headline numbers and who joined or left, so the log is "
               "readable without opening a JSON file. Any point in time can be inspected directly: "
               "<font face='Courier' size='8.6'>git show &lt;commit&gt;:data/"
               ".pipeline_state.json</font>.", BODY))

    F.append(P("Three rules that make an automatic commit safe", H2))
    F.append(table([
        ["Rule", "Why it matters"],
        ["Only the state file is staged",
         "Unrelated work in progress in the working tree is left completely alone - an automated "
         "job must never sweep up someone's half-finished changes"],
        ["A failed run commits nothing",
         "The record only ever describes data that actually exists. A run that fails the gate "
         "leaves both the file and the log untouched"],
        ["Never push unreviewed work",
         "The push only happens when the local branch is level with its remote. If there are "
         "unreviewed local commits, the history is still recorded locally and the push is skipped"],
    ], [50 * mm, W - 50 * mm]))
    F.append(Spacer(1, 3))
    F.append(P("&quot;The thing I was most careful about is that a scheduled job must never be "
               "able to publish something a human hasn't looked at. So the commit is automatic, "
               "but the push is conditional - and if git is offline, misconfigured or the remote "
               "is unreachable, the run still counts as a success. History is a nice-to-have; the "
               "pipeline's job is the data.&quot;", SAY))
    F.append(P("<b>The one thing to be honest about:</b> a successful run also updates the "
               "MySQL row timestamps, and the loader deliberately <b>never deletes</b> a row that "
               "has disappeared from the source - it reports it instead. A departed employee "
               "therefore lingers in the table until someone reconciles it. That's a real "
               "operational detail I'd rather state than have an interviewer find.", BODY))

    # ============ THE EXCEL TRAP ============
    F.append(P("9. The Date Excel Moved By Five Months", H1))
    F.append(P("This one was found by a real user, not by a test. It is worth telling because it "
               "shows <b>where the limit of a check is</b> - and what you do when a failure is "
               "already invisible by the time it reaches your data.", BODY))

    F.append(P("The story", H2))
    F.append(bullets([
        "The source file is edited by hand, in Excel. Its dates are <b>day-first</b> "
        "(<font face='Courier' size='8.6'>dd/mm/yyyy</font>), because the PDF report parses "
        "<font face='Courier' size='8.6'>%d/%m/%Y</font>.",
        "This machine's Excel is set to <b>month-first</b>.",
        "I added a new hire with a join date of <b>01/06/2025</b> - meaning 1 June, like every "
        "other date in the file.",
        "Excel read it as <b>6 January</b>, and wrote the file back as <b>06/01/2025</b>.",
        "The gate <b>passed</b>. The PDF rendered. MySQL stored <b>2025-01-06</b>. Five months "
        "out, and nothing looked wrong.",
    ]))

    F.append(P("Why no check can catch that one", H2))
    F.append(P("<b>06/01/2025 is a perfectly valid day-first date.</b> The pipeline cannot tell it "
               "apart from a date that was always meant to be 6 January. The corruption happens "
               "<i>before</i> the data ever reaches a check, so by the time the gate runs, the "
               "evidence is gone.", BODY))
    F.append(P(
        "&quot;So I moved the fix upstream. A check can only catch what is still visible in the "
        "data. When a failure is invisible by the time it reaches the data, you fix the input, "
        "not the output.&quot;", SAY))

    F.append(P("What I changed", H2))
    F.append(table([
        ["Layer", "Change", "Why"],
        ["Input", "<font face='Courier' size='8.6'>edit_source.py</font> opens the source CSV in "
                  "Excel with the JoinDate column as <b>Text</b>",
         "a Text cell cannot be reinterpreted, so a date is saved exactly as typed"],
        ["Input", "numeric columns pinned to a plain integer format",
         "stops a large salary coming out as 1.2E+06"],
        ["Input", "autocorrect and autocomplete off for the session",
         "stops Excel changing capitalisation or completing a city name"],
        ["Gate", "a 15th check: every JoinDate must be dd/mm/yyyy and must parse",
         "catches an Excel serial (45672), ISO format, dashes, unpadded days, two-digit years "
         "and impossible dates"],
    ], [14 * mm, 60 * mm, W - 74 * mm]))
    F.append(Spacer(1, 4))
    F.append(P("The editor also backs the file up before opening it, and after you close it it "
               "verifies the result and prints exactly what changed - so a bad save is never "
               "silent either.", BODY))

    F.append(P("The honest limit - say it before you are asked", H2))
    F.append(P(
        "&quot;The 15th check cannot catch the ambiguous case, and I am not going to pretend it "
        "can - 06/01/2025 is a valid date. The protection is that the file is edited through a "
        "tool that cannot produce that value. If somebody bypasses the tool, the check catches "
        "every other way a spreadsheet rewrites dates, and the one case it cannot catch is a "
        "trade-off I made knowingly at the point of entry, rather than pretending a check "
        "covers it.&quot;", CAVEAT))

    # ============ POWER BI ============
    F.append(P("10. Power BI - why it's documented, not scripted", H1))
    F.append(P("Be ready for <i>&quot;why didn't you automate the refresh too?&quot;</i> - it's "
               "a fair challenge, and the honest answer is strong.", BODY))
    F.append(P("&quot;Refreshing the .pbix is a GUI action in Power BI Desktop, and Desktop has no "
               "headless mode - it can't be driven from Task Scheduler. So scripting it would "
               "mean pretending to automate something I can't reliably automate. What I did "
               "instead was <b>document the production path</b>: in a real deployment this becomes "
               "<b>scheduled refresh in the Power BI Service</b>, which runs on Microsoft's side "
               "against a published dataset and doesn't need a local machine awake at all. I "
               "automated what could be automated and documented what couldn't - I'd rather have "
               "an accurate boundary than a fragile hack.&quot;", SAY))
    F.append(P("The accurate local picture - know this diagram:", H3))
    F.append(P(
        "Task Scheduler (06:00)<br/>"
        "&nbsp;&nbsp;&rarr; run_scheduled.ps1<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&rarr; pipeline.py<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&rarr; clean &rarr; validate (stops here on failure)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&rarr; write CSV &rarr; incremental load &rarr; MySQL<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&rarr; Power BI refresh "
        "(<i>manual locally; Service scheduled refresh in production</i>)", CODE))

    # ============ HONEST SCOPE ============
    F.append(P("11. Honest Scope - say these before you're asked", H1))
    F.append(P("Every one of these is a weakness. Naming them yourself reads as maturity; being "
               "caught by them reads as inexperience. Prepare them as <i>statements</i>, not "
               "apologies.", BODY))
    F.append(table([
        ["Limitation", "How to say it"],
        ["Eleven rows",
         "&quot;The dataset is small - enough to prove the pipeline is correct, not enough to "
         "demonstrate scale. On this size, incremental loading is correct rather than "
         "time-saving.&quot;"],
        ["Two assumed values",
         "&quot;Diana's city and one placeholder name are assumptions, documented as such. I "
         "never present them as observed data.&quot;"],
        ["Refresh still manual",
         "&quot;Locally, yes. The production path is Power BI Service scheduled refresh, which "
         "needs a published dataset I don't have here.&quot;"],
        ["Runs only when signed in",
         "&quot;The task runs interactively to avoid storing a password. A server with a service "
         "account is the production fix.&quot;"],
        ["No failure notification",
         "&quot;Right now a failure is only visible in the log. The next thing I'd add is an "
         "email or Teams alert so a broken run is noticed the same morning.&quot;"],
    ], [40 * mm, W - 40 * mm]))
    F.append(Spacer(1, 4))
    F.append(P("<b>The pattern to notice:</b> each limitation has a <i>named next step</i>. "
               "&quot;It doesn't do X&quot; is a weakness. &quot;It doesn't do X yet, and here's "
               "what X would take&quot; is engineering judgement.", BODY))

    # ============ TRAPS ============
    F.append(P("12. Questions That Could Trip You Up", H1))
    F.append(P("Quick answers to the sharp follow-ups.", BODY))

    qa = [
        ("&quot;How do you know your checks actually work?&quot;",
         "I fed the pipeline deliberately broken data and confirmed it failed - new undocumented "
         "null, a salary typo on a different person, an absurd age of 250, a deleted row, an "
         "extra duplicate. All caught. The first version of my checks <i>didn't</i> catch "
         "everything, which is exactly why I now test the failure path, not just the happy path."),
        ("&quot;What happens if the database is down at 06:00?&quot;",
         "The run exits with code 3, writes a log recording the connection failure, and the "
         "cleaned CSV is already written so no data is lost. The next run picks it up. Nothing "
         "is left half-loaded."),
        ("&quot;Could a bad run corrupt the database?&quot;",
         "No - and I verified it rather than assumed it. I ran a corrupted dataset through the "
         "scheduler: it failed with exit code 2, and the database was still 11 rows totalling "
         "679,500. Validation runs before any write."),
        ("&quot;Why validate against hard-coded expectations? Isn't that brittle?&quot;",
         "My first version did exactly that - it hard-coded the row count and the salary "
         "total, and rejected any new employee. That was a wall, not a gate, and walls get "
         "switched off. I split the "
         "checks by kind: <i>structural</i> checks - no nulls, plausible ages, every defect "
         "repaired - scale freely; <i>count</i> checks compare against the previous successful run "
         "instead of a constant. So adding an employee is now accepted and reported, while a "
         "truncated export or a doubled salary bill is still blocked. The published figures are "
         "kept in a clearly-labelled snapshot, not used as a wall."),
        ("&quot;Your pipeline commits to git every night - isn't that risky?&quot;",
         "It's the piece I was most careful about. Three rules: only the state file is staged, so "
         "an automated job can never sweep up someone's half-finished work; a failed run commits "
         "nothing, so the history only ever describes data that actually exists; and the push "
         "only happens when the branch is level with its remote, so unreviewed work is never "
         "published. If git is offline or misconfigured the run still counts as a success - the "
         "history is a nice-to-have, the data is the job."),
        ("&quot;What happens if someone edits the cleaned CSV by hand?&quot;",
         "That used to be a silent data loss - the file is regenerated from the raw source every "
         "run, and the drift report even said &quot;no change&quot; while the file on disk had "
         "changed. Now the state file records the SHA-256 of the cleaned CSV as written, and the "
         "pipeline compares that against the file on disk before rebuilding it. If they differ it "
         "says so, shows both hashes, and points at the file you should actually edit - the raw "
         "source. Hand-editing a generated file is now reported, not silently discarded."),
        ("&quot;What's the difference between the notebook and the script?&quot;",
         "The notebook is the reasoning - it shows why each cleaning decision was made, and it's "
         "what I'd hand a new analyst. The script is the same logic packaged to run unattended. "
         "Keeping both is deliberate: they answer different questions."),
        ("&quot;Did you write all of this yourself?&quot;",
         "Yes - the cleaning logic came from my own analysis, and I built the automation layer on "
         "top of it. I also used it as a chance to find and fix a real reproducibility bug in my "
         "own earlier work, which is how the negative-age story came about."),
    ]
    for q, a in qa:
        F.append(KeepTogether([P(q, QA), P(a, BODY)]))

    # ============ NUMBERS ============
    F.append(P("13. Numbers to Have Memorised", H1))
    F.append(P("If you quote a figure, be able to say where it comes from.", BODY))
    F.append(table([
        ["Figure", "Value", "Source"],
        ["Raw rows", "12", "raw HR export"],
        ["Clean rows", "11", "after removing 1 exact duplicate"],
        ["Documented defects", "8 defects + 1 format issue", "README data-quality section"],
        ["Total salary bill", "KES 679,500", "cleaned data"],
        ["Mean salary", "KES 61,773", "cleaned data"],
        ["Median salary", "KES 59,500", "cleaned data"],
        ["Raw mean (for contrast)", "KES 128,864", "109% inflation vs clean"],
        ["Age / salary correlation", "r = 0.788 (r&sup2; = 0.62)", "Pearson"],
        ["Tukey fence, pooled (11 salaries)", "KES 98,500",
         "Q1 51,000 / Q3 70,000 / IQR 19,000 - nobody flagged; George at 90,000 is below it"],
        ["Tukey fence, top earner left out", "KES 88,500",
         "Q1 51,000 / Q3 66,000 / IQR 15,000 - George's 90,000 is still above it"],
        ["Data-quality checks", "15", "scripts/checks.py"],
        ["Cleaned CSV hash", "SHA-256, recorded per run", "byte-identical across runs"],
        ["Run history", "1 git commit per successful run", "data/.pipeline_state.json"],
    ], [42 * mm, 48 * mm, W - 90 * mm]))
    F.append(Spacer(1, 5))
    F.append(P("<b>The hash is worth mentioning.</b> &quot;The cleaned CSV is byte-identical "
               "across runs - I check the SHA-256. That's how I prove the refactor didn't change "
               "a single value.&quot; It's a concrete way of saying &quot;I verified it&quot; "
               "instead of &quot;I think it's the same.&quot;", BODY))

    # ============ CLOSING ============
    F.append(P("14. If You Only Remember Five Things", H1))
    F.append(table([
        ["1", "<b>The gate.</b> Validation runs before any write, so a bad night cannot publish "
              "wrong numbers. Verified by deliberately corrupting the data."],
        ["2", "<b>The negative age.</b> A real reproducibility bug in your own earlier work, "
              "found and fixed - and the check that prevents it now."],
        ["3", "<b>The key mismatch.</b> The notebook and the CSV disagreed about EmployeeID for "
              "months. Harmless until the load became incremental, at which point it broke "
              "idempotency. Found by re-testing after an assumption changed."],
        ["4", "<b>The scheduler that looked fine.</b> A task that reported &quot;Ready&quot; but "
              "failed silently - and, once that was fixed, a daily job that would never have "
              "fired at all on an unplugged laptop. Both caught because you triggered the task "
              "and read the log instead of trusting the status."],
        ["5", "<b>The date Excel moved by five months.</b> Found by doing the workflow for real. "
              "The honest lesson is where a check stops being enough, and that you move the fix "
              "to the input rather than pretending a check covers it."],
    ], [8 * mm, W - 8 * mm], header=False, fs=9.4))
    F.append(Spacer(1, 6))
    F.append(P("All five share one theme, and it's the theme to leave them with:", BODY))
    F.append(P("&quot;Every time I trusted something without checking it - the notebook output, "
               "the status of the scheduled task, the old test result, the way I thought Excel "
               "had saved my file - it turned out to be wrong. So the thing I'd say about my "
               "approach is that I test the failure path, not just the happy path, and I re-test "
               "when I change an assumption. That's what turned this from a cleaning exercise "
               "into something closer to production.&quot;", SAY))

    doc.build(F)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"written: {path}")
    print(f"size   : {path.stat().st_size:,} bytes")

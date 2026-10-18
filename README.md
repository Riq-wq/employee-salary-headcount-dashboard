<div align="center">

# Employee Salary & Headcount Dashboard

**An end-to-end HR analytics pipeline â€” from a raw, messy CSV to a decision-ready Power BI dashboard.**

`Python` Â· `Pandas` Â· `MySQL` Â· `SQL` Â· `Power BI` Â· `DAX` Â· `ReportLab`

</div>

---
## Dashboard Preview
## Dashboard Preview

![Employee Salary and Headcount Dashboard](assets/dashboard.png?v=2)



---

## ðŸŽ¯ The Business Problem

A growing company is hiring fast across several cities, but HR has no clean view of:

- **Are we paying fairly across cities â€” or is location creating hidden pay gaps?**
- **How fast is headcount growing, and where?**
- **Which hires sit far outside expected pay ranges?**

The raw export is small, inconsistent, and unaggregated, so it answers none of these directly. This project builds the pipeline that turns it into answers.

---

## ðŸ—‚ï¸ Dataset

| | |
| --- | --- |
| **Source** | Raw HR export (CSV) â€” deliberately messy, as in the real world |
| **Raw rows** | 10 |
| **Clean rows** | 9 |
| **Fields** | `EmployeeID`, `Name`, `Age`, `City`, `Salary`, `JoinDate` |
| **Coverage** | 5 Kenyan cities Â· Janâ€“May 2025 Â· ages 25â€“40 |

### ðŸ§¹ Data-Quality Issues & Cleaning Decisions

The raw export contained **7 distinct problems** â€” enough to make any naive analysis wrong. Each was fixed deliberately and documented, never silently:

| Row | Raw problem | Decision | Reasoning |
| --- | --- | --- | --- |
| `ID 2` (Bob) | `Age` blank | Imputed **29** (median age) | Median is robust to outliers; safe for a single gap |
| `ID 3` (Charlie) | `Salary` blank | Imputed **59,500** (median salary) | The 900,000 typo makes the mean unusable â€” median is safer |
| `ID 4` (Alice) | **Exact duplicate** of `ID 1` | **Row removed** | Same person twice would double-count headcount and salary bill |
| `ID 5` (Diana) | `City` blank | Recovered as **Kisumu** | *State your recovery method here â€” e.g. cross-checked the source record* |
| `ID 7` (Faith) | `Age = -5` | Corrected to **29** | A negative age is invalid data, not a real value |
| `ID 8` (George) | `Salary = 900,000` | Corrected to **90,000** | A 10Ã— typo â€” inconsistent with the role and every peer |
| `ID 9` (â€”) | `Name` blank | Recovered as **Jamal** | *State your recovery method here* |

> âš ï¸ **Why this matters.** Computed on the raw data, the average salary comes out at **KES 151,111**. The true figure is **KES 61,611** â€” the uncleaned number is **145% too high**. A single `900,000` typo and one duplicate row are enough to make a dashboard actively mislead. This step is the analysis.

---

## ðŸ—ï¸ Architecture

```mermaid
flowchart LR
    A[("ðŸ“„ Raw HR CSV")] --> B["ðŸ Python / Pandas<br/>Clean & Transform"]
    B --> C[("ðŸ—„ï¸ MySQL<br/>Structured Storage")]
    C --> D["ðŸ§® SQL Queries<br/>Business Logic"]
    D --> E["ðŸ“Š Power BI + DAX<br/>KPI Cards & Slicers"]
    E --> F["ðŸ“‘ ReportLab<br/>Automated PDF Report"]
```

**Why this order?** Each stage does one job well: Python for messy cleaning, SQL for reliable aggregation, Power BI for the visual layer, and ReportLab for a shareable report that doesn't require opening a BI tool.

---

## â“ Questions This Analysis Answers

1. What is the total headcount and salary bill?
2. How has headcount grown month over month?
3. How does average salary differ by city?
4. How does pay relate to age / experience?
5. Which employees sit outside the normal pay range?

---

## ðŸ” Key Findings

- **Headcount grew from 1 to 9 employees in five months** (Janâ€“May 2025), with a steady ~2 hires per month from February onward.
- **The pay distribution is right-skewed.** Mean salary is **KES 61,611** but the median is **KES 59,500** â€” a small number of high earners pull the average above what a typical employee earns. Any "average salary" headline is misleading on its own.
- **Nairobi pays the most â€” but the number is deceptive.** Its average of **KES 72,500** is **17.7% above the company mean**, yet that is driven almost entirely by a *single* senior hire. Nairobi's average is not evidence of a systematic city premium.
- **Nakuru is the lowest-paying city** at **KES 48,000**, **22% below** the company mean, and **Eldoret** sits at **KES 51,000**.
- **Pay rises steeply with age.** The youngest employee (25) earns **KES 55,000**; the oldest (40) earns **KES 90,000** â€” a **1.88Ã— gap**. On this dataset, age is the strongest single predictor of salary.
- **One statistical outlier.** George's **KES 90,000** sits above the Tukey upper fence of **KES 85,500** (Q1 = 53,000, Q3 = 66,000, IQR = 13,000). He is the only employee flagged.
- **Cleaning changed the entire conclusion.** Computed on the raw export, average salary reads **KES 151,111**; correctly cleaned it is **KES 61,611** â€” a **145% inflation** caused by a single `900,000` typo and one duplicated row. Untreated, this data would have produced a false narrative.

> **Recommendation**
> 1. **Introduce age/experience-based pay bands** so compensation tracks seniority explicitly rather than implicitly â€” this removes the guesswork behind city-level differences.
> 2. **Review the single senior outlier** against market benchmarks before treating Nairobi's average as a real signal.
> 3. **Add validation at the source.** A primary-key constraint to block duplicate `EmployeeID`s, a range check to reject impossible ages, and a sanity cap on `Salary` would have caught all 7 issues before they reached a report â€” this is cheaper than cleaning downstream every time.

---

## ðŸ“Š Dashboard Features

- **KPI cards** â€” total headcount, total salary bill, average salary
- **Headcount trend line** â€” monthly hiring, Janâ€“May 2025
- **City slicer** â€” filter every visual by location
- **Average salary by city** â€” ranked comparison
- **Age vs salary scatter** â€” visualises the experienceâ€“pay relationship and isolates the outlier
- **Automated PDF export** â€” a shareable report generated with ReportLab

---

## ðŸ“ Repository Structure

```
employee-salary-headcount-dashboard/
â”œâ”€â”€ assets/
â”‚   â””â”€â”€ dashboard.png          # dashboard screenshot
â”œâ”€â”€ data/
â”‚   â””â”€â”€ raw_employees.csv      # source data
â”œâ”€â”€ notebooks/
â”‚   â””â”€â”€ cleaning.ipynb         # Python/Pandas cleaning
â”œâ”€â”€ sql/
â”‚   â””â”€â”€ analysis_queries.sql   # business-logic queries
â”œâ”€â”€ reports/
â”‚   â””â”€â”€ employee_report.pdf    # ReportLab output
â”œâ”€â”€ dashboard.pbix             # Power BI file
â””â”€â”€ README.md
```



---

## â–¶ï¸ How to Reproduce

```bash
# 1. Clone
git clone https://github.com/Riq-wq/employee-salary-headcount-dashboard.git
cd employee-salary-headcount-dashboard

# 2. Install Python dependencies
pip install pandas mysql-connector-python reportlab

# 3. Run the cleaning script
python notebooks/cleaning.py

# 4. Load into MySQL
mysql -u <user> -p < schema.sql

# 5. Open dashboard.pbix in Power BI Desktop and refresh
```

---

## ðŸ§  Skills Demonstrated

| Skill | Where |
| --- | --- |
| **Data cleaning** â€” missing values, duplicate detection, invalid ranges, outlier correction | `notebooks/cleaning.ipynb` |
| **Relational storage & schema design** | MySQL |
| **Business-logic SQL** â€” aggregation, grouping, ranking | `sql/analysis_queries.sql` |
| **Distribution analysis** â€” mean vs median, IQR outlier detection | Analysis + report |
| **Data modeling & DAX measures** | Power BI |
| **Automated reporting** | ReportLab |
| **End-to-end pipeline thinking** | Whole repo |

---

## ðŸš€ What I'd Do Next

- Add **department / job-title data** to separate *pay-for-role* from *pay-for-location* â€” the current data can't distinguish them.
- Add **salary-benchmark comparison** against external market data.
- Scale the pipeline to a **scheduled cloud refresh** (dbt + a warehouse) as headcount grows.

---

<div align="center">
<sub>Built by <a href="https://github.com/Riq-wq">Hassan Jumaa</a> Â· <a href="https://riq-wq.github.io/Myportfolio/">Portfolio</a> Â· <a href="https://www.linkedin.com/in/mrisa-juma-56a600416">LinkedIn</a></sub>
</div>


# Employee Salary & Headcount Dashboard

An end-to-end data analytics project: cleaning raw employee HR data with Python, storing it in MySQL, querying it with SQL, and visualizing salary and headcount trends in an interactive Power BI dashboard.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat&logo=pandas&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat&logo=mysql&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-F2C811?style=flat&logo=powerbi&logoColor=black)

---

## Project Overview

This project takes a messy, real-world-style HR dataset (duplicates, missing values, invalid entries, salary outliers) through a full analytics pipeline:

1. **Clean** — Python (Pandas, NumPy) in a Jupyter notebook
2. **Store** — Load the cleaned data into a MySQL database
3. **Query** — Explore and aggregate the data with SQL
4. **Visualize** — Build an interactive Power BI dashboard with KPIs, charts, and slicers
5. **Report** — Export key findings as a shareable PDF report

The dataset covers 9 employees across 5 Kenyan cities: Nairobi, Mombasa, Kisumu, Nakuru, and Eldoret.

---

## Repository Structure

```
employee-salary-headcount-dashboard/
├── data/
│   ├── employee_dataset_raw.csv          # Original, uncleaned dataset
│   └── employee_dataset_cleaned.csv      # Cleaned dataset after processing
├── notebooks/
│   └── employee_data_cleaning.ipynb      # Python/Pandas cleaning pipeline
├── sql/
│   └── employees_queries.sql             # SQL analysis queries
├── dashboard/
│   └── Employee_salary_dashboard.pbix    # Power BI dashboard file
├── reports/
│   ├── Employee_Salary_Dashboard_Report.pdf
│   └── charts/                           # Chart images used in the report
└── README.md
```

---

## Data Cleaning

The raw dataset contained several common real-world data quality issues, each handled explicitly in the cleaning notebook:

| Issue | Resolution |
|---|---|
| Duplicate employee records | Dropped exact duplicate rows |
| Missing employee name | Filled with a placeholder, corrected manually |
| Missing age values | Filled with median age |
| Invalid negative age | Reset to missing, re-filled with median, rounded to whole years |
| Missing salary value | Filled with median salary |
| Missing city value | Filled with the most frequent city (mode) |
| Salary outlier (KES 900,000) | Reviewed against IQR bounds and corrected |
| Inconsistent date format | Parsed as day-first dates and standardized |

---

## SQL Analysis

The `sql/employees_queries.sql` file includes queries covering:
- Total employee count and total salary expense
- Highest- and lowest-paid employees
- Average salary and average age
- Salary and headcount breakdowns by city
- Employees earning above the company average
- Hiring trends by month

---

## Power BI Dashboard

The dashboard includes:
- **KPI cards** — Total Employees, Total Salary Expense, Average Salary, Average Age
- **Bar chart** — Average salary by city
- **Column chart** — Headcount by city
- **Line chart** — Hiring trend by month
- **Table** — Employees ranked by salary
- **Slicers** — Filter by City and by Month hired

### Key Findings
- Nairobi has the highest average salary (KES 72,500); Nakuru has the lowest (KES 48,000)
- Kisumu has the largest headcount (3 employees)
- Hiring was steady across the first five months of 2025
- Total salary expense across all employees: KES 554,500

---

## How to Run This Project

1. Clone the repository
   ```bash
   git clone https://github.com/Riq-wq/employee-salary-headcount-dashboard.git
   ```
2. Open `notebooks/employee_data_cleaning.ipynb` to view/re-run the cleaning pipeline
3. Load the cleaned CSV into MySQL, or run the queries in `sql/employees_queries.sql` against your own instance
4. Open `dashboard/Employee_salary_dashboard.pbix` in Power BI Desktop to explore the interactive dashboard
5. View `reports/Employee_Salary_Dashboard_Report.pdf` for a static summary of findings

---

## Tools & Skills Demonstrated

Python · Pandas · NumPy · SQL · MySQL · Power BI · DAX · Data Cleaning · Data Visualization

---

## Author

**Hassan Jumaa (Riq)**
Data Analyst | [GitHub](https://github.com/Riq-wq)

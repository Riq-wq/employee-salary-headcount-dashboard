#!/usr/bin/env python3
"""
Chart generator for the Employee Salary & Headcount report.

Why this file exists
--------------------
The three PNGs in ``reports/charts/`` used to be static files with no
generator anywhere in the repo. ``generate_report.py`` simply embedded
whatever was on disk, so a freshly generated PDF could have shown
nine-employee charts sitting next to ten-employee tables - two different
datasets in one document, with nothing to warn you.

That is precisely the "stale artefact" failure this project exists to
prevent, so the charts are now generated from the same cleaned CSV that
feeds the tables, and ``generate_report.py`` calls this module before it
renders. The PDF can no longer carry a chart from an earlier run.

    python reports/make_charts.py

Everything is derived from the data: the city lists, the headcounts, the
averages and the month buckets are all read from the cleaned CSV, so a
new employee changes the charts without anyone editing a label.
"""

from __future__ import annotations

import csv
import statistics
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: must work on a machine with no display
import matplotlib.pyplot as plt  # noqa: E402

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
CLEAN_CSV = ROOT / "data" / "employee_dataset_cleaned.csv"
CHART_DIR = ROOT / "reports" / "charts"

# --------------------------------------------------------------------------
# Palette
#
# Sampled from the PNGs that were previously committed by hand, so the
# regenerated charts keep the look the report was designed around instead
# of replacing it with a different house style.
# --------------------------------------------------------------------------
BLUE = "#4472C4"   # average salary bars
TEAL = "#2E8B8B"   # headcount bars
NAVY = "#1F3864"   # cumulative headcount line
BAND = "#E8EAEF"   # new-hires bars
EDGE = "#AAB3C4"   # new-hires bar edges / area outline
INK = "#2A2A2A"    # value labels
MUTED = "#64748B"  # axis text
RULE = "#E2E8F0"   # baseline

# The PDF scales every chart to CONTENT_W wide and CONTENT_W * 480/900 high,
# so the PNGs must be exactly 900 x 480 or the report distorts them.
FIG_W, FIG_H, DPI = 9.0, 4.8, 100


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def load(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def city_rollup(rows: list[dict]) -> list[tuple[str, int, float]]:
    """(city, headcount, average salary) ordered by headcount, then name.

    Both city charts use this one order, so the same city sits in the same
    horizontal position in each and the two can be read against each other.
    """
    grouped: dict[str, list[int]] = {}
    for r in rows:
        grouped.setdefault(r["City"], []).append(int(r["Salary"]))
    return sorted(
        ((city, len(vals), statistics.mean(vals)) for city, vals in grouped.items()),
        key=lambda t: (-t[1], t[0]),
    )


def monthly_hires(rows: list[dict]) -> tuple[list[str], list[int], list[int]]:
    """(month labels, new hires, cumulative headcount) in join order."""
    counts: dict[str, int] = {}
    for r in rows:
        label = datetime.strptime(r["JoinDate"], "%d/%m/%Y").strftime("%b")
        counts[label] = counts.get(label, 0) + 1

    labels = list(counts)
    hires = [counts[m] for m in labels]
    running, cumulative = 0, []
    for h in hires:
        running += h
        cumulative.append(running)
    return labels, hires, cumulative


# --------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------
def _clean_frame(ax) -> None:
    """Strip matplotlib's default chrome - the report supplies the titles."""
    ax.set_facecolor("white")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.spines["bottom"].set_linewidth(1.0)
    ax.set_yticks([])
    ax.tick_params(axis="x", colors=MUTED, labelsize=9.5, length=0, pad=6)
    ax.margins(x=0.02)


def _bar_labels(ax, bars, values, fmt) -> None:
    for bar, value in zip(bars, values):
        ax.annotate(
            fmt(value),
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center", va="bottom",
            fontsize=9.5, color=INK,
        )


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
def salary_by_city(rows: list[dict]) -> Path:
    rollup = city_rollup(rows)
    cities = [c for c, _, _ in rollup]
    averages = [a for _, _, a in rollup]

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor("white")
    bars = ax.bar(cities, averages, color=BLUE, width=0.56)
    _clean_frame(ax)
    _bar_labels(ax, bars, averages, lambda v: f"{v:,.0f}")
    ax.set_ylim(0, max(averages) * 1.22)

    path = CHART_DIR / "salary_by_city.png"
    fig.tight_layout(pad=1.1)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def headcount_by_city(rows: list[dict]) -> Path:
    rollup = city_rollup(rows)
    cities = [c for c, _, _ in rollup]
    counts = [n for _, n, _ in rollup]

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor("white")
    bars = ax.bar(cities, counts, color=TEAL, width=0.56)
    _clean_frame(ax)
    _bar_labels(ax, bars, counts, lambda v: f"{int(v)}")
    ax.set_ylim(0, max(counts) * 1.22)

    path = CHART_DIR / "headcount_by_city.png"
    fig.tight_layout(pad=1.1)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def hiring_trend(rows: list[dict]) -> Path:
    labels, hires, cumulative = monthly_hires(rows)

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor("white")

    bars = ax.bar(labels, hires, color=BAND, edgecolor=EDGE, width=0.5)
    _clean_frame(ax)
    _bar_labels(ax, bars, hires, lambda v: f"{int(v)}")
    ax.set_ylim(0, max(hires) * 1.30)

    # Cumulative headcount on its own scale, so the shape of the ramp is
    # readable even when the monthly counts are small.
    twin = ax.twinx()
    twin.plot(labels, cumulative, color=NAVY, marker="o", markersize=5,
              linewidth=2.0, zorder=3)
    for x, y in zip(labels, cumulative):
        twin.annotate(str(y), xy=(x, y), xytext=(0, -16), textcoords="offset points",
                      ha="center", fontsize=8.5, color=NAVY)
    twin.set_ylim(0, max(cumulative) * 1.35)
    twin.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        twin.spines[side].set_visible(False)

    path = CHART_DIR / "hiring_trend.png"
    fig.tight_layout(pad=1.1)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def build_all(rows: list[dict] | None = None) -> list[Path]:
    """Rebuild all three charts from the cleaned CSV."""
    if rows is None:
        rows = load(CLEAN_CSV)
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    return [salary_by_city(rows), headcount_by_city(rows), hiring_trend(rows)]


if __name__ == "__main__":
    for p in build_all():
        print(f"Written : {p}")

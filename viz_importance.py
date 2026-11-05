"""Ranked dot plot: how much each variable separates who enrolls (admitted students).

Input : data_clean.csv
Output: factor_importance.png (dpi=200), importance_groups.csv, importance_all.csv

For each variable, admitted students are split into groups (bins for numeric variables,
missing values as their own "Missing" group). Gap = max - min enrollment rate across
groups with at least MIN_GROUP_N students. Variables with fewer than 2 such groups are
not plotted.
"""
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MultipleLocator
from sklearn.isotonic import IsotonicRegression

IN_PATH = "data_clean.csv"
DATE_COLS = ["app_date", "deposit_date", "visit_date", "first_contact_date"]
OUT_PNG = "factor_importance.png"
OUT_GROUPS = "importance_groups.csv"
OUT_ALL = "importance_all.csv"
MIN_GROUP_N = 300
INF = np.inf

BG, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
C_TOP, C_MID, C_BOTTOM, STEM = "#2166ac", "#c4c4c4", "#b2182b", "#d4d3cf"
TAIL = 0.15

# Reference gaps (percentage points) from an earlier analysis
REFERENCE_GAPS = {"Application fee": 51.6, "Campus visits": 48.6, "Residency": 39.0,
                  "Legacy": 19.2, "Sex": 4.1, "First generation": 0.5}


# ---------------------------------------------------------------- grouping helpers
def bins(col, edges, labels):
    """Left-closed, right-open bins; missing -> "Missing"."""
    def f(d):
        g = pd.cut(d[col], edges, right=False, labels=labels).astype(object)
        return g.where(d[col].notna(), "Missing")
    return f, list(labels) + ["Missing"]


def raw(col, order):
    def f(d):
        return d[col].astype(object).where(d[col].notna(), "Missing")
    return f, list(order) + ["Missing"]


def yes_no(col):
    def f(d):
        return d[col].map({1: "Yes", 0: "No"}).astype(object).where(d[col].notna(), "Missing")
    return f, ["No", "Yes", "Missing"]


def campus_visits(d):
    v = d["campus_visit_tot"]
    return pd.Series(np.select([v == 0, v == 1], ["0", "1"], default="2+"), index=d.index)


def visit_timing(d):
    return pd.Series(np.select(
        [d["visit_date"].isna(), d["visit_date"] < d["app_date"]],
        ["No visit", "Last visit before applying"], default="Last visit after applying"),
        index=d.index)


def application_month(d):
    idx = (d["app_date"].dt.year - d["entry_year"]) * 12 + d["app_date"].dt.month
    return pd.Series(np.select(
        [idx <= -4, idx <= -2, idx <= 0],
        ["Jun–Aug (prior yr)", "Sep–Oct", "Nov–Dec"], default="Jan or later"),
        index=d.index)


def first_contact(d):
    start = pd.to_datetime(dict(year=d["entry_year"], month=8, day=25))
    days = (start - d["first_contact_date"]).dt.days
    g = pd.cut(days, [0, 365, 540, 730, INF], right=False,
               labels=["<1 yr", "1–1.5 yr", "1.5–2 yr", "2+ yr"]).astype(object)
    return g.where(days.notna(), "Missing")


def test_score(d):
    """act_cmpst, else SAT converted to the ACT scale; neither -> "None submitted"."""
    g = pd.cut(d["test_act_scale"], [0, 21, 25, 29, INF], right=False,
               labels=["<21", "21–24", "25–28", "29+"]).astype(object)
    return g.where(d["test_act_scale"].notna(), "None submitted")


def add_test_scale(df):
    """Fit isotonic SAT -> ACT on all students with both scores; adds test_act_scale."""
    both = df["act_cmpst"].notna() & df["sat_comb"].notna()
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(df.loc[both, "sat_comb"], df.loc[both, "act_cmpst"])
    sat_conv = pd.Series(np.nan, index=df.index)
    has_sat = df["sat_comb"].notna()
    sat_conv[has_sat] = iso.predict(df.loc[has_sat, "sat_comb"])
    df["test_act_scale"] = df["act_cmpst"].fillna(sat_conv)
    return int(both.sum())


CR4 = ([0, 8, 9, 11, INF], ["<8", "8", "9–10", "11+"])
CR3 = ([0, 8, 9, INF], ["<8", "8", "9+"])
CR01 = ([0, 1, INF], ["0", "1+"])
COLLEGES = ["Applied Science and Engineering", "Business, Finance and Industry",
            "Land, Environment and Food Sciences", "Liberal Arts and Sciences",
            "Performing and Fine Arts", "Public Health and Translational Science"]

# (variable name, theme, (group function, group order))
VARIABLES = [
    # Geography & contact
    ("Residency", "Geography & contact", raw("residency", ["Resident", "Contiguous", "Non-Contiguous"])),
    ("Distance (miles)", "Geography & contact",
     bins("miles_from_campus", [0, 50, 100, 200, 500, INF],
          ["0–49", "50–99", "100–199", "200–499", "500+"])),
    ("Campus visits", "Geography & contact", (campus_visits, ["0", "1", "2+"])),
    ("Visit timing", "Geography & contact",
     (visit_timing, ["No visit", "Last visit before applying", "Last visit after applying"])),
    ("Stealth applicant", "Geography & contact", yes_no("stealth")),
    ("Application month", "Geography & contact",
     (application_month, ["Jun–Aug (prior yr)", "Sep–Oct", "Nov–Dec", "Jan or later"])),
    ("First contact (days before start)", "Geography & contact",
     (first_contact, ["<1 yr", "1–1.5 yr", "1.5–2 yr", "2+ yr", "Missing"])),
    ("Application fee", "Geography & contact", raw("app_fee", ["Paid", "Deferred", "Waived"])),
    # Background
    ("Legacy", "Background", yes_no("legacy")),
    ("First generation", "Background", yes_no("first_generation")),
    ("URM", "Background", yes_no("urm")),
    ("Veteran", "Background", yes_no("veteran")),
    ("ROTC interest", "Background", yes_no("rotc_interest")),
    ("Sex", "Background", raw("sex", ["F", "M"])),
    ("Age", "Background", bins("age", [0, 18, 19, 20, INF], ["≤17", "18", "19", "20+"])),
    # Academics
    ("HS GPA", "Academics",
     bins("hs_gpa", [0, 3.0, 3.5, 4.0, INF], ["<3.0", "3.0–3.49", "3.5–3.99", "4.0+"])),
    ("Test score (ACT scale)", "Academics",
     (test_score, ["<21", "21–24", "25–28", "29+", "None submitted"])),
    ("HS rank (percentile)", "Academics",
     bins("hs_rank", [0, 0.5, 50, 75, 90, 101], ["0", "1–49", "50–74", "75–89", "90–100"])),
    ("HS math credits", "Academics", bins("hs_math", *CR4)),
    ("HS science credits", "Academics", bins("hs_sci", *CR4)),
    ("HS-only math credits", "Academics", bins("hs_only_math", *CR4)),
    ("HS-only science credits", "Academics", bins("hs_only_sci", *CR4)),
    ("HS English credits", "Academics", bins("hs_engl", *CR3)),
    ("HS social science credits", "Academics", bins("hs_ss", *CR3)),
    ("HS foreign language credits", "Academics",
     bins("hs_flang", [0, 4, 8, 9, INF], ["<4", "4–7", "8", "9+"])),
    ("HS algebra credits", "Academics", bins("hs_algbr_cr", [0, 4, 5, INF], ["<4", "4", "5+"])),
    ("HS geometry credits", "Academics", bins("hs_geom_cr", [0, 2, 3, INF], ["<2", "2", "3+"])),
    ("HS trig credits", "Academics", bins("hs_trig_cr", [0, 1, 2, INF], ["0", "1", "2+"])),
    ("HS calculus credits", "Academics", bins("hs_calc_cr", *CR01)),
    ("College math credits", "Academics", bins("coll_math", *CR01)),
    ("College science credits", "Academics", bins("coll_sci", *CR01)),
    ("College algebra credits", "Academics", bins("coll_algbr_cr", *CR01)),
    ("College geometry credits", "Academics", bins("coll_geom_cr", *CR01)),
    ("College trig credits", "Academics", bins("coll_trig_cr", *CR01)),
    ("College calculus credits", "Academics", bins("coll_calc_cr", *CR01)),
    # Major & intentions
    ("College (intended)", "Major & intentions", raw("college", COLLEGES)),
    ("STEM major", "Major & intentions", yes_no("stem_major")),
    ("Undecided major", "Major & intentions", yes_no("undecided")),
    ("Expects grad school", "Major & intentions", yes_no("grad_expct")),
    ("Help: educational planning", "Major & intentions", yes_no("ed_plan_asst")),
    ("Help: writing", "Major & intentions", yes_no("wrtng_asst")),
    ("Help: reading", "Major & intentions", yes_no("read_asst")),
    ("Help: study skills", "Major & intentions", yes_no("study_skll_asst")),
    ("Help: math", "Major & intentions", yes_no("math_asst")),
]


# ---------------------------------------------------------------- compute
def compute(adm):
    group_rows, all_rows = [], []
    for name, theme, (fn, order) in VARIABLES:
        g = fn(adm)
        stats = adm.groupby(g, sort=False)["enrolled"].agg(n="size", enroll_rate="mean")
        stats = stats.reindex([o for o in order if o in stats.index]
                              + [o for o in stats.index if o not in order])
        stats["counted"] = stats["n"] >= MIN_GROUP_N
        for grp, r in stats.iterrows():
            group_rows.append({"variable": name, "theme": theme, "group": grp, "n": int(r["n"]),
                               "enroll_rate": r["enroll_rate"], "counted": bool(r["counted"])})
        c = stats[stats["counted"]]
        row = {"variable": name, "theme": theme, "n_groups": len(stats), "n_groups_counted": len(c)}
        if len(c) >= 2:
            hi, lo = c["enroll_rate"].idxmax(), c["enroll_rate"].idxmin()
            row.update(gap_pts=100 * (c.loc[hi, "enroll_rate"] - c.loc[lo, "enroll_rate"]),
                       top_group=hi, top_rate=c.loc[hi, "enroll_rate"], top_n=int(c.loc[hi, "n"]),
                       bottom_group=lo, bottom_rate=c.loc[lo, "enroll_rate"],
                       bottom_n=int(c.loc[lo, "n"]))
        all_rows.append(row)
    groups = pd.DataFrame(group_rows)
    summary = pd.DataFrame(all_rows)
    summary = summary.sort_values("gap_pts", ascending=False, na_position="last").reset_index(drop=True)
    return groups, summary


# ---------------------------------------------------------------- plot
def plot(summary, n_adm, rate_adm, out_path):
    plt.rcParams["font.family"] = "DejaVu Sans"
    s = summary.dropna(subset=["gap_pts"]).sort_values("gap_pts").reset_index(drop=True)
    hi_cut, lo_cut = np.quantile(s["gap_pts"], 1 - TAIL), np.quantile(s["gap_pts"], TAIL)
    colors = np.where(s["gap_pts"] >= hi_cut, C_TOP, np.where(s["gap_pts"] <= lo_cut, C_BOTTOM, C_MID))
    median = float(np.median(s["gap_pts"]))

    row_h = 0.27
    plot_h = row_h * len(s)
    top_in, bottom_in = 1.55, 1.25
    fig_h = plot_h + top_in + bottom_in
    fig_w = 10
    left_in, right_in = 2.9, 0.4
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=BG)
    ax = fig.add_axes([left_in / fig_w, bottom_in / fig_h,
                       1 - (left_in + right_in) / fig_w, plot_h / fig_h])
    ax.set_facecolor(BG)

    y = np.arange(len(s))
    ax.hlines(y, 0, s["gap_pts"], color=STEM, linewidth=1.2, zorder=2)
    ax.scatter(s["gap_pts"], y, s=46, c=colors, zorder=3, linewidths=0)

    ax.axvline(median, color=MUTED, linestyle=(0, (4, 3)), linewidth=1, zorder=1)
    ax.text(median + 0.6, len(s) - 0.4, f"Median: {median:.1f} pts", ha="left", va="center",
            fontsize=9, color=MUTED)

    ax.set_yticks(y)
    ax.set_yticklabels(s["variable"], fontsize=9.5, color=INK)
    ax.set_ylim(-0.7, len(s) - 0.3)
    xmax = np.ceil(s["gap_pts"].max() / 10) * 10
    ax.set_xlim(0, xmax)
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f} pts"))
    ax.tick_params(axis="x", colors=MUTED, labelsize=9, length=0, pad=6)
    ax.tick_params(axis="y", length=0, pad=6)
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlabel("Gap in enrollment rate between a variable's highest and lowest group "
                  "(percentage points)", fontsize=9.5, color=MUTED, labelpad=8)

    x0 = 0.35 / fig_w
    fig.text(x0, 1 - 0.3 / fig_h, "How much does each variable separate who enrolls?",
             ha="left", va="top", fontsize=17, fontweight="bold", color=INK)
    fig.text(x0, 1 - 0.72 / fig_h,
             f"Admitted students, 2022–2026 (n = {n_adm:,}; overall enrollment rate {rate_adm:.0%})",
             ha="left", va="top", fontsize=10.5, color=MUTED)

    handles = [Line2D([], [], marker="o", linestyle="", markersize=7.5, markerfacecolor=c,
                      markeredgewidth=0) for c in (C_TOP, C_MID, C_BOTTOM)]
    fig.legend(handles, ["Top 15%", "Middle", "Bottom 15%"], loc="upper left",
               bbox_to_anchor=(x0 - 0.008, 1 - 1.02 / fig_h), ncol=3, frameon=False,
               fontsize=9.5, handletextpad=0.3, columnspacing=1.4, labelcolor=INK)

    foot = ("Each variable is split into groups (bins for numeric variables); only groups with "
            f"≥{MIN_GROUP_N} students count. One variable at a time, not adjusted for the others; "
            "association, not cause.")
    fig.text(x0, 0.25 / fig_h, textwrap.fill(foot, 125), ha="left", va="bottom",
             fontsize=8.5, color=MUTED, linespacing=1.4)

    fig.savefig(out_path, dpi=200, facecolor=BG)
    plt.close(fig)
    return median, hi_cut, lo_cut


# ---------------------------------------------------------------- report
def report(df, adm, n_fit, groups, summary, median, hi_cut, lo_cut):
    print("=== Sample ===")
    print(f"admitted == 1: {len(adm):,} (expected 62,071); "
          f"enrollment rate {adm['enrolled'].mean():.2%} (expected ~37.1%)")
    print(f"SAT -> ACT isotonic fit on {n_fit:,} students with both scores (expected ~3,430)")
    print(f"Variables defined: {len(VARIABLES)}")

    print(f"\n=== Gap ranking (median {median:.1f} pts; top 15% >= {hi_cut:.1f}, "
          f"bottom 15% <= {lo_cut:.1f}) ===")
    ranked = summary.dropna(subset=["gap_pts"]).copy()
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    with pd.option_context("display.width", 200, "display.max_colwidth", 30):
        print(ranked.assign(
            gap_pts=ranked["gap_pts"].round(1),
            top=ranked["top_group"].astype(str) + " (" + (100 * ranked["top_rate"]).round(1).astype(str) + "%)",
            bottom=ranked["bottom_group"].astype(str) + " (" + (100 * ranked["bottom_rate"]).round(1).astype(str) + "%)",
        )[["rank", "variable", "gap_pts", "top", "bottom", "n_groups_counted", "n_groups"]].to_string(index=False))

    print("\n=== Variables with fewer than 2 groups of >= 300 ===")
    few = summary[summary["gap_pts"].isna()]
    print("None" if few.empty else few[["variable", "n_groups_counted", "n_groups"]].to_string(index=False))

    print("\n=== Reference check (gap, pts) ===")
    gap = summary.set_index("variable")["gap_pts"]
    for name, ref in REFERENCE_GAPS.items():
        diff = gap[name] - ref
        flag = "" if abs(diff) <= 0.5 else "  <- differs by more than 0.5"
        print(f"{name:20s} {gap[name]:5.1f}  (reference {ref:4.1f}, diff {diff:+.1f}){flag}")

    geo = groups[(groups["variable"] == "HS geometry credits") & (groups["group"] == "<2")]
    sub = adm[adm["hs_geom_cr"] < 2]
    print("\n=== HS geometry credits, group \"<2\" ===")
    print(f"n = {int(geo['n'].iloc[0]):,}, enrollment rate {geo['enroll_rate'].iloc[0]:.1%}; "
          f"hs_geom_cr == 0: {int((sub['hs_geom_cr'] == 0).sum()):,}, "
          f"hs_geom_cr == 1: {int((sub['hs_geom_cr'] == 1).sum()):,}")


def main():
    df = pd.read_csv(IN_PATH, parse_dates=DATE_COLS)
    n_fit = add_test_scale(df)
    adm = df[df["admitted"] == 1].copy()

    groups, summary = compute(adm)
    groups.to_csv(OUT_GROUPS, index=False)
    summary.to_csv(OUT_ALL, index=False)

    median, hi_cut, lo_cut = plot(summary, len(adm), adm["enrolled"].mean(), OUT_PNG)
    report(df, adm, n_fit, groups, summary, median, hi_cut, lo_cut)
    print(f"\nSaved {OUT_PNG}, {OUT_GROUPS}, {OUT_ALL}")


if __name__ == "__main__":
    main()

"""Heatmap: enrollment rate of admitted students by residency x test score.

Input : data_clean.csv
Output: heatmap_residency_test.png (dpi=200), heatmap_table.csv
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_rgb
from matplotlib.patches import Rectangle
from matplotlib.ticker import PercentFormatter
from sklearn.isotonic import IsotonicRegression

IN_PATH = "data_clean.csv"
DATE_COLS = ["app_date", "deposit_date", "visit_date", "first_contact_date"]
OUT_PNG = "heatmap_residency_test.png"
OUT_TABLE = "heatmap_table.csv"

BG, INK, MUTED = "#fcfcfb", "#0b0b0b", "#52514e"
BLUES = ["#eff3ff", "#bdd7e7", "#6baed6", "#3182bd", "#08519c"]   # ColorBrewer Blues
VMIN, VMAX = 0.0, 0.8
MIN_N = 300

ROWS = [("Resident", "In-state"), ("Contiguous", "Bordering state"),
        ("Non-Contiguous", "Non-bordering state")]
COLS = ["No test submitted", "<21", "21–24", "25–28", "29+"]


def add_test_scale(df):
    """Unified ACT-scale score: act_cmpst, else SAT converted by isotonic regression
    fit on all students with both scores. Returns the number of students used in the fit."""
    both = df["act_cmpst"].notna() & df["sat_comb"].notna()
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(df.loc[both, "sat_comb"], df.loc[both, "act_cmpst"])
    sat_conv = pd.Series(np.nan, index=df.index)
    has_sat = df["sat_comb"].notna()
    sat_conv[has_sat] = iso.predict(df.loc[has_sat, "sat_comb"])
    df["test_act_scale"] = df["act_cmpst"].fillna(sat_conv)
    return int(both.sum())


def build_table(df):
    adm = df[df["admitted"] == 1].copy()
    score = adm["test_act_scale"]
    adm["score_group"] = (pd.cut(score, [0, 21, 25, 29, np.inf], right=False, labels=COLS[1:])
                          .astype(object).where(score.notna(), COLS[0]))
    t = (adm.groupby(["residency", "score_group"])["enrolled"]
            .agg(n="size", enrolled="sum", enroll_rate="mean").reset_index())
    t["group"] = t["residency"].map(dict(ROWS))
    t["row"] = t["residency"].map({r: i for i, (r, _) in enumerate(ROWS)})
    t["col"] = t["score_group"].map({c: j for j, c in enumerate(COLS)})
    t = t.sort_values(["row", "col"]).reset_index(drop=True)
    return adm, t[["residency", "group", "score_group", "n", "enrolled", "enroll_rate", "row", "col"]]


def luminance(hex_color):
    r, g, b = to_rgb(hex_color)
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def plot(table, n_adm, n_fit, out_path):
    plt.rcParams["font.family"] = "DejaVu Sans"
    cmap = LinearSegmentedColormap.from_list("blues5", BLUES)
    norm = Normalize(VMIN, VMAX)

    fig_w, fig_h = 11, 5.9
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=BG)
    ax = fig.add_axes([2.0 / fig_w, 1.25 / fig_h, 7.9 / fig_w, 3.15 / fig_h])
    cax = fig.add_axes([10.15 / fig_w, 1.25 / fig_h, 0.14 / fig_w, 3.15 / fig_h])
    ax.set_facecolor(BG)

    any_small = False
    for r in table.itertuples():
        color = cmap(norm(r.enroll_rate))
        ax.add_patch(Rectangle((r.col, r.row), 1, 1, facecolor=color, edgecolor=BG, linewidth=4))
        txt = "white" if luminance(matplotlib.colors.to_hex(color)) < 0.3 else INK
        star = "*" if r.n < MIN_N else ""
        any_small |= bool(star)
        ax.text(r.col + 0.5, r.row + 0.42, f"{r.enroll_rate:.0%}", ha="center", va="center",
                fontsize=15, fontweight="bold", color=txt)
        ax.text(r.col + 0.5, r.row + 0.70, f"n={r.n:,}{star}", ha="center", va="center",
                fontsize=9.5, color=txt)

    ax.set_xlim(0, len(COLS))
    ax.set_ylim(len(ROWS), 0)
    ax.set_xticks(np.arange(len(COLS)) + 0.5)
    ax.set_xticklabels(COLS, fontsize=10.5, color=INK)
    ax.set_yticks(np.arange(len(ROWS)) + 0.5)
    ax.set_yticklabels([g for _, g in ROWS], fontsize=10.5, color=INK, fontweight="bold")
    ax.tick_params(length=0, pad=7)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlabel("Test score (ACT scale; SAT converted)", fontsize=10, color=MUTED, labelpad=10)

    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax)
    cb.outline.set_visible(False)
    cb.set_ticks(np.arange(0, 0.81, 0.2))
    cb.ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    cb.ax.tick_params(labelsize=9, colors=MUTED, length=0, pad=4)
    cb.ax.set_title("Enrollment\nrate", fontsize=9, color=MUTED, loc="left", pad=8)

    x0 = 0.35 / fig_w
    fig.text(x0, 1 - 0.3 / fig_h, "Enrollment rate of admitted students, by residency and test score",
             ha="left", va="top", fontsize=16, fontweight="bold", color=INK)
    fig.text(x0, 1 - 0.75 / fig_h,
             "In every residency group, top scorers (29+) have the lowest rate among students who "
             "sent a score;\nstudents who sent no score almost never enroll.",
             ha="left", va="top", fontsize=10.5, color=MUTED, linespacing=1.45)

    foot = (f"Admitted students, 2022–2026 (n = {n_adm:,}). SAT converted to the ACT scale by "
            f"isotonic regression fit on {n_fit:,} students with both scores.")
    if any_small:
        foot += f"\n* fewer than {MIN_N} students; rate is less reliable."
    fig.text(x0, 0.2 / fig_h, foot, ha="left", va="bottom", fontsize=8.5, color=MUTED,
             linespacing=1.4)

    fig.savefig(out_path, dpi=200, facecolor=BG)
    plt.close(fig)


def main():
    df = pd.read_csv(IN_PATH, parse_dates=DATE_COLS)
    n_fit = add_test_scale(df)
    adm, table = build_table(df)
    table.drop(columns=["row", "col"]).to_csv(OUT_TABLE, index=False)

    print(f"Admitted: {len(adm):,}; isotonic fit on {n_fit:,} students with both scores")
    print((table.pivot(index="group", columns="score_group", values="enroll_rate")
                .loc[[g for _, g in ROWS], COLS] * 100).round(1).to_string())
    print(table.pivot(index="group", columns="score_group", values="n")
               .loc[[g for _, g in ROWS], COLS].to_string())
    plot(table, len(adm), n_fit, OUT_PNG)
    print(f"Saved {OUT_PNG}, {OUT_TABLE}")


if __name__ == "__main__":
    main()

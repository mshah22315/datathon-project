"""Admissions funnel by residency (alluvial-style).

Input : data_clean.csv
Output: funnel.png (dpi=200), funnel_table.csv
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

IN_PATH = "data_clean.csv"
DATE_COLS = ["app_date", "deposit_date", "visit_date", "first_contact_date"]
OUT_PNG = "funnel.png"
OUT_TABLE = "funnel_table.csv"

BG, INK, MUTED, LOSS = "#fcfcfb", "#0b0b0b", "#52514e", "#b2182b"
GROUPS = [  # residency value, display name, color (top to bottom)
    ("Resident", "In-state", "#2a78d6"),
    ("Contiguous", "Bordering state", "#eb6834"),
    ("Non-Contiguous", "Non-bordering state", "#1baf7a"),
]
RIBBON_ALPHA = 0.28
BAR_W = 0.13          # bar width in stage units (stages are 1 apart)
GAP = 1100            # vertical gap between segments, in students


def stage_masks(df):
    admitted = df["admitted"] == 1
    return {
        "Applied": pd.Series(True, index=df.index),
        "Completed application": df["app_completed"] == 1,
        "Admitted": admitted,
        "Paid deposit": admitted & (df["deposit_paid"] == 1),
        "Enrolled": df["enrolled"] == 1,
    }


def build_table(df):
    masks = stage_masks(df)
    counts = pd.DataFrame({s: m.groupby(df["residency"]).sum() for s, m in masks.items()})
    counts = counts.loc[[g[0] for g in GROUPS]].astype(int)

    stages = list(masks)
    for a, b in zip(stages[:-1], stages[1:]):
        if (masks[b] & ~masks[a]).any():
            raise ValueError(f"'{b}' is not a subset of '{a}'")
        grew = counts[b] > counts[a]
        if grew.any():
            raise ValueError(f"Group count increases from '{a}' to '{b}': {list(counts.index[grew])}")

    rows = []
    applicants = counts["Applied"]
    for i, s in enumerate(stages):
        for res, name, _ in GROUPS:
            n = int(counts.loc[res, s])
            prev = int(counts.loc[res, stages[i - 1]]) if i else None
            rows.append({"stage": s, "stage_order": i + 1, "residency": res, "group": name, "n": n,
                         "lost_from_previous": (prev - n) if prev is not None else 0,
                         "share_of_group_applicants": n / applicants[res]})
    return counts, pd.DataFrame(rows)


def smoothstep(t):
    return t * t * (3 - 2 * t)


def segment_tops(col):
    """Top y of each group's segment for one stage (top-aligned at 0, stacked downward)."""
    tops, y = [], 0.0
    for n in col:
        tops.append(y)
        y -= n + GAP
    return np.array(tops)


def plot(counts, out_path):
    plt.rcParams["font.family"] = "DejaVu Sans"
    stages = list(counts.columns)
    colors = [g[2] for g in GROUPS]
    applied_total = counts["Applied"].sum()
    full_h = applied_total + GAP * (len(GROUPS) - 1)

    fig_w = 13.6
    fig = plt.figure(figsize=(fig_w, 7.2), facecolor=BG)
    ax = fig.add_axes([2.55 / fig_w, 0.11, 6.9 / fig_w, 0.72])
    ax.set_facecolor(BG)
    ax.set_axis_off()

    tops = {s: segment_tops(counts[s].to_numpy()) for s in stages}

    # Ribbons: retained (top) part of each group's segment -> whole segment of next stage
    t = np.linspace(0, 1, 120)
    for i in range(len(stages) - 1):
        a, b = stages[i], stages[i + 1]
        x0, x1 = i + BAR_W / 2, i + 1 - BAR_W / 2
        xs = x0 + (x1 - x0) * t
        for k in range(len(GROUPS)):
            n_next = counts[b].iloc[k]
            top = tops[a][k] + (tops[b][k] - tops[a][k]) * smoothstep(t)
            ax.fill_between(xs, top - n_next, top, color=colors[k], alpha=RIBBON_ALPHA,
                            linewidth=0, zorder=1)

    # Bars
    for i, s in enumerate(stages):
        for k in range(len(GROUPS)):
            n = counts[s].iloc[k]
            ax.bar(i, n, width=BAR_W, bottom=tops[s][k] - n, color=colors[k], linewidth=0, zorder=2)

    pad = 0.025 * full_h
    for i, s in enumerate(stages):
        total = counts[s].sum()
        bottom = tops[s][-1] - counts[s].iloc[-1]
        ax.text(i, pad, s.replace(" ", "\n", 1) if len(s) > 14 else s, ha="center", va="baseline",
                fontsize=11.5, fontweight="bold", color=INK, linespacing=1.15)
        ax.text(i, bottom - pad, f"{total:,}", ha="center", va="top", fontsize=11,
                fontweight="bold", color=INK)
        ax.text(i, bottom - pad - 0.055 * full_h, f"{total / applied_total:.0%} of applicants",
                ha="center", va="top", fontsize=9, color=MUTED)

    # Losses between stages, on one row below the tallest bar
    loss_y = -full_h - 0.17 * full_h
    for i in range(len(stages) - 1):
        lost = counts[stages[i]].sum() - counts[stages[i + 1]].sum()
        ax.text(i + 0.5, loss_y, f"−{lost:,} lost", ha="center", va="top", fontsize=10,
                color=LOSS, fontweight="bold")

    # Left of first bar: groups and applicant counts
    first = stages[0]
    for k, (_, name, c) in enumerate(GROUPS):
        n = counts[first].iloc[k]
        y = tops[first][k] - n / 2
        ax.text(-BAR_W / 2 - 0.06, y + 0.012 * full_h, name, ha="right", va="bottom",
                fontsize=10, fontweight="bold", color=c)
        ax.text(-BAR_W / 2 - 0.06, y - 0.012 * full_h, f"{n:,} applicants", ha="right", va="top",
                fontsize=9.5, color=INK)

    ax.set_xlim(-BAR_W / 2 - 0.02, len(stages) - 1 + BAR_W / 2 + 0.02)
    ax.set_ylim(loss_y - 0.06 * full_h, pad + 0.1 * full_h)

    # Right of last bar: bold group name, then enrolled count and share of group's applicants
    last = stages[-1]
    x_name = len(stages) - 1 + BAR_W / 2 + 0.06
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for k, (_, name, c) in enumerate(GROUPS):
        n = counts[last].iloc[k]
        y = tops[last][k] - n / 2
        name_txt = ax.text(x_name, y, name, ha="left", va="center", fontsize=10,
                           fontweight="bold", color=c)
        x_end = ax.transData.inverted().transform((name_txt.get_window_extent(renderer).x1, 0))[0]
        share = n / counts[first].iloc[k]
        ax.text(x_end, y, f"  {n:,} ({share:.0%} of applicants)", ha="left", va="center",
                fontsize=9.5, color=INK)

    x0 = 0.035
    fig.text(x0, 0.955, "From application to enrollment, 2022–2026", ha="left", va="top",
             fontsize=18, fontweight="bold", color=INK)
    fig.text(x0, 0.905, "Bar height = number of students; color = residency. "
             "Largest loss: admitted students who never pay a deposit.",
             ha="left", va="top", fontsize=11, color=MUTED)
    fig.text(x0, 0.03, "Paid deposit = admitted and any deposit record (deposited flag, acceptance fee, "
             "or deposit year); 56 non-admitted students with a deposit record are not shown in that stage.",
             ha="left", va="bottom", fontsize=8.5, color=MUTED)

    fig.savefig(out_path, dpi=200, facecolor=BG)
    plt.close(fig)


def main():
    df = pd.read_csv(IN_PATH, parse_dates=DATE_COLS)
    counts, table = build_table(df)
    table.to_csv(OUT_TABLE, index=False)
    print(counts.to_string())
    print("Totals:", counts.sum().to_dict())
    plot(counts, OUT_PNG)
    print(f"Saved {OUT_PNG}, {OUT_TABLE}")


if __name__ == "__main__":
    main()

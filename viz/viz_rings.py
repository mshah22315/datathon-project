"""Concentric-ring distance chart: where enrolled students come from.

Input : data_clean.csv
Output: rings_enrolled_pink.png, rings_enrolled_blue.png (dpi=200), rings_enrolled_table.csv

Usage:
    python viz_rings.py                   # both palettes
    python viz_rings.py --palette blue    # one palette
"""
import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

IN_PATH = "data_clean.csv"
TABLE_PATH = "rings_enrolled_table.csv"

RESIDENCIES = ["Resident", "Contiguous", "Non-Contiguous"]
BAND_EDGES = [0, 50, 100, 200, 500, np.inf]
BAND_LABELS = ["0–50 mi", "50–100 mi", "100–200 mi", "200–500 mi", "500+ mi"]

# Color classes by number enrolled (lower bounds of classes 2-5)
CLASS_BREAKS = [100, 1000, 3000, 5000]
CLASS_LABELS = ["0–99", "100–999", "1,000–2,999", "3,000–4,999", "5,000+"]
PALETTES = {
    "pink": ["#feebe2", "#fbb4b9", "#f768a1", "#c51b8a", "#7a0177"],   # ColorBrewer RdPu
    "blue": ["#eff3ff", "#bdd7e7", "#6baed6", "#3182bd", "#08519c"],   # ColorBrewer Blues
}
LIGHT_TEXT_CLASSES = {3, 4}          # darkest two classes get white text

BG = "#fcfcfb"
INK = "#0b0b0b"
MUTED = "#52514e"
MIN_APPLICANTS = 100

# Geometry (polar radius units): hole of radius HOLE, then 5 rings of width 1
HOLE = 1.0
RING_W = 1.0
SECTOR = 2 * np.pi / 3
# Theta measured clockwise from north: Resident at top, Contiguous lower right,
# Non-Contiguous lower left; the Contiguous / Non-Contiguous boundary is straight down.
SECTOR_CENTER = {"Resident": 0.0, "Contiguous": 2 * np.pi / 3, "Non-Contiguous": 4 * np.pi / 3}


def build_table(path=IN_PATH):
    df = pd.read_csv(path, usecols=["residency", "miles_from_campus", "enrolled"])
    n_missing = int(df["miles_from_campus"].isna().sum())
    df = df.dropna(subset=["miles_from_campus"])
    df["distance_band"] = pd.cut(df["miles_from_campus"], BAND_EDGES, labels=BAND_LABELS,
                                 right=True, include_lowest=True)
    df["residency"] = pd.Categorical(df["residency"], categories=RESIDENCIES)
    table = (df.groupby(["residency", "distance_band"], observed=False)["enrolled"]
               .agg(enrolled="sum", applicants="size")
               .reset_index())
    table["enroll_rate"] = table["enrolled"] / table["applicants"].replace(0, np.nan)
    return table, n_missing


def print_table(table):
    for col in ["enrolled", "applicants"]:
        print(f"\n{col}:")
        print(table.pivot(index="residency", columns="distance_band", values=col)
                   .to_string())
    print("\nenroll_rate:")
    print(table.pivot(index="residency", columns="distance_band", values="enroll_rate")
               .map(lambda v: f"{v:.1%}").to_string())


def cell_text(row):
    count = f"{int(row.enrolled):,}"
    if row.applicants == 0:
        return f"{count}\n–"
    star = "*" if row.applicants < MIN_APPLICANTS else ""
    return f"{count}\n{row.enroll_rate:.0%}{star}"


def render(table, n_missing, palette, out_path):
    colors = PALETTES[palette]
    plt.rcParams["font.family"] = "DejaVu Sans"

    fig_w, fig_h, diam = 10, 11.4, 7.0          # inches; diam = outer ring diameter
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=BG)
    ax = fig.add_axes([(1 - diam / fig_w) / 2, 2.6 / fig_h, diam / fig_w, diam / fig_h], projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, HOLE + 5 * RING_W)
    ax.set_axis_off()

    font_by_ring = [9.5, 10, 10, 10.5, 10.5]        # inner rings slightly smaller
    for row in table.itertuples():
        i = BAND_LABELS.index(row.distance_band)
        cls = int(np.digitize(row.enrolled, CLASS_BREAKS))
        theta = SECTOR_CENTER[row.residency]
        r0 = HOLE + i * RING_W
        ax.bar(theta, RING_W, width=SECTOR, bottom=r0, color=colors[cls],
               edgecolor=BG, linewidth=2.5, align="center")
        ax.text(theta, r0 + RING_W / 2, cell_text(row), ha="center", va="center",
                fontsize=font_by_ring[i], linespacing=1.25,
                color="white" if cls in LIGHT_TEXT_CLASSES else INK)

    # Campus
    ax.plot(0, 0, marker="*", markersize=20, color="black", zorder=5)

    # Distance labels along the Contiguous / Non-Contiguous boundary (straight down)
    for i, label in enumerate(BAND_LABELS):
        ax.text(np.pi, HOLE + (i + 0.5) * RING_W, label, ha="center", va="center",
                fontsize=8.5, color=INK, zorder=6,
                bbox=dict(boxstyle="round,pad=0.25", facecolor=BG, edgecolor="none", alpha=0.85))

    # Sector names outside the rings, anchored away from the circle
    r_outer = HOLE + 5 * RING_W
    name_pos = {"Resident": (r_outer + 0.25, "center", "bottom"),
                "Contiguous": (r_outer + 0.3, "left", "top"),
                "Non-Contiguous": (r_outer + 0.3, "right", "top")}
    for name, theta in SECTOR_CENTER.items():
        r, ha, va = name_pos[name]
        ax.text(theta, r, name, ha=ha, va=va, fontsize=13, fontweight="bold", color=INK)

    # Title, subtitle
    fig.text(0.06, 0.96, "Where enrolled students come from", ha="left", va="top",
             fontsize=19, fontweight="bold", color=INK)
    fig.text(0.06, 0.925,
             "Campus at center · rings = distance from home · color = number enrolled "
             "(2022–2026).\nEach cell: enrolled count and enrollment rate among applicants.",
             ha="left", va="top", fontsize=10.5, color=MUTED, linespacing=1.45)

    # Legend: framed box, title, 5 swatches
    handles = [Patch(facecolor=c, edgecolor="none") for c in colors]
    leg = fig.legend(handles, CLASS_LABELS, title="Enrolled students", loc="lower left",
                     bbox_to_anchor=(0.06, 0.06), frameon=True, fontsize=9.5,
                     title_fontsize=10, handlelength=1.6, handleheight=1.1,
                     borderpad=0.8, labelspacing=0.45, alignment="left")
    leg.get_frame().set_edgecolor("#c9c8c4")
    leg.get_frame().set_linewidth(0.8)
    leg.get_frame().set_facecolor(BG)
    leg.get_title().set_fontweight("bold")
    leg.get_title().set_color(INK)
    for t in leg.get_texts():
        t.set_color(INK)

    # Footnote
    fig.text(0.06, 0.018,
             f"Rings are equal width, not to scale. {n_missing} applicants with missing distance "
             f"are excluded.\n* fewer than {MIN_APPLICANTS} applicants; rate is unreliable.",
             ha="left", va="bottom", fontsize=8.5, color=MUTED, linespacing=1.4)

    fig.savefig(out_path, dpi=200, facecolor=BG)
    plt.close(fig)
    print(f"Saved {out_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--palette", choices=["all", *PALETTES], default="all")
    ap.add_argument("--input", default=IN_PATH)
    args = ap.parse_args()

    table, n_missing = build_table(args.input)
    print(f"Dropped {n_missing} rows with missing miles_from_campus")
    print_table(table)
    table.to_csv(TABLE_PATH, index=False)
    print(f"\nSaved {TABLE_PATH}")

    for name in (PALETTES if args.palette == "all" else [args.palette]):
        render(table, n_missing, name, f"rings_enrolled_{name}.png")


if __name__ == "__main__":
    main()

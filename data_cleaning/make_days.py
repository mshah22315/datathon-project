"""Convert dates to days before term start: data_may1.csv -> data_may1_days.csv.

Term start is taken from clean_data.py (TERM_START_MONTH/TERM_START_DAY of entry_year).
Each new column = term start - date, in whole days, placed where its date column was; the date
columns are then dropped. Missing dates stay missing (not visited, no deposit by the cutoff, or
first contact not recorded). All other columns are unchanged.

Usage:
    python make_days.py
    python make_days.py --src data_may1.csv --out data_may1_days.csv

Read the output with integer day columns:
    pd.read_csv("data_may1_days.csv", dtype={c: "Int64" for c in DAY_COLS.values()})
"""
import argparse

import pandas as pd

from clean_data import TERM_START_DAY, TERM_START_MONTH, term_start
from make_may1 import CUTOFF_DAY, CUTOFF_MONTH, DATE_COLS

SRC_PATH = "data_may1.csv"
OUT_PATH = "data_may1_days.csv"
DAY_COLS = {
    "app_date": "app_days_before_start",
    "first_contact_date": "contact_days_before_start",
    "visit_date": "visit_days_before_start",
    "deposit_date": "deposit_days_before_start",
}


def min_days():
    """Days from the cutoff to term start (same in every year: no Feb in between)."""
    return (pd.Timestamp(2000, TERM_START_MONTH, TERM_START_DAY)
            - pd.Timestamp(2000, CUTOFF_MONTH, CUTOFF_DAY)).days


def make_days(src):
    """As-of-cutoff data with dates -> same data with days before term start."""
    df = src.copy()
    start = term_start(df)
    for date_col, day_col in DAY_COLS.items():
        days = (start - df[date_col]).dt.days.astype("Int64")
        df.insert(df.columns.get_loc(date_col), day_col, days)
    df = df.drop(columns=list(DAY_COLS))
    check(src, df)
    return df


def check(src, df):
    """Stop if any day count is below the cutoff minimum, missing counts change, or types are wrong."""
    low = min_days()
    for date_col, day_col in DAY_COLS.items():
        if df[day_col].dtype != "Int64":
            raise TypeError(f"{day_col} is {df[day_col].dtype}, expected Int64")
        if (df[day_col] < low).any():
            raise ValueError(f"{day_col}: {(df[day_col] < low).sum()} values below {low}")
        if df[day_col].isna().sum() != src[date_col].isna().sum():
            raise ValueError(f"{day_col}: missing count differs from {date_col}")
    if len(df) != len(src) or df.shape[1] != src.shape[1]:
        raise ValueError(f"shape changed: {src.shape} -> {df.shape}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=SRC_PATH, help="as-of-cutoff csv path (input)")
    ap.add_argument("--out", default=OUT_PATH, help="output csv path")
    args = ap.parse_args()

    df = make_days(pd.read_csv(args.src, parse_dates=DATE_COLS))
    df.to_csv(args.out, index=False)
    print(f"Saved {args.out}: {df.shape[0]} rows x {df.shape[1]} columns")


if __name__ == "__main__":
    main()

"""Datathon 2026 data cleaning: raw xlsx -> data_clean.csv.

Usage:
    python clean_data.py
    python clean_data.py --raw X.xlsx --out Y.csv

Read the output with parsed dates:
    pd.read_csv("data_clean.csv", parse_dates=DATE_COLS)
"""
import argparse

import numpy as np
import pandas as pd

RAW_PATH = "datathon-dataset.xlsx"
RAW_SHEET = "data"
OUT_PATH = "data_clean.csv"
DATE_COLS = ["app_date", "deposit_date", "visit_date", "first_contact_date"]
# Assumed term start: TERM_START_MONTH/TERM_START_DAY of entry_year. "After term start" means
# strictly later than this date (the day itself is not late).
TERM_START_MONTH, TERM_START_DAY = 8, 31

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def month_num(s):
    """Month abbreviation (any case) -> 1-12."""
    return s.astype("string").str.strip().str.lower().str[:3].map(MONTHS)


def build_date(year, month, day, mask):
    """Build dates on rows in mask; other rows are NaT."""
    out = pd.Series(pd.NaT, index=year.index, dtype="datetime64[ns]")
    out.loc[mask] = pd.to_datetime(
        dict(year=year[mask].astype("int64"), month=month[mask].astype("int64"),
             day=day[mask].astype("int64")),
        errors="coerce",
    )
    return out


def replace_with(df, new_col, values, drop_cols, at):
    """Insert values at the position of column `at`, then drop drop_cols."""
    df.insert(df.columns.get_loc(at), new_col, values)
    return df.drop(columns=drop_cols)


def term_start(df):
    """Assumed term start of each row: TERM_START_MONTH/TERM_START_DAY of entry_year."""
    return pd.to_datetime(dict(year=df["entry_year"], month=TERM_START_MONTH, day=TERM_START_DAY))


def clean(raw):
    """Raw data (original row order) -> cleaned data."""
    df = raw.copy()

    # row_id = original row order, never renumbered; drop student_id
    df.insert(0, "row_id", pd.RangeIndex(len(df)).astype("int64"))
    df = df.drop(columns="student_id")

    # credit_hrs is post-enrollment information
    df = df.drop(columns="credit_hrs")

    # Application date; missing day -> 15
    app_date = build_date(df["app_yr"], month_num(df["app_mo"]), df["app_dt"].fillna(15),
                          pd.Series(True, index=df.index))
    df.insert(df.columns.get_loc("app_dt"), "app_date", app_date)
    # Drop applications after term start (none at Aug 31) or with app_yr == 2018 (row_id 12703)
    df = df.loc[~((df["app_date"] > term_start(df)) | (df["app_yr"] == 2018))]
    df = df.drop(columns=["app_yr", "app_mo", "app_dt"])

    # Missing acceptance_fee means not paid (missing app_fee stays NA)
    df["acceptance_fee"] = df["acceptance_fee"].fillna("NotPaid")

    # Deposit date: needs year and month; missing day -> 15; otherwise NaT
    dep = ["deposit_yr", "deposit_mo", "deposit_dt"]
    deposit_date = build_date(df["deposit_yr"], df["deposit_mo"], df["deposit_dt"].fillna(15),
                              df["deposit_yr"].notna() & df["deposit_mo"].notna())
    df = replace_with(df, "deposit_date", deposit_date, dep, at="deposit_dt")

    # applied is always 1
    df = df.drop(columns="applied")

    # hs_rank outside 0-100 -> NA
    df.loc[(df["hs_rank"] < 0) | (df["hs_rank"] > 100), "hs_rank"] = np.nan

    # Visit date; missing means no visit, stays NaT
    V = ["visit_yr", "visit_mo", "visit_dt"]
    visit_date = build_date(df["visit_yr"], month_num(df["visit_mo"]), df["visit_dt"],
                            df[V].notna().all(axis=1))
    df = replace_with(df, "visit_date", visit_date, V, at="visit_dt")

    # First contact date: needs year and month; missing day -> 15
    FC = ["first_contact_yr", "first_contact_mo", "first_contact_dt"]
    fc_month = month_num(df["first_contact_mo"])
    fc_date = build_date(df["first_contact_yr"], fc_month, df["first_contact_dt"].fillna(15),
                         df["first_contact_yr"].notna() & fc_month.notna())
    # First contact after app_date: if same year-month and the raw app_dt or first_contact_dt
    # was missing (filled with 15), set to app_date; otherwise NaT
    r = raw.loc[df["row_id"], ["app_dt", "first_contact_dt"]]
    r.index = df.index
    late = fc_date > df["app_date"]
    same_ym = (fc_date.dt.year == df["app_date"].dt.year) & (fc_date.dt.month == df["app_date"].dt.month)
    fix = late & same_ym & (r["app_dt"].isna() | r["first_contact_dt"].isna())
    fc_date.loc[fix] = df.loc[fix, "app_date"]
    fc_date.loc[late & ~fix] = pd.NaT
    df = replace_with(df, "first_contact_date", fc_date, FC, at="first_contact_dt")

    # age < 14 -> NA
    df.loc[df["age"] < 14, "age"] = np.nan

    # deposit_paid: 1 if any source shows a deposit (deposited, acceptance_fee, or raw deposit_yr
    # present). 383 rows are paid only through the deposit record (deposited = 0 and
    # acceptance_fee = NotPaid): 379 have a full deposit date, and 4 (row_id 22865, 48848,
    # 53163, 54359) have a deposit year but no month.
    raw_dep_yr = raw.loc[df["row_id"], "deposit_yr"].notna().to_numpy()
    deposit_paid = (df["deposited"] == 1) | (df["acceptance_fee"] != "NotPaid") | raw_dep_yr
    df.insert(df.columns.get_loc("deposited") + 1, "deposit_paid", deposit_paid.astype("int64"))

    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", default=RAW_PATH, help="raw xlsx path")
    ap.add_argument("--out", default=OUT_PATH, help="output csv path")
    args = ap.parse_args()

    df = clean(pd.read_excel(args.raw, sheet_name=RAW_SHEET))
    df.to_csv(args.out, index=False)
    print(f"Saved {args.out}: {df.shape[0]} rows x {df.shape[1]} columns")
    report_late(df)


def report_late(df):
    """Print dates later than term start. Recorded only; these values are not changed."""
    start = term_start(df)
    for col in ["deposit_date", "visit_date", "first_contact_date"]:
        late = df[col] > start
        print(f"{col} after term start: {late.sum()} rows")
        if late.any():
            print(df.loc[late, ["row_id", "entry_year", col]].to_string(index=False))


if __name__ == "__main__":
    main()

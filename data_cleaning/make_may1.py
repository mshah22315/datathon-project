"""Build the "as of May 1" modeling dataset: data_clean.csv -> data_may1.csv.

Cutoff: CUTOFF_MONTH/CUTOFF_DAY of each row's entry_year. "After cutoff" means strictly later
than the cutoff date (the day itself is kept).

Steps (in this order):
    1. Drop applicants with app_date after cutoff; their counts by entry_year are saved to
       late_applicants_by_year.csv first.
    2. Visits after cutoff: visit_date -> NA, campus_visit_tot - 1.
    3. Deposits after cutoff: deposit_date -> NA, deposit_paid -> 0, acceptance_fee -> "NotPaid".
       Rows with no deposit_date but deposit_paid == 1 are left as paid.
    4. Check that no first_contact_date is after app_date or after cutoff (stop if any).
    5. Drop deposited (no date, nearly equal to the outcome).
All other columns are unchanged. data_clean.csv is not modified.

Usage:
    python make_may1.py
    python make_may1.py --clean data_clean.csv --out data_may1.csv --late late_applicants_by_year.csv

Read the output with parsed dates:
    pd.read_csv("data_may1.csv", parse_dates=DATE_COLS)
"""
import argparse

import pandas as pd

CLEAN_PATH = "data_clean.csv"
OUT_PATH = "data_may1.csv"
LATE_PATH = "late_applicants_by_year.csv"
DATE_COLS = ["app_date", "deposit_date", "visit_date", "first_contact_date"]
CUTOFF_MONTH, CUTOFF_DAY = 5, 1


def cutoff(df):
    """Cutoff date of each row: CUTOFF_MONTH/CUTOFF_DAY of entry_year."""
    return pd.to_datetime(dict(year=df["entry_year"], month=CUTOFF_MONTH, day=CUTOFF_DAY))


def by_year(df, rows):
    """Count of rows by entry_year."""
    return df.loc[rows].groupby("entry_year").size().to_dict()


def make_may1(clean):
    """Cleaned data -> (as-of-cutoff data, late applicant counts by entry_year)."""
    df = clean.copy()

    # 1. Applicants after cutoff: save counts by entry_year, then drop
    late_app = df["app_date"] > cutoff(df)
    late_counts = (df.loc[late_app]
                   .groupby("entry_year")
                   .agg(applied=("row_id", "size"), admitted=("admitted", "sum"),
                        enrolled=("enrolled", "sum"))
                   .reset_index())
    print(f"[1] app_date after cutoff: {late_app.sum()} rows dropped, "
          f"{df.loc[late_app, 'enrolled'].sum()} enrolled")
    print(late_counts.to_string(index=False))
    df = df.loc[~late_app].copy()
    cut = cutoff(df)

    # 2. Visits after cutoff: date unknown as of cutoff, so remove that visit
    late_visit = df["visit_date"] > cut
    print(f"[2] visit_date after cutoff: {late_visit.sum()} rows, by year {by_year(df, late_visit)}")
    df.loc[late_visit, "visit_date"] = pd.NaT
    df.loc[late_visit, "campus_visit_tot"] -= 1
    if (df["campus_visit_tot"] < 0).any():
        raise ValueError("campus_visit_tot is negative after removing late visits")
    print("    campus_visit_tot after change:",
          df.loc[late_visit, "campus_visit_tot"].value_counts().sort_index().to_dict())

    # 3. Deposits after cutoff: not paid as of cutoff. Select rows first, by deposit_date only,
    #    so rows with no deposit_date but deposit_paid == 1 stay paid.
    late_dep = df["deposit_date"] > cut
    paid_no_date = df["deposit_date"].isna() & (df["deposit_paid"] == 1)
    print(f"[3] deposit_date after cutoff: {late_dep.sum()} rows "
          f"({df.loc[late_dep, 'enrolled'].sum()} enrolled), by year {by_year(df, late_dep)}")
    print("    acceptance_fee before change:",
          df.loc[late_dep, "acceptance_fee"].value_counts().to_dict())
    print(f"    paid with no deposit_date (unchanged): {paid_no_date.sum()} rows")
    df.loc[late_dep, "deposit_date"] = pd.NaT
    df.loc[late_dep, "deposit_paid"] = 0
    df.loc[late_dep, "acceptance_fee"] = "NotPaid"

    # 4. First contact: must not be after app_date or after cutoff
    fc_after_app = (df["first_contact_date"] > df["app_date"]).sum()
    fc_after_cut = (df["first_contact_date"] > cut).sum()
    if fc_after_app or fc_after_cut:
        raise ValueError(f"first_contact_date after app_date: {fc_after_app} rows, "
                         f"after cutoff: {fc_after_cut} rows")
    print("[4] first_contact_date: none after app_date or cutoff")

    # 5. deposited has no date and nearly equals the outcome
    df = df.drop(columns="deposited")

    return df, late_counts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clean", default=CLEAN_PATH, help="cleaned csv path (input)")
    ap.add_argument("--out", default=OUT_PATH, help="output csv path")
    ap.add_argument("--late", default=LATE_PATH, help="late applicant counts csv path")
    args = ap.parse_args()

    clean = pd.read_csv(args.clean, parse_dates=DATE_COLS)
    df, late_counts = make_may1(clean)
    late_counts.to_csv(args.late, index=False)
    df.to_csv(args.out, index=False)

    back = pd.read_csv(args.out, parse_dates=DATE_COLS)
    bad = [c for c in DATE_COLS if not pd.api.types.is_datetime64_any_dtype(back[c])]
    if bad:
        raise ValueError(f"not datetime after reading back: {bad}")
    print(f"Saved {args.out}: {back.shape[0]} rows x {back.shape[1]} columns; {args.late}")


if __name__ == "__main__":
    main()

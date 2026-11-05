"""Build the as-of-cutoff modeling dataset: data_clean.csv -> data_asof_MMDD.csv.

Cutoff: a month and day (--cutoff MM-DD, default 05-01), applied to each row's entry_year.
"After the cutoff" means strictly later than the cutoff date (the day itself is kept).
Term start comes from clean_data.py (TERM_START_MONTH/TERM_START_DAY of entry_year).

Steps, in this order:
    apply_cutoff()
        1. Drop applicants with app_date after the cutoff; their counts by entry_year are saved
           to late_applicants_MMDD.csv first.
        2. Visits after the cutoff: visit_date -> NA, campus_visit_tot - 1.
        3. Deposits after the cutoff: deposit_date -> NA, deposit_paid -> 0,
           acceptance_fee -> "NotPaid". Rows with no deposit_date but deposit_paid == 1 stay paid.
        4. Check that no first_contact_date is after app_date or after the cutoff (stop if any).
        5. Drop deposited (no date, nearly equal to the outcome).
    dates_to_days()
        6. Replace the 4 dates, in place, by whole days before term start (term start - date).
           Missing dates stay missing. Stops if any day count is earlier than the cutoff allows,
           missing counts change, or a column is not Int64.
All other columns are unchanged. data_clean.csv is not modified.

Outputs (MMDD = cutoff, e.g. 0501), in the working folder:
    data_asof_MMDD.csv           modeling dataset (days, no date columns)
    late_applicants_MMDD.csv     applied / admitted / enrolled after the cutoff, by entry_year
    data_asof_MMDD_dated.csv     only with --save-dated: result of apply_cutoff(), with dates

Usage:
    python make_asof.py
    python make_asof.py --cutoff 03-01 --save-dated
    python make_asof.py --clean data_clean.csv

Read the outputs:
    pd.read_csv("data_asof_0501.csv", dtype={c: "Int64" for c in DAY_COLS.values()})
    pd.read_csv("data_asof_0501_dated.csv", parse_dates=DATE_COLS)
The day columns must be read as Int64; otherwise columns with missing values load as float.
"""
import argparse

import pandas as pd

from clean_data import term_start

CLEAN_PATH = "data_clean.csv"
DEFAULT_CUTOFF = "05-01"
DATE_COLS = ["app_date", "deposit_date", "visit_date", "first_contact_date"]
DAY_COLS = {
    "app_date": "app_days_before_start",
    "first_contact_date": "contact_days_before_start",
    "visit_date": "visit_days_before_start",
    "deposit_date": "deposit_days_before_start",
}


def parse_cutoff(text):
    """'MM-DD' -> (month, day). Must be a valid date in every year and before term start."""
    try:
        month, day = (int(x) for x in text.split("-"))
        pd.Timestamp(2001, month, day)  # non-leap year: rejects 02-29 and invalid dates
    except ValueError:
        raise argparse.ArgumentTypeError(f"cutoff must be MM-DD, got {text!r}")
    start = term_start(pd.DataFrame({"entry_year": [2001]}))[0]
    if pd.Timestamp(2001, month, day) >= start:
        raise argparse.ArgumentTypeError(f"cutoff {text} is not before term start")
    return month, day


def cutoff_dates(df, cutoff):
    """Cutoff date of each row: cutoff month/day of entry_year."""
    month, day = cutoff
    return pd.to_datetime(dict(year=df["entry_year"], month=month, day=day))


def by_year(df, rows):
    """Count of rows by entry_year."""
    return df.loc[rows].groupby("entry_year").size().to_dict()


def apply_cutoff(clean, cutoff):
    """Cleaned data -> (as-of-cutoff data with dates, late applicant counts by entry_year)."""
    df = clean.copy()

    # 1. Applicants after cutoff: save counts by entry_year, then drop
    late_app = df["app_date"] > cutoff_dates(df, cutoff)
    late_counts = (df.loc[late_app]
                   .groupby("entry_year")
                   .agg(applied=("row_id", "size"), admitted=("admitted", "sum"),
                        enrolled=("enrolled", "sum"))
                   .reset_index())
    print(f"[1] app_date after cutoff: {late_app.sum()} rows dropped, "
          f"{df.loc[late_app, 'enrolled'].sum()} enrolled")
    print(late_counts.to_string(index=False))
    df = df.loc[~late_app].copy()
    cut = cutoff_dates(df, cutoff)

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


def dates_to_days(dated, cutoff):
    """As-of-cutoff data with dates -> same data with days before term start."""
    df = dated.copy()
    start = term_start(df)
    for date_col, day_col in DAY_COLS.items():
        days = (start - df[date_col]).dt.days.astype("Int64")
        df.insert(df.columns.get_loc(date_col), day_col, days)
    df = df.drop(columns=list(DAY_COLS))
    check_days(dated, df, cutoff)
    print("[6] dates -> days before term start")
    return df


def check_days(dated, df, cutoff):
    """Stop if a day count is below its row's minimum, missing counts change, or types are wrong."""
    # Minimum = days from the row's cutoff to its term start (122 for May 1 -> Aug 31)
    low = (term_start(df) - cutoff_dates(df, cutoff)).dt.days
    for date_col, day_col in DAY_COLS.items():
        if df[day_col].dtype != "Int64":
            raise TypeError(f"{day_col} is {df[day_col].dtype}, expected Int64")
        below = (df[day_col] < low).fillna(False)
        if below.any():
            raise ValueError(f"{day_col}: {below.sum()} values below the cutoff minimum")
        if df[day_col].isna().sum() != dated[date_col].isna().sum():
            raise ValueError(f"{day_col}: missing count differs from {date_col}")
    if len(df) != len(dated) or df.shape[1] != dated.shape[1]:
        raise ValueError(f"shape changed: {dated.shape} -> {df.shape}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cutoff", type=parse_cutoff, default=DEFAULT_CUTOFF,
                    help=f"cutoff as MM-DD (default {DEFAULT_CUTOFF})")
    ap.add_argument("--clean", default=CLEAN_PATH, help="cleaned csv path (input)")
    ap.add_argument("--save-dated", action="store_true",
                    help="also save the as-of-cutoff data with dates (data_asof_MMDD_dated.csv)")
    args = ap.parse_args()
    tag = f"{args.cutoff[0]:02d}{args.cutoff[1]:02d}"

    clean = pd.read_csv(args.clean, parse_dates=DATE_COLS)
    dated, late_counts = apply_cutoff(clean, args.cutoff)
    days = dates_to_days(dated, args.cutoff)

    outputs = {f"late_applicants_{tag}.csv": late_counts, f"data_asof_{tag}.csv": days}
    if args.save_dated:
        outputs[f"data_asof_{tag}_dated.csv"] = dated
    for path, frame in outputs.items():
        frame.to_csv(path, index=False)
        print(f"Saved {path}: {frame.shape[0]} rows x {frame.shape[1]} columns")

    if args.save_dated:
        back = pd.read_csv(f"data_asof_{tag}_dated.csv", parse_dates=DATE_COLS)
        bad = [c for c in DATE_COLS if not pd.api.types.is_datetime64_any_dtype(back[c])]
        if bad:
            raise ValueError(f"not datetime after reading back: {bad}")


if __name__ == "__main__":
    main()

# Data Cleaning Notes

## Pipeline

```
datathon-dataset.xlsx
  → clean_data.py → data_clean.csv          (69,556 × 58; sections 1–7)
  → make_may1.py  → data_may1.csv           (68,910 × 57; section 8)
                    + late_applicants_by_year.csv
  → make_days.py  → data_may1_days.csv      (68,910 × 57; section 9; modeling input)
```

Run all three steps from the raw file (works from any folder; all files are read and written in the project folder):

```
python data_cleaning/run_all.py
```

**Raw data:** 69,557 rows × 67 columns → **Cleaned:** 69,556 rows × 58 columns (`data_clean.csv`, produced by `clean_data.py`)

Principle: the cleaning step only fixes clear errors and standardizes formats. Variables are not filtered by prediction cutoff at this stage. Values that look unusual but could be real are recorded, not changed.

Assumed term start: **Aug 31 of `entry_year`** (`TERM_START_MONTH`, `TERM_START_DAY` in `clean_data.py`). "After term start" means strictly later than Aug 31; Aug 31 itself is not late.

## 1. Rows removed (1 row, not enrolled)
- 1 row with application year 2018, four years before entry (row_id 12703)
- Rule also drops applications after term start, but no row has `app_date` later than Aug 31 of its entry year

## 2. Columns removed
- `student_id`: 10 IDs are shared by 24 rows (verified to be different people), and 2 rows are missing. Replaced by `row_id` (original row order).
- `credit_hrs`: only known after enrollment
- `applied`: equal to 1 for every row

## 3. Dates merged (year, month, day → one date column)
| New column | Handling |
|---|---|
| `app_date` | Missing day filled with 15 (2,315 rows) |
| `first_contact_date` | Missing day filled with 15; missing year or month → NaT. Dates later than `app_date`: set to `app_date` if same year-month and a day was imputed (211 rows), otherwise NaT (73 rows) |
| `visit_date` | Missing means no visit; matches `campus_visit_tot = 0` exactly |
| `deposit_date` | Missing day filled with 15; missing month → NaT (606 rows) |

## 4. Values set to missing
- `hs_rank`: 4 negative values and one value of 941 (inferred to be a 0–100 percentile)
- `age`: one value of 1

## 5. Encoding and new variables
- `acceptance_fee`: missing filled with `"NotPaid"`. The 3 missing values in `app_fee` are kept as NA.
- New `deposit_paid`: 1 if any of `deposited`, `acceptance_fee`, or the raw deposit record (year present) shows a deposit. 26,434 students; 87.0% of them enrolled. 383 rows are flagged as paid only through the deposit record (`deposited = 0` and `acceptance_fee = NotPaid`); 379 of them have a full deposit date and 4 (row_id 22865, 48848, 53163, 54359) have a deposit year but no month.

## 6. Known issues (not changed)
- **2025 cohort is recorded differently:** lower ACT share, higher SAT share, lower rates for the assistance flags and `grad_expct`, and 155 enrolled students with no deposit date.
- **`deposited` behaves like "deposited and enrolled":** 3,224 students who paid a deposit (by the `deposit_paid` definition) but did not enroll have `deposited = 0`; in addition, 3 students have `deposited = 0` but enrolled, and 201 have `deposited = 1` but did not enroll.
- **SAT:** 25.1% of the 7,802 SAT records have a composite that does not equal verbal + math (14% differ by 50 points or more). The mismatch is concentrated in the 2024 cohort (98.4%); other cohorts range from 12% to 20%.
- **2024 cohort SAT recording:** the 2024 cohort appears to record SAT composite scores differently, similar to the recording differences seen in 2025.
- **`hs_rank = 0`:** 91 students, none enrolled; possibly a placeholder.
- **Dates after term start:** 1 `deposit_date` (row_id 913, entry 2022, 2022-09-04) is later than Aug 31 and is kept as is. No `visit_date` or `first_contact_date` is later than term start.

## 7. Variables

| # | Variable | Description | Format |
|---|---|---|---|
| 1 | `row_id` | Row number in the raw data (from 0); unique ID | int64 |
| 2 | `entry_year` | Year of first fall semester | int64, 2022–2026 |
| 3 | `app_date` | Application date | datetime64 |
| 4 | `app_fee` | Application fee status | string: Paid / Deferred / Waived; 3 missing |
| 5 | `acceptance_fee` | Acceptance fee status | string: Paid / Deferred / Waived / NotPaid |
| 6 | `hs_gpa` | High school GPA | float64 |
| 7 | `act_cmpst` | ACT composite | float64, 1–36 |
| 8 | `act_engl` | ACT English | float64, 1–36 |
| 9 | `act_math` | ACT Math | float64, 1–36 |
| 10 | `sat_comb` | SAT combined | float64, 400–1600 |
| 11 | `sat_vrbl` | SAT verbal | float64, 200–800 |
| 12 | `sat_math` | SAT math | float64, 200–800 |
| 13 | `deposit_date` | Date the student accepted the offer (deposit) | datetime64 |
| 14 | `hs_math` | Math credits (includes college credits taken in high school) | float64 |
| 15 | `hs_sci` | Science credits (includes college credits taken in high school) | float64 |
| 16 | `hs_engl` | English credits | float64 |
| 17 | `hs_ss` | Social science credits | float64 |
| 18 | `hs_flang` | Foreign language credits | float64 |
| 19 | `residency` | Residency status | string: Resident / Contiguous / Non-Contiguous |
| 20 | `app_completed` | Completed the application | int64, 0/1 |
| 21 | `admitted` | Admitted | int64, 0/1 |
| 22 | `deposited` | Paid deposit (raw; see known issues) | int64, 0/1 |
| 23 | `deposit_paid` | Paid deposit (combined from three sources) | int64, 0/1 |
| 24 | `enrolled` | Enrolled (target) | int64, 0/1 |
| 25 | `undecided` | Undecided major | int64, 0/1 |
| 26 | `hs_rank` | High school rank (inferred percentile; higher is better) | float64, 0–100 |
| 27 | `first_generation` | First-generation college student | int64, 0/1 |
| 28 | `legacy` | Family member graduated from this university | int64, 0/1 |
| 29 | `campus_visit_tot` | Number of campus visits | int64, 0–4 |
| 30 | `visit_date` | Most recent campus visit | datetime64 |
| 31 | `first_contact_date` | First engagement with the university | datetime64 |
| 32 | `stealth` | Applied without prior contact | int64, 0/1 |
| 33 | `grad_expct` | Expects graduate school (`grad_school_expct` in the dictionary) | int64, 0/1 |
| 34 | `ed_plan_asst` | Needs help with educational planning | int64, 0/1 |
| 35 | `wrtng_asst` | Needs help with writing | int64, 0/1 |
| 36 | `read_asst` | Needs help with reading | int64, 0/1 |
| 37 | `study_skll_asst` | Needs help with study skills | int64, 0/1 |
| 38 | `math_asst` | Needs help with math | int64, 0/1 |
| 39 | `hs_algbr_cr` | High school algebra credits | float64 |
| 40 | `hs_geom_cr` | High school geometry credits | float64 |
| 41 | `hs_trig_cr` | High school trigonometry credits | float64 |
| 42 | `hs_calc_cr` | High school calculus credits | float64 |
| 43 | `coll_algbr_cr` | College algebra credits before entry | float64 |
| 44 | `coll_geom_cr` | College geometry credits before entry | float64 |
| 45 | `coll_trig_cr` | College trigonometry credits before entry | float64 |
| 46 | `coll_calc_cr` | College calculus credits before entry | float64 |
| 47 | `coll_math` | College math credits before entry (sum of 43–46) | float64 |
| 48 | `coll_sci` | College science credits before entry | float64 |
| 49 | `hs_only_math` | High-school-only math credits. Approximately `hs_math` − `coll_math`; the relationship holds for about 98.6% of rows where all three values are present. This is inferred from the data, not stated in the data dictionary. | float64 |
| 50 | `hs_only_sci` | High-school-only science credits. Approximately `hs_sci` − `coll_sci`; the relationship holds for about 98.5% of rows where all three values are present. This is inferred from the data, not stated in the data dictionary. | float64 |
| 51 | `rotc_interest` | Interested in ROTC | int64, 0/1 |
| 52 | `miles_from_campus` | Distance from home to campus (miles) | float64 |
| 53 | `veteran` | Veteran or family member eligible for veteran benefits | int64, 0/1 |
| 54 | `age` | Age | float64 |
| 55 | `stem_major` | STEM major | int64, 0/1 |
| 56 | `urm` | Underrepresented minority | int64, 0/1 |
| 57 | `sex` | Biological sex | string: F / M |
| 58 | `college` | College applied to (6 colleges) | string |

Numeric columns with missing values are read as float64 even when all values are whole numbers.

## 8. As-of-May-1 dataset (`make_may1.py`)

Goal: keep only what is known on the cutoff, **May 1 of `entry_year`** (`CUTOFF_MONTH`, `CUTOFF_DAY` in `make_may1.py`). "After the cutoff" means strictly later than May 1. Steps run in this order:

1. **Late applicants removed:** 646 rows with `app_date` after the cutoff (187 enrolled). Their applied / admitted / enrolled counts by `entry_year` are saved first to `late_applicants_by_year.csv`, for use when predicting class totals.
2. **Visits after the cutoff (15 rows):** `visit_date` → NA and `campus_visit_tot` − 1. All 15 had one visit, so all become 0.
3. **Deposits after the cutoff (749 rows, 682 enrolled):** `deposit_date` → NA, `deposit_paid` → 0, `acceptance_fee` → `"NotPaid"`. Rows paid with no `deposit_date` (752) are left as paid, since the payment cannot be dated.
4. **First contact:** checked that no `first_contact_date` is after `app_date` or the cutoff (none).
5. **`deposited` dropped:** it has no date and nearly equals the outcome (see section 6).

`admitted` and `app_completed` are assumed to be known by the cutoff. All other columns are unchanged.

## 9. Days before term start (`make_days.py`)

The four dates are replaced, in place, by whole days before term start (Aug 31 of `entry_year`, taken from `clean_data.py`): `app_days_before_start`, `contact_days_before_start`, `visit_days_before_start`, `deposit_days_before_start`. All values are ≥ 122 (May 1 to Aug 31).

Missing dates stay missing and are not filled; the gap has meaning: no campus visit, no deposit by the cutoff (or paid with no date), or no recorded first contact.

Read with integer day columns:

```python
days = ["app_days_before_start", "contact_days_before_start",
        "visit_days_before_start", "deposit_days_before_start"]
df = pd.read_csv("data_may1_days.csv", dtype={c: "Int64" for c in days})
```

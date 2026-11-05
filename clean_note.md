# Data Cleaning Notes

**Raw data:** 69,557 rows × 67 columns → **Cleaned:** 69,554 rows × 58 columns (`data_clean.csv`)

Principle: the cleaning step only fixes clear errors and standardizes formats. Variables are not filtered by prediction cutoff at this stage. Values that look unusual but could be real are recorded, not changed.

## 1. Rows removed (3 rows, none enrolled)
- 2 rows with application date after Aug 25 of the entry year (assumed semester start)
- 1 row with application year 2018, four years before entry

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
- New `deposit_paid`: 1 if any of `deposited`, `acceptance_fee`, or the raw deposit record (year present) shows a deposit. 26,434 students; 87.0% of them enrolled. 4 rows (row_id 22865, 48848, 53163, 54359) are flagged by deposit year only.

## 6. Known issues (not changed)
- **2025 cohort is recorded differently:** lower ACT share, higher SAT share, lower rates for the assistance flags and `grad_expct`, and 155 enrolled students with no deposit date.
- **`deposited` behaves like "deposited and enrolled":** about 2,800 students who paid but did not enroll have `deposited = 0`.
- **SAT:** about 15% of composite scores do not equal verbal + math.
- **`hs_rank = 0`:** 91 students, none enrolled; possibly a placeholder.

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
| 49 | `hs_only_math` | High-school-only math credits (= `hs_math` − `coll_math`) | float64 |
| 50 | `hs_only_sci` | High-school-only science credits (= `hs_sci` − `coll_sci`) | float64 |
| 51 | `rotc_interest` | Interested in ROTC | int64, 0/1 |
| 52 | `miles_from_campus` | Distance from home to campus (miles) | float64 |
| 53 | `veteran` | Veteran or family member eligible for veteran benefits | int64, 0/1 |
| 54 | `age` | Age | float64 |
| 55 | `stem_major` | STEM major | int64, 0/1 |
| 56 | `urm` | Underrepresented minority | int64, 0/1 |
| 57 | `sex` | Biological sex | string: F / M |
| 58 | `college` | College applied to (6 colleges) | string |

Numeric columns with missing values are read as float64 even when all values are whole numbers.
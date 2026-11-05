# Visualizations

All charts are built from `data_clean.csv` (output of `clean_data.py`; entry years 2022–2026).

> **Note:** The charts and numbers below were made from the old cleaned data (69,554 applicants, assumed term start Aug 25). The current `data_clean.csv` has 69,556 applicants (term start Aug 31; 2 non-admitted, non-enrolled applicants restored), so the charts need to be regenerated. Each script is run from the project folder and writes a PNG at 200 dpi plus a CSV of the plotted numbers.

**Conventions.** Background `#fcfcfb`, text `#0b0b0b`, secondary text `#52514e`, DejaVu Sans, no axis frames. Magnitudes use single-hue ColorBrewer ramps (RdPu or Blues); red `#b2182b` marks losses or the weakest group. Residency labels: Resident = In-state, Contiguous = Bordering state, Non-Contiguous = Non-bordering state. "Enrollment rate" is the mean of `enrolled` within a group.

## 1. Where enrolled students come from

- **File:** `rings_enrolled_pink.png`, `rings_enrolled_blue.png` (same chart, two palettes) — `viz_rings.py`; table `rings_enrolled_table.csv`
- **Question:** From which residency group and how far from campus do enrolled students come?
- **Data:** All applicants with a known distance (69,317; 237 with missing `miles_from_campus` are excluded). Distance bands 0–50, 50–100, 100–200, 200–500, 500+ miles (left-open, right-closed; 0 is in the first band).
- **How to read:** Campus is the star at the center; the three 120° sectors are residency groups and the five rings are distance bands (equal width, not to scale). Color shows the number enrolled in five classes; each cell gives the count and the enrollment rate among its applicants.
- **Key findings:**
  - The largest single cell is Contiguous at 200–500 miles: 6,065 enrolled, but only 24% of its 25,167 applicants.
  - In-state students within 200 miles supply 12,371 enrolled, with rates of 50–54%.
  - Non-Contiguous enrollment comes mainly from 500+ miles (1,456 enrolled, 16% rate).
- **Caveats:** Six cells have fewer than 100 applicants (marked *); their rates are unreliable. Rings are not proportional to distance.

## 2. How much each variable separates who enrolls

- **File:** `factor_importance.png` — `viz_importance.py`; tables `importance_all.csv`, `importance_groups.csv`
- **Question:** Among admitted students, which variables show the largest difference in enrollment rate between their groups?
- **Data:** Admitted students (62,071; enrollment rate 37.1%). 44 variables, each split into groups (bins for numeric variables, missing values as their own group). Gap = highest minus lowest group rate, using only groups with ≥300 students. The test score puts SAT on the ACT scale with an isotonic regression fit on the 3,430 students with both scores.
- **How to read:** One row per variable, sorted by gap. Blue marks the top 15% of gaps and red the bottom 15%; the dashed line is the median gap (12.7 points).
- **Key findings:**
  - Application fee (51.6 pts; Waived 72.4% vs Deferred 20.8%) and campus visits (48.6 pts; 2+ visits 68.9% vs none 20.3%) separate enrollers the most.
  - The test-score gap (42.7 pts) is driven by students who sent no score (6.1%). Among those who did, lower scores enroll more often; HS GPA shows the same pattern (<3.0: 40.3% vs 4.0+: 33.0%).
  - First generation (0.5 pts), Veteran (1.7) and grad-school expectation (2.1) barely differ.
- **Caveats:** One variable at a time, not adjusted for the others; association, not cause. Several gaps come from a "Missing" group, which may reflect how data were collected (e.g., the 2025 cohort) rather than the students themselves.

## 3. Admissions funnel

- **File:** `funnel.png` — `viz_funnel.py`; table `funnel_table.csv`
- **Question:** Where are applicants lost between application and enrollment, and does it differ by residency?
- **Data:** All 69,554 applicants (old data). Stages: Applied → Completed application (67,156) → Admitted (62,071) → Paid deposit (26,378) → Enrolled (23,009). Paid deposit = admitted and `deposit_paid == 1` (deposited flag, acceptance fee, or a raw deposit year); 56 non-admitted students with a deposit record are left out of that stage.
- **How to read:** Bars are stacked by residency and top-aligned; bar height is the number of students. Ribbons connect each group's retained students to the next stage, and red numbers are the students lost between stages.
- **Key findings:**
  - The largest loss is between admission and deposit: 35,693 admitted students (58%) never pay a deposit.
  - Of admitted students, 65% of in-state students pay a deposit, compared with 32% bordering and 23% non-bordering.
  - Once a deposit is paid, 87% enroll. Overall, 52% of in-state, 25% of bordering and 16% of non-bordering applicants enroll.
- **Caveats:** Counts are pooled over five cohorts. The 2025 cohort has 155 enrolled students with no deposit date, although they still count as paid through the other sources.

## 4. Enrollment rate by residency and test score

- **File:** `heatmap_residency_test.png` — `viz_heatmap.py`; table `heatmap_table.csv`
- **Question:** For admitted students, how does the enrollment rate vary by residency and test score?
- **Data:** Admitted students (62,071). Unified ACT-scale score as in chart 2, with bins <21, 21–24, 25–28 and 29+ (left-closed), plus "No test submitted".
- **How to read:** Rows are residency groups and columns are score bands. Color is the enrollment rate on a fixed 0–80% Blues scale; each cell shows the rate and the number of admitted students.
- **Key findings:**
  - Students who sent no score rarely enroll: 9% in-state, 6% bordering and 4% non-bordering.
  - Among students who sent a score, residency matters more than score: 56–66% in-state, 29–38% bordering and 24–30% non-bordering.
  - Within each residency group, the 29+ band has the lowest rate among score senders (56%, 29% and 24%).
- **Caveats:** Every cell has at least 1,049 students, so no cell is flagged for small size. The SAT-to-ACT conversion is fit on only 3,430 students. The chart shows association only.

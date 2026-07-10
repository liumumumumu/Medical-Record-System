# Data Quality Report

## Scope

This report summarizes the current data quality status of
`data/processed/nhanes_standardized.csv`.

Current standardized dataset:

| Item | Value |
| --- | --- |
| Rows | 9254 |
| Columns | 34 |
| Source cycle | NHANES 2017-2018 |
| Base table | `DEMO_J` |
| Join key | `SEQN`, renamed as `patient_id` |

## Missing Value Summary

The standardized table keeps all 9254 participants from the demographic table.
Missing values are expected because NHANES examination and laboratory modules do
not cover every participant.

Fields with the highest missing rates are mainly laboratory indicators from
`BIOPRO_J`:

| Field | Missing Count | Missing Rate |
| --- | ---: | ---: |
| `ast_u_l` | 3372 | 36.44% |
| `blood_urea_nitrogen_mg_dl` | 3353 | 36.23% |
| `uric_acid_mg_dl` | 3353 | 36.23% |
| `glucose_mg_dl` | 3353 | 36.23% |
| `triglycerides_mg_dl` | 3353 | 36.23% |
| `ggt_u_l` | 3352 | 36.22% |
| `alt_u_l` | 3352 | 36.22% |
| `total_cholesterol_mg_dl` | 3351 | 36.21% |
| `creatinine_mg_dl` | 3351 | 36.21% |
| `albumin_g_dl` | 3349 | 36.19% |

Blood pressure fields also have noticeable missing values:

| Field | Missing Count | Missing Rate |
| --- | ---: | ---: |
| `systolic_bp_mean` | 2537 | 27.42% |
| `diastolic_bp_mean` | 2618 | 28.29% |
| `pulse_rate` | 2512 | 27.15% |

## Outlier Review Summary

Outlier rules are review ranges, not automatic deletion rules. Flagged values
should be checked before modeling, visualization, or clinical interpretation.

| Field | Checked Count | Outlier Count | Outlier Rate | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| `bmi` | 8005 | 97 | 1.21% | 12.30 | 86.20 |
| `systolic_bp_mean` | 6717 | 76 | 1.13% | 72.70 | 238.00 |
| `diastolic_bp_mean` | 6636 | 80 | 1.21% | 8.00 | 135.30 |
| `glucose_mg_dl` | 5901 | 5 | 0.08% | 47.00 | 626.00 |
| `total_cholesterol_mg_dl` | 5903 | 4 | 0.07% | 77.00 | 438.00 |
| `triglycerides_mg_dl` | 5901 | 7 | 0.12% | 25.00 | 2923.00 |
| `hba1c_percent` | 6045 | 1 | 0.02% | 3.80 | 16.20 |
| `albumin_creatinine_ratio_mg_g` | 7632 | 6 | 0.08% | 0.27 | 11676.92 |

## Cleaning Recommendations

1. Keep `nhanes_standardized.csv` as the primary standardized dataset.
2. Do not delete outlier rows automatically. Use `nhanes_outlier_summary.csv` as
   a manual review guide.
3. For descriptive statistics, report valid sample size for each indicator.
4. For modeling, either select features with acceptable missing rates or use an
   explicit imputation strategy.
5. For health-risk analysis, build task-specific subsets:
   diabetes analysis can focus on `glucose_mg_dl`, `hba1c_percent`, `bmi`, and
   age; kidney-risk analysis can focus on `creatinine_mg_dl`,
   `blood_urea_nitrogen_mg_dl`, and `albumin_creatinine_ratio_mg_g`.

## Analysis Subsets

Task-specific subsets were generated from the standardized table. Each subset
keeps only the fields relevant to one analysis direction and removes rows with
missing task-critical indicators.

| Subset | Rows | Columns | Purpose |
| --- | ---: | ---: | --- |
| `nhanes_diabetes_analysis.csv` | 5804 | 9 | Diabetes-related indicator analysis |
| `nhanes_kidney_analysis.csv` | 5798 | 11 | Kidney-related indicator analysis |
| `nhanes_cardiovascular_analysis.csv` | 5525 | 12 | Cardiovascular-related indicator analysis |

## Generated Files

| File | Description |
| --- | --- |
| `data/processed/nhanes_quality_summary.csv` | Per-column missingness and numeric distribution summary |
| `data/processed/nhanes_outlier_summary.csv` | Review-range outlier summary for key clinical indicators |
| `data/processed/nhanes_analysis_subset_summary.csv` | Row and column counts for task-specific analysis subsets |
| `data/processed/nhanes_output_validation.csv` | Validation result for expected output shapes |

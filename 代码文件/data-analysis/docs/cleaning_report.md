# Data Cleaning Report

## Data Source

The current workflow uses NHANES 2017-2018 public-use data. Seven tables are
included: `DEMO_J`, `BMX_J`, `BPX_J`, `BIOPRO_J`, `CBC_J`, `GHB_J`, and
`ALB_CR_J`.

The repository also includes fictional, desensitized clinical case samples for
frontend/backend/AI handoff. These samples are stored under
`data/clinical_cases/` and follow the frontend field contract documented in
`docs/data_schema.md`.

## Merge Rule

`DEMO_J` is used as the base table. All other tables are left-joined by `SEQN`.
The merged table contains 9254 rows and 155 columns.

## Standardization Rule

1. Rename `SEQN` to `patient_id`.
2. Keep the full merged table as `nhanes_merged.csv`.
3. Extract selected demographics, body measure, blood pressure, biochemistry,
   blood count, glycohemoglobin, and urine test fields.
4. Rename selected fields to readable snake_case names.
5. Map `RIAGENDR` into `gender`: `1=male`, `2=female`.
6. Compute `systolic_bp_mean` and `diastolic_bp_mean` from repeated blood
   pressure measurements.
7. Convert extremely small placeholder values below `1e-50` into missing values
   in the standardized workflow.

## Clinical Case Preprocessing Rule

`scripts/preprocess.py` handles user-submitted clinical case data:

1. Validate required frontend fields and keep validation errors keyed by
   lowerCamelCase field names.
2. Convert frontend fields such as `patientName`, `chiefComplaint`, and
   `presentIllness` into snake_case fields for AI/NLP modules.
3. Remove HTML tags, normalize whitespace and repeated punctuation, and apply
   synonym mapping such as `发烧 -> 发热` and `拉肚子 -> 腹泻`.
4. Standardize attachments into file name, MIME type, parse status, extracted
   text, failure reason, and confidence fields.
5. Build `clean_text`, `symptoms`, `medical_terms`, and `tokens` for AI
   analysis. `clean_text` uses complaint, history, exam, auxiliary exam, and
   parsed attachment text. Human-entered preliminary diagnosis, treatment, and
   medication fields are kept as structured fields but excluded from
   `clean_text` to avoid label leakage.

`scripts/feature_builder.py` creates dictionary-based keyword features from the
clinical train/test/demo CSV files.

## Data Quality Rule

`scripts/analyze_data_quality.py` reads `nhanes_standardized.csv` and generates
two quality-control outputs:

1. `nhanes_quality_summary.csv`: missing count, missing rate, unique count,
   mean, standard deviation, quartiles, minimum, and maximum for each column.
2. `nhanes_outlier_summary.csv`: review-range checks for key clinical
   indicators, including BMI, blood pressure, glucose, creatinine, cholesterol,
   triglycerides, HbA1c, and urine albumin/creatinine ratio.

The outlier summary is a review aid. Values flagged by these rules should be
checked before modeling or visualization rather than deleted automatically.

## Analysis Subset Rule

`scripts/create_analysis_subsets.py` reads `nhanes_standardized.csv` and creates
three task-specific datasets:

1. `nhanes_diabetes_analysis.csv`: age, BMI, waist, blood pressure, glucose, and
   HbA1c indicators.
2. `nhanes_kidney_analysis.csv`: age, blood pressure, blood urea nitrogen,
   creatinine, uric acid, urine albumin, urine creatinine, and albumin/creatinine
   ratio.
3. `nhanes_cardiovascular_analysis.csv`: age, BMI, waist, blood pressure, pulse,
   cholesterol, triglycerides, glucose, and HbA1c indicators.

Rows with missing task-critical indicators are removed in each subset, while the
full standardized table is kept unchanged.

## Output Validation Rule

`scripts/validate_outputs.py` checks whether the generated CSV files exist and
match the expected row and column counts. It writes
`nhanes_output_validation.csv` as a machine-readable validation summary.

## Outputs

| File | Description |
| --- | --- |
| `data/processed/nhanes_merged.csv` | Full merged table |
| `data/processed/nhanes_missing_summary.csv` | Missing count and missing rate for each merged column |
| `data/processed/nhanes_standardized.csv` | Selected standardized analysis table |
| `data/processed/nhanes_quality_summary.csv` | Data quality summary for standardized fields |
| `data/processed/nhanes_outlier_summary.csv` | Outlier review summary for key clinical indicators |
| `data/processed/nhanes_diabetes_analysis.csv` | Diabetes-focused analysis table |
| `data/processed/nhanes_kidney_analysis.csv` | Kidney-focused analysis table |
| `data/processed/nhanes_cardiovascular_analysis.csv` | Cardiovascular-focused analysis table |
| `data/processed/nhanes_analysis_subset_summary.csv` | Row and column counts for analysis subsets |
| `data/processed/nhanes_output_validation.csv` | Output shape validation summary |

## Current Result

The standardized table contains 9254 rows and 34 columns.
The current quality summary contains 34 rows, and the outlier summary checks 9
key clinical indicators.
The current analysis subsets contain 5804 diabetes rows, 5798 kidney rows, and
5525 cardiovascular rows.
The current output validation summary checks 8 generated CSV files.

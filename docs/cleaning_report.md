# Data Cleaning Report

## Data Source

The current workflow uses NHANES 2017-2018 public-use data. Seven tables are
included: `DEMO_J`, `BMX_J`, `BPX_J`, `BIOPRO_J`, `CBC_J`, `GHB_J`, and
`ALB_CR_J`.

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

## Outputs

| File | Description |
| --- | --- |
| `data/processed/nhanes_merged.csv` | Full merged table |
| `data/processed/nhanes_missing_summary.csv` | Missing count and missing rate for each merged column |
| `data/processed/nhanes_standardized.csv` | Selected standardized analysis table |

## Current Result

The standardized table contains 9254 rows and 34 columns.

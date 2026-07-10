# Medical-Record-System

Medical Record Generation and Analysis System.

## Data Processing

This branch contains the NHANES 2017-2018 data processing workflow used by the
data processing and standardization module.

### Dataset

Raw NHANES files are stored in:

```text
data/raw/nhanes_2017_2018/
```

The current dataset includes demographics, body measures, blood pressure,
biochemistry profile, complete blood count, glycohemoglobin, and urine
albumin/creatinine data.

### Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Recommended one-command workflow:

```bash
python scripts/run_pipeline.py
```

The pipeline runs the scripts in dependency order:

1. Merge the NHANES tables by `SEQN`.
2. Generate the standardized analysis table.
3. Generate data quality and outlier summaries.
4. Generate task-specific analysis datasets.
5. Validate generated output shapes.

You can also run each step manually:

```bash
python scripts/merge_nhanes.py
python scripts/standardize_nhanes.py
python scripts/analyze_data_quality.py
python scripts/create_analysis_subsets.py
python scripts/validate_outputs.py
```

### Outputs

```text
data/processed/nhanes_merged.csv
data/processed/nhanes_missing_summary.csv
data/processed/nhanes_standardized.csv
data/processed/nhanes_quality_summary.csv
data/processed/nhanes_outlier_summary.csv
data/processed/nhanes_diabetes_analysis.csv
data/processed/nhanes_kidney_analysis.csv
data/processed/nhanes_cardiovascular_analysis.csv
data/processed/nhanes_analysis_subset_summary.csv
data/processed/nhanes_output_validation.csv
docs/data_quality_report.md
docs/data_processing_work_summary_zh.md
```

`nhanes_merged.csv` keeps the merged raw columns. `nhanes_standardized.csv`
keeps selected fields with standardized names for later analysis and model
development. The quality and outlier summaries are used to review missing
values, distributions, and suspicious clinical indicator values. The analysis
subsets provide smaller task-specific tables for diabetes, kidney, and
cardiovascular analysis. `docs/data_processing_work_summary_zh.md` summarizes
the data processing work in Chinese for project reporting.

# Medical-Record-System

Medical Record Generation and Analysis System.

## Data Processing

This branch contains the NHANES 2017-2018 data processing workflow used by the
data processing and standardization module.

It now contains two data-processing parts:

1. NHANES numeric indicator processing for large public health data analysis.
2. Clinical case preprocessing for frontend/backend/AI field handoff.

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

### Clinical Case Preprocessing

The clinical case preprocessing module follows the frontend field contract from
`前后端与 AI 交接规范.md`. It maps lowerCamelCase request fields such as
`patientName`, `chiefComplaint`, and `presentIllness` into snake_case fields for
Python AI/NLP modules.

Run:

```bash
python scripts/preprocess.py
python scripts/feature_builder.py
```

Resources and samples:

```text
data/resources/symptom_dict.txt
data/resources/medical_terms.txt
data/resources/stopwords.txt
data/resources/synonyms.json
data/clinical_cases/demo_cases.json
data/clinical_cases/demo_data.csv
data/clinical_cases/train.csv
data/clinical_cases/test.csv
docs/data_schema.md
docs/clinical_field_dictionary.csv
```

Generated outputs:

```text
data/processed/clinical_cases_standardized.json
data/processed/train_keyword_features.csv
data/processed/test_keyword_features.csv
data/processed/demo_data_keyword_features.csv
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

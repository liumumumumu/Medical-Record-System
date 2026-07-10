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

Merge the NHANES tables by `SEQN`:

```bash
python scripts/merge_nhanes.py
```

Generate the standardized analysis table:

```bash
python scripts/standardize_nhanes.py
```

### Outputs

```text
data/processed/nhanes_merged.csv
data/processed/nhanes_missing_summary.csv
data/processed/nhanes_standardized.csv
```

`nhanes_merged.csv` keeps the merged raw columns. `nhanes_standardized.csv`
keeps selected fields with standardized names for later analysis and model
development.

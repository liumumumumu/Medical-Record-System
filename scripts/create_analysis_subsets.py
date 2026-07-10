from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
STANDARDIZED_FILE = PROCESSED_DIR / "nhanes_standardized.csv"

SUBSET_CONFIGS = {
    "diabetes": {
        "output": "nhanes_diabetes_analysis.csv",
        "columns": [
            "patient_id",
            "gender",
            "age_years",
            "bmi",
            "waist_cm",
            "systolic_bp_mean",
            "diastolic_bp_mean",
            "glucose_mg_dl",
            "hba1c_percent",
        ],
        "required": ["age_years", "bmi", "glucose_mg_dl", "hba1c_percent"],
    },
    "kidney": {
        "output": "nhanes_kidney_analysis.csv",
        "columns": [
            "patient_id",
            "gender",
            "age_years",
            "systolic_bp_mean",
            "diastolic_bp_mean",
            "blood_urea_nitrogen_mg_dl",
            "creatinine_mg_dl",
            "uric_acid_mg_dl",
            "urine_albumin_ug_ml",
            "urine_creatinine_mg_dl",
            "albumin_creatinine_ratio_mg_g",
        ],
        "required": [
            "age_years",
            "blood_urea_nitrogen_mg_dl",
            "creatinine_mg_dl",
            "albumin_creatinine_ratio_mg_g",
        ],
    },
    "cardiovascular": {
        "output": "nhanes_cardiovascular_analysis.csv",
        "columns": [
            "patient_id",
            "gender",
            "age_years",
            "bmi",
            "waist_cm",
            "systolic_bp_mean",
            "diastolic_bp_mean",
            "pulse_rate",
            "total_cholesterol_mg_dl",
            "triglycerides_mg_dl",
            "glucose_mg_dl",
            "hba1c_percent",
        ],
        "required": [
            "age_years",
            "bmi",
            "systolic_bp_mean",
            "diastolic_bp_mean",
            "total_cholesterol_mg_dl",
            "triglycerides_mg_dl",
        ],
    },
}


def build_subset(df: pd.DataFrame, columns: list[str], required_columns: list[str]) -> pd.DataFrame:
    missing_columns = [column for column in columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing columns in standardized table: {missing_columns}")

    missing_required = [column for column in required_columns if column not in columns]
    if missing_required:
        raise ValueError(f"Required columns must be included in subset columns: {missing_required}")

    subset = df[columns].copy()
    subset = subset.dropna(subset=required_columns)
    subset = subset.reset_index(drop=True)
    return subset


def build_subset_summary(subsets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for subset_name, subset in subsets.items():
        rows.append(
            {
                "subset_name": subset_name,
                "row_count": int(subset.shape[0]),
                "column_count": int(subset.shape[1]),
                "columns": ",".join(subset.columns),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    if not STANDARDIZED_FILE.exists():
        raise FileNotFoundError(
            f"Missing standardized file: {STANDARDIZED_FILE}. Run scripts/standardize_nhanes.py first."
        )

    df = pd.read_csv(STANDARDIZED_FILE)
    subsets = {}

    for subset_name, config in SUBSET_CONFIGS.items():
        subset = build_subset(df, config["columns"], config["required"])
        subset.to_csv(PROCESSED_DIR / config["output"], index=False, encoding="utf-8-sig")
        subsets[subset_name] = subset
        print(f"{subset_name}: {subset.shape[0]} rows, {subset.shape[1]} columns")

    summary = build_subset_summary(subsets)
    summary.to_csv(PROCESSED_DIR / "nhanes_analysis_subset_summary.csv", index=False, encoding="utf-8-sig")
    print(PROCESSED_DIR / "nhanes_analysis_subset_summary.csv")


if __name__ == "__main__":
    main()

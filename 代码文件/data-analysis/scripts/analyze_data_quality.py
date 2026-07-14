from pathlib import Path

import pandas as pd

from output_io import write_csv


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
STANDARDIZED_FILE = PROCESSED_DIR / "nhanes_standardized.csv"
QUALITY_OUTPUT = PROCESSED_DIR / "nhanes_quality_summary.csv"
OUTLIER_OUTPUT = PROCESSED_DIR / "nhanes_outlier_summary.csv"

OUTLIER_RULES = {
    "bmi": (13, 50, "BMI outside review range"),
    "systolic_bp_mean": (90, 250, "Mean systolic blood pressure outside review range"),
    "diastolic_bp_mean": (40, 140, "Mean diastolic blood pressure outside broad plausibility range"),
    "glucose_mg_dl": (40, 450, "Glucose outside broad plausibility range"),
    "creatinine_mg_dl": (0.2, 15, "Serum creatinine outside broad plausibility range"),
    "total_cholesterol_mg_dl": (70, 400, "Total cholesterol outside broad plausibility range"),
    "triglycerides_mg_dl": (20, 1200, "Triglycerides outside broad plausibility range"),
    "hba1c_percent": (3.5, 16, "HbA1c outside broad plausibility range"),
    "albumin_creatinine_ratio_mg_g": (0, 5000, "Urine albumin/creatinine ratio outside broad plausibility range"),
}


def build_quality_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in df.columns:
        series = df[column]
        numeric = pd.to_numeric(series, errors="coerce")
        is_numeric = pd.api.types.is_numeric_dtype(series)

        row = {
            "column": column,
            "dtype": str(series.dtype),
            "non_null_count": int(series.notna().sum()),
            "missing_count": int(series.isna().sum()),
            "missing_rate": round(float(series.isna().mean()), 4),
            "unique_count": int(series.nunique(dropna=True)),
            "mean": pd.NA,
            "std": pd.NA,
            "min": pd.NA,
            "q1": pd.NA,
            "median": pd.NA,
            "q3": pd.NA,
            "max": pd.NA,
        }

        if is_numeric:
            row.update(
                {
                    "mean": round(float(numeric.mean()), 4) if numeric.notna().any() else pd.NA,
                    "std": round(float(numeric.std()), 4) if numeric.notna().sum() > 1 else pd.NA,
                    "min": round(float(numeric.min()), 4) if numeric.notna().any() else pd.NA,
                    "q1": round(float(numeric.quantile(0.25)), 4) if numeric.notna().any() else pd.NA,
                    "median": round(float(numeric.median()), 4) if numeric.notna().any() else pd.NA,
                    "q3": round(float(numeric.quantile(0.75)), 4) if numeric.notna().any() else pd.NA,
                    "max": round(float(numeric.max()), 4) if numeric.notna().any() else pd.NA,
                }
            )

        rows.append(row)

    return pd.DataFrame(rows)


def build_outlier_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column, (lower, upper, rule) in OUTLIER_RULES.items():
        if column not in df.columns:
            continue

        values = pd.to_numeric(df[column], errors="coerce")
        valid = values.dropna()
        outliers = valid[(valid < lower) | (valid > upper)]
        rows.append(
            {
                "column": column,
                "lower_bound": lower,
                "upper_bound": upper,
                "checked_count": int(valid.shape[0]),
                "outlier_count": int(outliers.shape[0]),
                "outlier_rate": round(float(outliers.shape[0] / valid.shape[0]), 4)
                if valid.shape[0]
                else 0,
                "min": round(float(valid.min()), 4) if valid.shape[0] else pd.NA,
                "max": round(float(valid.max()), 4) if valid.shape[0] else pd.NA,
                "rule": rule,
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    if not STANDARDIZED_FILE.exists():
        raise FileNotFoundError(
            f"Missing standardized file: {STANDARDIZED_FILE}. Run scripts/standardize_nhanes.py first."
        )

    df = pd.read_csv(STANDARDIZED_FILE)
    quality_summary = build_quality_summary(df)
    outlier_summary = build_outlier_summary(df)

    write_csv(quality_summary, QUALITY_OUTPUT)
    write_csv(outlier_summary, OUTLIER_OUTPUT)

    print(f"quality summary rows: {quality_summary.shape[0]}")
    print(f"outlier summary rows: {outlier_summary.shape[0]}")
    print(QUALITY_OUTPUT)
    print(OUTLIER_OUTPUT)


if __name__ == "__main__":
    main()

from pathlib import Path

import pandas as pd

from output_io import write_csv


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
MERGED_FILE = PROCESSED_DIR / "nhanes_merged.csv"
OUTPUT_FILE = PROCESSED_DIR / "nhanes_standardized.csv"

FIELD_MAP = {
    "patient_id": "patient_id",
    "RIAGENDR": "gender_code",
    "RIDAGEYR": "age_years",
    "RIDRETH3": "race_ethnicity_code",
    "INDFMPIR": "family_income_poverty_ratio",
    "BMXWT": "weight_kg",
    "BMXHT": "height_cm",
    "BMXBMI": "bmi",
    "BMXWAIST": "waist_cm",
    "BPXPLS": "pulse_rate",
    "LBXSAL": "albumin_g_dl",
    "LBXSAPSI": "alkaline_phosphatase_u_l",
    "LBXSASSI": "ast_u_l",
    "LBXSATSI": "alt_u_l",
    "LBXSBU": "blood_urea_nitrogen_mg_dl",
    "LBXSCR": "creatinine_mg_dl",
    "LBXSGL": "glucose_mg_dl",
    "LBXSGTSI": "ggt_u_l",
    "LBXSTB": "total_bilirubin_mg_dl",
    "LBXSCH": "total_cholesterol_mg_dl",
    "LBXSTR": "triglycerides_mg_dl",
    "LBXSUA": "uric_acid_mg_dl",
    "LBXWBCSI": "white_blood_cell_1000_ul",
    "LBXRBCSI": "red_blood_cell_million_ul",
    "LBXHGB": "hemoglobin_g_dl",
    "LBXHCT": "hematocrit_percent",
    "LBXPLTSI": "platelet_1000_ul",
    "LBXGH": "hba1c_percent",
    "URXUMA": "urine_albumin_ug_ml",
    "URXUCR": "urine_creatinine_mg_dl",
    "URDACT": "albumin_creatinine_ratio_mg_g",
}


def main() -> None:
    if not MERGED_FILE.exists():
        raise FileNotFoundError(
            f"Missing merged file: {MERGED_FILE}. Run scripts/merge_nhanes.py first."
        )

    df = pd.read_csv(MERGED_FILE)
    numeric_columns = df.select_dtypes(include="number").columns
    df[numeric_columns] = df[numeric_columns].mask(df[numeric_columns].abs().lt(1e-50), pd.NA)

    systolic_cols = ["BPXSY1", "BPXSY2", "BPXSY3", "BPXSY4"]
    diastolic_cols = ["BPXDI1", "BPXDI2", "BPXDI3", "BPXDI4"]
    bp_mean = pd.DataFrame(
        {
            "systolic_bp_mean": df[systolic_cols].mean(axis=1, skipna=True).round(1),
            "diastolic_bp_mean": df[diastolic_cols].mean(axis=1, skipna=True).round(1),
        }
    )

    standardized = pd.concat([df[list(FIELD_MAP.keys())].rename(columns=FIELD_MAP), bp_mean], axis=1)
    standardized["gender"] = standardized["gender_code"].map({1: "male", 2: "female"})

    ordered_columns = [
        "patient_id",
        "gender",
        "gender_code",
        "age_years",
        "race_ethnicity_code",
        "family_income_poverty_ratio",
        "weight_kg",
        "height_cm",
        "bmi",
        "waist_cm",
        "systolic_bp_mean",
        "diastolic_bp_mean",
        "pulse_rate",
        "albumin_g_dl",
        "alkaline_phosphatase_u_l",
        "ast_u_l",
        "alt_u_l",
        "blood_urea_nitrogen_mg_dl",
        "creatinine_mg_dl",
        "glucose_mg_dl",
        "ggt_u_l",
        "total_bilirubin_mg_dl",
        "total_cholesterol_mg_dl",
        "triglycerides_mg_dl",
        "uric_acid_mg_dl",
        "white_blood_cell_1000_ul",
        "red_blood_cell_million_ul",
        "hemoglobin_g_dl",
        "hematocrit_percent",
        "platelet_1000_ul",
        "hba1c_percent",
        "urine_albumin_ug_ml",
        "urine_creatinine_mg_dl",
        "albumin_creatinine_ratio_mg_g",
    ]
    standardized = standardized[ordered_columns]
    write_csv(standardized, OUTPUT_FILE)

    print(f"standardized rows: {standardized.shape[0]}")
    print(f"standardized columns: {standardized.shape[1]}")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()

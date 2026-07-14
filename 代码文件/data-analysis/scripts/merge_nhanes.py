from pathlib import Path

import pandas as pd

from output_io import write_csv


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "nhanes_2017_2018"
PROCESSED_DIR = ROOT / "data" / "processed"

TABLES = [
    ("BMX_J.csv", "bmx"),
    ("BPX_J.csv", "bpx"),
    ("BIOPRO_J.csv", "biopro"),
    ("CBC_J.csv", "cbc"),
    ("GHB_J.csv", "ghb"),
    ("ALB_CR_J.csv", "alb_cr"),
]


def read_table(filename: str) -> pd.DataFrame:
    path = RAW_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    df = pd.read_csv(path)
    if "SEQN" not in df.columns:
        raise ValueError(f"{filename} does not contain SEQN")
    df["SEQN"] = df["SEQN"].astype("Int64")
    return df


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    merged = read_table("DEMO_J.csv")
    for filename, _name in TABLES:
        table = read_table(filename)
        merged = merged.merge(table, on="SEQN", how="left")

    merged = merged.rename(columns={"SEQN": "patient_id"})
    write_csv(merged, PROCESSED_DIR / "nhanes_merged.csv")

    summary = pd.DataFrame(
        {
            "column": merged.columns,
            "missing_count": merged.isna().sum().values,
            "missing_rate": merged.isna().mean().round(4).values,
            "dtype": [str(dtype) for dtype in merged.dtypes],
        }
    )
    write_csv(summary, PROCESSED_DIR / "nhanes_missing_summary.csv")

    print(f"merged rows: {merged.shape[0]}")
    print(f"merged columns: {merged.shape[1]}")
    print(PROCESSED_DIR / "nhanes_merged.csv")
    print(PROCESSED_DIR / "nhanes_missing_summary.csv")


if __name__ == "__main__":
    main()

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
VALIDATION_OUTPUT = PROCESSED_DIR / "nhanes_output_validation.csv"

EXPECTED_SHAPES = {
    "nhanes_merged.csv": (9254, 155),
    "nhanes_standardized.csv": (9254, 34),
    "nhanes_quality_summary.csv": (34, 13),
    "nhanes_outlier_summary.csv": (9, 9),
    "nhanes_diabetes_analysis.csv": (5804, 9),
    "nhanes_kidney_analysis.csv": (5798, 11),
    "nhanes_cardiovascular_analysis.csv": (5525, 12),
    "nhanes_analysis_subset_summary.csv": (3, 4),
}


def validate_outputs(
    processed_dir: Path = PROCESSED_DIR,
    expected_shapes: dict[str, tuple[int, int]] = EXPECTED_SHAPES,
) -> pd.DataFrame:
    rows = []
    failures = []

    for filename, expected_shape in expected_shapes.items():
        path = processed_dir / filename
        if not path.exists():
            rows.append(
                {
                    "filename": filename,
                    "expected_shape": str(expected_shape),
                    "actual_shape": "missing",
                    "passed": False,
                }
            )
            failures.append(f"{filename}: missing")
            continue

        df = pd.read_csv(path)
        actual_shape = tuple(df.shape)
        passed = actual_shape == expected_shape
        rows.append(
            {
                "filename": filename,
                "expected_shape": str(expected_shape),
                "actual_shape": str(actual_shape),
                "passed": passed,
            }
        )

        if not passed:
            failures.append(f"{filename}: expected {expected_shape}, got {actual_shape}")

    summary = pd.DataFrame(rows)
    if failures:
        raise ValueError("Output validation failed: " + "; ".join(failures))

    return summary


def main() -> None:
    summary = validate_outputs()
    summary.to_csv(VALIDATION_OUTPUT, index=False, encoding="utf-8-sig")
    print(f"validated outputs: {summary.shape[0]}")
    print(VALIDATION_OUTPUT)


if __name__ == "__main__":
    main()

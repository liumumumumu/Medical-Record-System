from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "data" / "resources"
CLINICAL_CASE_DIR = ROOT / "data" / "clinical_cases"
PROCESSED_DIR = ROOT / "data" / "processed"


def read_terms(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def load_keywords(resource_dir: Path = RESOURCE_DIR) -> list[str]:
    keywords = read_terms(resource_dir / "symptom_dict.txt")
    keywords.extend(read_terms(resource_dir / "medical_terms.txt"))
    seen: set[str] = set()
    unique_keywords: list[str] = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)
    return unique_keywords


def row_text(row: pd.Series) -> str:
    parts: list[str] = []
    for column in ("clean_text", "tokens"):
        value = row.get(column, "")
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif pd.notna(value):
            parts.append(str(value))
    return " ".join(parts)


def build_keyword_features(cases: pd.DataFrame, keywords: Iterable[str]) -> pd.DataFrame:
    feature_rows: list[dict[str, object]] = []
    keyword_list = list(keywords)

    for _, row in cases.iterrows():
        text = row_text(row)
        feature_row: dict[str, object] = {"case_id": row.get("case_id", "")}
        for keyword in keyword_list:
            feature_row[f"kw_{keyword}"] = 1 if keyword in text else 0
        feature_row["diagnosis_label"] = row.get("diagnosis_label", "")
        feature_rows.append(feature_row)

    columns = ["case_id"] + [f"kw_{keyword}" for keyword in keyword_list] + ["diagnosis_label"]
    return pd.DataFrame(feature_rows, columns=columns)


def build_feature_file(
    input_file: Path,
    output_file: Path,
    resource_dir: Path = RESOURCE_DIR,
) -> pd.DataFrame:
    cases = pd.read_csv(input_file)
    features = build_keyword_features(cases, load_keywords(resource_dir))
    output_file.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(output_file, index=False, encoding="utf-8-sig")
    return features


def main() -> None:
    for filename in ("train.csv", "test.csv", "demo_data.csv"):
        input_file = CLINICAL_CASE_DIR / filename
        output_file = PROCESSED_DIR / filename.replace(".csv", "_keyword_features.csv")
        features = build_feature_file(input_file, output_file)
        print(f"{output_file.name}: {features.shape[0]} rows, {features.shape[1]} columns")


if __name__ == "__main__":
    main()

import json
import sys
from collections import Counter
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from src.config import (  # noqa: E402
    CONFIG_DIR,
    DATASET_ROOT,
    RESOURCE_DIR,
    ensure_output_directories,
    load_json,
)


ENTITY_TYPES = {
    "dis": "疾病",
    "dru": "药物",
    "ite": "检查",
    "pro": "医疗操作",
    "equ": "医疗设备",
    "dep": "科室",
}


def build_medical_terms() -> dict[str, str]:
    cmeee_dir = DATASET_ROOT / "CBLUE_mirrors" / "CMeEE-V2"
    counts: Counter[tuple[str, str]] = Counter()
    for split in ("train", "dev"):
        path = cmeee_dir / f"CMeEE-V2_{split}.json"
        for item in load_json(path):
            for entity in item.get("entities", []):
                entity_type = entity.get("type")
                term = str(entity.get("entity", "")).strip()
                if entity_type in ENTITY_TYPES and 2 <= len(term) <= 30:
                    counts[(term, ENTITY_TYPES[entity_type])] += 1

    terms: dict[str, str] = {}
    for (term, entity_type), count in counts.most_common():
        if count >= 2 and term not in terms:
            terms[term] = entity_type
    ordered = dict(sorted(terms.items(), key=lambda item: (-len(item[0]), item[0])))
    (RESOURCE_DIR / "medical_terms.json").write_text(
        json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return ordered


def _load_disease_rows() -> list[dict[str, str]]:
    path = DATASET_ROOT / "Disease_Database" / "disease_database_zh.json"
    if not path.exists():
        return []
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError("Disease_Database must be a JSON array")
    return [item for item in data if isinstance(item, dict)]


def build_knowledge_index() -> dict[str, object]:
    diagnoses = load_json(CONFIG_DIR / "diagnosis_labels.json")
    rows = _load_disease_rows()
    database_documents: list[str] = []
    for row in rows:
        disease = str(row.get("disease", "")).strip()
        symptom = str(row.get("common_symptom", "")).strip()
        if disease and symptom:
            database_documents.append(f"{disease} {symptom}")

    profiles: dict[str, dict[str, object]] = {}
    allowed_documents: list[str] = []
    labels: list[str] = []
    for diagnosis in diagnoses:
        label = diagnosis["label"]
        aliases = [label, *diagnosis["aliases"]]
        matched_rows = [
            row
            for row in rows
            if any(
                alias == str(row.get("disease", "")).strip()
                or alias in str(row.get("disease", "")).strip()
                for alias in aliases
            )
        ]
        database_symptoms = [
            str(row.get("common_symptom", "")).strip()
            for row in matched_rows
            if str(row.get("common_symptom", "")).strip()
        ]
        document = " ".join(
            [label, *diagnosis["aliases"], *diagnosis["keySymptoms"], *database_symptoms]
        )
        labels.append(label)
        allowed_documents.append(document)
        profiles[label] = {
            "core": diagnosis["core"],
            "aliases": diagnosis["aliases"],
            "keySymptoms": diagnosis["keySymptoms"],
            "matchedDatabaseRows": len(matched_rows),
        }

    corpus = database_documents + allowed_documents
    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 4),
        min_df=1,
        max_features=60_000,
        sublinear_tf=True,
    )
    vectorizer.fit(corpus)
    matrix = vectorizer.transform(allowed_documents)
    artifact = {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "labels": labels,
        "profiles": profiles,
        "sourceRowCount": len(rows),
        "indexedDocumentCount": len(database_documents),
    }
    joblib.dump(artifact, RESOURCE_DIR / "knowledge_index.joblib")
    (RESOURCE_DIR / "knowledge_profiles.json").write_text(
        json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return artifact


def main() -> None:
    ensure_output_directories()
    terms = build_medical_terms()
    knowledge = build_knowledge_index()
    report = {
        "medicalTermCount": len(terms),
        "diseaseDatabaseRows": knowledge["sourceRowCount"],
        "indexedDiseaseDocuments": knowledge["indexedDocumentCount"],
        "supportedDiagnosisCount": len(knowledge["labels"]),
    }
    (RESOURCE_DIR / "resource_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

import json
import sys
from collections import Counter
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from src.config import MODEL_DIR  # noqa: E402
from src.service import MedicalAIService  # noqa: E402


def evaluate() -> dict[str, object]:
    cases = json.loads((SERVICE_ROOT / "ai_test_cases.json").read_text(encoding="utf-8"))
    diagnosis_cases = [case for case in cases if case["kind"] == "diagnosis"]
    service = MedicalAIService()
    hits = 0
    per_diagnosis: Counter[str] = Counter()
    per_diagnosis_hits: Counter[str] = Counter()
    misses: list[dict[str, object]] = []
    for case in diagnosis_cases:
        payload = {
            "name": "测试患者",
            "gender": case.get("gender", "女"),
            "age": case.get("age", 30),
            "chiefComplaint": case["text"],
            "historyPresentIllness": case["text"],
        }
        result = service.analyze(payload)
        expected = case["expectedDiagnosis"]
        predicted = [result.diagnosis_top1, *result.diagnosis_candidates]
        per_diagnosis[expected] += 1
        if expected in predicted:
            hits += 1
            per_diagnosis_hits[expected] += 1
        else:
            misses.append({"id": case["id"], "expected": expected, "predicted": predicted})

    metrics: dict[str, object] = {
        "caseCount": len(diagnosis_cases),
        "hitCount": hits,
        "top3HitRate": round(hits / len(diagnosis_cases), 6),
        "representedDiagnosisCount": len(per_diagnosis),
        "perDiagnosis": {
            label: {
                "cases": count,
                "hits": per_diagnosis_hits[label],
                "hitRate": round(per_diagnosis_hits[label] / count, 6),
            }
            for label, count in sorted(per_diagnosis.items())
        },
        "misses": misses,
        "scopeNote": "Curated course-project cases; this is not a clinical validation metric.",
    }
    (MODEL_DIR / "curated_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return metrics


if __name__ == "__main__":
    evaluate()

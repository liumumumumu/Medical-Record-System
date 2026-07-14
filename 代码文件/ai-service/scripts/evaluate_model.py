import json
import sys
from pathlib import Path

import joblib
from sklearn.metrics import accuracy_score, classification_report, f1_score


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from scripts.train_model import load_split  # noqa: E402
from src.config import MODEL_DIR  # noqa: E402


def evaluate() -> dict[str, float]:
    artifact = joblib.load(MODEL_DIR / "diagnosis_model.joblib")
    texts, labels = load_split("test")
    matrix = artifact["vectorizer"].transform(texts)
    predictions = artifact["classifier"].predict(matrix)
    metrics = {
        "accuracy": round(float(accuracy_score(labels, predictions)), 6),
        "macroF1": round(float(f1_score(labels, predictions, average="macro")), 6),
    }
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(classification_report(labels, predictions, digits=4, zero_division=0))
    return metrics


if __name__ == "__main__":
    evaluate()

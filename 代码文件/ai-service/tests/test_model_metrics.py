import json

from src.config import MODEL_DIR


def test_supervised_model_meets_acceptance_threshold():
    metrics = json.loads((MODEL_DIR / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["test"]["accuracy"] >= 0.80
    assert metrics["test"]["macroF1"] >= 0.80
    assert metrics["sampleCounts"] == {"train": 1358, "dev": 445, "test": 453}

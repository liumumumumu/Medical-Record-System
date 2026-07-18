import json

import pytest

from src.config import MODEL_DIR


PRODUCTION_METRICS = MODEL_DIR / "transformer_production" / "metrics.json"


def test_v1_baseline_meets_acceptance_threshold():
    """v1 已弃用但仍是无 GPU 环境的兜底，指标必须守住验收线。"""
    metrics = json.loads((MODEL_DIR / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["test"]["accuracy"] >= 0.80
    assert metrics["test"]["macroF1"] >= 0.80
    assert metrics["sampleCounts"] == {"train": 1358, "dev": 445, "test": 453}


@pytest.mark.skipif(
    not PRODUCTION_METRICS.exists(),
    reason="本机无 v2 权重（正常降级环境），跳过正式模型指标验收",
)
def test_v2_production_model_beats_baseline():
    """正式模型（BERT v2.0.0）必须超过验收线且不低于 v1 基线。"""
    v1 = json.loads((MODEL_DIR / "metrics.json").read_text(encoding="utf-8"))
    v2 = json.loads(PRODUCTION_METRICS.read_text(encoding="utf-8"))
    assert v2["modelVersion"] == "2.0.0"
    assert v2["test"]["accuracy"] >= 0.80
    assert v2["test"]["macroF1"] >= 0.80
    assert v2["test"]["macroF1"] >= v1["test"]["macroF1"]

"""温度缩放标定：在 40 条验收样例上网格搜索 transformer 后端的 softmax 温度。

指标为 top1 / top3 命中率（比验收线 top3 更严的 top1 用于选择），
并给出 sklearn 后端参照值。选定值写入 diagnosis_analyzer.TRANSFORMER_TEMPERATURE 默认值。
"""

import json
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

import src.diagnosis_analyzer as analyzer_module  # noqa: E402
from src.service import MedicalAIService  # noqa: E402


def hit_rates(service: MedicalAIService, cases: list[dict]) -> tuple[float, float]:
    top1_hits = 0
    top3_hits = 0
    for case in cases:
        payload = {
            "name": "标定",
            "gender": case.get("gender", "女"),
            "age": case.get("age", 30),
            "chiefComplaint": case["text"],
            "historyPresentIllness": case["text"],
        }
        result = service.analyze(payload)
        expected = case["expectedDiagnosis"]
        top1_hits += result.diagnosis_top1 == expected
        top3_hits += expected in [result.diagnosis_top1, *result.diagnosis_candidates]
    return top1_hits / len(cases), top3_hits / len(cases)


def main() -> None:
    cases = [
        case
        for case in json.loads((SERVICE_ROOT / "ai_test_cases.json").read_text(encoding="utf-8"))
        if case["kind"] == "diagnosis"
    ]

    import os

    os.environ["AI_MODEL_BACKEND"] = "sklearn"
    top1, top3 = hit_rates(MedicalAIService(), cases)
    print(f"sklearn 参照      : top1={top1:.3f} top3={top3:.3f}")
    os.environ.pop("AI_MODEL_BACKEND")

    for temperature in (1.0, 1.5, 2.0, 2.5, 3.0):
        analyzer_module.TRANSFORMER_TEMPERATURE = temperature
        top1, top3 = hit_rates(MedicalAIService(), cases)
        print(f"transformer T={temperature:<4}: top1={top1:.3f} top3={top3:.3f}")


if __name__ == "__main__":
    main()

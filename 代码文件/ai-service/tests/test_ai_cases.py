import json

from src.config import SERVICE_ROOT
from src.service import MedicalAIService


def test_curated_cases_reach_top3_acceptance():
    cases = json.loads((SERVICE_ROOT / "ai_test_cases.json").read_text(encoding="utf-8"))
    diagnosis_cases = [case for case in cases if case["kind"] == "diagnosis"]
    service = MedicalAIService()
    hits = 0
    represented = set()
    for case in diagnosis_cases:
        payload = {
            "name": "测试患者",
            "gender": case.get("gender", "女"),
            "age": case.get("age", 30),
            "chiefComplaint": case["text"],
            "historyPresentIllness": case["text"],
            "pastHistory": case.get("pastHistory", "无特殊"),
            "physicalExam": case.get("physicalExam", "未提供"),
            "labResults": case.get("labResults", "未提供"),
        }
        result = service.analyze(payload)
        represented.add(case["expectedDiagnosis"])
        if case["expectedDiagnosis"] in [result.diagnosis_top1, *result.diagnosis_candidates]:
            hits += 1
    assert len(diagnosis_cases) >= 40
    assert len(represented) == 20
    assert hits / len(diagnosis_cases) >= 0.80


def test_edge_cases_are_safe():
    cases = json.loads((SERVICE_ROOT / "ai_test_cases.json").read_text(encoding="utf-8"))
    service = MedicalAIService()
    for case in cases:
        if case["kind"] != "edge":
            continue
        payload = {
            "name": "边界测试",
            "gender": "男",
            "age": 40,
            "chiefComplaint": case["text"],
            "historyPresentIllness": case["text"],
        }
        result = service.analyze(payload)
        assert case["expectedAdviceContains"] in result.treatment_advice

import json

from app import create_app
from src.config import SERVICE_ROOT


VALID_PAYLOAD = {
    "name": "张三",
    "gender": "男",
    "age": 28,
    "chiefComplaint": "发热咳嗽3天，伴咽痛和鼻塞",
    "historyPresentIllness": "受凉后出现发热、咳嗽、咽痛和鼻塞",
    "pastHistory": "无高血压糖尿病史",
    "physicalExam": "体温38.5℃，咽部充血",
    "labResults": "白细胞轻度升高",
}

FRONTEND_PAYLOAD = {
    "patientName": "李四",
    "gender": "female",
    "age": 130,
    "department": "internal",
    "visitDate": "2026-07-10",
    "chiefComplaint": "高热咳嗽伴全身酸痛2天",
    "presentIllness": "突然高烧39.5℃，全身乏力、肌肉酸痛、头痛并咳嗽",
    "pastHistory": "无高血压糖尿病史",
    "allergyHistory": "无",
    "vitalSigns": "体温39.5℃，血压120/80mmHg",
    "physicalExam": "未见明显异常",
    "auxiliaryExam": "白细胞正常",
    "attachments": ["blood-test.pdf"],
    "preliminaryDiagnosis": "待查",
    "treatmentTaken": "休息补水",
    "medicationUsage": "无",
    "generationNeeds": ["record", "diagnosis", "full-report"],
}

STANDARDIZED_PAYLOAD = {
    "patient_name": "张某",
    "gender": "male",
    "age": 32,
    "department": "internal",
    "visit_date": "2026-07-10",
    "chief_complaint": "发热、咳嗽 3 天",
    "present_illness": "3天前受凉后出现发热、咳嗽、乏力，无明显气促。",
    "past_history": "无高血压、糖尿病史。",
    "allergy_history": "无",
    "vital_signs": "体温 38.5℃，脉搏 88 次/分。",
    "physical_exam": "咽部充血，双肺未闻及明显湿啰音。",
    "auxiliary_exam": "血常规提示白细胞轻度升高。",
    "preliminary_diagnosis": "上呼吸道感染",
    "treatment_taken": "已给予退热处理。",
    "medication_usage": "口服对乙酰氨基酚。",
    "generation_needs": ["record", "symptom", "diagnosis"],
    "attachments": [
        {
            "id": "file_01",
            "file_name": "blood-test.pdf",
            "mime_type": "application/pdf",
            "parse_status": "parsed",
            "extracted_text": "白细胞轻度升高，C反应蛋白轻度升高。",
            "failure_reason": "",
            "confidence": 0.93,
        }
    ],
    "clean_text": "不可信派生文本：腹痛、腹泻、肺炎、处方药。",
    "symptoms": ["腹泻"],
    "medical_terms": ["肺炎"],
    "tokens": ["腹泻", "肺炎"],
    "source_schema": "frontend_case_v0.2",
}


def test_health_contract():
    client = create_app().test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"
    assert response.json["modelLoaded"] is True
    assert response.json["knowledgeLoaded"] is True
    assert response.json["supportedDiagnoses"] == 20


def test_analysis_contract_and_camel_case_output():
    client = create_app().test_client()
    response = client.post("/nlp/analyze", json=VALID_PAYLOAD)
    assert response.status_code == 200
    assert response.content_type == "application/json; charset=utf-8"
    expected_fields = {
        "generatedRecord",
        "symptoms",
        "medicalTerms",
        "diagnosisTop1",
        "diagnosisCandidates",
        "diagnosisReason",
        "treatmentAdvice",
    }
    assert set(response.json) == expected_fields
    assert len(response.json["diagnosisCandidates"]) <= 3
    assert "不替代医生诊断" in response.json["treatmentAdvice"]


def test_accepts_snake_case_input():
    client = create_app().test_client()
    payload = {
        "name": "李四",
        "gender": "女",
        "age": 35,
        "chief_complaint": "腹痛腹泻伴恶心",
        "history_present_illness": "腹泻一天，大便稀，伴呕吐",
        "past_history": "无特殊",
        "physical_exam": "腹部轻压痛",
        "lab_results": "未提供",
    }
    response = client.post("/nlp/analyze", json=payload)
    assert response.status_code == 200
    assert response.json["diagnosisTop1"] != "暂无法确定"


def test_validation_error_contract():
    client = create_app().test_client()
    response = client.post("/nlp/analyze", json={"name": ""})
    assert response.status_code == 400
    assert set(response.json) == {"code", "message", "data"}
    assert response.json["code"] == 400


def test_frontend_compatible_contract():
    client = create_app().test_client()
    response = client.post("/nlp/analyze/frontend", json=FRONTEND_PAYLOAD)
    assert response.status_code == 200
    assert set(response.json) == {
        "status",
        "generatedAt",
        "processingTimeMs",
        "model",
        "summary",
        "structuredRecord",
        "analysis",
        "attachments",
        "failureReason",
    }
    assert response.json["summary"]["patientName"] == "李四"
    assert response.json["summary"]["gender"] == "female"
    assert response.json["summary"]["age"] == 130
    assert response.json["structuredRecord"]["presentIllness"] == FRONTEND_PAYLOAD["presentIllness"]
    assert "流行性感冒" in [
        response.json["analysis"]["diagnosisTop1"],
        *response.json["analysis"]["diagnosisCandidates"],
    ]
    assert response.json["analysis"]["generationNeeds"] == FRONTEND_PAYLOAD["generationNeeds"]
    assert response.json["model"]["version"] == "1.0.0"
    assert response.json["attachments"][0]["fileName"] == "blood-test.pdf"


def test_frontend_validation_error_maps_field_names():
    client = create_app().test_client()
    payload = dict(FRONTEND_PAYLOAD)
    payload["presentIllness"] = ""
    response = client.post("/nlp/analyze/frontend", json=payload)
    assert response.status_code == 400
    assert response.json["code"] == "VALIDATION_ERROR"
    assert response.json["fieldErrors"] == {"presentIllness": "该字段为必填项"}
    assert response.json["requestId"].startswith("req_")


def test_frontend_accepts_missing_optional_past_history():
    payload = dict(FRONTEND_PAYLOAD)
    payload.pop("pastHistory")
    response = create_app().test_client().post("/nlp/analyze/frontend", json=payload)
    assert response.status_code == 200
    assert response.json["structuredRecord"]["pastHistory"] == "未提供"


def test_rejects_fractional_age_instead_of_truncating_it():
    client = create_app().test_client()
    for age in (1.9, "1.9"):
        payload = dict(FRONTEND_PAYLOAD, age=age)
        response = client.post("/nlp/analyze/frontend", json=payload)
        assert response.status_code == 400
        assert response.json["fieldErrors"] == {"age": "请输入整数年龄"}


def test_standardized_case_contract_and_attachment_metadata():
    response = create_app().test_client().post(
        "/nlp/analyze/standardized", json=STANDARDIZED_PAYLOAD
    )
    assert response.status_code == 200
    assert response.json["summary"]["patientName"] == "张某"
    assert response.json["structuredRecord"]["presentIllness"] == (
        STANDARDIZED_PAYLOAD["present_illness"]
    )
    assert response.json["attachments"][0] == {
        "id": "file_01",
        "fileName": "blood-test.pdf",
        "mimeType": "application/pdf",
        "url": "",
        "processingStatus": "parsed",
        "extractedText": "白细胞轻度升高，C反应蛋白轻度升高。",
        "failureReason": "",
        "confidence": 0.93,
    }
    assert "不替代医生诊断" in response.json["analysis"]["disclaimer"]


def test_standardized_case_ignores_derived_and_label_fields_for_inference():
    client = create_app().test_client()
    baseline = dict(STANDARDIZED_PAYLOAD)
    baseline.update(
        {
            "clean_text": "",
            "symptoms": [],
            "medical_terms": [],
            "tokens": [],
            "preliminary_diagnosis": "",
            "treatment_taken": "",
            "medication_usage": "",
        }
    )
    baseline_analysis = client.post(
        "/nlp/analyze/standardized", json=baseline
    ).json["analysis"]
    poisoned_analysis = client.post(
        "/nlp/analyze/standardized", json=STANDARDIZED_PAYLOAD
    ).json["analysis"]

    for field in (
        "symptoms",
        "medicalTerms",
        "diagnosisTop1",
        "diagnosisCandidates",
        "diagnosisReason",
    ):
        assert poisoned_analysis[field] == baseline_analysis[field]


def test_standardized_case_validation_uses_snake_case_fields():
    payload = dict(STANDARDIZED_PAYLOAD)
    payload["present_illness"] = ""
    response = create_app().test_client().post(
        "/nlp/analyze/standardized", json=payload
    )
    assert response.status_code == 400
    assert response.json["code"] == "VALIDATION_ERROR"
    assert response.json["fieldErrors"] == {"present_illness": "该字段为必填项"}

    payload = dict(STANDARDIZED_PAYLOAD)
    payload["chief_complaint"] = "咳嗽" * 101
    response = create_app().test_client().post(
        "/nlp/analyze/standardized", json=payload
    )
    assert response.status_code == 400
    assert response.json["fieldErrors"] == {
        "chief_complaint": "不能超过 200 个字符"
    }

    payload = dict(STANDARDIZED_PAYLOAD)
    payload.pop("past_history")
    response = create_app().test_client().post(
        "/nlp/analyze/standardized", json=payload
    )
    assert response.status_code == 200
    assert response.json["structuredRecord"]["pastHistory"] == "未提供"


def test_metadata_exposes_model_and_limits():
    client = create_app().test_client()
    response = client.get("/metadata")
    assert response.status_code == 200
    assert response.json["modelVersion"] == "1.0.0"
    assert len(response.json["supportedDiagnoses"]) == 20
    assert response.json["coreMetrics"]["accuracy"] >= 0.80
    assert response.json["limits"]["attachmentParsing"] is False


def test_frontend_rejects_invalid_enums():
    client = create_app().test_client()
    payload = dict(FRONTEND_PAYLOAD)
    payload["gender"] = "unknown"
    payload["generationNeeds"] = ["unsupported"]
    response = client.post("/nlp/analyze/frontend", json=payload)
    assert response.status_code == 400
    assert response.json["fieldErrors"]["gender"] == "性别必须为 male 或 female"
    assert response.json["fieldErrors"]["generationNeeds"] == "生成需求枚举值无效"


def test_handoff_examples_match_live_contract():
    request_payload = json.loads(
        (SERVICE_ROOT / "handoff" / "frontend_request.example.json").read_text(encoding="utf-8")
    )
    response_example = json.loads(
        (SERVICE_ROOT / "handoff" / "frontend_response.example.json").read_text(encoding="utf-8")
    )
    response = create_app().test_client().post("/nlp/analyze/frontend", json=request_payload)
    assert response.status_code == 200
    assert response.json["analysis"]["diagnosisTop1"] == response_example["analysis"]["diagnosisTop1"]
    assert response.json["analysis"]["diagnosisCandidates"] == response_example["analysis"]["diagnosisCandidates"]
    assert response.json["summary"] == response_example["summary"]
    assert response.json["model"]["version"] == response_example["model"]["version"]

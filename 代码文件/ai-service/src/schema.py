from dataclasses import dataclass
import math
import re
from typing import Any

from src.config import MODEL_VERSION


class ValidationError(ValueError):
    def __init__(self, message: str, field_errors: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.field_errors = field_errors or {}


def _value(payload: dict[str, Any], camel: str, snake: str, default: Any = "") -> Any:
    if camel in payload:
        return payload[camel]
    return payload.get(snake, default)


def _parse_age(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError
        return int(value)
    if isinstance(value, str) and re.fullmatch(r"\d+", value.strip()):
        return int(value.strip())
    raise ValueError


@dataclass(frozen=True)
class PatientInput:
    name: str
    gender: str
    age: int
    chief_complaint: str
    history_present_illness: str
    past_history: str = "未提供"
    physical_exam: str = "未提供"
    lab_results: str = "未提供"
    gender_code: str = ""
    department: str = ""
    visit_date: str = ""
    allergy_history: str = "未提供"
    vital_signs: str = "未提供"
    preliminary_diagnosis: str = ""
    treatment_taken: str = ""
    medication_usage: str = ""
    generation_needs: tuple[str, ...] = ()
    attachments: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: Any) -> "PatientInput":
        if not isinstance(payload, dict):
            raise ValidationError("请求体必须是 JSON 对象")

        name = str(payload.get("patientName", _value(payload, "name", "name", ""))).strip()
        raw_gender = str(_value(payload, "gender", "gender", "")).strip()
        gender = {"male": "男", "female": "女"}.get(raw_gender, raw_gender)
        raw_age = _value(payload, "age", "age", None)
        chief_complaint = str(
            _value(payload, "chiefComplaint", "chief_complaint", "")
        ).strip()
        history_present_illness = str(
            payload.get(
                "presentIllness",
                _value(payload, "historyPresentIllness", "history_present_illness", ""),
            )
        ).strip()

        missing = []
        for field_name, field_value in (
            ("name", name),
            ("gender", gender),
            ("chiefComplaint", chief_complaint),
            ("historyPresentIllness", history_present_illness),
        ):
            if not field_value:
                missing.append(field_name)
        if missing:
            field_errors = {field: "该字段为必填项" for field in missing}
            raise ValidationError(f"缺少必填字段: {', '.join(missing)}", field_errors)

        try:
            age = _parse_age(raw_age)
        except ValueError as error:
            raise ValidationError("age 必须是 0 到 130 之间的整数", {"age": "请输入整数年龄"}) from error
        if not 0 <= age <= 130:
            raise ValidationError(
                "age 必须是 0 到 130 之间的整数",
                {"age": "年龄必须在 0 至 130 之间"},
            )

        raw_needs = payload.get("generationNeeds", payload.get("generation_needs", ()))
        if isinstance(raw_needs, str):
            generation_needs = (raw_needs,) if raw_needs else ()
        elif isinstance(raw_needs, list):
            generation_needs = tuple(str(item) for item in raw_needs if str(item).strip())
        else:
            generation_needs = ()

        raw_attachments = payload.get("attachments", ())
        if isinstance(raw_attachments, str):
            attachments = tuple(
                item.strip() for item in raw_attachments.split(" / ") if item.strip()
            )
        elif isinstance(raw_attachments, list):
            attachments = tuple(str(item) for item in raw_attachments if str(item).strip())
        else:
            attachments = ()

        return cls(
            name=name,
            gender=gender,
            age=age,
            chief_complaint=chief_complaint,
            history_present_illness=history_present_illness,
            past_history=str(
                _value(payload, "pastHistory", "past_history", "未提供") or "未提供"
            ).strip(),
            physical_exam=str(
                _value(payload, "physicalExam", "physical_exam", "未提供") or "未提供"
            ).strip(),
            lab_results=str(
                payload.get(
                    "auxiliaryExam",
                    _value(payload, "labResults", "lab_results", "未提供"),
                )
                or "未提供"
            ).strip(),
            gender_code=raw_gender if raw_gender in {"male", "female"} else "",
            department=str(payload.get("department", "")).strip(),
            visit_date=str(payload.get("visitDate", payload.get("visit_date", ""))).strip(),
            allergy_history=str(
                payload.get("allergyHistory", payload.get("allergy_history", "未提供"))
                or "未提供"
            ).strip(),
            vital_signs=str(
                payload.get("vitalSigns", payload.get("vital_signs", "未提供"))
                or "未提供"
            ).strip(),
            preliminary_diagnosis=str(
                payload.get("preliminaryDiagnosis", payload.get("preliminary_diagnosis", ""))
            ).strip(),
            treatment_taken=str(
                payload.get("treatmentTaken", payload.get("treatment_taken", ""))
            ).strip(),
            medication_usage=str(
                payload.get("medicationUsage", payload.get("medication_usage", ""))
            ).strip(),
            generation_needs=generation_needs,
            attachments=attachments,
        )

    def model_text(self) -> str:
        return "。".join(
            (
                self.chief_complaint,
                self.history_present_illness,
                self.past_history,
                self.allergy_history,
                self.vital_signs,
                self.physical_exam,
                self.lab_results,
            )
        )


@dataclass(frozen=True)
class DiagnosisResult:
    top1: str
    candidates: list[str]
    reason: str
    scores: dict[str, float]


@dataclass(frozen=True)
class AnalysisResult:
    generated_record: str
    symptoms: list[str]
    medical_terms: list[str]
    diagnosis_top1: str
    diagnosis_candidates: list[str]
    diagnosis_reason: str
    treatment_advice: str
    confidence: float
    low_confidence: bool
    low_confidence_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "generatedRecord": self.generated_record,
            "symptoms": self.symptoms,
            "medicalTerms": self.medical_terms,
            "diagnosisTop1": self.diagnosis_top1,
            "diagnosisCandidates": self.diagnosis_candidates,
            "diagnosisReason": self.diagnosis_reason,
            "treatmentAdvice": self.treatment_advice,
            "content": self.diagnosis_reason,
            "modelVersion": MODEL_VERSION,
            "confidence": round(self.confidence, 6),
            "lowConfidence": self.low_confidence,
            "lowConfidenceReason": self.low_confidence_reason,
        }

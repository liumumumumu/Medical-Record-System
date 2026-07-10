import json
from datetime import datetime, timezone
from time import perf_counter

from src.config import MODEL_DIR, MODEL_NAME, MODEL_VERSION
from src.diagnosis_analyzer import DiagnosisAnalyzer
from src.medical_term_extractor import MedicalTermExtractor
from src.record_generator import RecordGenerator
from src.schema import AnalysisResult, PatientInput, ValidationError
from src.symptom_extractor import SymptomExtractor
from src.treatment_advisor import DISCLAIMER, TreatmentAdvisor
from src.text_utils import unique_preserve


class MedicalAIService:
    def __init__(self) -> None:
        self.symptom_extractor = SymptomExtractor()
        self.medical_term_extractor = MedicalTermExtractor()
        self.diagnosis_analyzer = DiagnosisAnalyzer()
        self.treatment_advisor = TreatmentAdvisor()
        self.record_generator = RecordGenerator()

    @property
    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "ai-service",
            "modelLoaded": self.diagnosis_analyzer.model_loaded,
            "knowledgeLoaded": self.diagnosis_analyzer.knowledge_loaded,
            "supportedDiagnoses": len(self.diagnosis_analyzer.labels),
            "modelName": MODEL_NAME,
            "modelVersion": MODEL_VERSION,
        }

    @property
    def metadata(self) -> dict[str, object]:
        metrics_path = MODEL_DIR / "metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
        return {
            "modelName": MODEL_NAME,
            "modelVersion": MODEL_VERSION,
            "supportedDiagnoses": self.diagnosis_analyzer.labels,
            "coreMetrics": metrics.get("test"),
            "limits": {
                "maxRequestBytes": 1_048_576,
                "maxCandidates": 3,
                "synchronousTimeoutSeconds": 10,
                "attachmentParsing": False,
            },
            "disclaimer": DISCLAIMER,
        }

    def _run(self, patient: PatientInput) -> tuple[AnalysisResult, object]:
        text = patient.model_text()
        symptom_result = self.symptom_extractor.extract(text)
        diagnosis = self.diagnosis_analyzer.analyze(
            text,
            symptom_result.positive,
            symptom_result.negated,
        )
        treatment = self.treatment_advisor.generate(diagnosis.top1, text)
        medical_terms = self.medical_term_extractor.extract(text)
        if diagnosis.top1 != "暂无法确定":
            medical_terms = unique_preserve([diagnosis.top1, *medical_terms])
        generated_record = self.record_generator.generate(
            patient,
            diagnosis.top1,
            treatment.advice,
        )
        result = AnalysisResult(
            generated_record=generated_record,
            symptoms=symptom_result.positive,
            medical_terms=medical_terms,
            diagnosis_top1=diagnosis.top1,
            diagnosis_candidates=diagnosis.candidates,
            diagnosis_reason=diagnosis.reason,
            treatment_advice=treatment.advice,
        )
        return result, diagnosis

    def analyze(self, payload: dict) -> AnalysisResult:
        patient = PatientInput.from_payload(payload)
        result, _diagnosis = self._run(patient)
        return result

    def analyze_frontend(self, payload: dict) -> dict[str, object]:
        started = perf_counter()
        if not isinstance(payload, dict):
            raise ValidationError("请求体必须是 JSON 对象")
        required_fields = (
            "patientName",
            "gender",
            "age",
            "chiefComplaint",
            "presentIllness",
            "pastHistory",
        )
        field_errors = {
            field: "该字段为必填项"
            for field in required_fields
            if field not in payload
            or payload[field] is None
            or (isinstance(payload[field], str) and not payload[field].strip())
        }
        text_limits = {
            "patientName": 30,
            "chiefComplaint": 200,
            "presentIllness": 1200,
            "pastHistory": 800,
        }
        for field, maximum in text_limits.items():
            value = payload.get(field)
            if isinstance(value, str) and len(value) > maximum:
                field_errors[field] = f"不能超过 {maximum} 个字符"
        if payload.get("gender") not in {None, "", "male", "female"}:
            field_errors["gender"] = "性别必须为 male 或 female"
        allowed_departments = {"", "internal", "surgery", "pediatrics", "emergency", "other"}
        if payload.get("department", "") not in allowed_departments:
            field_errors["department"] = "就诊科室枚举值无效"
        allowed_needs = {"record", "symptom", "diagnosis", "treatment", "full-report"}
        raw_needs = payload.get("generationNeeds", [])
        if not isinstance(raw_needs, list) or any(item not in allowed_needs for item in raw_needs):
            field_errors["generationNeeds"] = "生成需求枚举值无效"
        if field_errors:
            raise ValidationError(
                f"缺少必填字段: {', '.join(field_errors)}",
                field_errors,
            )
        patient = PatientInput.from_payload(payload)
        result, diagnosis = self._run(patient)
        generated_at = datetime.now(timezone.utc).isoformat()
        confidence = (
            diagnosis.scores.get(result.diagnosis_top1, 0.0)
            if result.diagnosis_top1 != "暂无法确定"
            else 0.0
        )
        low_confidence = result.diagnosis_top1 == "暂无法确定"
        gender_code = patient.gender_code or {"男": "male", "女": "female"}.get(
            patient.gender, patient.gender
        )
        attachments = [
            {
                "id": f"input_{index}",
                "fileName": file_name,
                "mimeType": "application/octet-stream",
                "url": "",
                "processingStatus": "metadata_only",
            }
            for index, file_name in enumerate(patient.attachments, start=1)
        ]
        return {
            "status": "completed",
            "generatedAt": generated_at,
            "processingTimeMs": round((perf_counter() - started) * 1000, 3),
            "model": {
                "name": MODEL_NAME,
                "version": MODEL_VERSION,
                "confidence": round(confidence, 6),
                "lowConfidence": low_confidence,
            },
            "summary": {
                "patientName": patient.name,
                "gender": gender_code,
                "age": patient.age,
                "department": patient.department,
                "visitDate": patient.visit_date,
                "chiefComplaint": patient.chief_complaint,
            },
            "structuredRecord": {
                "presentIllness": patient.history_present_illness,
                "pastHistory": patient.past_history,
                "allergyHistory": patient.allergy_history,
                "vitalSigns": patient.vital_signs,
                "physicalExam": patient.physical_exam,
                "auxiliaryExam": patient.lab_results,
                "generatedRecord": result.generated_record,
            },
            "analysis": {
                "preliminaryDiagnosis": patient.preliminary_diagnosis,
                "treatmentTaken": patient.treatment_taken,
                "medicationUsage": patient.medication_usage,
                "generationNeeds": list(patient.generation_needs),
                "symptoms": result.symptoms,
                "medicalTerms": result.medical_terms,
                "diagnosisTop1": result.diagnosis_top1,
                "diagnosisCandidates": result.diagnosis_candidates,
                "diagnosisReason": result.diagnosis_reason,
                "treatmentAdvice": result.treatment_advice,
                "content": result.diagnosis_reason,
                "lowConfidence": low_confidence,
                "lowConfidenceReason": (
                    "有效症状或融合得分不足" if low_confidence else None
                ),
                "disclaimer": DISCLAIMER,
            },
            "attachments": attachments,
            "failureReason": None,
        }

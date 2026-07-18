import json
from datetime import datetime, timezone
from time import perf_counter

from src.config import MODEL_DIR, MODEL_NAME
from src.diagnosis_analyzer import DiagnosisAnalyzer
from src.medical_term_extractor import MedicalTermExtractor
from src.record_generator import RecordGenerationResult, RecordGenerator
from src.schema import AnalysisResult, PatientInput, ValidationError
from src.symptom_extractor import SymptomExtractor
from src.treatment_advisor import DISCLAIMER, TreatmentAdvisor
from src.text_utils import unique_preserve


STANDARDIZED_TO_FRONTEND = {
    "patient_name": "patientName",
    "gender": "gender",
    "age": "age",
    "department": "department",
    "visit_date": "visitDate",
    "chief_complaint": "chiefComplaint",
    "present_illness": "presentIllness",
    "past_history": "pastHistory",
    "allergy_history": "allergyHistory",
    "vital_signs": "vitalSigns",
    "physical_exam": "physicalExam",
    "auxiliary_exam": "auxiliaryExam",
    "preliminary_diagnosis": "preliminaryDiagnosis",
    "treatment_taken": "treatmentTaken",
    "medication_usage": "medicationUsage",
    "generation_needs": "generationNeeds",
}


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
            "modelBackend": self.diagnosis_analyzer.model_backend,
            "knowledgeLoaded": self.diagnosis_analyzer.knowledge_loaded,
            "supportedDiagnoses": len(self.diagnosis_analyzer.labels),
            "modelName": MODEL_NAME,
            "modelVersion": self.diagnosis_analyzer.model_version,
            "recordGeneratorLoaded": self.record_generator.model_loaded,
            "recordGeneratorBackend": self.record_generator.backend,
            "recordGeneratorVersion": self.record_generator.model_version,
        }

    @property
    def metadata(self) -> dict[str, object]:
        if self.diagnosis_analyzer.model_backend == "transformer":
            metrics_path = MODEL_DIR / "transformer_production" / "metrics.json"
        else:
            metrics_path = MODEL_DIR / "metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
        return {
            "modelName": MODEL_NAME,
            "modelVersion": self.diagnosis_analyzer.model_version,
            "modelBackend": self.diagnosis_analyzer.model_backend,
            "recordGeneration": self.record_generator.metadata,
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

    def _run(
        self,
        patient: PatientInput,
    ) -> tuple[AnalysisResult, object, RecordGenerationResult]:
        generated_record = self.record_generator.generate(patient)
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
        formalized_input = {
            "chiefComplaint": generated_record.sections["主诉"],
            "presentIllness": generated_record.sections["现病史"],
            "pastHistory": generated_record.sections["既往史"],
            "allergyHistory": generated_record.record_fields["过敏史"],
            "vitalSigns": generated_record.record_fields["生命体征"],
            "physicalExam": generated_record.record_fields["体格检查"],
            "auxiliaryExam": generated_record.sections["辅助检查"],
            "preliminaryDiagnosis": generated_record.record_fields["初步诊断"],
            "treatmentTaken": generated_record.record_fields["既往治疗记录"],
            "medicationUsage": generated_record.record_fields["用药记录"],
        }
        result = AnalysisResult(
            generated_record=generated_record.text,
            symptoms=symptom_result.positive,
            medical_terms=medical_terms,
            diagnosis_top1=diagnosis.top1,
            diagnosis_candidates=diagnosis.candidates,
            diagnosis_reason=diagnosis.reason,
            treatment_advice=treatment.advice,
            confidence=(
                diagnosis.scores.get(diagnosis.top1, 0.0)
                if diagnosis.top1 != "暂无法确定"
                else 0.0
            ),
            low_confidence=diagnosis.top1 == "暂无法确定",
            low_confidence_reason=(
                "有效症状或融合得分不足" if diagnosis.top1 == "暂无法确定" else None
            ),
            formalized_input=formalized_input,
            model_version=self.diagnosis_analyzer.model_version,
            record_generation=generated_record.info,
        )
        return result, diagnosis, generated_record

    def analyze(self, payload: dict) -> AnalysisResult:
        patient = PatientInput.from_payload(payload)
        result, _diagnosis, _generated_record = self._run(patient)
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
        result, diagnosis, generated_record = self._run(patient)
        generated_at = datetime.now(timezone.utc).isoformat()
        confidence = result.confidence
        low_confidence = result.low_confidence
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
                "version": self.diagnosis_analyzer.model_version,
                "confidence": round(confidence, 6),
                "lowConfidence": low_confidence,
            },
            "recordGeneration": result.record_generation.to_dict(),
            "summary": {
                "patientName": patient.name,
                "gender": gender_code,
                "age": patient.age,
                "department": patient.department,
                "visitDate": patient.visit_date,
                "chiefComplaint": generated_record.sections["主诉"],
            },
            "structuredRecord": {
                "presentIllness": generated_record.sections["现病史"],
                "pastHistory": generated_record.sections["既往史"],
                "allergyHistory": generated_record.record_fields["过敏史"],
                "vitalSigns": generated_record.record_fields["生命体征"],
                "physicalExam": generated_record.record_fields["体格检查"],
                "auxiliaryExam": generated_record.sections["辅助检查"],
                "generatedRecord": result.generated_record,
            },
            "analysis": {
                "preliminaryDiagnosis": generated_record.record_fields["初步诊断"],
                "treatmentTaken": generated_record.record_fields["既往治疗记录"],
                "medicationUsage": generated_record.record_fields["用药记录"],
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
                    result.low_confidence_reason
                ),
                "disclaimer": DISCLAIMER,
            },
            "attachments": attachments,
            "failureReason": None,
        }

    def analyze_standardized(self, payload: dict) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise ValidationError("请求体必须是 JSON 对象")
        required_fields = (
            "patient_name",
            "gender",
            "age",
            "chief_complaint",
            "present_illness",
        )
        field_errors = {
            field: "该字段为必填项"
            for field in required_fields
            if field not in payload
            or payload[field] is None
            or (isinstance(payload[field], str) and not payload[field].strip())
        }
        text_limits = {
            "patient_name": 30,
            "chief_complaint": 200,
            "present_illness": 1200,
            "past_history": 800,
        }
        for field, maximum in text_limits.items():
            value = payload.get(field)
            if isinstance(value, str) and len(value) > maximum:
                field_errors[field] = f"不能超过 {maximum} 个字符"
        if payload.get("gender") not in {None, "", "male", "female"}:
            field_errors["gender"] = "性别必须为 male 或 female"
        raw_needs = payload.get("generation_needs", [])
        allowed_needs = {"record", "symptom", "diagnosis", "treatment", "full-report"}
        if not isinstance(raw_needs, list) or any(
            item not in allowed_needs for item in raw_needs
        ):
            field_errors["generation_needs"] = "生成需求枚举值无效"
        if field_errors:
            raise ValidationError(
                f"缺少或无效字段: {', '.join(field_errors)}",
                field_errors,
            )

        frontend_payload = {
            frontend_field: payload[standardized_field]
            for standardized_field, frontend_field in STANDARDIZED_TO_FRONTEND.items()
            if standardized_field in payload
        }
        standardized_attachments = payload.get("attachments", [])
        frontend_payload["attachments"] = [
            attachment.get("file_name", "")
            for attachment in standardized_attachments
            if isinstance(attachment, dict) and attachment.get("file_name")
        ]
        result = self.analyze_frontend(frontend_payload)
        result["attachments"] = self._standardized_attachment_results(
            standardized_attachments
        )
        return result

    def _standardized_attachment_results(self, attachments: object) -> list[dict[str, object]]:
        if not isinstance(attachments, list):
            return []
        results = []
        for index, attachment in enumerate(attachments, start=1):
            if not isinstance(attachment, dict):
                continue
            file_name = str(
                attachment.get("file_name")
                or attachment.get("fileName")
                or ""
            ).strip()
            if not file_name:
                continue
            results.append(
                {
                    "id": str(attachment.get("id") or f"file_{index:02d}"),
                    "fileName": file_name,
                    "mimeType": str(
                        attachment.get("mime_type")
                        or attachment.get("mimeType")
                        or "application/octet-stream"
                    ),
                    "url": str(attachment.get("url") or ""),
                    "processingStatus": str(
                        attachment.get("parse_status")
                        or attachment.get("processingStatus")
                        or "pending"
                    ),
                    "extractedText": str(attachment.get("extracted_text") or ""),
                    "failureReason": str(attachment.get("failure_reason") or ""),
                    "confidence": attachment.get("confidence"),
                }
            )
        return results

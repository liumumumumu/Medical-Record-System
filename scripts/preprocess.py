from __future__ import annotations

from datetime import datetime
from html import unescape
import json
from numbers import Integral
from pathlib import Path
import re
from typing import Any

from output_io import write_json


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "data" / "resources"
CLINICAL_CASE_DIR = ROOT / "data" / "clinical_cases"
PROCESSED_DIR = ROOT / "data" / "processed"
DEFAULT_INPUT_FILE = CLINICAL_CASE_DIR / "demo_cases.json"
DEFAULT_OUTPUT_FILE = PROCESSED_DIR / "clinical_cases_standardized.json"

API_FIELD_MAP = {
    "patientName": "patient_name",
    "gender": "gender",
    "age": "age",
    "department": "department",
    "visitDate": "visit_date",
    "chiefComplaint": "chief_complaint",
    "presentIllness": "present_illness",
    "pastHistory": "past_history",
    "allergyHistory": "allergy_history",
    "vitalSigns": "vital_signs",
    "physicalExam": "physical_exam",
    "auxiliaryExam": "auxiliary_exam",
    "preliminaryDiagnosis": "preliminary_diagnosis",
    "treatmentTaken": "treatment_taken",
    "medicationUsage": "medication_usage",
    "generationNeeds": "generation_needs",
    "attachments": "attachments",
}

REQUIRED_FIELDS = {
    "patientName": "姓名不能为空",
    "gender": "性别不能为空",
    "age": "年龄不能为空",
    "chiefComplaint": "主诉不能为空",
    "presentIllness": "现病史不能为空",
}

TEXT_LIMITS = {
    "patientName": 30,
    "chiefComplaint": 200,
    "presentIllness": 1200,
    "pastHistory": 800,
}

TEXT_FIELDS = [
    "chief_complaint",
    "present_illness",
    "past_history",
    "allergy_history",
    "vital_signs",
    "physical_exam",
    "auxiliary_exam",
    "preliminary_diagnosis",
    "treatment_taken",
    "medication_usage",
]

TEXT_DEFAULTS = {
    "past_history": "未提供",
    "allergy_history": "无",
    "vital_signs": "无",
    "physical_exam": "无",
    "auxiliary_exam": "无",
    "preliminary_diagnosis": "无",
    "treatment_taken": "无",
    "medication_usage": "无",
}

MODEL_TEXT_FIELDS = [
    "chief_complaint",
    "present_illness",
    "past_history",
    "allergy_history",
    "vital_signs",
    "physical_exam",
    "auxiliary_exam",
]

GENDER_VALUES = {"male", "female"}
DEPARTMENT_VALUES = {"internal", "surgery", "pediatrics", "emergency", "other"}
GENERATION_NEED_VALUES = {"record", "symptom", "diagnosis", "treatment", "full-report"}
DEFAULT_GENERATION_NEEDS = ["record", "symptom", "diagnosis"]
DEFAULT_SYNONYMS = {"发烧": "发热", "拉肚子": "腹泻"}
NEGATION_CUES = ["无明显", "无", "未见", "否认", "没有", "未", "不伴"]
POSITIVE_CUES = ["偶有", "有", "伴", "出现", "提示"]
CLAUSE_SPLIT_PATTERN = re.compile(r"(?:但是|不过|然而|但|[。；！？!?]|，(?=(?:无明显|无|未见|否认|没有|未|不伴|伴|出现|提示|偶有|有)))")


class CaseValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]):
        self.code = "VALIDATION_ERROR"
        self.field_errors = field_errors
        message = "病例输入字段校验失败"
        super().__init__(message)

    def to_error_response(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "fieldErrors": self.field_errors,
        }


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def load_resources(resource_dir: Path = RESOURCE_DIR) -> dict[str, Any]:
    synonyms_path = resource_dir / "synonyms.json"
    if synonyms_path.exists():
        synonyms = json.loads(synonyms_path.read_text(encoding="utf-8"))
    else:
        synonyms = DEFAULT_SYNONYMS.copy()

    return {
        "symptoms": read_lines(resource_dir / "symptom_dict.txt"),
        "medical_terms": read_lines(resource_dir / "medical_terms.txt"),
        "stopwords": set(read_lines(resource_dir / "stopwords.txt")),
        "synonyms": synonyms,
    }


def normalize_repeated_punctuation(text: str) -> str:
    text = re.sub(r"([。！？!?；;，,、])\1+", r"\1", text)
    text = re.sub(r"\.{2,}", ".", text)
    return text


def apply_synonyms(text: str, synonyms: dict[str, str] | None = None) -> str:
    normalized = text
    for source, target in sorted((synonyms or DEFAULT_SYNONYMS).items(), key=lambda item: len(item[0]), reverse=True):
        normalized = normalized.replace(source, target)
    return normalized


def clean_text(value: Any, synonyms: dict[str, str] | None = None) -> str:
    if value is None:
        return ""
    text = unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\u3000", " ")
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = apply_synonyms(text, synonyms)
    text = normalize_repeated_punctuation(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_age(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None

    if isinstance(value, Integral):
        return int(value)

    if isinstance(value, float):
        return None

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or not re.fullmatch(r"\d+", stripped):
            return None
        return int(stripped)

    return None


def validate_case(raw_case: dict[str, Any]) -> dict[str, str]:
    field_errors: dict[str, str] = {}

    for field, message in REQUIRED_FIELDS.items():
        if raw_case.get(field) is None or str(raw_case.get(field)).strip() == "":
            field_errors[field] = message

    for field, limit in TEXT_LIMITS.items():
        value = raw_case.get(field)
        if value is not None and len(str(value).strip()) > limit:
            field_errors[field] = f"长度不能超过 {limit} 字"

    age = parse_age(raw_case.get("age"))
    if age is None or age < 0 or age > 130:
        field_errors["age"] = "年龄必须是 0 至 130 之间的整数"

    gender = raw_case.get("gender")
    if gender is not None and gender not in GENDER_VALUES:
        field_errors["gender"] = "性别只能是 male 或 female"

    department = raw_case.get("department")
    if department not in (None, "") and department not in DEPARTMENT_VALUES:
        field_errors["department"] = "科室枚举值不在约定范围内"

    visit_date = raw_case.get("visitDate")
    if visit_date not in (None, ""):
        try:
            datetime.strptime(str(visit_date), "%Y-%m-%d")
        except ValueError:
            field_errors["visitDate"] = "就诊日期必须使用 YYYY-MM-DD 格式"

    generation_needs = raw_case.get("generationNeeds")
    if generation_needs not in (None, ""):
        if not isinstance(generation_needs, list):
            field_errors["generationNeeds"] = "生成需求必须是数组"
        else:
            invalid_needs = [need for need in generation_needs if need not in GENERATION_NEED_VALUES]
            if invalid_needs:
                field_errors["generationNeeds"] = "生成需求包含未约定的枚举值"

    return field_errors


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def split_clauses(text: str) -> list[str]:
    clauses = [clause.strip() for clause in CLAUSE_SPLIT_PATTERN.split(text) if clause.strip()]
    return clauses or [text]


def build_polarity_markers(clause: str) -> list[tuple[int, int, bool]]:
    ordered_cues = [(cue, False) for cue in NEGATION_CUES] + [(cue, True) for cue in POSITIVE_CUES]
    ordered_cues.sort(key=lambda item: len(item[0]), reverse=True)

    markers: list[tuple[int, int, bool]] = []
    index = 0
    while index < len(clause):
        matched = None
        for cue, polarity in ordered_cues:
            if clause.startswith(cue, index):
                matched = (cue, polarity)
                break
        if matched is None:
            index += 1
            continue

        cue, polarity = matched
        markers.append((index, index + len(cue), polarity))
        index += len(cue)

    return markers


def clause_has_positive_term(clause: str, term: str) -> bool:
    markers = build_polarity_markers(clause)

    for match in re.finditer(re.escape(term), clause):
        last_polarity = None
        for start, end, polarity in markers:
            if end <= match.start():
                last_polarity = polarity
                continue
            break

        if last_polarity is not False:
            return True

    return False


def find_terms(text: str, terms: list[str]) -> list[str]:
    matches: list[str] = []
    clauses = split_clauses(text)
    for term in terms:
        if term and any(clause_has_positive_term(clause, term) for clause in clauses):
            matches.append(term)
    return unique_in_order(matches)


def tokenize_text(cleaned_text: str, resources: dict[str, Any]) -> dict[str, list[str]]:
    symptoms = find_terms(cleaned_text, resources.get("symptoms", []))
    medical_terms = find_terms(cleaned_text, resources.get("medical_terms", []))
    tokens = unique_in_order(symptoms + medical_terms)
    stopwords = resources.get("stopwords", set())
    tokens = [token for token in tokens if token not in stopwords]
    return {"symptoms": symptoms, "medical_terms": medical_terms, "tokens": tokens}


def standardize_attachments(attachments: Any, synonyms: dict[str, str]) -> list[dict[str, Any]]:
    if not attachments:
        return []
    if isinstance(attachments, str):
        attachments = [
            file_name.strip()
            for file_name in re.split(r"\s+/\s+", attachments)
            if file_name.strip()
        ]
    elif not isinstance(attachments, list):
        return []

    standardized: list[dict[str, Any]] = []
    for index, attachment in enumerate(attachments, start=1):
        if isinstance(attachment, str):
            item = {"fileName": attachment}
        elif isinstance(attachment, dict):
            item = attachment
        else:
            continue

        parse_status = item.get("parseStatus") or item.get("parse_status") or "pending"
        if parse_status not in {"pending", "parsed", "failed"}:
            parse_status = "pending"

        standardized.append(
            {
                "id": item.get("id") or f"file_{index:02d}",
                "file_name": item.get("fileName") or item.get("file_name") or item.get("name") or "",
                "mime_type": item.get("mimeType") or item.get("mime_type") or "",
                "parse_status": parse_status,
                "extracted_text": clean_text(item.get("extractedText") or item.get("extracted_text") or "", synonyms),
                "failure_reason": item.get("failureReason") or item.get("failure_reason") or "",
                "confidence": item.get("confidence"),
            }
        )
    return standardized


def standardize_case(raw_case: dict[str, Any], resources: dict[str, Any] | None = None) -> dict[str, Any]:
    resources = resources or load_resources()
    synonyms = resources.get("synonyms", DEFAULT_SYNONYMS)
    field_errors = validate_case(raw_case)
    if field_errors:
        raise CaseValidationError(field_errors)

    standardized: dict[str, Any] = {}
    for frontend_field, standard_field in API_FIELD_MAP.items():
        value = raw_case.get(frontend_field)
        if standard_field == "age":
            standardized[standard_field] = parse_age(value)
        elif standard_field == "department":
            standardized[standard_field] = value or "other"
        elif standard_field == "generation_needs":
            standardized[standard_field] = value or DEFAULT_GENERATION_NEEDS.copy()
        elif standard_field == "attachments":
            standardized[standard_field] = standardize_attachments(value, synonyms)
        elif standard_field in TEXT_FIELDS or standard_field == "patient_name":
            cleaned = clean_text(value, synonyms)
            if standard_field in TEXT_DEFAULTS and cleaned == "":
                cleaned = TEXT_DEFAULTS[standard_field]
            standardized[standard_field] = cleaned
        else:
            standardized[standard_field] = value or ""

    attachment_text = " ".join(
        attachment["extracted_text"]
        for attachment in standardized["attachments"]
        if attachment.get("parse_status") == "parsed" and attachment.get("extracted_text")
    )
    clean_text_parts = [
        standardized[field] for field in MODEL_TEXT_FIELDS if standardized.get(field)
    ]
    if attachment_text:
        clean_text_parts.append(attachment_text)
    standardized["clean_text"] = clean_text(" ".join(clean_text_parts), synonyms)

    token_result = tokenize_text(standardized["clean_text"], resources)
    standardized["symptoms"] = token_result["symptoms"]
    standardized["medical_terms"] = token_result["medical_terms"]
    standardized["tokens"] = token_result["tokens"]
    standardized["source_schema"] = "frontend_case_v0.2"
    return standardized


def load_case_list(input_file: Path = DEFAULT_INPUT_FILE) -> list[dict[str, Any]]:
    payload = json.loads(input_file.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Input JSON must be a list of case objects.")
    return payload


def preprocess_cases(
    input_file: Path = DEFAULT_INPUT_FILE,
    output_file: Path = DEFAULT_OUTPUT_FILE,
    resource_dir: Path = RESOURCE_DIR,
) -> list[dict[str, Any]]:
    resources = load_resources(resource_dir)
    raw_cases = load_case_list(input_file)
    standardized_cases = [standardize_case(case, resources=resources) for case in raw_cases]

    write_json(standardized_cases, output_file, ensure_ascii=False, indent=2)
    return standardized_cases


def main() -> None:
    standardized_cases = preprocess_cases()
    print(f"standardized clinical cases: {len(standardized_cases)}")
    print(DEFAULT_OUTPUT_FILE)


if __name__ == "__main__":
    main()

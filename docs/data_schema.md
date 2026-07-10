# Clinical Case Data Schema

This document is the data-processing schema for frontend, backend, and AI
handoff. It follows the current frontend contract in
`前后端与 AI 交接规范.md` and converts lowerCamelCase request fields into
snake_case fields for Python NLP/AI modules.

## 1. Scope

The existing NHANES pipeline remains the numeric health-indicator workflow.
This schema covers user-submitted clinical case text:

- frontend form input
- backend validation reference
- data cleaning and standardization
- AI/NLP service input
- demo, train, and test sample data

All demo data is fictional and desensitized.

## 2. Frontend Input Fields

| Frontend key | Standard field | Required | Rule |
| --- | --- | --- | --- |
| `patientName` | `patient_name` | yes | string, max 30 chars |
| `gender` | `gender` | yes | `male` or `female` |
| `age` | `age` | yes | integer, 0-130 |
| `department` | `department` | no | `internal`, `surgery`, `pediatrics`, `emergency`, `other`; default `other` |
| `visitDate` | `visit_date` | no | `YYYY-MM-DD` |
| `chiefComplaint` | `chief_complaint` | yes | string, max 200 chars |
| `presentIllness` | `present_illness` | yes | string, max 1200 chars |
| `pastHistory` | `past_history` | yes | string, max 800 chars; use `无` when empty in UI |
| `allergyHistory` | `allergy_history` | no | default `无` |
| `vitalSigns` | `vital_signs` | no | default `无` |
| `physicalExam` | `physical_exam` | no | default `无` |
| `auxiliaryExam` | `auxiliary_exam` | no | default `无` |
| `attachments` | `attachments` | no | list of parsed or failed file objects |
| `preliminaryDiagnosis` | `preliminary_diagnosis` | no | default `无` |
| `treatmentTaken` | `treatment_taken` | no | default `无` |
| `medicationUsage` | `medication_usage` | no | default `无` |
| `generationNeeds` | `generation_needs` | no | list of `record`, `symptom`, `diagnosis`, `treatment`, `full-report`; default `record/symptom/diagnosis` |

## 3. Validation Rules

`scripts/preprocess.py` raises `CaseValidationError` with frontend field names in
`fieldErrors`, so backend can directly map validation errors back to the React
form.

Example:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "病例输入字段校验失败",
  "fieldErrors": {
    "age": "年龄必须是 0 至 130 之间的整数",
    "chiefComplaint": "主诉不能为空"
  }
}
```

## 4. Cleaning Rules

The preprocessing script applies these rules:

- remove HTML tags and escaped HTML entities
- normalize tabs, newlines, full-width spaces, and repeated whitespace
- collapse repeated punctuation such as `!!!` into `!`
- replace common synonyms, for example `发烧 -> 发热`, `拉肚子 -> 腹泻`
- default optional text fields to `无`
- combine complaint, history, signs, exam, and parsed attachment text into `clean_text`
- keep preliminary diagnosis, treatment, and medication as display-only fields; never include them in model features, which avoids label leakage
- extract dictionary-based `symptoms`, `medical_terms`, and `tokens`

## 5. Attachment Parse Schema

Input may use frontend-style field names:

```json
{
  "fileName": "blood-test.pdf",
  "mimeType": "application/pdf",
  "parseStatus": "parsed",
  "extractedText": "白细胞轻度升高"
}
```

Standardized output:

```json
{
  "id": "file_01",
  "file_name": "blood-test.pdf",
  "mime_type": "application/pdf",
  "parse_status": "parsed",
  "extracted_text": "白细胞轻度升高",
  "failure_reason": "",
  "confidence": null
}
```

When parsing fails, `parse_status` is `failed`, `extracted_text` is empty, and
`failure_reason` explains the reason.

## 6. Standardized AI Input Example

```json
{
  "patient_name": "张某",
  "gender": "male",
  "age": 32,
  "department": "internal",
  "visit_date": "2026-07-10",
  "chief_complaint": "发热、咳嗽 3 天",
  "present_illness": "3天前受凉后出现发热、咳嗽、乏力。",
  "past_history": "无高血压、糖尿病史。",
  "allergy_history": "无",
  "vital_signs": "体温 38.5℃，脉搏 88 次/分。",
  "physical_exam": "咽部充血。",
  "auxiliary_exam": "血常规提示白细胞轻度升高。",
  "preliminary_diagnosis": "上呼吸道感染",
  "treatment_taken": "已给予退热处理。",
  "medication_usage": "口服对乙酰氨基酚。",
  "generation_needs": ["record", "symptom", "diagnosis"],
  "clean_text": "发热、咳嗽 3 天 3天前受凉后出现发热、咳嗽、乏力。 体温 38.5℃ ...",
  "symptoms": ["发热", "咳嗽", "乏力", "咽部充血"],
  "medical_terms": ["血常规", "白细胞"],
  "tokens": ["发热", "咳嗽", "乏力", "咽部充血", "血常规", "白细胞"],
  "source_schema": "frontend_case_v0.2"
}
```

## 7. Data Files

| File | Purpose |
| --- | --- |
| `data/resources/symptom_dict.txt` | symptom dictionary |
| `data/resources/medical_terms.txt` | medical term dictionary |
| `data/resources/stopwords.txt` | Chinese stopword list |
| `data/resources/synonyms.json` | synonym normalization map |
| `data/clinical_cases/demo_cases.json` | 3 end-to-end frontend-style demo cases |
| `data/clinical_cases/demo_data.csv` | 10 desensitized demo rows |
| `data/clinical_cases/train.csv` | training sample rows with diagnosis labels |
| `data/clinical_cases/test.csv` | testing sample rows with diagnosis labels |

## 8. Commands

```bash
python scripts/preprocess.py
python scripts/feature_builder.py
python -m unittest tests.test_preprocess tests.test_feature_builder
```

Generated files:

- `data/processed/clinical_cases_standardized.json`
- `data/processed/train_keyword_features.csv`
- `data/processed/test_keyword_features.csv`
- `data/processed/demo_data_keyword_features.csv`

## 9. Handoff Notes

- Frontend and backend should keep request fields in lowerCamelCase.
- Python data and AI modules should use snake_case fields from this schema.
- If the frontend field contract changes, update this file, tests, and
  `scripts/preprocess.py` together.
- Diagnosis labels in sample data are for course demo and model/rule testing
  only. They do not replace clinician judgment.

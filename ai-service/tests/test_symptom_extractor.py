from src.symptom_extractor import SymptomExtractor


def test_extracts_synonyms_and_numeric_signs():
    result = SymptomExtractor().extract(
        "患者高烧，拉肚子并喘不上气，体温39.6℃，血压165/105mmHg，血糖9.2"
    )
    assert {"高热", "腹泻", "呼吸困难", "发热", "血压升高", "血糖升高"} <= set(
        result.positive
    )


def test_excludes_negated_symptoms():
    result = SymptomExtractor().extract("否认发热、咳嗽，无腹痛腹泻，存在鼻塞和流鼻涕")
    assert "发热" not in result.positive
    assert "咳嗽" not in result.positive
    assert "腹泻" not in result.positive
    assert {"发热", "咳嗽", "腹泻"} <= set(result.negated)
    assert {"鼻塞", "鼻流涕"} <= set(result.positive)


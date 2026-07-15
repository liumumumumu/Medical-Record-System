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


def test_negation_scope_continues_across_commas_until_positive_transition():
    result = SymptomExtractor().extract("否认发热，咳嗽，乏力，但有鼻塞")
    assert {"发热", "咳嗽", "乏力"} <= set(result.negated)
    assert not {"发热", "咳嗽", "乏力"} & set(result.positive)
    assert "鼻塞" in result.positive

    assert "发热" in SymptomExtractor().extract("否认有发热").negated


def test_no_obvious_trigger_idiom_does_not_negate_following_symptoms():
    result = SymptomExtractor().extract("一天前无明显诱因出现腹痛、腹泻、呕吐，水样便五次")
    assert {"腹痛", "腹泻", "呕吐"} <= set(result.positive)
    assert not {"腹痛", "腹泻", "呕吐"} & set(result.negated)

    result = SymptomExtractor().extract("患者无诱因出现头痛，伴畏光")
    assert "头痛" in result.positive


def test_temperature_recognized_with_du_and_degree_c_units():
    assert "发热" in SymptomExtractor().extract("体温最高38.9度，精神稍差").positive
    assert "发热" in SymptomExtractor().extract("查体温38.5°C").positive
    assert {"发热", "高热"} <= set(SymptomExtractor().extract("体温39.2度").positive)


def test_blood_pressure_requires_bp_context():
    assert "血压升高" not in SymptomExtractor().extract("身高体重 175/80").positive
    assert "血压升高" in SymptomExtractor().extract("血压150/95").positive
    assert "血压升高" in SymptomExtractor().extract("测得165/100mmHg").positive

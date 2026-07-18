import pytest

from src.record_generation_metrics import evaluate_generation
from src.record_generator import (
    RecordGenerator,
    RecordGuard,
    build_model_input,
    extract_numeric_facts,
    normalize_clinical_sections,
    normalize_record_fields,
    parse_generated_sections,
    sanitize_generated_text,
)
from src.schema import PatientInput


def patient(**overrides) -> PatientInput:
    values = {
        "name": "张某",
        "gender": "男",
        "age": 32,
        "chief_complaint": "发热咳嗽3天",
        "history_present_illness": "受凉后发热咳嗽3天，体温38.5℃",
        "past_history": "未提供",
        "physical_exam": "咽部充血",
        "lab_results": "未提供",
        "preliminary_diagnosis": "上呼吸道感染",
        "treatment_taken": "已接受物理降温",
        "medication_usage": "未提供",
    }
    values.update(overrides)
    return PatientInput(**values)


def test_parser_and_guard_accept_fact_preserving_output():
    generated = (
        "<主诉>发热咳嗽3天"
        "<现病史>受凉后发热咳嗽3天，体温38.5℃"
        "<既往史>未提供"
        "<辅助检查>未提供"
    )
    sections = parse_generated_sections(generated)
    assert list(sections) == ["主诉", "现病史", "既往史", "辅助检查"]
    assert RecordGuard().validate(patient(), sections) == []


def test_model_input_contains_prior_treatment_context():
    source = build_model_input(
        patient(
            preliminary_diagnosis="医生已记录诊断",
            treatment_taken="患者已经接受雾化治疗",
            medication_usage="既往使用药物甲",
        )
    )
    assert "[医生初步诊断]医生已记录诊断" in source
    assert "[已接受治疗]患者已经接受雾化治疗" in source
    assert "[用药记录]既往使用药物甲" in source


def test_model_input_explicitly_requires_oral_to_clinical_rewriting():
    source = build_model_input(patient())
    assert "患者口语、自述或医患对话" in source
    assert "第三人称临床书面语" in source
    assert "不得整段照抄口语" in source


def test_chinese_numbers_are_comparable_with_clinical_arabic_numbers():
    source = "肚子疼还拉肚子两天，今天拉了四五次，前天开始"
    generated = "腹痛伴腹泻2天，排稀便4-5次，2天前起病"
    assert extract_numeric_facts(generated).issubset(extract_numeric_facts(source))


def test_clinical_style_normalizer_rewrites_common_oral_phrases():
    source_patient = patient(
        age=24,
        chief_complaint="肚子疼还拉肚子两天",
        history_present_illness=(
            "前天晚上吃了烧烤，第二天开始肚子一阵一阵疼，"
            "拉了四五次，都是稀的，有点恶心，但是没吐，也没发烧。"
            "自己喝了点热水，感觉没什么用。"
        ),
        past_history="平时身体正常",
    )
    sections, warnings = normalize_clinical_sections(
        source_patient,
        {
            "主诉": source_patient.chief_complaint,
            "现病史": source_patient.history_present_illness,
            "既往史": source_patient.past_history,
            "辅助检查": "未提供",
        },
    )
    assert sections["主诉"] == "腹痛伴腹泻2天"
    assert "2天前晚间" in sections["现病史"]
    assert sections["现病史"].startswith("患者于2天前晚间进食烧烤后")
    assert "阵发性腹痛" in sections["现病史"]
    assert "排稀便4-5次" in sections["现病史"]
    assert "无呕吐" in sections["现病史"]
    assert "无发热" in sections["现病史"]
    assert "效果欠佳" in sections["现病史"]
    assert sections["既往史"] == "既往体健"
    assert warnings


def test_all_record_fields_are_normalized_from_oral_to_clinical_writing():
    oral = patient(
        allergy_history="没发现有什么药过敏",
        vital_signs="体温36.8度，心率78次每分钟，血压120/80",
        physical_exam="肚脐周围按着有点疼，无反跳痛",
        preliminary_diagnosis="医生考虑急性胃肠炎",
        treatment_taken="门诊补液一次，之后腹泻次数减少",
        medication_usage="吃过蒙脱石散",
    )
    fields = normalize_record_fields(oral)
    assert fields == {
        "过敏史": "否认药物过敏史",
        "生命体征": "T 36.8℃，P 78次/分，BP 120/80mmHg",
        "体格检查": "脐周轻压痛，无反跳痛",
        "初步诊断": "考虑急性胃肠炎",
        "既往治疗记录": "曾于门诊接受补液治疗1次，治疗后腹泻次数减少",
        "用药记录": "曾服用蒙脱石散",
    }


def test_guard_accepts_medical_synonyms_and_chinese_number_normalization():
    oral = patient(
        chief_complaint="肚子疼还拉肚子两天",
        history_present_illness="前天开始肚子疼，拉了四五次稀便",
    )
    sections = {
        "主诉": "腹痛伴腹泻2天",
        "现病史": "患者2天前出现腹痛、腹泻，排稀便4-5次。",
        "既往史": "未提供",
        "辅助检查": "未提供",
    }
    assert RecordGuard().validate(oral, sections) == []


def test_transformer_omitted_provided_past_history_is_restored(monkeypatch):
    class OmittingTransformer:
        def generate_sections(self, _patient):
            return {
                "主诉": "腹痛伴腹泻2天",
                "现病史": "患者2天前出现腹痛、腹泻。",
                "既往史": "未提供",
                "辅助检查": "未提供",
            }

    monkeypatch.setenv("RECORD_GENERATOR_BACKEND", "template")
    generator = RecordGenerator()
    generator.requested_backend = "transformer"
    generator.transformer = OmittingTransformer()
    result = generator.generate(
        patient(
            chief_complaint="肚子疼还拉肚子两天",
            history_present_illness="前天开始肚子疼、拉肚子",
            past_history="平时身体正常",
        )
    )
    assert result.info.backend == "transformer"
    assert "四、既往史\n既往体健" in result.text
    assert "既往史已按原始输入" in "；".join(result.info.warnings)


def test_sentencepiece_byte_token_temperature_is_normalized():
    generated = (
        "<主诉>发热<现病史>体温37.7<0x7E>C"
        "<既往史>未提供<辅助检查>未提供<extra_id_0>"
    )
    cleaned = sanitize_generated_text(generated)
    sections = parse_generated_sections(cleaned)
    assert sections["现病史"] == "体温37.7℃"
    assert "<0x" not in cleaned
    assert "<extra_id" not in cleaned
    assert RecordGuard().validate(
        patient(
            chief_complaint="发热",
            history_present_illness="发热，体温37.7℃",
        ),
        sections,
    ) == []


def test_model_missing_synonyms_are_normalized_to_required_value():
    sections = parse_generated_sections(
        "<主诉>咳嗽<现病史>咳嗽3天<既往史>无。<辅助检查>暂无"
    )
    assert sections["既往史"] == "未提供"
    assert sections["辅助检查"] == "未提供"


def test_unresolved_unknown_token_is_rejected():
    sections = parse_generated_sections(
        "<主诉>发热<现病史>发热<unk>伴咳嗽<既往史>未提供<辅助检查>未提供"
    )
    warnings = RecordGuard().validate(patient(), sections)
    assert any("无法可靠解码" in warning for warning in warnings)


def test_guard_rejects_added_number_and_missing_field_hallucination():
    sections = parse_generated_sections(
        "<主诉>发热咳嗽7天<现病史>受凉后发热咳嗽，体温39.9℃"
        "<既往史>高血压10年<辅助检查>白细胞20"
    )
    warnings = RecordGuard().validate(patient(), sections)
    assert any("不存在的数值" in warning for warning in warnings)
    assert any("既往史原始输入缺失" in warning for warning in warnings)
    assert any("辅助检查原始输入缺失" in warning for warning in warnings)


def test_guard_rejects_new_disease_or_drug_term_without_new_number():
    sections = parse_generated_sections(
        "<主诉>发热咳嗽<现病史>发热咳嗽，考虑肺炎并使用阿莫西林"
        "<既往史>未提供<辅助检查>未提供"
    )
    warnings = RecordGuard().validate(patient(), sections)
    assert any("不存在的疾病或药物术语" in warning for warning in warnings)


def test_template_record_preserves_official_diagnosis_treatment_and_medication(monkeypatch):
    monkeypatch.setenv("RECORD_GENERATOR_BACKEND", "template")
    result = RecordGenerator().generate(patient())
    assert result.info.backend == "template"
    assert result.info.fallback_used is False
    assert "初步诊断（医生输入）\n上呼吸道感染" in result.text
    assert "既往治疗记录（患者已接受）\n已接受物理降温" in result.text
    assert "用药记录（患者已使用）\n未提供" in result.text


def test_fact_guard_failure_switches_to_safe_template(monkeypatch):
    class HallucinatingTransformer:
        def generate_sections(self, _patient):
            return {
                "主诉": "发热99天",
                "现病史": "新增不存在的病史",
                "既往史": "高血压20年",
                "辅助检查": "白细胞99",
            }

    monkeypatch.setenv("RECORD_GENERATOR_BACKEND", "template")
    generator = RecordGenerator()
    generator.requested_backend = "transformer"
    generator.transformer = HallucinatingTransformer()
    result = generator.generate(patient())
    assert result.info.backend == "template"
    assert result.info.fallback_used is True
    assert result.info.warnings
    assert "发热99天" not in result.text
    assert "已接受物理降温" in result.text


def test_missing_source_field_is_constrained_without_full_fallback(monkeypatch):
    class MissingFieldHallucinatingTransformer:
        def generate_sections(self, _patient):
            return {
                "主诉": "发热咳嗽3天",
                "现病史": "受凉后发热咳嗽3天，体温38.5℃",
                "既往史": "未提供",
                "辅助检查": "凭空补写的检查结果",
            }

    monkeypatch.setenv("RECORD_GENERATOR_BACKEND", "template")
    generator = RecordGenerator()
    generator.requested_backend = "transformer"
    generator.transformer = MissingFieldHallucinatingTransformer()
    result = generator.generate(patient())
    assert result.info.backend == "transformer"
    assert result.info.fallback_used is False
    assert "辅助检查原始输入缺失" in "；".join(result.info.warnings)
    assert "七、辅助检查\n未提供" in result.text
    assert "凭空补写" not in result.text


def test_attachment_context_is_preserved_as_authoritative_input(monkeypatch):
    class SummarizingTransformer:
        def generate_sections(self, _patient):
            return {
                "主诉": "发热咳嗽3天",
                "现病史": "受凉后发热咳嗽3天，体温38.5℃",
                "既往史": "未提供",
                "辅助检查": "待结合附件",
            }

    with_attachment = patient(
        lab_results=(
            "待结合附件\n附件提取内容：\n"
            "化验单.docx：\n附件检查提示白细胞轻度升高，C反应蛋白升高。"
        )
    )
    monkeypatch.setenv("RECORD_GENERATOR_BACKEND", "template")
    generator = RecordGenerator()
    generator.requested_backend = "transformer"
    generator.transformer = SummarizingTransformer()
    result = generator.generate(with_attachment)
    assert result.info.backend == "transformer"
    assert result.info.fallback_used is False
    assert "白细胞轻度升高" in result.text
    assert "事实约束原样补入" in "；".join(result.info.warnings)


def test_missing_generated_section_uses_constrained_transformer_retry(monkeypatch):
    class RepairingTransformer:
        retried_section = None

        def generate_sections(self, _patient):
            return {
                "主诉": "发热咳嗽3天",
                "既往史": "未提供",
                "辅助检查": "未提供",
            }

        def regenerate_from_section(self, _patient, section_name):
            self.retried_section = section_name
            return {
                "主诉": "发热咳嗽3天",
                "现病史": "受凉后发热咳嗽3天，体温38.5℃",
                "既往史": "未提供",
                "辅助检查": "未提供",
            }

    transformer = RepairingTransformer()
    monkeypatch.setenv("RECORD_GENERATOR_BACKEND", "template")
    generator = RecordGenerator()
    generator.requested_backend = "transformer"
    generator.transformer = transformer
    result = generator.generate(patient())
    assert transformer.retried_section == "现病史"
    assert result.info.backend == "transformer"
    assert result.info.fallback_used is False
    assert "受约束二次生成" in "；".join(result.info.warnings)
    assert "三、现病史\n受凉后发热、咳嗽3天，体温38.5℃" in result.text


def test_required_mode_rejects_template_backend(monkeypatch):
    monkeypatch.setenv("RECORD_GENERATOR_BACKEND", "template")
    monkeypatch.setenv("REQUIRE_RECORD_GENERATOR", "true")
    with pytest.raises(RuntimeError, match="模型未就绪"):
        RecordGenerator()


def test_generation_metrics_cover_structure_and_numbers():
    target = "<主诉>发热3天<现病史>发热3天<既往史>未提供<辅助检查>未提供"
    metrics = evaluate_generation([target], [[target]], ["患者发热3天"])
    assert metrics["rougeL"] == 1.0
    assert metrics["parseRate"] == 1.0
    assert metrics["sectionCompleteness"] == 1.0
    assert metrics["numericConsistency"] == 1.0
    assert metrics["criticalTermConsistency"] == 1.0

    unsafe = evaluate_generation(
        ["<主诉>发热3天<现病史>发热3天，诊断肺炎<既往史>未提供<辅助检查>未提供"],
        [[target]],
        ["患者发热3天"],
    )
    assert unsafe["criticalTermConsistency"] == 0.0

    standardized = evaluate_generation(
        ["<主诉>腹泻3天<现病史>腹泻3天<既往史>未提供<辅助检查>未提供"],
        [[target]],
        ["患者拉肚子3天"],
    )
    assert standardized["criticalTermConsistency"] == 1.0

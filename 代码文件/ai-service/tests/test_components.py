from src.medical_term_extractor import MedicalTermExtractor
from src.record_generator import RecordGenerator
from src.schema import PatientInput
from src.treatment_advisor import DISCLAIMER, TreatmentAdvisor


def test_medical_term_extraction_ignores_negated_disease():
    terms = MedicalTermExtractor().extract("血常规提示白细胞升高，否认糖尿病史")
    assert "血常规" in terms
    assert "白细胞" in terms
    assert "糖尿病" not in terms


def test_record_contains_all_sections():
    patient = PatientInput(
        name="张三",
        gender="男",
        age=30,
        chief_complaint="发热咳嗽3天",
        history_present_illness="受凉后发热咳嗽",
        past_history="无特殊",
        physical_exam="体温38.5℃",
        lab_results="白细胞升高",
    )
    record = RecordGenerator().generate(patient, "上呼吸道感染", "建议就医")
    for section in ("基本信息", "主诉", "现病史", "既往史", "体格检查", "辅助检查", "初步诊断", "处理建议"):
        assert section in record


def test_red_flag_overrides_normal_advice():
    result = TreatmentAdvisor().generate("普通感冒", "患者持续胸痛且胸痛不缓解")
    assert "立即前往急诊" in result.advice
    assert "持续胸痛" in result.red_flags
    assert DISCLAIMER not in result.advice

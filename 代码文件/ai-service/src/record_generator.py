from __future__ import annotations

from dataclasses import dataclass
import os
import re
from threading import Lock
from typing import Any

from src.config import RECORD_MODEL_DIR, RECORD_MODEL_NAME, RECORD_MODEL_VERSION
from src.medical_term_extractor import MedicalTermExtractor
from src.schema import PatientInput, RecordGenerationInfo
from src.text_utils import normalize_text


SECTION_NAMES = ("主诉", "现病史", "既往史", "辅助检查")
SECTION_TAG_PATTERN = re.compile(
    r"<(主诉|现病史|既往史|辅助检查)>\s*(.*?)(?=<(?:主诉|现病史|既往史|辅助检查)>|$)",
    re.DOTALL,
)
NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")
CONTROL_TAG_PATTERN = re.compile(r"</?(?:主诉|现病史|既往史|辅助检查)>")
BYTE_TOKEN_GROUP_PATTERN = re.compile(r"(?:<0x[0-9A-Fa-f]{2}>)+")
BYTE_TOKEN_PATTERN = re.compile(r"<0x([0-9A-Fa-f]{2})>")
WHITESPACE_PATTERN = re.compile(r"[\t\r ]+")
SENTENCE_SPACE_PATTERN = re.compile(r"\n{3,}")
MISSING_SECTION_VALUES = frozenset(
    {
        "无",
        "暂无",
        "不详",
        "未提供",
        "未查",
        "未检查",
        "未行检查",
        "无相关检查",
        "无辅助检查",
    }
)
ATTACHMENT_CONTEXT_MARKER = "附件提取内容："
CRITICAL_TERM_SUPPORT_ALIASES: dict[str, frozenset[str]] = {
    "腹泻": frozenset({"拉肚子", "拉稀", "稀便", "大便稀", "水样便", "蛋花样便"}),
    "便秘": frozenset(
        {"排便困难", "排不出大便", "大便干结", "大便干燥", "大便很干", "几天没大便"}
    ),
    "退热药": frozenset({"退烧药"}),
}

CLINICAL_TERM_ALIASES: dict[str, tuple[str, ...]] = {
    "腹泻": ("拉肚子", "拉稀", "稀便", "大便稀", "水样便", "蛋花样便"),
    "便秘": ("排不出大便", "排便困难", "大便干结", "大便干燥", "大便很干"),
    "腹痛": ("肚子一阵一阵疼", "肚子疼", "肚子痛", "肚痛"),
    "腹胀": ("肚子胀",),
    "发热": ("发烧",),
    "头痛": ("头疼",),
    "咳痰": ("有痰", "吐痰"),
    "呼吸困难": ("喘不上气", "呼吸不上来", "气短"),
    "心悸": ("心慌",),
    "乏力": ("没劲", "没有力气", "没力气"),
    "恶心": ("反胃", "想吐"),
}
CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
CHINESE_NUMBER_WITH_UNIT_PATTERN = re.compile(
    r"([零〇一二两三四五六七八九十百]+)(?=余|多|来|个|次|天|日|周|星期|月|年|岁|小时|分钟|"
    r"度|℃|支|片|粒|袋|毫升|升|厘米|毫米|公斤|斤)"
)
ORAL_FILLER_PATTERN = re.compile(
    r"(?:大夫|医生)(?:您好|你好)[：:，,、 ]*|(?:我想问|请问)[：:，,、 ]*|谢谢(?:大夫|医生)?[了。！!]*"
)
ORAL_QUESTION_SENTENCE_PATTERN = re.compile(
    r"(?:那|请问|想问|我想知道)?(?:这个|这种)?(?:情况)?(?:我)?(?:该|需要)?"
    r"(?:怎么办|怎么治疗|能不能治)[？?]?"
)
CLINICAL_STYLE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("肚子一阵一阵疼", "阵发性腹痛"),
    ("肚子一阵疼", "阵发性腹痛"),
    ("一阵一阵肚子疼", "阵发性腹痛"),
    ("排不出大便", "排便困难"),
    ("大便很干", "大便干结"),
    ("拉肚子", "腹泻"),
    ("拉稀", "腹泻"),
    ("肚子疼", "腹痛"),
    ("肚子痛", "腹痛"),
    ("肚子胀", "腹胀"),
    ("发烧", "发热"),
    ("高烧", "高热"),
    ("头疼", "头痛"),
    ("没吐", "无呕吐"),
    ("没有吐", "无呕吐"),
    ("没发热", "无发热"),
    ("没有发热", "无发热"),
    ("没发烧", "无发热"),
    ("没有发烧", "无发热"),
    ("没有胸痛", "无胸痛"),
    ("没有腰痛", "无腰痛"),
    ("有点恶心", "伴恶心"),
    ("自己喝了点热水", "自行饮用热水"),
    ("自己喝了热水", "自行饮用热水"),
    ("没什么用", "效果欠佳"),
    ("没有什么用", "效果欠佳"),
    ("没效果", "效果欠佳"),
    ("都是稀的", "均为稀便"),
    ("平时身体正常", "既往体健"),
    ("平时身体挺好的", "既往体健"),
    ("小便的时候疼", "尿痛"),
    ("尿尿疼", "尿痛"),
    ("一会儿就想去厕所", "尿频"),
    ("老想上厕所", "尿频"),
    ("每次尿得不多", "每次尿量少"),
    ("脑袋发胀", "头部胀痛"),
    ("站起来有点晕", "站立时头晕"),
    ("胸口疼", "胸痛"),
    ("腰疼", "腰痛"),
    ("也没有胸痛", "无胸痛"),
    ("没有胸痛", "无胸痛"),
    ("也没有腰痛", "无腰痛"),
    ("没有腰痛", "无腰痛"),
    ("晚上咳得睡不好", "夜间咳嗽加重，影响睡眠"),
    ("晚上特别厉害", "夜间加重"),
    ("吐黄色的痰", "咳黄痰"),
    ("黄色的痰", "黄痰"),
    ("还有黄痰", "伴咳黄痰"),
    ("咳嗽还有痰", "咳嗽伴咳痰"),
    ("自己喝了止咳糖浆", "自行服用止咳糖浆"),
    ("吃了退烧药以后能降下来", "服用退热药后体温可下降"),
    ("过几个小时又烧", "数小时后体温再次升高"),
    ("没怎么好转", "症状无明显缓解"),
    ("以前得过", "既往有"),
    ("腹痛还腹泻", "腹痛伴腹泻"),
    ("肚脐周围", "脐周"),
    ("按着有点疼", "轻压痛"),
    ("按着疼", "压痛"),
    ("退烧药", "退热药"),
)
ORAL_SOURCE_MARKERS = (
    "我",
    "自己",
    "肚子",
    "拉肚子",
    "拉稀",
    "发烧",
    "没吐",
    "没发",
    "没什么用",
    "老是",
    "上厕所",
    "尿尿",
    "脑袋",
    "胸口",
    "孩子",
    "宝宝",
    "怎么办",
    "请问",
    "感觉",
    "特别厉害",
    "还有痰",
    "还有黄痰",
)


def _provided(value: str | None) -> str:
    cleaned = (value or "").strip()
    return cleaned if cleaned else "未提供"


def _prompt_value(value: str | None) -> str:
    return CONTROL_TAG_PATTERN.sub("", _provided(value)).replace("\x00", "").strip()


def _source_sections(patient: PatientInput) -> dict[str, str]:
    return {
        "主诉": _provided(patient.chief_complaint),
        "现病史": _provided(patient.history_present_illness),
        "既往史": _provided(patient.past_history),
        "辅助检查": _provided(patient.lab_results),
    }


def normalize_missing_source_sections(
    patient: PatientInput,
    sections: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    """Constrain absent source fields to the required literal instead of hallucinated text."""
    normalized = dict(sections)
    warnings: list[str] = []
    for name, source_value in _source_sections(patient).items():
        if source_value == "未提供" and normalized.get(name) != "未提供":
            normalized[name] = "未提供"
            warnings.append(f"{name}原始输入缺失，已由事实约束归一为“未提供”")
        elif name in {"既往史", "辅助检查"} and source_value != "未提供":
            authoritative = _clinical_style_text(source_value, patient.age, name)
            if normalized.get(name) != authoritative:
                normalized[name] = authoritative
                warnings.append(f"{name}已按原始输入进行事实锚定和书面化")

    if ATTACHMENT_CONTEXT_MARKER in patient.lab_results:
        attachment_context = patient.lab_results.split(ATTACHMENT_CONTEXT_MARKER, 1)[1].strip()
        generated_auxiliary = normalized.get("辅助检查", "").strip()
        if attachment_context and attachment_context not in generated_auxiliary:
            prefix = "" if generated_auxiliary in {"", "未提供"} else generated_auxiliary + "\n"
            normalized["辅助检查"] = (
                f"{prefix}{ATTACHMENT_CONTEXT_MARKER}\n{attachment_context}"
            )
            warnings.append("附件提取内容未被模型完整保留，已由事实约束原样补入辅助检查")
    return normalized, warnings


def sanitize_generated_text(text: str) -> str:
    """Decode SentencePiece byte tokens and remove generation-only artifacts."""

    def decode_byte_group(match: re.Match[str]) -> str:
        raw = bytes(
            int(value, 16)
            for value in BYTE_TOKEN_PATTERN.findall(match.group(0))
        )
        return raw.decode("utf-8", errors="replace")

    cleaned = BYTE_TOKEN_GROUP_PATTERN.sub(decode_byte_group, text or "")
    cleaned = re.sub(r"<extra_id_\d+>", "", cleaned)
    cleaned = re.sub(r"(?<=\d)(?:~|°|<unk>)\s*C\b", "℃", cleaned, flags=re.IGNORECASE)
    return cleaned.replace("\x00", "").strip()


def _chinese_number_values(token: str) -> tuple[int, ...]:
    """Parse common clinical Chinese numerals, including colloquial ranges such as 四五次."""
    if not token:
        return ()
    if "百" in token:
        hundreds, remainder = token.split("百", 1)
        base = CHINESE_DIGITS.get(hundreds, 1) * 100
        if not remainder:
            return (base,)
        tail = _chinese_number_values(remainder)
        return (base + tail[0],) if len(tail) == 1 else ()
    if "十" in token:
        tens, ones = token.split("十", 1)
        value = CHINESE_DIGITS.get(tens, 1) * 10
        if ones:
            if ones not in CHINESE_DIGITS:
                return ()
            value += CHINESE_DIGITS[ones]
        return (value,)
    values = tuple(CHINESE_DIGITS[character] for character in token if character in CHINESE_DIGITS)
    if len(values) <= 1:
        return values
    # Consecutive single numerals before a unit are commonly spoken ranges: 四五次、六七天。
    return tuple(dict.fromkeys(values))


def extract_numeric_facts(text: str) -> set[str]:
    """Return comparable numeric facts while accepting safe Chinese-to-Arabic normalization."""
    normalized = normalize_text(text)
    facts = set(NUMBER_PATTERN.findall(normalized))
    for match in CHINESE_NUMBER_WITH_UNIT_PATTERN.finditer(normalized):
        facts.update(str(value) for value in _chinese_number_values(match.group(1)))
    if "前天" in normalized:
        facts.add("2")
    if "昨天" in normalized or "昨日" in normalized:
        facts.add("1")
    if re.search(r"(?:一|1)(?:个)?(?:周|星期)", normalized):
        facts.add("7")
    if "半天" in normalized:
        facts.add("0.5")
    return facts


def _normalize_numerals_for_anchor(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        values = _chinese_number_values(match.group(1))
        if not values:
            return match.group(1)
        return "-".join(str(value) for value in values)

    normalized = CHINESE_NUMBER_WITH_UNIT_PATTERN.sub(replace, text)
    return normalized.replace("前天", "2天前").replace("昨天", "1天前").replace("昨日", "1天前")


def _normalize_anchor_terms(text: str) -> str:
    normalized = _normalize_numerals_for_anchor(normalize_text(text))
    aliases = sorted(
        (
            (alias, canonical)
            for canonical, values in CLINICAL_TERM_ALIASES.items()
            for alias in values
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for alias, canonical in aliases:
        normalized = normalized.replace(alias, canonical)
    return normalized


def _clinical_style_text(text: str, patient_age: int, section_name: str = "") -> str:
    cleaned = sanitize_generated_text(text)
    if cleaned == "无" and section_name == "既往史":
        return "既往无特殊病史"
    if cleaned in MISSING_SECTION_VALUES or not cleaned:
        return "未提供" if cleaned in MISSING_SECTION_VALUES else cleaned
    cleaned = ORAL_FILLER_PATTERN.sub("", cleaned)
    cleaned = ORAL_QUESTION_SENTENCE_PATTERN.sub("", cleaned)
    for source, replacement in CLINICAL_STYLE_REPLACEMENTS:
        cleaned = cleaned.replace(source, replacement)
    cleaned = re.sub(
        r"拉了([零〇一二两三四五六七八九十百\d]+(?:[至到~-][零〇一二两三四五六七八九十百\d]+)?)次",
        r"排稀便\1次",
        cleaned,
    )
    cleaned = cleaned.replace("前天晚上", "2天前晚间").replace("前天夜里", "2天前夜间")
    cleaned = cleaned.replace("第二天开始", "次日出现").replace("第二天就", "次日")
    cleaned = re.sub(
        r"(\d+天前(?:晚间|夜间)?)(?:吃了|食用)([^，,。；;]{1,30}?)(?:后)?(?=[，,。；;])",
        r"\1进食\2后",
        cleaned,
    )
    cleaned = cleaned.replace("感觉效果欠佳", "效果欠佳")
    cleaned = re.sub(r"[，,](?:但是|但|也)(?=无)", "，", cleaned)
    cleaned = cleaned.replace(",", "，").replace(";", "；")
    cleaned = _normalize_numerals_for_anchor(cleaned)
    cleaned = cleaned.replace("上周", "1周前")
    cleaned = cleaned.replace("淋雨以后就开始咳", "淋雨后出现咳嗽")
    cleaned = re.sub(r"咳(?:了|嗽)(\d+)(?:个)?星期", r"咳嗽\1周", cleaned)
    cleaned = re.sub(
        r"(\d+(?:\.\d+)?(?:天|周|月|年)前)开始",
        r"\1出现",
        cleaned,
    )
    cleaned = re.sub(r"最高(\d+(?:\.\d+)?)度", r"最高体温\1℃", cleaned)
    cleaned = cleaned.replace("头痛头晕", "头痛、头晕")
    cleaned = cleaned.replace("发热咳嗽", "发热、咳嗽")
    cleaned = re.sub(r"^这(\d+)天老是(.+)$", r"\2\1天", cleaned)
    cleaned = re.sub(r"^孩子(.+?)(\d+(?:\.\d+)?天)了?$", r"\1\2", cleaned)
    cleaned = re.sub(r"高血压(\d+(?:\.\d+)?年)", r"高血压病史\1", cleaned)
    cleaned = cleaned.replace("，还尿频", "、尿频").replace("尿痛还尿频", "尿痛、尿频")
    cleaned = cleaned.replace("，但是", "，").replace("，但", "，")
    if patient_age >= 14:
        cleaned = re.sub(r"患儿|宝宝|小儿", "患者", cleaned)
    if section_name == "现病史" and re.match(
        r"\d+(?:\.\d+)?(?:天|周|月|年)前",
        cleaned,
    ):
        subject = "患者" if patient_age >= 14 else "患儿"
        cleaned = f"{subject}于{cleaned}"
    if section_name == "现病史" and cleaned.startswith("突然"):
        subject = "患者" if patient_age >= 14 else "患儿"
        cleaned = re.sub(r"^突然(?:出现)?", f"{subject}突发", cleaned)
    if section_name == "既往史" and cleaned.startswith("既往有") and not cleaned.endswith("病史"):
        cleaned = f"{cleaned}病史"
    if section_name == "既往史" and cleaned in {"无特殊", "无特殊病史"}:
        cleaned = "既往无特殊病史"
    cleaned = re.sub(r"排稀便(\d+(?:-\d+)?次)，均为稀便", r"排稀便\1", cleaned)
    cleaned = re.sub(r"\s*([，。；：])\s*", r"\1", cleaned)
    cleaned = re.sub(r"[，；]{2,}", "，", cleaned)
    return cleaned.strip(" ，；")


def _allergy_history_text(value: str) -> str:
    cleaned = sanitize_generated_text(value).strip()
    if not cleaned or cleaned in {"未提供", "不详", "未询问"}:
        return "未提供"
    compact = re.sub(r"[，,。；;、\s]", "", cleaned)
    no_allergy_patterns = (
        r"无(?:明确)?(?:药物|药品)?过敏(?:史)?",
        r"否认(?:明确)?(?:药物|药品)?过敏(?:史)?",
        r"(?:我)?没(?:有)?(?:发现|听说)?(?:有)?(?:什么)?(?:药物|药品|药)?过敏(?:史)?",
        r"(?:我)?没有(?:发现|听说)?(?:有)?(?:什么)?(?:药物|药品|药)?过敏(?:史)?",
    )
    if compact in {"无", "没有", "未发现"} or any(
        re.fullmatch(pattern, compact) for pattern in no_allergy_patterns
    ):
        return "否认药物过敏史"
    cleaned = re.sub(r"^(?:我)?对", "对", cleaned)
    return _clinical_style_text(cleaned, 18, "过敏史")


def _vital_signs_text(value: str) -> str:
    cleaned = sanitize_generated_text(value).strip()
    if not cleaned or cleaned in MISSING_SECTION_VALUES:
        return "未提供"
    cleaned = _normalize_numerals_for_anchor(cleaned)
    cleaned = re.sub(
        r"(?:体温|T)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:摄氏)?(?:度|℃)",
        r"T \1℃",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"(?:心率|脉搏|P)\s*[:：]?\s*(\d+)\s*次(?:每分钟|/分钟|/分|/min)?",
        r"P \1次/分",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"(?:呼吸频率|呼吸|R)\s*[:：]?\s*(\d+)\s*次(?:每分钟|/分钟|/分|/min)?",
        r"R \1次/分",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"(?:血压|BP)\s*[:：]?\s*(\d+)\s*[/／]\s*(\d+)\s*(?:mmHg)?",
        r"BP \1/\2mmHg",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = cleaned.replace(",", "，").replace(";", "；")
    cleaned = re.sub(r"\s*([，；])\s*", r"\1", cleaned)
    return cleaned.strip(" ，；")


def _diagnosis_text(value: str, patient_age: int) -> str:
    cleaned = sanitize_generated_text(value).strip()
    if not cleaned or cleaned in MISSING_SECTION_VALUES:
        return "未提供"
    cleaned = re.sub(r"^(?:医生|大夫)?输入诊断[:：，, ]*", "", cleaned)
    cleaned = re.sub(r"^(?:医生|大夫)(?:说|说是|诊断为)[:：，, ]*", "", cleaned)
    cleaned = re.sub(r"^(?:医生|大夫)?考虑(?:可能)?[:：，, ]*", "考虑", cleaned)
    cleaned = re.sub(r"^(?:医生|大夫)?觉得(?:可能)?是?[:：，, ]*", "考虑", cleaned)
    cleaned = re.sub(r"^可能是?", "考虑", cleaned)
    return _clinical_style_text(cleaned, patient_age, "初步诊断")


def _treatment_record_text(value: str, patient_age: int) -> str:
    cleaned = sanitize_generated_text(value).strip()
    if cleaned == "无":
        return "未接受相关治疗"
    if not cleaned or cleaned in MISSING_SECTION_VALUES:
        return "未提供"
    if cleaned == "休息补水":
        return "曾休息并补充水分"
    if cleaned.startswith(("已接受", "曾接受", "已进行", "曾进行", "已给予", "曾给予", "已完成")):
        return _clinical_style_text(cleaned, patient_age, "既往治疗记录")
    cleaned = re.sub(r"^(?:我|患者)?(?:已经|已)?", "", cleaned)
    cleaned = cleaned.replace("打了点滴", "接受静脉输液治疗")
    cleaned = re.sub(r"做了(?:一次)?雾化", "接受雾化治疗", cleaned)
    cleaned = re.sub(r"^门诊补液([零〇一二两三四五六七八九十百\d]+次)", r"曾于门诊接受补液治疗\1", cleaned)
    cleaned = cleaned.replace("之后", "治疗后")
    cleaned = _clinical_style_text(cleaned, patient_age, "既往治疗记录")
    if cleaned.startswith(("接受", "进行")):
        cleaned = f"曾{cleaned}"
    return cleaned


def _medication_usage_text(value: str, patient_age: int) -> str:
    cleaned = sanitize_generated_text(value).strip()
    if cleaned == "无":
        return "未用药"
    if not cleaned or cleaned in MISSING_SECTION_VALUES:
        return "未提供"
    compact = re.sub(r"[，,。；;、\s]", "", cleaned)
    if compact in {"没吃药", "没有吃药", "没用药", "没有用药", "未用药"}:
        return "未自行用药"
    cleaned = re.sub(r"^(?:我|患者)?(?:已经|已)服用", "曾服用", cleaned)
    cleaned = re.sub(r"^(?:我|患者)?(?:已经|已)使用", "曾使用", cleaned)
    cleaned = re.sub(r"^(?:我|患者)?吃过", "曾服用", cleaned)
    cleaned = re.sub(r"^(?:我|患者)?吃了", "曾服用", cleaned)
    cleaned = re.sub(r"^(?:我|患者)?喝过", "曾服用", cleaned)
    cleaned = re.sub(r"^(?:我|患者)?喝了", "曾服用", cleaned)
    cleaned = re.sub(r"^(?:我|患者)?用过", "曾使用", cleaned)
    cleaned = re.sub(r"^(?:我|患者)?用了", "曾使用", cleaned)
    cleaned = re.sub(r"^口服", "曾口服", cleaned)
    return _clinical_style_text(cleaned, patient_age, "用药记录")


def normalize_record_fields(patient: PatientInput) -> dict[str, str]:
    """Normalize every non-generated field before it is assembled into the record."""
    return {
        "过敏史": _allergy_history_text(patient.allergy_history),
        "生命体征": _vital_signs_text(patient.vital_signs),
        "体格检查": _clinical_style_text(patient.physical_exam, patient.age, "体格检查"),
        "初步诊断": _diagnosis_text(patient.preliminary_diagnosis, patient.age),
        "既往治疗记录": _treatment_record_text(patient.treatment_taken, patient.age),
        "用药记录": _medication_usage_text(patient.medication_usage, patient.age),
    }


def normalize_clinical_sections(
    patient: PatientInput,
    sections: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    """Apply conservative clinical-writing normalization without adding medical facts."""
    normalized = {
        name: _clinical_style_text(value, patient.age, name)
        for name, value in sections.items()
    }
    changed = any(normalized.get(name) != sections.get(name) for name in sections)
    warnings = ["模型输出已完成临床书面语规范化"] if changed else []
    return normalized, warnings


def normalize_oral_source_sections(
    patient: PatientInput,
    sections: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    """Prefer a fact-complete grounded rewrite when short front-end fields are colloquial."""
    normalized = dict(sections)
    rewritten: list[str] = []
    for name, source_value in (
        ("主诉", patient.chief_complaint),
        ("现病史", patient.history_present_illness),
    ):
        source = _provided(source_value)
        if source == "未提供" or not any(marker in source for marker in ORAL_SOURCE_MARKERS):
            continue
        grounded = _clinical_style_text(source, patient.age, name)
        if grounded and grounded != normalized.get(name):
            normalized[name] = grounded
            rewritten.append(name)
    warnings = (
        [f"检测到口语输入，已对{'、'.join(rewritten)}执行原始事实锚定的临床书面化"]
        if rewritten
        else []
    )
    return normalized, warnings


def unsupported_critical_terms(
    source_text: str,
    generated_text: str,
    critical_terms: frozenset[str],
) -> list[str]:
    """Return new disease/drug concepts, allowing explicit colloquial aliases."""
    normalized_source = normalize_text(source_text)
    normalized_output = normalize_text(generated_text)
    return sorted(
        term
        for term in critical_terms
        if term in normalized_output
        and term not in normalized_source
        and not any(
            alias in normalized_source
            for alias in CRITICAL_TERM_SUPPORT_ALIASES.get(term, ())
        )
    )


def build_model_input(patient: PatientInput) -> str:
    """Build the fact-only source text used by both training and inference."""
    department = {
        "internal": "内科",
        "surgery": "外科",
        "pediatrics": "儿科",
        "emergency": "急诊",
        "other": "其他",
    }.get(patient.department, patient.department or "未提供")
    fields = (
        ("姓名", patient.name),
        ("性别", patient.gender),
        ("年龄", f"{patient.age}岁"),
        ("科室", department),
        ("就诊日期", patient.visit_date),
        ("主诉原文", patient.chief_complaint),
        ("现病史原文", patient.history_present_illness),
        ("既往史原文", patient.past_history),
        ("过敏史", patient.allergy_history),
        ("生命体征", patient.vital_signs),
        ("体格检查", patient.physical_exam),
        ("辅助检查原文", patient.lab_results),
        ("医生初步诊断", patient.preliminary_diagnosis),
        ("已接受治疗", patient.treatment_taken),
        ("用药记录", patient.medication_usage),
    )
    facts = "\n".join(f"[{name}]{_prompt_value(value)}" for name, value in fields)
    return (
        "任务：将患者口语、自述或医患对话改写为精简住院病历的四个规范叙述段；"
        "使用第三人称临床书面语，去除问候、提问、情绪和重复表达；"
        "主诉概括主要症状及持续时间，现病史按时间顺序描述症状、阴性表现及已执行处理。"
        "只保留输入中明确出现的事实，不得补充疾病、药物、检查数值或治疗；"
        "除原文本身已规范外，不得整段照抄口语。缺失项写‘未提供’。\n"
        "输出格式：<主诉>...<现病史>...<既往史>...<辅助检查>...\n"
        f"{facts}"
    )


def parse_generated_sections(text: str) -> dict[str, str]:
    normalized = sanitize_generated_text(text)
    sections: dict[str, str] = {}
    for name, value in SECTION_TAG_PATTERN.findall(normalized):
        cleaned = SENTENCE_SPACE_PATTERN.sub("\n\n", WHITESPACE_PATTERN.sub(" ", value)).strip()
        missing_key = re.sub(r"[\s，。；;,.]", "", cleaned)
        if missing_key in MISSING_SECTION_VALUES:
            cleaned = "未提供"
        if name not in sections:
            sections[name] = cleaned
    return sections


@dataclass(frozen=True)
class RecordGenerationResult:
    text: str
    info: RecordGenerationInfo
    sections: dict[str, str]
    record_fields: dict[str, str]


class RecordGuard:
    """Reject malformed or clearly fact-inconsistent generated sections."""

    def __init__(self) -> None:
        self.critical_terms = MedicalTermExtractor(limit=20).terms_for_categories(
            {"疾病", "药物"}
        )

    def validate(self, patient: PatientInput, sections: dict[str, str]) -> list[str]:
        warnings: list[str] = []
        missing = [name for name in SECTION_NAMES if not sections.get(name, "").strip()]
        if missing:
            warnings.append(f"模型输出缺少段落：{'、'.join(missing)}")
            return warnings

        source = build_model_input(patient)
        source_numbers = extract_numeric_facts(source)
        output_numbers = extract_numeric_facts("\n".join(sections.values()))
        added_numbers = sorted(output_numbers - source_numbers)
        if added_numbers:
            warnings.append(f"模型输出出现输入中不存在的数值：{'、'.join(added_numbers)}")

        patient_facts = "\n".join(
            _provided(value)
            for value in (
                patient.chief_complaint,
                patient.history_present_illness,
                patient.past_history,
                patient.allergy_history,
                patient.vital_signs,
                patient.physical_exam,
                patient.lab_results,
                patient.preliminary_diagnosis,
                patient.treatment_taken,
                patient.medication_usage,
            )
        )
        added_terms = unsupported_critical_terms(
            patient_facts,
            "\n".join(sections.values()),
            self.critical_terms,
        )
        if added_terms:
            preview = "、".join(added_terms[:8])
            suffix = "等" if len(added_terms) > 8 else ""
            warnings.append(f"模型输出出现输入中不存在的疾病或药物术语：{preview}{suffix}")

        for name in SECTION_NAMES:
            value = sections[name]
            if len(value) > 1_200:
                warnings.append(f"{name}段落异常过长")
            if CONTROL_TAG_PATTERN.search(value):
                warnings.append(f"{name}段落包含未解析控制标签")
            if "<unk>" in value or "�" in value:
                warnings.append(f"{name}段落包含无法可靠解码的字符")

        for name, source_value in (
            ("既往史", patient.past_history),
            ("辅助检查", patient.lab_results),
        ):
            if _provided(source_value) == "未提供" and sections[name] != "未提供":
                warnings.append(f"{name}原始输入缺失，但模型补写了内容")

        for name, source_value in (
            ("主诉", patient.chief_complaint),
            ("现病史", patient.history_present_illness),
        ):
            if not self._shares_anchor(source_value, sections[name]):
                warnings.append(f"{name}与原始输入缺少可核对的共同信息")
        return warnings

    @staticmethod
    def _shares_anchor(source: str, generated: str) -> bool:
        compact_source = re.sub(
            r"[^\u4e00-\u9fffA-Za-z0-9]",
            "",
            _normalize_anchor_terms(source),
        )
        compact_generated = re.sub(
            r"[^\u4e00-\u9fffA-Za-z0-9]",
            "",
            _normalize_anchor_terms(generated),
        )
        if not compact_source:
            return generated == "未提供"
        width = 2 if len(compact_source) >= 2 else 1
        anchors = {
            compact_source[index : index + width]
            for index in range(max(1, len(compact_source) - width + 1))
        }
        return any(anchor and anchor in compact_generated for anchor in anchors)


class RecordAssembler:
    def assemble(
        self,
        patient: PatientInput,
        sections: dict[str, str],
        record_fields: dict[str, str] | None = None,
    ) -> str:
        department = {
            "internal": "内科",
            "surgery": "外科",
            "pediatrics": "儿科",
            "emergency": "急诊",
            "other": "其他",
        }.get(patient.department, patient.department or "未提供")
        fields = record_fields or normalize_record_fields(patient)
        return "\n".join(
            (
                "住院病历",
                "",
                "一、基本信息",
                f"姓名：{patient.name}",
                f"性别：{patient.gender}",
                f"年龄：{patient.age}岁",
                f"就诊科室：{department}",
                f"就诊日期：{_provided(patient.visit_date)}",
                "",
                "二、主诉",
                _provided(sections.get("主诉")),
                "",
                "三、现病史",
                _provided(sections.get("现病史")),
                "",
                "四、既往史",
                _provided(sections.get("既往史")),
                "",
                "五、过敏史",
                fields["过敏史"],
                "",
                "六、生命体征与体格检查",
                f"生命体征：{fields['生命体征']}",
                f"体格检查：{fields['体格检查']}",
                "",
                "七、辅助检查",
                _provided(sections.get("辅助检查")),
                "",
                "八、初步诊断（医生输入）",
                fields["初步诊断"],
                "",
                "九、既往治疗记录（患者已接受）",
                fields["既往治疗记录"],
                "",
                "十、用药记录（患者已使用）",
                fields["用药记录"],
            )
        )


class TemplateRecordGenerator:
    name = "fact-preserving-template-fallback"

    def generate_sections(self, patient: PatientInput) -> dict[str, str]:
        return {
            "主诉": _provided(patient.chief_complaint),
            "现病史": _provided(patient.history_present_illness),
            "既往史": _provided(patient.past_history),
            "辅助检查": _provided(patient.lab_results),
        }


class TransformerRecordGenerator:
    _cache: dict[str, tuple[Any, Any, Any, str]] = {}
    _cache_lock = Lock()

    def __init__(self) -> None:
        if not (RECORD_MODEL_DIR / "config.json").exists():
            raise FileNotFoundError(f"病历生成模型目录不存在：{RECORD_MODEL_DIR}")
        self.tokenizer, self.model, self.torch, self.device = self._load_assets()

    @classmethod
    def _load_assets(cls) -> tuple[Any, Any, Any, str]:
        cache_key = str(RECORD_MODEL_DIR.resolve())
        with cls._cache_lock:
            if cache_key in cls._cache:
                return cls._cache[cache_key]
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(
                RECORD_MODEL_DIR,
                local_files_only=True,
                use_fast=False,
            )
            model = AutoModelForSeq2SeqLM.from_pretrained(
                RECORD_MODEL_DIR,
                local_files_only=True,
            )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cuda":
                model = model.bfloat16() if torch.cuda.is_bf16_supported() else model.half()
            model.to(device)
            model.eval()
            cls._cache[cache_key] = (tokenizer, model, torch, device)
            return cls._cache[cache_key]

    @staticmethod
    def _beam_count() -> int:
        raw = os.getenv("RECORD_GENERATOR_BEAMS", "4").strip()
        try:
            beams = int(raw)
        except ValueError as error:
            raise ValueError("RECORD_GENERATOR_BEAMS 必须为 1 到 8 的整数") from error
        if not 1 <= beams <= 8:
            raise ValueError("RECORD_GENERATOR_BEAMS 必须为 1 到 8 的整数")
        return beams

    def generate_text(
        self,
        patient: PatientInput,
        decoder_prefix: str | None = None,
    ) -> str:
        encoded = self.tokenizer(
            build_model_input(patient),
            return_tensors="pt",
            truncation=True,
            max_length=768,
        )
        encoded = {name: tensor.to(self.device) for name, tensor in encoded.items()}
        beams = self._beam_count()
        generation_options: dict[str, Any] = {
            "max_length": 320,
            "num_beams": beams,
        }
        if beams > 1:
            generation_options["early_stopping"] = True
        if decoder_prefix:
            decoder_input_ids = self.tokenizer(
                decoder_prefix,
                return_tensors="pt",
                add_special_tokens=False,
            )["input_ids"].to(self.device)
            generation_options["decoder_input_ids"] = decoder_input_ids
            generation_options["max_length"] = min(
                768,
                max(320, int(decoder_input_ids.shape[-1]) + 160),
            )
        with self.torch.inference_mode():
            tokens = self.model.generate(
                **encoded,
                **generation_options,
            )
        decoded = self.tokenizer.decode(tokens[0], skip_special_tokens=False)
        for token in (
            self.tokenizer.pad_token,
            self.tokenizer.eos_token,
            self.tokenizer.bos_token,
        ):
            if token:
                decoded = decoded.replace(token, "")
        return sanitize_generated_text(decoded)

    def generate_sections(self, patient: PatientInput) -> dict[str, str]:
        return parse_generated_sections(self.generate_text(patient))

    def regenerate_from_section(
        self,
        patient: PatientInput,
        section_name: str,
    ) -> dict[str, str]:
        """Retry a structurally incomplete result using a safe decoder prefix."""
        if section_name not in SECTION_NAMES:
            raise ValueError(f"未知病历段落：{section_name}")
        source_sections = _source_sections(patient)
        prefix_parts: list[str] = []
        for name in SECTION_NAMES:
            prefix_parts.append(f"<{name}>")
            if name == section_name:
                break
            prefix_parts.append(_prompt_value(source_sections[name]))
        return parse_generated_sections(
            self.generate_text(patient, decoder_prefix="".join(prefix_parts))
        )


class RecordGenerator:
    """Select the trained Transformer and safely fall back to fact-only assembly."""

    def __init__(self) -> None:
        requested = os.getenv("RECORD_GENERATOR_BACKEND", "auto").strip().lower()
        if requested not in {"auto", "transformer", "template"}:
            raise ValueError(
                "RECORD_GENERATOR_BACKEND 必须为 auto、transformer 或 template"
            )
        self.requested_backend = requested
        self.template = TemplateRecordGenerator()
        self.assembler = RecordAssembler()
        self.guard = RecordGuard()
        self.transformer: TransformerRecordGenerator | None = None
        self.startup_warnings: list[str] = []

        if requested != "template":
            try:
                self.transformer = TransformerRecordGenerator()
            except Exception as error:  # dependency/model availability is environment-specific
                self.startup_warnings.append(
                    f"Transformer 病历生成器未加载（{type(error).__name__}），已启用模板兜底"
                )
        if self._required() and self.transformer is None:
            detail = "；".join(self.startup_warnings) or "当前配置为模板后端"
            raise RuntimeError(f"REQUIRE_RECORD_GENERATOR=true，但模型未就绪：{detail}")

    @staticmethod
    def _required() -> bool:
        return os.getenv("REQUIRE_RECORD_GENERATOR", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    @property
    def model_loaded(self) -> bool:
        return self.transformer is not None

    @property
    def backend(self) -> str:
        return "transformer" if self.model_loaded else "template"

    @property
    def model_version(self) -> str:
        return RECORD_MODEL_VERSION

    @property
    def metadata(self) -> dict[str, object]:
        return RecordGenerationInfo(
            backend=self.backend,
            model_name=(
                RECORD_MODEL_NAME if self.requested_backend != "template" else self.template.name
            ),
            model_version=RECORD_MODEL_VERSION,
            fallback_used=self.backend == "template" and self.requested_backend != "template",
            warnings=tuple(self.startup_warnings),
        ).to_dict()

    def generate(self, patient: PatientInput) -> RecordGenerationResult:
        if self.transformer is not None:
            try:
                sections = self.transformer.generate_sections(patient)
                sections, style_warnings = normalize_clinical_sections(patient, sections)
                sections, grounding_warnings = normalize_oral_source_sections(
                    patient,
                    sections,
                )
                style_warnings.extend(grounding_warnings)
                sections, constraint_warnings = normalize_missing_source_sections(
                    patient,
                    sections,
                )
                missing = [
                    name for name in SECTION_NAMES if not sections.get(name, "").strip()
                ]
                retry_warnings: list[str] = []
                if missing:
                    first_missing = missing[0]
                    sections = self.transformer.regenerate_from_section(
                        patient,
                        first_missing,
                    )
                    sections, retry_style_warnings = normalize_clinical_sections(
                        patient,
                        sections,
                    )
                    style_warnings.extend(retry_style_warnings)
                    sections, retry_grounding_warnings = normalize_oral_source_sections(
                        patient,
                        sections,
                    )
                    style_warnings.extend(retry_grounding_warnings)
                    sections, retry_constraints = normalize_missing_source_sections(
                        patient,
                        sections,
                    )
                    constraint_warnings.extend(retry_constraints)
                    retry_warnings.append(
                        f"模型首次输出缺少{first_missing}，已完成受约束二次生成"
                    )
                guard_warnings = self.guard.validate(patient, sections)
                if guard_warnings:
                    raise ValueError("；".join(guard_warnings))
                record_fields = normalize_record_fields(patient)
                return RecordGenerationResult(
                    text=self.assembler.assemble(patient, sections, record_fields),
                    info=RecordGenerationInfo(
                        backend="transformer",
                        model_name=RECORD_MODEL_NAME,
                        model_version=RECORD_MODEL_VERSION,
                        warnings=tuple(
                            dict.fromkeys(style_warnings + constraint_warnings + retry_warnings)
                        ),
                    ),
                    sections=dict(sections),
                    record_fields=record_fields,
                )
            except Exception as error:  # the request must still produce a safe record
                warnings = [
                    *self.startup_warnings,
                    f"Transformer 输出未通过生成或事实校验（{error}），已使用输入事实兜底",
                ]
                return self._template_result(patient, True, warnings)

        fallback_used = self.requested_backend != "template"
        return self._template_result(patient, fallback_used, self.startup_warnings)

    def _template_result(
        self,
        patient: PatientInput,
        fallback_used: bool,
        warnings: list[str],
    ) -> RecordGenerationResult:
        sections = self.template.generate_sections(patient)
        sections, _style_warnings = normalize_clinical_sections(patient, sections)
        record_fields = normalize_record_fields(patient)
        return RecordGenerationResult(
            text=self.assembler.assemble(patient, sections, record_fields),
            info=RecordGenerationInfo(
                backend="template",
                model_name=(RECORD_MODEL_NAME if fallback_used else self.template.name),
                model_version=RECORD_MODEL_VERSION,
                fallback_used=fallback_used,
                warnings=tuple(warnings),
            ),
            sections=dict(sections),
            record_fields=record_fields,
        )

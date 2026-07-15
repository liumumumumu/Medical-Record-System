import html
import re
from collections.abc import Iterable


NEGATION_WORDS = ("无", "未见", "未", "否认", "不伴", "没有", "排除", "并无")
POSITIVE_SCOPE_PATTERN = re.compile(
    r"(?:但|而|另|现|仍|并)(?:有|伴有|出现|存在)"
    r"|(?<=[，,])(?:有|伴有|出现|存在)"
    r"|^(?:有|伴有|出现|存在)"
    r"|提示|可见"
)


# “无明显诱因”是病程描述习语，其中的“无”并不否定后续症状，需在归一化时整体剔除。
NO_TRIGGER_IDIOM_PATTERN = re.compile(r"无(?:明显)?(?:诱因|原因)")


def normalize_text(text: str) -> str:
    normalized = html.unescape(str(text or ""))
    normalized = re.sub(r"<[^>]+>", " ", normalized)
    normalized = NO_TRIGGER_IDIOM_PATTERN.sub("", normalized)
    normalized = normalized.replace("\u3000", " ").replace("\xa0", " ")
    normalized = re.sub(r"[\r\n\t]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def is_negated(text: str, start: int, window: int = 24) -> bool:
    context = text[max(0, start - window) : start]
    clause = re.split(r"[。；;！？!?]", context)[-1]
    last_negation = max((clause.rfind(word) for word in NEGATION_WORDS), default=-1)
    if last_negation < 0:
        return False
    last_positive = max(
        (match.start() for match in POSITIVE_SCOPE_PATTERN.finditer(clause)),
        default=-1,
    )
    return last_negation > last_positive


def has_positive_occurrence(text: str, term: str) -> bool:
    return any(not is_negated(text, match.start()) for match in re.finditer(re.escape(term), text))


def unique_preserve(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def extract_numeric_symptoms(text: str) -> list[str]:
    symptoms: list[str] = []
    for match in re.finditer(
        r"(?:(?:体温|T)\s*[:：]?\s*)?(3[5-9](?:\.\d)?|4[0-2](?:\.\d)?)\s*(?:℃|°C|度)", text, re.I
    ):
        temperature = float(match.group(1))
        if temperature >= 39:
            symptoms.extend(("发热", "高热"))
        elif temperature >= 37.3:
            symptoms.append("发热")

    for match in re.finditer(
        r"(?:血压|BP)\s*[:：]?\s*(\d{2,3})\s*/\s*(\d{2,3})\s*(?:mmHg)?"
        r"|(\d{2,3})\s*/\s*(\d{2,3})\s*mmHg",
        text,
        re.I,
    ):
        systolic = int(match.group(1) or match.group(3))
        diastolic = int(match.group(2) or match.group(4))
        if systolic >= 140 or diastolic >= 90:
            symptoms.append("血压升高")

    for match in re.finditer(r"(?:空腹)?血糖\s*[:：]?\s*(\d+(?:\.\d+)?)", text):
        glucose = float(match.group(1))
        if glucose >= 7.0:
            symptoms.append("血糖升高")
    return unique_preserve(symptoms)

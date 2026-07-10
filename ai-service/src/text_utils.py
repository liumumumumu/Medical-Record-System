import html
import re
from collections.abc import Iterable


NEGATION_WORDS = ("无", "未见", "未", "否认", "不伴", "没有", "排除", "并无")


def normalize_text(text: str) -> str:
    normalized = html.unescape(str(text or ""))
    normalized = re.sub(r"<[^>]+>", " ", normalized)
    normalized = normalized.replace("\u3000", " ").replace("\xa0", " ")
    normalized = re.sub(r"[\r\n\t]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def is_negated(text: str, start: int, window: int = 10) -> bool:
    context = text[max(0, start - window) : start]
    clause = re.split(r"[。；;，,！？!?]", context)[-1]
    return any(word in clause for word in NEGATION_WORDS)


def has_positive_occurrence(text: str, term: str) -> bool:
    return any(not is_negated(text, match.start()) for match in re.finditer(re.escape(term), text))


def unique_preserve(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def extract_numeric_symptoms(text: str) -> list[str]:
    symptoms: list[str] = []
    for match in re.finditer(r"(?:(?:体温|T)\s*[:：]?\s*)?(3[5-9](?:\.\d)?|4[0-2](?:\.\d)?)\s*℃", text, re.I):
        temperature = float(match.group(1))
        if temperature >= 39:
            symptoms.extend(("发热", "高热"))
        elif temperature >= 37.3:
            symptoms.append("发热")

    for match in re.finditer(r"(?:血压\s*[:：]?\s*)?(\d{2,3})\s*/\s*(\d{2,3})\s*(?:mmHg)?", text, re.I):
        systolic, diastolic = int(match.group(1)), int(match.group(2))
        if systolic >= 140 or diastolic >= 90:
            symptoms.append("血压升高")

    for match in re.finditer(r"(?:空腹)?血糖\s*[:：]?\s*(\d+(?:\.\d+)?)", text):
        glucose = float(match.group(1))
        if glucose >= 7.0:
            symptoms.append("血糖升高")
    return unique_preserve(symptoms)

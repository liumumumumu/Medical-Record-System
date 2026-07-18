from src.config import CONFIG_DIR, RESOURCE_DIR, load_json
from src.text_utils import has_positive_occurrence, normalize_text


# 语料中混入的日常泛化词，出现在“医学术语”结果里没有信息量。
GENERIC_TERMS = frozenset({"休息", "保暖", "按摩", "治疗", "护理"})

DEFAULT_TERMS = {
    "白细胞": "检查",
    "血常规": "检查",
    "尿常规": "检查",
    "体温": "指标",
    "血压": "指标",
    "血糖": "指标",
    "胸片": "检查",
    "CT": "检查",
    "核磁共振": "检查",
    "心电图": "检查",
    "C反应蛋白": "检查",
}


class MedicalTermExtractor:
    def __init__(self, limit: int = 20) -> None:
        self.limit = limit
        terms = dict(DEFAULT_TERMS)
        for diagnosis in load_json(CONFIG_DIR / "diagnosis_labels.json"):
            terms[diagnosis["label"]] = "疾病"
            for alias in diagnosis["aliases"]:
                terms[alias] = "疾病"
        resource_path = RESOURCE_DIR / "medical_terms.json"
        if resource_path.exists():
            terms.update(load_json(resource_path))
        self.term_categories = dict(terms)
        self.terms = sorted(
            (term for term in terms if term not in GENERIC_TERMS),
            key=lambda term: (-len(term), term),
        )

    def extract(self, text: str) -> list[str]:
        normalized = normalize_text(text)
        matches: list[str] = []
        for term in self.terms:
            if term in normalized and has_positive_occurrence(normalized, term):
                if any(term in matched for matched in matches):
                    continue
                matches.append(term)
                if len(matches) >= self.limit:
                    break
        return matches

    def terms_for_categories(self, categories: set[str]) -> frozenset[str]:
        return frozenset(
            normalize_text(term)
            for term, category in self.term_categories.items()
            if category in categories and len(normalize_text(term)) >= 2
        )

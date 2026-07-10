from dataclasses import dataclass

from src.config import CONFIG_DIR, load_json
from src.text_utils import extract_numeric_symptoms, is_negated, normalize_text, unique_preserve


@dataclass(frozen=True)
class SymptomExtraction:
    positive: list[str]
    negated: list[str]


class SymptomExtractor:
    def __init__(self) -> None:
        diagnoses = load_json(CONFIG_DIR / "diagnosis_labels.json")
        synonyms = load_json(CONFIG_DIR / "symptom_synonyms.json")
        canonical_terms = {
            symptom
            for diagnosis in diagnoses
            for symptom in diagnosis["keySymptoms"]
        }
        self.aliases = {term: term for term in canonical_terms}
        self.aliases.update(synonyms)
        self.sorted_aliases = sorted(self.aliases, key=lambda term: (-len(term), term))

    def extract(self, text: str) -> SymptomExtraction:
        normalized = normalize_text(text)
        positive: list[str] = []
        negated: list[str] = []
        occupied: list[tuple[int, int]] = []

        for alias in self.sorted_aliases:
            canonical = self.aliases[alias]
            start = 0
            while True:
                index = normalized.find(alias, start)
                if index < 0:
                    break
                end = index + len(alias)
                start = end
                if any(index >= left and end <= right for left, right in occupied):
                    continue
                occupied.append((index, end))
                if is_negated(normalized, index):
                    negated.append(canonical)
                else:
                    positive.append(canonical)

        positive.extend(extract_numeric_symptoms(normalized))
        positive = unique_preserve(positive)
        negated = [item for item in unique_preserve(negated) if item not in positive]
        return SymptomExtraction(positive=positive, negated=negated)

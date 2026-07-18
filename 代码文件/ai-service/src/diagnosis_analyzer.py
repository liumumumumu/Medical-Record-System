import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from src.config import CONFIG_DIR, MODEL_DIR, MODEL_VERSION, RESOURCE_DIR, load_json
from src.schema import DiagnosisResult
from src.text_utils import has_positive_occurrence, normalize_text


MIN_ASSERTED_SCORE = 0.25
MIN_CANDIDATE_SCORE = 0.15
TRANSFORMER_DIR = MODEL_DIR / "transformer_production"
TRANSFORMER_MAX_LENGTH = 256
TRANSFORMER_MODEL_VERSION = "2.0.0"

TRANSFORMER_TEMPERATURE = float(os.getenv("AI_TRANSFORMER_TEMPERATURE", "2.5"))

_TRANSFORMER_CACHE: dict[str, object] = {"loaded": False, "backend": None}


def _load_transformer_backend() -> dict | None:
    if _TRANSFORMER_CACHE["loaded"]:
        return _TRANSFORMER_CACHE["backend"]
    _TRANSFORMER_CACHE["loaded"] = True
    if not (TRANSFORMER_DIR / "config.json").exists():
        return None
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(TRANSFORMER_DIR)
        model = AutoModelForSequenceClassification.from_pretrained(TRANSFORMER_DIR)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device).eval()
        backend = {
            "torch": torch,
            "tokenizer": tokenizer,
            "model": model,
            "device": device,
            "labels": [model.config.id2label[i] for i in range(model.config.num_labels)],
        }
    except Exception:
        backend = None
    _TRANSFORMER_CACHE["backend"] = backend
    return backend


class DiagnosisAnalyzer:
    def __init__(
        self,
        model_path: Path | None = None,
        knowledge_path: Path | None = None,
    ) -> None:
        diagnoses = load_json(CONFIG_DIR / "diagnosis_labels.json")
        self.profiles = {item["label"]: item for item in diagnoses}
        self.labels = list(self.profiles)
        self.model_artifact = self._load_artifact(
            model_path or MODEL_DIR / "diagnosis_model.joblib"
        )
        self.knowledge_artifact = self._load_artifact(
            knowledge_path or RESOURCE_DIR / "knowledge_index.joblib"
        )

        mode = os.getenv("AI_MODEL_BACKEND", "auto").strip().lower()
        self.transformer_backend = None if mode == "sklearn" else _load_transformer_backend()

    @staticmethod
    def _load_artifact(path: Path) -> dict | None:
        return joblib.load(path) if path.exists() else None

    @property
    def model_loaded(self) -> bool:
        return self.transformer_backend is not None or self.model_artifact is not None

    @property
    def model_backend(self) -> str:
        if self.transformer_backend is not None:
            return "transformer"
        return "sklearn" if self.model_artifact is not None else "none"

    @property
    def model_version(self) -> str:
        return (
            TRANSFORMER_MODEL_VERSION
            if self.transformer_backend is not None
            else MODEL_VERSION
        )

    @property
    def knowledge_loaded(self) -> bool:
        return self.knowledge_artifact is not None

    def _transformer_scores(self, text: str) -> dict[str, float]:
        backend = self.transformer_backend
        torch = backend["torch"]
        with torch.no_grad():
            encoded = backend["tokenizer"](
                text,
                truncation=True,
                max_length=TRANSFORMER_MAX_LENGTH,
                return_tensors="pt",
            ).to(backend["device"])
            logits = backend["model"](**encoded).logits[0]
            probabilities = torch.softmax(
                logits / TRANSFORMER_TEMPERATURE, dim=-1
            ).cpu().tolist()
        return {
            label: float(probability)
            for label, probability in zip(backend["labels"], probabilities)
        }

    def _model_scores(self, text: str) -> dict[str, float]:
        if self.transformer_backend is not None:
            return self._transformer_scores(text)
        if not self.model_artifact:
            return {}
        vectorizer = self.model_artifact["vectorizer"]
        classifier = self.model_artifact["classifier"]
        matrix = vectorizer.transform([text])
        probabilities = classifier.predict_proba(matrix)[0]
        return {
            label: float(probability)
            for label, probability in zip(classifier.classes_, probabilities)
        }

    def _knowledge_scores(self, symptoms: list[str]) -> dict[str, float]:
        if not self.knowledge_artifact or not symptoms:
            return {}
        query = " ".join(sorted(symptoms))
        vectorizer = self.knowledge_artifact["vectorizer"]
        query_matrix = vectorizer.transform([query])
        similarities = cosine_similarity(query_matrix, self.knowledge_artifact["matrix"])[0]
        return {
            label: min(1.0, float(similarity) * 2.0)
            for label, similarity in zip(self.knowledge_artifact["labels"], similarities)
        }

    def _rule_scores(
        self, symptoms: list[str], text: str
    ) -> tuple[dict[str, float], dict[str, list[str]]]:
        symptom_set = set(symptoms)
        normalized = normalize_text(text)
        scores: dict[str, float] = {}
        matches: dict[str, list[str]] = {}
        for label, profile in self.profiles.items():
            matched = [item for item in profile["keySymptoms"] if item in symptom_set]
            aliases = [label, *profile["aliases"]]
            direct_mention = any(
                alias in normalized and has_positive_occurrence(normalized, alias)
                for alias in aliases
            )
            score = min(1.0, len(matched) / 3.0)
            if direct_mention:
                score = max(score, 0.9)
            scores[label] = score
            matches[label] = matched
        return scores, matches

    def analyze(
        self,
        text: str,
        symptoms: list[str],
        negated_symptoms: list[str] | None = None,
    ) -> DiagnosisResult:
        model_scores = self._model_scores(text)
        knowledge_scores = self._knowledge_scores(symptoms)
        rule_scores, matches = self._rule_scores(symptoms, text)
        final_scores: dict[str, float] = {}

        for label, profile in self.profiles.items():
            if profile["core"]:
                score = (
                    0.55 * model_scores.get(label, 0.0)
                    + 0.30 * knowledge_scores.get(label, 0.0)
                    + 0.15 * rule_scores.get(label, 0.0)
                )
            else:
                score = (
                    0.70 * knowledge_scores.get(label, 0.0)
                    + 0.30 * rule_scores.get(label, 0.0)
                )
            final_scores[label] = float(score)

        ranked = sorted(final_scores.items(), key=lambda item: (-item[1], item[0]))
        candidates = [
            label for label, score in ranked if score >= MIN_CANDIDATE_SCORE
        ][:3]
        best_label, best_score = ranked[0]
        can_assert = len(symptoms) >= 2 and best_score >= MIN_ASSERTED_SCORE
        top1 = best_label if can_assert else "暂无法确定"

        if can_assert:
            matched = matches.get(best_label) or symptoms[:4]
            reason = f"识别到{('、'.join(matched))}等表现，融合模型、症状知识库和规则后，{best_label}得分最高。"
        elif symptoms:
            reason = (
                f"当前仅识别到{('、'.join(symptoms[:5]))}，有效证据或融合得分不足，"
                "暂不形成明确判断。"
            )
        else:
            reason = "未识别到足够的阳性症状或指标，暂不形成明确判断。"

        negated = negated_symptoms or []
        if negated:
            reason += f" 已排除否定描述：{('、'.join(negated[:4]))}。"

        return DiagnosisResult(
            top1=top1,
            candidates=candidates,
            reason=reason,
            scores={label: round(score, 6) for label, score in ranked},
        )

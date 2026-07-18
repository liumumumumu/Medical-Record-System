from __future__ import annotations

from collections import Counter
import math
import re
from typing import Iterable

from src.medical_term_extractor import MedicalTermExtractor
from src.record_generator import (
    SECTION_NAMES,
    extract_numeric_facts,
    parse_generated_sections,
    unsupported_critical_terms,
)


TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]|[A-Za-z]+|\d+(?:\.\d+)?")
CRITICAL_TERMS = MedicalTermExtractor(limit=20).terms_for_categories({"疾病", "药物"})


def tokens(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def ngrams(items: list[str], width: int) -> list[tuple[str, ...]]:
    return [tuple(items[index : index + width]) for index in range(len(items) - width + 1)]


def overlap_f1(candidate: list[object], reference: list[object]) -> float:
    if not candidate or not reference:
        return float(candidate == reference)
    overlap = sum((Counter(candidate) & Counter(reference)).values())
    precision = overlap / len(candidate)
    recall = overlap / len(reference)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def lcs_length(left: list[str], right: list[str]) -> int:
    if len(left) > len(right):
        left, right = right, left
    previous = [0] * (len(left) + 1)
    for right_token in right:
        current = [0]
        for index, left_token in enumerate(left, start=1):
            if left_token == right_token:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current
    return previous[-1]


def rouge_l(candidate: list[str], reference: list[str]) -> float:
    if not candidate or not reference:
        return float(candidate == reference)
    lcs = lcs_length(candidate, reference)
    precision = lcs / len(candidate)
    recall = lcs / len(reference)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def best_reference_scores(prediction: str, references: list[str]) -> tuple[float, float, float]:
    candidate = tokens(prediction)
    scores = []
    for reference in references:
        reference_tokens = tokens(reference)
        scores.append(
            (
                overlap_f1(candidate, reference_tokens),
                overlap_f1(ngrams(candidate, 2), ngrams(reference_tokens, 2)),
                rouge_l(candidate, reference_tokens),
            )
        )
    return max(scores, key=lambda item: item[2]) if scores else (0.0, 0.0, 0.0)


def critical_terms_are_consistent(prediction: str, source: str) -> bool:
    return not unsupported_critical_terms(source, prediction, CRITICAL_TERMS)


def corpus_bleu(
    predictions: list[str],
    references: list[list[str]],
    max_order: int,
) -> float:
    matches = [0] * max_order
    possible = [0] * max_order
    candidate_length = 0
    reference_length = 0
    for prediction, reference_group in zip(predictions, references, strict=True):
        candidate = tokens(prediction)
        tokenized_references = [tokens(reference) for reference in reference_group]
        candidate_length += len(candidate)
        reference_length += min(
            (len(reference) for reference in tokenized_references),
            key=lambda length: (abs(length - len(candidate)), length),
            default=0,
        )
        for order in range(1, max_order + 1):
            candidate_counts = Counter(ngrams(candidate, order))
            maximum_reference_counts: Counter[tuple[str, ...]] = Counter()
            for reference in tokenized_references:
                reference_counts = Counter(ngrams(reference, order))
                for gram, count in reference_counts.items():
                    maximum_reference_counts[gram] = max(maximum_reference_counts[gram], count)
            matches[order - 1] += sum((candidate_counts & maximum_reference_counts).values())
            possible[order - 1] += max(len(candidate) - order + 1, 0)
    if not candidate_length:
        return 0.0
    precisions = [(matched + 1.0) / (total + 1.0) for matched, total in zip(matches, possible, strict=True)]
    geometric_mean = math.exp(sum(math.log(value) for value in precisions) / max_order)
    brevity_penalty = 1.0 if candidate_length > reference_length else math.exp(
        1.0 - reference_length / max(candidate_length, 1)
    )
    return brevity_penalty * geometric_mean


def evaluate_generation(
    predictions: Iterable[str],
    reference_groups: Iterable[list[str]],
    sources: Iterable[str] | None = None,
) -> dict[str, float]:
    prediction_list = list(predictions)
    references_list = list(reference_groups)
    if len(prediction_list) != len(references_list):
        raise ValueError("预测数量与参考答案数量不一致")
    source_list = list(sources) if sources is not None else [""] * len(prediction_list)
    if len(source_list) != len(prediction_list):
        raise ValueError("预测数量与输入数量不一致")

    rouge_scores = [
        best_reference_scores(prediction, references)
        for prediction, references in zip(prediction_list, references_list, strict=True)
    ]
    parsed = [parse_generated_sections(prediction) for prediction in prediction_list]
    parse_rate = sum(all(section in value for section in SECTION_NAMES) for value in parsed) / max(
        len(parsed), 1
    )
    section_completeness = sum(
        sum(bool(value.get(section, "").strip()) for section in SECTION_NAMES) / len(SECTION_NAMES)
        for value in parsed
    ) / max(len(parsed), 1)
    numeric_consistency = sum(
        extract_numeric_facts(prediction).issubset(extract_numeric_facts(source))
        for prediction, source in zip(prediction_list, source_list, strict=True)
    ) / max(len(prediction_list), 1)
    critical_term_consistency = sum(
        critical_terms_are_consistent(prediction, source)
        for prediction, source in zip(prediction_list, source_list, strict=True)
    ) / max(len(prediction_list), 1)
    return {
        "bleu2": corpus_bleu(prediction_list, references_list, 2),
        "bleu4": corpus_bleu(prediction_list, references_list, 4),
        "rouge1": sum(score[0] for score in rouge_scores) / max(len(rouge_scores), 1),
        "rouge2": sum(score[1] for score in rouge_scores) / max(len(rouge_scores), 1),
        "rougeL": sum(score[2] for score in rouge_scores) / max(len(rouge_scores), 1),
        "parseRate": parse_rate,
        "sectionCompleteness": section_completeness,
        "numericConsistency": numeric_consistency,
        "criticalTermConsistency": critical_term_consistency,
        "sampleCount": float(len(prediction_list)),
    }

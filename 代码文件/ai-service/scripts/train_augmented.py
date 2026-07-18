"""数据扩充对比实验：远程监督弱标签能否提升五类诊断模型。

数据源：Toyhom 中文医疗对话数据集儿科部分（dataset/Chinese-medical-dialogue/pediatric_qa.csv，
GB18030，department/title/ask/answer 四列，无诊断标签）。

弱标签协议（远程监督）：
- 输入 = 患者侧 title + ask；标签 = 医生 answer 中出现的疾病名。
- answer 命中且只命中五类中的一类才收录（多类命中视为歧义丢弃）；
- "支气管肺炎/毛细支气管炎" 先行剔除，避免误配"支气管炎"；
- 去重、输入至少 10 字、每类按种子 42 随机采样至上限。

评估协议与基线完全一致：IMCS-21 官方 dev/test 划分原样不动，超参数与
scripts/train_model.py 相同。产物写入 models/augmentation_metrics.json，
不覆盖任何现有模型或指标文件。
"""

import csv
import json
import random
import sys
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from scripts.train_model import load_split  # noqa: E402
from src.config import DATASET_ROOT, MODEL_DIR  # noqa: E402


QA_PATH = DATASET_ROOT / "Chinese-medical-dialogue" / "pediatric_qa.csv"
INTERNAL_QA_PATH = DATASET_ROOT / "Chinese-medical-dialogue" / "internal_qa.csv"
RANDOM_STATE = 42
CLASS_CAPS = (500, 2000)

LABEL_ALIASES = {
    "上呼吸道感染": ("上呼吸道感染", "上感"),
    "普通感冒": ("感冒",),
    "支气管炎": ("支气管炎",),
    "腹泻": ("腹泻",),
    "便秘": ("便秘",),
}
# 这些串包含五类别名但属于其他疾病，匹配前整体剔除
CONFUSABLE_TERMS = ("支气管肺炎", "毛细支气管炎", "胃肠感冒")


def weak_label(answer: str) -> str | None:
    cleaned = answer
    for term in CONFUSABLE_TERMS:
        cleaned = cleaned.replace(term, "")
    matched = [
        label
        for label, aliases in LABEL_ALIASES.items()
        if any(alias in cleaned for alias in aliases)
    ]
    # “上感”是“感冒”的近义表述，医生常并提，二者同现时保守丢弃
    return matched[0] if len(matched) == 1 else None


def build_augmented_pool(paths: tuple[Path, ...] = (QA_PATH,)) -> dict[str, list[str]]:
    pool: dict[str, list[str]] = {label: [] for label in LABEL_ALIASES}
    seen: set[str] = set()
    for path in paths:
        with path.open("r", encoding="gb18030", errors="ignore", newline="") as file:
            for row in csv.DictReader(file):
                text = f"{(row.get('title') or '').strip()} {(row.get('ask') or '').strip()}".strip()
                if len(text) < 10 or text in seen:
                    continue
                label = weak_label(row.get("answer") or "")
                if label is None:
                    continue
                seen.add(text)
                pool[label].append(text)
    return pool


def train_and_eval(
    train_texts: list[str], train_labels: list[str],
    dev: tuple[list[str], list[str]], test: tuple[list[str], list[str]],
) -> dict[str, object]:
    vectorizer = TfidfVectorizer(
        analyzer="char", ngram_range=(2, 5), min_df=2, max_features=70_000, sublinear_tf=True
    )
    matrix = vectorizer.fit_transform(train_texts)
    classifier = LogisticRegression(
        max_iter=1500, class_weight="balanced", solver="lbfgs", random_state=RANDOM_STATE
    )
    classifier.fit(matrix, train_labels)
    result: dict[str, object] = {"trainSize": len(train_texts)}
    for split_name, (texts, labels) in (("dev", dev), ("test", test)):
        predictions = classifier.predict(vectorizer.transform(texts))
        result[split_name] = {
            "accuracy": round(float(accuracy_score(labels, predictions)), 6),
            "macroF1": round(float(f1_score(labels, predictions, average="macro")), 6),
        }
        if split_name == "test":
            result["testReport"] = classification_report(
                labels, predictions, digits=4, zero_division=0, output_dict=True
            )
    return result


def main() -> None:
    train_texts, train_labels = load_split("train")
    dev = load_split("dev")
    test = load_split("test")

    pool = build_augmented_pool()
    pool_sizes = {label: len(texts) for label, texts in pool.items()}
    print("弱标签样本池:", json.dumps(pool_sizes, ensure_ascii=False))

    experiments: dict[str, object] = {
        "baseline_imcs_only": train_and_eval(train_texts, train_labels, dev, test),
    }

    rng = random.Random(RANDOM_STATE)
    sampled_full: dict[str, list[str]] = {
        label: rng.sample(texts, len(texts)) for label, texts in pool.items()
    }
    for cap in CLASS_CAPS:
        extra_texts: list[str] = []
        extra_labels: list[str] = []
        for label, texts in sampled_full.items():
            take = texts[: min(cap, len(texts))]
            extra_texts.extend(take)
            extra_labels.extend([label] * len(take))
        experiments[f"imcs_plus_weak_{cap}_per_class"] = train_and_eval(
            train_texts + extra_texts, train_labels + extra_labels, dev, test
        )

    weak_texts = [text for label in sampled_full for text in sampled_full[label][:2000]]
    weak_labels = [label for label in sampled_full for _ in sampled_full[label][:2000]]
    experiments["weak_only_no_imcs"] = train_and_eval(weak_texts, weak_labels, dev, test)

    output = {
        "protocol": "distant supervision from Toyhom pediatric QA; evaluation on untouched IMCS-21 official dev/test",
        "weakPoolSizes": pool_sizes,
        "randomState": RANDOM_STATE,
        "experiments": experiments,
    }
    (MODEL_DIR / "augmentation_metrics.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

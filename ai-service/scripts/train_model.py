import json
import platform
import sys
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from src.config import (  # noqa: E402
    DATASET_ROOT,
    MODEL_DIR,
    MODEL_NAME,
    MODEL_VERSION,
    ensure_output_directories,
    load_json,
)


SELECTED_LABELS = {
    "上呼吸道感染": "上呼吸道感染",
    "小儿感冒": "普通感冒",
    "小儿支气管炎": "支气管炎",
    "小儿腹泻": "腹泻",
    "小儿便秘": "便秘",
}
RANDOM_STATE = 42


def load_split(split: str) -> tuple[list[str], list[str]]:
    path = DATASET_ROOT / "IMCS-21" / "dataset" / f"{split}.json"
    data = load_json(path)
    texts: list[str] = []
    labels: list[str] = []
    for item in data.values():
        source_label = item.get("diagnosis")
        if source_label not in SELECTED_LABELS:
            continue
        report_list = item.get("report") or [{}]
        report = report_list[-1] if isinstance(report_list, list) else {}
        structured_text = " ".join(
            str(report.get(field, ""))
            for field in ("主诉", "现病史", "既往史", "辅助检查")
        )
        texts.append(f"{item.get('self_report', '')} {structured_text}".strip())
        labels.append(SELECTED_LABELS[source_label])
    return texts, labels


def _metrics(y_true: list[str], y_pred: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "macroF1": round(float(f1_score(y_true, y_pred, average="macro")), 6),
    }


def train() -> dict[str, object]:
    ensure_output_directories()
    train_texts, train_labels = load_split("train")
    dev_texts, dev_labels = load_split("dev")
    test_texts, test_labels = load_split("test")

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 5),
        min_df=2,
        max_features=70_000,
        sublinear_tf=True,
    )
    train_matrix = vectorizer.fit_transform(train_texts)
    dev_matrix = vectorizer.transform(dev_texts)
    test_matrix = vectorizer.transform(test_texts)
    classifier = LogisticRegression(
        max_iter=1500,
        class_weight="balanced",
        solver="lbfgs",
        random_state=RANDOM_STATE,
    )
    classifier.fit(train_matrix, train_labels)
    dev_predictions = classifier.predict(dev_matrix)
    test_predictions = classifier.predict(test_matrix)
    labels = list(classifier.classes_)

    metrics: dict[str, object] = {
        "modelName": MODEL_NAME,
        "modelVersion": MODEL_VERSION,
        "randomState": RANDOM_STATE,
        "algorithm": "character TF-IDF (2-5 grams) + LogisticRegression",
        "labels": labels,
        "sampleCounts": {
            "train": len(train_labels),
            "dev": len(dev_labels),
            "test": len(test_labels),
        },
        "featureCount": int(train_matrix.shape[1]),
        "dev": _metrics(dev_labels, dev_predictions),
        "test": _metrics(test_labels, test_predictions),
        "environment": {
            "python": platform.python_version(),
            "scikitLearn": sklearn.__version__,
        },
    }
    report = classification_report(
        test_labels,
        test_predictions,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )
    report_text = classification_report(
        test_labels,
        test_predictions,
        labels=labels,
        digits=4,
        zero_division=0,
    )
    matrix = confusion_matrix(test_labels, test_predictions, labels=labels)

    artifact = {
        "vectorizer": vectorizer,
        "classifier": classifier,
        "labels": labels,
        "metadata": metrics,
    }
    joblib.dump(artifact, MODEL_DIR / "diagnosis_model.joblib")
    (MODEL_DIR / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (MODEL_DIR / "classification_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (MODEL_DIR / "classification_report.txt").write_text(report_text, encoding="utf-8")

    figure, axis = plt.subplots(figsize=(8, 6))
    ConfusionMatrixDisplay(confusion_matrix=matrix, display_labels=labels).plot(
        ax=axis, cmap="Blues", colorbar=False, xticks_rotation=25
    )
    axis.set_title("IMCS-21 核心五类诊断混淆矩阵")
    figure.tight_layout()
    figure.savefig(MODEL_DIR / "confusion_matrix.png", dpi=160)
    plt.close(figure)

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return metrics


if __name__ == "__main__":
    train()

"""BERT 对比实验：与 TF-IDF + LogisticRegression 基线在同一 IMCS-21 官方划分上对比。

训练 bert-base-chinese 五类诊断分类器，评估协议与 scripts/train_model.py 完全一致：
同一 load_split、同一官方 train/dev/test 划分、同样的平衡类别权重、随机种子 42。
产物写入 models/transformer_* 与 models/transformer/，不影响线上推理链路。
"""

import json
import platform
import sys
import time
from pathlib import Path

import matplotlib
import numpy as np
import torch
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from transformers import AutoModelForSequenceClassification, AutoTokenizer


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from scripts.train_model import load_split  # noqa: E402
from src.config import MODEL_DIR, ensure_output_directories  # noqa: E402


PRETRAINED = "bert-base-chinese"
MAX_LENGTH = 256
BATCH_SIZE = 16
EPOCHS = 5
LEARNING_RATE = 2e-5
WEIGHT_DECAY = 0.01
WARMUP_RATIO = 0.1
RANDOM_STATE = 42
OUTPUT_DIR = MODEL_DIR / "transformer"


def batches(texts: list[str], labels: np.ndarray | None, size: int, shuffle: bool, generator: np.random.Generator):
    order = np.arange(len(texts))
    if shuffle:
        generator.shuffle(order)
    for start in range(0, len(order), size):
        index = order[start : start + size]
        chunk = [texts[i] for i in index]
        yield chunk, (labels[index] if labels is not None else None)


@torch.no_grad()
def predict(model, tokenizer, texts: list[str], device: torch.device) -> np.ndarray:
    model.eval()
    outputs: list[np.ndarray] = []
    generator = np.random.default_rng(0)
    for chunk, _ in batches(texts, None, BATCH_SIZE * 2, shuffle=False, generator=generator):
        encoded = tokenizer(
            chunk, truncation=True, max_length=MAX_LENGTH, padding=True, return_tensors="pt"
        ).to(device)
        logits = model(**encoded).logits
        outputs.append(logits.argmax(dim=-1).cpu().numpy())
    return np.concatenate(outputs)


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "macroF1": round(float(f1_score(y_true, y_pred, average="macro")), 6),
    }


def measure_latency(model, tokenizer, texts: list[str], device: torch.device, rounds: int = 50) -> float:
    model.eval()
    sample = texts[:rounds] if len(texts) >= rounds else texts * (rounds // len(texts) + 1)
    with torch.no_grad():
        # 预热，排除首次编译/搬运开销
        for text in sample[:5]:
            encoded = tokenizer(text, truncation=True, max_length=MAX_LENGTH, return_tensors="pt").to(device)
            model(**encoded)
        if device.type == "cuda":
            torch.cuda.synchronize()
        started = time.perf_counter()
        for text in sample[:rounds]:
            encoded = tokenizer(text, truncation=True, max_length=MAX_LENGTH, return_tensors="pt").to(device)
            model(**encoded)
        if device.type == "cuda":
            torch.cuda.synchronize()
    return round((time.perf_counter() - started) / rounds * 1000, 2)


def train() -> dict[str, object]:
    ensure_output_directories()
    torch.manual_seed(RANDOM_STATE)
    np.random.seed(RANDOM_STATE)

    train_texts, train_label_names = load_split("train")
    dev_texts, dev_label_names = load_split("dev")
    test_texts, test_label_names = load_split("test")

    # 与 sklearn classifier.classes_ 的字典序一致，保证分类报告可逐行对比
    labels = sorted(set(train_label_names))
    label_to_id = {label: index for index, label in enumerate(labels)}
    train_labels = np.array([label_to_id[name] for name in train_label_names])
    dev_labels = np.array([label_to_id[name] for name in dev_label_names])
    test_labels = np.array([label_to_id[name] for name in test_label_names])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(PRETRAINED)
    model = AutoModelForSequenceClassification.from_pretrained(
        PRETRAINED,
        num_labels=len(labels),
        id2label={index: label for label, index in label_to_id.items()},
        label2id=label_to_id,
    ).to(device)

    # 与基线 class_weight="balanced" 对齐：n_samples / (n_classes * bincount)
    counts = np.bincount(train_labels, minlength=len(labels))
    class_weights = torch.tensor(
        len(train_labels) / (len(labels) * counts), dtype=torch.float32, device=device
    )
    criterion = torch.nn.CrossEntropyLoss(weight=class_weights)

    optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    steps_per_epoch = int(np.ceil(len(train_texts) / BATCH_SIZE))
    total_steps = steps_per_epoch * EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)

    def lr_lambda(step: int) -> float:
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        return max(0.0, (total_steps - step) / max(1, total_steps - warmup_steps))

    scheduler = LambdaLR(optimizer, lr_lambda)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    generator = np.random.default_rng(RANDOM_STATE)

    history: list[dict[str, object]] = []
    best_dev_f1 = -1.0
    started = time.perf_counter()

    for epoch in range(1, EPOCHS + 1):
        model.train()
        epoch_loss = 0.0
        for chunk, chunk_labels in batches(train_texts, train_labels, BATCH_SIZE, shuffle=True, generator=generator):
            encoded = tokenizer(
                chunk, truncation=True, max_length=MAX_LENGTH, padding=True, return_tensors="pt"
            ).to(device)
            targets = torch.tensor(chunk_labels, dtype=torch.long, device=device)
            optimizer.zero_grad()
            with torch.amp.autocast("cuda", enabled=device.type == "cuda"):
                logits = model(**encoded).logits
                loss = criterion(logits, targets)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            epoch_loss += float(loss.detach())

        dev_predictions = predict(model, tokenizer, dev_texts, device)
        dev_metrics = _metrics(dev_labels, dev_predictions)
        history.append(
            {"epoch": epoch, "trainLoss": round(epoch_loss / steps_per_epoch, 4), **dev_metrics}
        )
        print(f"epoch {epoch}: loss={history[-1]['trainLoss']} dev={dev_metrics}")
        if dev_metrics["macroF1"] > best_dev_f1:
            best_dev_f1 = dev_metrics["macroF1"]
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(OUTPUT_DIR)
            tokenizer.save_pretrained(OUTPUT_DIR)

    training_seconds = round(time.perf_counter() - started, 1)

    # 用 dev macro-F1 最优的权重做最终测试集评估
    model = AutoModelForSequenceClassification.from_pretrained(OUTPUT_DIR).to(device)
    test_predictions = predict(model, tokenizer, test_texts, device)
    test_metrics = _metrics(test_labels, test_predictions)
    dev_predictions = predict(model, tokenizer, dev_texts, device)
    dev_metrics = _metrics(dev_labels, dev_predictions)

    report_text = classification_report(
        test_labels, test_predictions, target_names=labels, digits=4, zero_division=0
    )
    report_dict = classification_report(
        test_labels, test_predictions, target_names=labels, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(test_labels, test_predictions)

    gpu_latency = measure_latency(model, tokenizer, test_texts, device) if device.type == "cuda" else None
    cpu_model = model.to(torch.device("cpu"))
    cpu_latency = measure_latency(cpu_model, tokenizer, test_texts, torch.device("cpu"))

    metrics: dict[str, object] = {
        "modelName": "bert-base-chinese-finetuned",
        "pretrained": PRETRAINED,
        "parameterCount": int(sum(p.numel() for p in cpu_model.parameters())),
        "randomState": RANDOM_STATE,
        "maxLength": MAX_LENGTH,
        "batchSize": BATCH_SIZE,
        "epochs": EPOCHS,
        "learningRate": LEARNING_RATE,
        "classWeighting": "balanced",
        "labels": labels,
        "sampleCounts": {
            "train": len(train_labels),
            "dev": len(dev_labels),
            "test": len(test_labels),
        },
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        "trainingSeconds": training_seconds,
        "history": history,
        "dev": dev_metrics,
        "test": test_metrics,
        "latencyMsPerSample": {"gpu": gpu_latency, "cpu": cpu_latency},
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
        },
    }

    (MODEL_DIR / "transformer_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (MODEL_DIR / "transformer_classification_report.json").write_text(
        json.dumps(report_dict, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (MODEL_DIR / "transformer_classification_report.txt").write_text(report_text, encoding="utf-8")

    figure, axis = plt.subplots(figsize=(8, 6))
    ConfusionMatrixDisplay(confusion_matrix=matrix, display_labels=labels).plot(
        ax=axis, cmap="Blues", colorbar=False, xticks_rotation=25
    )
    axis.set_title("BERT 微调模型：IMCS-21 核心五类混淆矩阵")
    figure.tight_layout()
    figure.savefig(MODEL_DIR / "transformer_confusion_matrix.png", dpi=160)
    plt.close(figure)

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(report_text)
    return metrics


if __name__ == "__main__":
    train()

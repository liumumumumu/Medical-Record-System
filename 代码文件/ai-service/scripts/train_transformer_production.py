"""生产候选 BERT 训练：儿科 + 内科双源弱标签，5k/10k 两档剂量，择优保存权重。

- 弱标签池：儿科问答优先、内科问答补足稀缺类（上感/支气管炎），协议同 train_augmented.py；
- 条件：金标 1,358 + 弱标 {1000, 2000}/类，训练配置与 train_transformer.py 完全一致；
- 模型选择只看 dev macro-F1（测试集不参与任何选择），两档的 test 结果均如实记录；
- 胜出条件的最优 epoch 权重保存到 models/transformer_production/，
  指标写入 models/transformer_production_metrics.json。
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import classification_report
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from transformers import AutoModelForSequenceClassification, AutoTokenizer


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from scripts.train_augmented import (  # noqa: E402
    INTERNAL_QA_PATH,
    QA_PATH,
    build_augmented_pool,
)
from scripts.train_model import load_split  # noqa: E402
from scripts.train_transformer import (  # noqa: E402
    BATCH_SIZE,
    EPOCHS,
    LEARNING_RATE,
    MAX_LENGTH,
    PRETRAINED,
    RANDOM_STATE,
    WARMUP_RATIO,
    WEIGHT_DECAY,
    _metrics,
    batches,
    measure_latency,
    predict,
)
from src.config import MODEL_DIR  # noqa: E402


CLASS_CAPS = (1000, 2000)
OUTPUT_DIR = MODEL_DIR / "transformer_production"


def build_priority_pool() -> dict[str, list[str]]:
    """儿科样本排前、内科样本排后，采样时自然实现'儿科优先、内科补足'。"""
    import random

    pediatric = build_augmented_pool((QA_PATH,))
    combined = build_augmented_pool((QA_PATH, INTERNAL_QA_PATH))
    rng = random.Random(RANDOM_STATE)
    pool: dict[str, list[str]] = {}
    for label, texts in combined.items():
        pediatric_set = set(pediatric.get(label, []))
        first = [text for text in texts if text in pediatric_set]
        rest = [text for text in texts if text not in pediatric_set]
        rng.shuffle(first)
        rng.shuffle(rest)
        pool[label] = first + rest
    return pool


def train_condition(
    cap: int,
    pool: dict[str, list[str]],
    splits: dict[str, tuple[list[str], list[str]]],
    device: torch.device,
    tokenizer,
) -> dict[str, object]:
    torch.manual_seed(RANDOM_STATE)
    np.random.seed(RANDOM_STATE)

    train_texts, train_label_names = splits["train"]
    train_texts = list(train_texts)
    train_label_names = list(train_label_names)
    added = {}
    for label, texts in pool.items():
        take = texts[: min(cap, len(texts))]
        train_texts.extend(take)
        train_label_names.extend([label] * len(take))
        added[label] = len(take)

    labels = sorted(set(train_label_names))
    label_to_id = {label: index for index, label in enumerate(labels)}
    train_labels = np.array([label_to_id[name] for name in train_label_names])
    dev_labels = np.array([label_to_id[name] for name in splits["dev"][1]])
    test_labels = np.array([label_to_id[name] for name in splits["test"][1]])

    model = AutoModelForSequenceClassification.from_pretrained(
        PRETRAINED,
        num_labels=len(labels),
        id2label={index: label for label, index in label_to_id.items()},
        label2id=label_to_id,
    ).to(device)

    counts = np.bincount(train_labels, minlength=len(labels))
    class_weights = torch.tensor(
        len(train_labels) / (len(labels) * counts), dtype=torch.float32, device=device
    )
    criterion = torch.nn.CrossEntropyLoss(weight=class_weights)
    optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    steps_per_epoch = int(np.ceil(len(train_texts) / BATCH_SIZE))
    total_steps = steps_per_epoch * EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)
    scheduler = LambdaLR(
        optimizer,
        lambda step: step / max(1, warmup_steps)
        if step < warmup_steps
        else max(0.0, (total_steps - step) / max(1, total_steps - warmup_steps)),
    )
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    generator = np.random.default_rng(RANDOM_STATE)

    best_dev_f1 = -1.0
    best_state: dict | None = None
    history: list[dict[str, object]] = []
    started = time.perf_counter()

    for epoch in range(1, EPOCHS + 1):
        model.train()
        epoch_loss = 0.0
        for chunk, chunk_labels in batches(
            train_texts, train_labels, BATCH_SIZE, shuffle=True, generator=generator
        ):
            encoded = tokenizer(
                chunk, truncation=True, max_length=MAX_LENGTH, padding=True, return_tensors="pt"
            ).to(device)
            targets = torch.tensor(chunk_labels, dtype=torch.long, device=device)
            optimizer.zero_grad()
            with torch.amp.autocast("cuda", enabled=device.type == "cuda"):
                loss = criterion(model(**encoded).logits, targets)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            epoch_loss += float(loss.detach())

        dev_metrics = _metrics(dev_labels, predict(model, tokenizer, splits["dev"][0], device))
        history.append(
            {"epoch": epoch, "trainLoss": round(epoch_loss / steps_per_epoch, 4), **dev_metrics}
        )
        print(f"[cap={cap}] epoch {epoch}: loss={history[-1]['trainLoss']} dev={dev_metrics}")
        if dev_metrics["macroF1"] > best_dev_f1:
            best_dev_f1 = dev_metrics["macroF1"]
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    model.to(device)
    test_predictions = predict(model, tokenizer, splits["test"][0], device)
    test_metrics = _metrics(test_labels, test_predictions)
    report = classification_report(
        test_labels,
        test_predictions,
        target_names=labels,
        output_dict=True,
        zero_division=0,
    )
    result = {
        "cap": cap,
        "addedPerClass": added,
        "trainSize": len(train_texts),
        "trainingSeconds": round(time.perf_counter() - started, 1),
        "history": history,
        "bestDevMacroF1": best_dev_f1,
        "test": test_metrics,
        "testReport": report,
    }
    del model
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return result, best_state, labels, label_to_id


def main() -> None:
    splits = {name: load_split(name) for name in ("train", "dev", "test")}
    pool = build_priority_pool()
    print("双源弱标签池:", json.dumps({k: len(v) for k, v in pool.items()}, ensure_ascii=False))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(PRETRAINED)

    conditions = []
    best = None
    for cap in CLASS_CAPS:
        result, state, labels, label_to_id = train_condition(cap, pool, splits, device, tokenizer)
        conditions.append(result)
        if best is None or result["bestDevMacroF1"] > best[0]["bestDevMacroF1"]:
            best = (result, state, labels, label_to_id)

    result, state, labels, label_to_id = best
    model = AutoModelForSequenceClassification.from_pretrained(
        PRETRAINED,
        num_labels=len(labels),
        id2label={index: label for label, index in label_to_id.items()},
        label2id=label_to_id,
    )
    model.load_state_dict(state)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    model.to(device).eval()
    gpu_latency = (
        measure_latency(model, tokenizer, splits["test"][0], device)
        if device.type == "cuda"
        else None
    )
    cpu_latency = measure_latency(model.to(torch.device("cpu")), tokenizer, splits["test"][0], torch.device("cpu"))

    metrics = {
        "modelName": "bert-base-chinese-finetuned-production",
        "selection": "best dev macro-F1 across caps; test never used for selection",
        "weakPoolSizes": {k: len(v) for k, v in pool.items()},
        "conditions": conditions,
        "selectedCap": result["cap"],
        "selectedTest": result["test"],
        "latencyMsPerSample": {"gpu": gpu_latency, "cpu": cpu_latency},
        "labels": labels,
        "outputDir": str(OUTPUT_DIR),
    }
    (MODEL_DIR / "transformer_production_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

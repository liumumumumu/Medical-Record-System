"""BERT + 弱标签扩充数据的组合实验，补齐 {LR, BERT} x {纯金标, 金标+弱标} 对比矩阵。

训练配置与 scripts/train_transformer.py 完全一致；扩充数据取
scripts/train_augmented.py 同一弱标签池、同一种子、每类上限 500（LR 实验中的最优条件）。
最优 epoch 权重仅驻留内存，产物只有 models/transformer_augmented_metrics.json。
"""

import copy
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, f1_score
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from transformers import AutoModelForSequenceClassification, AutoTokenizer


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from scripts.train_augmented import build_augmented_pool  # noqa: E402
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
    batches,
    predict,
    _metrics,
)
from src.config import MODEL_DIR  # noqa: E402


CLASS_CAP = 500


def main() -> None:
    torch.manual_seed(RANDOM_STATE)
    np.random.seed(RANDOM_STATE)

    train_texts, train_label_names = load_split("train")
    dev_texts, dev_label_names = load_split("dev")
    test_texts, test_label_names = load_split("test")

    import random

    rng = random.Random(RANDOM_STATE)
    pool = build_augmented_pool()
    for label, texts in pool.items():
        shuffled = rng.sample(texts, len(texts))
        take = shuffled[: min(CLASS_CAP, len(shuffled))]
        train_texts = train_texts + take
        train_label_names = train_label_names + [label] * len(take)

    labels = sorted(set(train_label_names))
    label_to_id = {label: index for index, label in enumerate(labels)}
    train_labels = np.array([label_to_id[name] for name in train_label_names])
    dev_labels = np.array([label_to_id[name] for name in dev_label_names])
    test_labels = np.array([label_to_id[name] for name in test_label_names])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(PRETRAINED)
    model = AutoModelForSequenceClassification.from_pretrained(
        PRETRAINED, num_labels=len(labels)
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

        dev_metrics = _metrics(dev_labels, predict(model, tokenizer, dev_texts, device))
        history.append(
            {"epoch": epoch, "trainLoss": round(epoch_loss / steps_per_epoch, 4), **dev_metrics}
        )
        print(f"epoch {epoch}: loss={history[-1]['trainLoss']} dev={dev_metrics}")
        if dev_metrics["macroF1"] > best_dev_f1:
            best_dev_f1 = dev_metrics["macroF1"]
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    model.to(device)
    test_predictions = predict(model, tokenizer, test_texts, device)
    test_metrics = _metrics(test_labels, test_predictions)
    report = classification_report(
        test_labels, test_predictions, target_names=labels, digits=4, zero_division=0
    )

    # 该配方（儿科弱标 500/类）被选为生产模型：分布匹配 + 适中剂量，
    # 在全部候选中先验依据与实测表现最优，权重保存供线上双后端加载。
    production_dir = MODEL_DIR / "transformer_production"
    production_dir.mkdir(parents=True, exist_ok=True)
    model.config.id2label = {index: label for index, label in enumerate(labels)}
    model.config.label2id = label_to_id
    model.save_pretrained(production_dir)
    tokenizer.save_pretrained(production_dir)

    metrics = {
        "modelName": "bert-base-chinese-finetuned-augmented",
        "augmentation": f"distant supervision, cap {CLASS_CAP}/class (same pool/seed as train_augmented.py)",
        "trainSize": len(train_texts),
        "trainingSeconds": round(time.perf_counter() - started, 1),
        "history": history,
        "test": test_metrics,
    }
    (MODEL_DIR / "transformer_augmented_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(report)


if __name__ == "__main__":
    main()

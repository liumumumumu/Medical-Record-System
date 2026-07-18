"""Two-stage fine-tuning for the Chinese Transformer record generator."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import sys
import time
from typing import Any


AI_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(AI_ROOT))

from src.config import RECORD_MODEL_DIR, RECORD_MODEL_NAME, RECORD_MODEL_VERSION  # noqa: E402
from src.record_generation_metrics import evaluate_generation  # noqa: E402
from src.record_generator import sanitize_generated_text  # noqa: E402


BASE_MODEL_REVISION = "06d379d7375245f31cfb87166eff134cfeb5dead"
TAGS = ["<主诉>", "<现病史>", "<既往史>", "<辅助检查>"]


@dataclass(frozen=True)
class TrainingConfig:
    base_model: str
    base_revision: str
    model_version: str
    source_max_length: int
    target_max_length: int
    batch_size: int
    gradient_accumulation: int
    learning_rate: float
    warmup_ratio: float
    weak_epochs: int
    gold_epochs: int
    patience: int
    seed: int
    generation_beams: int
    fp16: bool
    bf16: bool


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="训练 Transformer 病历生成模型")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / "dataset" / "derived" / "record-generation-v1",
    )
    parser.add_argument("--output-dir", type=Path, default=RECORD_MODEL_DIR)
    parser.add_argument("--base-model", default=RECORD_MODEL_NAME)
    parser.add_argument("--revision", default=BASE_MODEL_REVISION)
    parser.add_argument("--source-max-length", type=int, default=768)
    parser.add_argument("--target-max-length", type=int, default=320)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=3e-5)
    parser.add_argument("--warmup-ratio", type=float, default=0.10)
    parser.add_argument("--weak-epochs", type=int, default=1)
    parser.add_argument("--gold-epochs", type=int, default=5)
    parser.add_argument("--patience", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-beams", type=int, default=4)
    parser.add_argument("--weak-limit", type=int)
    parser.add_argument("--gold-limit", type=int)
    parser.add_argument("--dev-limit", type=int)
    parser.add_argument("--skip-weak", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--quick-smoke", action="store_true")
    return parser.parse_args()


def load_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
                if limit is not None and len(records) >= limit:
                    break
    if not records:
        raise RuntimeError(f"训练文件为空：{path}")
    return records


def seed_everything(seed: int, torch: Any) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except AttributeError:
        pass


class TokenizedDataset:
    def __init__(
        self,
        records: list[dict[str, Any]],
        tokenizer: Any,
        source_max_length: int,
        target_max_length: int,
    ) -> None:
        self.records = records
        self.tokenizer = tokenizer
        self.source_max_length = source_max_length
        self.target_max_length = target_max_length

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        row = self.records[index]
        encoded = self.tokenizer(
            str(row["source"]),
            truncation=True,
            max_length=self.source_max_length,
        )
        target = self.tokenizer(
            text_target=str(row["target"]),
            truncation=True,
            max_length=self.target_max_length,
        )
        encoded["labels"] = target["input_ids"]
        return encoded


def save_model(model: Any, tokenizer: Any, output_dir: Path, metadata: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)
    (output_dir / "record_generator_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def train_stage(
    *,
    stage: str,
    model: Any,
    tokenizer: Any,
    records: list[dict[str, Any]],
    epochs: int,
    config: TrainingConfig,
    device: str,
    torch: Any,
    DataLoader: Any,
    DataCollatorForSeq2Seq: Any,
    get_linear_schedule_with_warmup: Any,
) -> list[dict[str, float]]:
    dataset = TokenizedDataset(
        records,
        tokenizer,
        config.source_max_length,
        config.target_max_length,
    )
    collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True,
        label_pad_token_id=-100,
        return_tensors="pt",
    )
    generator = torch.Generator()
    generator.manual_seed(config.seed + (0 if stage == "weak" else 10_000))
    loader = DataLoader(
        dataset,
        batch_size=config.batch_size,
        shuffle=True,
        collate_fn=collator,
        generator=generator,
        num_workers=0,
        pin_memory=device == "cuda",
    )
    update_steps_per_epoch = math.ceil(len(loader) / config.gradient_accumulation)
    total_updates = max(update_steps_per_epoch * epochs, 1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=0.01)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(int(total_updates * config.warmup_ratio), 1),
        num_training_steps=total_updates,
    )
    scaler = torch.amp.GradScaler("cuda", enabled=device == "cuda" and config.fp16)
    history: list[dict[str, float]] = []
    optimizer.zero_grad(set_to_none=True)
    model.train()
    model.config.use_cache = False
    last_reported_update = 0

    for epoch in range(1, epochs + 1):
        started = time.perf_counter()
        running_loss = 0.0
        update_count = 0
        for batch_index, batch in enumerate(loader, start=1):
            batch = {name: tensor.to(device, non_blocking=True) for name, tensor in batch.items()}
            autocast_dtype = torch.bfloat16 if config.bf16 else torch.float16
            autocast = (
                torch.amp.autocast(device_type="cuda", dtype=autocast_dtype)
                if device == "cuda" and (config.fp16 or config.bf16)
                else nullcontext()
            )
            with autocast:
                outputs = model(**batch)
                if not torch.isfinite(outputs.loss):
                    raise RuntimeError(
                        f"{stage} 第 {epoch} 轮出现非有限损失；停止训练以避免保存损坏权重"
                    )
                loss = outputs.loss / config.gradient_accumulation
            scaler.scale(loss).backward()
            running_loss += float(outputs.loss.detach().cpu())
            should_update = (
                batch_index % config.gradient_accumulation == 0 or batch_index == len(loader)
            )
            if not should_update:
                continue
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scale_before_step = scaler.get_scale()
            scaler.step(optimizer)
            scaler.update()
            optimizer_stepped = not scaler.is_enabled() or scaler.get_scale() >= scale_before_step
            if optimizer_stepped:
                scheduler.step()
            optimizer.zero_grad(set_to_none=True)
            update_count += int(optimizer_stepped)
            if update_count != last_reported_update and (
                update_count % 25 == 0 or update_count == update_steps_per_epoch
            ):
                last_reported_update = update_count
                print(
                    json.dumps(
                        {
                            "stage": stage,
                            "epoch": epoch,
                            "updates": update_count,
                            "updatesTotal": update_steps_per_epoch,
                            "meanLoss": running_loss / batch_index,
                            "learningRate": scheduler.get_last_lr()[0],
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
        history.append(
            {
                "epoch": float(epoch),
                "meanLoss": running_loss / max(len(loader), 1),
                "seconds": time.perf_counter() - started,
            }
        )
    return history


def decode_generated(tokenizer: Any, token_ids: Any) -> str:
    value = tokenizer.decode(token_ids, skip_special_tokens=False)
    for token in (tokenizer.pad_token, tokenizer.eos_token, tokenizer.bos_token):
        if token:
            value = value.replace(token, "")
    return sanitize_generated_text(value)


def evaluate(
    model: Any,
    tokenizer: Any,
    records: list[dict[str, Any]],
    config: TrainingConfig,
    device: str,
    torch: Any,
    predictions_path: Path,
) -> dict[str, float]:
    predictions: list[str] = []
    references: list[list[str]] = []
    sources: list[str] = []
    model.eval()
    model.config.use_cache = True
    started = time.perf_counter()
    with torch.inference_mode():
        for start in range(0, len(records), config.batch_size):
            batch_rows = records[start : start + config.batch_size]
            encoded = tokenizer(
                [str(row["source"]) for row in batch_rows],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=config.source_max_length,
            )
            encoded = {name: tensor.to(device) for name, tensor in encoded.items()}
            generated = model.generate(
                **encoded,
                max_length=config.target_max_length,
                num_beams=config.generation_beams,
                early_stopping=True,
            )
            predictions.extend(decode_generated(tokenizer, item) for item in generated)
            references.extend(
                [[str(value) for value in row.get("targets") or [row["target"]]]
                for row in batch_rows
                ]
            )
            sources.extend(str(row["source"]) for row in batch_rows)
    metrics = evaluate_generation(predictions, references, sources)
    metrics["seconds"] = time.perf_counter() - started
    metrics["samplesPerSecond"] = len(records) / max(metrics["seconds"], 1e-9)
    predictions_path.parent.mkdir(parents=True, exist_ok=True)
    with predictions_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row, prediction in zip(records, predictions, strict=True):
            handle.write(
                json.dumps(
                    {
                        "id": row["id"],
                        "prediction": prediction,
                        "references": row.get("targets") or [row["target"]],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    model.train()
    model.config.use_cache = False
    return metrics


def main() -> None:
    args = arguments()
    if args.quick_smoke:
        args.weak_limit = args.weak_limit or 64
        args.gold_limit = args.gold_limit or 64
        args.dev_limit = args.dev_limit or 16
        args.weak_epochs = 0 if args.skip_weak else 1
        args.gold_epochs = 1
        args.patience = 1

    try:
        import torch
        from torch.utils.data import DataLoader
        from transformers import (
            AutoModelForSeq2SeqLM,
            AutoTokenizer,
            DataCollatorForSeq2Seq,
            get_linear_schedule_with_warmup,
        )
    except ImportError as error:
        raise SystemExit(
            "缺少训练依赖。请先安装 requirements-generation.txt 中的依赖。"
        ) from error

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device != "cuda" and not args.allow_cpu:
        raise SystemExit("未检测到 CUDA；如仅做流程验证，请显式传入 --allow-cpu")
    seed_everything(args.seed, torch)
    config = TrainingConfig(
        base_model=args.base_model,
        base_revision=args.revision,
        model_version=RECORD_MODEL_VERSION,
        source_max_length=args.source_max_length,
        target_max_length=args.target_max_length,
        batch_size=args.batch_size,
        gradient_accumulation=args.gradient_accumulation,
        learning_rate=args.learning_rate,
        warmup_ratio=args.warmup_ratio,
        weak_epochs=args.weak_epochs,
        gold_epochs=args.gold_epochs,
        patience=args.patience,
        seed=args.seed,
        generation_beams=args.num_beams,
        fp16=device == "cuda" and not torch.cuda.is_bf16_supported(),
        bf16=device == "cuda" and torch.cuda.is_bf16_supported(),
    )
    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.resolve()
    weak_train = load_jsonl(data_dir / "weak_train.jsonl", args.weak_limit)
    gold_train = load_jsonl(data_dir / "gold_train.jsonl", args.gold_limit)
    gold_dev = load_jsonl(data_dir / "gold_dev.jsonl", args.dev_limit)

    print(
        json.dumps(
            {
                "device": device,
                "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
                "weakTrain": len(weak_train),
                "goldTrain": len(gold_train),
                "goldDev": len(gold_dev),
                "output": str(output_dir),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        config.base_model,
        revision=config.base_revision,
        use_fast=False,
    )
    model = AutoModelForSeq2SeqLM.from_pretrained(
        config.base_model,
        revision=config.base_revision,
    )
    added_tokens = tokenizer.add_special_tokens({"additional_special_tokens": TAGS})
    if added_tokens:
        # This checkpoint stores distinct shared/lm_head weights. Mean/covariance
        # resizing can produce NaNs for the four new Chinese structure tags.
        model.config.tie_word_embeddings = False
        model.resize_token_embeddings(len(tokenizer), mean_resizing=False)
    model.gradient_checkpointing_enable()
    model.to(device)

    run_started = datetime.now(timezone.utc).isoformat()
    history: dict[str, Any] = {"weak": [], "gold": [], "dev": []}
    if config.weak_epochs:
        history["weak"] = train_stage(
            stage="weak",
            model=model,
            tokenizer=tokenizer,
            records=weak_train,
            epochs=config.weak_epochs,
            config=config,
            device=device,
            torch=torch,
            DataLoader=DataLoader,
            DataCollatorForSeq2Seq=DataCollatorForSeq2Seq,
            get_linear_schedule_with_warmup=get_linear_schedule_with_warmup,
        )
        save_model(
            model,
            tokenizer,
            output_dir / "stage_weak",
            {"stage": "weak", "config": asdict(config), "completedAt": datetime.now(timezone.utc).isoformat()},
        )

    best_rouge_l = -1.0
    epochs_without_improvement = 0
    for epoch in range(1, config.gold_epochs + 1):
        epoch_config = TrainingConfig(**{**asdict(config), "gold_epochs": 1})
        train_history = train_stage(
            stage=f"gold-{epoch}",
            model=model,
            tokenizer=tokenizer,
            records=gold_train,
            epochs=1,
            config=epoch_config,
            device=device,
            torch=torch,
            DataLoader=DataLoader,
            DataCollatorForSeq2Seq=DataCollatorForSeq2Seq,
            get_linear_schedule_with_warmup=get_linear_schedule_with_warmup,
        )
        history["gold"].extend(train_history)
        dev_metrics = evaluate(
            model,
            tokenizer,
            gold_dev,
            config,
            device,
            torch,
            output_dir / "evaluation" / f"dev_predictions_epoch_{epoch}.jsonl",
        )
        dev_metrics["epoch"] = float(epoch)
        history["dev"].append(dev_metrics)
        print(json.dumps({"goldEpoch": epoch, "dev": dev_metrics}, ensure_ascii=False), flush=True)
        if dev_metrics["rougeL"] > best_rouge_l:
            best_rouge_l = dev_metrics["rougeL"]
            epochs_without_improvement = 0
            save_model(
                model,
                tokenizer,
                output_dir,
                {
                    "stage": "gold-best",
                    "bestEpoch": epoch,
                    "bestDevMetrics": dev_metrics,
                    "config": asdict(config),
                    "baseModelRevision": config.base_revision,
                    "completedAt": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= config.patience:
                print(f"dev ROUGE-L 连续 {config.patience} 轮未提升，提前停止", flush=True)
                break

    metrics = {
        "modelVersion": RECORD_MODEL_VERSION,
        "startedAt": run_started,
        "completedAt": datetime.now(timezone.utc).isoformat(),
        "device": device,
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "config": asdict(config),
        "dataCounts": {
            "weakTrain": len(weak_train),
            "goldTrain": len(gold_train),
            "goldDev": len(gold_dev),
        },
        "bestDevRougeL": best_rouge_l,
        "history": history,
    }
    metrics_text = json.dumps(metrics, ensure_ascii=False, indent=2) + "\n"
    (output_dir / "training_metrics.json").write_text(metrics_text, encoding="utf-8")
    artifact = AI_ROOT / "artifacts" / "record-generation-v1" / "training_metrics.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(metrics_text, encoding="utf-8")
    print(json.dumps({"bestDevRougeL": best_rouge_l, "output": str(output_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

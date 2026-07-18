"""Fine-tune the best checkpoint on runtime-shaped structured inputs."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


AI_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(AI_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import RECORD_MODEL_DIR, RECORD_MODEL_VERSION  # noqa: E402
from train_record_generator import (  # noqa: E402
    TrainingConfig,
    evaluate,
    load_jsonl,
    save_model,
    seed_everything,
    train_stage,
)


CANDIDATE_VERSION = RECORD_MODEL_VERSION


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="病历生成结构字段对齐微调")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / "dataset" / "derived" / "record-generation-v1",
    )
    parser.add_argument("--base-dir", type=Path, default=RECORD_MODEL_DIR)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=AI_ROOT / "models" / "record_generator_alignment",
    )
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--gradient-accumulation", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--train-file", default="alignment_train.jsonl")
    parser.add_argument("--train-limit", type=int)
    parser.add_argument("--dev-limit", type=int)
    return parser.parse_args()


def main() -> None:
    args = arguments()
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
        raise SystemExit("缺少 torch/transformers 病历生成依赖") from error
    if not torch.cuda.is_available():
        raise SystemExit("结构对齐正式训练要求 CUDA GPU")

    base_dir = args.base_dir.resolve()
    metadata = json.loads(
        (base_dir / "record_generator_metadata.json").read_text(encoding="utf-8")
    )
    saved = dict(metadata["config"])
    saved.update(
        {
            "model_version": CANDIDATE_VERSION,
            "batch_size": args.batch_size,
            "gradient_accumulation": args.gradient_accumulation,
            "learning_rate": args.learning_rate,
            "weak_epochs": 0,
            "gold_epochs": args.epochs,
            "patience": 1,
            "fp16": False,
            "bf16": bool(torch.cuda.is_bf16_supported()),
        }
    )
    config = TrainingConfig(**saved)
    seed_everything(config.seed + 1, torch)
    tokenizer = AutoTokenizer.from_pretrained(base_dir, local_files_only=True, use_fast=False)
    model = AutoModelForSeq2SeqLM.from_pretrained(base_dir, local_files_only=True)
    model.config.tie_word_embeddings = False
    model.gradient_checkpointing_enable()
    device = "cuda"
    model.to(device)

    data_dir = args.data_dir.resolve()
    train = load_jsonl(data_dir / args.train_file, args.train_limit)
    dev = load_jsonl(data_dir / "alignment_dev.jsonl", args.dev_limit)
    started = datetime.now(timezone.utc).isoformat()
    history = train_stage(
        stage="alignment",
        model=model,
        tokenizer=tokenizer,
        records=train,
        epochs=args.epochs,
        config=config,
        device=device,
        torch=torch,
        DataLoader=DataLoader,
        DataCollatorForSeq2Seq=DataCollatorForSeq2Seq,
        get_linear_schedule_with_warmup=get_linear_schedule_with_warmup,
    )
    output_dir = args.output_dir.resolve()
    dev_metrics = evaluate(
        model,
        tokenizer,
        dev,
        config,
        device,
        torch,
        output_dir / "evaluation" / "alignment_dev_predictions.jsonl",
    )
    metadata_out: dict[str, Any] = {
        "stage": "runtime-alignment",
        "baseCheckpoint": str(base_dir),
        "modelVersion": CANDIDATE_VERSION,
        "config": asdict(config),
        "dataCounts": {"train": len(train), "dev": len(dev)},
        "trainFile": args.train_file,
        "history": history,
        "alignmentDevMetrics": dev_metrics,
        "startedAt": started,
        "completedAt": datetime.now(timezone.utc).isoformat(),
    }
    save_model(model, tokenizer, output_dir, metadata_out)
    text = json.dumps(metadata_out, ensure_ascii=False, indent=2) + "\n"
    (output_dir / "alignment_training_metrics.json").write_text(text, encoding="utf-8")
    artifact = AI_ROOT / "artifacts" / "record-generation-v1" / "alignment_training_metrics.json"
    artifact.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

"""Evaluate the saved best checkpoint on the untouched IMCS-21 test split."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


AI_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(AI_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import RECORD_MODEL_DIR, RECORD_MODEL_VERSION  # noqa: E402
from train_record_generator import TrainingConfig, evaluate, load_jsonl  # noqa: E402


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="评估病历生成模型")
    parser.add_argument("--model-dir", type=Path, default=RECORD_MODEL_DIR)
    parser.add_argument(
        "--data-file",
        type=Path,
        default=ROOT / "dataset" / "derived" / "record-generation-v1" / "gold_test.jsonl",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--batch-size", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as error:
        raise SystemExit("缺少 torch/transformers 病历生成依赖") from error

    model_dir = args.model_dir.resolve()
    metadata_path = model_dir / "record_generator_metadata.json"
    if not metadata_path.exists():
        raise SystemExit(f"模型元数据不存在：{metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    saved = dict(metadata["config"])
    saved["batch_size"] = args.batch_size
    config = TrainingConfig(**saved)
    records = load_jsonl(args.data_file.resolve(), args.limit)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True, use_fast=False)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_dir, local_files_only=True)
    if device == "cuda":
        model = model.bfloat16() if torch.cuda.is_bf16_supported() else model.half()
    model.to(device)
    metrics = evaluate(
        model,
        tokenizer,
        records,
        config,
        device,
        torch,
        model_dir / "evaluation" / "test_predictions.jsonl",
    )
    result = {
        "modelVersion": RECORD_MODEL_VERSION,
        "evaluatedAt": datetime.now(timezone.utc).isoformat(),
        "dataFile": str(args.data_file.resolve()),
        "device": device,
        "config": asdict(config),
        "metrics": metrics,
        "acceptanceTargets": {
            "rougeLAtLeast0.45": metrics["rougeL"] >= 0.45,
            "bleu2AtLeast0.45": metrics["bleu2"] >= 0.45,
            "parseRateAtLeast0.98": metrics["parseRate"] >= 0.98,
            "numericConsistencyAtLeast0.99": metrics["numericConsistency"] >= 0.99,
            "criticalTermConsistencyAtLeast0.90": metrics["criticalTermConsistency"] >= 0.90,
        },
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    (model_dir / "test_metrics.json").write_text(text, encoding="utf-8")
    artifact = AI_ROOT / "artifacts" / "record-generation-v1" / "test_metrics.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

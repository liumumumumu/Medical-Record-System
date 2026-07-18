"""Prepare reproducible gold/weak datasets for Chinese medical-record generation.

The script keeps the official IMCS-21 dev/test split intact, filters CBLUE mirror
examples against those holdouts, and uses Toyhom dialogues only as weak labels.
It never derives a diagnosis, medication, or treatment fact that was not written
in the source row.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
from typing import Iterable, Iterator


ROOT = Path(__file__).resolve().parents[3]
AI_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_ROOT = ROOT / "dataset"
DEFAULT_OUTPUT = DEFAULT_DATASET_ROOT / "derived" / "record-generation-v1"
DEFAULT_MANIFEST_COPY = AI_ROOT / "artifacts" / "record-generation-v1" / "manifest.json"
SECTIONS = ("主诉", "现病史", "既往史", "辅助检查")
BASE_TASK = (
    "任务：只整理输入中明确出现的事实，生成精简住院病历的四个叙述段；"
    "不得补充疾病、药物、检查数值或治疗。缺失项写‘未提供’。\n"
    "输出格式：<主诉>...<现病史>...<既往史>...<辅助检查>..."
)
REPORT_SECTION_PATTERN = re.compile(
    r"(?:^|\n)(主诉|现病史|既往史|辅助检查)[：:][ \t]*(.*?)(?=\n(?:主诉|现病史|既往史|辅助检查|诊断|建议)[：:]|$)",
    re.DOTALL,
)
SPLIT_PATTERN = re.compile(r"(?<=[。！？；])")
PHONE_PATTERN = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
ID_PATTERN = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
URL_PATTERN = re.compile(r"https?://\S+")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建病历生成训练集")
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest-copy", type=Path, default=DEFAULT_MANIFEST_COPY)
    parser.add_argument("--weak-per-domain", type=int, default=3_000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def clean_text(value: object, default: str = "未提供") -> str:
    text = str(value or "").replace("\x00", "").strip()
    text = re.sub(r"[\t\r ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    missing_key = re.sub(r"[\s。.!！?？；;：:]", "", text)
    if not text or missing_key in {"不详", "暂缺", "无记录", "未知", "none", "None"}:
        return default
    return text


def deidentify(value: object) -> str:
    text = clean_text(value, "")
    text = PHONE_PATTERN.sub("[手机号已脱敏]", text)
    text = ID_PATTERN.sub("[证件号已脱敏]", text)
    text = EMAIL_PATTERN.sub("[邮箱已脱敏]", text)
    return URL_PATTERN.sub("[链接已脱敏]", text)


def canonical(value: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", value).lower()


def digest_text(value: str) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def format_target(sections: dict[str, object]) -> str:
    return "".join(f"<{name}>{clean_text(sections.get(name))}" for name in SECTIONS)


def make_record(
    *,
    identifier: str,
    source: str,
    target: str,
    targets: list[str] | None,
    source_dataset: str,
    quality_tier: str,
    split: str,
    department: str = "",
    original_id: str = "",
) -> dict[str, object]:
    return {
        "id": identifier,
        "source": source,
        "target": target,
        "targets": targets or [target],
        "sourceDataset": source_dataset,
        "qualityTier": quality_tier,
        "trainingStage": "weak" if quality_tier == "weak" else "gold",
        "split": split,
        "department": department,
        "originalId": original_id or identifier,
    }


def imcs_source(case: dict[str, object]) -> str:
    dialogue = case.get("dialogue") or []
    turns = []
    for turn in dialogue if isinstance(dialogue, list) else []:
        if not isinstance(turn, dict) or turn.get("dialogue_act") == "Other":
            continue
        sentence = deidentify(turn.get("sentence"))
        if sentence:
            turns.append(f"{clean_text(turn.get('speaker'), '未知')}：{sentence}")
    self_report = deidentify(case.get("self_report"))
    return f"{BASE_TASK}\n[患者自述]{self_report or '未提供'}\n[问诊与治疗记录]\n" + "\n".join(turns)


def read_imcs(dataset_root: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[Path]]:
    folder = dataset_root / "IMCS-21" / "dataset"
    outputs: dict[str, list[dict[str, object]]] = {"train": [], "dev": [], "test": []}
    paths: list[Path] = []
    for split in ("train", "dev", "test"):
        path = folder / f"{split}.json"
        paths.append(path)
        cases = json.loads(path.read_text(encoding="utf-8"))
        for case_id, case in cases.items():
            reports = case.get("report") or []
            if isinstance(reports, dict):
                reports = [reports]
            targets = [format_target(report) for report in reports if isinstance(report, dict)]
            if not targets:
                continue
            source = imcs_source(case)
            if split == "train":
                for ref_index, target in enumerate(targets, start=1):
                    outputs[split].append(
                        make_record(
                            identifier=f"imcs-{case_id}-r{ref_index}",
                            source=source,
                            target=target,
                            targets=targets,
                            source_dataset="IMCS-21",
                            quality_tier="gold",
                            split=split,
                            department="儿科",
                            original_id=str(case_id),
                        )
                    )
            else:
                outputs[split].append(
                    make_record(
                        identifier=f"imcs-{case_id}",
                        source=source,
                        target=targets[0],
                        targets=targets,
                        source_dataset="IMCS-21",
                        quality_tier="gold",
                        split=split,
                        department="儿科",
                        original_id=str(case_id),
                    )
                )
    return outputs["train"], outputs["dev"], outputs["test"], paths


def parse_cblue_target(text: str) -> str | None:
    sections = {name: clean_text(value) for name, value in REPORT_SECTION_PATTERN.findall(text)}
    if not all(name in sections for name in SECTIONS):
        return None
    return format_target(sections)


def read_cblue(
    dataset_root: Path,
    holdout_hashes: set[str],
) -> tuple[list[dict[str, object]], Path, dict[str, int]]:
    path = dataset_root / "CBLUE_mirrors" / "chinese-med" / "train.json"
    records: list[dict[str, object]] = []
    stats = Counter()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("task_type") != "report_generation":
                continue
            stats["report_generation_seen"] += 1
            target = parse_cblue_target(clean_text(row.get("target"), ""))
            if not target:
                stats["invalid_target"] += 1
                continue
            if digest_text(target) in holdout_hashes:
                stats["holdout_duplicate_removed"] += 1
                continue
            source = clean_text(row.get("input"), "")
            identifier = f"cblue-{row.get('sample_id') or stats['report_generation_seen']}"
            records.append(
                make_record(
                    identifier=identifier,
                    source=f"{BASE_TASK}\n[问诊与治疗记录]\n{source}",
                    target=target,
                    targets=[target],
                    source_dataset="CBLUE-IMCS-V2-MRG",
                    quality_tier="gold",
                    split="train",
                    department="儿科",
                    original_id=str(row.get("sample_id") or ""),
                )
            )
    stats["kept"] = len(records)
    return records, path, dict(stats)


def open_csv(path: Path):
    for encoding in ("utf-8-sig", "gb18030"):
        handle = path.open("r", encoding=encoding, newline="")
        try:
            handle.readline()
            handle.seek(0)
            return handle
        except UnicodeDecodeError:
            handle.close()
    raise UnicodeError(f"无法识别 CSV 编码：{path}")


def valid_dialogue_rows(path: Path) -> Iterator[dict[str, str]]:
    with open_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ask = deidentify(row.get("ask") or row.get("question"))
            title = deidentify(row.get("title"))
            if not ask or not title:
                continue
            yield {
                "department": clean_text(row.get("department"), ""),
                "title": title,
                "ask": ask,
                "answer": deidentify(row.get("answer")),
            }


def reservoir(path: Path, size: int, rng: random.Random) -> tuple[list[dict[str, str]], int]:
    sample: list[dict[str, str]] = []
    seen = 0
    for row in valid_dialogue_rows(path):
        seen += 1
        if len(sample) < size:
            sample.append(row)
            continue
        candidate = rng.randrange(seen)
        if candidate < size:
            sample[candidate] = row
    return sample, seen


def explicit_sentences(text: str, keywords: tuple[str, ...]) -> str:
    sentences = [piece.strip() for piece in SPLIT_PATTERN.split(text) if piece.strip()]
    matches = [sentence for sentence in sentences if any(word in sentence for word in keywords)]
    return "".join(matches[:3]) if matches else "未提供"


def weak_target(row: dict[str, str]) -> str:
    ask = row["ask"]
    sections = {
        "主诉": row["title"][:160],
        "现病史": ask[:1_600],
        "既往史": explicit_sentences(
            ask,
            ("既往", "以前", "曾经", "病史", "手术史", "患有", "确诊", "多年"),
        ),
        "辅助检查": explicit_sentences(
            ask,
            ("检查", "化验", "血常规", "胸片", "彩超", "B超", "CT", "核磁", "结果", "显示", "提示", "报告"),
        ),
    }
    return format_target(sections)


def stable_weak_split(identifier: str) -> str:
    return "dev" if int(hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:8], 16) % 20 == 0 else "train"


def read_weak(
    dataset_root: Path,
    per_domain: int,
    seed: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[Path], dict[str, int]]:
    root = dataset_root / "external" / "Chinese-medical-dialogue-data" / "Data_数据"
    domain_map = {
        "Andriatria_男科": "男科",
        "IM_内科": "内科",
        "OAGD_妇产科": "妇产科",
        "Oncology_肿瘤科": "肿瘤科",
        "Pediatric_儿科": "儿科",
        "Surgical_外科": "外科",
    }
    train: list[dict[str, object]] = []
    dev: list[dict[str, object]] = []
    source_paths: list[Path] = []
    seen_by_domain: dict[str, int] = {}
    for offset, (folder, domain) in enumerate(domain_map.items()):
        csv_paths = sorted((root / folder).glob("*.csv"))
        if len(csv_paths) != 1:
            raise FileNotFoundError(f"{folder} 应包含且仅包含一个 CSV，实际为 {len(csv_paths)}")
        path = csv_paths[0]
        source_paths.append(path)
        rows, seen = reservoir(path, per_domain, random.Random(seed + offset))
        seen_by_domain[domain] = seen
        for index, row in enumerate(rows, start=1):
            identifier = f"toyhom-{domain}-{index:04d}"
            split = stable_weak_split(identifier)
            source = (
                f"{BASE_TASK}\n[科室]{domain}/{row['department'] or '未提供'}"
                f"\n[患者陈述]{row['ask'][:1_800]}"
                f"\n[医患对话答复（仅作上下文，不代表患者已执行）]{row['answer'][:1_200] or '未提供'}"
            )
            record = make_record(
                identifier=identifier,
                source=source,
                target=weak_target(row),
                targets=None,
                source_dataset="Toyhom-Chinese-medical-dialogue-data",
                quality_tier="weak",
                split=split,
                department=domain,
            )
            (dev if split == "dev" else train).append(record)
    return train, dev, source_paths, seen_by_domain


def write_jsonl(path: Path, records: Iterable[dict[str, object]]) -> int:
    materialized = list(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in materialized:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    return len(materialized)


def assert_integrity(
    gold_train: list[dict[str, object]],
    gold_dev: list[dict[str, object]],
    gold_test: list[dict[str, object]],
) -> dict[str, object]:
    ids = {
        split: {
            (row["sourceDataset"], row["originalId"])
            for row in records
            if row["sourceDataset"] == "IMCS-21"
        }
        for split, records in (
            ("train", gold_train),
            ("dev", gold_dev),
            ("test", gold_test),
        )
    }
    overlap = {
        "train_dev": len(ids["train"] & ids["dev"]),
        "train_test": len(ids["train"] & ids["test"]),
        "dev_test": len(ids["dev"] & ids["test"]),
    }
    if any(overlap.values()):
        raise RuntimeError(f"IMCS 官方切分出现病例泄漏：{overlap}")
    malformed = sum(
        not all(f"<{section}>" in str(row["target"]) for section in SECTIONS)
        for records in (gold_train, gold_dev, gold_test)
        for row in records
    )
    if malformed:
        raise RuntimeError(f"发现 {malformed} 条缺少结构标签的金标记录")
    return {"imcsIdOverlap": overlap, "malformedGoldTargets": malformed}


def main() -> None:
    args = arguments()
    dataset_root = args.dataset_root.resolve()
    output = args.output.resolve()

    imcs_train, gold_dev, gold_test, imcs_paths = read_imcs(dataset_root)
    holdout_hashes = {
        digest_text(str(target))
        for row in [*gold_dev, *gold_test]
        for target in row["targets"]
    }
    cblue_train, cblue_path, cblue_stats = read_cblue(dataset_root, holdout_hashes)
    gold_train = [*imcs_train, *cblue_train]
    weak_train, weak_dev, weak_paths, weak_seen = read_weak(
        dataset_root, args.weak_per_domain, args.seed
    )
    integrity = assert_integrity(gold_train, gold_dev, gold_test)

    files = {
        "train.jsonl": [*weak_train, *gold_train],
        "dev.jsonl": gold_dev,
        "test.jsonl": gold_test,
        "weak_train.jsonl": weak_train,
        "weak_dev.jsonl": weak_dev,
        "gold_train.jsonl": gold_train,
        "gold_dev.jsonl": gold_dev,
        "gold_test.jsonl": gold_test,
    }
    output_counts = {name: write_jsonl(output / name, rows) for name, rows in files.items()}
    source_paths = [*imcs_paths, cblue_path, *weak_paths]
    manifest = {
        "schemaVersion": "record-generation-dataset-v1",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "weakSamplesPerDomain": args.weak_per_domain,
        "outputCounts": output_counts,
        "sourceCounts": {
            "IMCS-21-train-expanded-references": len(imcs_train),
            "IMCS-21-dev-cases": len(gold_dev),
            "IMCS-21-test-cases": len(gold_test),
            "CBLUE-IMCS-V2-MRG": len(cblue_train),
            "Toyhom-weak-train": len(weak_train),
            "Toyhom-weak-dev": len(weak_dev),
        },
        "weakRowsAvailableByDomain": weak_seen,
        "cblueFiltering": cblue_stats,
        "integrity": integrity,
        "sources": [
            {
                "path": str(path.relative_to(dataset_root)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in source_paths
        ],
        "licenses": {
            "IMCS-21": "仓库未声明许可证；仅用于课程研究，不公开再分发数据或权重",
            "CBLUE_mirrors": "Apache-2.0（以本地镜像 README 声明为准）",
            "Toyhom-Chinese-medical-dialogue-data": "MIT; git commit 26724a4357fcd142f0cab81188cacf1a2dd8a827",
        },
        "weakLabelPolicy": (
            "仅从标题和患者 ask 中摘取主诉、现病史、明确既往史及明确检查句；"
            "answer 只作为带警示的上下文，不生成诊断、药物或已执行治疗标签"
        ),
    }
    manifest_path = output / "manifest.json"
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    args.manifest_copy.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_copy.write_text(manifest_text, encoding="utf-8")
    print(json.dumps({"output": str(output), **manifest["sourceCounts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

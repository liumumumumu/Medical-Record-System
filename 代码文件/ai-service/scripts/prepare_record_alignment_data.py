"""Build leakage-free runtime inputs for oral-to-clinical record generation.

The source must come from the original patient self-report/dialogue.  Never build
runtime input fields from the reference report: doing so turns seq2seq training
into an identity-copy task and makes evaluation scores meaningless.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import re
import sys
from typing import Any, Iterable


AI_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(AI_ROOT))

from src.record_generator import SECTION_NAMES, build_model_input, parse_generated_sections  # noqa: E402
from src.schema import PatientInput  # noqa: E402


BLOCK_PATTERN_TEMPLATE = r"\[{marker}\](.*?)(?=\n\[[^\]]+\]|$)"
PATIENT_LINE_PATTERN = re.compile(
    r"^(?:患者|患儿家长|患儿母亲|患儿父亲|家长|母亲|父亲)[：:]\s*(.+)$",
    re.MULTILINE,
)
AGE_PATTERN = re.compile(r"(\d{1,3})\s*(个月|岁)")
SPACE_PATTERN = re.compile(r"[\t\r ]+")
FORMAL_MARKERS = (
    "患者",
    "患儿",
    "于",
    "出现",
    "伴",
    "无明显诱因",
    "否认",
    "给予",
    "治疗",
    "症状",
    "查",
    "示",
    "最高",
    "效果欠佳",
    "既往体健",
    "腹痛",
    "腹泻",
    "发热",
    "呕吐",
)
COLLOQUIAL_MARKERS = (
    "大夫你好",
    "医生你好",
    "请问",
    "我想问",
    "谢谢医生",
    "怎么办",
    "能不能",
    "是不是",
    "怎么治疗",
    "肚子疼",
    "拉肚子",
    "拉稀",
    "发烧",
    "没什么用",
)
ORALIZATION_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("呼吸困难", "喘不上气"),
    ("阵发性腹痛", "肚子一阵一阵疼"),
    ("排便困难", "大便拉不出来"),
    ("大便干结", "大便很干"),
    ("效果欠佳", "没什么用"),
    ("无明显缓解", "没怎么好转"),
    ("既往体健", "平时身体挺好的"),
    ("患儿", "我家孩子"),
    ("患者", "我"),
    ("腹泻", "拉肚子"),
    ("腹痛", "肚子疼"),
    ("腹胀", "肚子胀"),
    ("发热", "发烧"),
    ("头痛", "头疼"),
    ("乏力", "没劲"),
    ("恶心", "有点想吐"),
    ("呕吐", "吐了"),
    ("咳痰", "有痰"),
    ("心悸", "心慌"),
    ("进食", "吃了"),
    ("自行服用", "自己吃了"),
    ("自行饮用", "自己喝了"),
    ("伴有", "还有"),
    ("伴", "还有"),
    ("否认", "没有"),
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建无答案泄露的口语转病历对齐数据")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / "dataset" / "derived" / "record-generation-v1",
    )
    parser.add_argument(
        "--weak-per-domain",
        type=int,
        default=0,
        help="已弃用；弱标注目标是口语摘抄，不能用于书面化对齐训练",
    )
    parser.add_argument(
        "--gold-count",
        type=int,
        default=0,
        help="最多使用多少个 gold 病例；0 表示全部",
    )
    parser.add_argument("--seed", type=int, default=43)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def canonical_target(sections: dict[str, str]) -> str:
    return "".join(f"<{name}>{sections[name]}" for name in SECTION_NAMES)


def clean_source_text(value: object) -> str:
    text = str(value or "").replace("\x00", "")
    text = SPACE_PATTERN.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clip_text(value: str, limit: int, default: str = "未提供") -> str:
    cleaned = clean_source_text(value)
    return cleaned[:limit].strip() if cleaned else default


def source_block(source: str, marker: str) -> str:
    match = re.search(
        BLOCK_PATTERN_TEMPLATE.format(marker=re.escape(marker)),
        source,
        flags=re.DOTALL,
    )
    return clean_source_text(match.group(1)) if match else ""


def patient_statements(conversation: str) -> str:
    statements = [clean_source_text(value) for value in PATIENT_LINE_PATTERN.findall(conversation)]
    return "。".join(value.rstrip("。！？!?") for value in statements[:6] if value)


def infer_age(source: str, source_dataset: str) -> int:
    match = AGE_PATTERN.search(source)
    if match:
        value = int(match.group(1))
        return min(value, 12) if match.group(2) == "个月" else min(value, 130)
    return 5 if source_dataset in {"IMCS-21", "CBLUE-IMCS-V2-MRG"} else 35


def patient_from_original_source(row: dict[str, Any], index: int) -> PatientInput:
    """Map original oral evidence to front-end-shaped fields without reading target text."""
    original = clean_source_text(row.get("source"))
    self_report = source_block(original, "患者自述")
    conversation = source_block(original, "问诊与治疗记录")
    if not conversation:
        conversation = original
    spoken_by_patient = patient_statements(conversation)
    chief_source = self_report or spoken_by_patient or conversation
    present_parts = [value for value in (self_report, conversation) if value]
    present_source = "\n".join(dict.fromkeys(present_parts))
    source_dataset = str(row.get("sourceDataset") or "")
    department = str(row.get("department") or "其他")
    return PatientInput(
        name=f"训练患者{index:05d}",
        gender="男" if index % 2 else "女",
        age=infer_age(original, source_dataset),
        chief_complaint=clip_text(chief_source, 200),
        history_present_illness=clip_text(present_source, 1_200),
        past_history="未提供",
        allergy_history="未提供",
        vital_signs="未提供",
        physical_exam="未提供",
        lab_results="未提供",
        department=department,
        preliminary_diagnosis="未提供",
        treatment_taken="未提供",
        medication_usage="未提供",
    )


def formal_style_score(target: str) -> tuple[int, int, int]:
    sections = parse_generated_sections(target)
    narrative = "\n".join(sections.get(name, "") for name in ("主诉", "现病史"))
    positive = sum(narrative.count(marker) for marker in FORMAL_MARKERS)
    negative = sum(narrative.count(marker) for marker in COLLOQUIAL_MARKERS)
    third_person = int("患者" in narrative or "患儿" in narrative)
    return (positive * 3 + third_person * 4 - negative * 5, len(narrative), -negative)


def valid_targets(row: dict[str, Any]) -> list[str]:
    candidates = row.get("targets") or [row.get("target")]
    values: list[str] = []
    for candidate in candidates:
        parsed = parse_generated_sections(str(candidate or ""))
        if all(parsed.get(name) for name in SECTION_NAMES):
            canonical = canonical_target(parsed)
            if canonical not in values:
                values.append(canonical)
    if not values:
        raise ValueError(f"{row.get('id', 'unknown')} 缺少完整参考病历")
    return values


def select_formal_target(row: dict[str, Any]) -> str:
    return max(valid_targets(row), key=formal_style_score)


def select_gold_cases(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one case per original dialogue and select its most clinical reference."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            str(row.get("sourceDataset") or ""),
            str(row.get("originalId") or row.get("id") or ""),
        )
        groups[key].append(row)
    selected: list[dict[str, Any]] = []
    for key in sorted(groups):
        group = groups[key]
        base = dict(group[0])
        candidates: list[str] = []
        for row in group:
            for target in valid_targets(row):
                if target not in candidates:
                    candidates.append(target)
        chosen = max(candidates, key=formal_style_score)
        base["target"] = chosen
        base["targets"] = [chosen]
        selected.append(base)
    return selected


def align_row(row: dict[str, Any], index: int, split: str) -> dict[str, Any]:
    patient = patient_from_original_source(row, index)
    target = select_formal_target(row)
    return {
        "id": f"formalization-{row['id']}",
        "source": build_model_input(patient),
        "target": target,
        "targets": [target],
        "sourceDataset": row.get("sourceDataset"),
        "qualityTier": "gold-runtime-formalization",
        "trainingStage": "formalization",
        "split": split,
        "department": row.get("department") or "其他",
        "originalId": row.get("originalId") or row["id"],
        "styleScore": formal_style_score(target)[0],
    }


def oralize_clinical_text(value: str) -> str:
    if value == "未提供":
        return value
    oral = value
    for clinical, colloquial in ORALIZATION_REPLACEMENTS:
        oral = oral.replace(clinical, colloquial)
    oral = re.sub(r"(?<!明)无(?=[\u4e00-\u9fff])", "没有", oral)
    oral = oral.replace("；", "，").replace("。", "，")
    oral = re.sub(r"，{2,}", "，", oral).strip("， ")
    return oral


def structured_oral_augmentation(
    row: dict[str, Any],
    index: int,
) -> dict[str, Any] | None:
    """Training-only noisy paraphrase; dev/test always retain real untouched dialogue."""
    target = select_formal_target(row)
    target_score = formal_style_score(target)[0]
    if target_score < 15 or any(marker in target for marker in COLLOQUIAL_MARKERS):
        return None
    sections = parse_generated_sections(target)
    chief = oralize_clinical_text(sections["主诉"])
    present = oralize_clinical_text(sections["现病史"])
    past = oralize_clinical_text(sections["既往史"])
    auxiliary = oralize_clinical_text(sections["辅助检查"])
    if chief == sections["主诉"] and present == sections["现病史"]:
        return None
    pediatric = "患儿" in sections["现病史"] or "小儿" in sections["现病史"]
    distractors = (
        "神志清，查体合作",
        "腹软，无反跳痛",
        "双肺呼吸音清",
        "咽部轻度充血",
    )
    patient = PatientInput(
        name=f"口语训练患者{index:05d}",
        gender="男" if index % 2 else "女",
        age=6 if pediatric else 35,
        chief_complaint=clip_text(chief, 200),
        history_present_illness=clip_text(present, 1_200),
        past_history=past,
        allergy_history="未提供",
        vital_signs="未提供",
        physical_exam=distractors[index % len(distractors)],
        lab_results=auxiliary,
        department=str(row.get("department") or "其他"),
        preliminary_diagnosis="未提供",
        treatment_taken="未提供",
        medication_usage="未提供",
    )
    return {
        "id": f"structured-oral-{row['id']}",
        "source": build_model_input(patient),
        "target": target,
        "targets": [target],
        "sourceDataset": f"{row.get('sourceDataset')}-train-only-oralization",
        "qualityTier": "gold-derived-oral-augmentation",
        "trainingStage": "formalization",
        "split": "train",
        "department": row.get("department") or "其他",
        "originalId": row.get("originalId") or row["id"],
        "styleScore": target_score,
    }


def exact_copy_row(row: dict[str, Any]) -> bool:
    sections = parse_generated_sections(str(row["target"]))
    source = str(row["source"])
    source_fields = {
        "主诉": source_block(source, "主诉原文"),
        "现病史": source_block(source, "现病史原文"),
        "既往史": source_block(source, "既往史原文"),
        "辅助检查": source_block(source, "辅助检查原文"),
    }
    return all(clean_source_text(sections[name]) == clean_source_text(source_fields[name]) for name in SECTION_NAMES)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> None:
    args = arguments()
    if args.weak_per_domain:
        raise SystemExit(
            "弱标注对话目标是原文摘抄，会重新把模型训练成复制器；书面化对齐仅允许 gold 数据"
        )
    data_dir = args.data_dir.resolve()
    rng = random.Random(args.seed)
    gold = select_gold_cases(load_jsonl(data_dir / "gold_train.jsonl"))
    rng.shuffle(gold)
    if args.gold_count > 0:
        gold = gold[: args.gold_count]
    real_dialogue_train = [
        align_row(row, index, "train") for index, row in enumerate(gold, start=1)
    ]
    augmented_train = [
        augmented
        for index, row in enumerate(gold, start=1)
        if (augmented := structured_oral_augmentation(row, index)) is not None
    ]
    train = [*real_dialogue_train, *augmented_train]
    rng.shuffle(train)
    dev_rows = load_jsonl(data_dir / "gold_dev.jsonl")
    dev = [align_row(row, index, "dev") for index, row in enumerate(dev_rows, start=1)]
    test_rows = load_jsonl(data_dir / "gold_test.jsonl")
    test = [align_row(row, index, "test") for index, row in enumerate(test_rows, start=1)]

    copy_counts = {
        "train": sum(exact_copy_row(row) for row in train),
        "dev": sum(exact_copy_row(row) for row in dev),
        "test": sum(exact_copy_row(row) for row in test),
    }
    if copy_counts["train"] / max(len(train), 1) > 0.05:
        raise RuntimeError(f"训练集仍存在异常高的整段答案复制率：{copy_counts}")

    write_jsonl(data_dir / "alignment_train.jsonl", train)
    write_jsonl(data_dir / "alignment_real_train.jsonl", real_dialogue_train)
    write_jsonl(data_dir / "alignment_oral_train.jsonl", augmented_train)
    write_jsonl(data_dir / "alignment_dev.jsonl", dev)
    write_jsonl(data_dir / "alignment_test.jsonl", test)
    manifest = {
        "schemaVersion": "record-generation-formalization-v2",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "sourceStrategy": "original-patient-self-report-and-dialogue-to-runtime-fields",
        "targetStrategy": "highest-clinical-style-gold-reference-per-original-case",
        "weakSamplesUsed": 0,
        "counts": {
            "train": len(train),
            "realDialogueTrain": len(real_dialogue_train),
            "trainOnlyOralAugmentation": len(augmented_train),
            "dev": len(dev),
            "test": len(test),
        },
        "exactInputTargetCopyRows": copy_counts,
        "trainingAugmentation": (
            "仅训练集使用 gold 目标的保事实口语扰动来模拟前端短字段；"
            "所有 dev/test 均保持真实原始医患对话且不做目标派生"
        ),
        "policy": (
            "输入仅来自原始患者自述和医患对话，绝不从参考病历反构造输入字段；"
            "弱标注口语摘抄不参与书面化微调；dev/test 不参与训练"
        ),
    }
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    (data_dir / "alignment_manifest.json").write_text(text, encoding="utf-8")
    artifact = AI_ROOT / "artifacts" / "record-generation-v1" / "alignment_manifest.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

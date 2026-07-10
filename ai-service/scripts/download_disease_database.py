import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from src.config import DATASET_ROOT  # noqa: E402


REVISION = "8e4982f797e0cee0a494e4ae82faf1e6a4ebbb44"
SOURCE_URL = (
    "https://huggingface.co/datasets/FreedomIntelligence/Disease_Database/"
    f"resolve/{REVISION}/disease_database_zh.json?download=true"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(force: bool = False) -> Path:
    target_dir = DATASET_ROOT / "Disease_Database"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "disease_database_zh.json"
    partial = target.with_suffix(".json.part")
    if target.exists() and not force:
        print(f"Dataset already exists: {target}")
    else:
        request = urllib.request.Request(
            SOURCE_URL,
            headers={"User-Agent": "medical-record-course-project/1.0"},
        )
        print(f"Downloading {SOURCE_URL}")
        with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as file:
            shutil.copyfileobj(response, file)
        if partial.stat().st_size < 1_000_000:
            raise RuntimeError("Downloaded file is unexpectedly small")
        partial.replace(target)

    metadata = {
        "dataset": "FreedomIntelligence/Disease_Database",
        "file": target.name,
        "sourceUrl": SOURCE_URL,
        "revision": REVISION,
        "license": "Apache-2.0",
        "downloadedAt": datetime.now(timezone.utc).isoformat(),
        "sizeBytes": target.stat().st_size,
        "sha256": sha256(target),
        "usage": "Only disease names and common-symptom fields are used for course-demo retrieval.",
    }
    (target_dir / "SOURCE.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (target_dir / "README.md").write_text(
        "# Disease_Database 中文镜像\n\n"
        "来源：FreedomIntelligence/Disease_Database（Hugging Face）。\n\n"
        f"固定版本：`{REVISION}`。许可：Apache-2.0。\n\n"
        "本项目只使用疾病名称和常见症状字段构建课程演示用检索索引，"
        "不直接使用其中的治疗文本，也不将结果用于真实诊疗。\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download the pinned Chinese disease database")
    parser.add_argument("--force", action="store_true", help="Download even if the file exists")
    arguments = parser.parse_args()
    download(force=arguments.force)


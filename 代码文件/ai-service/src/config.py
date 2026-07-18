import json
import os
from pathlib import Path
from typing import Any


SERVICE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = SERVICE_ROOT.parents[1]
CONFIG_DIR = SERVICE_ROOT / "config"
MODEL_DIR = SERVICE_ROOT / "models"
RESOURCE_DIR = SERVICE_ROOT / "resources"
DATASET_ROOT = Path(os.getenv("MEDICAL_DATASET_ROOT", WORKSPACE_ROOT / "dataset"))
MODEL_NAME = "medical-record-hybrid-diagnosis"
MODEL_VERSION = "1.0.0"
RECORD_MODEL_DIR = Path(
    os.getenv("RECORD_GENERATOR_MODEL_DIR", MODEL_DIR / "record_generator_v1")
)
RECORD_MODEL_NAME = "IDEA-CCNL/Randeng-T5-77M-MultiTask-Chinese"
RECORD_MODEL_VERSION = "record-gen-t5-v1.2.0"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def ensure_output_directories() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)

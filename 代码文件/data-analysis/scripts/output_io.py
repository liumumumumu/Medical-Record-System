from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def write_csv(
    df: pd.DataFrame,
    output_file: Path,
    *,
    encoding: str = "utf-8-sig",
    index: bool = False,
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding=encoding, newline="") as handle:
        df.to_csv(handle, index=index, lineterminator="\n")


def write_json(
    payload: Any,
    output_file: Path,
    *,
    encoding: str = "utf-8",
    ensure_ascii: bool = False,
    indent: int = 2,
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding=encoding, newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=ensure_ascii, indent=indent)
        handle.write("\n")

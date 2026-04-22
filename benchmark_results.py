from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESULTS_DIR = Path("bench_mark_result")


def ensure_results_dir() -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_result_json(filename: str, payload: dict[str, Any]) -> Path:
    output_path = ensure_results_dir() / filename
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


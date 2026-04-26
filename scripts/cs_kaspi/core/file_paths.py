from __future__ import annotations
from pathlib import Path
from typing import Any
from .read_yaml import read_yaml

ROOT = Path(__file__).resolve().parents[3]
PROJECT_CONFIG = ROOT / "config" / "project.yml"

def get_project_config() -> dict[str, Any]:
    return read_yaml(PROJECT_CONFIG)

def get_path(key: str) -> Path:
    cfg = get_project_config()
    path = ROOT / cfg["paths"][key]
    path.mkdir(parents=True, exist_ok=True)
    return path

def ensure_base_dirs() -> None:
    for key in [
        "input_official_dir",
        "input_market_dir",
        "artifacts_state_dir",
        "artifacts_raw_dir",
        "artifacts_preview_dir",
        "artifacts_reports_dir",
        "artifacts_exports_dir",
    ]:
        get_path(key)

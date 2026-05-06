from __future__ import annotations

from pathlib import Path
from typing import Any

from .yaml_io import read_yaml

ROOT = Path(__file__).resolve().parents[3]
PROJECT_CONFIG_PATH = ROOT / "config" / "project.yml"


def project_config() -> dict[str, Any]:
    return read_yaml(PROJECT_CONFIG_PATH)


def path_from_config(key: str) -> Path:
    cfg = project_config()
    rel = cfg.get("paths", {}).get(key)
    if not rel:
        raise KeyError(f"Path key not found in config/project.yml: {key}")
    return ROOT / rel


def ensure_runtime_dirs() -> None:
    cfg = project_config()
    for rel in cfg.get("paths", {}).values():
        (ROOT / rel).mkdir(parents=True, exist_ok=True)

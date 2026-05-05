from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import ROOT
from .yaml_io import read_yaml


def enabled_suppliers() -> list[dict[str, Any]]:
    suppliers: list[dict[str, Any]] = []
    for path in sorted((ROOT / "config" / "suppliers").glob("*.yml")):
        cfg = read_yaml(path)
        if not cfg.get("enabled", True):
            continue
        supplier_key = cfg.get("supplier_key") or path.stem
        cfg["supplier_key"] = supplier_key
        cfg["_config_path"] = str(path)
        suppliers.append(cfg)
    return suppliers


def supplier_state_path(supplier_cfg: dict[str, Any]) -> Path:
    supplier_key = supplier_cfg["supplier_key"]
    state_files = supplier_cfg.get("state_files", {})
    rel = state_files.get("official_products_file", f"artifacts/state/{supplier_key}_official_products.json")
    return ROOT / rel

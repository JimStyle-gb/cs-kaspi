from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.yaml_io import read_yaml


def cfg() -> dict[str, Any]:
    return read_yaml(ROOT / "config" / "market_sources.yml")


def discovery_cfg() -> dict[str, Any]:
    return cfg().get("discovery", {}) or {}


def browser_cfg() -> dict[str, Any]:
    return cfg().get("browser", {}) or {}


def matching_cfg() -> dict[str, Any]:
    return cfg().get("matching", {}) or {}


def seeds() -> list[dict[str, Any]]:
    rows = cfg().get("seeds", []) or []
    return [dict(row) for row in rows if isinstance(row, dict) and row.get("enabled", True) is not False]

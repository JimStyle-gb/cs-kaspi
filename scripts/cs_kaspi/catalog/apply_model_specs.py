from __future__ import annotations

from copy import deepcopy
from typing import Any

from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.yaml_io import read_yaml


def _load_spec_file(supplier_key: str, category_key: str | None) -> dict[str, Any]:
    if not category_key:
        return {}
    return read_yaml(ROOT / "config" / "model_specs" / f"{supplier_key}_{category_key}.yml")


def _pick_model_block(spec_data: dict[str, Any], model_key: str | None) -> dict[str, Any] | None:
    if not model_key:
        return None
    models = spec_data.get("models", {}) or {}
    block = models.get(model_key)
    if isinstance(block, dict) and block.get("enabled") is not False:
        return block
    return None


def _merge_specs_override(row: dict[str, Any], override: dict[str, Any]) -> None:
    """Добавляет подтверждённые model_specs в official.specs без guess-логики."""
    if not override:
        return
    official = row.setdefault("official", {})
    if not isinstance(official, dict):
        return
    specs = official.setdefault("specs", {})
    if not isinstance(specs, dict):
        specs = {}
        official["specs"] = specs
    for key, value in override.items():
        if value in (None, "", [], {}):
            continue
        specs[key] = value


def run(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for product in products:
        row = deepcopy(product)
        supplier_key = row.get("supplier_key")
        category_key = row.get("category_key")
        spec_data = _load_spec_file(supplier_key, category_key)
        model_block = _pick_model_block(spec_data, row.get("model_key"))
        existing = row.get("model_specs") if isinstance(row.get("model_specs"), dict) else {}
        specs_override = (model_block or {}).get("known_specs", {}) or existing.get("specs_override", {}) or {}
        row["model_specs"] = {
            **existing,
            "exists": bool(model_block) or bool(existing.get("exists")),
            "spec_file": f"config/model_specs/{supplier_key}_{category_key}.yml" if spec_data else existing.get("spec_file"),
            "canonical_model_name": (model_block or {}).get("canonical_model_name") or existing.get("canonical_model_name"),
            "title_template": (model_block or {}).get("kaspi_identity", {}).get("title_template") or existing.get("title_template"),
            "group_key": (model_block or {}).get("kaspi_identity", {}).get("group_key") or existing.get("group_key"),
            "specs_override": specs_override,
            "content_blocks": (model_block or {}).get("content_defaults", {}) or existing.get("content_blocks", {}),
        }
        _merge_specs_override(row, specs_override)
        result.append(row)
    return result

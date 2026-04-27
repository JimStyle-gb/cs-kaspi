from __future__ import annotations

from copy import deepcopy
from typing import Any

from scripts.cs_kaspi.core.file_paths import ROOT
from scripts.cs_kaspi.core.read_yaml import read_yaml


def _load_supplier_model_specs(supplier_key: str, category_key: str) -> dict[str, Any]:
    spec_name = f"{supplier_key}_{category_key}.yml"
    spec_path = ROOT / "config" / "model_specs" / spec_name
    if not spec_path.exists():
        return {}
    data = read_yaml(spec_path) or {}
    data["_spec_file"] = str(spec_path)
    return data


def _pick_model_block(spec_data: dict[str, Any], model_key: str | None) -> dict[str, Any]:
    models = spec_data.get("models", {})
    if model_key and model_key in models:
        return deepcopy(models[model_key])
    return {}


def run(products: list[dict], model_specs: dict | None = None) -> list[dict]:
    result: list[dict] = []

    for product in products:
        row = deepcopy(product)
        supplier_key = row.get("supplier_key")
        category_key = row.get("category_key")
        model_key = row.get("model_key")

        spec_data = _load_supplier_model_specs(supplier_key, category_key)
        model_block = _pick_model_block(spec_data, model_key)

        row["model_specs"] = {
            "exists": bool(model_block),
            "spec_file": spec_data.get("_spec_file"),
            "canonical_model_name": model_block.get("canonical_model_name"),
            "title_template_key": model_block.get("kaspi_identity", {}).get("group_key"),
            "specs_override": model_block.get("known_specs", {}),
            "content_blocks": model_block.get("content_defaults", {}),
            "package_defaults": model_block.get("package_defaults", {}),
            "aliases": model_block.get("aliases", []),
            "kaspi_identity": model_block.get("kaspi_identity", {}),
        }

        result.append(row)

    return result

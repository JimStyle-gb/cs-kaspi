from __future__ import annotations

from copy import deepcopy
from typing import Any

from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.yaml_io import read_yaml


def _load_spec_file(supplier_key: str, category_key: str | None) -> dict[str, Any]:
    if not category_key:
        return {}
    return read_yaml(ROOT / "config" / "model_specs" / f"{supplier_key}_{category_key}.yml")


def _enabled_model(models: dict[str, Any], model_key: str | None) -> tuple[str | None, dict[str, Any] | None, str | None]:
    if not model_key:
        return None, None, None
    block = models.get(model_key)
    if isinstance(block, dict) and block.get("enabled") is not False:
        return model_key, block, "direct_model_key"
    return None, None, None


def _alias_text(row: dict[str, Any]) -> str:
    parts = [
        row.get("model_key"),
        row.get("product_key"),
        row.get("variant_key"),
        (row.get("market") or {}).get("market_title") if isinstance(row.get("market"), dict) else None,
        (row.get("market_variant") or {}).get("market_title") if isinstance(row.get("market_variant"), dict) else None,
        (row.get("official") or {}).get("title_official") if isinstance(row.get("official"), dict) else None,
        (row.get("official") or {}).get("title_listing") if isinstance(row.get("official"), dict) else None,
        (row.get("listing_snapshot") or {}).get("title_listing") if isinstance(row.get("listing_snapshot"), dict) else None,
    ]
    return " ".join(str(p) for p in parts if p).lower().replace("-", "_")


def _alias_contains(alias_block: Any) -> list[str]:
    if isinstance(alias_block, str):
        return [alias_block]
    if isinstance(alias_block, list):
        return [str(v) for v in alias_block if v]
    if isinstance(alias_block, dict):
        values: list[str] = []
        for key in ("contains", "model_key_contains", "title_contains", "product_key_contains"):
            raw = alias_block.get(key)
            if isinstance(raw, str):
                values.append(raw)
            elif isinstance(raw, list):
                values.extend(str(v) for v in raw if v)
        return values
    return []


def _pick_model_block(spec_data: dict[str, Any], row: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None, str | None]:
    models = spec_data.get("models", {}) or {}
    model_key, block, source = _enabled_model(models, row.get("model_key"))
    if block:
        return model_key, block, source

    aliases = spec_data.get("aliases", {}) or {}
    if not isinstance(aliases, dict):
        return None, None, None

    haystack = _alias_text(row)
    for target_model_key, alias_block in aliases.items():
        target_key = str(target_model_key)
        target = models.get(target_key)
        if not isinstance(target, dict) or target.get("enabled") is False:
            continue
        needles = _alias_contains(alias_block)
        for needle in needles:
            normalized = str(needle).lower().replace("-", "_").strip()
            if normalized and normalized in haystack:
                return target_key, target, f"alias:{needle}"
    return None, None, None


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
        model_key, model_block, match_source = _pick_model_block(spec_data, row)
        existing = row.get("model_specs") if isinstance(row.get("model_specs"), dict) else {}
        specs_override = (model_block or {}).get("known_specs", {}) or existing.get("specs_override", {}) or {}
        row["model_specs"] = {
            **existing,
            "exists": bool(model_block) or bool(existing.get("exists")),
            "spec_file": f"config/model_specs/{supplier_key}_{category_key}.yml" if spec_data else existing.get("spec_file"),
            "matched_model_key": model_key or existing.get("matched_model_key"),
            "match_source": match_source or existing.get("match_source"),
            "canonical_model_name": (model_block or {}).get("canonical_model_name") or existing.get("canonical_model_name"),
            "title_template": (model_block or {}).get("kaspi_identity", {}).get("title_template") or existing.get("title_template"),
            "group_key": (model_block or {}).get("kaspi_identity", {}).get("group_key") or existing.get("group_key"),
            "specs_override": specs_override,
            "content_blocks": (model_block or {}).get("content_defaults", {}) or existing.get("content_blocks", {}),
        }
        _merge_specs_override(row, specs_override)
        result.append(row)
    return result

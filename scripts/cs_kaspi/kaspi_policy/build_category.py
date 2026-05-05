from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.yaml_io import read_yaml


def _categories_config() -> dict[str, Any]:
    data = read_yaml(ROOT / "config" / "categories.yml")
    categories = data.get("categories", {}) if isinstance(data, dict) else {}
    return categories if isinstance(categories, dict) else {}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def run(product: dict[str, Any]) -> dict[str, Any]:
    """Build safe Kaspi category draft mapping.

    We do not invent real Kaspi category IDs. Codes must come from the user's
    Kaspi cabinet/API and are stored in config/categories.yml. Until a real code
    exists, create payload remains draft-only with a clear live blocker.
    """
    category_key = _clean(product.get("category_key")) or "unknown"
    categories = _categories_config()
    category_cfg = categories.get(category_key, {}) if isinstance(categories.get(category_key), dict) else {}
    kaspi_cfg = category_cfg.get("kaspi", {}) if isinstance(category_cfg.get("kaspi"), dict) else {}

    category_code = _clean(kaspi_cfg.get("category_code"))
    category_name = _clean(kaspi_cfg.get("category_name_ru")) or _clean(category_cfg.get("name_ru")) or category_key
    category_path = _clean(kaspi_cfg.get("category_path_ru")) or category_name
    product_type_ru = _clean(category_cfg.get("product_type_ru")) or category_name.lower()
    configured_status = _clean(kaspi_cfg.get("mapping_status"))

    if category_code:
        status = "mapped"
        live_ready = True
    else:
        status = configured_status or "needs_real_kaspi_category_code"
        live_ready = False

    return {
        "category_key": category_key,
        "project_category_name_ru": _clean(category_cfg.get("name_ru")) or category_name,
        "product_type_ru": product_type_ru,
        "kaspi_category_code": category_code or None,
        "kaspi_category_name": category_name,
        "kaspi_category_path": category_path,
        "kaspi_category_status": status,
        "kaspi_category_live_ready": live_ready,
        "kaspi_category_note": _clean(kaspi_cfg.get("note")),
        "kaspi_category_search_hint": _clean(kaspi_cfg.get("search_hint_ru")),
        "kaspi_category_fill_instruction": _clean(kaspi_cfg.get("fill_instruction_ru")),
    }

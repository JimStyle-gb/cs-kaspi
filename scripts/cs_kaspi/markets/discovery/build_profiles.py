from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.catalog.apply_model_specs import run as apply_model_specs
from scripts.cs_kaspi.catalog.load_official_states import run as load_official_states
from scripts.cs_kaspi.catalog.merge_products import run as merge_products
from scripts.cs_kaspi.core.text_utils import normalize_spaces

CATEGORY_PRIORITY = {
    "air_fryers": 10,
    "coffee_makers": 20,
    "blenders": 30,
    "ovens": 40,
    "air_fryer_accessories": 50,
}


def _profile(product: dict[str, Any]) -> dict[str, Any]:
    official = product.get("official", {}) or {}
    brand = product.get("brand") or official.get("brand") or "DEMIAND"
    model_key = product.get("model_key") or official.get("model_key") or ""
    title = official.get("title_official") or official.get("title") or product.get("name") or ""
    specs = official.get("specs", {}) or {}
    aliases = [
        str(brand),
        str(model_key).replace("_", " "),
        str(official.get("product_id") or ""),
        str(specs.get("Модель") or specs.get("model") or ""),
        str(title),
    ]
    aliases = [normalize_spaces(x) for x in aliases if normalize_spaces(x)]
    return {
        "base_product_key": product.get("product_key"),
        "supplier_key": product.get("supplier_key"),
        "category_key": product.get("category_key"),
        "brand": brand,
        "model_key": model_key,
        "variant_key": product.get("variant_key"),
        "official_article": official.get("product_id"),
        "official_title": title,
        "official_url": official.get("url"),
        "official_specs": specs,
        "aliases": aliases,
        "priority": CATEGORY_PRIORITY.get(product.get("category_key"), 99),
    }


def run() -> list[dict[str, Any]]:
    states = load_official_states(required=True)
    products = apply_model_specs(merge_products(states))
    profiles = [_profile(product) for product in products if product.get("product_key")]
    # Keep all official cards as reference, but sort stable so non-accessory base
    # models are preferred when one market listing mentions the same model.
    return sorted(profiles, key=lambda p: (int(p.get("priority") or 99), str(p.get("base_product_key") or "")))

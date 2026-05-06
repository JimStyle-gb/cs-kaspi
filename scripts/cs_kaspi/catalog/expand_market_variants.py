from __future__ import annotations

from copy import deepcopy
from typing import Any


def _market_only_product(product_key: str, market: dict[str, Any]) -> dict[str, Any]:
    title = market.get("market_title") or "DEMIAND товар WB"
    market_url = market.get("market_url") or ""
    image = market.get("market_image")
    category_key = market.get("category_key") or "air_fryer_accessories"
    brand = market.get("brand") or "DEMIAND"
    model_key = market.get("model_key") or "wb_market_variant"
    return {
        "product_key": product_key,
        "source_product_key": None,
        "is_market_variant": True,
        "is_market_only": True,
        "supplier_key": market.get("supplier_key") or "demiand",
        "supplier_category_name": category_key,
        "category_key": category_key,
        "brand": brand,
        "model_key": model_key,
        "variant_key": market.get("market_variant_signature"),
        "official": {
            "exists": False,
            "status": "market_only_wb",
            "product_id": market.get("market_product_key") or product_key,
            "url": market_url,
            "title_official": title,
            "short_description": "Товар найден в подтверждённой выдаче WB по бренду DEMIAND. Official-страница не найдена или не нужна как жёсткий фильтр; official слой используется только для обогащения, когда уверенно совпадает.",
            "description_official": "",
            "images": [image] if image else [],
            "specs": {},
            "specs_raw": {},
        },
        "listing_snapshot": {
            "product_url": market_url,
            "title_listing": title,
            "image_preview": image,
        },
        "meta": {
            "parsed_ok": True,
            "parse_errors": [],
            "market_only_reason": market.get("official_match_status") or "official_match_missing",
        },
        "compatibility": {},
        "market_variant": {
            "base_product_key": None,
            "market_product_key": product_key,
            "market_color": market.get("market_color"),
            "market_bundle": market.get("market_bundle"),
            "market_variant_signature": market.get("market_variant_signature"),
            "market_title": title,
        },
    }


def run(products: list[dict[str, Any]], market_state: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Expand official products into WB sellable variants.

    WB is the sellable source. Official products are optional enrichment.
    If a WB DEMIAND item has no confident official match, it still becomes a market-only Kaspi candidate.
    Exact duplicate WB variants are already collapsed earlier by market_product_key/variant_signature.
    """
    market_products = (market_state or {}).get("products", {}) or {}
    by_key = {str(p.get("product_key")): p for p in products if p.get("product_key")}
    result = list(products)

    for market_product_key, market in sorted(market_products.items()):
        if not market_product_key or market_product_key in by_key:
            continue
        base_key = market.get("base_product_key")
        base = by_key.get(str(base_key)) if base_key else None

        if base:
            clone = deepcopy(base)
            clone["product_key"] = market_product_key
            clone["source_product_key"] = base_key
            clone["is_market_variant"] = True
            clone["market_variant"] = {
                "base_product_key": base_key,
                "market_product_key": market_product_key,
                "market_color": market.get("market_color"),
                "market_bundle": market.get("market_bundle"),
                "market_variant_signature": market.get("market_variant_signature"),
                "market_title": market.get("market_title"),
            }
            official = clone.setdefault("official", {})
            official["base_product_key"] = base_key
            official["title_listing"] = market.get("market_title") or official.get("title_listing") or official.get("title_official")
            result.append(clone)
            continue

        result.append(_market_only_product(str(market_product_key), market))

    return result

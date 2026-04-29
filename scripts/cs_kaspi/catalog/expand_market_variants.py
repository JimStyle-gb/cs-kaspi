from __future__ import annotations

from copy import deepcopy
from typing import Any


def run(products: list[dict[str, Any]], market_state: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Expand official products into market variants.

    Official source remains the technical truth. Ozon/WB can create extra
    sellable variants by model: color/bundle/set from the market card become
    separate Kaspi candidates, but technical specs/descriptions still come
    from the base official product.
    """
    market_products = (market_state or {}).get("products", {}) or {}
    by_key = {str(p.get("product_key")): p for p in products if p.get("product_key")}
    result = list(products)

    for market_product_key, market in sorted(market_products.items()):
        if not market_product_key or market_product_key in by_key:
            continue
        base_key = market.get("base_product_key")
        base = by_key.get(str(base_key)) if base_key else None
        if not base:
            continue

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

    return result

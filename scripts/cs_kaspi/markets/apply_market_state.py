from __future__ import annotations

from typing import Any


def _empty_market() -> dict[str, Any]:
    return {
        "sources": {},
        "sellable": False,
        "sellable_reason": "market_data_not_loaded",
        "market_price": None,
        "market_price_source": None,
        "market_url": None,
        "stock": 0,
        "lead_time_days": 20,
    }


def run(products: list[dict[str, Any]], market_state: dict[str, Any] | None) -> list[dict[str, Any]]:
    market_products = (market_state or {}).get("products", {}) or {}
    result: list[dict[str, Any]] = []
    for product in products:
        product_key = product.get("product_key")
        market = market_products.get(product_key) or _empty_market()
        product["market"] = market
        result.append(product)
    return result

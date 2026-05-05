from __future__ import annotations

from typing import Any


def _empty_match() -> dict[str, Any]:
    return {
        "exists": False,
        "kaspi_product_id": None,
        "kaspi_sku": None,
        "kaspi_title": None,
        "kaspi_url": None,
        "kaspi_price": None,
        "kaspi_stock": None,
        "kaspi_available": None,
        "matched_by": None,
        "confidence": None,
        "records_count": 0,
    }


def run(products: list[dict[str, Any]], match_state: dict[str, Any] | None) -> list[dict[str, Any]]:
    matched_products = (match_state or {}).get("products", {}) or {}
    result: list[dict[str, Any]] = []
    for product in products:
        product_key = product.get("product_key")
        product["kaspi_match"] = matched_products.get(product_key) or _empty_match()
        result.append(product)
    return result

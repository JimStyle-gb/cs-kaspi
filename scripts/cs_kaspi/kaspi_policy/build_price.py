from __future__ import annotations


def run(product: dict) -> int | None:
    market = product.get("market", {}) or {}
    price = market.get("kaspi_price") or market.get("price")
    if price in (None, ""):
        return None
    try:
        return int(round(float(price)))
    except Exception:
        return None

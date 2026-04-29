from __future__ import annotations


def run(product: dict) -> int:
    market = product.get("market", {}) or {}
    if market.get("sellable") is not True:
        return 0
    stock = market.get("stock")
    try:
        return max(1, int(stock or 1))
    except Exception:
        return 1

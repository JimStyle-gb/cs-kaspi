from __future__ import annotations


def run(product: dict) -> int:
    market = product.get("market", {}) or {}
    if market.get("sellable") is True:
        return int(market.get("lead_time_days") or 3)
    return 20

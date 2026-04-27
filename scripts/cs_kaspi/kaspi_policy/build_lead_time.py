from __future__ import annotations


def run(product: dict) -> int:
    market = product.get("market", {}) or {}
    if market.get("sellable") is True:
        try:
            return max(1, int(market.get("lead_time_days") or 3))
        except Exception:
            return 3
    return 20

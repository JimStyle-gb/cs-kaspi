from __future__ import annotations

import math

from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.yaml_io import read_yaml


def _round_up(value: float, step: int) -> int:
    if step <= 1:
        return int(round(value))
    return int(math.ceil(value / step) * step)


def _price_policy() -> dict:
    return (read_yaml(ROOT / "config" / "kaspi.yml").get("price_policy", {}) or {})


def run(product: dict) -> int | None:
    market = product.get("market", {}) or {}
    if market.get("sellable") is not True:
        return None

    raw_price = market.get("market_price") or market.get("price")
    if raw_price in (None, ""):
        return None

    try:
        base_price = float(raw_price)
    except Exception:
        return None
    if base_price <= 0:
        return None

    policy = _price_policy()
    markup_percent = float(policy.get("markup_percent") or 0)
    fixed_add_kzt = int(policy.get("fixed_add_kzt") or 0)
    min_margin_kzt = int(policy.get("min_margin_kzt") or 0)
    round_to_kzt = int(policy.get("round_to_kzt") or 100)

    percent_margin = base_price * markup_percent / 100
    margin = max(percent_margin, float(min_margin_kzt))
    final_price = base_price + margin + fixed_add_kzt
    return _round_up(final_price, round_to_kzt)

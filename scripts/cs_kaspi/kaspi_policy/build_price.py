from __future__ import annotations

import math
from typing import Any

from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.yaml_io import read_yaml


def _round_up(value: float, step: int) -> int:
    if step <= 1:
        return int(round(value))
    return int(math.ceil(value / step) * step)


def _price_policy() -> dict[str, Any]:
    return (read_yaml(ROOT / "config" / "kaspi.yml").get("price_policy", {}) or {})


def _allowed_price_sources(policy: dict[str, Any]) -> set[str]:
    values = policy.get("market_sources_for_price") or ["ozon", "wb", "manual"]
    return {str(value).strip().lower() for value in values if str(value).strip()}


def _forbidden_price_sources(policy: dict[str, Any]) -> set[str]:
    values = policy.get("forbidden_price_sources") or ["google", "kaspi"]
    return {str(value).strip().lower() for value in values if str(value).strip()}


def run(product: dict[str, Any]) -> int | None:
    market = product.get("market", {}) or {}
    if market.get("sellable") is not True:
        return None

    policy = _price_policy()
    source = str(market.get("market_price_source") or "").strip().lower()
    if source in _forbidden_price_sources(policy):
        return None
    if source not in _allowed_price_sources(policy):
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

    markup_percent = float(policy.get("markup_percent") or 0)
    fixed_add_kzt = int(policy.get("fixed_add_kzt") or 0)
    min_margin_kzt = int(policy.get("min_margin_kzt") or 0)
    round_to_kzt = int(policy.get("round_to_kzt") or 100)

    percent_margin = base_price * markup_percent / 100
    margin = max(percent_margin, float(min_margin_kzt))
    final_price = base_price + margin + fixed_add_kzt
    return _round_up(final_price, round_to_kzt)

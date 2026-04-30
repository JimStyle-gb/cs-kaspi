from __future__ import annotations

import math
from typing import Any

from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.yaml_io import read_yaml


def _round_price(value: float, step: int, mode: str) -> int:
    if step <= 1:
        return int(round(value))
    mode = (mode or "floor").strip().lower()
    if mode in {"floor", "floor_to_100", "down", "truncate"}:
        rounded = int(math.floor(value / step) * step)
        return max(step, rounded)
    if mode in {"ceil", "up"}:
        return int(math.ceil(value / step) * step)
    return int(round(value / step) * step)


def _price_policy() -> dict[str, Any]:
    return (read_yaml(ROOT / "config" / "kaspi.yml").get("price_policy", {}) or {})


def _allowed_price_sources(policy: dict[str, Any]) -> set[str]:
    values = policy.get("market_sources_for_price") or ["wb"]
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
    rounding_mode = str(policy.get("rounding_mode") or "floor")

    percent_margin = base_price * markup_percent / 100
    margin = max(percent_margin, float(min_margin_kzt))
    final_price = base_price + margin + fixed_add_kzt
    return _round_price(final_price, round_to_kzt, rounding_mode)

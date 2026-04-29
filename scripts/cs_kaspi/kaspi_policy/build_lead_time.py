from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.yaml_io import read_yaml


def _policy() -> dict[str, Any]:
    return (read_yaml(ROOT / "config" / "kaspi.yml").get("lead_time_policy", {}) or {})


def run(product: dict) -> int:
    market = product.get("market", {}) or {}
    policy = _policy()
    fallback = int(policy.get("fallback_days_when_market_eta_missing") or 3)
    missing = int(policy.get("missing_market_days") or 20)

    if market.get("sellable") is True:
        try:
            days = int(market.get("lead_time_days") or fallback)
            return max(1, days)
        except Exception:
            return fallback
    return missing

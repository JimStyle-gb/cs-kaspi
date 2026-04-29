from __future__ import annotations

from collections import defaultdict
from typing import Any


def _is_sellable(candidate: dict[str, Any]) -> bool:
    if candidate.get("market_available") is False:
        return False
    if candidate.get("market_stock") is not None:
        try:
            if int(candidate.get("market_stock") or 0) <= 0:
                return False
        except Exception:
            return False
    return candidate.get("market_price") not in (None, "", 0)


def _to_market_record(candidate: dict[str, Any], *, status: str, duplicates_count: int) -> dict[str, Any]:
    return {
        "source": candidate.get("source"),
        "product_key": candidate.get("market_product_key"),
        "base_product_key": candidate.get("base_product_key"),
        "supplier_key": candidate.get("supplier_key"),
        "category_key": candidate.get("category_key"),
        "official_article": candidate.get("official_article"),
        "model_key": candidate.get("model_key"),
        "variant_key": candidate.get("variant_signature"),
        "title": candidate.get("market_title"),
        "market_title": candidate.get("market_title"),
        "url": candidate.get("market_url"),
        "image": candidate.get("market_image"),
        "price": candidate.get("market_price"),
        "available": candidate.get("market_available"),
        "stock": candidate.get("market_stock"),
        "eta_text": candidate.get("eta_text"),
        "lead_time_days": candidate.get("lead_time_days"),
        "market_color": candidate.get("market_color"),
        "market_bundle": candidate.get("market_bundle"),
        "market_variant_signature": candidate.get("variant_signature"),
        "market_product_key": candidate.get("market_product_key"),
        "match_confidence": candidate.get("match_confidence"),
        "matched_by": candidate.get("matched_by"),
        "discovery_status": status,
        "duplicates_collapsed": duplicates_count,
        "seed_key": candidate.get("seed_key"),
        "seed_url": candidate.get("seed_url"),
    }


def run(accepted: list[dict[str, Any]], review_needed: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in accepted:
        if _is_sellable(candidate):
            grouped[str(candidate.get("market_product_key"))].append(candidate)
        else:
            review_needed.append(candidate)

    best: list[dict[str, Any]] = []
    for _, candidates in sorted(grouped.items()):
        chosen = sorted(
            candidates,
            key=lambda c: (
                int(c.get("market_price") or 10**12),
                -int(c.get("match_confidence") or 0),
                str(c.get("source") or ""),
            ),
        )[0]
        best.append(_to_market_record(chosen, status="auto_best_seed_listing_offer", duplicates_count=len(candidates)))

    return {
        "records": best,
        "review_needed": review_needed,
        "rejected": rejected,
        "summary": {
            "scored_candidates": len(accepted) + len(review_needed) + len(rejected),
            "auto_best_offer_records": len(best),
            "duplicates_collapsed": sum(max(0, len(v) - 1) for v in grouped.values()),
            "review_needed": len(review_needed),
            "rejected": len(rejected),
        },
    }

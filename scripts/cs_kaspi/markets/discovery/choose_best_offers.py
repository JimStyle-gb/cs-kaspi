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


def _offer_audit(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "market_id": candidate.get("market_id"),
        "wb_root": candidate.get("wb_root"),
        "wb_supplier_id": candidate.get("wb_supplier_id"),
        "wb_entity": candidate.get("wb_entity"),
        "title": candidate.get("market_title"),
        "url": candidate.get("market_url"),
        "price": candidate.get("market_price"),
        "stock": candidate.get("market_stock"),
        "eta_text": candidate.get("eta_text"),
        "lead_time_days": candidate.get("lead_time_days"),
        "market_color": candidate.get("market_color"),
        "market_bundle": candidate.get("market_bundle"),
        "seed_key": candidate.get("seed_key"),
        "matched_by": candidate.get("matched_by"),
        "official_match_status": candidate.get("official_match_status"),
        "seed_role": candidate.get("seed_role"),
        "review_only": candidate.get("review_only"),
        "wb_brand": candidate.get("wb_brand"),
        "wb_brand_id": candidate.get("wb_brand_id"),
        "wb_brand_status": candidate.get("wb_brand_status"),
    }


def _to_market_record(candidate: dict[str, Any], *, status: str, duplicates: list[dict[str, Any]]) -> dict[str, Any]:
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
        "price_currency": candidate.get("market_price_currency"),
        "available": candidate.get("market_available"),
        "stock": candidate.get("market_stock"),
        "eta_text": candidate.get("eta_text"),
        "lead_time_days": candidate.get("lead_time_days"),
        "market_color": candidate.get("market_color"),
        "market_bundle": candidate.get("market_bundle"),
        "wb_root": candidate.get("wb_root"),
        "wb_supplier_id": candidate.get("wb_supplier_id"),
        "wb_entity": candidate.get("wb_entity"),
        "market_variant_signature": candidate.get("variant_signature"),
        "market_product_key": candidate.get("market_product_key"),
        "match_confidence": candidate.get("match_confidence"),
        "matched_by": candidate.get("matched_by"),
        "official_match_status": candidate.get("official_match_status"),
        "seed_role": candidate.get("seed_role"),
        "review_only": candidate.get("review_only"),
        "wb_brand": candidate.get("wb_brand"),
        "wb_brand_id": candidate.get("wb_brand_id"),
        "wb_brand_status": candidate.get("wb_brand_status"),
        "discovery_status": status,
        "duplicates_collapsed": max(0, len(duplicates) - 1),
        "collapsed_offers": duplicates,
        "seed_key": candidate.get("seed_key"),
        "seed_url": candidate.get("seed_url"),
    }


def _sort_key(candidate: dict[str, Any]) -> tuple[int, int, int, str]:
    # Lowest price wins inside the same exact sellable variant. When prices match, prefer bigger stock and
    # shorter delivery, then stronger match confidence.
    price = int(candidate.get("market_price") or 10**12)
    stock = int(candidate.get("market_stock") or 0)
    lead = int(candidate.get("lead_time_days") or 9999)
    confidence = int(candidate.get("match_confidence") or 0)
    return (price, lead, -stock, -confidence)


def run(accepted: list[dict[str, Any]], review_needed: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in accepted:
        if _is_sellable(candidate):
            grouped[str(candidate.get("market_product_key"))].append(candidate)
        else:
            review_needed.append(candidate)

    best: list[dict[str, Any]] = []
    duplicate_groups: list[dict[str, Any]] = []
    for group_key, candidates in sorted(grouped.items()):
        chosen = sorted(candidates, key=_sort_key)[0]
        offers = [_offer_audit(row) for row in sorted(candidates, key=_sort_key)]
        best.append(_to_market_record(chosen, status="auto_best_seed_listing_offer", duplicates=offers))
        if len(candidates) > 1:
            duplicate_groups.append({
                "market_product_key": group_key,
                "variant_key": chosen.get("variant_signature"),
                "chosen_market_id": chosen.get("market_id"),
                "chosen_price": chosen.get("market_price"),
                "chosen_title": chosen.get("market_title"),
                "market_color": chosen.get("market_color"),
                "market_bundle": chosen.get("market_bundle"),
                "wb_entity": chosen.get("wb_entity"),
                "collapsed_count": len(candidates),
                "collapse_rule": "same title/model/color/entity/bundle signature; lowest price wins",
                "offers": offers,
            })

    return {
        "records": best,
        "review_needed": review_needed,
        "rejected": rejected,
        "duplicate_groups": duplicate_groups,
        "summary": {
            "scored_candidates": len(accepted) + len(review_needed) + len(rejected),
            "auto_best_offer_records": len(best),
            "duplicates_collapsed": sum(max(0, len(v) - 1) for v in grouped.values()),
            "duplicate_groups": len(duplicate_groups),
            "review_needed": len(review_needed),
            "rejected": len(rejected),
        },
    }

from __future__ import annotations

from typing import Any

from .common import (
    detect_bundle,
    detect_color,
    make_market_product_key,
    same_model_score,
    variant_signature,
)
from .seed_config import matching_cfg


def _best_profile(title: str, profiles: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, int]:
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for profile in profiles:
        score = same_model_score(
            title=title,
            brand=str(profile.get("brand") or "DEMIAND"),
            model_key=str(profile.get("model_key") or ""),
            category_key=profile.get("category_key"),
        )
        ranked.append((score, -int(profile.get("priority") or 99), profile))
    if not ranked:
        return None, 0
    score, _, profile = sorted(ranked, key=lambda x: (x[0], x[1]), reverse=True)[0]
    return profile, score


def score_listing_cards(listings: list[dict[str, Any]], profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for item in listings:
        title = str(item.get("title") or "")
        profile, confidence = _best_profile(title, profiles)
        if not profile:
            continue
        official_specs = profile.get("official_specs", {}) or {}
        color = detect_color(title, fallback=official_specs.get("color"))
        bundle = detect_bundle(title)
        model_key = str(profile.get("model_key") or "")
        signature = variant_signature(model_key=model_key, color=color, bundle=bundle, title=title)
        base_key = str(profile.get("base_product_key") or "")
        market_key = make_market_product_key(base_product_key=base_key, signature=signature)
        scored.append({
            "source": item.get("source"),
            "seed_key": item.get("seed_key"),
            "seed_url": item.get("seed_url"),
            "market_id": item.get("market_id"),
            "market_url": item.get("url"),
            "market_title": title,
            "market_image": item.get("image"),
            "market_price": item.get("price"),
            "market_available": item.get("available"),
            "market_stock": item.get("stock"),
            "eta_text": item.get("eta_text"),
            "lead_time_days": item.get("lead_time_days"),
            "supplier_key": profile.get("supplier_key"),
            "category_key": profile.get("category_key"),
            "brand": profile.get("brand"),
            "model_key": model_key,
            "base_product_key": base_key,
            "official_article": profile.get("official_article"),
            "official_title": profile.get("official_title"),
            "official_url": profile.get("official_url"),
            "market_color": color,
            "market_bundle": bundle,
            "variant_signature": signature,
            "market_product_key": market_key,
            "match_confidence": confidence,
            "matched_by": "seed_listing_model_match",
            "raw": item,
        })
    return scored


def split_by_status(scored: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    cfg = matching_cfg()
    minimum = int(cfg.get("minimum_confidence_for_auto_market_record") or 70)
    review_min = int(cfg.get("confidence_for_review") or 45)
    accepted: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in scored:
        conf = int(row.get("match_confidence") or 0)
        if conf >= minimum and row.get("market_price") and row.get("market_available") is not False:
            accepted.append(row)
        elif conf >= review_min:
            review.append(row)
        else:
            rejected.append(row)
    return {"accepted": accepted, "review_needed": review, "rejected": rejected}

from __future__ import annotations

from typing import Any

from .common import (
    detect_bundle,
    detect_color,
    is_demiand_text,
    make_market_product_key,
    same_model_score,
    variant_signature,
)
from .seed_config import matching_cfg

SEED_CATEGORY_BY_KEY = {
    "wb_demiand_cooking": "air_fryers",
    "wb_demiand_drinks": "coffee_makers",
    "wb_demiand_blending": "blenders",
    "wb_demiand_accessories": "air_fryer_accessories",
}


def _seed_category(seed_key: Any) -> str | None:
    return SEED_CATEGORY_BY_KEY.get(str(seed_key or ""))


def _profile_priority_for_seed(profile: dict[str, Any], seed_key: Any) -> int:
    wanted = _seed_category(seed_key)
    if wanted and profile.get("category_key") == wanted:
        return 20
    return 0


def _best_profile(title: str, profiles: list[dict[str, Any]], *, seed_key: Any = None) -> tuple[dict[str, Any] | None, int]:
    ranked: list[tuple[int, int, int, dict[str, Any]]] = []
    for profile in profiles:
        score = same_model_score(
            title=title,
            brand=str(profile.get("brand") or "DEMIAND"),
            model_key=str(profile.get("model_key") or ""),
            category_key=profile.get("category_key"),
            aliases=profile.get("aliases") or [],
        )
        seed_boost = _profile_priority_for_seed(profile, seed_key)
        ranked.append((score + seed_boost, score, -int(profile.get("priority") or 99), profile))
    if not ranked:
        return None, 0
    boosted, raw_score, _, profile = sorted(ranked, key=lambda x: (x[0], x[1], x[2]), reverse=True)[0]
    return profile, min(boosted, 100)


def _brand_ok(item: dict[str, Any], match_text: str) -> bool:
    brand = str(item.get("brand") or "")
    return is_demiand_text(match_text) or is_demiand_text(brand) or brand.strip().lower() == "demiand"


def _market_accept_confidence(confidence: int, item: dict[str, Any], match_text: str) -> tuple[int, str]:
    """WB is the sellable source; official data enriches, it must not kill variants.

    Exact model/alias matches keep their natural confidence. If WB clearly says
    the item is DEMIAND and it has a price, we still accept it as a sellable
    variant even when the official model match is soft. This is intentional for
    colors, комплектации, наборы and accessories that are not one-to-one with
    the official catalog.
    """
    if confidence >= int(matching_cfg().get("minimum_confidence_for_auto_market_record") or 65):
        return confidence, "seed_listing_model_or_alias_match"
    if _brand_ok(item, match_text) and item.get("price"):
        return max(confidence, 65), "wb_brand_sellable_variant"
    return confidence, "seed_listing_soft_match"


def score_listing_cards(listings: list[dict[str, Any]], profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for item in listings:
        title = str(item.get("title") or "")
        match_text = " ".join(x for x in [str(item.get("brand") or ""), title, str(item.get("raw_text") or "")[:500]] if x).strip()
        profile, confidence = _best_profile(match_text or title, profiles, seed_key=item.get("seed_key"))
        if not profile:
            continue
        confidence, matched_by = _market_accept_confidence(confidence, item, match_text or title)
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
            "matched_by": matched_by,
            "raw": item,
        })
    return scored


def split_by_status(scored: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    cfg = matching_cfg()
    minimum = int(cfg.get("minimum_confidence_for_auto_market_record") or 65)
    review_min = int(cfg.get("confidence_for_review") or 45)
    accepted: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in scored:
        conf = int(row.get("match_confidence") or 0)
        has_price = row.get("market_price") not in (None, "", 0)
        is_available = row.get("market_available") is not False
        if conf >= minimum and has_price and is_available:
            accepted.append(row)
        elif conf >= review_min:
            review.append(row)
        else:
            rejected.append(row)
    return {"accepted": accepted, "review_needed": review, "rejected": rejected}

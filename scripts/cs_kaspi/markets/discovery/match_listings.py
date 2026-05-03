from __future__ import annotations

from typing import Any

from .common import (
    detect_bundle,
    detect_color,
    is_demiand_text,
    make_market_product_key,
    norm_text,
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

CATEGORY_HINTS = {
    "blenders": ("блендер", "суповар", "demixi", "измельч", "смешив"),
    "coffee_makers": ("кофевар", "кофемаш", "капучин", "кофе"),
    "ovens": ("мини печ", "мини-печ", "духов", "печь"),
    "air_fryer_accessories": (
        "решетка", "решётка", "шампур", "стаканчик", "стаканчики", "форма", "корзин",
        "пергамент", "вкладыш", "поддон", "держатель", "клетка", "аксессуар",
    ),
    "air_fryers": ("аэрогр", "air fryer", "аэрофрит", "гриль"),
}

COLOR_HINTS_BY_KEY = {
    "black": ("черный", "чёрный", "black"),
    "white": ("белый", "white"),
    "metal": ("металл", "металлик", "сереб", "metal", "silver"),
    "beige": ("беж", "beige"),
}


def _seed_category(seed_key: Any) -> str | None:
    return SEED_CATEGORY_BY_KEY.get(str(seed_key or ""))


def _title_category(title: str) -> str | None:
    text = norm_text(title)
    for category, hints in CATEGORY_HINTS.items():
        if any(norm_text(hint) in text for hint in hints):
            return category
    return None


def _profile_color(profile: dict[str, Any]) -> str | None:
    specs = profile.get("official_specs", {}) or {}
    values = [
        specs.get("color"), specs.get("Цвет"), specs.get("цвет"),
        profile.get("official_title"), " ".join(map(str, profile.get("aliases") or [])),
        profile.get("base_product_key"), profile.get("variant_key"),
    ]
    text = norm_text(" ".join(str(x or "") for x in values))
    for key, hints in COLOR_HINTS_BY_KEY.items():
        if any(norm_text(hint) in text for hint in hints):
            return key
    return None


def _category_priority(profile: dict[str, Any], wanted: str | None, fallback_seed_key: Any) -> int:
    actual = profile.get("category_key")
    if wanted and actual == wanted:
        return 25
    if wanted and actual != wanted:
        return -25
    seed_wanted = _seed_category(fallback_seed_key)
    if seed_wanted and actual == seed_wanted:
        return 8
    return 0


def _color_priority(profile: dict[str, Any], wanted_color: str | None) -> int:
    if not wanted_color:
        return 0
    profile_color = _profile_color(profile)
    if not profile_color:
        return 0
    if profile_color == wanted_color:
        return 18
    return -18


def _best_profile(title: str, profiles: list[dict[str, Any]], *, seed_key: Any = None) -> tuple[dict[str, Any] | None, int]:
    wanted_category = _title_category(title)
    wanted_color = detect_color(title)
    ranked: list[tuple[int, int, int, int, dict[str, Any]]] = []
    for profile in profiles:
        raw_score = same_model_score(
            title=title,
            brand=str(profile.get("brand") or "DEMIAND"),
            model_key=str(profile.get("model_key") or ""),
            category_key=profile.get("category_key"),
            aliases=profile.get("aliases") or [],
        )
        category_boost = _category_priority(profile, wanted_category, seed_key)
        color_boost = _color_priority(profile, wanted_color)
        boosted = max(0, min(raw_score + category_boost + color_boost, 100))
        ranked.append((boosted, raw_score, color_boost, -int(profile.get("priority") or 99), profile))
    if not ranked:
        return None, 0
    boosted, raw_score, _, _, profile = sorted(ranked, key=lambda x: (x[0], x[1], x[2], x[3]), reverse=True)[0]
    return profile, min(boosted, 100)


def _brand_ok(item: dict[str, Any], match_text: str) -> bool:
    brand = str(item.get("brand") or "")
    return is_demiand_text(match_text) or is_demiand_text(brand) or brand.strip().lower() == "demiand"


def _market_accept_confidence(confidence: int, item: dict[str, Any], match_text: str) -> tuple[int, str]:
    if str(item.get("price_currency") or "").upper() == "RUB":
        return min(confidence, 40), "wrong_wb_currency_rub_needs_kzt"
    if confidence >= int(matching_cfg().get("minimum_confidence_for_auto_market_record") or 65):
        return confidence, "seed_listing_model_or_alias_match"
    if _brand_ok(item, match_text) and item.get("price"):
        return max(confidence, 65), "wb_brand_sellable_variant"
    return confidence, "seed_listing_soft_match"


def score_listing_cards(listings: list[dict[str, Any]], profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for item in listings:
        title = str(item.get("title") or "")
        title_match_text = " ".join(x for x in [str(item.get("brand") or ""), title] if x).strip()
        # Do not use raw_text for model matching: WB body text can contain neighbouring products.
        # raw_text is still kept below only for reporting/debugging.
        profile, confidence = _best_profile(title_match_text or title, profiles, seed_key=item.get("seed_key"))
        if not profile:
            continue
        confidence, matched_by = _market_accept_confidence(confidence, item, title_match_text or title)
        official_specs = profile.get("official_specs", {}) or {}
        color = detect_color(title, fallback=official_specs.get("color") or _profile_color(profile))
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
            "market_price_currency": item.get("price_currency"),
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
        is_kzt_or_unknown = str(row.get("market_price_currency") or "").upper() != "RUB"
        if conf >= minimum and has_price and is_available and is_kzt_or_unknown:
            accepted.append(row)
        elif conf >= review_min or not is_kzt_or_unknown:
            review.append(row)
        else:
            rejected.append(row)
    return {"accepted": accepted, "review_needed": review, "rejected": rejected}

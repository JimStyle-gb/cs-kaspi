from __future__ import annotations

import re
from typing import Any

from scripts.cs_kaspi.core.text_utils import slugify_ascii

from .common import (
    detect_bundle,
    detect_color,
    is_demiand_text,
    make_market_only_product_key,
    make_market_product_key,
    model_tokens,
    norm_text,
    same_model_score,
    title_fingerprint,
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
        "решетка", "решётка", "шампур", "стакан", "стаканчик", "стаканчики", "бумажн",
        "форма", "корзин", "пергамент", "вкладыш", "поддон", "держатель", "клетка", "аксессуар",
    ),
    "air_fryers": ("аэрогр", "air fryer", "аэрофрит", "гриль"),
}

COLOR_HINTS_BY_KEY = {
    "black": ("черный", "чёрный", "black"),
    "white": ("белый", "white"),
    "metal": ("металл", "металлик", "сереб", "metal", "silver"),
    "beige": ("беж", "beige"),
}

MODEL_CODE_RE = re.compile(r"\b(?:dk|дк|aa|bl|kf)[\s\-/]*(\d{2,5})\b", re.IGNORECASE)


def _seed_category(seed_key: Any) -> str | None:
    return SEED_CATEGORY_BY_KEY.get(str(seed_key or ""))


def _title_category(title: str) -> str | None:
    text = norm_text(title)
    # Accessories must win over generic air-fryer words because accessory titles often contain "для аэрогриля".
    for category in ("air_fryer_accessories", "blenders", "coffee_makers", "ovens", "air_fryers"):
        hints = CATEGORY_HINTS.get(category) or ()
        if any(norm_text(hint) in text for hint in hints):
            return category
    return None


def _fallback_category(title: str, seed_key: Any) -> str:
    return _title_category(title) or _seed_category(seed_key) or "air_fryers"


def _model_from_title(title: str, category_key: str) -> str:
    text = norm_text(title)
    code = MODEL_CODE_RE.search(text)
    if code:
        prefix = code.group(0).lower().replace("дк", "dk")
        prefix = re.sub(r"[^a-z0-9]+", "_", prefix).strip("_")
        return prefix[:48]
    aliases = {
        "demixi": "demixi",
        "tison": "tison",
        "waison": "waison",
        "sanders max": "sanders_max",
        "sanders": "sanders",
        "combo": "combo",
        "duos": "duos",
        "crispo": "crispo",
        "luneo": "luneo",
        "tarvin": "tarvin",
        "sole": "sole",
        "leo": "leo",
    }
    for key, value in aliases.items():
        if key in text:
            return value
    fp = title_fingerprint(title)
    if category_key == "air_fryer_accessories":
        return ("accessory_" + fp)[:58]
    return ("wb_" + fp)[:58]


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


def _best_profile(
    title: str,
    profiles: list[dict[str, Any]],
    *,
    seed_key: Any = None,
    market_color: str | None = None,
) -> tuple[dict[str, Any] | None, int]:
    wanted_category = _title_category(title)
    wanted_color = detect_color(title, fallback=market_color)
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



def _strong_profile_evidence(title: str, profile: dict[str, Any]) -> bool:
    text = norm_text(title)
    if not text:
        return False
    article = norm_text(profile.get("official_article"))
    if article and article in text:
        return True
    mt = model_tokens(str(profile.get("model_key") or ""))
    title_tokens = set(text.split())
    if mt and (mt.issubset(title_tokens) or mt & title_tokens):
        return True
    for alias in profile.get("aliases") or []:
        alias_norm = norm_text(alias)
        if not alias_norm or alias_norm in {"demiand", "демианд"}:
            continue
        words = [w for w in alias_norm.split() if w not in {"demiand", "демианд", "аэрогриль", "для", "с", "и", "в"}]
        if len(words) >= 2 and " ".join(words[: min(6, len(words))]) in text:
            return True
        if len(set(words) & title_tokens) >= 2 and any(w in title_tokens for w in ("aa", "dk", "bl", "kf", "tison", "waison", "demixi", "решетка", "решётка", "шампурами")):
            return True
    return False

def _brand_ok(item: dict[str, Any], match_text: str) -> bool:
    brand = str(item.get("brand") or "")
    return is_demiand_text(match_text) or is_demiand_text(brand) or brand.strip().lower() == "demiand"


def _price_ok(item: dict[str, Any]) -> bool:
    return item.get("price") not in (None, "", 0) and str(item.get("price_currency") or "").upper() == "KZT"


def _market_confidence(item: dict[str, Any], match_text: str, profile_confidence: int) -> tuple[int, str]:
    currency = str(item.get("price_currency") or "").upper()
    if currency == "RUB":
        return min(profile_confidence, 40), "wrong_wb_currency_rub_needs_kzt"
    if item.get("price") and currency != "KZT":
        return min(profile_confidence, 55), "wb_price_currency_unknown_needs_kzt"
    minimum = int(matching_cfg().get("minimum_confidence_for_auto_market_record") or 65)
    if profile_confidence >= minimum:
        return profile_confidence, "official_enrichment_match"
    if _brand_ok(item, match_text) and _price_ok(item):
        return max(profile_confidence, minimum), "wb_demiand_brand_sellable_variant"
    return profile_confidence, "seed_listing_soft_match"


def _market_color(item: dict[str, Any], title: str, fallback: str | None = None) -> str | None:
    return detect_color(title, fallback=str(item.get("market_color") or fallback or "") or None)


def _wb_entity(item: dict[str, Any]) -> str | None:
    return str(item.get("wb_entity") or "").strip() or None


def _market_only_candidate(item: dict[str, Any], title: str, confidence: int, matched_by: str) -> dict[str, Any]:
    category_key = _fallback_category(title, item.get("seed_key"))
    model_key = _model_from_title(title, category_key)
    color = _market_color(item, title)
    bundle = detect_bundle(title)
    signature = variant_signature(model_key=model_key, color=color, bundle=bundle, title=title)
    market_key = make_market_only_product_key(
        supplier_key=str(item.get("supplier_key") or "demiand"),
        category_key=category_key,
        signature=signature,
    )
    return {
        "source": item.get("source"),
        "seed_key": item.get("seed_key"),
        "seed_url": item.get("seed_url"),
        "market_id": item.get("market_id"),
        "wb_root": item.get("wb_root"),
        "wb_supplier_id": item.get("wb_supplier_id"),
        "wb_entity": item.get("wb_entity"),
        "market_url": item.get("url"),
        "market_title": title,
        "market_image": item.get("image"),
        "market_price": item.get("price"),
        "market_price_currency": item.get("price_currency"),
        "market_available": item.get("available"),
        "market_stock": item.get("stock"),
        "eta_text": item.get("eta_text"),
        "lead_time_days": item.get("lead_time_days"),
        "supplier_key": item.get("supplier_key") or "demiand",
        "category_key": category_key,
        "brand": "DEMIAND",
        "model_key": model_key,
        "base_product_key": None,
        "official_article": None,
        "official_title": None,
        "official_url": None,
        "market_color": color,
        "market_bundle": bundle,
        "variant_signature": signature,
        "market_product_key": market_key,
        "match_confidence": confidence,
        "matched_by": matched_by,
        "official_match_status": "missing_or_not_confident_official_used_as_optional_enrichment_only",
        "raw": item,
    }


def _official_enriched_candidate(item: dict[str, Any], profile: dict[str, Any], title: str, confidence: int, matched_by: str) -> dict[str, Any]:
    official_specs = profile.get("official_specs", {}) or {}
    color = _market_color(item, title, fallback=official_specs.get("color") or _profile_color(profile))
    bundle = detect_bundle(title)
    model_key = str(profile.get("model_key") or "")
    signature = variant_signature(model_key=model_key, color=color, bundle=bundle, title=title)
    base_key = str(profile.get("base_product_key") or "")
    market_key = make_market_product_key(base_product_key=base_key, signature=signature)
    return {
        "source": item.get("source"),
        "seed_key": item.get("seed_key"),
        "seed_url": item.get("seed_url"),
        "market_id": item.get("market_id"),
        "wb_root": item.get("wb_root"),
        "wb_supplier_id": item.get("wb_supplier_id"),
        "wb_entity": item.get("wb_entity"),
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
        "brand": profile.get("brand") or "DEMIAND",
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
        "official_match_status": "matched_for_enrichment",
        "raw": item,
    }


def score_listing_cards(listings: list[dict[str, Any]], profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    minimum = int(matching_cfg().get("minimum_confidence_for_auto_market_record") or 65)
    allow_market_only = matching_cfg().get("allow_market_only_when_official_missing", True) is not False
    for item in listings:
        title = str(item.get("title") or "")
        title_match_text = " ".join(x for x in [str(item.get("brand") or ""), title] if x).strip()
        match_text = title_match_text or title
        if not _brand_ok(item, match_text):
            continue

        profile, profile_confidence = _best_profile(
            match_text,
            profiles,
            seed_key=item.get("seed_key"),
            market_color=str(item.get("market_color") or "") or None,
        )
        confidence, matched_by = _market_confidence(item, match_text, profile_confidence)

        # Official is optional enrichment. If confidence is weak or only category/brand based,
        # do not force a wrong official model.
        if profile and profile_confidence >= minimum and _strong_profile_evidence(match_text, profile):
            scored.append(_official_enriched_candidate(item, profile, title, confidence, matched_by))
        elif allow_market_only:
            scored.append(_market_only_candidate(item, title, confidence, matched_by))
        elif profile:
            scored.append(_official_enriched_candidate(item, profile, title, confidence, matched_by))
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
        is_kzt = str(row.get("market_price_currency") or "").upper() == "KZT"
        if conf >= minimum and has_price and is_available and is_kzt:
            accepted.append(row)
        elif conf >= review_min or not is_kzt:
            review.append(row)
        else:
            rejected.append(row)
    return {"accepted": accepted, "review_needed": review, "rejected": rejected}

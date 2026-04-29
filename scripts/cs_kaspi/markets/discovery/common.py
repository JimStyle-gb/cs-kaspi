from __future__ import annotations

import re
from typing import Any

from scripts.cs_kaspi.core.text_utils import normalize_spaces, slugify_ascii

_WORD_RE = re.compile(r"[^a-z0-9а-яё]+", re.IGNORECASE)

COLOR_WORDS = {
    "black": "black", "черный": "black", "чёрный": "black", "черн": "black",
    "white": "white", "белый": "white", "бел": "white",
    "metal": "metal", "металл": "metal", "металлик": "metal", "silver": "metal", "серебро": "metal",
    "beige": "beige", "беж": "beige", "бежевый": "beige",
    "ash": "ash", "пепельный": "ash", "пепел": "ash",
    "caramel": "caramel", "карамель": "caramel",
    "chocolate": "chocolate", "шоколад": "chocolate",
}

BUNDLE_HINTS = [
    "шампур", "шампуры", "набор", "комплект", "аксессуар", "аксессуары",
    "решетка", "решётка", "клетка", "тост", "форма", "пергамент", "корзина",
    "две чаши", "2 чаш", "двумя чаш", "сковород", "гриль",
]

TYPE_HINTS = {
    "air_fryers": ("аэрогр", "air fryer", "аэрофрит", "гриль"),
    "coffee_makers": ("кофевар", "кофемаш", "coffee", "капучин"),
    "blenders": ("блендер", "измельч", "смешив"),
    "ovens": ("печь", "мини печ", "духов"),
    "air_fryer_accessories": ("аксессуар", "шампур", "клетка", "тост", "форма", "пергамент", "решет"),
}


def norm_text(value: Any) -> str:
    text = normalize_spaces(str(value or "")).lower().replace("ё", "е")
    text = _WORD_RE.sub(" ", text)
    return " ".join(text.split())


def tokens(value: Any) -> set[str]:
    return {x for x in norm_text(value).split() if len(x) >= 2}


def contains_brand(title: str, brand: str) -> bool:
    if not brand:
        return True
    return norm_text(brand) in norm_text(title)


def model_tokens(model_key: str) -> set[str]:
    raw = str(model_key or "").replace("_", " ")
    stop = {"wifi", "wi", "fi", "white", "black", "metal", "beige", "ash", "caramel", "chocolate"}
    return {t for t in tokens(raw) if t not in stop}


def detect_color(title: str, fallback: str | None = None) -> str | None:
    title_tokens = set(norm_text(title).split())
    for word, key in COLOR_WORDS.items():
        if norm_text(word) in title_tokens:
            return key
    return fallback or None


def detect_bundle(title: str) -> str | None:
    text = norm_text(title)
    found = [hint for hint in BUNDLE_HINTS if norm_text(hint) in text]
    if not found:
        return None
    return "_".join(slugify_ascii(x) for x in found[:5] if x)


def category_score(title: str, category_key: str | None) -> int:
    if not category_key:
        return 0
    text = norm_text(title)
    hints = TYPE_HINTS.get(category_key) or ()
    return 10 if any(norm_text(hint) in text for hint in hints) else 0


def variant_signature(*, model_key: str, color: str | None, bundle: str | None, title: str | None = None) -> str:
    parts = [slugify_ascii(model_key)]
    if color:
        parts.append(slugify_ascii(color))
    if bundle:
        parts.append(slugify_ascii(bundle))
    if len(parts) == 1 and title:
        parts.append(slugify_ascii(title)[:32])
    return "__".join([p for p in parts if p])


def same_model_score(*, title: str, brand: str, model_key: str, category_key: str | None = None) -> int:
    title_norm = norm_text(title)
    score = 0
    if contains_brand(title, brand):
        score += 25
    mt = model_tokens(model_key)
    title_tokens = tokens(title_norm)
    if mt and mt.issubset(title_tokens):
        score += 55
    elif mt and mt & title_tokens:
        score += 25
    if "demiand" in title_norm:
        score += 10
    score += category_score(title, category_key)
    return min(score, 100)


def make_market_product_key(*, base_product_key: str, signature: str) -> str:
    # Do not include Ozon/WB source here: same variant from both marketplaces
    # must collapse into one Kaspi candidate and use the lowest source price.
    key = f"{base_product_key}__mv_{slugify_ascii(signature)[:48]}"
    return slugify_ascii(key)[:120]

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
    "две чаши", "2 чаш", "двумя чаш", "сковород", "гриль", "чаша", "противень",
    "стаканчик", "стаканчики", "фильтр", "поддон", "вкладыш", "вкладыши",
]

TYPE_HINTS = {
    "air_fryers": ("аэрогр", "air fryer", "аэрофрит", "гриль"),
    "coffee_makers": ("кофевар", "кофемаш", "coffee", "капучин"),
    "blenders": ("блендер", "суповар", "измельч", "смешив"),
    "ovens": ("печь", "мини печ", "духов"),
    "air_fryer_accessories": (
        "аксессуар", "шампур", "клетка", "тост", "форма", "пергамент", "решет",
        "решёт", "корзин", "чаша", "поддон", "вкладыш", "противень", "стаканчик",
    ),
}

GENERIC_ALIAS_WORDS = {
    "demiand", "аэрогриль", "блендер", "суповарка", "аксессуар", "аксессуары",
    "кофеварка", "печь", "товар", "кухонный", "кухонная", "электрический",
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


def is_demiand_text(value: Any) -> bool:
    return "demiand" in norm_text(value) or "демианд" in norm_text(value)


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
    return "_".join(slugify_ascii(x) for x in found[:7] if x)


def category_score(title: str, category_key: str | None) -> int:
    if not category_key:
        return 0
    text = norm_text(title)
    hints = TYPE_HINTS.get(category_key) or ()
    return 10 if any(norm_text(hint) in text for hint in hints) else 0


def title_fingerprint(title: str | None) -> str:
    """Stable fingerprint for one sellable WB variant.

    We deliberately keep the market title in the signature: different colors,
    комплектации, наборы and accessories must become separate Kaspi candidates.
    Only exact/near-exact same WB variants collapse later by lowest price.
    """
    text = norm_text(title or "")
    words = [w for w in text.split() if w not in {"demiand", "демианд", "с", "и", "для", "в", "на"}]
    return slugify_ascii(" ".join(words))[:72] or "variant"


def variant_signature(*, model_key: str, color: str | None, bundle: str | None, title: str | None = None) -> str:
    parts = [slugify_ascii(model_key)]
    if color:
        parts.append(slugify_ascii(color))
    if bundle:
        parts.append(slugify_ascii(bundle))
    if title:
        parts.append(title_fingerprint(title))
    return "__".join([p for p in parts if p])


def alias_score(title: str, aliases: list[Any] | tuple[Any, ...] | None) -> int:
    title_norm = norm_text(title)
    if not title_norm:
        return 0
    best = 0
    for alias in aliases or []:
        alias_norm = norm_text(alias)
        if not alias_norm or alias_norm in GENERIC_ALIAS_WORDS:
            continue
        alias_words = [w for w in alias_norm.split() if w not in GENERIC_ALIAS_WORDS]
        if not alias_words:
            continue
        compact_alias = " ".join(alias_words)
        if len(compact_alias) < 3:
            continue
        if compact_alias in title_norm:
            best = max(best, 60)
            continue
        overlap = set(alias_words) & set(title_norm.split())
        if len(overlap) >= 2:
            best = max(best, 45)
        elif overlap:
            best = max(best, 25)
    return best


def same_model_score(*, title: str, brand: str, model_key: str, category_key: str | None = None, aliases: list[Any] | None = None) -> int:
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
    score = max(score, alias_score(title, aliases))
    if "demiand" in title_norm or "демианд" in title_norm:
        score += 10
    score += category_score(title, category_key)
    return min(score, 100)


def make_market_product_key(*, base_product_key: str, signature: str) -> str:
    # Same exact WB variant from duplicated WB listings collapses by this key.
    # Different colors/sets/bundles/accessories keep different title fingerprints.
    key = f"{base_product_key}__mv_{slugify_ascii(signature)[:80]}"
    return slugify_ascii(key)[:140]

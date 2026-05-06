from __future__ import annotations

import re
from typing import Any

from scripts.cs_kaspi.core.text_utils import normalize_spaces, slugify_ascii

_WORD_RE = re.compile(r"[^a-z0-9а-яё]+", re.IGNORECASE)

COLOR_WORDS = {
    "black": "black", "черный": "black", "чёрный": "black", "черн": "black",
    "white": "white", "белый": "white", "белая": "white", "бел": "white",
    "grey": "grey", "gray": "grey", "серый": "grey", "серая": "grey", "сер": "grey",
    "metal": "metal", "металл": "metal", "металлик": "metal", "silver": "metal", "серебро": "metal", "серебристый": "metal",
    "beige": "beige", "беж": "beige", "бежевый": "beige", "бежевая": "beige",
    "brown": "brown", "коричневый": "brown", "коричневая": "brown", "коричнев": "brown",
    "red": "red", "красный": "red", "красная": "red",
    "green": "green", "зеленый": "green", "зелёный": "green", "зеленая": "green", "зелёная": "green",
    "blue": "blue", "синий": "blue", "синяя": "blue", "голубой": "blue",
    "ash": "ash", "пепельный": "ash", "пепел": "ash",
    "caramel": "caramel", "карамель": "caramel",
    "chocolate": "chocolate", "шоколад": "chocolate",
}

_COLOR_ORDER = [
    "black", "white", "grey", "metal", "beige", "brown", "red", "green", "blue",
    "ash", "caramel", "chocolate",
]

BUNDLE_HINTS = [
    "шампур", "шампуры", "набор", "комплект", "аксессуар", "аксессуары",
    "решетка", "решётка", "клетка", "тост", "форма", "пергамент", "корзина",
    "две чаши", "2 чаш", "двумя чаш", "сковород", "гриль", "чаша", "противень",
    "стаканчик", "стаканчики", "стакан", "стаканы", "фильтр", "поддон", "вкладыш", "вкладыши",
    "4 шампур", "5 шампур", "2 тэна", "2 тэн", "два тэна", "двумя тен",
]

TYPE_HINTS = {
    "air_fryers": ("аэрогр", "air fryer", "аэрофрит", "гриль"),
    "coffee_maker_accessories": ("стаканчик", "стаканчики", "бумажн", "для кофевар", "для кофемаш"),
    "coffee_makers": ("кофевар", "кофемаш", "coffee", "капучин"),
    "blenders": ("блендер", "суповар", "измельч", "смешив"),
    "ovens": ("печь", "мини печ", "духов"),
    "air_fryer_accessories": (
        "аксессуар", "шампур", "клетка", "тост", "форма", "пергамент", "решет",
        "решёт", "корзин", "чаша", "поддон", "вкладыш", "противень",
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
    stop = {"wifi", "wi", "fi", "white", "black", "grey", "metal", "beige", "ash", "caramel", "chocolate"}
    return {t for t in tokens(raw) if t not in stop}


def _find_colors(value: Any) -> list[str]:
    source_tokens = set(norm_text(value).split())
    found: list[str] = []
    for word, key in COLOR_WORDS.items():
        if norm_text(word) in source_tokens and key not in found:
            found.append(key)
    found.sort(key=lambda x: _COLOR_ORDER.index(x) if x in _COLOR_ORDER else 999)
    return found


def detect_color(title: str, fallback: str | None = None) -> str | None:
    # Title color wins; WB API color is used as fallback when title has no explicit color.
    title_colors = _find_colors(title)
    if title_colors:
        return "_".join(title_colors[:3])
    fallback_colors = _find_colors(fallback)
    if fallback_colors:
        return "_".join(fallback_colors[:3])
    return fallback or None


def detect_bundle(title: str) -> str | None:
    text = norm_text(title)
    found = [hint for hint in BUNDLE_HINTS if norm_text(hint) in text]
    if not found:
        return None
    return "_".join(slugify_ascii(x) for x in found[:10] if x)


def category_score(title: str, category_key: str | None) -> int:
    if not category_key:
        return 0
    text = norm_text(title)
    hints = TYPE_HINTS.get(category_key) or ()
    return 10 if any(norm_text(hint) in text for hint in hints) else 0


def _canonical_variant_text(title: str | None) -> str:
    text = norm_text(title or "")
    # Canonicalize WB title noise/typos without hiding real sellable differences such as color, kit or accessory type.
    replacements = {
        "wi fi": "wifi",
        "wi-fi": "wifi",
        "тэнaми": "тенами",
        "тэнaм": "тенами",
        "тэнами": "тенами",
        "тэнам": "тенами",
        "тенaми": "тенами",
        "14 5л": "14 5 л",
        "7 в 1": "7 1",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = normalize_spaces(text)
    return text


def title_fingerprint(title: str | None) -> str:
    """Stable fingerprint for one sellable WB variant.

    Different colors, комплект, наборы and accessories must remain separate Kaspi candidates.
    Pure WB spelling noise/typos must collapse, for example "2 тэнaм" and "2 тэнaми".
    """
    text = _canonical_variant_text(title)
    stop_words = {"demiand", "демианд", "с", "и", "для", "в", "на"}
    words = [w for w in text.split() if w not in stop_words]
    return slugify_ascii(" ".join(words))[:72] or "variant"


def variant_signature(
    *,
    model_key: str,
    color: str | None,
    bundle: str | None,
    title: str | None = None,
    wb_entity: str | None = None,
) -> str:
    # The signature is intentionally strict enough to keep sellable WB variations separate.
    # Same exact variant from several WB cards/sellers still collapses by this key; lowest price wins later.
    parts = [slugify_ascii(model_key)]
    if color:
        parts.append(slugify_ascii(color))
    if wb_entity:
        parts.append(slugify_ascii(wb_entity)[:32])
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
    key = f"{base_product_key}__mv_{slugify_ascii(signature)[:80]}"
    return slugify_ascii(key)[:118]


def make_market_only_product_key(*, supplier_key: str, category_key: str, signature: str) -> str:
    key = f"{supplier_key}_{category_key}__wb_{slugify_ascii(signature)[:88]}"
    return slugify_ascii(key)[:118]

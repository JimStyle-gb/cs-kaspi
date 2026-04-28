from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.text_utils import limit_text, normalize_spaces
from scripts.cs_kaspi.core.yaml_io import read_yaml

COLOR_RU = {
    "black": "черный",
    "white": "белый",
    "metal": "металлик",
    "beige": "бежевый",
    "ash": "пепельный",
    "caramel": "карамель",
    "chocolate": "шоколадный",
}

CATEGORY_TITLE_RU = {
    "air_fryer_accessories": "аксессуар для аэрогриля",
    "air_fryers": "аэрогриль",
    "blenders": "блендер",
    "coffee_makers": "кофеварка",
    "ovens": "печь",
}


def _kaspi_config() -> dict[str, Any]:
    return read_yaml(ROOT / "config" / "kaspi.yml")


def _title_policy() -> dict[str, Any]:
    return (_kaspi_config().get("title_policy", {}) or {})


def _title_max_length() -> int:
    config = _kaspi_config()
    defaults = config.get("defaults", {}) or {}
    return int(defaults.get("title_max_length") or 120)


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _clean_source_title(title: str, brand: str) -> str:
    title = normalize_spaces(title)
    if not title:
        return ""

    # Убираем повтор бренда только в начале, чтобы не получить "VAITAN Demiand DEMIAND ...".
    brand_variants = {brand, brand.upper(), brand.lower(), brand.title(), "DEMIAND", "Demiand", "Демианд"}
    for variant in sorted(brand_variants, key=len, reverse=True):
        if title.lower().startswith(variant.lower() + " "):
            return normalize_spaces(title[len(variant):])
    return title


def _contains_word(title: str, word: str) -> bool:
    return word.lower() in title.lower()


def _ensure_vaitan_brand(title: str, brand: str) -> str:
    policy = _title_policy()
    prefix = str(policy.get("title_prefix") or "VAITAN").strip()
    use_vaitan = policy.get("use_vaitan_in_title", True) is not False
    brand_clean = brand.title() if brand else "Demiand"

    title = normalize_spaces(title)
    if use_vaitan and not title.lower().startswith(prefix.lower()):
        title = normalize_spaces(f"{prefix} {title}")

    if brand_clean and brand_clean.lower() not in title.lower():
        if use_vaitan and title.lower().startswith(prefix.lower()):
            title = normalize_spaces(f"{prefix} {brand_clean} {title[len(prefix):].strip()}")
        else:
            title = normalize_spaces(f"{brand_clean} {title}")

    return title


def run(product: dict[str, Any]) -> str:
    official = product.get("official", {}) or {}
    specs = official.get("specs", {}) or {}
    model_specs = product.get("model_specs", {}) or {}
    template = model_specs.get("title_template")
    brand = product.get("brand") or official.get("brand") or "Demiand"
    max_length = _title_max_length()

    values = {
        "color": COLOR_RU.get(specs.get("color"), specs.get("color") or ""),
        "volume_l": _fmt(specs.get("volume_l")),
        "programs": _fmt(specs.get("programs")),
        "power_w": _fmt(specs.get("power_w")),
    }

    title = ""
    if template:
        try:
            title = normalize_spaces(template.format(**values))
        except Exception:
            title = ""

    if not title:
        source_title = official.get("title_official") or product.get("listing_snapshot", {}).get("title_listing") or "Товар"
        source_title = _clean_source_title(str(source_title), str(brand))
        category_name = CATEGORY_TITLE_RU.get(product.get("category_key"), "товар")
        title = normalize_spaces(f"{brand.title()} {source_title}")
        if category_name and not _contains_word(title, category_name):
            title = normalize_spaces(f"{title} {category_name}")

    title = _ensure_vaitan_brand(title, str(brand))
    return limit_text(title, max_length)

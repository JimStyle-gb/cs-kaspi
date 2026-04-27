from __future__ import annotations

from scripts.cs_kaspi.core.text_utils import limit_text, normalize_spaces

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


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def run(product: dict) -> str:
    official = product.get("official", {})
    specs = official.get("specs", {}) or {}
    model_specs = product.get("model_specs", {}) or {}
    template = model_specs.get("title_template")

    values = {
        "color": COLOR_RU.get(specs.get("color"), specs.get("color") or ""),
        "volume_l": _fmt(specs.get("volume_l")),
        "programs": _fmt(specs.get("programs")),
        "power_w": _fmt(specs.get("power_w")),
    }

    if template:
        try:
            title = template.format(**values)
            return limit_text(title, 120)
        except Exception:
            pass

    source_title = official.get("title_official") or product.get("listing_snapshot", {}).get("title_listing") or "Товар"
    source_title = normalize_spaces(source_title)
    if source_title.lower().startswith("vaitan"):
        return limit_text(source_title, 120)

    category_name = CATEGORY_TITLE_RU.get(product.get("category_key"), "товар")
    brand = product.get("brand") or "DEMIAND"
    title = f"VAITAN {brand.title()} {source_title}"
    if category_name not in title.lower():
        title = f"{title} {category_name}"
    return limit_text(title, 120)

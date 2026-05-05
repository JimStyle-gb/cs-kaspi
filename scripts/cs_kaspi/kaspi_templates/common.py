from __future__ import annotations

import html
import re
from functools import lru_cache
from typing import Any

from scripts.cs_kaspi.core.hash_utils import stable_hash
from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.text_utils import clean_html_text, limit_text, normalize_spaces
from scripts.cs_kaspi.core.yaml_io import read_yaml

TEMPLATE_BY_CATEGORY = {
    "air_fryers": "air_fryers",
    "blenders": "blenders",
    "air_fryer_accessories": "accessories_small_kitchen",
    "coffee_maker_accessories": "accessories_small_kitchen",
    "ovens": "tabletop_ovens",
}

COLOR_MAP = {
    "black": "черный",
    "white": "белый",
    "grey": "серый",
    "gray": "серый",
    "metal": "серый",
    "metallic": "серый",
    "beige": "бежевый",
    "brown": "коричневый",
    "red": "красный",
    "green": "зеленый",
    "blue": "синий",
    "ash": "серый",
    "caramel": "коричневый",
    "chocolate": "коричневый",
    "black_white": "черный, белый",
    "white_black": "белый, черный",
}


@lru_cache(maxsize=1)
def _categories_config() -> dict[str, Any]:
    return read_yaml(ROOT / "config" / "categories.yml").get("categories", {}) or {}


def template_key_for_category(category_key: str | None) -> str:
    if not category_key:
        return ""
    categories = _categories_config()
    kaspi = (categories.get(category_key, {}) or {}).get("kaspi", {}) or {}
    return str(kaspi.get("template_key") or TEMPLATE_BY_CATEGORY.get(category_key) or "").strip()


@lru_cache(maxsize=16)
def load_template(template_key: str) -> dict[str, Any]:
    if not template_key:
        return {}
    return read_yaml(ROOT / "config" / "kaspi_templates" / f"{template_key}.yml")


def field_codes(template: dict[str, Any]) -> list[str]:
    return [str(field.get("code") or "") for field in template.get("fields", []) if field.get("code")]


def field_name_by_code(template: dict[str, Any]) -> dict[str, str]:
    return {str(field.get("code") or ""): str(field.get("name_ru") or "") for field in template.get("fields", []) if field.get("code")}


def field_by_name(template: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(field.get("name_ru") or ""): field for field in template.get("fields", []) if field.get("name_ru")}


def code_for(template: dict[str, Any], name_ru: str) -> str:
    return str(field_by_name(template).get(name_ru, {}).get("code") or "")


def allowed_values(template: dict[str, Any], name_ru: str) -> set[str]:
    values = (template.get("value_lists", {}) or {}).get(name_ru, []) or []
    return {str(value).strip() for value in values if str(value).strip()}


def put(row: dict[str, Any], template: dict[str, Any], name_ru: str, value: Any) -> None:
    code = code_for(template, name_ru)
    if not code:
        return
    if value in (None, "", [], {}):
        row[code] = ""
        return
    if isinstance(value, bool):
        row[code] = "TRUE" if value else "FALSE"
    elif isinstance(value, float) and value.is_integer():
        row[code] = int(value)
    else:
        row[code] = normalize_spaces(str(value))


def merchant_sku(product: dict[str, Any]) -> str:
    match = product.get("kaspi_match", {}) or {}
    existing = normalize_spaces(str(match.get("kaspi_sku") or ""))
    if existing:
        return existing
    basis = {
        "product_key": product.get("product_key"),
        "variant": (product.get("market", {}) or {}).get("market_variant_signature") or product.get("variant_key"),
        "url": (product.get("market", {}) or {}).get("market_url"),
    }
    return "VT-" + stable_hash(basis).upper()[:12]


def plain_description(product: dict[str, Any], title: str) -> str:
    official = product.get("official", {}) or {}
    market = product.get("market", {}) or {}
    specs = official.get("specs", {}) or {}
    raw = official.get("short_description") or official.get("description_official") or ""
    base = clean_html_text(html.unescape(str(raw)))
    lines = [title]
    if base:
        lines.append(base)
    else:
        lines.append("Товар DEMIAND подготовлен для карточки VAITAN на основе подтвержденного WB-варианта и официальных характеристик поставщика.")
    extra = []
    if market.get("market_title"):
        extra.append(f"WB-вариант: {market.get('market_title')}")
    if specs.get("article"):
        extra.append(f"Артикул: {specs.get('article')}")
    if specs.get("power_w"):
        extra.append(f"Мощность: {number(specs.get('power_w'))} Вт")
    if specs.get("volume_l"):
        extra.append(f"Объем: {number(specs.get('volume_l'))} л")
    if specs.get("programs"):
        extra.append(f"Количество программ: {number(specs.get('programs'))}")
    color = normalize_color(market.get("market_color") or specs.get("color"))
    if color:
        extra.append(f"Цвет: {color}")
    if specs.get("warranty_text"):
        extra.append(f"Гарантия: {specs.get('warranty_text')}")
    if extra:
        lines.append("; ".join(extra) + ".")
    text = normalize_spaces(". ".join(x.strip(" .") for x in lines if x))
    if len(text) < 100:
        text = normalize_spaces(text + " Подходит для ежедневного использования дома, помогает быстро готовить и удобно подбирать товар по характеристикам.")
    return limit_text(text, 7000)


def number(value: Any, default: Any = "") -> Any:
    if value in (None, "", [], {}):
        return default
    try:
        f = float(str(value).replace(",", "."))
        return int(f) if f.is_integer() else f
    except Exception:
        return value


def first_number(text: str, *, suffixes: tuple[str, ...] = ()) -> float | None:
    raw = str(text or "")
    if suffixes:
        suffix = "|".join(re.escape(s) for s in suffixes)
        pattern = rf"(\d+(?:[\.,]\d+)?)\s*(?:{suffix})"
    else:
        pattern = r"(\d+(?:[\.,]\d+)?)"
    m = re.search(pattern, raw, flags=re.IGNORECASE)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def normalize_color(value: Any) -> str:
    raw = normalize_spaces(str(value or "")).lower().replace("ё", "е")
    if not raw:
        return ""
    raw = raw.replace("/", "_").replace("-", "_")
    if raw in COLOR_MAP:
        return COLOR_MAP[raw]
    parts = [p for p in raw.split("_") if p]
    if len(parts) > 1:
        mapped = [COLOR_MAP.get(p, p) for p in parts]
        return ", ".join(dict.fromkeys(mapped))
    return COLOR_MAP.get(raw, raw)


def text_blob(product: dict[str, Any]) -> str:
    official = product.get("official", {}) or {}
    market = product.get("market", {}) or {}
    specs = official.get("specs", {}) or {}
    values = [
        product.get("product_key"), product.get("category_key"), product.get("model_key"), product.get("brand"),
        official.get("title_official"), official.get("description_official"), official.get("short_description"),
        market.get("market_title"), market.get("market_bundle"), market.get("market_variant_signature"),
        specs.get("article"), specs.get("control_type"), specs.get("product_dimensions_text"), specs.get("package_dimensions_text"),
    ]
    return normalize_spaces(" ".join(str(v or "") for v in values)).lower().replace("ё", "е")


def contains_any(text: str, needles: list[str]) -> bool:
    return any(n.lower().replace("ё", "е") in text for n in needles)


def base_row(product: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    kaspi = product.get("kaspi_policy", {}) or {}
    title = normalize_spaces(str(kaspi.get("kaspi_title") or (product.get("market", {}) or {}).get("market_title") or (product.get("official", {}) or {}).get("title_official") or ""))
    sku = merchant_sku(product)
    row = {code: "" for code in field_codes(template)}
    put(row, template, "Артикул", sku)
    put(row, template, "Название товара", title)
    put(row, template, "Бренд", "DEMIAND")
    put(row, template, "Код изображений", sku)
    images = kaspi.get("kaspi_images") or []
    put(row, template, "Ссылка на картинку", ", ".join(str(x) for x in images[:10] if x))
    put(row, template, "Описание (мин. 100 символов, макс. 7 000 символов)", plain_description(product, title))
    specs = (product.get("official", {}) or {}).get("specs", {}) or {}
    if specs.get("weight_kg"):
        put(row, template, "Вес для расчета логистики", number(specs.get("weight_kg")))
        put(row, template, "Вес", number(specs.get("weight_kg")))
    return row

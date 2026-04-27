from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.text_utils import normalize_spaces
from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.core.yaml_io import read_yaml

from .utils import build_product_key, state_paths


def _number(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d+[\.,]?\d*)", str(text))
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def _normalize_color(text: str | None) -> str | None:
    value = (text or "").lower()
    if "чер" in value or "black" in value:
        return "black"
    if "бел" in value or "white" in value:
        return "white"
    if "сер" in value or "метал" in value or "silver" in value:
        return "metal"
    if "беж" in value:
        return "beige"
    return None


def _clean_article(article: str | None) -> str | None:
    if not article:
        return None
    article = re.split(r"(?:Категори[яи]:|Метк[аи]:)", article, maxsplit=1)[0]
    article = normalize_spaces(article).strip(" ,;-")
    return article or None


def _load_model_specs(supplier_key: str, category_key: str | None) -> dict[str, Any]:
    if not category_key:
        return {}
    path = ROOT / "config" / "model_specs" / f"{supplier_key}_{category_key}.yml"
    return read_yaml(path)


def _match_model(title: str, article: str | None, models: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    title_lower = (title or "").lower()
    article_lower = (_clean_article(article) or "").lower()
    best_score = -1
    best_key: str | None = None
    best_cfg: dict[str, Any] | None = None
    for key, cfg in models.items():
        if cfg.get("enabled") is False:
            continue
        aliases = [str(a).lower() for a in cfg.get("aliases", [])]
        patterns = [str(p).lower() for p in cfg.get("identity", {}).get("article_patterns", [])]
        for candidate in aliases + patterns:
            if candidate and (candidate in title_lower or candidate in article_lower):
                score = len(candidate)
                if score > best_score:
                    best_score = score
                    best_key = key
                    best_cfg = cfg
    return best_key, best_cfg


def _guess_model_from_article(article: str | None) -> str | None:
    text = (_clean_article(article) or "").lower()
    mapping = {
        "dk-2400": "sanders_max",
        "dk-2200": "sanders",
        "dk-1416": "tison",
        "dk-1800": "waison",
    }
    for token, model_key in mapping.items():
        if token in text:
            return model_key
    return None


def _guess_model_from_title(title: str) -> str | None:
    text = (title or "").lower()
    for model in ("sanders max", "sanders", "tison", "waison", "luneo", "tarvin", "leo", "duos", "combo", "crispo", "raung"):
        if model in text:
            return model.replace(" ", "_")
    return None


def _color_from_identity(title: str, article: str | None, specs_raw: dict[str, Any]) -> str | None:
    """
    Цвет для variant/model identity берём сначала из артикула и названия.

    На official-сайте Demiand у некоторых товаров встречается конфликт:
    в артикуле/названии указан один цвет, а в таблице характеристик — другой.
    Для стабильного product_key важнее артикул и название, потому что именно они
    отличают отдельные карточки товара.
    """
    identity_text = f"{article or ''} {title or ''}"
    return _normalize_color(identity_text) or _normalize_color(specs_raw.get("Цвет"))


def _guess_variant(title: str, article: str | None, specs_raw: dict[str, Any]) -> str | None:
    parts: list[str] = []
    text = f"{title} {article or ''} {specs_raw.get('Цвет', '')}".lower()
    if "wifi" in text or "wi-fi" in text:
        parts.append("wifi")
    color = _color_from_identity(title, article, specs_raw)
    if color:
        parts.append(color)
    return "_".join(parts) if parts else None


def _guess_accessory_kind(title: str) -> str | None:
    text = (title or "").lower().replace("ё", "е")
    patterns = [
        (r"тост", "toast_holder"),
        (r"шампур", "skewer_holder"),
        (r"поддон", "oil_tray"),
        (r"решетк", "rack"),
        (r"форма.*выпеч", "baking_pan"),
        (r"камн", "pizza_stone"),
        (r"щипц", "tongs"),
        (r"вертел", "rotisserie_spit"),
        (r"корзин", "basket"),
        (r"против", "tray"),
        (r"клетк", "steak_cage"),
    ]
    for pattern, kind in patterns:
        if re.search(pattern, text):
            return kind
    return None


def _extract_compatibility_models(title: str, article: str | None) -> list[str]:
    text = f"{title} {article or ''}".lower()
    found: list[str] = []
    for source, target in [
        ("sanders max", "sanders_max"),
        ("sanders", "sanders"),
        ("tison", "tison"),
        ("waison", "waison"),
        ("leo", "leo"),
        ("tarvin", "tarvin"),
        ("luneo", "luneo"),
    ]:
        if source in text and target not in found:
            found.append(target)
    return found


def run(parsed_products_payload: dict[str, Any]) -> dict[str, Any]:
    normalized_products: list[dict[str, Any]] = []

    for product in parsed_products_payload.get("products", []):
        row = deepcopy(product)
        official = row["official"]
        article = _clean_article(official.get("product_id"))
        official["product_id"] = article
        title = official.get("title_official") or ""
        specs_raw = official.get("specs_raw", {}) or {}
        category_key = row.get("category_key")

        spec_data = _load_model_specs(row.get("supplier_key", "demiand"), category_key)
        model_key, model_cfg = _match_model(title, article, spec_data.get("models", {}))
        model_key = model_key or _guess_model_from_article(article) or _guess_model_from_title(title) or row.get("model_key") or official.get("slug")
        variant_key = _guess_variant(title, article, specs_raw)

        row["model_key"] = model_key
        row["variant_key"] = variant_key

        normalized_specs = {
            "article": article,
            "power_w": _number(specs_raw.get("Мощность")),
            "volume_l": _number(specs_raw.get("Объем камеры") or specs_raw.get("Объём") or specs_raw.get("Объем")),
            "programs": int(_number(specs_raw.get("Количество программ")) or 0) or None,
            "color": _color_from_identity(title, article, specs_raw),
            "control_type": specs_raw.get("Управление"),
            "temperature_range_text": specs_raw.get("Температура"),
            "timer_range_text": specs_raw.get("Время"),
            "delayed_start": specs_raw.get("Отложенный старт"),
            "weight_kg": _number(specs_raw.get("Вес аэрогриля") or specs_raw.get("Вес")),
            "package_dimensions_text": specs_raw.get("Габариты"),
            "product_dimensions_text": specs_raw.get("Размеры аэрогриля (ДхШхВ)"),
            "warranty_text": specs_raw.get("Гарантия"),
            "service_life_text": specs_raw.get("Срок службы"),
            "wifi": True if "wifi" in f"{title} {article or ''}".lower() or "wi-fi" in f"{title} {article or ''}".lower() else None,
        }
        official["specs"] = {k: v for k, v in normalized_specs.items() if v not in (None, "", 0)}

        package = official.get("package", {}) or {}
        raw_text = package.get("raw_text", "") or ""
        package["recipe_book"] = "книга рецептов" in raw_text.lower()
        acc_match = re.search(r"(\d+)\s+аксесс", raw_text.lower())
        if acc_match:
            package["accessories_count"] = int(acc_match.group(1))
        official["package"] = package

        if category_key == "air_fryer_accessories":
            compatibility = {
                "models": _extract_compatibility_models(title, article),
                "article": article,
                "accessory_kind": _guess_accessory_kind(title),
            }
            row["compatibility"] = compatibility
            accessory_base = article or compatibility.get("accessory_kind") or official.get("slug") or title
            row["product_key"] = build_product_key(category_key or "product", accessory_base, article=article)
        else:
            row["product_key"] = build_product_key(category_key or "product", official.get("slug") or title, model_key=model_key, variant_key=variant_key, article=article)

        row["model_specs"] = {
            "exists": bool(model_cfg),
            "spec_file": f"config/model_specs/{row.get('supplier_key', 'demiand')}_{category_key}.yml" if spec_data else None,
            "canonical_model_name": model_cfg.get("canonical_model_name") if model_cfg else None,
            "title_template": model_cfg.get("kaspi_identity", {}).get("title_template") if model_cfg else None,
            "group_key": model_cfg.get("kaspi_identity", {}).get("group_key") if model_cfg else None,
            "specs_override": model_cfg.get("known_specs", {}) if model_cfg else {},
            "content_blocks": model_cfg.get("content_defaults", {}) if model_cfg else {},
        }
        row["normalized_at"] = now_iso()
        normalized_products.append(row)

    state = {
        "meta": {
            "supplier_key": "demiand",
            "built_at": now_iso(),
            "products_count": len(normalized_products),
        },
        "products": normalized_products,
    }
    write_json(state_paths()["official_products"], state)
    return state

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

_WORD_RE = re.compile(r"[^a-z0-9а-яё]+", re.IGNORECASE)


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower().replace("ё", "е")
    text = _WORD_RE.sub(" ", text)
    return " ".join(text.split())


def _add_unique(index: dict[str, str], counts: Counter, key: str | None, product_key: str) -> None:
    if not key:
        return
    counts[key] += 1
    index[key] = product_key


def _unique_indexes(products: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    temp: dict[str, dict[str, str]] = defaultdict(dict)
    counts: dict[str, Counter] = defaultdict(Counter)

    for product in products:
        product_key = product.get("product_key")
        if not product_key:
            continue
        supplier = product.get("supplier_key") or ""
        official = product.get("official", {}) or {}
        article = _norm(official.get("product_id"))
        model = _norm(product.get("model_key"))
        variant = _norm(product.get("variant_key"))
        title = _norm(official.get("title_official"))

        _add_unique(temp["product_key"], counts["product_key"], _norm(product_key), product_key)
        _add_unique(temp["supplier_article"], counts["supplier_article"], f"{supplier}|{article}" if article else None, product_key)
        _add_unique(temp["article"], counts["article"], article, product_key)
        category = _norm(product.get("category_key"))
        _add_unique(temp["supplier_category_model_variant"], counts["supplier_category_model_variant"], f"{supplier}|{category}|{model}|{variant}" if supplier and category and model and variant else None, product_key)
        _add_unique(temp["category_model_variant"], counts["category_model_variant"], f"{category}|{model}|{variant}" if category and model and variant else None, product_key)
        _add_unique(temp["supplier_category_model"], counts["supplier_category_model"], f"{supplier}|{category}|{model}" if supplier and category and model else None, product_key)
        _add_unique(temp["category_model"], counts["category_model"], f"{category}|{model}" if category and model else None, product_key)
        _add_unique(temp["supplier_model_variant"], counts["supplier_model_variant"], f"{supplier}|{model}|{variant}" if model and variant else None, product_key)
        _add_unique(temp["model_variant"], counts["model_variant"], f"{model}|{variant}" if model and variant else None, product_key)
        _add_unique(temp["title"], counts["title"], title, product_key)

    result: dict[str, dict[str, str]] = {}
    for name, mapping in temp.items():
        result[name] = {key: value for key, value in mapping.items() if counts[name][key] == 1}
    return result


def _record_match_candidates(record: dict[str, Any]) -> list[tuple[str, str | None, int]]:
    product_key = _norm(record.get("product_key"))
    base_product_key = _norm(record.get("base_product_key"))
    supplier = record.get("supplier_key") or ""
    category = _norm(record.get("category_key"))
    article = _norm(record.get("official_article"))
    model = _norm(record.get("model_key"))
    variant = _norm(record.get("variant_key"))
    title = _norm(record.get("title"))

    return [
        ("product_key", base_product_key, 100),
        ("product_key", product_key, 100),
        ("supplier_article", f"{supplier}|{article}" if supplier and article else None, 96),
        ("article", article, 90),
        ("supplier_category_model_variant", f"{supplier}|{category}|{model}|{variant}" if supplier and category and model and variant else None, 88),
        ("category_model_variant", f"{category}|{model}|{variant}" if category and model and variant else None, 84),
        ("supplier_category_model", f"{supplier}|{category}|{model}" if supplier and category and model else None, 78),
        ("category_model", f"{category}|{model}" if category and model else None, 74),
        ("supplier_model_variant", f"{supplier}|{model}|{variant}" if supplier and model and variant else None, 72),
        ("model_variant", f"{model}|{variant}" if model and variant else None, 68),
        ("title", title, 60),
    ]


def match_one(record: dict[str, Any], indexes: dict[str, dict[str, str]]) -> dict[str, Any]:
    for method, key, confidence in _record_match_candidates(record):
        if not key:
            continue
        base_product_key = indexes.get(method, {}).get(key)
        if base_product_key:
            market_product_key = record.get("market_product_key") or record.get("product_key") or base_product_key
            if method == "product_key" and _norm(record.get("product_key")) == _norm(base_product_key):
                market_product_key = base_product_key
            return {
                **record,
                "matched_product_key": market_product_key,
                "matched_base_product_key": base_product_key,
                "matched_by": method,
                "match_confidence": max(int(record.get("match_confidence") or 0), confidence),
            }
    return {
        **record,
        "matched_product_key": None,
        "matched_by": None,
        "match_confidence": 0,
    }


def run(products: list[dict[str, Any]], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexes = _unique_indexes(products)
    return [match_one(record, indexes) for record in records]

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.json_io import read_json, write_json
from scripts.cs_kaspi.core.paths import ROOT, ensure_runtime_dirs, path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso

CSV_HEADERS = [
    "priority",
    "product_key",
    "supplier_key",
    "category_key",
    "model_key",
    "variant_key",
    "official_article",
    "official_price",
    "official_url",
    "official_title",
    "kaspi_title",
    "current_market_status",
    "market_sellable_reason",
    "current_market_source",
    "current_market_price",
    "current_market_url",
    "kaspi_price",
    "kaspi_stock",
    "lead_time_days",
    "recommended_source",
    "fill_source",
    "fill_url",
    "fill_price",
    "fill_available",
    "fill_stock",
    "fill_lead_time_days",
    "search_query",
    "notes",
]

INPUT_HEADERS = [
    "source",
    "product_key",
    "supplier_key",
    "category_key",
    "model_key",
    "variant_key",
    "official_article",
    "title",
    "url",
    "price",
    "available",
    "stock",
    "lead_time_days",
    "rating",
    "reviews_count",
]

CATEGORY_PRIORITY = {
    "air_fryers": 10,
    "coffee_makers": 20,
    "ovens": 30,
    "blenders": 40,
    "air_fryer_accessories": 50,
}


def _worklist_dir() -> Path:
    try:
        return path_from_config("artifacts_market_worklists_dir")
    except KeyError:
        return ROOT / "artifacts" / "market_worklists"


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except Exception:
        return default


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return path.as_posix()


def _load_products() -> list[dict[str, Any]]:
    state_dir = path_from_config("artifacts_state_dir")
    catalog = read_json(state_dir / "master_catalog.json", required=True)
    products = catalog.get("products", []) if isinstance(catalog, dict) else []
    if not products:
        raise RuntimeError("Master catalog is empty. Run build_master_catalog before build_market_worklist.")
    return [p for p in products if isinstance(p, dict)]


def _priority(product: dict[str, Any]) -> int:
    category_key = str(product.get("category_key") or "")
    official = product.get("official", {}) or {}
    base = CATEGORY_PRIORITY.get(category_key, 90)
    price = _int(official.get("price"), 0)
    if price >= 50_000:
        return base
    if price >= 25_000:
        return base + 1
    if price >= 10_000:
        return base + 2
    return base + 3


def _search_query(product: dict[str, Any]) -> str:
    official = product.get("official", {}) or {}
    brand = product.get("brand") or official.get("brand") or "Demiand"
    pieces = [
        brand,
        official.get("product_id") or "",
        product.get("model_key") or "",
        official.get("title_official") or "",
    ]
    result: list[str] = []
    seen: set[str] = set()
    for piece in pieces:
        text = _text(piece)
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return " ".join(result)


def _recommended_source(product: dict[str, Any]) -> str:
    category_key = str(product.get("category_key") or "")
    if category_key in {"air_fryers", "coffee_makers", "ovens", "blenders"}:
        return "ozon/wb/manual"
    return "manual/ozon/wb"


def _row(product: dict[str, Any]) -> dict[str, Any]:
    official = product.get("official", {}) or {}
    kaspi = product.get("kaspi_policy", {}) or {}
    market = product.get("market", {}) or {}
    status = product.get("status", {}) or {}
    title = official.get("title_official") or kaspi.get("kaspi_title") or ""
    market_sellable = market.get("sellable") is True
    return {
        "priority": _priority(product),
        "product_key": product.get("product_key"),
        "supplier_key": product.get("supplier_key"),
        "category_key": product.get("category_key"),
        "model_key": product.get("model_key"),
        "variant_key": product.get("variant_key"),
        "official_article": official.get("product_id") or official.get("article") or "",
        "official_price": official.get("price") or "",
        "official_url": official.get("url") or "",
        "official_title": title,
        "kaspi_title": kaspi.get("kaspi_title") or "",
        "current_market_status": "ready" if market_sellable else "missing",
        "market_sellable_reason": market.get("sellable_reason") or status.get("action_status") or "",
        "current_market_source": market.get("market_price_source") or "",
        "current_market_price": market.get("market_price") or "",
        "current_market_url": market.get("market_url") or "",
        "kaspi_price": kaspi.get("kaspi_price") or "",
        "kaspi_stock": kaspi.get("kaspi_stock") or "",
        "lead_time_days": kaspi.get("lead_time_days") or market.get("lead_time_days") or "",
        "recommended_source": _recommended_source(product),
        "fill_source": "",
        "fill_url": "",
        "fill_price": "",
        "fill_available": "",
        "fill_stock": "",
        "fill_lead_time_days": "",
        "search_query": _search_query(product),
        "notes": "для input/market заполнять fill_*; product_key не менять",
    }


def _input_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": row.get("fill_source") or "",
        "product_key": row.get("product_key") or "",
        "supplier_key": row.get("supplier_key") or "",
        "category_key": row.get("category_key") or "",
        "model_key": row.get("model_key") or "",
        "variant_key": row.get("variant_key") or "",
        "official_article": row.get("official_article") or "",
        "title": row.get("official_title") or "",
        "url": row.get("fill_url") or "",
        "price": row.get("fill_price") or "",
        "available": row.get("fill_available") or "",
        "stock": row.get("fill_stock") or "",
        "lead_time_days": row.get("fill_lead_time_days") or "",
        "rating": "",
        "reviews_count": "",
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _text(row.get(key)) for key in headers})


def _write_readme(path: Path, summary: dict[str, Any]) -> None:
    text = f"""CS-Kaspi market worklists

built_at: {summary.get('built_at')}
total_products: {summary.get('total_products')}
missing_market_products: {summary.get('missing_market_products')}
ready_market_products: {summary.get('ready_market_products')}

Файлы:
- market_missing_products.csv — товары, где ещё нет sellable market-данных.
- market_ready_products.csv — товары, где market-данные уже есть.
- market_all_products.csv — полный список товаров с текущим статусом рынка.
- market_input_missing_blank.csv — заготовка в формате input/market для товаров без market-данных.
- market_worklist_summary.json — краткая статистика.

Как работать:
1. Открой market_missing_products.csv.
2. Для нужных товаров заполни fill_source, fill_url, fill_price, fill_available, fill_stock, fill_lead_time_days.
3. Перенеси заполненные строки в боевой input-файл: input/market/manual/demiand_manual_market_real.csv, input/market/ozon/demiand_ozon_market.csv или input/market/wb/demiand_wb_market.csv.
4. В боевом файле должны быть стандартные колонки: source, product_key, url, price, available, stock, lead_time_days.
5. product_key менять нельзя.

Важно:
- Эти worklist-файлы лежат в artifacts и не являются боевым input сами по себе.
- Пустой market_input_missing_blank.csv нельзя просто класть в input/market как боевой файл.
- Для Ozon/WB активные строки должны иметь url, price, available=true и stock > 0, иначе safety gate остановит сборку.
"""
    path.write_text(text, encoding="utf-8")


def run() -> dict[str, Any]:
    ensure_runtime_dirs()
    products = _load_products()
    rows = [_row(product) for product in products]
    rows.sort(key=lambda r: (_int(r.get("priority"), 99), str(r.get("category_key") or ""), str(r.get("product_key") or "")))

    missing_rows = [row for row in rows if row.get("current_market_status") != "ready"]
    ready_rows = [row for row in rows if row.get("current_market_status") == "ready"]
    blank_input_rows = [_input_row(row) for row in missing_rows]

    out_dir = _worklist_dir()
    all_csv = out_dir / "market_all_products.csv"
    missing_csv = out_dir / "market_missing_products.csv"
    ready_csv = out_dir / "market_ready_products.csv"
    blank_csv = out_dir / "market_input_missing_blank.csv"
    summary_json = out_dir / "market_worklist_summary.json"
    readme_txt = out_dir / "README.txt"

    _write_csv(all_csv, rows, CSV_HEADERS)
    _write_csv(missing_csv, missing_rows, CSV_HEADERS)
    _write_csv(ready_csv, ready_rows, CSV_HEADERS)
    _write_csv(blank_csv, blank_input_rows, INPUT_HEADERS)

    summary = {
        "built_at": now_iso(),
        "total_products": len(rows),
        "missing_market_products": len(missing_rows),
        "ready_market_products": len(ready_rows),
        "missing_by_category": dict(Counter(row.get("category_key") for row in missing_rows)),
        "ready_by_category": dict(Counter(row.get("category_key") for row in ready_rows)),
        "files": {
            "all_products": _rel(all_csv),
            "missing_products": _rel(missing_csv),
            "ready_products": _rel(ready_csv),
            "blank_input": _rel(blank_csv),
            "readme": _rel(readme_txt),
        },
    }
    write_json(summary_json, summary)
    _write_readme(readme_txt, summary)

    return summary


if __name__ == "__main__":
    run()

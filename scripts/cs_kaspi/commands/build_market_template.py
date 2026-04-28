from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.json_io import read_json, write_json
from scripts.cs_kaspi.core.paths import ROOT, ensure_runtime_dirs, path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso

CSV_HEADERS = [
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
    "_official_title",
    "_official_price",
    "_kaspi_title",
    "_notes",
]


def _template_dir() -> Path:
    try:
        return path_from_config("artifacts_market_templates_dir")
    except KeyError:
        return ROOT / "artifacts" / "market_templates"


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _row(product: dict[str, Any]) -> dict[str, Any]:
    official = product.get("official", {}) or {}
    kaspi = product.get("kaspi_policy", {}) or {}
    title = official.get("title_official") or official.get("title") or kaspi.get("kaspi_title") or ""
    return {
        "source": "manual",
        "product_key": product.get("product_key"),
        "supplier_key": product.get("supplier_key"),
        "category_key": product.get("category_key"),
        "model_key": product.get("model_key"),
        "variant_key": product.get("variant_key"),
        "official_article": official.get("product_id") or official.get("article") or "",
        "title": title,
        "url": "",
        "price": "",
        "available": "",
        "stock": "",
        "lead_time_days": "",
        "rating": "",
        "reviews_count": "",
        "_official_title": title,
        "_official_price": official.get("price") or "",
        "_kaspi_title": kaspi.get("kaspi_title") or "",
        "_notes": "заполнить price/available/stock/url; product_key не менять",
    }


def _load_master_products() -> list[dict[str, Any]]:
    state_dir = path_from_config("artifacts_state_dir")
    catalog = read_json(state_dir / "master_catalog.json", required=True)
    products = catalog.get("products", []) if isinstance(catalog, dict) else []
    if not products:
        raise RuntimeError("Master catalog is empty. Run build_master_catalog before build_market_template.")
    return [p for p in products if isinstance(p, dict)]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADERS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _text(row.get(key)) for key in CSV_HEADERS})


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return path.as_posix()


def _write_readme(path: Path, *, rows_count: int, csv_path: Path, json_path: Path) -> None:
    text = f"""CS-Kaspi market input template

built_at: {now_iso()}
products: {rows_count}

Сгенерированные файлы:
- {_rel(csv_path)}
- {_rel(json_path)}

Как использовать CSV-шаблон:
1. Скачай файл manual_market_template.csv из artifacts/market_templates.
2. Заполни рыночные поля:
   - source: manual / ozon / wb
   - url: ссылка на источник цены/наличия
   - price: рыночная цена, число без пробелов и валюты
   - available: true/false, да/нет, 1/0, в наличии/нет в наличии
   - stock: остаток, число
   - lead_time_days: срок в днях
3. Не меняй product_key.
4. Готовый рабочий файл положи в проект по пути:
   input/market/manual/demiand_manual_market.csv
5. Запусти Build_All.

Важно:
- Колонки с подчёркиванием `_...` — справочные, они помогают видеть товар, но не являются обязательными.
- Файлы с `sample`, `example`, `readme` в названии market-loader игнорирует.
- Не клади незаполненный template напрямую в input/market/manual, иначе строки будут считаться рыночными записями без цены.
"""
    path.write_text(text, encoding="utf-8")


def run() -> dict[str, Any]:
    ensure_runtime_dirs()
    products = sorted(
        _load_master_products(),
        key=lambda p: (
            str(p.get("supplier_key") or ""),
            str(p.get("category_key") or ""),
            str(p.get("product_key") or ""),
        ),
    )
    rows = [_row(product) for product in products]

    out_dir = _template_dir()
    csv_path = out_dir / "manual_market_template.csv"
    json_path = out_dir / "manual_market_template.json"
    readme_path = out_dir / "README.txt"

    _write_csv(csv_path, rows)
    write_json(json_path, {"meta": {"built_at": now_iso(), "products": len(rows)}, "records": rows})
    _write_readme(readme_path, rows_count=len(rows), csv_path=csv_path, json_path=json_path)

    return {
        "built_at": now_iso(),
        "products": len(rows),
        "csv": _rel(csv_path),
        "json": _rel(json_path),
        "readme": _rel(readme_path),
    }


if __name__ == "__main__":
    run()

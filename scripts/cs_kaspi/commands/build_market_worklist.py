from __future__ import annotations

import csv
import re
from collections import Counter
from html import escape
from urllib.parse import quote_plus
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
    "market_priority_bucket",
    "recommended_source",
    "fill_source",
    "fill_url",
    "fill_price",
    "fill_available",
    "fill_stock",
    "fill_lead_time_days",
    "search_query",
    "search_ozon_url",
    "search_wb_url",
    "search_kaspi_url",
    "search_google_url",
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

CATEGORY_SEARCH_WORDS = {
    "air_fryers": "аэрогриль",
    "coffee_makers": "кофеварка",
    "ovens": "печь",
    "blenders": "блендер",
    "air_fryer_accessories": "аксессуар аэрогриль",
}

VARIANT_SEARCH_WORDS = {
    "black": "черный",
    "white": "белый",
    "metal": "металл",
    "ash": "пепельный",
    "caramel": "карамельный",
    "chocolate": "шоколадный",
}

MAX_SEARCH_QUERY_CHARS = 120


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


def _compact_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _article_for_search(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""

    text = text.replace("_", " ").replace("/", " ")
    text = re.sub(r"(?<=[0-9])(?=[A-Za-zА-Яа-яЁё])", " ", text)
    text = re.sub(r"(?<=[A-Za-zА-Яа-яЁё])(?=[0-9])", " ", text)
    text = re.sub(r"[(){}\[\],;:|]+", " ", text)
    text = re.sub(r"\s*-\s*", "-", text)
    return _compact_spaces(text)


def _model_for_search(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    text = text.replace("_", " ").replace("-", " ")
    return _compact_spaces(text).upper()


def _variant_for_search(product: dict[str, Any]) -> str:
    variant_key = str(product.get("variant_key") or "").lower()
    if not variant_key:
        return ""
    words: list[str] = []
    for key, label in VARIANT_SEARCH_WORDS.items():
        if key in variant_key:
            words.append(label)
    return _compact_spaces(" ".join(words))


def _title_hint(product: dict[str, Any]) -> str:
    """Короткая подсказка из title только для аксессуаров, где одного артикула мало."""
    category_key = str(product.get("category_key") or "")
    if category_key != "air_fryer_accessories":
        return ""

    official = product.get("official", {}) or {}
    title = _text(official.get("title_official"))
    if not title:
        return ""

    stop_words = {
        "demiand",
        "для",
        "к",
        "и",
        "с",
        "на",
        "в",
        "цвета",
        "черного",
        "белого",
        "аэрогрилю",
        "аэрогриля",
        "аэрогрилей",
    }
    words: list[str] = []
    for raw in re.split(r"\s+", title):
        word = re.sub(r"[^0-9A-Za-zА-Яа-яЁё-]+", "", raw).strip()
        if len(word) < 3:
            continue
        if word.lower() in stop_words:
            continue
        words.append(word)
        if len(words) >= 5:
            break
    return _compact_spaces(" ".join(words))


def _dedupe_words(query: str) -> str:
    result: list[str] = []
    seen: set[str] = set()
    for word in re.split(r"\s+", query):
        cleaned = word.strip()
        key = cleaned.lower().replace("ё", "е")
        if not cleaned or key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return " ".join(result)


def _trim_query(query: str, max_chars: int = MAX_SEARCH_QUERY_CHARS) -> str:
    query = _compact_spaces(query)
    if len(query) <= max_chars:
        return query

    words = query.split()
    result: list[str] = []
    for word in words:
        candidate = _compact_spaces(" ".join(result + [word]))
        if len(candidate) > max_chars:
            break
        result.append(word)
    return _compact_spaces(" ".join(result)) or query[:max_chars].strip()


def _search_query(product: dict[str, Any]) -> str:
    official = product.get("official", {}) or {}
    brand = product.get("brand") or official.get("brand") or "Demiand"
    category_key = str(product.get("category_key") or "")

    pieces = [
        brand,
        _article_for_search(official.get("product_id") or official.get("article") or ""),
        _model_for_search(product.get("model_key") or ""),
        CATEGORY_SEARCH_WORDS.get(category_key, ""),
        _variant_for_search(product),
        _title_hint(product),
    ]

    query = _dedupe_words(_compact_spaces(" ".join(_text(piece) for piece in pieces if _text(piece))))
    return _trim_query(query)


def _recommended_source(product: dict[str, Any]) -> str:
    category_key = str(product.get("category_key") or "")
    if category_key in {"air_fryers", "coffee_makers", "ovens", "blenders"}:
        return "ozon/wb/manual"
    return "manual/ozon/wb"


def _priority_bucket(product: dict[str, Any]) -> str:
    category_key = str(product.get("category_key") or "")
    official = product.get("official", {}) or {}
    price = _int(official.get("price"), 0)
    if category_key == "air_fryers":
        return "1_main_air_fryers"
    if category_key in {"coffee_makers", "ovens", "blenders"}:
        return "2_main_kitchen"
    if price >= 10_000:
        return "3_high_price_accessories"
    return "4_accessories"


def _search_urls(query: str) -> dict[str, str]:
    encoded = quote_plus(query)
    google_query = _compact_spaces(query + " купить Казахстан")
    return {
        "search_ozon_url": f"https://www.ozon.kz/search/?text={encoded}",
        "search_wb_url": f"https://www.wildberries.ru/catalog/0/search.aspx?search={encoded}",
        "search_kaspi_url": f"https://kaspi.kz/shop/search/?text={encoded}",
        "search_google_url": f"https://www.google.com/search?q={quote_plus(google_query)}",
    }


def _row(product: dict[str, Any]) -> dict[str, Any]:
    official = product.get("official", {}) or {}
    kaspi = product.get("kaspi_policy", {}) or {}
    market = product.get("market", {}) or {}
    status = product.get("status", {}) or {}
    title = official.get("title_official") or kaspi.get("kaspi_title") or ""
    market_sellable = market.get("sellable") is True
    query = _search_query(product)
    search_urls = _search_urls(query)
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
        "market_priority_bucket": _priority_bucket(product),
        "recommended_source": _recommended_source(product),
        "fill_source": "",
        "fill_url": "",
        "fill_price": "",
        "fill_available": "",
        "fill_stock": "",
        "fill_lead_time_days": "",
        "search_query": query,
        "search_ozon_url": search_urls["search_ozon_url"],
        "search_wb_url": search_urls["search_wb_url"],
        "search_kaspi_url": search_urls["search_kaspi_url"],
        "search_google_url": search_urls["search_google_url"],
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



def _short(value: Any, max_chars: int = 120) -> str:
    text = _text(value)
    if len(text) <= max_chars:
        return text

    words = text.split()
    result: list[str] = []
    for word in words:
        candidate = _compact_spaces(" ".join(result + [word]))
        if len(candidate) > max_chars:
            break
        result.append(word)

    return (_compact_spaces(" ".join(result)) or text[:max_chars]).rstrip(".,;:-") + "…"


def _html_link(url: Any, label: str) -> str:
    text = _text(url)
    if not text:
        return ""
    return f'<a href="{escape(text, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(label)}</a>'


def _write_html(path: Path, rows: list[dict[str, Any]], title: str, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    parts: list[str] = []

    parts.append(f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f7f7; color: #1f2933; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    .meta {{ margin: 0 0 18px; color: #52606d; line-height: 1.5; }}
    .hint {{ background: #fff7cc; border: 1px solid #f0d66a; padding: 12px 14px; border-radius: 10px; margin-bottom: 18px; }}
    table {{ border-collapse: collapse; width: 100%; background: #fff; box-shadow: 0 1px 8px rgba(15, 23, 42, .08); }}
    th, td {{ border: 1px solid #e4e7eb; padding: 8px 10px; vertical-align: top; font-size: 13px; }}
    th {{ background: #eef2f7; position: sticky; top: 0; z-index: 1; text-align: left; }}
    tr:nth-child(even) {{ background: #fafafa; }}
    .links a {{ display: inline-block; margin: 0 6px 6px 0; padding: 4px 7px; border-radius: 7px; background: #e6f4ff; color: #0967d2; text-decoration: none; }}
    .links a:hover {{ text-decoration: underline; }}
    .key {{ font-family: Consolas, monospace; font-size: 12px; color: #334e68; }}
    .fill {{ color: #7b8794; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <div class="meta">
    built_at: {escape(_text(summary.get("built_at")))}<br>
    total_products: {escape(_text(summary.get("total_products")))} |
    missing_market_products: {escape(_text(summary.get("missing_market_products")))} |
    ready_market_products: {escape(_text(summary.get("ready_market_products")))}
  </div>
  <div class="hint">
    Открывай ссылки Ozon/WB/Kaspi/Google, находи реальную цену и наличие, затем заполняй CSV-колонки
    <b>fill_source</b>, <b>fill_url</b>, <b>fill_price</b>, <b>fill_available</b>,
    <b>fill_stock</b>, <b>fill_lead_time_days</b>. Product_key не менять.
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Priority</th>
        <th>Product</th>
        <th>Search</th>
        <th>Links</th>
        <th>Fill fields</th>
      </tr>
    </thead>
    <tbody>
""")

    for idx, row in enumerate(rows, start=1):
        links = " ".join([
            _html_link(row.get("search_ozon_url"), "Ozon"),
            _html_link(row.get("search_wb_url"), "WB"),
            _html_link(row.get("search_kaspi_url"), "Kaspi"),
            _html_link(row.get("search_google_url"), "Google"),
            _html_link(row.get("official_url"), "Official"),
            _html_link(row.get("current_market_url"), "Market URL"),
        ])

        product_html = "<br>".join([
            f'<span class="key">{escape(_text(row.get("product_key")))}</span>',
            escape(_text(row.get("category_key"))),
            f'Артикул: {escape(_text(row.get("official_article")))}',
            f'Цена official: {escape(_text(row.get("official_price")))}',
            escape(_short(row.get("official_title"), 150)),
        ])

        fill_html = "<br>".join([
            f'source: <span class="fill">{escape(_text(row.get("fill_source")))}</span>',
            f'url: <span class="fill">{escape(_short(row.get("fill_url"), 80))}</span>',
            f'price: <span class="fill">{escape(_text(row.get("fill_price")))}</span>',
            f'available: <span class="fill">{escape(_text(row.get("fill_available")))}</span>',
            f'stock: <span class="fill">{escape(_text(row.get("fill_stock")))}</span>',
            f'lead_time_days: <span class="fill">{escape(_text(row.get("fill_lead_time_days")))}</span>',
        ])

        parts.append(f"""      <tr>
        <td>{idx}</td>
        <td>{escape(_text(row.get("priority")))}<br>{escape(_text(row.get("market_priority_bucket")))}</td>
        <td>{product_html}</td>
        <td>{escape(_text(row.get("search_query")))}</td>
        <td class="links">{links}</td>
        <td>{fill_html}</td>
      </tr>
""")

    parts.append("""    </tbody>
  </table>
</body>
</html>
""")
    path.write_text("".join(parts), encoding="utf-8")

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
- market_priority_missing_products.csv — приоритетные товары без market-данных: основная техника выше аксессуаров.
- market_input_missing_blank.csv — заготовка в формате input/market для товаров без market-данных.
- market_worklist_summary.json — краткая статистика.
- market_priority_missing_products.html — HTML-страница с кликабельными ссылками по приоритетным товарам.
- market_missing_products.html — HTML-страница по всем товарам без market-данных.
- market_ready_products.html — HTML-страница по товарам, где market-данные уже есть.

Как работать:
1. Открой market_missing_products.csv или market_priority_missing_products.csv.
2. Для быстрого поиска используй HTML-файлы или колонки search_ozon_url, search_wb_url, search_kaspi_url, search_google_url.
3. В patch 24 search_query специально укорочен: бренд + артикул + модель + тип товара + цвет.
4. Для нужных товаров заполни fill_source, fill_url, fill_price, fill_available, fill_stock, fill_lead_time_days.
5. Заполненный CSV можно положить в input/market/worklists/ — importer сам создаст стандартный input.
6. Либо перенеси заполненные строки в боевой input-файл: input/market/manual/demiand_manual_market_real.csv, input/market/ozon/demiand_ozon_market.csv или input/market/wb/demiand_wb_market.csv.
7. product_key менять нельзя.

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
    priority_missing_rows = [
        row for row in missing_rows
        if str(row.get("market_priority_bucket") or "").startswith(("1_", "2_", "3_"))
    ]
    blank_input_rows = [_input_row(row) for row in missing_rows]

    out_dir = _worklist_dir()
    all_csv = out_dir / "market_all_products.csv"
    missing_csv = out_dir / "market_missing_products.csv"
    priority_csv = out_dir / "market_priority_missing_products.csv"
    ready_csv = out_dir / "market_ready_products.csv"
    blank_csv = out_dir / "market_input_missing_blank.csv"
    missing_html = out_dir / "market_missing_products.html"
    priority_html = out_dir / "market_priority_missing_products.html"
    ready_html = out_dir / "market_ready_products.html"
    summary_json = out_dir / "market_worklist_summary.json"
    readme_txt = out_dir / "README.txt"

    _write_csv(all_csv, rows, CSV_HEADERS)
    _write_csv(missing_csv, missing_rows, CSV_HEADERS)
    _write_csv(priority_csv, priority_missing_rows, CSV_HEADERS)
    _write_csv(ready_csv, ready_rows, CSV_HEADERS)
    _write_csv(blank_csv, blank_input_rows, INPUT_HEADERS)

    summary = {
        "built_at": now_iso(),
        "total_products": len(rows),
        "missing_market_products": len(missing_rows),
        "ready_market_products": len(ready_rows),
        "missing_by_category": dict(Counter(row.get("category_key") for row in missing_rows)),
        "ready_by_category": dict(Counter(row.get("category_key") for row in ready_rows)),
        "missing_by_priority_bucket": dict(Counter(row.get("market_priority_bucket") for row in missing_rows)),
        "priority_missing_products": len(priority_missing_rows),
        "max_search_query_length": max((len(str(row.get("search_query") or "")) for row in rows), default=0),
        "files": {
            "all_products": _rel(all_csv),
            "missing_products": _rel(missing_csv),
            "priority_missing_products": _rel(priority_csv),
            "ready_products": _rel(ready_csv),
            "blank_input": _rel(blank_csv),
            "missing_products_html": _rel(missing_html),
            "priority_missing_products_html": _rel(priority_html),
            "ready_products_html": _rel(ready_html),
            "readme": _rel(readme_txt),
        },
    }
    write_json(summary_json, summary)
    _write_html(missing_html, missing_rows, "CS-Kaspi: товары без market-данных", summary)
    _write_html(priority_html, priority_missing_rows, "CS-Kaspi: приоритетный поиск market-данных", summary)
    _write_html(ready_html, ready_rows, "CS-Kaspi: товары с market-данными", summary)
    _write_readme(readme_txt, summary)

    return summary


if __name__ == "__main__":
    run()
